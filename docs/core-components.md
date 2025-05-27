# Core Components

This document provides a comprehensive overview of the core components that make up the Amazon Chat Completions Server.

## 📋 Table of Contents

- [Core Models](#core-models)
- [Service Layer](#service-layer)
- [Adapter Layer](#adapter-layer)
- [Strategy Layer](#strategy-layer)
- [Utilities](#utilities)
- [API Layer](#api-layer)
- [CLI Layer](#cli-layer)

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
    def convert_to_provider_request(self, request: ChatCompletionRequest) -> Dict[str, Any]:
        # Convert to OpenAI format
        return {
            "model": self.model_id,
            "messages": [msg.model_dump() for msg in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": request.stream,
            "tools": request.tools,
            "tool_choice": request.tool_choice
        }
    
    def convert_from_provider_response(self, response, request) -> ChatCompletionResponse:
        # Convert from OpenAI response format
        return ChatCompletionResponse(
            id=response.id,
            choices=[...],  # Convert choices
            created=response.created,
            model=response.model,
            usage=Usage(...) if response.usage else None
        )
```

### Bedrock Adapter

**`BedrockAdapter`** - Handles AWS Bedrock integration using strategies:
```python
class BedrockAdapter(BaseLLMAdapter):
    def __init__(self, model_id: str, **kwargs):
        super().__init__(model_id, **kwargs)
        self.bedrock_model_id = get_bedrock_model_id(model_id)
        self.strategy = self._get_strategy()
    
    def _get_strategy(self) -> BedrockAdapterStrategy:
        if self.bedrock_model_id.startswith("anthropic.claude"):
            return ClaudeStrategy(self.bedrock_model_id, self._get_default_param)
        elif self.bedrock_model_id.startswith("amazon.titan"):
            return TitanStrategy(self.bedrock_model_id, self._get_default_param)
        else:
            raise ModelNotFoundError(f"Unsupported Bedrock model: {self.bedrock_model_id}")
```

### Reverse Adapter

**`BedrockToOpenAIAdapter`** - Handles reverse integration (Bedrock format → OpenAI models):
```python
class BedrockToOpenAIAdapter(BaseLLMAdapter):
    def __init__(self, openai_model: str, target_format: str = "bedrock", **kwargs):
        self.openai_model = openai_model
        self.target_format = target_format
        self.openai_adapter = OpenAIAdapter(model_id=openai_model, **kwargs)
    
    def convert_bedrock_to_openai(self, bedrock_request) -> ChatCompletionRequest:
        # Convert Bedrock format to OpenAI format
        pass
    
    def convert_openai_to_bedrock(self, openai_response) -> Dict[str, Any]:
        # Convert OpenAI response to Bedrock format
        pass
```

## Strategy Layer

The strategy layer handles model-specific logic within providers, particularly for Bedrock.

### Base Strategy

**`BedrockAdapterStrategy`** - Abstract base for Bedrock strategies:
```python
class BedrockAdapterStrategy(ABC):
    @abstractmethod
    def prepare_request_payload(self, request: ChatCompletionRequest, **kwargs) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def parse_response(self, response: Dict[str, Any], request: ChatCompletionRequest) -> ChatCompletionResponse:
        pass
    
    @abstractmethod
    def handle_stream_chunk(self, chunk: Dict[str, Any], request: ChatCompletionRequest, response_id: str, created: int) -> ChatCompletionChunk:
        pass
```

### Claude Strategy

**`ClaudeStrategy`** - Handles Anthropic Claude models:
```python
class ClaudeStrategy(BedrockAdapterStrategy):
    def prepare_request_payload(self, request: ChatCompletionRequest, **kwargs) -> Dict[str, Any]:
        system_prompt, messages = self._extract_system_prompt_and_messages(request.messages)
        
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": request.max_tokens or 1000,
            "messages": [self._convert_message(msg) for msg in messages],
            "temperature": request.temperature
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        if request.tools:
            payload["tools"] = self._convert_tools(request.tools)
            payload["tool_choice"] = self._convert_tool_choice(request.tool_choice)
        
        return payload
```

### Titan Strategy

**`TitanStrategy`** - Handles Amazon Titan models:
```python
class TitanStrategy(BedrockAdapterStrategy):
    def prepare_request_payload(self, request: ChatCompletionRequest, **kwargs) -> Dict[str, Any]:
        # Convert conversation to single input text
        input_text = self._format_conversation_for_titan(request.messages)
        
        return {
            "inputText": input_text,
            "textGenerationConfig": {
                "maxTokenCount": request.max_tokens or 1000,
                "temperature": request.temperature or 0.7,
                "stopSequences": []
            }
        }
```

## Utilities

### Configuration Management

**`AppConfig`** - Centralized configuration:
```python
class AppConfig:
    def __init__(self):
        load_dotenv()  # Load .env file
        
        # API Keys
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        self.API_KEY = os.getenv("API_KEY")
        
        # AWS Configuration
        self.AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
        self.AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
        self.AWS_PROFILE = os.getenv("AWS_PROFILE")
        
        # Default Settings
        self.DEFAULT_OPENAI_MODEL = os.getenv("DEFAULT_OPENAI_MODEL", "gpt-4o-mini")
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
```

### API Client

**`APIClient`** - Handles HTTP communication with providers:
```python
class APIClient:
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def make_openai_chat_completion_request(self, payload: Dict[str, Any], stream: bool = False):
        client = self.get_openai_client()
        if stream:
            return await client.chat.completions.create(**payload)
        else:
            return await client.chat.completions.create(**payload)
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def make_bedrock_request(self, model_id: str, payload: Dict[str, Any], stream: bool = False):
        client = self.get_bedrock_runtime_client()
        if stream:
            return client.invoke_model_with_response_stream(
                modelId=model_id,
                body=json.dumps(payload)
            )
        else:
            return client.invoke_model(
                modelId=model_id,
                body=json.dumps(payload)
            )
```

### Format Detection

**`RequestFormatDetector`** - Automatically detects request formats:
```python
class RequestFormatDetector:
    @staticmethod
    def detect_format(request_data: Dict[str, Any]) -> str:
        # Priority-based detection
        if "anthropic_version" in request_data:
            return "bedrock_claude"
        elif "inputText" in request_data:
            return "bedrock_titan"
        elif "model" in request_data and "messages" in request_data:
            return "openai"
        else:
            return "unknown"
```

### Exception Handling

**Custom Exceptions** - Hierarchical exception structure:
```python
class LLMIntegrationError(Exception):
    """Base exception for all LLM integration errors"""
    pass

class ConfigurationError(LLMIntegrationError):
    """Configuration-related errors"""
    pass

class APIConnectionError(LLMIntegrationError):
    """Network/connectivity errors"""
    pass

class AuthenticationError(LLMIntegrationError):
    """Authentication failures"""
    pass

class RateLimitError(LLMIntegrationError):
    """Rate limit exceeded"""
    pass

class ModelNotFoundError(LLMIntegrationError):
    """Model not found or not supported"""
    pass
```

## API Layer

### FastAPI Application

**`app.py`** - Main FastAPI application:
```python
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Amazon Chat Completions Server",
    description="Provider-agnostic chat completions API",
    version="1.0.0"
)

app.add_middleware(CORSMiddleware, allow_origins=["*"])
app.include_router(chat_router, prefix="/v1")
app.include_router(bedrock_router, prefix="/bedrock")
app.include_router(universal_router, prefix="/v1/completions")
```

### Route Handlers

**Chat Routes** - Standard OpenAI-compatible endpoints:
```python
@router.post("/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    service: AbstractLLMService = Depends(get_openai_service)
):
    try:
        if request.stream:
            return StreamingResponse(
                stream_chat_completion(service, request),
                media_type="text/plain"
            )
        else:
            response = await service.chat_completion(request.messages, **request.model_dump())
            return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**Bedrock Routes** - Bedrock-compatible endpoints:
```python
@router.post("/claude/invoke-model")
async def claude_invoke_model(
    request: BedrockClaudeRequest,
    openai_model: str = Query(default="gpt-4o-mini")
):
    adapter = BedrockToOpenAIAdapter(openai_model=openai_model, target_format="bedrock")
    # Process request and return Bedrock-formatted response
```

### Middleware

**Authentication Middleware**:
```python
async def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(HTTPBearer())):
    # Implementation of verify_api_key function
    pass
```

**Logging Middleware**:
```python
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(f"{request.method} {request.url} - {response.status_code} - {process_time:.3f}s")
    return response
```

## CLI Layer

### Click Application

**`main.py`** - Main CLI application:
```python
import click
from rich.console import Console

console = Console()

@click.group()
@click.version_option()
def cli():
    """Amazon Chat Completions Server CLI"""
    pass

@cli.command()
@click.option("--model", default="gpt-4o-mini", help="Model to use for chat")
@click.option("--server-url", default="http://localhost:8000", help="Server URL")
@click.option("--api-key", help="API key for authentication")
def chat(model, server_url, api_key):
    """Start an interactive chat session"""
    # Implementation
```

### Command Implementations

**Chat Command**:
```python
async def start_chat_session(model: str, server_url: str, api_key: str):
    console.print(f"[bold green]Starting chat with {model}[/bold green]")
    
    while True:
        user_input = console.input("[bold blue]You:[/bold blue] ")
        if user_input.lower() in ['exit', 'quit']:
            break
        
        # Send request to server and display response
        response = await send_chat_request(user_input, model, server_url, api_key)
        console.print(f"[bold yellow]Assistant:[/bold yellow] {response}")
```

**Configuration Commands**:
```python
@cli.group()
def config():
    """Configuration management"""
    pass

@config.command()
def set():
    """Set configuration values interactively"""
    # Interactive configuration setup

@config.command()
def show():
    """Show current configuration (sensitive values masked)"""
    # Display current configuration
```

This comprehensive component overview provides the foundation for understanding how all parts of the system work together to provide seamless, provider-agnostic LLM integration. 