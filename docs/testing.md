# Testing

This document outlines the implemented testing strategy for the Amazon Chat Completions Server.

## 1. Test Structure

The tests are organized in the `tests/` directory, mirroring the structure of the `src/` directory:

```
tests/
├── __init__.py
├── test_auth.py           # Authentication tests
├── test_chat.py          # Chat completion endpoint tests
├── test_bedrock_chat.py  # Bedrock-specific chat tests
├── test_models.py        # Model listing tests
├── test_main.py          # Main application tests
├── core/
│   ├── __init__.py
│   └── test_models.py    # Core model validation tests
├── adapters/
│   ├── __init__.py
│   ├── test_openai_adapter.py
│   └── bedrock/
│       ├── __init__.py
│       └── test_claude_strategy.py
├── services/
│   └── __init__.py
├── cli/
│   ├── __init__.py
│   └── test_commands.py  # CLI command tests
└── utils/
    └── __init__.py
```

## 2. Running Tests

To run all tests:

```bash
uv run pytest
```

To run specific test files or patterns:

```bash
# Run specific test file
pytest tests/core/test_models.py

# Run tests matching a pattern
pytest -k "test_chat"

# Run tests with coverage report
pytest --cov=src/amazon_chat_completions_server
```

## 3. Test Coverage

### Core Tests (`tests/core/test_models.py`)
- Message model validation
- ChatCompletionRequest validation
- ChatCompletionResponse structure
- ChatCompletionChunk format
- Tool calls format
- Usage statistics

### Adapter Tests
1. **OpenAI Adapter (`tests/adapters/test_openai_adapter.py`)**
   - Request conversion
   - Response parsing
   - Streaming functionality
   - Error handling
   - Tool calls

2. **Claude Strategy (`tests/adapters/bedrock/test_claude_strategy.py`)**
   - Request payload preparation
   - Response parsing
   - Stream chunk handling
   - System prompt extraction
   - Tool calls support

### CLI Tests (`tests/cli/test_commands.py`)
- Configuration management
  - Setting configuration values
  - Showing configuration
  - Masking sensitive values
- Chat command
  - Model selection
  - Message exchange
  - Error handling
- Models command
  - Listing available models
  - Error handling
- Serve command
  - Server startup
  - Configuration loading

### API Tests
1. **Authentication (`test_auth.py`)**
   - API key validation
   - Invalid key handling
   - Missing key handling

2. **Chat Endpoints (`test_chat.py`)**
   - REST endpoint functionality
   - WebSocket streaming
   - Request validation
   - Error responses
   - Rate limiting

3. **Model Listing (`test_models.py`)**
   - Available models retrieval
   - Response format
   - Error handling

## 4. Mocking Strategy

The tests use `pytest-mock` for mocking external dependencies:

1. **API Clients**
   - OpenAI API calls
   - AWS Bedrock API calls
   - HTTP requests in CLI tests

2. **Configuration**
   - Environment variables
   - .env file loading
   - AWS credentials

3. **File System**
   - Temporary file creation
   - Configuration file handling

## 5. Test Data

Test fixtures provide common test data:

1. **Message Fixtures**
   - System messages
   - User messages
   - Assistant messages
   - Tool calls

2. **Request/Response Fixtures**
   - Chat completion requests
   - API responses
   - Streaming chunks

3. **Configuration Fixtures**
   - Mock .env files
   - API keys
   - AWS credentials

## 6. Error Testing

Comprehensive error testing is implemented for:

1. **API Errors**
   - 400 Bad Request
   - 401 Unauthorized
   - 404 Not Found
   - 429 Rate Limit
   - 500 Internal Server Error

2. **LLM Provider Errors**
   - Connection failures
   - Rate limiting
   - Invalid requests
   - Authentication failures

3. **WebSocket Errors**
   - Connection handling
   - Message validation
   - Stream interruption

## 7. Integration Testing

Integration tests verify the interaction between components:

1. **Service Integration**
   - Factory → Service → Adapter → API Client flow
   - Configuration loading and validation
   - Error propagation

2. **CLI Integration**
   - Command execution flow
   - Server interaction
   - Configuration management

3. **API Integration**
   - Request → Response flow
   - Authentication middleware
   - Error handling middleware

## 8. Running Tests in CI/CD

The test suite is designed to run in CI/CD environments:

```bash
# Install dependencies
uv pip install -e ".[dev]"

# Run tests with coverage
pytest --cov=src/amazon_chat_completions_server --cov-report=xml

# Run specific test groups
pytest tests/core/  # Run core tests
pytest tests/api/   # Run API tests
pytest tests/cli/   # Run CLI tests
```

## 9. Test Reports

Test results can be generated in various formats:

```bash
# Generate HTML coverage report
pytest --cov=src/amazon_chat_completions_server --cov-report=html

# Generate JUnit XML report
pytest --junitxml=test-results.xml

# Generate coverage badge
coverage-badge -o coverage.svg
``` 