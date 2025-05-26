import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch
import json
import os

from src.amazon_chat_completions_server.api.app import app
from src.amazon_chat_completions_server.core.bedrock_models import (
    BedrockClaudeRequest,
    BedrockTitanRequest,
    BedrockMessage,
    BedrockContentBlock,
    BedrockTool,
    BedrockToolChoice,
    BedrockTitanConfig,
    BedrockClaudeResponse,
    BedrockTitanResponse
)


class TestBedrockEndpoints:
    """Test Bedrock-compatible API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create a test client"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_service(self):
        """Create a mock LLM service"""
        service = Mock()
        service.chat_completion_bedrock = AsyncMock()
        service.stream_chat_completion_bedrock = AsyncMock()
        return service
    
    @patch('src.amazon_chat_completions_server.api.routes.bedrock.BedrockToOpenAIAdapter')
    def test_claude_invoke_model(self, mock_adapter_class, client, mock_service):
        """Test /bedrock/claude/invoke-model endpoint"""
        # Mock the adapter class to return our mock service
        mock_adapter_class.return_value = mock_service
        
        # Mock response
        mock_response = BedrockClaudeResponse(
            id="msg_123",
            role="assistant",
            content=[BedrockContentBlock(type="text", text="Hello! How can I help you?")],
            model="claude-3-haiku",
            stop_reason="end_turn",
            usage={"input_tokens": 10, "output_tokens": 8}
        )
        mock_service.chat_completion_bedrock.return_value = mock_response
        
        # Test request
        claude_request = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": [
                {"role": "user", "content": "Hello, how are you?"}
            ],
            "temperature": 0.7
        }
        
        response = client.post(
            "/bedrock/claude/invoke-model?openai_model=gpt-4o-mini",
            json=claude_request,
            headers={"X-API-Key": "test-api-key"}
        )
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["id"] == "msg_123"
        assert response_data["role"] == "assistant"
        assert len(response_data["content"]) == 1
        assert response_data["content"][0]["text"] == "Hello! How can I help you?"
        assert response_data["stop_reason"] == "end_turn"
        
        # Verify service was called correctly
        mock_service.chat_completion_bedrock.assert_called_once()
        call_args = mock_service.chat_completion_bedrock.call_args
        assert isinstance(call_args[0][0], BedrockClaudeRequest)
        assert call_args[1]["original_format"] == "claude"
    
    @patch('src.amazon_chat_completions_server.api.routes.bedrock.BedrockToOpenAIAdapter')
    def test_claude_invoke_model_stream(self, mock_adapter_class, client, mock_service):
        """Test /bedrock/claude/invoke-model-stream endpoint"""
        # Mock the adapter class to return our mock service
        mock_adapter_class.return_value = mock_service
        
        # Mock streaming response
        async def mock_stream():
            from src.amazon_chat_completions_server.core.bedrock_models import BedrockClaudeStreamChunk
            chunks = [
                BedrockClaudeStreamChunk(type="content_block_delta", delta={"text": "Hello"}),
                BedrockClaudeStreamChunk(type="content_block_delta", delta={"text": " there!"}),
                BedrockClaudeStreamChunk(type="message_stop", delta={"stop_reason": "end_turn"})
            ]
            for chunk in chunks:
                yield chunk
        
        # Set the streaming method to return the async generator directly
        mock_service.stream_chat_completion_bedrock.return_value = mock_stream()
        
        claude_request = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": [
                {"role": "user", "content": "Hello"}
            ]
        }
        
        response = client.post(
            "/bedrock/claude/invoke-model-stream?openai_model=gpt-4o-mini",
            json=claude_request,
            headers={"X-API-Key": "test-api-key"}
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
        
        # Verify service was called correctly
        mock_service.stream_chat_completion_bedrock.assert_called_once()
    
    @patch('src.amazon_chat_completions_server.api.routes.bedrock.BedrockToOpenAIAdapter')
    def test_titan_invoke_model(self, mock_adapter_class, client, mock_service):
        """Test /bedrock/titan/invoke-model endpoint"""
        # Mock the adapter class to return our mock service
        mock_adapter_class.return_value = mock_service
        
        # Mock response
        mock_response = BedrockTitanResponse(
            inputTextTokenCount=5,
            results=[{
                "tokenCount": 8,
                "outputText": "Hello! How can I help you?",
                "completionReason": "FINISH"
            }]
        )
        mock_service.chat_completion_bedrock.return_value = mock_response
        
        # Test request
        titan_request = {
            "inputText": "Hello, how are you?",
            "textGenerationConfig": {
                "maxTokenCount": 1000,
                "temperature": 0.7,
                "topP": 0.9
            }
        }
        
        response = client.post(
            "/bedrock/titan/invoke-model?openai_model=gpt-4o-mini",
            json=titan_request,
            headers={"X-API-Key": "test-api-key"}
        )
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["inputTextTokenCount"] == 5
        assert len(response_data["results"]) == 1
        assert response_data["results"][0]["outputText"] == "Hello! How can I help you?"
        assert response_data["results"][0]["completionReason"] == "FINISH"
        
        # Verify service was called correctly
        mock_service.chat_completion_bedrock.assert_called_once()
        call_args = mock_service.chat_completion_bedrock.call_args
        assert isinstance(call_args[0][0], BedrockTitanRequest)
        assert call_args[1]["original_format"] == "titan"
    
    @patch('src.amazon_chat_completions_server.api.routes.bedrock.BedrockToOpenAIAdapter')
    def test_titan_invoke_model_stream(self, mock_adapter_class, client, mock_service):
        """Test /bedrock/titan/invoke-model-stream endpoint"""
        # Mock the adapter class to return our mock service
        mock_adapter_class.return_value = mock_service
        
        # Mock streaming response
        async def mock_stream():
            from src.amazon_chat_completions_server.core.bedrock_models import BedrockTitanStreamChunk
            chunks = [
                BedrockTitanStreamChunk(outputText="Hello", index=0),
                BedrockTitanStreamChunk(outputText=" there!", index=0),
                BedrockTitanStreamChunk(outputText="", index=0, completionReason="FINISH")
            ]
            for chunk in chunks:
                yield chunk
        
        # Set the streaming method to return the async generator directly
        mock_service.stream_chat_completion_bedrock.return_value = mock_stream()
        
        titan_request = {
            "inputText": "Hello",
            "textGenerationConfig": {
                "maxTokenCount": 1000
            }
        }
        
        response = client.post(
            "/bedrock/titan/invoke-model-stream?openai_model=gpt-4o-mini",
            json=titan_request,
            headers={"X-API-Key": "test-api-key"}
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
        
        # Verify service was called correctly
        mock_service.stream_chat_completion_bedrock.assert_called_once()
    
    @patch('src.amazon_chat_completions_server.api.routes.bedrock.BedrockToOpenAIAdapter')
    def test_model_routing_by_endpoint(self, mock_adapter_class, client, mock_service):
        """Test that endpoints route to correct OpenAI models"""
        # Mock the adapter class to return our mock service
        mock_adapter_class.return_value = mock_service
        
        mock_response = BedrockClaudeResponse(
            id="msg_123",
            role="assistant",
            content=[BedrockContentBlock(type="text", text="Test")],
            model="claude-3-haiku",
            stop_reason="end_turn",
            usage={"input_tokens": 5, "output_tokens": 1}
        )
        mock_service.chat_completion_bedrock.return_value = mock_response
        
        claude_request = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 100,
            "messages": [{"role": "user", "content": "Test"}]
        }
        
        # Test different OpenAI model routing
        test_models = ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"]
        
        for model in test_models:
            response = client.post(
                f"/bedrock/claude/invoke-model?openai_model={model}",
                json=claude_request,
                headers={"X-API-Key": "test-api-key"}
            )
            
            assert response.status_code == 200
            # Verify the adapter was created with the correct model
            mock_adapter_class.assert_called_with(openai_model_id=model)
    
    def test_authentication(self, client):
        """Test authentication for Bedrock endpoints"""
        claude_request = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 100,
            "messages": [{"role": "user", "content": "Test"}]
        }
        
        # Test without API key
        response = client.post(
            "/bedrock/claude/invoke-model",
            json=claude_request
        )
        assert response.status_code == 403
        
        # Test with invalid API key
        response = client.post(
            "/bedrock/claude/invoke-model",
            json=claude_request,
            headers={"X-API-Key": "invalid-key"}
        )
        assert response.status_code == 403
    
    @patch('src.amazon_chat_completions_server.api.routes.bedrock.BedrockToOpenAIAdapter')
    def test_error_responses(self, mock_adapter_class, client, mock_service):
        """Test error response format compatibility"""
        # Test invalid request format
        invalid_request = {
            "invalid_field": "value"
        }
        
        response = client.post(
            "/bedrock/claude/invoke-model",
            json=invalid_request,
            headers={"X-API-Key": "test-api-key"}
        )
        assert response.status_code == 422  # Validation error
        
        # Test service error
        mock_adapter_class.return_value = mock_service
        mock_service.chat_completion_bedrock.side_effect = Exception("Service error")
        
        valid_request = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 100,
            "messages": [{"role": "user", "content": "Test"}]
        }
        
        response = client.post(
            "/bedrock/claude/invoke-model",
            json=valid_request,
            headers={"X-API-Key": "test-api-key"}
        )
        
        assert response.status_code == 500
    
    @patch('src.amazon_chat_completions_server.api.routes.bedrock.BedrockToOpenAIAdapter')
    def test_claude_with_tools(self, mock_adapter_class, client, mock_service):
        """Test Claude endpoint with tools"""
        # Mock the adapter class to return our mock service
        mock_adapter_class.return_value = mock_service
        
        mock_response = BedrockClaudeResponse(
            id="msg_123",
            role="assistant",
            content=[BedrockContentBlock(type="text", text="I'll help you with the weather.")],
            model="claude-3-haiku",
            stop_reason="tool_use",
            usage={"input_tokens": 20, "output_tokens": 10}
        )
        mock_service.chat_completion_bedrock.return_value = mock_response
        
        claude_request = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": [
                {"role": "user", "content": "What's the weather in London?"}
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
        }
        
        response = client.post(
            "/bedrock/claude/invoke-model?openai_model=gpt-4o-mini",
            json=claude_request,
            headers={"X-API-Key": "test-api-key"}
        )
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["stop_reason"] == "tool_use"
    
    @patch('src.amazon_chat_completions_server.api.routes.bedrock.BedrockToOpenAIAdapter')
    def test_complex_content_blocks(self, mock_adapter_class, client, mock_service):
        """Test Claude endpoint with complex content blocks"""
        # Mock the adapter class to return our mock service
        mock_adapter_class.return_value = mock_service
        
        mock_response = BedrockClaudeResponse(
            id="msg_123",
            role="assistant",
            content=[BedrockContentBlock(type="text", text="I can see the image you shared.")],
            model="claude-3-haiku",
            stop_reason="end_turn",
            usage={"input_tokens": 50, "output_tokens": 12}
        )
        mock_service.chat_completion_bedrock.return_value = mock_response
        
        claude_request = {
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
        }
        
        response = client.post(
            "/bedrock/claude/invoke-model?openai_model=gpt-4o-mini",
            json=claude_request,
            headers={"X-API-Key": "test-api-key"}
        )
        
        assert response.status_code == 200
        response_data = response.json()
        assert "image" in response_data["content"][0]["text"].lower()
    
    @patch('src.amazon_chat_completions_server.api.routes.bedrock.BedrockToOpenAIAdapter')
    def test_default_model_selection(self, mock_adapter_class, client, mock_service):
        """Test default OpenAI model selection when not specified"""
        # Mock the adapter class to return our mock service
        mock_adapter_class.return_value = mock_service
        
        mock_response = BedrockClaudeResponse(
            id="msg_123",
            role="assistant",
            content=[BedrockContentBlock(type="text", text="Hello!")],
            model="claude-3-haiku",
            stop_reason="end_turn",
            usage={"input_tokens": 5, "output_tokens": 2}
        )
        mock_service.chat_completion_bedrock.return_value = mock_response
        
        claude_request = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 100,
            "messages": [{"role": "user", "content": "Hello"}]
        }
        
        # Test without specifying openai_model parameter
        response = client.post(
            "/bedrock/claude/invoke-model",
            json=claude_request,
            headers={"X-API-Key": "test-api-key"}
        )
        
        assert response.status_code == 200
        # Should use default model (gpt-4o-mini)
        mock_adapter_class.assert_called_with(openai_model_id="gpt-4o-mini")
    
    def test_parameter_validation(self, client):
        """Test parameter validation for Bedrock endpoints"""
        # Test missing required fields
        incomplete_claude_request = {
            "anthropic_version": "bedrock-2023-05-31",
            "messages": [{"role": "user", "content": "Hello"}]
            # Missing max_tokens
        }
        
        response = client.post(
            "/bedrock/claude/invoke-model",
            json=incomplete_claude_request,
            headers={"X-API-Key": "test-api-key"}
        )
        assert response.status_code == 422
        
        # Test invalid field values
        invalid_claude_request = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": -1,  # Invalid negative value
            "messages": [{"role": "user", "content": "Hello"}]
        }
        
        response = client.post(
            "/bedrock/claude/invoke-model",
            json=invalid_claude_request,
            headers={"X-API-Key": "test-api-key"}
        )
        assert response.status_code == 422 