import pytest
from src.open_amazon_chat_completions_server.adapters.bedrock.claude_strategy import ClaudeStrategy
from src.open_amazon_chat_completions_server.core.models import (
    Message,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionChunk
)
from typing import Any

@pytest.fixture
def claude_strategy():
    def get_default_param_func(param_name: str, default_value: Any = None) -> Any:
        # Simple default param function for testing
        return default_value
    
    return ClaudeStrategy(
        model_id="anthropic.claude-3-7-sonnet-20250219-v1:0",
        get_default_param_func=get_default_param_func
    )

@pytest.fixture
def sample_request():
    return ChatCompletionRequest(
        model="claude-3-sonnet",
        messages=[
            Message(role="system", content="You are a helpful assistant."),
            Message(role="user", content="Hello!")
        ]
    )

def test_prepare_request_payload(claude_strategy, sample_request):
    payload = claude_strategy.prepare_request_payload(sample_request, {})
    
    assert "anthropic_version" in payload
    assert "messages" in payload
    assert "system" in payload
    assert len(payload["messages"]) == 1
    assert payload["messages"][0]["role"] == "user"
    assert payload["system"] == "You are a helpful assistant."

def test_parse_response(claude_strategy, sample_request):
    provider_response = {
        "id": "msg_123",
        "content": [{
            "type": "text",
            "text": "Hello! How can I help you today?"
        }],
        "role": "assistant",
        "stop_reason": "end_turn",
        "usage": {
            "input_tokens": 10,
            "output_tokens": 8
        }
    }
    
    response = claude_strategy.parse_response(provider_response, sample_request)
    
    assert isinstance(response, ChatCompletionResponse)
    assert response.choices[0].message.content == "Hello! How can I help you today?"
    assert response.choices[0].finish_reason == "stop"
    assert response.usage.prompt_tokens == 10
    assert response.usage.completion_tokens == 8

@pytest.mark.asyncio
async def test_handle_stream_chunk(claude_strategy, sample_request):
    chunk_data = {
        "type": "content_block_delta",
        "index": 0,
        "delta": {
            "type": "text",
            "text": "Hello"
        }
    }
    
    chunk = await claude_strategy.handle_stream_chunk(
        chunk_data,
        sample_request,
        "resp_123",
        1677652288
    )
    
    assert isinstance(chunk, ChatCompletionChunk)
    assert chunk.choices[0].delta.content == "Hello"
    assert chunk.id == "resp_123"

def test_tool_calls(claude_strategy):
    request = ChatCompletionRequest(
        model="claude-3-sonnet",
        messages=[Message(role="user", content="What's the weather in London?")],
        tools=[{
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get weather information",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string"}
                    },
                    "required": ["location"]
                }
            }
        }]
    )
    
    payload = claude_strategy.prepare_request_payload(request, {})
    assert "tools" in payload
    assert len(payload["tools"]) == 1
    assert payload["tools"][0]["function"]["name"] == "get_weather"

def test_system_prompt_extraction(claude_strategy):
    messages = [
        Message(role="system", content="You are a helpful assistant."),
        Message(role="user", content="Hi"),
        Message(role="assistant", content="Hello!"),
        Message(role="system", content="Be concise."),
        Message(role="user", content="How are you?")
    ]
    
    system_prompt, chat_messages = claude_strategy._extract_system_prompt_and_messages(messages)
    
    assert system_prompt == "You are a helpful assistant.\nBe concise."
    assert len(chat_messages) == 3  # user, assistant, user
    assert chat_messages[0].role == "user"
    assert chat_messages[1].role == "assistant"
    assert chat_messages[2].role == "user" 