import pytest
from unittest.mock import AsyncMock, patch
from src.open_amazon_chat_completions_server.adapters.openai_adapter import OpenAIAdapter
from src.open_amazon_chat_completions_server.core.models import (
    Message,
    ChatCompletionRequest,
    ChatCompletionResponse
)
from src.open_amazon_chat_completions_server.core.exceptions import (
    APIConnectionError,
    APIRequestError,
    RateLimitError
)

@pytest.fixture
def openai_adapter():
    return OpenAIAdapter(model_id="gpt-4")

@pytest.fixture
def sample_request():
    return ChatCompletionRequest(
        model="gpt-4",
        messages=[
            Message(role="system", content="You are a helpful assistant."),
            Message(role="user", content="Hello!")
        ]
    )

@pytest.mark.asyncio
async def test_chat_completion(openai_adapter, sample_request):
    mock_response = {
        "id": "chatcmpl-123",
        "object": "chat.completion",
        "created": 1677652288,
        "model": "gpt-4",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "Hello! How can I help you today?"
            },
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": 9,
            "completion_tokens": 12,
            "total_tokens": 21
        }
    }

    with patch('src.open_amazon_chat_completions_server.utils.api_client.APIClient.make_openai_chat_completion_request', 
               new_callable=AsyncMock) as mock_api:
        mock_api.return_value = mock_response
        response = await openai_adapter.chat_completion(sample_request)
        
        assert isinstance(response, ChatCompletionResponse)
        assert response.choices[0].message.content == "Hello! How can I help you today?"
        assert response.usage.total_tokens == 21

@pytest.mark.asyncio
async def test_stream_chat_completion(openai_adapter, sample_request):
    mock_chunks = [
        {
            "id": "chatcmpl-123",
            "object": "chat.completion.chunk",
            "created": 1677652288,
            "model": "gpt-4",
            "choices": [{
                "index": 0,
                "delta": {
                    "role": "assistant",
                    "content": "Hello"
                }
            }]
        },
        {
            "id": "chatcmpl-123",
            "object": "chat.completion.chunk",
            "created": 1677652288,
            "model": "gpt-4",
            "choices": [{
                "index": 0,
                "delta": {
                    "content": "!"
                },
                "finish_reason": "stop"
            }]
        }
    ]

    async def mock_stream():
        for chunk in mock_chunks:
            yield chunk

    with patch('src.open_amazon_chat_completions_server.utils.api_client.APIClient.make_openai_chat_completion_request', 
               new_callable=AsyncMock) as mock_api:
        mock_api.return_value = mock_stream()
        
        chunks = []
        async for chunk in openai_adapter.stream_chat_completion(sample_request):
            chunks.append(chunk)
        
        assert len(chunks) == 2
        assert chunks[0].choices[0].delta.content == "Hello"
        assert chunks[1].choices[0].delta.content == "!"

@pytest.mark.asyncio
async def test_error_handling(openai_adapter, sample_request):
    with patch('src.open_amazon_chat_completions_server.utils.api_client.APIClient.make_openai_chat_completion_request', 
               new_callable=AsyncMock) as mock_api:
        # Test rate limit error
        mock_api.side_effect = RateLimitError("Rate limit exceeded")
        with pytest.raises(RateLimitError):
            await openai_adapter.chat_completion(sample_request)

        # Test connection error
        mock_api.side_effect = APIConnectionError("Connection failed")
        with pytest.raises(APIConnectionError):
            await openai_adapter.chat_completion(sample_request)

        # Test invalid request
        mock_api.side_effect = APIRequestError("Invalid request")
        with pytest.raises(APIRequestError):
            await openai_adapter.chat_completion(sample_request)

def test_convert_to_provider_request(openai_adapter, sample_request):
    provider_request = openai_adapter.convert_to_provider_request(sample_request)
    
    assert provider_request["model"] == "gpt-4"
    assert len(provider_request["messages"]) == 2
    assert provider_request["messages"][0]["role"] == "system"
    assert provider_request["messages"][1]["role"] == "user" 