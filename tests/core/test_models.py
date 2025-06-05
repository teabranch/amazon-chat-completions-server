import pytest
from src.open_amazon_chat_completions_server.core.models import (
    Message,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionChoice,
    ChatCompletionChunk,
    ChatCompletionChunkChoice,
    ChoiceDelta,
    Usage,
    ModelProviderInfo
)

def test_message_creation():
    # Test basic message
    msg = Message(role="user", content="Hello")
    assert msg.role == "user"
    assert msg.content == "Hello"
    
    # Test tool message
    tool_msg = Message(
        role="assistant",
        content=None,
        tool_calls=[{
            "id": "call_123",
            "type": "function",
            "function": {
                "name": "get_weather",
                "arguments": '{"location": "London"}'
            }
        }]
    )
    assert tool_msg.role == "assistant"
    assert tool_msg.tool_calls is not None
    assert len(tool_msg.tool_calls) == 1

def test_chat_completion_request():
    messages = [
        Message(role="system", content="You are a helpful assistant."),
        Message(role="user", content="Hello!")
    ]
    request = ChatCompletionRequest(
        model="test-model",
        messages=messages,
        temperature=0.7,
        max_tokens=100
    )
    assert request.model == "test-model"
    assert len(request.messages) == 2
    assert request.temperature == 0.7
    assert request.max_tokens == 100

def test_chat_completion_response():
    choice = ChatCompletionChoice(
        index=0,
        message=Message(role="assistant", content="Hi there!"),
        finish_reason="stop"
    )
    usage = Usage(prompt_tokens=10, completion_tokens=5, total_tokens=15)
    
    response = ChatCompletionResponse(
        id="resp_123",
        choices=[choice],
        model="test-model",
        usage=usage,
        created=1234567890
    )
    
    assert response.id == "resp_123"
    assert len(response.choices) == 1
    assert response.choices[0].message.content == "Hi there!"
    assert response.usage.total_tokens == 15

def test_chat_completion_chunk():
    delta = ChoiceDelta(role="assistant", content="Hi")
    chunk_choice = ChatCompletionChunkChoice(
        index=0,
        delta=delta,
        finish_reason=None
    )
    
    chunk = ChatCompletionChunk(
        id="chunk_123",
        choices=[chunk_choice],
        model="test-model",
        created=1234567890
    )
    
    assert chunk.id == "chunk_123"
    assert len(chunk.choices) == 1
    assert chunk.choices[0].delta.content == "Hi"

def test_model_provider_info():
    model_info = ModelProviderInfo(
        id="model-123",
        provider="test-provider",
        display_name="Test Model"
    )
    
    assert model_info.id == "model-123"
    assert model_info.provider == "test-provider"
    assert model_info.display_name == "Test Model"

def test_invalid_message_role():
    with pytest.raises(ValueError):
        Message(role="invalid_role", content="test")

def test_empty_messages_list():
    with pytest.raises(ValueError):
        ChatCompletionRequest(model="test-model", messages=[]) 