"""Pydantic request and response schemas for chat persistence."""

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
