from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any

from ..core.models import (
    ChatCompletionChunk,
    ChatCompletionRequest,
    ChatCompletionResponse,
)


class BaseLLMAdapter(ABC):
    """Abstract base class for LLM provider adapters."""

    @abstractmethod
    def __init__(self, model_id: str, **kwargs):
        """Initialize the adapter with a specific model ID and any provider-specific kwargs."""
        self.model_id = model_id
        self.config_kwargs = kwargs  # Store for later use

    @abstractmethod
    def convert_to_provider_request(self, request: ChatCompletionRequest) -> Any:
        """Converts a generic ChatCompletionRequest to the provider-specific request format."""
        pass

    @abstractmethod
    def convert_from_provider_response(
        self, provider_response: Any
    ) -> ChatCompletionResponse:
        """Converts a provider-specific response to a generic ChatCompletionResponse."""
        pass

    @abstractmethod
    async def chat_completion(
        self, request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        """Processes a chat completion request and returns a standard response."""
        pass

    @abstractmethod
    def convert_from_provider_stream_chunk(
        self, provider_chunk: Any, original_request: ChatCompletionRequest
    ) -> ChatCompletionChunk:
        """Converts a provider-specific streaming chunk to a generic ChatCompletionChunk."""
        pass

    @abstractmethod
    async def stream_chat_completion(
        self, request: ChatCompletionRequest
    ) -> AsyncGenerator[ChatCompletionChunk, None]:
        """Processes a streaming chat completion request and yields standard chunks."""
        # Ensure the generator is properly defined, even if it's just to satisfy the ABC
        # Actual implementation will be in concrete classes.
        # For example, a simple way to make this an async generator:
        if False:  # This ensures the method is recognized as an async generator
            yield
        pass  # Must be overridden by concrete implementations

    # Helper methods that might be common or overridden
    def _get_default_param(
        self,
        param_name: str,
        provider_specific_name: str | None = None,
        default_value: Any = None,
    ) -> Any:
        """Helper to get parameters from kwargs or app_config with defaults."""
        from ..utils.config_loader import (
            app_config,
        )  # Local import to avoid circular deps at module load time

        if (
            param_name in self.config_kwargs
            and self.config_kwargs[param_name] is not None
        ):
            return self.config_kwargs[param_name]

        # Construct a potential config key based on provider and model type (e.g., DEFAULT_MAX_TOKENS_OPENAI)
        # This logic determines the provider prefix based on model_id patterns
        provider_prefix = "OPENAI"  # Default fallback

        if self.model_id.startswith("anthropic."):
            provider_prefix = "CLAUDE"
        elif self.model_id.startswith("amazon.titan"):
            provider_prefix = "TITAN"
        elif self.model_id.startswith("amazon.nova"):
            provider_prefix = "NOVA"
        elif self.model_id.startswith("ai21."):
            provider_prefix = "AI21"
        elif self.model_id.startswith("cohere."):
            provider_prefix = "COHERE"
        elif self.model_id.startswith("meta."):
            provider_prefix = "META"
        elif self.model_id.startswith("mistral."):
            provider_prefix = "MISTRAL"
        elif self.model_id.startswith("stability."):
            provider_prefix = "STABILITY"
        elif self.model_id.startswith("writer."):
            provider_prefix = "WRITER"
        else:
            # Fallback to OPENAI for any unrecognized model patterns
            # This assumes non-Bedrock models are OpenAI compatible for defaults
            provider_prefix = "OPENAI"

        config_key = f"DEFAULT_{param_name.upper()}_{provider_prefix}"

        if hasattr(app_config, config_key):
            return getattr(app_config, config_key)

        return default_value
