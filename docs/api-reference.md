# API Reference

> 📚 **[← Back to Documentation Hub](README.md)** | **[Main README](../README.md)**

Complete reference for all API endpoints in the Amazon Chat Completions Server.

## 📋 Table of Contents

- [Authentication](#authentication)
- [Standard Endpoints](#standard-endpoints)
- [Reverse Integration Endpoints](#reverse-integration-endpoints)
- [Universal Endpoints](#universal-endpoints)
- [Documentation Endpoints](#documentation-endpoints)
- [Error Responses](#error-responses)
- [Request/Response Examples](#requestresponse-examples)

## Authentication

All API endpoints require authentication using an API key passed in the `X-API-Key` header.

```bash
curl -H "X-API-Key: your-api-key" http://localhost:8000/endpoint
```

**Authentication Errors:**
- `401 Unauthorized` - Missing or invalid API key
- `403 Forbidden` - API key lacks required permissions

## Standard Endpoints

### POST /v1/chat/completions

OpenAI-compatible chat completions endpoint.

**Request Body:**
```json
{
  "model": "gpt-4o-mini",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"}
  ],
  "temperature": 0.7,
  "max_tokens": 1000,
  "stream": false,
  "tools": [...],
  "tool_choice": "auto"
}
```

**Response:**
```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1677652288,
  "model": "gpt-4o-mini",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello! How can I help you today?"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 9,
    "completion_tokens": 12,
    "total_tokens": 21
  }
}
```

**Streaming Response:**
When `stream: true`, returns Server-Sent Events:
```
data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1677652288,"model":"gpt-4o-mini","choices":[{"index":0,"delta":{"role":"assistant","content":"Hello"},"finish_reason":null}]}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1677652288,"model":"gpt-4o-mini","choices":[{"index":0,"delta":{"content":"!"},"finish_reason":null}]}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1677652288,"model":"gpt-4o-mini","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}

data: [DONE]
```

### GET /v1/models

List available models.

**Response:**
```json
{
  "object": "list",
  "data": [
    {
      "id": "gpt-4o",
      "object": "model",
      "created": 1677610602,
      "owned_by": "openai"
    },
    {
      "id": "gpt-4o-mini",
      "object": "model",
      "created": 1677610602,
      "owned_by": "openai"
    }
  ]
}
```

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "version": "1.0.0",
  "services": {
    "openai": "available",
    "bedrock": "available"
  }
}
```

## Reverse Integration Endpoints

### POST /bedrock/claude/invoke-model

Bedrock Claude format with OpenAI models.

**Query Parameters:**
- `openai_model` (optional) - OpenAI model to use (default: gpt-4o-mini)

**Request Body:**
```json
{
  "anthropic_version": "bedrock-2023-05-31",
  "max_tokens": 1000,
  "messages": [
    {"role": "user", "content": "Hello!"}
  ],
  "system": "You are a helpful assistant.",
  "temperature": 0.7,
  "tools": [...],
  "tool_choice": {"type": "auto"}
}
```

**Response (Bedrock Claude format):**
```json
{
  "id": "msg_123",
  "type": "message",
  "role": "assistant",
  "content": [
    {"type": "text", "text": "Hello! How can I help you today?"}
  ],
  "model": "gpt-4o-mini-2024-07-18",
  "stop_reason": "end_turn",
  "usage": {
    "input_tokens": 9,
    "output_tokens": 12
  }
}
```

### POST /bedrock/claude/invoke-model-stream

Streaming version of Claude endpoint.

**Query Parameters:**
- `openai_model` (optional) - OpenAI model to use

**Request Body:** Same as `/bedrock/claude/invoke-model`

**Streaming Response:**
```
event: message_start
data: {"type":"message_start","message":{"id":"msg_123","type":"message","role":"assistant","content":[],"model":"gpt-4o-mini","stop_reason":null,"usage":{"input_tokens":9,"output_tokens":0}}}

event: content_block_start
data: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}

event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Hello"}}

event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"!"}}

event: content_block_stop
data: {"type":"content_block_stop","index":0}

event: message_delta
data: {"type":"message_delta","delta":{"stop_reason":"end_turn","usage":{"output_tokens":12}}}

event: message_stop
data: {"type":"message_stop"}
```

### POST /bedrock/titan/invoke-model

Bedrock Titan format with OpenAI models.

**Query Parameters:**
- `openai_model` (optional) - OpenAI model to use

**Request Body:**
```json
{
  "inputText": "User: Hello!\n\nBot:",
  "textGenerationConfig": {
    "maxTokenCount": 1000,
    "temperature": 0.7,
    "stopSequences": []
  }
}
```

**Response (Bedrock Titan format):**
```json
{
  "inputTextTokenCount": 5,
  "results": [
    {
      "tokenCount": 12,
      "outputText": " Hello! How can I help you today?",
      "completionReason": "FINISH"
    }
  ]
}
```

### POST /bedrock/titan/invoke-model-stream

Streaming version of Titan endpoint.

**Query Parameters:**
- `openai_model` (optional) - OpenAI model to use

**Request Body:** Same as `/bedrock/titan/invoke-model`

**Streaming Response:**
```json
{"outputText": " Hello"}
{"outputText": "!"}
{"outputText": " How"}
{"outputText": " can"}
{"outputText": " I"}
{"outputText": " help"}
{"outputText": " you"}
{"outputText": " today"}
{"outputText": "?"}
{"completionReason": "FINISH"}
```

## Universal Endpoints

### POST /v1/completions/universal

Auto-detecting endpoint that handles any format.

**Query Parameters:**
- `target_provider` (optional) - Force output format: "openai" or "bedrock"
- `model_override` (optional) - Override model selection

**Request Body:** Any supported format (OpenAI, Bedrock Claude, or Bedrock Titan)

**Response:** Matches input format unless overridden by `target_provider`

**Examples:**

1. **OpenAI input → OpenAI output:**
```bash
curl -X POST /v1/completions/universal \
  -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"Hello"}]}'
```

2. **Bedrock input → Bedrock output:**
```bash
curl -X POST /v1/completions/universal \
  -d '{"anthropic_version":"bedrock-2023-05-31","max_tokens":100,"messages":[{"role":"user","content":"Hello"}]}'
```

3. **OpenAI input → Bedrock output:**
```bash
curl -X POST /v1/completions/universal?target_provider=bedrock \
  -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"Hello"}]}'
```

### POST /v1/completions/universal/stream

Streaming version of universal endpoint.

**Query Parameters:** Same as `/v1/completions/universal`

**Request Body:** Any supported format

**Response:** Streaming in detected or specified format

### GET /v1/completions/universal/health

Health check for universal endpoints.

**Response:**
```json
{
  "status": "healthy",
  "supported_formats": ["openai", "bedrock_claude", "bedrock_titan"],
  "format_detection": "enabled",
  "streaming": "enabled"
}
```

## Documentation Endpoints

### GET /docs

Interactive API documentation (Swagger UI).

### GET /redoc

Alternative API documentation (ReDoc).

### GET /openapi.json

OpenAPI schema in JSON format.

## Error Responses

All endpoints return consistent error responses:

### 400 Bad Request
```json
{
  "error": {
    "type": "invalid_request_error",
    "message": "Invalid request format",
    "details": "Missing required field: messages"
  }
}
```

### 401 Unauthorized
```json
{
  "error": {
    "type": "authentication_error",
    "message": "Invalid API key"
  }
}
```

### 404 Not Found
```json
{
  "error": {
    "type": "not_found_error",
    "message": "Model not found",
    "details": "Model 'invalid-model' is not supported"
  }
}
```

### 429 Too Many Requests
```json
{
  "error": {
    "type": "rate_limit_error",
    "message": "Rate limit exceeded",
    "details": "Please try again in 60 seconds"
  }
}
```

### 500 Internal Server Error
```json
{
  "error": {
    "type": "internal_server_error",
    "message": "An unexpected error occurred",
    "details": "Please try again later"
  }
}
```

### 503 Service Unavailable
```json
{
  "error": {
    "type": "service_unavailable_error",
    "message": "Service temporarily unavailable",
    "details": "OpenAI API is currently unavailable"
  }
}
```

## Request/Response Examples

### Multimodal Content

**Request with image:**
```json
{
  "anthropic_version": "bedrock-2023-05-31",
  "max_tokens": 1000,
  "messages": [
    {
      "role": "user",
      "content": [
        {"type": "text", "text": "What's in this image?"},
        {
          "type": "image",
          "source": {
            "type": "base64",
            "media_type": "image/jpeg",
            "data": "iVBORw0KGgoAAAANSUhEUgAA..."
          }
        }
      ]
    }
  ]
}
```

### Tool Calls

**Request with tools:**
```json
{
  "anthropic_version": "bedrock-2023-05-31",
  "max_tokens": 1000,
  "messages": [
    {"role": "user", "content": "What's the weather in London?"}
  ],
  "tools": [
    {
      "name": "get_weather",
      "description": "Get current weather for a location",
      "input_schema": {
        "type": "object",
        "properties": {
          "location": {"type": "string", "description": "City name"}
        },
        "required": ["location"]
      }
    }
  ],
  "tool_choice": {"type": "auto"}
}
```

**Response with tool call:**
```json
{
  "id": "msg_123",
  "type": "message",
  "role": "assistant",
  "content": [
    {"type": "text", "text": "I'll check the weather in London for you."},
    {
      "type": "tool_use",
      "id": "toolu_123",
      "name": "get_weather",
      "input": {"location": "London"}
    }
  ],
  "model": "gpt-4o-mini",
  "stop_reason": "tool_use",
  "usage": {
    "input_tokens": 25,
    "output_tokens": 45
  }
}
```

### Multi-turn Conversation

**Request:**
```json
{
  "model": "gpt-4o-mini",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"},
    {"role": "assistant", "content": "Hello! How can I help you today?"},
    {"role": "user", "content": "What's 2+2?"}
  ]
}
```

**Response:**
```json
{
  "id": "chatcmpl-124",
  "object": "chat.completion",
  "created": 1677652300,
  "model": "gpt-4o-mini",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "2 + 2 equals 4."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 25,
    "completion_tokens": 8,
    "total_tokens": 33
  }
}
```

## Rate Limits

- **Default**: 100 requests per minute per API key
- **Burst**: Up to 10 concurrent requests
- **Headers**: Rate limit information in response headers:
  - `X-RateLimit-Limit`: Requests per minute
  - `X-RateLimit-Remaining`: Remaining requests
  - `X-RateLimit-Reset`: Reset time (Unix timestamp)

## Content Types

- **Request**: `application/json`
- **Response**: `application/json`
- **Streaming**: `text/plain` (Server-Sent Events)

## CORS

Cross-Origin Resource Sharing (CORS) is enabled for all origins in development. In production, configure specific origins as needed.

---

This API reference provides complete documentation for all endpoints. For interactive testing, visit `/docs` when the server is running. 