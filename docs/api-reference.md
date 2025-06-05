---
layout: default
title: API Reference
nav_order: 3
description: "Complete API reference for Amazon Chat Completions Server"
---

# API Reference
{: .no_toc }

Complete reference for all API endpoints in the Amazon Chat Completions Server.
{: .fs-6 .fw-300 }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Authentication

All API endpoints require authentication using an API key passed in the `Authorization` header with Bearer format.

```bash
curl -H "Authorization: Bearer your-api-key" http://localhost:8000/endpoint
```

**Authentication Errors:**
- `401 Unauthorized` - Missing or invalid API key
- `403 Forbidden` - API key lacks required permissions

## Unified Endpoint

### POST /v1/chat/completions

This is the **main unified endpoint** for all chat completion requests. It automatically:

- **Auto-detects input format** (OpenAI, Bedrock Claude, Bedrock Titan)
- **Routes to appropriate provider** based on model ID
- **Converts between formats** as needed
- **Supports streaming and non-streaming** requests
- **Maintains full compatibility** with OpenAI Chat Completions API

**Query Parameters:**
- `target_format` (optional): `openai`, `bedrock_claude`, or `bedrock_titan`

**Request Body Examples:**

**OpenAI Format:**
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

**Bedrock Claude Format:**
```json
{
  "anthropic_version": "bedrock-2023-05-31",
  "model": "anthropic.claude-3-haiku-20240307-v1:0",
  "max_tokens": 1000,
  "messages": [
    {"role": "user", "content": "Hello!"}
  ],
  "temperature": 0.7,
  "stream": false
}
```

**Bedrock Titan Format:**
```json
{
  "model": "amazon.titan-text-express-v1",
  "inputText": "User: Hello!\n\nBot:",
  "textGenerationConfig": {
    "maxTokenCount": 1000,
    "temperature": 0.7,
    "stopSequences": []
  }
}
```

**Response (OpenAI Format - Default):**
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
When `stream: true`, returns Server-Sent Events in the appropriate format based on the model and target format.

**Format Conversion Example:**
```bash
# OpenAI input → Bedrock Claude output
curl -X POST "http://localhost:8000/v1/chat/completions?target_format=bedrock_claude" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

**Response (Bedrock Claude Format):**
```json
{
  "id": "msg_123",
  "type": "message",
  "role": "assistant",
  "content": [
    {"type": "text", "text": "Hello! How can I help you today?"}
  ],
  "model": "gpt-4o-mini",
  "stop_reason": "end_turn",
  "usage": {
    "input_tokens": 9,
    "output_tokens": 12
  }
}
```

## Standard Endpoints

### GET /v1/chat/completions/health

Health check for the unified endpoint.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "version": "1.0.0",
  "message": "Unified model routing operational",
  "supported_input_formats": ["openai", "bedrock_claude", "bedrock_titan"],
  "model_routing": "enabled"
}
```

### GET /v1/models

List available models from all configured providers.

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
    },
    {
      "id": "anthropic.claude-3-haiku-20240307-v1:0",
      "object": "model",
      "created": 1677610602,
      "owned_by": "anthropic"
    }
  ]
}
```

### GET /health

General health check endpoint.

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

### 422 Unprocessable Entity
```json
{
  "error": {
    "type": "validation_error",
    "message": "Request validation failed",
    "details": "Field 'max_tokens' must be a positive integer"
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

**Request with image (Bedrock Claude format):**
```json
{
  "anthropic_version": "bedrock-2023-05-31",
  "model": "anthropic.claude-3-haiku-20240307-v1:0",
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

**Request with tools (Bedrock Claude format):**
```json
{
  "anthropic_version": "bedrock-2023-05-31",
  "model": "anthropic.claude-3-haiku-20240307-v1:0",
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

**Response with tool call (Bedrock Claude format):**
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
  "model": "anthropic.claude-3-haiku-20240307-v1:0",
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

### Streaming Example

**Request:**
```json
{
  "model": "gpt-4o-mini",
  "messages": [
    {"role": "user", "content": "Tell me a short story"}
  ],
  "stream": true
}
```

**Streaming Response:**
```
data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1677652288,"model":"gpt-4o-mini","choices":[{"index":0,"delta":{"role":"assistant","content":""},"finish_reason":null}]}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1677652288,"model":"gpt-4o-mini","choices":[{"index":0,"delta":{"content":"Once"},"finish_reason":null}]}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1677652288,"model":"gpt-4o-mini","choices":[{"index":0,"delta":{"content":" upon"},"finish_reason":null}]}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1677652288,"model":"gpt-4o-mini","choices":[{"index":0,"delta":{"content":" a"},"finish_reason":null}]}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1677652288,"model":"gpt-4o-mini","choices":[{"index":0,"delta":{"content":" time..."},"finish_reason":"stop"}]}

data: [DONE]
```

## Model Routing

The unified endpoint automatically routes requests based on model ID patterns:

### OpenAI Models
- `gpt-*` (e.g., `gpt-4o-mini`, `gpt-3.5-turbo`)
- `text-*` (e.g., `text-davinci-003`)
- `dall-e-*` (e.g., `dall-e-3`)

### Bedrock Models
- `anthropic.*` (e.g., `anthropic.claude-3-haiku-20240307-v1:0`)
- `amazon.*` (e.g., `amazon.titan-text-express-v1`)
- `ai21.*`, `cohere.*`, `meta.*`
- Regional formats: `us.anthropic.*`, `eu.anthropic.*`

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

This API reference provides complete documentation for the unified endpoint. For interactive testing, visit `/docs` when the server is running. 