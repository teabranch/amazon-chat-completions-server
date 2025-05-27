# Architecture Guide

> 📚 **[← Back to Documentation Hub](README.md)** | **[Main README](../README.md)**

This document describes the architecture of the Amazon Chat Completions Server, which implements a unified, provider-agnostic approach to LLM integration.

## Core Principles

*   **Unified Interface:** Single endpoint (`/v1/chat/completions`) handles all format conversions and provider routing
*   **Auto-Detection:** Intelligent format detection eliminates the need for format-specific endpoints
*   **Model-Based Routing:** Automatic provider selection based on model ID patterns
*   **Format Conversion:** Seamless translation between OpenAI, Bedrock Claude, and Bedrock Titan formats
*   **Streaming Support:** Real-time response streaming with format preservation

## Unified Architecture

```mermaid
graph TD
    A[Client Request] --> B[/v1/chat/completions]
    B --> C{Format Detection}
    
    C --> D1[OpenAI Format]
    C --> D2[Bedrock Claude Format]
    C --> D3[Bedrock Titan Format]
    
    D1 --> E{Model-Based Routing}
    D2 --> F[Format Conversion] --> E
    D3 --> F
    
    E --> G1[OpenAI Service]
    E --> G2[Bedrock Service]
    
    G1 --> H1[OpenAI API]
    G2 --> H2[AWS Bedrock API]
    
    H1 --> I[Response Processing]
    H2 --> I
    
    I --> J{Target Format?}
    J --> K1[OpenAI Response]
    J --> K2[Bedrock Claude Response]
    J --> K3[Bedrock Titan Response]
    
    K1 --> L[Client Response]
    K2 --> L
    K3 --> L

    classDef endpoint fill:#E6E6FA,stroke:#B0C4DE,stroke-width:2px,color:#333;
    classDef service fill:#F0F8FF,stroke:#87CEEB,stroke-width:2px,color:#333;
    classDef api fill:#FFF8DC,stroke:#DAA520,stroke-width:2px,color:#333;
    
    class B endpoint;
    class G1,G2 service;
    class H1,H2 api;
```

## Core Components

### 1. Unified Endpoint Layer

**Single Entry Point:**
- `POST /v1/chat/completions` - Handles all chat completion requests
- `GET /v1/chat/completions/health` - Health check for unified system
- `GET /v1/models` - Lists available models from all providers
- `GET /health` - General system health

**Key Features:**
- Auto-detects input format (OpenAI, Bedrock Claude, Bedrock Titan)
- Routes to appropriate provider based on model ID
- Supports format conversion via `target_format` query parameter
- Handles both streaming and non-streaming requests

### 2. Format Detection Layer

**RequestFormatDetector:**
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

### 3. Model-Based Routing Layer

**LLMServiceFactory:**
```python
class LLMServiceFactory:
    @staticmethod
    def get_service_for_model(model_id: str) -> AbstractLLMService:
        # OpenAI models: gpt-*, text-*, dall-e-*
        if model_id.startswith(("gpt-", "text-", "dall-e-")):
            return OpenAIService()
        
        # Bedrock models: anthropic.*, amazon.*, ai21.*, etc.
        elif any(model_id.startswith(prefix) for prefix in 
                ["anthropic.", "amazon.", "ai21.", "cohere.", "meta."]):
            return BedrockService()
        
        # Regional Bedrock: us.anthropic.*, eu.anthropic.*, etc.
        elif len(model_id.split(".")) > 2:
            return BedrockService()
        
        else:
            raise ModelNotFoundError(f"Unsupported model: {model_id}")
```

### 4. Service Layer

**Abstract Service Interface:**
```python
class AbstractLLMService(ABC):
    @abstractmethod
    async def chat_completion(
        self,
        request: ChatCompletionRequest
    ) -> Union[ChatCompletionResponse, AsyncGenerator[ChatCompletionChunk, None]]:
        pass
```

**Concrete Services:**
- `OpenAIService` - Handles OpenAI API integration
- `BedrockService` - Handles AWS Bedrock integration with strategy pattern

### 5. Adapter Layer

**Format Conversion:**
```python
class BedrockToOpenAIAdapter:
    def convert_bedrock_to_openai_request(self, bedrock_request) -> ChatCompletionRequest:
        # Convert Bedrock format to OpenAI format
        pass
    
    def convert_openai_to_bedrock_response(self, openai_response, target_format) -> Dict:
        # Convert OpenAI response to Bedrock format
        pass
```

**Strategy Pattern for Bedrock:**
- `ClaudeStrategy` - Handles Anthropic Claude models
- `TitanStrategy` - Handles Amazon Titan models
- Extensible for additional Bedrock model families

### 6. API Client Layer

**Unified API Client:**
```python
class APIClient:
    @retry(stop=stop_after_attempt(3))
    async def make_openai_request(self, payload: Dict) -> Any:
        # OpenAI API calls with retry logic
        pass
    
    @retry(stop=stop_after_attempt(3))
    async def make_bedrock_request(self, model_id: str, payload: Dict) -> Any:
        # Bedrock API calls with retry logic
        pass
```

## Data Flow

### 1. Request Processing Flow

```
Client Request
    ↓
Format Detection (OpenAI/Bedrock Claude/Bedrock Titan)
    ↓
Model Extraction (from request)
    ↓
Service Routing (based on model ID patterns)
    ↓
Format Conversion (if needed)
    ↓
Provider API Call (OpenAI/Bedrock)
    ↓
Response Processing
    ↓
Format Conversion (if target_format specified)
    ↓
Client Response
```

### 2. Streaming Flow

```
Streaming Request (stream=true)
    ↓
Format Detection & Routing (same as above)
    ↓
Streaming API Call
    ↓
Chunk Processing & Format Conversion
    ↓
Server-Sent Events (SSE) Response
    ↓
Client Receives Real-time Chunks
```

## Format Support Matrix

| Input Format | Output Format | Conversion Required | Supported |
|-------------|---------------|-------------------|-----------|
| OpenAI | OpenAI | No | ✅ |
| OpenAI | Bedrock Claude | Yes | ✅ |
| OpenAI | Bedrock Titan | Yes | ✅ |
| Bedrock Claude | OpenAI | Yes | ✅ |
| Bedrock Claude | Bedrock Claude | No | ✅ |
| Bedrock Titan | OpenAI | Yes | ✅ |
| Bedrock Titan | Bedrock Titan | No | ✅ |

## Authentication & Security

**API Key Authentication:**
```python
async def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(HTTPBearer())):
    if not credentials or credentials.credentials != app_config.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return credentials.credentials
```

**Security Features:**
- API key validation on all endpoints
- Request/response logging with sensitive data masking
- CORS configuration for cross-origin requests
- Input validation using Pydantic models

## Error Handling

**Hierarchical Exception Structure:**
```python
LLMIntegrationError (Base)
├── ConfigurationError
├── ModelNotFoundError
├── AuthenticationError
├── RateLimitError
├── APIConnectionError
└── ServiceUnavailableError
```

**Error Response Format:**
```json
{
  "error": {
    "type": "error_type",
    "message": "Human-readable message",
    "details": "Additional context"
  }
}
```

## Configuration Management

**Environment-Based Configuration:**
```python
class AppConfig:
    # API Keys
    OPENAI_API_KEY: str
    API_KEY: str
    
    # AWS Configuration
    AWS_ACCESS_KEY_ID: Optional[str]
    AWS_SECRET_ACCESS_KEY: Optional[str]
    AWS_REGION: str = "us-east-1"
    AWS_PROFILE: Optional[str]
    
    # Defaults
    DEFAULT_OPENAI_MODEL: str = "gpt-4o-mini"
    LOG_LEVEL: str = "INFO"
```

## Monitoring & Observability

**Request Logging:**
- Request/response timing
- Model routing decisions
- Format conversion operations
- Error tracking and categorization

**Health Checks:**
- Unified endpoint health (`/v1/chat/completions/health`)
- Provider availability checks
- Configuration validation

## Scalability Considerations

**Horizontal Scaling:**
- Stateless design enables multiple server instances
- Load balancing across instances
- Shared configuration via environment variables

**Performance Optimizations:**
- Service instance caching in `LLMServiceFactory`
- Connection pooling for API clients
- Streaming responses for long completions

**Resource Management:**
- Configurable timeouts and retry policies
- Rate limiting and quota management
- Memory-efficient streaming processing

## Extension Points

**Adding New Providers:**
1. Implement `AbstractLLMService`
2. Add model ID patterns to `LLMServiceFactory`
3. Create format conversion adapters if needed
4. Update configuration and documentation

**Adding New Bedrock Models:**
1. Create new strategy class implementing `BedrockAdapterStrategy`
2. Update `BedrockAdapter` to use new strategy
3. Add model ID mappings
4. Write comprehensive tests

This unified architecture provides a clean, maintainable, and extensible foundation for multi-provider LLM integration while maintaining a simple, consistent API surface. 