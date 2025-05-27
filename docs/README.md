# Amazon Chat Completions Server Documentation

Welcome to the comprehensive documentation for the Amazon Chat Completions Server - a unified, provider-agnostic chat completions API server.

## 📚 Documentation Overview

This documentation covers all aspects of the server, from basic usage to advanced development and deployment scenarios.

### Quick Navigation

- **[API Reference](api-reference.md)** - Complete API documentation for the unified endpoint
- **[CLI Reference](cli-reference.md)** - Command-line interface documentation
- **[Architecture](architecture.md)** - System design and unified architecture
- **[Usage Guide](usage.md)** - Programming examples and practical use cases
- **[Core Components](core-components.md)** - Detailed component documentation
- **[Testing Guide](testing.md)** - Testing strategies and coverage
- **[Development Guide](extending.md)** - Extending and customizing the server

## 🚀 Quick Start

### Installation & Setup

```bash
# Clone and install
git clone https://github.com/teabranch/amazon-chat-completions-server.git
cd amazon-chat-completions-server
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

**Complete API documentation**: [api-reference.md](api-reference.md)

## 💻 CLI Reference

### Core Commands

```bash
# Interactive chat
amazon-chat chat --model gpt-4o-mini

# Server management
amazon-chat serve --host 0.0.0.0 --port 8000

# Configuration
amazon-chat config set
amazon-chat config show

# Model listing
amazon-chat models
```

### Configuration Management

The CLI provides interactive configuration setup and management with secure handling of API keys and credentials.

**Complete CLI documentation**: [cli-reference.md](cli-reference.md)

## 🏗️ Architecture

### Unified Design

The system uses a layered architecture with intelligent format detection and model-based routing:

```mermaid
graph LR
    A[Any Format Request] --> B[Format Detection]
    B --> C[Model-Based Routing]
    C --> D[Provider API Call]
    D --> E[Format Conversion]
    E --> F[Unified Response]
    
    style A fill:#e1f5fe
    style F fill:#e8f5e8
```

### Core Principles

1. **Single Responsibility**: Each component has a clear, focused purpose
2. **Auto-Detection**: Intelligent format detection eliminates complexity
3. **Model-Based Routing**: Automatic provider selection based on model ID patterns
4. **Format Conversion**: Seamless translation between all supported formats
5. **Streaming Support**: Real-time response streaming with format preservation

**Detailed architecture documentation**: [architecture.md](architecture.md)

## 🔧 Core Components

### Service Layer

- `AbstractLLMService` - Unified interface for all LLM providers
- `LLMServiceFactory` - Model-based service creation and routing
- `OpenAIService` / `BedrockService` - Provider-specific implementations

### Format Detection & Conversion

- `RequestFormatDetector` - Automatic input format detection
- `BedrockToOpenAIAdapter` - Bidirectional format conversion
- Strategy pattern for different model families

### API Layer

- Unified `/v1/chat/completions` endpoint
- Authentication and security middleware
- Streaming response handling

**Detailed component documentation**: [core-components.md](core-components.md)

## 🔧 Development

### Adding New Providers

1. **Create Service**: Implement `AbstractLLMService`
2. **Update Factory**: Add model ID patterns to `LLMServiceFactory`
3. **Add Adapters**: Create format conversion adapters if needed
4. **Write Tests**: Comprehensive test coverage
5. **Update Documentation**: Document new capabilities

### Project Structure

```ini
src/amazon_chat_completions_server/
├── api/                    # FastAPI application
├── cli/                   # Command-line interface
├── core/                  # Core models and exceptions
├── adapters/              # Format conversion adapters
├── services/              # Service layer
└── utils/                 # Utilities and configuration
```

**Complete development guide**: [extending.md](extending.md)

## 🧪 Testing

### Test Coverage

- ✅ **113 tests passing** with comprehensive coverage
- ✅ **Format detection** with auto-detection logic
- ✅ **Model-based routing** logic
- ✅ **Format conversion** in all directions
- ✅ **Streaming** functionality
- ✅ **Error handling** and edge cases
- ✅ **Authentication** and security
- ✅ **CLI commands** and configuration

### Running Tests

```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=src --cov-report=html

# Run specific test categories
python -m pytest tests/api/  # API tests
python -m pytest tests/cli/  # CLI tests
python -m pytest tests/core/ # Core functionality tests
```

**Complete testing guide**: [testing.md](testing.md)

## 📚 Additional Resources

### Programming Guide

- **[Usage Guide](usage.md)** - Practical Python examples and use cases
- Code examples for all supported formats
- Advanced features like tool calling and multimodal content
- Best practices and error handling

### Deployment & Operations

- __[Server & CLI Guide](server_and_cli.md)__ - Server management and operations
- Docker deployment examples
- Production considerations
- Monitoring and logging

### Package Management

- __[Packaging Guide](packaging_guide.md)__ - Building and distributing the package
- Creating wheels and distributions
- Version management

## 🎯 Key Features

### Unified Interface

- **Single Endpoint**: `/v1/chat/completions` handles everything
- **Auto-Detection**: Intelligent format detection
- **Model-Based Routing**: Automatic provider selection
- **Format Conversion**: Seamless translation between formats

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

## 🔗 External Links

- **GitHub Repository**: [amazon-chat-completions-server](https://github.com/teabranch/amazon-chat-completions-server)
- **Issues & Support**: [GitHub Issues](https://github.com/teabranch/amazon-chat-completions-server/issues)
- **OpenAI API Reference**: [Chat Completions](https://platform.openai.com/docs/api-reference/chat)
- **AWS Bedrock Documentation**: [Bedrock User Guide](https://docs.aws.amazon.com/bedrock/)

---

This documentation provides comprehensive coverage of the Amazon Chat Completions Server. For interactive API testing, visit `/docs` when the server is running.