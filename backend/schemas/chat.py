from datetime import datetime
from pydantic import BaseModel, field_validator, ConfigDict


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Message cannot be empty")
        return v.strip()


class CitationItem(BaseModel):
    type: str
    file: str | None = None
    page: int | None = None
    excerpt: str | None = None
    entity: str | None = None
    relation: str | None = None
    target: str | None = None


class ChatResponse(BaseModel):
    conversation_id: str
    answer: str
    citations: list[CitationItem]
    query_mode: str = "mix"
    latency_ms: int | None = None


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str | None = None
    created_at: datetime
    updated_at: datetime


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    role: str
    content: str
    citations: list[dict] | None = None
    graphiti_synced: bool
    created_at: datetime
