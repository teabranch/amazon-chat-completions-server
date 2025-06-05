---
layout: default
title: Testing
parent: Guides
nav_order: 5
description: "Testing strategies and coverage for Amazon Chat Completions Server"
---

# Testing Guide
{: .no_toc }

Comprehensive testing strategies and coverage for the Amazon Chat Completions Server.
{: .fs-6 .fw-300 }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Testing Philosophy

The Amazon Chat Completions Server follows a comprehensive testing strategy that ensures reliability, maintainability, and confidence in deployments. Our testing approach includes:

- **Unit Tests** - Test individual components in isolation
- **Integration Tests** - Test component interactions
- **End-to-End Tests** - Test complete user workflows
- **Performance Tests** - Validate system performance under load
- **Contract Tests** - Ensure API compatibility

## Test Structure

```
tests/
├── unit/                    # Unit tests
│   ├── test_services/
│   ├── test_adapters/
│   ├── test_strategies/
│   ├── test_models/
│   └── test_utils/
├── integration/             # Integration tests
│   ├── test_api/
│   ├── test_cli/
│   └── test_providers/
├── e2e/                     # End-to-end tests
├── performance/             # Performance tests
├── fixtures/                # Test data and fixtures
├── mocks/                   # Mock implementations
└── conftest.py             # Pytest configuration
```

## Unit Testing

### Service Layer Tests

**Testing LLM Services:**
```python
# tests/unit/test_services/test_openai_service.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.open_amazon_chat_completions_server.services.openai_service import OpenAIService
from src.open_amazon_chat_completions_server.core.models import Message, ChatCompletionResponse

@pytest.fixture
def openai_service():
    with patch('src.open_amazon_chat_completions_server.services.openai_service.AsyncOpenAI') as mock_client:
        service = OpenAIService(api_key="test-key")
        service.client = mock_client.return_value
        return service

@pytest.mark.asyncio
async def test_chat_completion_success(openai_service):
    """Test successful chat completion"""
    # Arrange
    mock_response = MagicMock()
    mock_response.id = "chatcmpl-123"
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Hello! How can I help you?"
    mock_response.choices[0].finish_reason = "stop"
    mock_response.created = 1677652288
    mock_response.model = "gpt-4o-mini"
    mock_response.usage.prompt_tokens = 10
    mock_response.usage.completion_tokens = 15
    mock_response.usage.total_tokens = 25
    
    openai_service.client.chat.completions.create = AsyncMock(return_value=mock_response)
    
    messages = [Message(role="user", content="Hello")]
    
    # Act
    response = await openai_service.chat_completion(messages, "gpt-4o-mini")
    
    # Assert
    assert isinstance(response, ChatCompletionResponse)
    assert response.id == "chatcmpl-123"
    assert response.choices[0].message.content == "Hello! How can I help you?"
    assert response.usage.total_tokens == 25

@pytest.mark.asyncio
async def test_chat_completion_with_tools(openai_service):
    """Test chat completion with tool calls"""
    # Setup mock response with tool calls
    mock_response = MagicMock()
    mock_response.choices[0].message.tool_calls = [MagicMock()]
    mock_response.choices[0].message.tool_calls[0].id = "call_123"
    mock_response.choices[0].message.tool_calls[0].function.name = "get_weather"
    mock_response.choices[0].message.tool_calls[0].function.arguments = '{"location": "London"}'
    
    openai_service.client.chat.completions.create = AsyncMock(return_value=mock_response)
    
    messages = [Message(role="user", content="What's the weather in London?")]
    tools = [{"type": "function", "function": {"name": "get_weather"}}]
    
    response = await openai_service.chat_completion(messages, "gpt-4o-mini", tools=tools)
    
    assert response.choices[0].message.tool_calls is not None
    assert len(response.choices[0].message.tool_calls) == 1
```

### Adapter Layer Tests

**Testing Format Conversion:**
```python
# tests/unit/test_adapters/test_bedrock_adapter.py
import pytest
from src.open_amazon_chat_completions_server.adapters.bedrock_adapter import BedrockAdapter
from src.open_amazon_chat_completions_server.strategies.claude_strategy import ClaudeStrategy
from src.open_amazon_chat_completions_server.core.models import ChatCompletionRequest, Message

@pytest.fixture
def bedrock_adapter():
    return BedrockAdapter(model_id="anthropic.claude-3-haiku-20240307-v1:0")

def test_claude_strategy_selection(bedrock_adapter):
    """Test that Claude strategy is selected for Claude models"""
    assert isinstance(bedrock_adapter.strategy, ClaudeStrategy)

def test_convert_to_bedrock_request(bedrock_adapter):
    """Test conversion from standard format to Bedrock format"""
    request = ChatCompletionRequest(
        model="anthropic.claude-3-haiku-20240307-v1:0",
        messages=[
            Message(role="system", content="You are a helpful assistant."),
            Message(role="user", content="Hello!")
        ],
        max_tokens=100,
        temperature=0.7
    )
    
    bedrock_request = bedrock_adapter.strategy.convert_to_bedrock_request(request)
    
    assert bedrock_request["anthropic_version"] == "bedrock-2023-05-31"
    assert bedrock_request["max_tokens"] == 100
    assert bedrock_request["temperature"] == 0.7
    assert bedrock_request["system"] == "You are a helpful assistant."
    assert len(bedrock_request["messages"]) == 1
    assert bedrock_request["messages"][0]["role"] == "user"
```

### Strategy Layer Tests

**Testing Bedrock Strategies:**
```python
# tests/unit/test_strategies/test_claude_strategy.py
import pytest
from src.open_amazon_chat_completions_server.strategies.claude_strategy import ClaudeStrategy
from src.open_amazon_chat_completions_server.core.models import ChatCompletionRequest, Message

@pytest.fixture
def claude_strategy():
    return ClaudeStrategy()

def test_convert_multimodal_content(claude_strategy):
    """Test conversion of multimodal content"""
    request = ChatCompletionRequest(
        model="anthropic.claude-3-haiku-20240307-v1:0",
        messages=[
            Message(
                role="user",
                content=[
                    {"type": "text", "text": "What's in this image?"},
                    {"type": "image_url", "image_url": {"url": "https://example.com/image.jpg"}}
                ]
            )
        ]
    )
    
    bedrock_request = claude_strategy.convert_to_bedrock_request(request)
    
    assert len(bedrock_request["messages"][0]["content"]) == 2
    assert bedrock_request["messages"][0]["content"][0]["type"] == "text"
    assert bedrock_request["messages"][0]["content"][1]["type"] == "image"

def test_convert_tool_calls(claude_strategy):
    """Test conversion of tool calls"""
    bedrock_response = {
        "id": "msg_123",
        "content": [
            {"type": "text", "text": "I'll check the weather for you."},
            {
                "type": "tool_use",
                "id": "toolu_123",
                "name": "get_weather",
                "input": {"location": "London"}
            }
        ],
        "stop_reason": "tool_use",
        "usage": {"input_tokens": 25, "output_tokens": 45}
    }
    
    request = ChatCompletionRequest(model="claude-3-haiku", messages=[])
    response = claude_strategy.convert_from_bedrock_response(bedrock_response, request)
    
    assert response.choices[0].message.tool_calls is not None
    assert len(response.choices[0].message.tool_calls) == 1
    assert response.choices[0].message.tool_calls[0].function.name == "get_weather"
```

### Model Tests

**Testing Pydantic Models:**
```python
# tests/unit/test_models/test_chat_models.py
import pytest
from pydantic import ValidationError
from src.open_amazon_chat_completions_server.core.models import (
    ChatCompletionRequest, Message, Tool, Function
)

def test_chat_completion_request_validation():
    """Test ChatCompletionRequest validation"""
    # Valid request
    request = ChatCompletionRequest(
        model="gpt-4o-mini",
        messages=[Message(role="user", content="Hello")]
    )
    assert request.model == "gpt-4o-mini"
    assert len(request.messages) == 1
    
    # Invalid request - missing required fields
    with pytest.raises(ValidationError):
        ChatCompletionRequest(model="gpt-4o-mini")  # Missing messages

def test_message_with_tool_calls():
    """Test Message model with tool calls"""
    message = Message(
        role="assistant",
        content="I'll help you with that.",
        tool_calls=[{
            "id": "call_123",
            "type": "function",
            "function": {"name": "get_weather", "arguments": '{"location": "London"}'}
        }]
    )
    
    assert message.role == "assistant"
    assert len(message.tool_calls) == 1
    assert message.tool_calls[0].function.name == "get_weather"

def test_tool_definition():
    """Test Tool model validation"""
    tool = Tool(
        type="function",
        function=Function(
            name="get_weather",
            description="Get current weather",
            parameters={
                "type": "object",
                "properties": {"location": {"type": "string"}},
                "required": ["location"]
            }
        )
    )
    
    assert tool.function.name == "get_weather"
    assert "location" in tool.function.parameters["properties"]
```

## Integration Testing

### API Integration Tests

**Testing FastAPI Endpoints:**
```python
# tests/integration/test_api/test_chat_completions.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from src.open_amazon_chat_completions_server.main import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def mock_openai_service():
    with patch('src.open_amazon_chat_completions_server.services.llm_service_factory.LLMServiceFactory.get_service') as mock:
        service = AsyncMock()
        mock.return_value = service
        yield service

def test_chat_completions_openai_format(client, mock_openai_service):
    """Test chat completions with OpenAI format"""
    # Mock service response
    mock_response = {
        "id": "chatcmpl-123",
        "object": "chat.completion",
        "created": 1677652288,
        "model": "gpt-4o-mini",
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": "Hello! How can I help you?"},
            "finish_reason": "stop"
        }],
        "usage": {"prompt_tokens": 10, "completion_tokens": 15, "total_tokens": 25}
    }
    mock_openai_service.chat_completion.return_value = mock_response
    
    # Make request
    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer test-api-key"},
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "Hello"}]
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "chatcmpl-123"
    assert data["choices"][0]["message"]["content"] == "Hello! How can I help you?"

def test_chat_completions_bedrock_claude_format(client, mock_openai_service):
    """Test chat completions with Bedrock Claude format input"""
    mock_response = {
        "id": "msg_123",
        "type": "message",
        "role": "assistant",
        "content": [{"type": "text", "text": "Hello! How can I help you?"}],
        "model": "anthropic.claude-3-haiku-20240307-v1:0",
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 10, "output_tokens": 15}
    }
    mock_openai_service.chat_completion.return_value = mock_response
    
    response = client.post(
        "/v1/chat/completions?target_format=bedrock_claude",
        headers={"Authorization": "Bearer test-api-key"},
        json={
            "anthropic_version": "bedrock-2023-05-31",
            "model": "anthropic.claude-3-haiku-20240307-v1:0",
            "max_tokens": 1000,
            "messages": [{"role": "user", "content": "Hello"}]
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "message"
    assert data["content"][0]["text"] == "Hello! How can I help you?"

def test_authentication_required(client):
    """Test that authentication is required"""
    response = client.post(
        "/v1/chat/completions",
        json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "Hello"}]}
    )
    
    assert response.status_code == 401

def test_invalid_model(client):
    """Test handling of invalid model"""
    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer test-api-key"},
        json={
            "model": "invalid-model",
            "messages": [{"role": "user", "content": "Hello"}]
        }
    )
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
```

### CLI Integration Tests

**Testing CLI Commands:**
```python
# tests/integration/test_cli/test_commands.py
import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock
from src.open_amazon_chat_completions_server.cli.main import cli

@pytest.fixture
def runner():
    return CliRunner()

def test_config_set_command(runner):
    """Test config set command"""
    with patch('builtins.input', side_effect=['sk-test-key', 'test-api-key', '', '', 'us-east-1']):
        result = runner.invoke(cli, ['config', 'set'])
        
        assert result.exit_code == 0
        assert "Configuration saved" in result.output

def test_config_show_command(runner):
    """Test config show command"""
    with patch.dict('os.environ', {
        'OPENAI_API_KEY': 'sk-test-key',
        'API_KEY': 'test-api-key',
        'AWS_REGION': 'us-east-1'
    }):
        result = runner.invoke(cli, ['config', 'show'])
        
        assert result.exit_code == 0
        assert "OPENAI_API_KEY" in result.output
        assert "sk-***" in result.output  # Masked value

def test_models_command(runner):
    """Test models list command"""
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "object": "list",
            "data": [
                {"id": "gpt-4o-mini", "object": "model", "owned_by": "openai"}
            ]
        }
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        result = runner.invoke(cli, ['models'])
        
        assert result.exit_code == 0
        assert "gpt-4o-mini" in result.output

@patch('src.open_amazon_chat_completions_server.cli.chat.InteractiveChatSession')
def test_chat_command(mock_chat_session, runner):
    """Test interactive chat command"""
    mock_session = MagicMock()
    mock_chat_session.return_value = mock_session
    
    result = runner.invoke(cli, ['chat', '--model', 'gpt-4o-mini'])
    
    assert result.exit_code == 0
    mock_chat_session.assert_called_once()
    mock_session.start.assert_called_once()
```

## End-to-End Testing

### Complete Workflow Tests

**Testing Full User Workflows:**
```python
# tests/e2e/test_complete_workflows.py
import pytest
import asyncio
from fastapi.testclient import TestClient
from src.open_amazon_chat_completions_server.main import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.mark.e2e
def test_openai_to_bedrock_conversion_workflow(client):
    """Test complete workflow: OpenAI input → Bedrock output"""
    # This would be a real integration test with actual API calls
    # or against a test environment
    
    response = client.post(
        "/v1/chat/completions?target_format=bedrock_claude",
        headers={"Authorization": "Bearer test-api-key"},
        json={
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "What is the capital of France?"}
            ],
            "max_tokens": 100,
            "temperature": 0.7
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify Bedrock Claude format
    assert data["type"] == "message"
    assert data["role"] == "assistant"
    assert "content" in data
    assert isinstance(data["content"], list)
    assert data["content"][0]["type"] == "text"

@pytest.mark.e2e
def test_streaming_workflow(client):
    """Test streaming response workflow"""
    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer test-api-key"},
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "Tell me a short story"}],
            "stream": True
        }
    )
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/plain; charset=utf-8"
    
    # Verify streaming format
    chunks = response.content.decode().split('\n')
    data_chunks = [chunk for chunk in chunks if chunk.startswith('data: ')]
    
    assert len(data_chunks) > 0
    assert any('data: [DONE]' in chunk for chunk in chunks)
```

## Performance Testing

### Load Testing

**Testing System Performance:**
```python
# tests/performance/test_load.py
import pytest
import asyncio
import aiohttp
import time
from concurrent.futures import ThreadPoolExecutor

@pytest.mark.performance
async def test_concurrent_requests():
    """Test system performance under concurrent load"""
    async def make_request(session, request_id):
        async with session.post(
            "http://localhost:8000/v1/chat/completions",
            headers={"Authorization": "Bearer test-api-key"},
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": f"Request {request_id}"}],
                "max_tokens": 50
            }
        ) as response:
            return await response.json()
    
    start_time = time.time()
    
    async with aiohttp.ClientSession() as session:
        tasks = [make_request(session, i) for i in range(50)]
        responses = await asyncio.gather(*tasks)
    
    end_time = time.time()
    duration = end_time - start_time
    
    # Verify all requests succeeded
    assert len(responses) == 50
    assert all('choices' in response for response in responses)
    
    # Performance assertions
    assert duration < 30  # Should complete within 30 seconds
    print(f"50 concurrent requests completed in {duration:.2f} seconds")

@pytest.mark.performance
def test_memory_usage():
    """Test memory usage under load"""
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    # Simulate load
    # ... perform operations ...
    
    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_increase = final_memory - initial_memory
    
    # Memory should not increase significantly
    assert memory_increase < 100  # Less than 100MB increase
```

## Test Configuration

### Pytest Configuration

**conftest.py:**
```python
# tests/conftest.py
import pytest
import os
import asyncio
from unittest.mock import patch
from fastapi.testclient import TestClient

# Test environment setup
@pytest.fixture(autouse=True)
def setup_test_env():
    """Setup test environment variables"""
    test_env = {
        "OPENAI_API_KEY": "sk-test-openai-key",
        "API_KEY": "test-api-key",
        "AWS_REGION": "us-east-1",
        "LOG_LEVEL": "DEBUG",
        "ENVIRONMENT": "test"
    }
    
    with patch.dict(os.environ, test_env):
        yield

# Async test support
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# Mock fixtures
@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing"""
    with patch('openai.AsyncOpenAI') as mock:
        yield mock

@pytest.fixture
def mock_bedrock_client():
    """Mock Bedrock client for testing"""
    with patch('boto3.client') as mock:
        yield mock

# Test data fixtures
@pytest.fixture
def sample_messages():
    """Sample messages for testing"""
    return [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"},
        {"role": "assistant", "content": "Hello! How can I help you?"},
        {"role": "user", "content": "What's the weather like?"}
    ]

@pytest.fixture
def sample_tools():
    """Sample tools for testing"""
    return [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get current weather for a location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string", "description": "City name"}
                    },
                    "required": ["location"]
                }
            }
        }
    ]
```

### Test Markers

**pytest.ini:**
```ini
[tool:pytest]
markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    performance: Performance tests
    slow: Slow running tests
    
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Async support
asyncio_mode = auto

# Coverage
addopts = 
    --cov=src
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80
```

## Running Tests

### Test Execution Commands

```bash
# Run all tests
pytest

# Run specific test types
pytest -m unit
pytest -m integration
pytest -m e2e
pytest -m performance

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_services/test_openai_service.py

# Run with verbose output
pytest -v

# Run tests in parallel
pytest -n auto

# Run only failed tests from last run
pytest --lf

# Run tests matching pattern
pytest -k "test_chat_completion"
```

### Continuous Integration

**GitHub Actions Workflow:**
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, 3.10, 3.11]
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v3
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install uv
        uv pip install -e ".[dev]"
    
    - name: Run unit tests
      run: pytest -m unit --cov=src --cov-report=xml
    
    - name: Run integration tests
      run: pytest -m integration
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

## Test Coverage Goals

- **Unit Tests**: 90%+ coverage
- **Integration Tests**: Cover all API endpoints and CLI commands
- **E2E Tests**: Cover major user workflows
- **Performance Tests**: Validate system performance under load

## Best Practices

1. **Test Isolation**: Each test should be independent
2. **Mock External Dependencies**: Use mocks for API calls
3. **Test Data**: Use fixtures for consistent test data
4. **Descriptive Names**: Test names should describe what they test
5. **Arrange-Act-Assert**: Follow AAA pattern in tests
6. **Edge Cases**: Test error conditions and edge cases
7. **Performance**: Include performance regression tests

---

This comprehensive testing strategy ensures the Amazon Chat Completions Server maintains high quality and reliability across all components and use cases. 