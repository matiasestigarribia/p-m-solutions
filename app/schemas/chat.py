"""Validated public chatbot request and response schemas."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

ChatRole = Literal["user", "assistant"]


class ChatHistoryMessage(BaseModel):
    role: ChatRole
    content: str = Field(min_length=1, max_length=4000)


class ChatRequestSchema(BaseModel):
    message: str = Field(min_length=2, max_length=1500)
    language: str = Field(default="pt", min_length=2, max_length=10)
    chat_history: list[ChatHistoryMessage] = Field(default_factory=list, max_length=8)

    @field_validator("message", "language")
    @classmethod
    def strip_values(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Value cannot be blank.")
        return value


class ChatResponseSchema(BaseModel):
    reply: str
