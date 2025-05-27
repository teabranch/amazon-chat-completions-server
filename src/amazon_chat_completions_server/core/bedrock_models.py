from typing import List, Optional, Literal, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class BedrockContentBlock(BaseModel):
    """Bedrock content block for multimodal content"""

    type: str
    text: Optional[str] = None
    source: Optional[Dict[str, Any]] = None  # For image content

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
    content: Union[str, List[BedrockContentBlock]]

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
    input_schema: Dict[str, Any]


class BedrockToolChoice(BaseModel):
    """Bedrock tool choice specification"""

    type: Literal["auto", "any", "tool"]
    name: Optional[str] = None  # Required when type is "tool"

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
    messages: List[BedrockMessage] = Field(..., min_length=1)
    system: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=0.0, le=1.0)
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0)
    top_k: Optional[int] = Field(None, ge=0)
    stop_sequences: Optional[List[str]] = None
    tools: Optional[List[BedrockTool]] = None
    tool_choice: Optional[Union[str, BedrockToolChoice]] = None

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
    temperature: Optional[float] = Field(None, ge=0.0, le=1.0)
    topP: Optional[float] = Field(None, ge=0.0, le=1.0)
    stopSequences: Optional[List[str]] = None


class BedrockTitanRequest(BaseModel):
    """Bedrock Titan request format"""

    inputText: str
    textGenerationConfig: BedrockTitanConfig


class BedrockClaudeResponse(BaseModel):
    """Bedrock Claude response format"""

    id: str
    type: str = "message"
    role: Literal["assistant"]
    content: List[BedrockContentBlock]
    model: str
    stop_reason: Literal["end_turn", "max_tokens", "stop_sequence", "tool_use"]
    stop_sequence: Optional[str] = None
    usage: Dict[str, int]  # {"input_tokens": int, "output_tokens": int}


class BedrockTitanResult(BaseModel):
    """Bedrock Titan result"""

    tokenCount: int
    outputText: str
    completionReason: Literal["FINISH", "LENGTH", "CONTENT_FILTERED"]


class BedrockTitanResponse(BaseModel):
    """Bedrock Titan response format"""

    inputTextTokenCount: int
    results: List[Dict[str, Any]]  # Using Dict to match the test expectations


# Streaming response models
class BedrockClaudeStreamChunk(BaseModel):
    """Bedrock Claude streaming chunk"""

    type: str
    index: Optional[int] = None
    delta: Optional[Dict[str, Any]] = None
    content_block: Optional[BedrockContentBlock] = None
    usage: Optional[Dict[str, int]] = None


class BedrockTitanStreamChunk(BaseModel):
    """Bedrock Titan streaming chunk"""

    outputText: str
    index: int
    totalOutputTextTokenCount: Optional[int] = None
    completionReason: Optional[str] = None


# Enum for request format detection
class RequestFormat(str, Enum):
    OPENAI = "openai"
    BEDROCK_CLAUDE = "bedrock_claude"
    BEDROCK_TITAN = "bedrock_titan"
    UNKNOWN = "unknown"
