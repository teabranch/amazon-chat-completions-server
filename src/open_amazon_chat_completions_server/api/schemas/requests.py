from pydantic import BaseModel, Field, field_validator


class Message(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[Message] = Field(..., min_length=1)
    stream: bool = False
    max_tokens: int | None = None
    temperature: float | None = 0.7
    file_ids: list[str] | None = Field(
        default=None, description="List of file IDs to include in the context"
    )

    @field_validator("messages")
    @classmethod
    def messages_must_not_be_empty(cls, v):
        if not v:
            raise ValueError("messages must not be empty")
        return v

    @field_validator("file_ids")
    @classmethod
    def validate_file_ids(cls, v):
        if v is not None:
            # Validate file ID format (should start with "file-")
            for file_id in v:
                if not isinstance(file_id, str):
                    raise ValueError("file_ids must be a list of strings")
                if not file_id.startswith("file-"):
                    raise ValueError(
                        f"Invalid file ID format: {file_id}. File IDs must start with 'file-'"
                    )
        return v

    # Optional: Keep this if you want to add custom validation logic beyond min_items
    # @validator('messages')
    # def messages_must_not_be_empty(cls, v):
    #     if not v:
    #         raise ValueError('messages must not be empty')
    #     return v
