"""FastAPI entry point for Lenny Growth Assistant."""

from contextlib import asynccontextmanager
from collections.abc import Generator

import httpx
from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import models  # noqa: F401 - registers chat tables with Base.metadata
from app.config import get_settings
from app.database import Base, SessionLocal, check_database_connection, engine
from app.knowledge_models import DocumentChunk  # noqa: F401 - registers vector table
from app.llm import generate_reply
from app.models import ChatMessage, ChatSession
from app.retrieval import retrieve_chunks
from app.schemas import (
    ChatRequest,
    ChatResponse,
    MessageCreate,
    MessageRead,
    RetrievalSearchRequest,
    RetrievedSource,
    SessionCreate,
    SessionDetail,
    SessionRead,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Ensure pgvector exists before creating the application's tables."""
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.3.0",
    description="Evidence-grounded assistant for product and growth research.",
    lifespan=lifespan,
)


def get_db() -> Generator[Session, None, None]:
    """Provide one database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/health", tags=["operations"])
def health() -> dict[str, str]:
    """Report API process liveness; this does not imply DB/model readiness."""
    return {"status": "ok", "app": settings.app_name, "environment": settings.app_env}


@app.get("/health/database", tags=["operations"])
def database_health() -> dict[str, str]:
    """Check whether PostgreSQL can execute a simple query."""
    try:
        check_database_connection()
    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail="Database unavailable. Check DATABASE_URL and the PostgreSQL service.",
        ) from None
    return {"status": "ok", "database": "connected"}


@app.post(
    "/api/v1/sessions",
    response_model=SessionRead,
    status_code=status.HTTP_201_CREATED,
    tags=["sessions"],
)
def create_session(payload: SessionCreate, db: Session = Depends(get_db)) -> ChatSession:
    """Create an independent conversation session."""
    session = ChatSession(title=payload.title, user_metadata=payload.metadata)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@app.get(
    "/api/v1/sessions/{session_id}",
    response_model=SessionDetail,
    tags=["sessions"],
)
def get_session(session_id: str, db: Session = Depends(get_db)) -> ChatSession:
    """Fetch one session and its persisted messages."""
    session = db.get(ChatSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@app.post(
    "/api/v1/sessions/{session_id}/messages",
    response_model=MessageRead,
    status_code=status.HTTP_201_CREATED,
    tags=["messages"],
)
def create_message(
    session_id: str,
    payload: MessageCreate,
    db: Session = Depends(get_db),
) -> ChatMessage:
    """Persist a message in an existing session; this endpoint does not generate AI replies yet."""
    session = db.get(ChatSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    message = ChatMessage(
        session_id=session_id,
        role=payload.role,
        content=payload.content,
        message_metadata=payload.metadata,
    )
    db.add(message)
    session.updated_at = models.utc_now()
    db.commit()
    db.refresh(message)
    return message


@app.post("/api/v1/retrieval/search", response_model=list[RetrievedSource], tags=["retrieval"])
def search_knowledge(
    payload: RetrievalSearchRequest,
    db: Session = Depends(get_db),
) -> list[dict]:
    """Search indexed podcast passages; run ingestion before expecting results."""
    try:
        return retrieve_chunks(payload.query, db, payload.top_k)
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="The local embedding model timed out.") from None
    except httpx.HTTPError:
        raise HTTPException(
            status_code=502,
            detail="Could not reach Ollama. Check that Ollama is running and the embedding model is installed.",
        ) from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    except RuntimeError:
        raise HTTPException(status_code=502, detail="The configured embedding provider is unavailable.") from None


@app.post("/api/v1/chat", response_model=ChatResponse, tags=["chat"])
def chat(payload: ChatRequest, db: Session = Depends(get_db)) -> dict[str, str]:
    """Generate a local-model reply and persist both sides of the exchange."""
    session = db.get(ChatSession, payload.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    previous_messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == payload.session_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(12)
        .all()
    )
    previous_messages.reverse()
    conversation = [
        {"role": item.role, "content": item.content}
        for item in previous_messages
        if item.role in {"user", "assistant"}
    ]
    conversation.append({"role": "user", "content": payload.message})

    user_message = ChatMessage(
        session_id=payload.session_id,
        role="user",
        content=payload.message,
        message_metadata={},
    )
    db.add(user_message)
    session.updated_at = models.utc_now()
    db.commit()
    db.refresh(user_message)

    try:
        answer = generate_reply(conversation)
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="The local model timed out. Try again.") from None
    except httpx.HTTPError:
        raise HTTPException(
            status_code=502,
            detail="Could not reach Ollama. Check that Ollama is running and the configured model is installed.",
        ) from None
    except (RuntimeError, ValueError):
        raise HTTPException(status_code=502, detail="The configured model could not generate a reply.") from None

    assistant_message = ChatMessage(
        session_id=payload.session_id,
        role="assistant",
        content=answer,
        message_metadata={"provider": settings.llm_provider, "model": settings.ollama_model},
    )
    db.add(assistant_message)
    session.updated_at = models.utc_now()
    db.commit()
    db.refresh(assistant_message)

    return {
        "session_id": payload.session_id,
        "user_message_id": user_message.id,
        "assistant_message_id": assistant_message.id,
        "answer": answer,
        "provider": settings.llm_provider,
        "model": settings.ollama_model,
    }
