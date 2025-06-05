from pydantic import BaseModel, Field, field_validator
from typing import List, Optional


class Message(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[Message] = Field(..., min_length=1)
    stream: bool = False
    max_tokens: Optional[int] = None
    temperature: Optional[float] = 0.7

    @field_validator("messages")
    @classmethod
    def messages_must_not_be_empty(cls, v):
        if not v:
            raise ValueError("messages must not be empty")
        return v

    # Optional: Keep this if you want to add custom validation logic beyond min_items
    # @validator('messages')
    # def messages_must_not_be_empty(cls, v):
    #     if not v:
    #         raise ValueError('messages must not be empty')
    #     return v
