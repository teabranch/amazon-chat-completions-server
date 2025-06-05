---
layout: default
title: Core Components
parent: Guides
nav_order: 4
description: "Detailed component documentation for Amazon Chat Completions Server"
---

# Core Components
{: .no_toc }

This document provides a comprehensive overview of the core components that make up the Amazon Chat Completions Server.
{: .fs-6 .fw-300 }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Core Models

The core models define the standardized data structures used throughout the system, primarily based on OpenAI's Chat Completions API format.

### Message Models

**`Message`** - Represents a single message in a conversation:
```python
class Message(BaseModel):
    role: str  # "system", "user", "assistant", "tool"
    content: Union[str, List[ContentBlock]]  # Text or multimodal content
    name: Optional[str] = None  # For tool calls
    tool_call_id: Optional[str] = None  # For tool responses
    tool_calls: Optional[List[ToolCall]] = None  # For assistant tool calls
```

**`ContentBlock`** - Supports multimodal content:
```python
class ContentBlock(BaseModel):
    type: str  # "text", "image"
    text: Optional[str] = None
    image_url: Optional[ImageUrl] = None
    source: Optional[ImageSource] = None  # For Bedrock format
```

### Request/Response Models

**`ChatCompletionRequest`** - Standardized request format:
```python
class ChatCompletionRequest(BaseModel):
    messages: List[Message]
    model: str
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 1000
    stream: Optional[bool] = False
    tools: Optional[List[Tool]] = None
    tool_choice: Optional[Union[str, ToolChoice]] = None
```

**`ChatCompletionResponse`** - Standardized response format:
```python
class ChatCompletionResponse(BaseModel):
    id: str
    choices: List[ChatCompletionChoice]
    created: int
    model: str
    usage: Optional[Usage] = None
```

**`ChatCompletionChunk`** - For streaming responses:
```python
class ChatCompletionChunk(BaseModel):
    id: str
    choices: List[ChatCompletionChunkChoice]
    created: int
    model: str
```

### Bedrock Models

**`BedrockClaudeRequest`** - Claude-specific request format:
```python
class BedrockClaudeRequest(BaseModel):
    anthropic_version: str = "bedrock-2023-05-31"
    max_tokens: int
    messages: List[BedrockMessage]
    system: Optional[str] = None
    temperature: Optional[float] = None
    tools: Optional[List[BedrockTool]] = None
    tool_choice: Optional[BedrockToolChoice] = None
```

**`BedrockTitanRequest`** - Titan-specific request format:
```python
class BedrockTitanRequest(BaseModel):
    inputText: str
    textGenerationConfig: Optional[TitanTextGenerationConfig] = None
```

### Tool Models

**`Tool`** - Function definition:
```python
class Tool(BaseModel):
    type: str = "function"
    function: Function

class Function(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]
```

**`ToolCall`** - Function call from assistant:
```python
class ToolCall(BaseModel):
    id: str
    type: str = "function"
    function: FunctionCall

class FunctionCall(BaseModel):
    name: str
    arguments: str  # JSON string
```

## Service Layer

The service layer provides a high-level, consistent interface for interacting with LLMs.

### Abstract Service

**`AbstractLLMService`** - Defines the contract for all LLM services:
```python
class AbstractLLMService(ABC):
    @abstractmethod
    async def chat_completion(
        self,
        messages: List[Message],
        model_id: Optional[str] = None,
        stream: bool = False,
        **kwargs
    ) -> Union[ChatCompletionResponse, AsyncGenerator[ChatCompletionChunk, None]]:
        pass
```

### Concrete Services

**`ConcreteLLMService`** - Generic implementation that delegates to adapters:
```python
class ConcreteLLMService(AbstractLLMService):
    def __init__(self, adapter: BaseLLMAdapter):
        self.adapter = adapter
        self.provider_name = "generic"
    
    async def chat_completion(self, messages, **kwargs):
        request = ChatCompletionRequest(messages=messages, **kwargs)
        if kwargs.get('stream', False):
            return self.adapter.stream_chat_completion(request)
        else:
            return await self.adapter.chat_completion(request)
```

**Specialized Services**:
- `OpenAIService(ConcreteLLMService)` - For OpenAI models
- `BedrockService(ConcreteLLMService)` - For Bedrock models

### Service Factory

**`LLMServiceFactory`** - Creates and manages service instances:
```python
class LLMServiceFactory:
    @staticmethod
    @lru_cache(maxsize=128)
    def get_service(provider_name: str, model_id: str = None, **kwargs) -> AbstractLLMService:
        if provider_name == "openai":
            adapter = OpenAIAdapter(model_id=model_id, **kwargs)
            return OpenAIService(adapter=adapter)
        elif provider_name == "bedrock":
            adapter = BedrockAdapter(model_id=model_id, **kwargs)
            return BedrockService(adapter=adapter)
        else:
            raise ModelNotFoundError(f"Provider {provider_name} not supported")
```

## Adapter Layer

The adapter layer handles the conversion between the standardized format and provider-specific APIs.

### Base Adapter

**`BaseLLMAdapter`** - Abstract base class for all adapters:
```python
class BaseLLMAdapter(ABC):
    def __init__(self, model_id: str, **kwargs):
        self.model_id = model_id
        self.config = kwargs
    
    @abstractmethod
    def convert_to_provider_request(self, request: ChatCompletionRequest) -> Any:
        pass
    
    @abstractmethod
    def convert_from_provider_response(self, response: Any, request: ChatCompletionRequest) -> ChatCompletionResponse:
        pass
    
    @abstractmethod
    async def chat_completion(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        pass
    
    @abstractmethod
    async def stream_chat_completion(self, request: ChatCompletionRequest) -> AsyncGenerator[ChatCompletionChunk, None]:
        pass
```

### OpenAI Adapter

**`OpenAIAdapter`** - Handles OpenAI API integration:
```python
class OpenAIAdapter(BaseLLMAdapter):
    def __init__(self, model_id: str, **kwargs):
        super().__init__(model_id, **kwargs)
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    def convert_to_provider_request(self, request: ChatCompletionRequest) -> Dict[str, Any]:
        # Convert standardized request to OpenAI format
        return {
            "model": request.model,
            "messages": [msg.model_dump() for msg in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": request.stream,
            "tools": request.tools,
            "tool_choice": request.tool_choice
        }
    
    async def chat_completion(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        provider_request = self.convert_to_provider_request(request)
        response = await self.client.chat.completions.create(**provider_request)
        return self.convert_from_provider_response(response, request)
```

### Bedrock Adapter

**`BedrockAdapter`** - Handles AWS Bedrock integration with strategy pattern:
```python
class BedrockAdapter(BaseLLMAdapter):
    def __init__(self, model_id: str, **kwargs):
        super().__init__(model_id, **kwargs)
        self.bedrock_client = boto3.client('bedrock-runtime')
        self.strategy = self._get_strategy_for_model(model_id)
    
    def _get_strategy_for_model(self, model_id: str) -> BedrockAdapterStrategy:
        if "claude" in model_id:
            return ClaudeStrategy()
        elif "titan" in model_id:
            return TitanStrategy()
        else:
            raise ModelNotFoundError(f"No strategy for model: {model_id}")
    
    async def chat_completion(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        provider_request = self.strategy.convert_to_bedrock_request(request)
        response = await self._invoke_bedrock_model(provider_request)
        return self.strategy.convert_from_bedrock_response(response, request)
```

## Strategy Layer

The strategy layer implements the Strategy pattern for handling different Bedrock model families.

### Base Strategy

**`BedrockAdapterStrategy`** - Abstract strategy interface:
```python
class BedrockAdapterStrategy(ABC):
    @abstractmethod
    def convert_to_bedrock_request(self, request: ChatCompletionRequest) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def convert_from_bedrock_response(self, response: Dict[str, Any], original_request: ChatCompletionRequest) -> ChatCompletionResponse:
        pass
    
    @abstractmethod
    def convert_streaming_chunk(self, chunk: Dict[str, Any], request: ChatCompletionRequest) -> Optional[ChatCompletionChunk]:
        pass
```

### Claude Strategy

**`ClaudeStrategy`** - Handles Anthropic Claude models:
```python
class ClaudeStrategy(BedrockAdapterStrategy):
    def convert_to_bedrock_request(self, request: ChatCompletionRequest) -> Dict[str, Any]:
        # Extract system message
        system_message = None
        messages = []
        
        for msg in request.messages:
            if msg.role == "system":
                system_message = msg.content
            else:
                messages.append({
                    "role": msg.role,
                    "content": self._convert_content(msg.content)
                })
        
        bedrock_request = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": request.max_tokens or 1000,
            "messages": messages
        }
        
        if system_message:
            bedrock_request["system"] = system_message
        if request.temperature is not None:
            bedrock_request["temperature"] = request.temperature
        if request.tools:
            bedrock_request["tools"] = self._convert_tools(request.tools)
        
        return bedrock_request
    
    def convert_from_bedrock_response(self, response: Dict[str, Any], original_request: ChatCompletionRequest) -> ChatCompletionResponse:
        # Convert Claude response to standardized format
        content = ""
        tool_calls = []
        
        for content_block in response.get("content", []):
            if content_block["type"] == "text":
                content += content_block["text"]
            elif content_block["type"] == "tool_use":
                tool_calls.append(ToolCall(
                    id=content_block["id"],
                    function=FunctionCall(
                        name=content_block["name"],
                        arguments=json.dumps(content_block["input"])
                    )
                ))
        
        return ChatCompletionResponse(
            id=response.get("id", f"msg_{uuid.uuid4().hex[:8]}"),
            choices=[ChatCompletionChoice(
                index=0,
                message=Message(
                    role="assistant",
                    content=content,
                    tool_calls=tool_calls if tool_calls else None
                ),
                finish_reason=self._map_stop_reason(response.get("stop_reason"))
            )],
            created=int(time.time()),
            model=original_request.model,
            usage=Usage(
                prompt_tokens=response.get("usage", {}).get("input_tokens", 0),
                completion_tokens=response.get("usage", {}).get("output_tokens", 0),
                total_tokens=response.get("usage", {}).get("input_tokens", 0) + response.get("usage", {}).get("output_tokens", 0)
            )
        )
```

### Titan Strategy

**`TitanStrategy`** - Handles Amazon Titan models:
```python
class TitanStrategy(BedrockAdapterStrategy):
    def convert_to_bedrock_request(self, request: ChatCompletionRequest) -> Dict[str, Any]:
        # Convert messages to single input text
        input_text = self._messages_to_text(request.messages)
        
        config = {}
        if request.max_tokens:
            config["maxTokenCount"] = request.max_tokens
        if request.temperature is not None:
            config["temperature"] = request.temperature
        
        return {
            "inputText": input_text,
            "textGenerationConfig": config
        }
    
    def convert_from_bedrock_response(self, response: Dict[str, Any], original_request: ChatCompletionRequest) -> ChatCompletionResponse:
        # Convert Titan response to standardized format
        results = response.get("results", [])
        content = results[0].get("outputText", "") if results else ""
        
        return ChatCompletionResponse(
            id=f"titan_{uuid.uuid4().hex[:8]}",
            choices=[ChatCompletionChoice(
                index=0,
                message=Message(role="assistant", content=content),
                finish_reason=self._map_completion_reason(results[0].get("completionReason") if results else None)
            )],
            created=int(time.time()),
            model=original_request.model,
            usage=Usage(
                prompt_tokens=response.get("inputTextTokenCount", 0),
                completion_tokens=results[0].get("tokenCount", 0) if results else 0,
                total_tokens=response.get("inputTextTokenCount", 0) + (results[0].get("tokenCount", 0) if results else 0)
            )
        )
```

## Utilities

### Configuration Management

**`AppConfig`** - Centralized configuration:
```python
class AppConfig:
    # API Keys
    OPENAI_API_KEY: str = Field(..., env="OPENAI_API_KEY")
    API_KEY: str = Field(..., env="API_KEY")
    
    # AWS Configuration
    AWS_ACCESS_KEY_ID: Optional[str] = Field(None, env="AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = Field(None, env="AWS_SECRET_ACCESS_KEY")
    AWS_REGION: str = Field("us-east-1", env="AWS_REGION")
    AWS_PROFILE: Optional[str] = Field(None, env="AWS_PROFILE")
    
    # Defaults
    DEFAULT_OPENAI_MODEL: str = Field("gpt-4o-mini", env="DEFAULT_OPENAI_MODEL")
    LOG_LEVEL: str = Field("INFO", env="LOG_LEVEL")
    
    class Config:
        env_file = ".env"
        case_sensitive = True
```

### Exception Handling

**Exception Hierarchy:**
```python
class LLMIntegrationError(Exception):
    """Base exception for LLM integration errors"""
    pass

class ConfigurationError(LLMIntegrationError):
    """Configuration-related errors"""
    pass

class ModelNotFoundError(LLMIntegrationError):
    """Model not found or not supported"""
    pass

class AuthenticationError(LLMIntegrationError):
    """Authentication failures"""
    pass

class RateLimitError(LLMIntegrationError):
    """Rate limiting errors"""
    pass

class APIConnectionError(LLMIntegrationError):
    """API connection failures"""
    pass

class ServiceUnavailableError(LLMIntegrationError):
    """Service temporarily unavailable"""
    pass
```

### Format Detection

**`RequestFormatDetector`** - Detects input format:
```python
class RequestFormatDetector:
    @staticmethod
    def detect_format(request_data: Dict[str, Any]) -> RequestFormat:
        # Priority-based detection
        if "anthropic_version" in request_data:
            return RequestFormat.BEDROCK_CLAUDE
        elif "inputText" in request_data:
            return RequestFormat.BEDROCK_TITAN
        elif "model" in request_data and "messages" in request_data:
            return RequestFormat.OPENAI
        else:
            return RequestFormat.UNKNOWN
```

### Response Conversion

**`ResponseConverter`** - Converts between response formats:
```python
class ResponseConverter:
    @staticmethod
    def convert_to_bedrock_claude(response: ChatCompletionResponse) -> Dict[str, Any]:
        # Convert OpenAI response to Bedrock Claude format
        content = []
        
        message = response.choices[0].message
        if message.content:
            content.append({"type": "text", "text": message.content})
        
        if message.tool_calls:
            for tool_call in message.tool_calls:
                content.append({
                    "type": "tool_use",
                    "id": tool_call.id,
                    "name": tool_call.function.name,
                    "input": json.loads(tool_call.function.arguments)
                })
        
        return {
            "id": response.id,
            "type": "message",
            "role": "assistant",
            "content": content,
            "model": response.model,
            "stop_reason": "end_turn",
            "usage": {
                "input_tokens": response.usage.prompt_tokens if response.usage else 0,
                "output_tokens": response.usage.completion_tokens if response.usage else 0
            }
        }
```

## API Layer

### FastAPI Application

**Main Application:**
```python
app = FastAPI(
    title="Amazon Chat Completions Server",
    description="Unified, provider-agnostic chat completions API",
    version="1.0.0"
)

# Include routers
app.include_router(chat_router, prefix="/v1")
app.include_router(health_router)
app.include_router(models_router, prefix="/v1")
```

### Authentication

**API Key Authentication:**
```python
async def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(HTTPBearer())):
    if not credentials or credentials.credentials != app_config.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return credentials.credentials
```

### Unified Endpoint

**Chat Completions Endpoint:**
```python
@router.post("/chat/completions")
async def unified_chat_completions(
    request: Request,
    target_format: Optional[str] = Query(None),
    api_key: str = Depends(verify_api_key)
):
    # Parse request body
    request_data = await request.json()
    
    # Detect input format
    input_format = RequestFormatDetector.detect_format(request_data)
    
    # Convert to standardized format if needed
    if input_format == RequestFormat.BEDROCK_CLAUDE:
        standardized_request = BedrockToOpenAIAdapter.convert_request(request_data)
    elif input_format == RequestFormat.BEDROCK_TITAN:
        standardized_request = TitanToOpenAIAdapter.convert_request(request_data)
    else:
        standardized_request = ChatCompletionRequest(**request_data)
    
    # Route to appropriate service
    service = LLMServiceFactory.get_service_for_model(standardized_request.model)
    
    # Execute request
    if standardized_request.stream:
        return StreamingResponse(
            stream_response(service, standardized_request, target_format),
            media_type="text/plain"
        )
    else:
        response = await service.chat_completion(standardized_request)
        
        # Convert response format if requested
        if target_format:
            response = ResponseConverter.convert_response(response, target_format)
        
        return response
```

## CLI Layer

### Command Structure

**Main CLI:**
```python
@click.group()
@click.version_option()
def cli():
    """Amazon Chat Completions Server CLI"""
    pass

# Add commands
cli.add_command(serve_command)
cli.add_command(chat_command)
cli.add_command(config_command)
cli.add_command(models_command)
```

### Configuration Commands

**Config Management:**
```python
@click.group()
def config():
    """Manage configuration settings"""
    pass

@config.command()
@click.option("--key", help="Configuration key to set")
@click.option("--value", help="Configuration value")
def set(key: Optional[str], value: Optional[str]):
    """Set configuration values"""
    if key and value:
        # Set specific key-value pair
        set_config_value(key, value)
    else:
        # Interactive configuration
        interactive_config_setup()
```

### Interactive Chat

**Chat Command:**
```python
@click.command()
@click.option("--model", default="gpt-4o-mini", help="Model to use")
@click.option("--server-url", default="http://localhost:8000", help="Server URL")
@click.option("--api-key", help="API key for authentication")
def chat(model: str, server_url: str, api_key: Optional[str]):
    """Start interactive chat session"""
    chat_session = InteractiveChatSession(
        model=model,
        server_url=server_url,
        api_key=api_key or os.getenv("API_KEY")
    )
    chat_session.start()
```

---

This comprehensive overview covers all the major components of the Amazon Chat Completions Server. Each component is designed to be modular, testable, and extensible, following SOLID principles and clean architecture patterns. 