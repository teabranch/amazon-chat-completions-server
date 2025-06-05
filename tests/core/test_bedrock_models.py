import pytest
from pydantic import ValidationError

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


class TestBedrockClaudeRequest:
    """Test Bedrock Claude request format validation"""
    
    def test_valid_claude_request(self):
        """Test valid Claude request creation"""
        request = BedrockClaudeRequest(
            max_tokens=1000,
            messages=[
                BedrockMessage(role="user", content="Hello, how are you?")
            ]
        )
        assert request.anthropic_version == "bedrock-2023-05-31"
        assert request.max_tokens == 1000
        assert len(request.messages) == 1
        assert request.messages[0].role == "user"
        assert request.messages[0].content == "Hello, how are you?"
    
    def test_claude_request_with_system_prompt(self):
        """Test Claude request with system prompt"""
        request = BedrockClaudeRequest(
            max_tokens=1000,
            messages=[
                BedrockMessage(role="user", content="Hello")
            ],
            system="You are a helpful assistant."
        )
        assert request.system == "You are a helpful assistant."
    
    def test_claude_request_with_tools(self):
        """Test Claude request with tools"""
        tool = BedrockTool(
            name="get_weather",
            description="Get weather information",
            input_schema={
                "type": "object",
                "properties": {
                    "location": {"type": "string"}
                },
                "required": ["location"]
            }
        )
        request = BedrockClaudeRequest(
            max_tokens=1000,
            messages=[
                BedrockMessage(role="user", content="What's the weather?")
            ],
            tools=[tool],
            tool_choice=BedrockToolChoice(type="auto")
        )
        assert len(request.tools) == 1
        assert request.tools[0].name == "get_weather"
        assert request.tool_choice.type == "auto"
    
    def test_claude_request_with_complex_content(self):
        """Test Claude request with complex content blocks"""
        content_blocks = [
            BedrockContentBlock(type="text", text="Hello"),
            BedrockContentBlock(type="image", source={
                "type": "base64",
                "media_type": "image/jpeg",
                "data": "base64data"
            })
        ]
        message = BedrockMessage(role="user", content=content_blocks)
        request = BedrockClaudeRequest(
            max_tokens=1000,
            messages=[message]
        )
        assert len(request.messages[0].content) == 2
        assert request.messages[0].content[0].type == "text"
        assert request.messages[0].content[1].type == "image"
    
    def test_claude_request_validation_errors(self):
        """Test Claude request validation errors"""
        # Missing required max_tokens
        with pytest.raises(ValidationError):
            BedrockClaudeRequest(
                messages=[BedrockMessage(role="user", content="Hello")]
            )
        
        # Empty messages
        with pytest.raises(ValidationError):
            BedrockClaudeRequest(
                max_tokens=1000,
                messages=[]
            )
        
        # Invalid role
        with pytest.raises(ValidationError):
            BedrockClaudeRequest(
                max_tokens=1000,
                messages=[BedrockMessage(role="invalid", content="Hello")]
            )


class TestBedrockTitanRequest:
    """Test Bedrock Titan request format validation"""
    
    def test_valid_titan_request(self):
        """Test valid Titan request creation"""
        config = BedrockTitanConfig(
            maxTokenCount=1000,
            temperature=0.7,
            topP=0.9
        )
        request = BedrockTitanRequest(
            inputText="Hello, how are you?",
            textGenerationConfig=config
        )
        assert request.inputText == "Hello, how are you?"
        assert request.textGenerationConfig.maxTokenCount == 1000
        assert request.textGenerationConfig.temperature == 0.7
        assert request.textGenerationConfig.topP == 0.9
    
    def test_titan_request_with_stop_sequences(self):
        """Test Titan request with stop sequences"""
        config = BedrockTitanConfig(
            maxTokenCount=1000,
            stopSequences=["Human:", "AI:"]
        )
        request = BedrockTitanRequest(
            inputText="Hello",
            textGenerationConfig=config
        )
        assert request.textGenerationConfig.stopSequences == ["Human:", "AI:"]
    
    def test_titan_request_validation_errors(self):
        """Test Titan request validation errors"""
        # Missing required inputText
        with pytest.raises(ValidationError):
            BedrockTitanRequest(
                textGenerationConfig=BedrockTitanConfig(maxTokenCount=1000)
            )
        
        # Missing required textGenerationConfig
        with pytest.raises(ValidationError):
            BedrockTitanRequest(inputText="Hello")
        
        # Invalid maxTokenCount
        with pytest.raises(ValidationError):
            BedrockTitanRequest(
                inputText="Hello",
                textGenerationConfig=BedrockTitanConfig(maxTokenCount=0)
            )


class TestBedrockToOpenAIConversion:
    """Test conversion from Bedrock format to OpenAI format"""
    
    def test_claude_to_openai_messages_conversion(self):
        """Test Claude messages to OpenAI messages conversion"""
        # This will test the conversion logic once implemented
        # Placeholder for conversion logic test
        # Expected OpenAI format:
        # This test will be implemented once the conversion logic is created
        pass
    
    def test_titan_to_openai_messages_conversion(self):
        """Test Titan inputText to OpenAI messages conversion"""
        # Expected OpenAI format:
        # This test will be implemented once the conversion logic is created
        pass
    
    def test_system_prompt_extraction(self):
        """Test system prompt extraction from Claude format"""
        # Expected: system prompt should be converted to OpenAI system message
        # This test will be implemented once the conversion logic is created
        pass
    
    def test_tool_calls_conversion(self):
        """Test tool calls format conversion"""
        # Expected OpenAI tool format
        # This test will be implemented once the conversion logic is created
        pass


class TestBedrockResponses:
    """Test Bedrock response models"""
    
    def test_claude_response_creation(self):
        """Test Claude response model creation"""
        response = BedrockClaudeResponse(
            id="msg_123",
            type="message",
            role="assistant",
            content=[
                BedrockContentBlock(type="text", text="Hello there!")
            ],
            model="claude-3-haiku",
            stop_reason="end_turn",
            usage={"input_tokens": 10, "output_tokens": 5}
        )
        assert response.id == "msg_123"
        assert response.role == "assistant"
        assert len(response.content) == 1
        assert response.content[0].text == "Hello there!"
        assert response.usage["input_tokens"] == 10
    
    def test_titan_response_creation(self):
        """Test Titan response model creation"""
        response = BedrockTitanResponse(
            inputTextTokenCount=10,
            results=[{
                "tokenCount": 5,
                "outputText": "Hello there!",
                "completionReason": "FINISH"
            }]
        )
        assert response.inputTextTokenCount == 10
        assert len(response.results) == 1
        assert response.results[0]["outputText"] == "Hello there!"
        assert response.results[0]["completionReason"] == "FINISH" 