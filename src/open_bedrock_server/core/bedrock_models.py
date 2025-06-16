from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class BedrockContentBlock(BaseModel):
    """Bedrock content block for multimodal content"""

    type: str
    text: str | None = None
    source: dict[str, Any] | None = None  # For image content

    @field_validator("type")
    @classmethod
    def validate_type(cls, v):
        allowed_types = ["text", "image", "tool_use", "tool_result"]
        if v not in allowed_types:
            raise ValueError(f"Content block type must be one of {allowed_types}")
        return v


class BedrockMessage(BaseModel):
    """Bedrock message format"""

    role: Literal["user", "assistant"]
    content: str | list[BedrockContentBlock]

    @field_validator("content", mode="before")
    @classmethod
    def validate_content(cls, v):
        if isinstance(v, str):
            return v
        elif isinstance(v, list):
            # Convert dict items to BedrockContentBlock if needed
            content_blocks = []
            for item in v:
                if isinstance(item, dict):
                    content_blocks.append(BedrockContentBlock(**item))
                elif isinstance(item, BedrockContentBlock):
                    content_blocks.append(item)
                else:
                    raise ValueError(
                        "Content list items must be dicts or BedrockContentBlock instances"
                    )
            return content_blocks
        else:
            raise ValueError("Content must be string or list of content blocks")


class BedrockTool(BaseModel):
    """Bedrock tool definition"""

    name: str
    description: str
    input_schema: dict[str, Any]


class BedrockToolChoice(BaseModel):
    """Bedrock tool choice specification"""

    type: Literal["auto", "any", "tool"]
    name: str | None = None  # Required when type is "tool"

    @field_validator("name")
    @classmethod
    def validate_name_for_tool_type(cls, v, info):
        if info.data.get("type") == "tool" and not v:
            raise ValueError("name is required when type is 'tool'")
        return v


class BedrockClaudeRequest(BaseModel):
    """Bedrock Claude request format"""

    anthropic_version: str = "bedrock-2023-05-31"
    max_tokens: int = Field(..., gt=0)
    messages: list[BedrockMessage] = Field(..., min_length=1)
    system: str | None = None
    temperature: float | None = Field(None, ge=0.0, le=1.0)
    top_p: float | None = Field(None, ge=0.0, le=1.0)
    top_k: int | None = Field(None, ge=0)
    stop_sequences: list[str] | None = None
    tools: list[BedrockTool] | None = None
    tool_choice: str | BedrockToolChoice | None = None

    @field_validator("tool_choice", mode="before")
    @classmethod
    def validate_tool_choice(cls, v):
        if isinstance(v, str):
            if v in ["auto", "any"]:
                return BedrockToolChoice(type=v)
            else:
                raise ValueError("String tool_choice must be 'auto' or 'any'")
        return v


class BedrockTitanConfig(BaseModel):
    """Bedrock Titan text generation configuration"""

    maxTokenCount: int = Field(..., gt=0)
    temperature: float | None = Field(None, ge=0.0, le=1.0)
    topP: float | None = Field(None, ge=0.0, le=1.0)
    stopSequences: list[str] | None = None


class BedrockTitanRequest(BaseModel):
    """Bedrock Titan request format"""

    inputText: str
    textGenerationConfig: BedrockTitanConfig


class BedrockClaudeResponse(BaseModel):
    """Bedrock Claude response format"""

    id: str
    type: str = "message"
    role: Literal["assistant"]
    content: list[BedrockContentBlock]
    model: str
    stop_reason: Literal["end_turn", "max_tokens", "stop_sequence", "tool_use"]
    stop_sequence: str | None = None
    usage: dict[str, int]  # {"input_tokens": int, "output_tokens": int}


class BedrockTitanResult(BaseModel):
    """Bedrock Titan result"""

    tokenCount: int
    outputText: str
    completionReason: Literal["FINISH", "LENGTH", "CONTENT_FILTERED"]


class BedrockTitanResponse(BaseModel):
    """Bedrock Titan response format"""

    inputTextTokenCount: int
    results: list[dict[str, Any]]  # Using Dict to match the test expectations


# Streaming response models
class BedrockClaudeStreamChunk(BaseModel):
    """Bedrock Claude streaming chunk"""

    type: str
    index: int | None = None
    delta: dict[str, Any] | None = None
    content_block: BedrockContentBlock | None = None
    usage: dict[str, int] | None = None


class BedrockTitanStreamChunk(BaseModel):
    """Bedrock Titan streaming chunk"""

    outputText: str
    index: int
    totalOutputTextTokenCount: int | None = None
    completionReason: str | None = None


# Enum for request format detection
class RequestFormat(str, Enum):
    OPENAI = "openai"
    BEDROCK_CLAUDE = "bedrock_claude"
    BEDROCK_TITAN = "bedrock_titan"
    UNKNOWN = "unknown"
