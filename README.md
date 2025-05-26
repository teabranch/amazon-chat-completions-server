# Amazon Chat Completions Server (ACCS)

A **provider-agnostic, bidirectional** chat completions API server that seamlessly integrates with multiple LLM providers while maintaining format compatibility. The server supports both forward and reverse integration, allowing you to use any request format with any underlying model.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-passing-green.svg)](tests/)

## 🚀 Key Features

### ✨ **Bidirectional Format Conversion**

- 🔄 **Universal Compatibility**: Use Bedrock format with OpenAI models, or OpenAI format with Bedrock models
- 🎯 **Auto-Format Detection**: Automatically detects and routes requests based on format
- 🌐 **Universal Endpoints**: Single endpoint that handles any format combination
- 📡 **Real-time Streaming**: Streaming support for all format combinations
- 🛠️ **Complex Content**: Full support for images, tools, and multimodal content across formats

### 🏗️ **Core Capabilities**

- **Multiple LLM Providers**: OpenAI, AWS Bedrock (Claude, Titan)
- **Unified API**: Consistent interface across all providers
- **Streaming Support**: Real-time response streaming with format conversion
- **Tool Calling**: Function calling capabilities across providers
- **Multimodal Support**: Text and image processing
- **Robust Error Handling**: Comprehensive error management
- **Authentication**: Secure API key-based authentication
- **CLI Interface**: Interactive command-line interface
- **Logging & Monitoring**: Detailed request/response logging

## 📋 Table of Contents

- [Quick Start](#-quick-start)
- [Supported Format Combinations](#-supported-format-combinations)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage Examples](#-usage-examples)
- [API Endpoints](#-api-endpoints)
- [CLI Usage](#-cli-usage)
- [Supported Models](#-supported-models)
- [Architecture](#-architecture)
- [Testing](#-testing)
- [Development](#-development)
- [Deployment](#-deployment)
- [Documentation](#-documentation)
- [Contributing](#-contributing)

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/teabranch/amazon-chat-completions-server.git
cd amazon-chat-completions-server

# Install with uv (recommended)
uv pip install -e .

# Or with pip
pip install -e .
```

### Configuration

Create a `.env` file in the project root:

```bash
# Required environment variables
export OPENAI_API_KEY="your-openai-api-key"
export API_KEY="your-server-api-key"

# AWS Configuration (choose one method)
# Method 1: Static credentials
export AWS_ACCESS_KEY_ID="your-aws-access-key"
export AWS_SECRET_ACCESS_KEY="your-aws-secret-key"
export AWS_REGION="us-east-1"

# Method 2: AWS Profile
export AWS_PROFILE="your-aws-profile"
export AWS_REGION="us-east-1"

# Optional
export DEFAULT_OPENAI_MODEL="gpt-4o-mini"
export LOG_LEVEL="INFO"
```

### Start the Server

```bash
# Using CLI (recommended)
amazon-chat serve --host 0.0.0.0 --port 8000

# Or directly with uvicorn
uvicorn src.amazon_chat_completions_server.api.app:app --host 0.0.0.0 --port 8000
```

The server will start on `http://localhost:8000` with automatic API documentation at `/docs`.

## 🔄 Supported Format Combinations

| Input Format | Output Format | Use Case | Endpoint |
|-------------|---------------|----------|----------|
| OpenAI | OpenAI | Standard OpenAI usage | `/v1/chat/completions` |
| OpenAI | Bedrock | OpenAI clients → Bedrock response | `/v1/completions/universal?target_provider=bedrock` |
| Bedrock Claude | Bedrock | Bedrock clients → OpenAI models | `/bedrock/claude/invoke-model` |
| Bedrock Claude | OpenAI | Bedrock clients → OpenAI response | `/v1/completions/universal?target_provider=openai` |
| Bedrock Titan | Bedrock | Titan format → OpenAI models | `/bedrock/titan/invoke-model` |
| Auto-detect | Auto-detect | Universal compatibility | `/v1/completions/universal` |

## 📖 Usage Examples

### 1. Standard OpenAI Format

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [
      {"role": "user", "content": "Hello, how are you?"}
    ],
    "max_tokens": 100
  }'
```

### 2. Bedrock Claude Format → OpenAI Models

```bash
curl -X POST http://localhost:8000/bedrock/claude/invoke-model \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": 1000,
    "messages": [
      {"role": "user", "content": "Hello, how are you?"}
    ],
    "temperature": 0.7
  }' \
  --query-string "openai_model=gpt-4o-mini"
```

**Response** (Bedrock Claude format):

```json
{
  "id": "msg_123",
  "type": "message",
  "role": "assistant",
  "content": [
    {"type": "text", "text": "Hello! I'm doing well, thank you for asking."}
  ],
  "model": "gpt-4o-mini-2024-07-18",
  "stop_reason": "end_turn",
  "usage": {
    "input_tokens": 12,
    "output_tokens": 15
  }
}
```

### 3. Universal Auto-Detecting Endpoint

```bash
# The endpoint automatically detects the format and responds appropriately
curl -X POST http://localhost:8000/v1/completions/universal \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": 100,
    "messages": [
      {"role": "user", "content": "Hello"}
    ]
  }'
```

### 4. Streaming with Format Conversion

```bash
# Bedrock Claude streaming with OpenAI models
curl -X POST http://localhost:8000/bedrock/claude/invoke-model-stream \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": 1000,
    "messages": [
      {"role": "user", "content": "Tell me a story"}
    ]
  }' \
  --query-string "openai_model=gpt-4o-mini"
```

### 5. Multimodal Content Support

```bash
# Image analysis with format conversion
curl -X POST http://localhost:8000/bedrock/claude/invoke-model \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": 1000,
    "messages": [
      {
        "role": "user",
        "content": [
          {"type": "text", "text": "What do you see in this image?"},
          {
            "type": "image",
            "source": {
              "type": "base64",
              "media_type": "image/jpeg",
              "data": "base64encodeddata"
            }
          }
        ]
      }
    ]
  }'
```

### 6. Tool Calls with Format Conversion

```bash
curl -X POST http://localhost:8000/bedrock/claude/invoke-model \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": 1000,
    "messages": [
      {"role": "user", "content": "What'\''s the weather in London?"}
    ],
    "tools": [
      {
        "name": "get_weather",
        "description": "Get weather information",
        "input_schema": {
          "type": "object",
          "properties": {
            "location": {"type": "string"}
          },
          "required": ["location"]
        }
      }
    ],
    "tool_choice": {"type": "auto"}
  }'
```

## 🛠️ API Endpoints

### Standard Endpoints

- `POST /v1/chat/completions` - OpenAI-compatible chat completions
- `GET /v1/models` - List available models
- `GET /health` - Health check

### Reverse Integration Endpoints

- `POST /bedrock/claude/invoke-model` - Bedrock Claude format → OpenAI models
- `POST /bedrock/claude/invoke-model-stream` - Bedrock Claude streaming
- `POST /bedrock/titan/invoke-model` - Bedrock Titan format → OpenAI models
- `POST /bedrock/titan/invoke-model-stream` - Bedrock Titan streaming

### Universal Endpoints

- `POST /v1/completions/universal` - Auto-detecting format endpoint
- `POST /v1/completions/universal/stream` - Auto-detecting streaming
- `GET /v1/completions/universal/health` - Universal endpoint health check

### Documentation

- `GET /docs` - Interactive API documentation (Swagger UI)
- `GET /redoc` - Alternative API documentation (ReDoc)
- `GET /openapi.json` - OpenAPI schema

## 💻 CLI Usage

The CLI provides an interactive interface for chat completions and server management.

### Interactive Chat

```bash
# Start an interactive chat session
amazon-chat chat --model gpt-4o-mini

# Chat with specific server
amazon-chat chat --model gpt-4o-mini --server-url http://localhost:8000 --api-key your-key
```

### Configuration Management

```bash
# Set up configuration interactively
amazon-chat config set

# Show current configuration (sensitive values masked)
amazon-chat config show
```

### Server Management

```bash
# Start the server
amazon-chat serve --host 0.0.0.0 --port 8000 --reload

# List available models
amazon-chat models
```

### CLI Help

```bash
# General help
amazon-chat --help

# Command-specific help
amazon-chat chat --help
amazon-chat serve --help
```

## 🎯 Supported Models

### OpenAI Models

- `gpt-4o` - Latest GPT-4 Omni model
- `gpt-4o-mini` - Efficient GPT-4 Omni model (default)
- `gpt-3.5-turbo` - Fast and efficient model
- `gpt-4-turbo` - Advanced GPT-4 model

### AWS Bedrock Models

- `anthropic.claude-3-haiku-20240307-v1:0` - Fast Claude model
- `anthropic.claude-3-sonnet-20240229-v1:0` - Balanced Claude model
- `anthropic.claude-3-opus-20240229-v1:0` - Most capable Claude model
- `amazon.titan-text-express-v1` - Amazon Titan model

### Model Selection

- __Bedrock endpoints__: Use `?openai_model=model-name` query parameter
- __Universal endpoint__: Use `?model_override=model-name` query parameter
- **Default**: `gpt-4o-mini` if not specified

## 🏗️ Architecture

### Core Components

The system is built with a layered architecture promoting modularity and extensibility:

```ini
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

### Key Architectural Patterns

1. **Adapter Pattern**: Convert between different API formats
2. **Strategy Pattern**: Handle different model families within providers
3. **Factory Pattern**: Create appropriate services for any format combination
4. **Observer Pattern**: Real-time streaming with format conversion

### Core Modules

- **Service Layer**: `AbstractLLMService`, `ConcreteLLMService`
- **Adapter Layer**: `BaseLLMAdapter`, `OpenAIAdapter`, `BedrockAdapter`
- **Strategy Layer**: `ClaudeStrategy`, `TitanStrategy`
- **API Layer**: FastAPI routes with authentication and validation
- **CLI Layer**: Click-based command interface

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test categories
pytest tests/core/ -v
pytest tests/adapters/ -v
pytest tests/api/ -v
```

### Test Coverage

- ✅ **51 source files** with comprehensive test coverage
- ✅ **24 test files** covering all functionality
- ✅ **Core models** validation and conversion
- ✅ **Format detection** with auto-detection logic
- ✅ **Reverse adapters** with bidirectional conversion
- ✅ **API endpoints** with authentication and streaming
- ✅ **CLI commands** with configuration management
- ✅ **Error handling** and edge cases

### Test Categories

- **Unit Tests**: Core functionality, models, adapters
- **Integration Tests**: Service interactions, API endpoints
- **CLI Tests**: Command execution, configuration management
- **Error Tests**: Exception handling, validation

## 🔧 Development

### Development Setup

```bash
# Clone and setup
git clone https://github.com/teabranch/amazon-chat-completions-server.git
cd amazon-chat-completions-server

# Create virtual environment with uv
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
uv pip install -e ".[dev]"

# Run tests
pytest

# Start development server with auto-reload
amazon-chat serve --reload
```

### Project Structure

```ini
src/amazon_chat_completions_server/
├── api/                    # FastAPI application
│   ├── routes/            # API route handlers
│   ├── middleware/        # Authentication, logging
│   └── schemas/           # Request/response models
├── cli/                   # Command-line interface
├── core/                  # Core models and exceptions
├── adapters/              # Provider adapters
│   ├── bedrock/          # Bedrock-specific strategies
│   └── reverse/          # Reverse integration adapters
├── services/              # Service layer
├── utils/                 # Utilities and configuration
└── version/               # Version information
```

### Adding New Providers

1. **Create Adapter**: Implement `BaseLLMAdapter`
2. **Update Factory**: Add provider to `LLMServiceFactory`
3. **Add Routes**: Create API endpoints if needed
4. **Write Tests**: Comprehensive test coverage
5. **Update Documentation**: Document new capabilities

### Code Quality

```bash
# Run linting (if configured)
ruff check src/

# Format code (if configured)
ruff format src/

# Type checking (if configured)
mypy src/
```

## 🚀 Deployment

### Docker Deployment

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY . .
RUN pip install -e .

EXPOSE 8000
CMD ["amazon-chat", "serve", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
# Build and run
docker build -t amazon-chat-server .
docker run -p 8000:8000 --env-file .env amazon-chat-server
```

### Environment Variables

```bash
# Required
OPENAI_API_KEY=your-openai-api-key
API_KEY=your-server-api-key

# AWS (choose one method)
AWS_ACCESS_KEY_ID=your-key-id
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=us-east-1

# Or use AWS profile
AWS_PROFILE=your-profile
AWS_REGION=us-east-1

# Optional
DEFAULT_OPENAI_MODEL=gpt-4o-mini
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=8000
```

### Production Considerations

- **Load Balancing**: Use multiple instances behind a load balancer
- **Monitoring**: Implement health checks and metrics collection
- **Security**: Use HTTPS, secure API keys, rate limiting
- **Logging**: Centralized logging with structured format
- **Caching**: Consider response caching for identical requests

## 📊 Performance

### Benchmarks

- **Format Detection**: < 1ms per request
- **Format Conversion**: < 5ms overhead
- **Streaming Latency**: Minimal additional latency
- **Memory Usage**: Efficient Pydantic model serialization

### Optimization Features

- Service instance caching with `@lru_cache`
- Adapter reuse for same model configurations
- Optimized format detection algorithms
- Streaming reduces memory footprint

## 🔒 Security

### Authentication

- API key-based authentication for all endpoints
- Secure header-based authentication (`X-API-Key`)
- Consistent authentication across all formats

### Input Validation

- Pydantic model validation for all request formats
- Request size limits and content type validation
- Comprehensive input sanitization

### Error Handling

- No sensitive information in error responses
- Consistent error format across all endpoints
- Proper HTTP status codes

## 📈 Monitoring

### Logging

- Structured logging for all operations
- Request/response tracking with correlation IDs
- Error logging with full context
- Performance metrics and timing

### Health Checks

- Multiple health check endpoints
- Service capability reporting
- Supported format enumeration
- Real-time status monitoring

## �� Documentation

### 📖 Complete Documentation Hub

For comprehensive documentation, visit the **[Documentation Hub](docs/README.md)** which provides organized access to all guides, references, and tutorials.

### Available Documentation

- **[API Reference](docs/api-reference.md)** - Complete API endpoint documentation
- **[CLI Reference](docs/cli-reference.md)** - Complete CLI command reference
- **[Architecture Guide](docs/architecture.md)** - System design and components
- **[Core Components](docs/core-components.md)** - Detailed component documentation
- **[Development Guide](docs/extending.md)** - Adding new providers and models
- **[Testing Guide](docs/testing.md)** - Running tests and test coverage

### Interactive Documentation

When the server is running, visit:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI Schema**: `http://localhost:8000/openapi.json`

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/amazing-feature`)
3. **Make your changes** with tests
4. **Run the test suite** (`pytest`)
5. **Commit your changes** (`git commit -m 'Add amazing feature'`)
6. **Push to the branch** (`git push origin feature/amazing-feature`)
7. **Open a Pull Request**

### Development Guidelines

- Write comprehensive tests for new features
- Follow existing code style and patterns
- Update documentation for new capabilities
- Ensure backward compatibility
- Add type hints for new code

### Reporting Issues

Please use the [GitHub Issues](https://github.com/teabranch/amazon-chat-completions-server/issues) page to report bugs or request features.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **OpenAI** for their excellent API design and comprehensive documentation
- **AWS** for Bedrock and comprehensive model support
- **FastAPI** for the excellent web framework
- **Click** for the intuitive CLI framework
- **The open-source community** for inspiration and best practices

## 🆕 What's New

### ✨ Latest Features

- **Bidirectional Format Support**: Use any format with any model
- **Auto-Format Detection**: Intelligent request format detection
- **Universal Endpoints**: Single endpoint for all format combinations
- **Streaming Conversion**: Real-time format conversion for streaming
- **CLI Interface**: Complete command-line interface for all operations
- **Comprehensive Testing**: 24 test files with full coverage

### 🚀 Enhanced Capabilities

- **Complex Content Support**: Images, tools, multimodal content across formats
- **Performance Optimizations**: Caching, efficient conversion algorithms
- **Developer Experience**: Rich error messages, extensive documentation
- **Health Monitoring**: Enhanced health checks and monitoring

---

**Ready to experience truly provider-agnostic LLM integration? Get started today!** 🚀

For detailed documentation, visit the [docs](docs/) directory or check out the interactive API documentation at `/docs` when running the server.
