import logging
from collections.abc import AsyncGenerator
from typing import Any

from ..adapters.base_adapter import (
    BaseLLMAdapter,
)  # OpenAIAdapter and BedrockAdapter inherit from this
from ..core.exceptions import APIRequestError, LLMIntegrationError
from ..core.models import (
    ChatCompletionChunk,
    ChatCompletionRequest,
    ChatCompletionResponse,
    Message,
)
from .llm_service_abc import AbstractLLMService

logger = logging.getLogger(__name__)


class ConcreteLLMService(AbstractLLMService):
    """A concrete implementation of AbstractLLMService that uses an adapter."""

    def __init__(self, adapter: BaseLLMAdapter):
        if not isinstance(adapter, BaseLLMAdapter):
            raise LLMIntegrationError(
                f"Adapter must be an instance of BaseLLMAdapter, got {type(adapter)}"
            )
        self.adapter = adapter
        self.provider_name = adapter.__class__.__name__.replace("Adapter", "").lower()
        logger.info(
            f"ConcreteLLMService initialized with {adapter.__class__.__name__} for model {adapter.model_id}"
        )

    async def chat_completion(
        self,
        messages: list[Message],
        model_id: str
        | None = None,  # If provided, can override adapter's default, though adapter is typically model-specific
        stream: bool = False,
        temperature: float | None = None,
        max_tokens: int | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,  # Provider-specific parameters not in ChatCompletionRequest model
    ) -> ChatCompletionResponse | AsyncGenerator[ChatCompletionChunk, None]:
        """
        Sends a chat completion request using the configured adapter.
        """

        # The adapter is initialized with a specific model_id.
        # If model_id is passed here, it should ideally match or be compatible.
        # For now, we assume the adapter's configured model_id is the one to be used.
        # If a different model_id is passed here, it might indicate a need for a different adapter instance.
        # This could be handled by the factory, or the service could re-fetch an adapter if model_id changes.
        # For simplicity, we will use the adapter's inherent model_id.
        effective_model_id = self.adapter.model_id
        if model_id and model_id != self.adapter.model_id:
            logger.warning(
                f"ChatCompletion called with model_id '{model_id}' which differs from adapter's model_id '{self.adapter.model_id}'. "
                f"Using adapter's model: '{self.adapter.model_id}'. To use a different model, get a new service instance from the factory."
            )
            # Or, you could choose to raise an error or try to use the passed model_id with the current adapter if it supports it.
            # For now, we stick to the adapter's configured model.

        # Merge kwargs from the call with kwargs from adapter initialization (adapter.config_kwargs)
        # Call-specific kwargs should take precedence.
        # However, adapter.config_kwargs are typically for adapter-level fixed settings.
        # Parameters like temperature, max_tokens are part of ChatCompletionRequest.
        # Other OpenAI/Bedrock params passed via **kwargs here are for the API call itself.

        # The adapter's `_get_default_param` already handles falling back to AppConfig defaults.
        # So, we only need to pass `temperature` and `max_tokens` if they are explicitly set in this call.

        # Create the generic ChatCompletionRequest DTO
        request_dto = ChatCompletionRequest(
            messages=messages,
            model=effective_model_id,  # This model is for the DTO, adapter will use its own configured one
            stream=stream,
            temperature=temperature,  # Pass through, adapter will use its default if None
            max_tokens=max_tokens,  # Pass through, adapter will use its default if None
            tool_choice=tool_choice,
            tools=tools,
            **kwargs,  # Pass any other standard OpenAI request params here
        )

        # The adapter.config_kwargs are those passed during adapter init (e.g. via factory)
        # The **kwargs in this method are call-specific additions.
        # The adapter's convert_to_provider_request should handle merging these appropriately if needed,
        # or primarily use what's in ChatCompletionRequest DTO and its own init kwargs.

        try:
            if stream:
                if not hasattr(self.adapter, "stream_chat_completion"):
                    raise NotImplementedError(
                        f"Adapter {self.adapter.__class__.__name__} does not support streaming."
                    )
                # The type hint for stream_chat_completion in BaseLLMAdapter is already AsyncGenerator[ChatCompletionChunk, None]
                return self.adapter.stream_chat_completion(request_dto)
            else:
                if not hasattr(self.adapter, "chat_completion"):
                    raise NotImplementedError(
                        f"Adapter {self.adapter.__class__.__name__} does not support non-streaming chat_completion."
                    )
                response: ChatCompletionResponse = await self.adapter.chat_completion(
                    request_dto
                )
                return response
        except APIRequestError as e:
            logger.error(f"{self.provider_name} API Request Error in service: {e}")
            raise
        except LLMIntegrationError as e:
            logger.error(f"{self.provider_name} LLM Integration Error in service: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in {self.provider_name} service: {e}")
            raise LLMIntegrationError(
                f"Unexpected error in {self.provider_name} service: {e}"
            ) from e


# Specific service classes (optional, could just use ConcreteLLMService with correct adapter)


class OpenAIService(ConcreteLLMService):
    def __init__(self, adapter: BaseLLMAdapter):
        super().__init__(adapter)
        if not type(adapter).__name__ == "OpenAIAdapter":  # Basic check
            raise LLMIntegrationError(
                "OpenAIService must be initialized with an OpenAIAdapter."
            )
        self.provider_name = "openai"


class BedrockService(ConcreteLLMService):
    def __init__(self, adapter: BaseLLMAdapter):
        super().__init__(adapter)
        if not type(adapter).__name__ == "BedrockAdapter":  # Basic check
            raise LLMIntegrationError(
                "BedrockService must be initialized with a BedrockAdapter."
            )
        self.provider_name = "bedrock"
