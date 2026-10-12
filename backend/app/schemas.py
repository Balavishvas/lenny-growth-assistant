"""Pydantic request and response schemas for chat and retrieval APIs."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class SessionCreate(BaseModel):
    title: str = Field(default="New conversation", min_length=1, max_length=200)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MessageCreate(BaseModel):
    role: Literal["user", "assistant"] = "user"
    content: str = Field(min_length=1, max_length=30000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    role: str
    content: str
    message_metadata: dict[str, Any] = Field(validation_alias="message_metadata")
    created_at: datetime


class SessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    user_metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class SessionDetail(SessionRead):
    messages: list[MessageRead]


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=36)
    message: str = Field(min_length=1, max_length=30000)
    provider: Literal["ollama", "anthropic"] = "ollama"
    model: str | None = Field(default=None, min_length=1, max_length=120)
    api_key: str | None = Field(default=None, min_length=10, max_length=500)


class ChatResponse(BaseModel):
    session_id: str
    user_message_id: str
    assistant_message_id: str
    answer: str
    provider: str
    model: str
    sources: list["RetrievedSource"] = Field(default_factory=list)
    grounded: bool = False


class RetrievalSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    top_k: int = Field(default=5, ge=1, le=20)


class RetrievedSource(BaseModel):
    chunk_id: str
    source_id: str
    source_type: str
    title: str
    guest: str | None = None
    url: str | None = None
    publish_date: str | None = None
    chunk_index: int
    content: str
    distance: float
