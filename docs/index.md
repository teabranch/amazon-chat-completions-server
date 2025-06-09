---
description: Amazon Chat Completions Server - A unified, provider-agnostic chat completions API server
layout: default
nav_order: 1
permalink: /
title: Home
---

# Amazon Chat Completions Server

{: .fs-9 }

A unified, provider-agnostic chat completions API server supporting OpenAI and AWS Bedrock.
{: .fs-6 .fw-300 }

[Get started now](getting-started){: .btn .btn-primary .fs-5 .mb-4 .mb-md-0 .mr-2 }
[View on GitHub](https://github.com/teabranch/open-amazon-chat-completions-server){: .btn .fs-5 .mb-4 .mb-md-0 }

---

## 🚀 Quick Start

### Installation & Setup

```bash
# Clone and install
git clone https://github.com/teabranch/open-amazon-chat-completions-server.git
cd open-amazon-chat-completions-server
uv pip install -e .

# Configure environment
amazon-chat config set

# Start server
amazon-chat serve --host 0.0.0.0 --port 8000
```

### Basic Usage

```bash
# Test the unified endpoint
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "Hello!"}],
    "stream": false
  }'
```

### File Query Example

```bash
# Upload a file
curl -X POST http://localhost:8000/v1/files \
  -H "Authorization: Bearer your-api-key" \
  -F "file=@data.csv" \
  -F "purpose=assistants"

# Use file in chat completion
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "Analyze this data"}],
    "file_ids": ["file-abc123def456"]
  }'
```

---

## 🔄 Unified Endpoint

### Single Endpoint for Everything

The `/v1/chat/completions` endpoint is the **only endpoint you need**. It:

1. **Auto-detects** your input format (OpenAI, Bedrock Claude, Bedrock Titan)
2. **Routes** to the appropriate provider based on model ID
3. **Converts** between formats as needed
4. **Streams** responses in real-time when requested
5. **Returns** responses in your preferred format

### Format Combinations

All format combinations are supported through the unified endpoint:

| Input Format | Output Format | Use Case | Streaming |
|-------------|---------------|----------|-----------|
| OpenAI | OpenAI | Standard OpenAI usage | ✅ |
| OpenAI | Bedrock Claude | OpenAI clients → Bedrock response | ✅ |
| OpenAI | Bedrock Titan | OpenAI clients → Titan response | ✅ |
| Bedrock Claude | OpenAI | Bedrock clients → OpenAI response | ✅ |
| Bedrock Claude | Bedrock Claude | Claude format preserved | ✅ |
| Bedrock Titan | OpenAI | Titan clients → OpenAI response | ✅ |
| Bedrock Titan | Bedrock Titan | Titan format preserved | ✅ |

---

## 📚 Documentation

### Core Documentation

- **[Getting Started](getting-started)** - Installation, setup, and first steps
- **[API Reference](api-reference)** - Complete API documentation
- __[Files API](files_api)__ - File upload, processing, and query system
- **[CLI Reference](cli-reference)** - Command-line interface guide
- **[Architecture](guides/architecture)** - System design and architecture

### Guides

- **[Usage Guide](guides/usage)** - Programming examples and use cases
- **[AWS Authentication](guides/aws-authentication)** - AWS credential configuration
- **[Core Components](guides/core-components)** - Detailed component documentation
- **[Testing](testing)** - Testing strategies and comprehensive test guide
- **[Real API Testing](real-api-testing)** - Real API integration test documentation

### Development

- **[Development Guide](development)** - Extending and customizing the server
- **[Packaging Guide](guides/packaging)** - Building and distributing the package

---

## 🎯 Key Features

### Unified Interface

- **Single Endpoint**: `/v1/chat/completions` handles everything
- **Auto-Detection**: Intelligent format detection
- **Model-Based Routing**: Automatic provider selection
- **Format Conversion**: Seamless translation between formats

### File Query System

- **File Upload**: Upload documents to S3 storage with OpenAI-compatible API
- **Smart Processing**: Automatic content extraction from CSV, JSON, HTML, XML, Markdown, and text files
- __Chat Integration__: Use `file_ids` parameter to include file content as context in conversations
- **File Management**: Complete CRUD operations for uploaded files

### Enterprise Ready

- **Authentication**: Secure API key-based authentication
- **Streaming**: Real-time response streaming
- **Error Handling**: Comprehensive error management
- **Monitoring**: Request/response logging and health checks

### Developer Friendly

- **CLI Tools**: Interactive chat, configuration, and server management
- **OpenAI Compatible**: Drop-in replacement for OpenAI Chat Completions API
- **Extensible**: Easy to add new providers and formats
- **Well Tested**: Comprehensive test coverage

---

## 🔗 Quick Links

- **[GitHub Repository](https://github.com/teabranch/open-amazon-chat-completions-server)**
- **[Issues & Support](https://github.com/teabranch/open-amazon-chat-completions-server/issues)**
- **[OpenAI API Reference](https://platform.openai.com/docs/api-reference/chat)**
- **[AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)**

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/teabranch/open-amazon-chat-completions-server/blob/main/LICENSE) file for details.