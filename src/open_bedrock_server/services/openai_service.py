import logging
import os
from collections.abc import AsyncGenerator

from openai import APIError, AsyncOpenAI, AuthenticationError, NotFoundError

# Import custom exceptions (assuming they would be defined in core.exceptions)
from src.open_bedrock_server.core.exceptions import (
    ConfigurationError,
    ServiceApiError,
    ServiceAuthenticationError,
    ServiceModelNotFoundError,
    ServiceUnavailableError,
)
from src.open_bedrock_server.core.models import (
    ChatCompletionChoice as CoreChatCompletionChoice,  # Renaming to avoid conflict if OpenAI's Choice is used
)
from src.open_bedrock_server.core.models import (
    ChatCompletionChunk,
    ChatCompletionChunkChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChoiceDelta,
    Message,
    ModelProviderInfo,
)
from src.open_bedrock_server.core.models import (
    Usage as CoreUsage,  # Import our Usage model
)

# Use AbstractLLMService from the existing module
from .llm_service_abc import AbstractLLMService

logger = logging.getLogger(__name__)


class OpenAIService(AbstractLLMService):
    def __init__(
        self, api_key: str | None = None, **kwargs
    ):  # Added **kwargs to match factory
        # kwargs might be used for other settings like base_url, timeout, etc.
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.error(
                "OpenAI API key not provided and not found in OPENAI_API_KEY environment variable."
            )
            # This error happens at service instantiation, will be caught by factory or route if not handled before.
            # For tests, OPENAI_API_KEY_IS_SET check should prevent this if key is truly missing.
            # If key is empty string, it might pass this but fail at client init or first call.
            raise ConfigurationError(
                "OpenAI API key not provided or found in environment variables."
            )

        # Allow overriding OpenAI client parameters if passed in kwargs
        client_params = {"api_key": self.api_key}
        if "base_url" in kwargs:
            client_params["base_url"] = kwargs["base_url"]
        # Add other relevant client params from kwargs if needed

        try:
            self.client = AsyncOpenAI(**client_params)
        except Exception as e:  # Catch potential errors during client instantiation
            logger.error(f"Failed to initialize OpenAI client: {e}")
            raise ConfigurationError(f"Failed to initialize OpenAI client: {e}")
        logger.info("OpenAIService initialized.")

    @property
    def provider_name(self) -> str:
        """Return the provider name for this service."""
        return "openai"

    async def _map_to_core_response(self, openai_response) -> ChatCompletionResponse:
        core_choices = [
            CoreChatCompletionChoice(
                index=choice.index,
                message=Message(
                    role=choice.message.role,
                    content=choice.message.content,
                    tool_calls=choice.message.tool_calls,
                ),
                finish_reason=choice.finish_reason,
            )
            for choice in openai_response.choices
        ]

        core_usage = None
        if openai_response.usage:
            core_usage = CoreUsage(
                prompt_tokens=openai_response.usage.prompt_tokens,
                completion_tokens=openai_response.usage.completion_tokens,
                total_tokens=openai_response.usage.total_tokens,
            )

        return ChatCompletionResponse(
            id=openai_response.id,
            object=openai_response.object,
            created=openai_response.created,
            model=openai_response.model,
            choices=core_choices,
            usage=core_usage,
        )

    async def _map_to_core_chunk(self, openai_chunk) -> ChatCompletionChunk:
        core_chunk_choices = [
            ChatCompletionChunkChoice(
                index=choice.index,
                delta=ChoiceDelta(
                    content=choice.delta.content,
                    role=choice.delta.role,
                    tool_calls=choice.delta.tool_calls,
                ),
                finish_reason=choice.finish_reason,
            )
            for choice in openai_chunk.choices
        ]
        return ChatCompletionChunk(
            id=openai_chunk.id,
            object=openai_chunk.object,
            created=openai_chunk.created,
            model=openai_chunk.model,
            choices=core_chunk_choices,
        )

    async def _handle_non_streaming(
        self, payload: dict, model_id: str
    ) -> ChatCompletionResponse:
        try:
            response = await self.client.chat.completions.create(**payload)
            return await self._map_to_core_response(response)
        except AuthenticationError as e:
            logger.error(f"OpenAI Authentication Error: {e} (Model: {model_id})")
            raise ServiceAuthenticationError(
                f"OpenAI authentication failed: {e.message}"
            )
        except NotFoundError as e:
            logger.error(f"OpenAI Model Not Found Error: {e} (Model: {model_id})")
            raise ServiceModelNotFoundError(
                f"OpenAI model not found or you do not have access: {model_id}. Detail: {e.message}"
            )
        except APIError as e:
            logger.error(
                f"OpenAI API Error: {e} (Model: {model_id}, Status: {e.status_code}, Type: {type(e).__name__})"
            )
            if e.status_code == 503:
                raise ServiceUnavailableError(
                    f"OpenAI service unavailable: {e.message}"
                )
            raise ServiceApiError(
                f"OpenAI API error: {e.message} (Status: {e.status_code}, Type: {type(e).__name__}, Param: {e.param}, Code: {e.code})"
            )
        except Exception as e:
            logger.error(
                f"Unexpected error during OpenAI call: {type(e).__name__} - {e} (Model: {model_id})"
            )
            raise ServiceApiError(
                f"Unexpected error communicating with OpenAI: {type(e).__name__} - {str(e)}"
            )

    async def _handle_streaming(
        self, payload: dict, model_id: str
    ) -> AsyncGenerator[ChatCompletionChunk, None]:
        try:
            stream = await self.client.chat.completions.create(**payload)
            async for chunk in stream:
                yield await self._map_to_core_chunk(chunk)
        except AuthenticationError as e:
            logger.error(f"OpenAI Authentication Error: {e} (Model: {model_id})")
            raise ServiceAuthenticationError(
                f"OpenAI authentication failed: {e.message}"
            )
        except NotFoundError as e:
            logger.error(f"OpenAI Model Not Found Error: {e} (Model: {model_id})")
            raise ServiceModelNotFoundError(
                f"OpenAI model not found or you do not have access: {model_id}. Detail: {e.message}"
            )
        except APIError as e:
            logger.error(
                f"OpenAI API Error: {e} (Model: {model_id}, Status: {e.status_code}, Type: {type(e).__name__})"
            )
            if e.status_code == 503:
                raise ServiceUnavailableError(
                    f"OpenAI service unavailable: {e.message}"
                )
            raise ServiceApiError(
                f"OpenAI API error: {e.message} (Status: {e.status_code}, Type: {type(e).__name__}, Param: {e.param}, Code: {e.code})"
            )
        except Exception as e:
            logger.error(
                f"Unexpected error during OpenAI call: {type(e).__name__} - {e} (Model: {model_id})"
            )
            raise ServiceApiError(
                f"Unexpected error communicating with OpenAI: {type(e).__name__} - {str(e)}"
            )

    async def chat_completion(
        self,
        messages: list[Message],
        model_id: str | None = None,
        stream: bool = False,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs,
    ) -> ChatCompletionResponse | AsyncGenerator[ChatCompletionChunk, None]:
        # Handle the standard interface (messages list)
        if not model_id:
            logger.error("Model ID is required for OpenAI chat completion.")
            raise ValueError("Model ID must be provided for OpenAI chat completion.")

        logger.info(
            f"OpenAIService: Sending chat completion. Model: {model_id}, Stream: {stream}"
        )

        payload = {
            "model": model_id,
            "messages": [msg.model_dump(exclude_none=True) for msg in messages],
            "stream": stream,
        }
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if "tools" in kwargs and kwargs["tools"] is not None:
            payload["tools"] = kwargs["tools"]
        if "tool_choice" in kwargs and kwargs["tool_choice"] is not None:
            payload["tool_choice"] = kwargs["tool_choice"]

        if stream:
            return self._handle_streaming(payload, model_id)
        else:
            return await self._handle_non_streaming(payload, model_id)

    async def chat_completion_with_request(
        self,
        request: ChatCompletionRequest,
    ) -> ChatCompletionResponse | AsyncGenerator[ChatCompletionChunk, None]:
        """
        Handle chat completion with a ChatCompletionRequest DTO.
        This method is used by the API routes.
        """
        kwargs = {}
        if request.tools:
            kwargs["tools"] = request.tools
        if request.tool_choice:
            kwargs["tool_choice"] = request.tool_choice

        return await self.chat_completion(
            messages=request.messages,
            model_id=request.model,
            stream=request.stream or False,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            **kwargs,
        )

    async def list_models(self) -> list[ModelProviderInfo]:
        logger.info("OpenAIService: Fetching models from OpenAI")
        try:
            models_response = await self.client.models.list()
            provider_models = [
                ModelProviderInfo(
                    id=model.id,
                    provider="openai",
                    display_name=model.id,
                )
                for model in models_response.data
                if "gpt" in model.id or model.id.startswith("text-davinci")
            ]
            logger.info(f"Found {len(provider_models)} OpenAI models.")
            return provider_models
        except AuthenticationError as e:
            logger.error(f"OpenAI Authentication Error listing models: {e}")
            raise ServiceAuthenticationError(
                f"OpenAI authentication failed while listing models: {e.message}"
            )
        except APIError as e:
            logger.error(f"OpenAI API Error listing models: {e}")
            raise ServiceApiError(
                f"OpenAI API error listing models: {e.message} (Status: {e.status_code})"
            )
        except Exception as e:
            logger.error(f"Unexpected error listing OpenAI models: {e}")
            # Return empty list or raise custom error? For now, let's be consistent with previous behavior.
            raise ServiceApiError(f"Unexpected error listing OpenAI models: {str(e)}")


# Need to define these custom exceptions, likely in core.exceptions.py
# For now, assume they exist for the purpose of this change.
# Example definitions (would go in core/exceptions.py):
# class ConfigurationError(Exception): pass
# class ServiceAuthenticationError(Exception): pass
# class ServiceModelNotFoundError(Exception): pass
# class ServiceApiError(Exception): pass
# class ServiceUnavailableError(Exception): pass
