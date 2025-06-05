import pytest
from unittest.mock import patch

from src.open_amazon_chat_completions_server.adapters.bedrock_to_openai_adapter import BedrockToOpenAIAdapter
from src.open_amazon_chat_completions_server.core.bedrock_models import (
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
from src.open_amazon_chat_completions_server.core.models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionChoice,
    ChatCompletionChunk,
    ChatCompletionChunkChoice,
    ChoiceDelta,
    Message,
    Usage
)


class TestBedrockToOpenAIAdapter:
    """Test Bedrock-to-OpenAI adapter functionality"""
    
    @pytest.fixture
    def adapter(self):
        """Create a BedrockToOpenAIAdapter instance for testing"""
        return BedrockToOpenAIAdapter(openai_model_id="gpt-4o-mini")
    
    def test_adapter_initialization(self, adapter):
        """Test adapter initialization"""
        assert adapter.openai_model_id == "gpt-4o-mini"
        assert adapter.openai_adapter is not None
    
    def test_claude_to_openai_conversion(self, adapter):
        """Test Claude format to OpenAI format conversion"""
        claude_request = BedrockClaudeRequest(
            max_tokens=1000,
            messages=[
                BedrockMessage(role="user", content="Hello, how are you?")
            ],
            temperature=0.7,
            system="You are a helpful assistant."
        )
        
        openai_request = adapter.convert_bedrock_to_openai_request(claude_request)
        
        assert isinstance(openai_request, ChatCompletionRequest)
        assert openai_request.model == "gpt-4o-mini"
        assert openai_request.max_tokens == 1000
        assert openai_request.temperature == 0.7
        assert len(openai_request.messages) == 2  # system + user message
        assert openai_request.messages[0].role == "system"
        assert openai_request.messages[0].content == "You are a helpful assistant."
        assert openai_request.messages[1].role == "user"
        assert openai_request.messages[1].content == "Hello, how are you?"
    
    def test_titan_to_openai_conversion(self, adapter):
        """Test Titan format to OpenAI format conversion"""
        titan_request = BedrockTitanRequest(
            inputText="Hello, how are you?",
            textGenerationConfig=BedrockTitanConfig(
                maxTokenCount=1000,
                temperature=0.7,
                topP=0.9
            )
        )
        
        openai_request = adapter.convert_bedrock_to_openai_request(titan_request)
        
        assert isinstance(openai_request, ChatCompletionRequest)
        assert openai_request.model == "gpt-4o-mini"
        assert openai_request.max_tokens == 1000
        assert openai_request.temperature == 0.7
        assert len(openai_request.messages) == 1
        assert openai_request.messages[0].role == "user"
        assert openai_request.messages[0].content == "Hello, how are you?"
    
    def test_system_message_handling(self, adapter):
        """Test system message extraction and conversion"""
        claude_request = BedrockClaudeRequest(
            max_tokens=1000,
            messages=[
                BedrockMessage(role="user", content="What's the weather?"),
                BedrockMessage(role="assistant", content="I'd be happy to help with weather information."),
                BedrockMessage(role="user", content="Tell me about London.")
            ],
            system="You are a weather assistant. Always provide accurate weather information."
        )
        
        openai_request = adapter.convert_bedrock_to_openai_request(claude_request)
        
        # System message should be first
        assert openai_request.messages[0].role == "system"
        assert openai_request.messages[0].content == "You are a weather assistant. Always provide accurate weather information."
        
        # Followed by conversation messages
        assert len(openai_request.messages) == 4  # system + 3 conversation messages
        assert openai_request.messages[1].role == "user"
        assert openai_request.messages[2].role == "assistant"
        assert openai_request.messages[3].role == "user"
    
    def test_tool_calls_conversion(self, adapter):
        """Test tool calls format conversion"""
        bedrock_tool = BedrockTool(
            name="get_weather",
            description="Get weather information for a location",
            input_schema={
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "The city name"},
                    "units": {"type": "string", "enum": ["celsius", "fahrenheit"]}
                },
                "required": ["location"]
            }
        )
        
        claude_request = BedrockClaudeRequest(
            max_tokens=1000,
            messages=[
                BedrockMessage(role="user", content="What's the weather in London?")
            ],
            tools=[bedrock_tool],
            tool_choice=BedrockToolChoice(type="auto")
        )
        
        openai_request = adapter.convert_bedrock_to_openai_request(claude_request)
        
        assert openai_request.tools is not None
        assert len(openai_request.tools) == 1
        
        openai_tool = openai_request.tools[0]
        assert openai_tool["type"] == "function"
        assert openai_tool["function"]["name"] == "get_weather"
        assert openai_tool["function"]["description"] == "Get weather information for a location"
        assert openai_tool["function"]["parameters"] == bedrock_tool.input_schema
        
        assert openai_request.tool_choice == "auto"
    
    def test_complex_content_conversion(self, adapter):
        """Test conversion of complex content blocks"""
        content_blocks = [
            BedrockContentBlock(type="text", text="Look at this image:"),
            BedrockContentBlock(
                type="image",
                source={
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": "base64encodeddata"
                }
            )
        ]
        
        claude_request = BedrockClaudeRequest(
            max_tokens=1000,
            messages=[
                BedrockMessage(role="user", content=content_blocks)
            ]
        )
        
        openai_request = adapter.convert_bedrock_to_openai_request(claude_request)
        
        # Should convert to OpenAI multimodal format
        assert len(openai_request.messages) == 1
        message_content = openai_request.messages[0].content
        assert isinstance(message_content, list)
        assert len(message_content) == 2
        
        # Text content
        assert message_content[0]["type"] == "text"
        assert message_content[0]["text"] == "Look at this image:"
        
        # Image content
        assert message_content[1]["type"] == "image_url"
        assert "image_url" in message_content[1]
    
    def test_openai_to_bedrock_response_conversion_claude(self, adapter):
        """Test OpenAI response to Claude response conversion"""
        openai_response = ChatCompletionResponse(
            id="chatcmpl-123",
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=Message(role="assistant", content="Hello! How can I help you today?"),
                    finish_reason="stop"
                )
            ],
            created=1234567890,
            model="gpt-4o-mini",
            usage=Usage(prompt_tokens=10, completion_tokens=15, total_tokens=25)
        )
        
        claude_response = adapter.convert_openai_to_bedrock_response(
            openai_response, 
            original_format="claude"
        )
        
        assert isinstance(claude_response, BedrockClaudeResponse)
        assert claude_response.id == "chatcmpl-123"
        assert claude_response.role == "assistant"
        assert len(claude_response.content) == 1
        assert claude_response.content[0].type == "text"
        assert claude_response.content[0].text == "Hello! How can I help you today?"
        assert claude_response.stop_reason == "end_turn"
        assert claude_response.usage["input_tokens"] == 10
        assert claude_response.usage["output_tokens"] == 15
    
    def test_openai_to_bedrock_response_conversion_titan(self, adapter):
        """Test OpenAI response to Titan response conversion"""
        openai_response = ChatCompletionResponse(
            id="chatcmpl-123",
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=Message(role="assistant", content="Hello! How can I help you today?"),
                    finish_reason="stop"
                )
            ],
            created=1234567890,
            model="gpt-4o-mini",
            usage=Usage(prompt_tokens=10, completion_tokens=15, total_tokens=25)
        )
        
        titan_response = adapter.convert_openai_to_bedrock_response(
            openai_response, 
            original_format="titan"
        )
        
        assert isinstance(titan_response, BedrockTitanResponse)
        assert titan_response.inputTextTokenCount == 10
        assert len(titan_response.results) == 1
        assert titan_response.results[0]["outputText"] == "Hello! How can I help you today?"
        assert titan_response.results[0]["tokenCount"] == 15
        assert titan_response.results[0]["completionReason"] == "FINISH"
    
    @pytest.mark.asyncio
    async def test_streaming_conversion(self, adapter):
        """Test streaming response conversion"""
        # Mock the OpenAI adapter's streaming method
        mock_chunks = [
            ChatCompletionChunk(
                id="chatcmpl-123",
                choices=[
                    ChatCompletionChunkChoice(
                        index=0,
                        delta=ChoiceDelta(role="assistant", content="Hello"),
                        finish_reason=None
                    )
                ],
                created=1234567890,
                model="gpt-4o-mini"
            ),
            ChatCompletionChunk(
                id="chatcmpl-123",
                choices=[
                    ChatCompletionChunkChoice(
                        index=0,
                        delta=ChoiceDelta(content=" there!"),
                        finish_reason=None
                    )
                ],
                created=1234567890,
                model="gpt-4o-mini"
            ),
            ChatCompletionChunk(
                id="chatcmpl-123",
                choices=[
                    ChatCompletionChunkChoice(
                        index=0,
                        delta=ChoiceDelta(),
                        finish_reason="stop"
                    )
                ],
                created=1234567890,
                model="gpt-4o-mini"
            )
        ]
        
        async def mock_stream_generator():
            for chunk in mock_chunks:
                yield chunk
        
        with patch.object(adapter.openai_adapter, 'stream_chat_completion', return_value=mock_stream_generator()):
            claude_request = BedrockClaudeRequest(
                max_tokens=1000,
                messages=[BedrockMessage(role="user", content="Hello")]
            )
            
            chunks = []
            async for chunk in adapter.stream_chat_completion_bedrock(claude_request, original_format="claude"):
                chunks.append(chunk)
            
            assert len(chunks) == 3
            # Verify chunks are converted to Bedrock format
            # This will be implemented once the streaming conversion logic is created
    
    def test_error_handling(self, adapter):
        """Test error scenarios and edge cases"""
        # Test with invalid request type
        with pytest.raises(ValueError):
            adapter.convert_bedrock_to_openai_request("invalid_request")
        
        # Test with unsupported format
        with pytest.raises(ValueError):
            openai_response = ChatCompletionResponse(
                id="test", choices=[], created=123, model="test"
            )
            adapter.convert_openai_to_bedrock_response(openai_response, "unsupported_format")
    
    def test_tool_choice_variations(self, adapter):
        """Test different tool choice formats"""
        # Test with string tool choice
        claude_request = BedrockClaudeRequest(
            max_tokens=1000,
            messages=[BedrockMessage(role="user", content="Hello")],
            tools=[BedrockTool(
                name="test_tool",
                description="Test tool",
                input_schema={"type": "object", "properties": {}}
            )],
            tool_choice="any"
        )
        
        openai_request = adapter.convert_bedrock_to_openai_request(claude_request)
        assert openai_request.tool_choice == "any"
        
        # Test with specific tool choice
        claude_request.tool_choice = BedrockToolChoice(type="tool", name="test_tool")
        openai_request = adapter.convert_bedrock_to_openai_request(claude_request)
        assert openai_request.tool_choice == {"type": "function", "function": {"name": "test_tool"}}
    
    def test_parameter_mapping(self, adapter):
        """Test parameter mapping between formats"""
        claude_request = BedrockClaudeRequest(
            max_tokens=1500,
            messages=[BedrockMessage(role="user", content="Hello")],
            temperature=0.8,
            top_p=0.95,
            top_k=40,
            stop_sequences=["Human:", "AI:"]
        )
        
        openai_request = adapter.convert_bedrock_to_openai_request(claude_request)
        
        assert openai_request.max_tokens == 1500
        assert openai_request.temperature == 0.8
        # top_p should be mapped correctly
        # top_k should be ignored (not supported in OpenAI)
        # stop_sequences should be mapped to stop parameter
    
    def test_finish_reason_mapping(self, adapter):
        """Test finish reason mapping between formats"""
        test_cases = [
            ("stop", "end_turn"),
            ("length", "max_tokens"),
            ("tool_calls", "tool_use"),
            ("content_filter", "stop_sequence")
        ]
        
        for openai_reason, expected_claude_reason in test_cases:
            openai_response = ChatCompletionResponse(
                id="test",
                choices=[
                    ChatCompletionChoice(
                        index=0,
                        message=Message(role="assistant", content="Test"),
                        finish_reason=openai_reason
                    )
                ],
                created=123,
                model="test"
            )
            
            claude_response = adapter.convert_openai_to_bedrock_response(
                openai_response, 
                original_format="claude"
            )
            
            assert claude_response.stop_reason == expected_claude_reason 