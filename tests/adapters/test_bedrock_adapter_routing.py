import pytest
from unittest.mock import patch
from src.open_amazon_chat_completions_server.adapters.bedrock.bedrock_adapter import BedrockAdapter
from src.open_amazon_chat_completions_server.adapters.bedrock.ai21_strategy import AI21Strategy
from src.open_amazon_chat_completions_server.adapters.bedrock.cohere_strategy import CohereStrategy
from src.open_amazon_chat_completions_server.adapters.bedrock.meta_strategy import MetaStrategy
from src.open_amazon_chat_completions_server.adapters.bedrock.mistral_strategy import MistralStrategy
from src.open_amazon_chat_completions_server.adapters.bedrock.stability_strategy import StabilityStrategy
from src.open_amazon_chat_completions_server.adapters.bedrock.writer_strategy import WriterStrategy
from src.open_amazon_chat_completions_server.adapters.bedrock.nova_strategy import NovaStrategy
from src.open_amazon_chat_completions_server.adapters.bedrock.claude_strategy import ClaudeStrategy
from src.open_amazon_chat_completions_server.adapters.bedrock.titan_strategy import TitanStrategy


class TestBedrockAdapterRouting:
    """Test that BedrockAdapter routes to the correct strategies."""

    @patch('src.open_amazon_chat_completions_server.adapters.bedrock.bedrock_adapter.app_config')
    @patch('src.open_amazon_chat_completions_server.adapters.bedrock.bedrock_adapter.APIClient')
    def test_strategy_routing(self, mock_api_client, mock_app_config):
        """Test that BedrockAdapter routes to correct strategies based on model ID."""
        # Mock the app_config to have valid AWS credentials
        mock_app_config.AWS_ACCESS_KEY_ID = "test_key"
        mock_app_config.AWS_SECRET_ACCESS_KEY = "test_secret"
        mock_app_config.AWS_REGION = "us-east-1"

        # Test cases: (model_id, expected_strategy_class)
        test_cases = [
            ("anthropic.claude-3-sonnet-20240229-v1:0", ClaudeStrategy),
            ("amazon.titan-text-express-v1", TitanStrategy),
            ("amazon.nova-pro-v1:0", NovaStrategy),
            ("ai21.jamba-1-5-large-v1:0", AI21Strategy),
            ("cohere.command-text-v14", CohereStrategy),
            ("meta.llama2-13b-chat-v1", MetaStrategy),
            ("mistral.mistral-large-2402-v1:0", MistralStrategy),
            ("stability.sd3-5-large-v1:0", StabilityStrategy),
            ("writer.palmyra-x4-v1:0", WriterStrategy),
        ]

        for model_id, expected_strategy_class in test_cases:
            with patch('src.open_amazon_chat_completions_server.adapters.bedrock.bedrock_models.get_bedrock_model_id', return_value=model_id):
                adapter = BedrockAdapter(model_id)
                assert isinstance(adapter.strategy, expected_strategy_class), f"Model {model_id} should use {expected_strategy_class.__name__}"

    @patch('src.open_amazon_chat_completions_server.adapters.bedrock.bedrock_adapter.app_config')
    @patch('src.open_amazon_chat_completions_server.adapters.bedrock.bedrock_adapter.APIClient')
    def test_unsupported_model_raises_error(self, mock_api_client, mock_app_config):
        """Test that unsupported model IDs raise ModelNotFoundError."""
        # Mock the app_config to have valid AWS credentials
        mock_app_config.AWS_ACCESS_KEY_ID = "test_key"
        mock_app_config.AWS_SECRET_ACCESS_KEY = "test_secret"
        mock_app_config.AWS_REGION = "us-east-1"

        unsupported_model_id = "unsupported.model-v1:0"
        
        with patch('src.open_amazon_chat_completions_server.adapters.bedrock.bedrock_models.get_bedrock_model_id', return_value=unsupported_model_id):
            with pytest.raises(Exception):  # Should raise ModelNotFoundError
                BedrockAdapter(unsupported_model_id) 