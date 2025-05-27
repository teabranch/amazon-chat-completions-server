import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient

from src.amazon_chat_completions_server.api.app import app
from src.amazon_chat_completions_server.core.models import (
    ChatCompletionResponse,
    ChatCompletionChoice,
    Message,
    Usage,
    ChatCompletionChunk,
    ChatCompletionChunkChoice,
    ChoiceDelta,
)
from src.amazon_chat_completions_server.core.exceptions import ModelNotFoundError


class TestUnifiedModelBasedEndpoint:
    """Test the unified /v1/chat/completions endpoint with model-based routing"""
    
    @pytest.fixture
    def client(self):
        """Create a test client"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_openai_service(self):
        """Mock OpenAI service"""
        service = Mock()
        service.provider_name = "openai"
        return service
    
    @pytest.fixture
    def mock_bedrock_service(self):
        """Mock Bedrock service"""
        service = Mock()
        service.provider_name = "bedrock"
        return service

    def test_openai_model_routing(self, client):
        """Test that OpenAI models are routed correctly"""
        mock_response = ChatCompletionResponse(
            id="chatcmpl-123",
            object="chat.completion",
            created=1677652288,
            model="gpt-4o-mini",
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=Message(role="assistant", content="Hello!"),
                    finish_reason="stop"
                )
            ],
            usage=Usage(prompt_tokens=5, completion_tokens=2, total_tokens=7)
        )
        
        mock_service = Mock()
        mock_service.provider_name = "openai"
        mock_service.chat_completion_with_request = AsyncMock(return_value=mock_response)
        
        with patch('src.amazon_chat_completions_server.services.llm_service_factory.LLMServiceFactory.get_service_for_model', return_value=mock_service):
            response = client.post(
                "/v1/chat/completions",
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "user", "content": "Hello"}
                    ]
                },
                headers={"Authorization": "Bearer test-api-key"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["model"] == "gpt-4o-mini"
        assert data["choices"][0]["message"]["content"] == "Hello!"

    def test_bedrock_model_routing(self, client):
        """Test that Bedrock models are routed correctly"""
        mock_response = ChatCompletionResponse(
            id="chatcmpl-br-123",
            object="chat.completion",
            created=1677652288,
            model="anthropic.claude-3-haiku-20240307-v1:0",
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=Message(role="assistant", content="Hello from Claude!"),
                    finish_reason="end_turn"
                )
            ],
            usage=Usage(prompt_tokens=5, completion_tokens=3, total_tokens=8)
        )
        
        mock_service = Mock()
        mock_service.provider_name = "bedrock"
        mock_service.chat_completion_with_request = AsyncMock(return_value=mock_response)
        
        with patch('src.amazon_chat_completions_server.services.llm_service_factory.LLMServiceFactory.get_service_for_model', return_value=mock_service):
            response = client.post(
                "/v1/chat/completions",
                json={
                    "model": "anthropic.claude-3-haiku-20240307-v1:0",
                    "messages": [
                        {"role": "user", "content": "Hello"}
                    ]
                },
                headers={"Authorization": "Bearer test-api-key"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["model"] == "anthropic.claude-3-haiku-20240307-v1:0"
        assert data["choices"][0]["message"]["content"] == "Hello from Claude!"

    def test_claude_format_input_with_model_routing(self, client, mock_bedrock_service):
        """Test that Claude format input is converted and routed correctly"""
        mock_response = ChatCompletionResponse(
            id="chatcmpl-bedrock-123",
            object="chat.completion",
            created=1677652288,
            model="anthropic.claude-3-haiku-20240307-v1:0",
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=Message(
                        role="assistant",
                        content="Hello! I'm Claude."
                    ),
                    finish_reason="stop"
                )
            ],
            usage=Usage(
                prompt_tokens=15,
                completion_tokens=8,
                total_tokens=23
            )
        )
        
        mock_bedrock_service.chat_completion_with_request = AsyncMock(return_value=mock_response)
        
        with patch('src.amazon_chat_completions_server.services.llm_service_factory.LLMServiceFactory.get_service_for_model', return_value=mock_bedrock_service):
            # Send Claude format request
            response = client.post(
                "/v1/chat/completions",
                json={
                    "anthropic_version": "bedrock-2023-05-31",
                    "model": "anthropic.claude-3-haiku-20240307-v1:0",
                    "max_tokens": 1000,
                    "messages": [
                        {"role": "user", "content": "Hello"}
                    ]
                },
                headers={"Authorization": "Bearer test-api-key"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["model"] == "anthropic.claude-3-haiku-20240307-v1:0"

    def test_target_format_conversion(self, client, mock_openai_service):
        """Test target format conversion using query parameter"""
        mock_response = ChatCompletionResponse(
            id="chatcmpl-123",
            object="chat.completion",
            created=1677652288,
            model="gpt-4o-mini",
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=Message(
                        role="assistant",
                        content="Hello! How can I help you?"
                    ),
                    finish_reason="stop"
                )
            ],
            usage=Usage(
                prompt_tokens=10,
                completion_tokens=8,
                total_tokens=18
            )
        )
        
        mock_openai_service.chat_completion_with_request = AsyncMock(return_value=mock_response)
        
        with patch('src.amazon_chat_completions_server.services.llm_service_factory.LLMServiceFactory.get_service_for_model', return_value=mock_openai_service):
            with patch('src.amazon_chat_completions_server.adapters.bedrock_to_openai_adapter.BedrockToOpenAIAdapter.convert_openai_to_bedrock_response') as mock_convert:
                mock_bedrock_response = {
                    "id": "msg_123",
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "text", "text": "Hello! How can I help you?"}],
                    "model": "gpt-4o-mini",
                    "stop_reason": "end_turn",
                    "usage": {"input_tokens": 10, "output_tokens": 8}
                }
                mock_convert.return_value = Mock()
                mock_convert.return_value.model_dump.return_value = mock_bedrock_response
                
                response = client.post(
                    "/v1/chat/completions?target_format=bedrock_claude",
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [
                            {"role": "user", "content": "Hello"}
                        ]
                    },
                    headers={"Authorization": "Bearer test-api-key"}
                )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "msg_123"
        assert data["type"] == "message"

    def test_model_not_found_error(self, client):
        """Test model not found error handling"""
        with patch('src.amazon_chat_completions_server.services.llm_service_factory.LLMServiceFactory.get_service_for_model', side_effect=ModelNotFoundError("Model not found")):
            response = client.post(
                "/v1/chat/completions",
                json={
                    "model": "non-existent-model",
                    "messages": [
                        {"role": "user", "content": "Hello"}
                    ]
                },
                headers={"Authorization": "Bearer test-api-key"}
            )
        
        assert response.status_code == 404
        assert "Model not found" in response.json()["error"]["message"]

    def test_authentication_required(self, client):
        """Test that authentication is required"""
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "user", "content": "Hello"}
                ]
            }
        )
        
        assert response.status_code == 403

    def test_unified_health_endpoint(self, client):
        """Test the unified health endpoint"""
        response = client.get("/v1/chat/completions/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_streaming_endpoint(self, client, mock_openai_service):
        """Test streaming functionality"""
        async def mock_stream():
            yield ChatCompletionChunk(
                id="chatcmpl-123",
                object="chat.completion.chunk",
                created=1677652288,
                model="gpt-4o-mini",
                choices=[
                    ChatCompletionChunkChoice(
                        index=0,
                        delta=ChoiceDelta(content="Hello"),
                        finish_reason=None
                    )
                ]
            )
            yield ChatCompletionChunk(
                id="chatcmpl-123",
                object="chat.completion.chunk",
                created=1677652288,
                model="gpt-4o-mini",
                choices=[
                    ChatCompletionChunkChoice(
                        index=0,
                        delta=ChoiceDelta(content="!"),
                        finish_reason="stop"
                    )
                ]
            )
        
        mock_openai_service.chat_completion_with_request = AsyncMock(return_value=mock_stream())
        
        with patch('src.amazon_chat_completions_server.services.llm_service_factory.LLMServiceFactory.get_service_for_model', return_value=mock_openai_service):
            response = client.post(
                "/v1/chat/completions",
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "user", "content": "Hello"}
                    ],
                    "stream": True
                },
                headers={"Authorization": "Bearer test-api-key"}
            )
        
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]


class TestStreamingSupport:
    """Test streaming support in the unified endpoint"""
    
    @pytest.fixture
    def client(self):
        """Create a test client"""
        return TestClient(app)

    def test_streaming_parameter_true(self, client):
        """Test that stream=True enables streaming"""
        async def mock_stream():
            yield ChatCompletionChunk(
                id="chatcmpl-123",
                object="chat.completion.chunk",
                created=1677652288,
                model="gpt-4o-mini",
                choices=[
                    ChatCompletionChunkChoice(
                        index=0,
                        delta=ChoiceDelta(content="Hello"),
                        finish_reason=None
                    )
                ]
            )
        
        mock_service = Mock()
        mock_service.provider_name = "openai"
        mock_service.chat_completion_with_request = AsyncMock(return_value=mock_stream())
        
        with patch('src.amazon_chat_completions_server.services.llm_service_factory.LLMServiceFactory.get_service_for_model', return_value=mock_service):
            response = client.post(
                "/v1/chat/completions",
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": "Hello"}],
                    "stream": True
                },
                headers={"Authorization": "Bearer test-api-key"}
            )
        
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

    def test_streaming_parameter_false(self, client):
        """Test that stream=False disables streaming"""
        mock_response = ChatCompletionResponse(
            id="chatcmpl-123",
            object="chat.completion",
            created=1677652288,
            model="gpt-4o-mini",
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=Message(role="assistant", content="Hello!"),
                    finish_reason="stop"
                )
            ],
            usage=Usage(prompt_tokens=5, completion_tokens=2, total_tokens=7)
        )
        
        mock_service = Mock()
        mock_service.provider_name = "openai"
        mock_service.chat_completion_with_request = AsyncMock(return_value=mock_response)
        
        with patch('src.amazon_chat_completions_server.services.llm_service_factory.LLMServiceFactory.get_service_for_model', return_value=mock_service):
            response = client.post(
                "/v1/chat/completions",
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": "Hello"}],
                    "stream": False
                },
                headers={"Authorization": "Bearer test-api-key"}
            )
        
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]
        data = response.json()
        assert data["object"] == "chat.completion"

    def test_unified_endpoint_functionality(self, client):
        """Test the unified endpoint handles all format conversions"""
        mock_response = ChatCompletionResponse(
            id="chatcmpl-123",
            object="chat.completion",
            created=1677652288,
            model="gpt-4o-mini",
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=Message(role="assistant", content="Test response"),
                    finish_reason="stop"
                )
            ],
            usage=Usage(prompt_tokens=5, completion_tokens=2, total_tokens=7)
        )
        
        mock_service = Mock()
        mock_service.provider_name = "openai"
        mock_service.chat_completion_with_request = AsyncMock(return_value=mock_response)
        
        with patch('src.amazon_chat_completions_server.services.llm_service_factory.LLMServiceFactory.get_service_for_model', return_value=mock_service):
            # Test OpenAI format
            response = client.post(
                "/v1/chat/completions",
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": "Hello"}]
                },
                headers={"Authorization": "Bearer test-api-key"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["model"] == "gpt-4o-mini"
            assert data["choices"][0]["message"]["content"] == "Test response"

    def test_health_endpoint(self, client):
        """Test the unified health endpoint"""
        response = client.get("/v1/chat/completions/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "supported_input_formats" in data
        assert "openai" in data["supported_input_formats"]
        assert "bedrock_claude" in data["supported_input_formats"]
        assert "bedrock_titan" in data["supported_input_formats"] 