"""FastAPI entry point for Lenny Growth Assistant."""

from contextlib import asynccontextmanager
from collections.abc import Generator

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import Base, SessionLocal, check_database_connection, engine
from app import models  # noqa: F401 - registers ORM tables with Base.metadata
from app.models import ChatMessage, ChatSession
from app.schemas import MessageCreate, MessageRead, SessionCreate, SessionDetail, SessionRead

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Create initial tables for the assessment MVP."""
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.2.0",
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
    """Check whether the configured database can execute a simple query."""
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
