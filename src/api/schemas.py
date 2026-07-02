from pydantic import BaseModel, Field, field_validator
from typing import List
from enum import Enum


class Message(BaseModel):
    """A single message in a conversation."""
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1)


class ChatRequest(BaseModel):
    """POST /chat request body."""
    messages: List[Message] = Field(..., min_length=1, max_length=7)

    @field_validator('messages')
    @classmethod
    def validate_message_count(cls, v):
        """Leave room for the assistant response within eight total messages."""
        if len(v) > 7:
            raise ValueError("History is too long to answer within 8 total messages")
        if len(v) % 2 == 0:
            raise ValueError("Conversation history must end with a user message")
        for index, message in enumerate(v):
            expected = "user" if index % 2 == 0 else "assistant"
            if message.role != expected:
                raise ValueError(f"Message {index + 1} must have role '{expected}'")
        return v


class RecommendationItem(BaseModel):
    """Single assessment recommendation."""
    name: str = Field(..., min_length=1)
    url: str = Field(..., pattern="^https://www\\.shl\\.com")
    test_type: str = Field(..., pattern="^[A-Z0-9]+(,[A-Z0-9]+)*$", max_length=15)


class ChatResponse(BaseModel):
    """POST /chat response body."""
    reply: str = Field(..., min_length=1)
    recommendations: List[RecommendationItem] = Field(default_factory=list, max_length=10)
    end_of_conversation: bool = Field(default=False)


class HealthResponse(BaseModel):
    """GET /health response."""
    status: str = Field(default="ok")


class ConversationPhase(str, Enum):
    """Current phase of the conversation."""
    CLARIFYING = "clarifying"
    RECOMMENDING = "recommending"
    REFINING = "refining"
    COMPARING = "comparing"
    COMPLETE = "complete"
    REFUSING = "refusing"
