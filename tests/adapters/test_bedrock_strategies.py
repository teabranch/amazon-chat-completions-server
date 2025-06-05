import pytest
from src.open_amazon_chat_completions_server.core.models import (
    ChatCompletionRequest,
    Message,
)
from src.open_amazon_chat_completions_server.adapters.bedrock.ai21_strategy import AI21Strategy
from src.open_amazon_chat_completions_server.adapters.bedrock.cohere_strategy import CohereStrategy
from src.open_amazon_chat_completions_server.adapters.bedrock.meta_strategy import MetaStrategy
from src.open_amazon_chat_completions_server.adapters.bedrock.mistral_strategy import MistralStrategy
from src.open_amazon_chat_completions_server.adapters.bedrock.stability_strategy import StabilityStrategy
from src.open_amazon_chat_completions_server.adapters.bedrock.writer_strategy import WriterStrategy
from src.open_amazon_chat_completions_server.adapters.bedrock.nova_strategy import NovaStrategy


class TestBedrockStrategies:
    """Test all Bedrock strategy implementations."""

    @pytest.fixture
    def mock_get_param_func(self):
        """Mock function for getting default parameters."""
        def mock_func(param_name, default_value=None):
            defaults = {
                "max_tokens": 2048,
                "temperature": 0.7,
            }
            return defaults.get(param_name, default_value)
        return mock_func

    @pytest.fixture
    def sample_request(self):
        """Sample chat completion request for testing."""
        return ChatCompletionRequest(
            model="test-model",
            messages=[
                Message(role="system", content="You are a helpful assistant."),
                Message(role="user", content="Hello, how are you?"),
            ],
            max_tokens=1000,
            temperature=0.8,
        )

    def test_ai21_strategy_initialization(self, mock_get_param_func):
        """Test AI21Strategy initialization."""
        strategy = AI21Strategy("ai21.jamba-1-5-large-v1:0", mock_get_param_func)
        assert strategy.model_id == "ai21.jamba-1-5-large-v1:0"

    def test_ai21_strategy_prepare_request(self, mock_get_param_func, sample_request):
        """Test AI21Strategy request preparation."""
        strategy = AI21Strategy("ai21.jamba-1-5-large-v1:0", mock_get_param_func)
        payload = strategy.prepare_request_payload(sample_request, {})
        
        assert "prompt" in payload
        assert "maxTokens" in payload
        assert "temperature" in payload
        assert payload["maxTokens"] == 1000
        assert payload["temperature"] == 0.8

    def test_cohere_strategy_initialization(self, mock_get_param_func):
        """Test CohereStrategy initialization."""
        strategy = CohereStrategy("cohere.command-text-v14", mock_get_param_func)
        assert strategy.model_id == "cohere.command-text-v14"

    def test_cohere_strategy_prepare_request(self, mock_get_param_func, sample_request):
        """Test CohereStrategy request preparation."""
        strategy = CohereStrategy("cohere.command-text-v14", mock_get_param_func)
        payload = strategy.prepare_request_payload(sample_request, {})
        
        assert "prompt" in payload
        assert "max_tokens" in payload
        assert "temperature" in payload
        assert payload["max_tokens"] == 1000
        assert payload["temperature"] == 0.8

    def test_meta_strategy_initialization(self, mock_get_param_func):
        """Test MetaStrategy initialization."""
        strategy = MetaStrategy("meta.llama2-13b-chat-v1", mock_get_param_func)
        assert strategy.model_id == "meta.llama2-13b-chat-v1"

    def test_meta_strategy_prepare_request(self, mock_get_param_func, sample_request):
        """Test MetaStrategy request preparation."""
        strategy = MetaStrategy("meta.llama2-13b-chat-v1", mock_get_param_func)
        payload = strategy.prepare_request_payload(sample_request, {})
        
        assert "prompt" in payload
        assert "max_gen_len" in payload
        assert "temperature" in payload
        assert payload["max_gen_len"] == 1000
        assert payload["temperature"] == 0.8

    def test_mistral_strategy_initialization(self, mock_get_param_func):
        """Test MistralStrategy initialization."""
        strategy = MistralStrategy("mistral.mistral-large-2402-v1:0", mock_get_param_func)
        assert strategy.model_id == "mistral.mistral-large-2402-v1:0"

    def test_mistral_strategy_prepare_request(self, mock_get_param_func, sample_request):
        """Test MistralStrategy request preparation."""
        strategy = MistralStrategy("mistral.mistral-large-2402-v1:0", mock_get_param_func)
        payload = strategy.prepare_request_payload(sample_request, {})
        
        assert "prompt" in payload
        assert "max_tokens" in payload
        assert "temperature" in payload
        assert payload["max_tokens"] == 1000
        assert payload["temperature"] == 0.8

    def test_stability_strategy_initialization(self, mock_get_param_func):
        """Test StabilityStrategy initialization."""
        strategy = StabilityStrategy("stability.sd3-5-large-v1:0", mock_get_param_func)
        assert strategy.model_id == "stability.sd3-5-large-v1:0"

    def test_stability_strategy_prepare_request(self, mock_get_param_func, sample_request):
        """Test StabilityStrategy request preparation."""
        strategy = StabilityStrategy("stability.sd3-5-large-v1:0", mock_get_param_func)
        payload = strategy.prepare_request_payload(sample_request, {})
        
        assert "prompt" in payload
        assert "max_tokens" in payload
        assert "temperature" in payload
        assert payload["max_tokens"] == 1000
        assert payload["temperature"] == 0.8

    def test_writer_strategy_initialization(self, mock_get_param_func):
        """Test WriterStrategy initialization."""
        strategy = WriterStrategy("writer.palmyra-x4-v1:0", mock_get_param_func)
        assert strategy.model_id == "writer.palmyra-x4-v1:0"

    def test_writer_strategy_prepare_request(self, mock_get_param_func, sample_request):
        """Test WriterStrategy request preparation."""
        strategy = WriterStrategy("writer.palmyra-x4-v1:0", mock_get_param_func)
        payload = strategy.prepare_request_payload(sample_request, {})
        
        assert "prompt" in payload
        assert "maxTokens" in payload
        assert "temperature" in payload
        assert payload["maxTokens"] == 1000
        assert payload["temperature"] == 0.8

    def test_nova_strategy_initialization(self, mock_get_param_func):
        """Test NovaStrategy initialization."""
        strategy = NovaStrategy("amazon.nova-pro-v1:0", mock_get_param_func)
        assert strategy.model_id == "amazon.nova-pro-v1:0"

    def test_nova_strategy_prepare_request(self, mock_get_param_func, sample_request):
        """Test NovaStrategy request preparation."""
        strategy = NovaStrategy("amazon.nova-pro-v1:0", mock_get_param_func)
        payload = strategy.prepare_request_payload(sample_request, {})
        
        assert "messages" in payload
        assert "maxTokens" in payload
        assert "temperature" in payload
        assert payload["maxTokens"] == 1000
        assert payload["temperature"] == 0.8

    def test_all_strategies_handle_tools_gracefully(self, mock_get_param_func):
        """Test that all strategies handle tool requests appropriately."""
        request_with_tools = ChatCompletionRequest(
            model="test-model",
            messages=[Message(role="user", content="Hello")],
            tools=[{"type": "function", "function": {"name": "test", "description": "test", "parameters": {}}}],
        )

        strategies = [
            AI21Strategy("ai21.jamba-1-5-large-v1:0", mock_get_param_func),
            CohereStrategy("cohere.command-text-v14", mock_get_param_func),
            MetaStrategy("meta.llama2-13b-chat-v1", mock_get_param_func),
            MistralStrategy("mistral.mistral-large-2402-v1:0", mock_get_param_func),
            StabilityStrategy("stability.sd3-5-large-v1:0", mock_get_param_func),
            WriterStrategy("writer.palmyra-x4-v1:0", mock_get_param_func),
            NovaStrategy("amazon.nova-pro-v1:0", mock_get_param_func),
        ]

        for strategy in strategies:
            with pytest.raises(Exception):  # Should raise UnsupportedFeatureError
                strategy.prepare_request_payload(request_with_tools, {})

    def test_all_strategies_parse_response(self, mock_get_param_func, sample_request):
        """Test that all strategies can parse mock responses."""
        # Mock responses for each strategy
        mock_responses = {
            "ai21": {"completions": [{"data": {"text": "Hello!"}, "finishReason": {"reason": "stop"}}]},
            "cohere": {"generations": [{"text": "Hello!", "finish_reason": "COMPLETE"}]},
            "meta": {"generation": "Hello!", "stop_reason": "stop", "prompt_token_count": 10, "generation_token_count": 5},
            "mistral": {"outputs": [{"text": "Hello!", "stop_reason": "stop"}], "usage": {"prompt_tokens": 10, "completion_tokens": 5}},
            "stability": {"completions": [{"text": "Hello!", "finish_reason": "stop"}], "usage": {"prompt_tokens": 10, "completion_tokens": 5}},
            "writer": {"completions": [{"data": {"text": "Hello!"}, "finishReason": "stop"}], "usage": {"promptTokens": 10, "completionTokens": 5}},
            "nova": {"output": {"message": {"content": [{"text": "Hello!"}]}}, "stopReason": "end_turn", "usage": {"inputTokens": 10, "outputTokens": 5}},
        }

        strategies_and_responses = [
            (AI21Strategy("ai21.jamba-1-5-large-v1:0", mock_get_param_func), mock_responses["ai21"]),
            (CohereStrategy("cohere.command-text-v14", mock_get_param_func), mock_responses["cohere"]),
            (MetaStrategy("meta.llama2-13b-chat-v1", mock_get_param_func), mock_responses["meta"]),
            (MistralStrategy("mistral.mistral-large-2402-v1:0", mock_get_param_func), mock_responses["mistral"]),
            (StabilityStrategy("stability.sd3-5-large-v1:0", mock_get_param_func), mock_responses["stability"]),
            (WriterStrategy("writer.palmyra-x4-v1:0", mock_get_param_func), mock_responses["writer"]),
            (NovaStrategy("amazon.nova-pro-v1:0", mock_get_param_func), mock_responses["nova"]),
        ]

        for strategy, mock_response in strategies_and_responses:
            response = strategy.parse_response(mock_response, sample_request)
            assert response.choices[0].message.content == "Hello!"
            assert response.choices[0].message.role == "assistant" 