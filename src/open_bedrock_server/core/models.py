from typing import Any, Literal

from pydantic import BaseModel, Field


# --- Core Message Structures (OpenAI-like) ---
class Message(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str | list[dict[str, Any]] | None = (
        None  # content can be string or list of content blocks for multimodal, and can be None for tool calls
    )
    name: str | None = None  # For tool calls
    tool_call_id: str | None = None  # For tool responses
    tool_calls: list[dict[str, Any]] | None = (
        None  # For assistant messages with tool calls
    )

    @property
    def is_tool_call(self) -> bool:
        return bool(self.tool_calls)

    @property
    def is_tool_response(self) -> bool:
        return bool(self.tool_call_id)

    def model_post_init(self, __context) -> None:
        # Validate that either content or tool_calls is present for non-tool messages
        if self.role != "tool" and self.content is None and self.tool_calls is None:
            raise ValueError(
                "Either content or tool_calls must be provided for non-tool messages"
            )

        # Validate tool call structure
        if self.tool_calls:
            for tool_call in self.tool_calls:
                if not isinstance(tool_call, dict):
                    raise ValueError("Tool calls must be dictionaries")
                if (
                    "id" not in tool_call
                    or "type" not in tool_call
                    or "function" not in tool_call
                ):
                    raise ValueError(
                        "Tool call missing required fields: id, type, function"
                    )
                if not isinstance(tool_call["function"], dict):
                    raise ValueError("Tool call function must be a dictionary")
                if (
                    "name" not in tool_call["function"]
                    or "arguments" not in tool_call["function"]
                ):
                    raise ValueError(
                        "Tool call function missing required fields: name, arguments"
                    )


class ChatCompletionRequest(BaseModel):
    messages: list[Message] = Field(..., min_length=1)
    model: str  # This will be the generic model identifier, mapped internally
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, gt=0)
    stream: bool | None = False
    # Add other common OpenAI parameters as needed (e.g., top_p, stop, presence_penalty, etc.)
    tool_choice: str | dict[str, Any] | None = None
    tools: list[dict[str, Any]] | None = None

    # File management support
    file_ids: list[str] | None = Field(
        default=None,
        description="List of file IDs to include in the conversation context",
    )

    # Knowledge Base support
    knowledge_base_id: str | None = Field(
        default=None, description="Knowledge Base ID for RAG functionality"
    )
    auto_kb: bool | None = Field(
        default=False, description="Auto-detect when to use knowledge base"
    )
    retrieval_config: dict[str, Any] | None = Field(
        default=None, description="Knowledge base retrieval configuration"
    )
    citation_format: Literal["openai", "bedrock"] | None = Field(
        default="openai", description="Citation format preference"
    )

    @property
    def is_tool_call_request(self) -> bool:
        return bool(self.tools)

    def model_post_init(self, __context) -> None:
        if not self.messages:
            raise ValueError("messages must not be empty")

        # Validate tool structure
        if self.tools:
            for tool in self.tools:
                if not isinstance(tool, dict):
                    raise ValueError("Tools must be dictionaries")
                if "type" not in tool or "function" not in tool:
                    raise ValueError("Tool missing required fields: type, function")
                if not isinstance(tool["function"], dict):
                    raise ValueError("Tool function must be a dictionary")
                if (
                    "name" not in tool["function"]
                    or "description" not in tool["function"]
                    or "parameters" not in tool["function"]
                ):
                    raise ValueError(
                        "Tool function missing required fields: name, description, parameters"
                    )


class ChoiceDelta(BaseModel):
    content: str | None = None
    role: Literal["system", "user", "assistant", "tool"] | None = None
    tool_calls: list[dict[str, Any]] | None = None


class ChatCompletionChunkChoice(BaseModel):
    delta: ChoiceDelta
    finish_reason: (
        Literal[
            "stop",
            "length",
            "tool_calls",
            "content_filter",
            "end_turn",
            "max_tokens",
            "stop_sequence",
        ]
        | None
    ) = None
    index: int


class ChatCompletionChunk(BaseModel):
    id: str
    choices: list[ChatCompletionChunkChoice]
    created: int
    model: str
    object: Literal["chat.completion.chunk"] = "chat.completion.chunk"
    system_fingerprint: str | None = None


class ChatCompletionChoice(BaseModel):
    message: Message
    finish_reason: (
        Literal[
            "stop",
            "length",
            "tool_calls",
            "content_filter",
            "end_turn",
            "max_tokens",
            "stop_sequence",
        ]
        | None
    ) = None
    index: int


class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int | None = None
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    id: str
    choices: list[ChatCompletionChoice]
    created: int  # Unix timestamp
    model: str  # Model ID used for the completion
    object: Literal["chat.completion"] = "chat.completion"
    system_fingerprint: str | None = None
    usage: Usage | None = None


# --- Bedrock Specific Structures (Illustrative - will be more detailed in adapter/strategy) ---

# These are simplified. Actual Bedrock request/response bodies are complex and model-dependent.
# The conversion logic will handle the detailed mapping.


class BedrockClaudeMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str | list[dict[str, Any]]


class BedrockClaudeRequestBody(BaseModel):
    anthropic_version: str = "bedrock-2023-05-31"
    messages: list[BedrockClaudeMessage]
    system: str | None = None
    max_tokens: int = Field(
        ..., alias="max_tokens_to_sample"
    )  # Example of alias for older versions if needed
    temperature: float | None = None
    # ... other Claude specific params (top_p, top_k, stop_sequences)


class BedrockTitanTextGenerationConfig(BaseModel):
    maxTokenCount: int
    temperature: float | None = None
    stopSequences: list[str] | None = None
    topP: float | None = None


class BedrockTitanRequestBody(BaseModel):
    inputText: str
    textGenerationConfig: BedrockTitanTextGenerationConfig
    # ... other Titan specific params


class BedrockContentBlock(BaseModel):
    type: str
    text: str | None = None
    # Potentially other types like 'image' for multimodal


class BedrockClaudeResponse(BaseModel):
    id: str
    type: str
    role: Literal["assistant"]
    content: list[BedrockContentBlock]
    model: str
    stop_reason: Literal["end_turn", "max_tokens", "stop_sequence"]
    stop_sequence: str | None = None
    usage: dict[str, int]  # { "input_tokens": ..., "output_tokens": ... }


class BedrockTitanResult(BaseModel):
    tokenCount: int
    outputText: str
    completionReason: Literal["FINISH", "LENGTH", "CONTENT_FILTERED"]


class BedrockTitanResponse(BaseModel):
    inputTextTokenCount: int
    results: list[BedrockTitanResult]


# The following ModelProviderInfo might be useful for the service factory or model listing logic.
class ModelProviderInfo(BaseModel):
    id: str  # The model ID recognized by the API (e.g., "gpt-4o-mini", "anthropic.us.anthropic.claude-3-5-haiku-20241022-v1:0-20240307-v1:0")
    provider: str  # e.g., "openai", "bedrock"
    display_name: str | None = None  # A user-friendly name
    # Add other relevant details, e.g., if it supports streaming, context window size etc.
