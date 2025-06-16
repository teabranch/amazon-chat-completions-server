# Pydantic models for API responses will be defined here.
# For example:

from pydantic import BaseModel

# class ModelDetails(BaseModel):
#     id: str
#     object: str = "model"
#     created: int
#     owned_by: str
#
# class ModelListResponse(BaseModel):
#     object: str = "list"
#     data: List[ModelDetails]
#
# class ChatCompletionChoice(BaseModel):
#     index: int
#     message: Any # Would be a Message schema
#     finish_reason: Optional[str] = None
#
# class ChatCompletionUsage(BaseModel):
#     prompt_tokens: int
#     completion_tokens: int
#     total_tokens: int
#
# class ChatCompletionResponse(BaseModel):
#     id: str
#     object: str = "chat.completion"
#     created: int
#     model: str
#     choices: List[ChatCompletionChoice]
#     usage: ChatCompletionUsage

# Added for /v1/models endpoint


class ModelInfo(BaseModel):  # Corresponds to ModelProviderInfo from core
    id: str
    object: str = "model"  # Typically, each item is a model object
    created: int | None = None  # Timestamps can be optional
    owned_by: str | None = None  # e.g., "openai", "anthropic"
    # Add other fields from ModelProviderInfo if they should be in the API response
    # provider: Optional[str] = None (already in owned_by, or can be explicit)
    # display_name: Optional[str] = None


class ModelListResponse(BaseModel):
    object: str = "list"
    data: list[ModelInfo]
