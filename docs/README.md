# Amazon Chat Completions Server - Documentation Hub

Welcome to the comprehensive documentation for the Amazon Chat Completions Server. This documentation provides everything you need to understand, deploy, and extend the provider-agnostic, bidirectional chat completions API server.

## 📚 Documentation Overview

### 🚀 Quick Navigation

| Section | Description | File |
|---------|-------------|------|
| **[Getting Started](#-getting-started)** | Installation, configuration, and first steps | [Main README](../README.md) |
| **[API Reference](#-api-reference)** | Complete REST API documentation | [api-reference.md](api-reference.md) |
| **[CLI Reference](#-cli-reference)** | Command-line interface guide | [cli-reference.md](cli-reference.md) |
| **[Architecture](#-architecture)** | System design and components | [architecture.md](architecture.md) |
| **[Core Components](#-core-components)** | Detailed component documentation | [core-components.md](core-components.md) |
| **[Development](#-development)** | Extending and contributing | [extending.md](extending.md) |
| **[Testing](#-testing)** | Testing guide and coverage | [testing.md](testing.md) |

## 🚀 Getting Started

### Quick Start
For immediate setup and basic usage, see the [Quick Start section](../README.md#-quick-start) in the main README.

### Key Concepts
- **Bidirectional Format Support**: Use any request format with any model
- **Auto-Format Detection**: Automatic request format detection and routing
- **Universal Endpoints**: Single endpoints handling multiple format combinations
- **Provider Agnostic**: Consistent interface across OpenAI and AWS Bedrock

### Installation & Configuration
Complete installation and configuration instructions are available in the [main README](../README.md#-installation).

## 📖 API Reference

### Endpoint Categories

#### Standard Endpoints
- `POST /v1/chat/completions` - OpenAI-compatible chat completions
- `GET /v1/models` - List available models
- `GET /health` - Health check

#### Reverse Integration Endpoints
- `POST /bedrock/claude/invoke-model` - Bedrock Claude format → OpenAI models
- `POST /bedrock/titan/invoke-model` - Bedrock Titan format → OpenAI models
- Streaming variants available for all endpoints

#### Universal Endpoints
- `POST /v1/completions/universal` - Auto-detecting format endpoint
- `POST /v1/completions/universal/stream` - Auto-detecting streaming

### Format Combinations

| Input Format | Output Format | Use Case |
|-------------|---------------|----------|
| OpenAI | OpenAI | Standard OpenAI usage |
| OpenAI | Bedrock | OpenAI clients → Bedrock response |
| Bedrock Claude | Bedrock | Bedrock clients → OpenAI models |
| Bedrock Claude | OpenAI | Bedrock clients → OpenAI response |
| Auto-detect | Auto-detect | Universal compatibility |

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

### System Design

The system uses a layered architecture with these key patterns:

1. **Adapter Pattern**: Convert between different API formats
2. **Strategy Pattern**: Handle different model families within providers
3. **Factory Pattern**: Create appropriate services for any format combination
4. **Observer Pattern**: Real-time streaming with format conversion

### Core Layers

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Any Format    │───▶│  Auto-Detection  │───▶│  Route to       │
│   Request       │    │  & Conversion    │    │  Appropriate    │
└─────────────────┘    └──────────────────┘    │  Provider       │
                                               └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Requested     │◀───│  Response        │◀───│  Provider       │
│   Format        │    │  Conversion      │    │  Response       │
│   Response      │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

**Detailed architecture documentation**: [architecture.md](architecture.md)

## 🔧 Core Components

### Service Layer
- `AbstractLLMService` - Unified interface for all LLM providers
- `ConcreteLLMService` - Generic implementation with adapter delegation
- `LLMServiceFactory` - Service creation and management

### Adapter Layer
- `BaseLLMAdapter` - Abstract base for all adapters
- `OpenAIAdapter` - OpenAI API integration
- `BedrockAdapter` - AWS Bedrock integration with strategy pattern
- `BedrockToOpenAIAdapter` - Reverse integration adapter

### Strategy Layer
- `ClaudeStrategy` - Anthropic Claude model handling
- `TitanStrategy` - Amazon Titan model handling
- Extensible for additional Bedrock model families

**Detailed component documentation**: [core-components.md](core-components.md)

## 🔧 Development

### Adding New Providers

1. **Create Adapter**: Implement `BaseLLMAdapter`
2. **Update Factory**: Add provider to `LLMServiceFactory`
3. **Add Routes**: Create API endpoints if needed
4. **Write Tests**: Comprehensive test coverage
5. **Update Documentation**: Document new capabilities

### Adding New Bedrock Models

1. **Create Strategy**: Implement `BedrockAdapterStrategy`
2. **Update BedrockAdapter**: Add strategy selection logic
3. **Update Model Mapping**: Add to `BEDROCK_MODEL_ID_MAP`
4. **Add Tests**: Strategy-specific test coverage

### Project Structure

```
src/amazon_chat_completions_server/
├── api/                    # FastAPI application
├── cli/                   # Command-line interface
├── core/                  # Core models and exceptions
├── adapters/              # Provider adapters
├── services/              # Service layer
└── utils/                 # Utilities and configuration
```

**Complete development guide**: [extending.md](extending.md)

## 🧪 Testing

### Test Coverage
- ✅ **51 source files** with comprehensive test coverage
- ✅ **24 test files** covering all functionality
- ✅ **Core models** validation and conversion
- ✅ **Format detection** with auto-detection logic
- ✅ **Reverse adapters** with bidirectional conversion
- ✅ **API endpoints** with authentication and streaming

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific categories
pytest tests/core/ -v
pytest tests/adapters/ -v
pytest tests/api/ -v
```

**Complete testing guide**: [testing.md](testing.md)

## 🚀 Deployment & Production

### Docker Deployment

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install -e .
EXPOSE 8000
CMD ["amazon-chat", "serve", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Configuration

```bash
# Required
OPENAI_API_KEY=your-openai-api-key
API_KEY=your-server-api-key

# AWS Configuration
AWS_ACCESS_KEY_ID=your-key-id
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=us-east-1

# Optional
DEFAULT_OPENAI_MODEL=gpt-4o-mini
LOG_LEVEL=INFO
```

### Production Considerations
- Load balancing with multiple instances
- Health checks and monitoring
- HTTPS and security configuration
- Centralized logging
- Response caching

**Complete deployment information**: [Main README - Deployment](../README.md#-deployment)

## 📊 Features & Capabilities

### Supported Models

#### OpenAI Models
- `gpt-4o` - Latest GPT-4 Omni model
- `gpt-4o-mini` - Efficient GPT-4 Omni model (default)
- `gpt-3.5-turbo` - Fast and efficient model
- `gpt-4-turbo` - Advanced GPT-4 model

#### AWS Bedrock Models
- `anthropic.claude-3-haiku-20240307-v1:0` - Fast Claude model
- `anthropic.claude-3-sonnet-20240229-v1:0` - Balanced Claude model
- `anthropic.claude-3-opus-20240229-v1:0` - Most capable Claude model
- `amazon.titan-text-express-v1` - Amazon Titan model

### Advanced Features
- **Multimodal Content**: Text and image processing
- **Tool Calling**: Function calling across providers
- **Streaming Support**: Real-time response streaming
- **Format Conversion**: Seamless format translation
- **Auto-Detection**: Intelligent request format detection

## 🔍 Interactive Documentation

When the server is running, access interactive documentation:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI Schema**: `http://localhost:8000/openapi.json`

## 📞 Support & Contributing

### Getting Help
- **GitHub Issues**: [Report bugs and request features](https://github.com/teabranch/amazon-chat-completions-server/issues)
- **Documentation**: This comprehensive guide and inline API docs
- **Examples**: Working code examples in the main README

### Contributing
We welcome contributions! See the [Contributing section](../README.md#-contributing) in the main README for guidelines.

### Development Guidelines
- Write comprehensive tests for new features
- Follow existing code style and patterns
- Update documentation for new capabilities
- Ensure backward compatibility

---

## 📋 Documentation Status

| Section | Status | Last Updated |
|---------|--------|--------------|
| Quick Start | ✅ Complete | Current |
| API Reference | ✅ Complete | Current |
| CLI Reference | ✅ Complete | Current |
| Architecture | ✅ Complete | Current |
| Core Components | ✅ Complete | Current |
| Development Guide | ✅ Complete | Current |
| Testing Guide | ✅ Complete | Current |
| Deployment Guide | ✅ Complete | Current |

---

**Ready to dive deeper? Choose a section above or start with the [Quick Start Guide](../README.md#-quick-start)!** 🚀 