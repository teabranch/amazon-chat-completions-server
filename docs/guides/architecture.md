---
layout: default
title: Architecture
parent: Guides
nav_order: 3
description: "System design and architecture overview for Amazon Chat Completions Server"
---

# Architecture Guide
{: .no_toc }

This document describes the architecture of the Amazon Chat Completions Server, which implements a unified, provider-agnostic approach to LLM integration.
{: .fs-6 .fw-300 }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

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
Real-time Client Response (Server-Sent Events)
```

### 3. Error Handling Flow

```
API Error
    ↓
Error Classification (Auth/Rate Limit/Service/etc.)
    ↓
Error Mapping (Provider-specific → Standard format)
    ↓
Retry Logic (if applicable)
    ↓
Standardized Error Response
```

## Format Support Matrix

### Input Formats

| Format | Detection Key | Example |
|--------|---------------|---------|
| OpenAI | `model` + `messages` | `{"model": "gpt-4o-mini", "messages": [...]}` |
| Bedrock Claude | `anthropic_version` | `{"anthropic_version": "bedrock-2023-05-31", ...}` |
| Bedrock Titan | `inputText` | `{"inputText": "User: Hello", ...}` |

### Output Formats

| Format | Query Parameter | Response Structure |
|--------|-----------------|-------------------|
| OpenAI | `target_format=openai` | Standard OpenAI Chat Completions format |
| Bedrock Claude | `target_format=bedrock_claude` | Anthropic Claude message format |
| Bedrock Titan | `target_format=bedrock_titan` | Amazon Titan text generation format |

### Model Routing Patterns

| Pattern | Provider | Examples |
|---------|----------|----------|
| `gpt-*` | OpenAI | `gpt-4o-mini`, `gpt-3.5-turbo` |
| `text-*` | OpenAI | `text-davinci-003` |
| `anthropic.*` | Bedrock | `anthropic.claude-3-haiku-20240307-v1:0` |
| `amazon.*` | Bedrock | `amazon.titan-text-express-v1` |
| `ai21.*` | Bedrock | `ai21.j2-ultra-v1` |
| `us.anthropic.*` | Bedrock | `us.anthropic.claude-3-haiku-20240307-v1:0` |

## Deployment Architecture

### Development Environment

```
Developer Machine
├── Python Application
├── Local Configuration (.env)
├── Direct API Access
│   ├── OpenAI API
│   └── AWS Bedrock (via credentials)
└── Local Testing
```

### Production Environment

```
Load Balancer
    ↓
Container Orchestration (ECS/Kubernetes)
    ↓
Application Containers
├── Environment Variables
├── IAM Roles (for AWS)
├── Health Checks
└── Logging/Monitoring
    ↓
External APIs
├── OpenAI API
└── AWS Bedrock
```

### Security Architecture

```
Client Request
    ↓
API Gateway (optional)
    ↓
Authentication Layer (API Key)
    ↓
Rate Limiting
    ↓
Application Layer
    ↓
Provider Authentication
├── OpenAI API Key
└── AWS IAM Roles/Credentials
```

## Performance Considerations

### Caching Strategy

- **Model Metadata**: Cache available models list
- **Configuration**: Cache environment variables and settings
- **Connection Pooling**: Reuse HTTP connections to providers

### Concurrency Management

- **Async/Await**: Non-blocking I/O operations
- **Connection Limits**: Respect provider rate limits
- **Request Queuing**: Handle burst traffic gracefully

### Monitoring Points

- **Request Latency**: Track end-to-end response times
- **Provider Health**: Monitor upstream API availability
- **Error Rates**: Track and alert on error patterns
- **Resource Usage**: Monitor memory and CPU utilization

## Extensibility

### Adding New Providers

1. **Create Service Class**: Implement `AbstractLLMService`
2. **Update Factory**: Add routing logic for new model patterns
3. **Add Adapters**: Implement format conversion if needed
4. **Update Tests**: Add comprehensive test coverage

### Adding New Formats

1. **Update Detection**: Add format detection logic
2. **Create Adapters**: Implement conversion to/from standard format
3. **Update Routing**: Ensure proper service selection
4. **Document Format**: Add to API documentation

### Configuration Management

- **Environment Variables**: Runtime configuration
- **Feature Flags**: Toggle functionality without deployment
- **Provider Settings**: Per-provider configuration options

---

This architecture provides a solid foundation for a unified LLM integration server while maintaining flexibility for future enhancements and provider additions. 