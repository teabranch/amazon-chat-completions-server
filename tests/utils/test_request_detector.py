
from src.open_amazon_chat_completions_server.utils.request_detector import RequestFormatDetector
from src.open_amazon_chat_completions_server.core.bedrock_models import RequestFormat


class TestRequestFormatDetector:
    """Test request format detection functionality"""
    
    def test_detect_openai_format(self):
        """Test detection of OpenAI format requests"""
        openai_request = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "user", "content": "Hello"}
            ],
            "temperature": 0.7,
            "max_tokens": 1000
        }
        
        format_result = RequestFormatDetector.detect_format(openai_request)
        assert format_result == RequestFormat.OPENAI
        assert RequestFormatDetector.is_openai_format(openai_request) is True
        assert RequestFormatDetector.is_bedrock_claude_format(openai_request) is False
        assert RequestFormatDetector.is_bedrock_titan_format(openai_request) is False
    
    def test_detect_bedrock_claude_format(self):
        """Test detection of Bedrock Claude format requests"""
        claude_request = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": [
                {"role": "user", "content": "Hello"}
            ],
            "system": "You are a helpful assistant."
        }
        
        format_result = RequestFormatDetector.detect_format(claude_request)
        assert format_result == RequestFormat.BEDROCK_CLAUDE
        assert RequestFormatDetector.is_bedrock_claude_format(claude_request) is True
        assert RequestFormatDetector.is_openai_format(claude_request) is False
        assert RequestFormatDetector.is_bedrock_titan_format(claude_request) is False
    
    def test_detect_bedrock_titan_format(self):
        """Test detection of Bedrock Titan format requests"""
        titan_request = {
            "inputText": "Hello, how are you?",
            "textGenerationConfig": {
                "maxTokenCount": 1000,
                "temperature": 0.7,
                "topP": 0.9
            }
        }
        
        format_result = RequestFormatDetector.detect_format(titan_request)
        assert format_result == RequestFormat.BEDROCK_TITAN
        assert RequestFormatDetector.is_bedrock_titan_format(titan_request) is True
        assert RequestFormatDetector.is_openai_format(titan_request) is False
        assert RequestFormatDetector.is_bedrock_claude_format(titan_request) is False
    
    def test_detect_openai_with_tools(self):
        """Test detection of OpenAI format with tools"""
        openai_request_with_tools = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "user", "content": "What's the weather?"}
            ],
            "tools": [
                {
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
                }
            ],
            "tool_choice": "auto"
        }
        
        format_result = RequestFormatDetector.detect_format(openai_request_with_tools)
        assert format_result == RequestFormat.OPENAI
    
    def test_detect_claude_with_tools(self):
        """Test detection of Claude format with tools"""
        claude_request_with_tools = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": [
                {"role": "user", "content": "What's the weather?"}
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
        
        format_result = RequestFormatDetector.detect_format(claude_request_with_tools)
        assert format_result == RequestFormat.BEDROCK_CLAUDE
    
    def test_ambiguous_format_handling(self):
        """Test handling of ambiguous request formats"""
        # Request with minimal fields that could be ambiguous
        minimal_request = {
            "messages": [
                {"role": "user", "content": "Hello"}
            ]
        }
        
        # Should default to OpenAI format when ambiguous
        format_result = RequestFormatDetector.detect_format(minimal_request)
        assert format_result == RequestFormat.OPENAI
    
    def test_unknown_format_handling(self):
        """Test handling of completely unknown request formats"""
        unknown_request = {
            "some_unknown_field": "value",
            "another_field": 123
        }
        
        format_result = RequestFormatDetector.detect_format(unknown_request)
        assert format_result == RequestFormat.UNKNOWN
    
    def test_empty_request_handling(self):
        """Test handling of empty requests"""
        empty_request = {}
        
        format_result = RequestFormatDetector.detect_format(empty_request)
        assert format_result == RequestFormat.UNKNOWN
    
    def test_claude_format_with_anthropic_version_variations(self):
        """Test Claude format detection with different anthropic_version values"""
        claude_requests = [
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "messages": [{"role": "user", "content": "Hello"}]
            },
            {
                "anthropic_version": "bedrock-2024-01-01",
                "max_tokens": 1000,
                "messages": [{"role": "user", "content": "Hello"}]
            }
        ]
        
        for request in claude_requests:
            format_result = RequestFormatDetector.detect_format(request)
            assert format_result == RequestFormat.BEDROCK_CLAUDE
    
    def test_titan_format_variations(self):
        """Test Titan format detection with different configuration options"""
        titan_requests = [
            {
                "inputText": "Hello",
                "textGenerationConfig": {
                    "maxTokenCount": 1000
                }
            },
            {
                "inputText": "Hello",
                "textGenerationConfig": {
                    "maxTokenCount": 1000,
                    "temperature": 0.7,
                    "topP": 0.9,
                    "stopSequences": ["Human:", "AI:"]
                }
            }
        ]
        
        for request in titan_requests:
            format_result = RequestFormatDetector.detect_format(request)
            assert format_result == RequestFormat.BEDROCK_TITAN
    
    def test_openai_format_variations(self):
        """Test OpenAI format detection with different parameter combinations"""
        openai_requests = [
            {
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "Hello"}]
            },
            {
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": "Hello"}],
                "temperature": 0.7,
                "max_tokens": 1000,
                "stream": True
            },
            {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": "You are helpful"},
                    {"role": "user", "content": "Hello"}
                ],
                "top_p": 0.9,
                "presence_penalty": 0.1
            }
        ]
        
        for request in openai_requests:
            format_result = RequestFormatDetector.detect_format(request)
            assert format_result == RequestFormat.OPENAI
    
    def test_format_detection_priority(self):
        """Test format detection priority when multiple indicators are present"""
        # Request with both OpenAI and Claude-like fields
        mixed_request = {
            "model": "gpt-4o-mini",  # OpenAI indicator
            "anthropic_version": "bedrock-2023-05-31",  # Claude indicator
            "max_tokens": 1000,
            "messages": [{"role": "user", "content": "Hello"}]
        }
        
        # Claude indicators should take priority due to specificity
        format_result = RequestFormatDetector.detect_format(mixed_request)
        assert format_result == RequestFormat.BEDROCK_CLAUDE
    
    def test_case_sensitivity(self):
        """Test that format detection is case-sensitive where appropriate"""
        # Test with incorrect case
        incorrect_case_request = {
            "Model": "gpt-4o-mini",  # Capital M
            "Messages": [{"role": "user", "content": "Hello"}]  # Capital M
        }
        
        format_result = RequestFormatDetector.detect_format(incorrect_case_request)
        assert format_result == RequestFormat.UNKNOWN
    
    def test_nested_structure_detection(self):
        """Test detection with complex nested structures"""
        complex_claude_request = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Hello"},
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": "base64data"
                            }
                        }
                    ]
                }
            ]
        }
        
        format_result = RequestFormatDetector.detect_format(complex_claude_request)
        assert format_result == RequestFormat.BEDROCK_CLAUDE 