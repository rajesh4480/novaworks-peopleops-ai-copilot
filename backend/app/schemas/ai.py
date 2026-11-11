from typing import Any

from pydantic import BaseModel, Field


class AIChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class PolicyChatResponse(BaseModel):
    answer: str
    sources: list[dict[str, Any]] = Field(default_factory=list)


class SQLChatResponse(BaseModel):
    answer: str
    sql: str | None = None
    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)


class ActionChatResponse(BaseModel):
    answer: str
    action: str | None = None
    status: str
    result: dict[str, Any] | None = None