import logging
import time
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from ..core.exceptions import APIRequestError, ConfigurationError, LLMIntegrationError
from ..core.models import (
    ChatCompletionChoice,
    ChatCompletionChunk,
    ChatCompletionChunkChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChoiceDelta,
    Message,
    Usage,
)
from ..utils.api_client import (
    APIClient,
)  # Assuming APIClient is synchronous for now, or make this adapter async
from ..utils.config_loader import app_config
from .base_adapter import BaseLLMAdapter

# To use the async APIClient
# from ..utils.api_client import get_openai_client, APIClient as AsyncAPIClient

logger = logging.getLogger(__name__)


class OpenAIAdapter(BaseLLMAdapter):
    """Adapter for OpenAI's Chat Completions API."""

    def __init__(self, model_id: str, **kwargs):
        super().__init__(model_id, **kwargs)
        self.api_client = APIClient()  # Or AsyncAPIClient()
        if not app_config.OPENAI_API_KEY:
            raise ConfigurationError("OpenAI API key not configured for OpenAIAdapter.")
        logger.info(f"OpenAIAdapter initialized for model: {self.model_id}")

    def convert_to_provider_request(
        self, request: ChatCompletionRequest
    ) -> dict[str, Any]:
        """Converts a generic ChatCompletionRequest to an OpenAI-specific request payload."""
        provider_messages = []
        for msg in request.messages:
            provider_msg = {"role": msg.role, "content": msg.content}
            if msg.name:
                provider_msg["name"] = msg.name
            if msg.tool_call_id:
                provider_msg["tool_call_id"] = msg.tool_call_id
            if msg.tool_calls:
                provider_msg["tool_calls"] = (
                    msg.tool_calls
                )  # OpenAI expects this directly
            provider_messages.append(provider_msg)

        payload = {
            "model": self.model_id,  # Use the specific model_id for this adapter instance
            "messages": provider_messages,
        }

        # Add optional parameters if they are not None in the original request
        # or fall back to defaults from config if not provided in request.
        temperature = (
            request.temperature
            if request.temperature is not None
            else self._get_default_param(
                "temperature", default_value=app_config.DEFAULT_TEMPERATURE_OPENAI
            )
        )
        if temperature is not None:
            payload["temperature"] = temperature

        max_tokens = (
            request.max_tokens
            if request.max_tokens is not None
            else self._get_default_param(
                "max_tokens", default_value=app_config.DEFAULT_MAX_TOKENS_OPENAI
            )
        )
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        if request.tools:
            payload["tools"] = request.tools
        if request.tool_choice:
            payload["tool_choice"] = request.tool_choice

        # Add other supported OpenAI parameters from request.kwargs or self.config_kwargs
        # For example: top_p, presence_penalty, frequency_penalty, stop, etc.
        # This needs to be explicitly mapped to avoid sending unsupported params.
        supported_openai_params = [
            "top_p",
            "presence_penalty",
            "frequency_penalty",
            "stop",
            "logit_bias",
            "user",
        ]
        for param_name in supported_openai_params:
            if (
                param_name in self.config_kwargs
                and self.config_kwargs[param_name] is not None
            ):
                # Check if param_name exists in ChatCompletionRequest model and if its value is not None
                if (
                    hasattr(request, param_name)
                    and getattr(request, param_name) is not None
                ):
                    payload[param_name] = getattr(request, param_name)
                else:
                    payload[param_name] = self.config_kwargs[param_name]
            elif (
                hasattr(request, param_name)
                and getattr(request, param_name) is not None
            ):
                payload[param_name] = getattr(request, param_name)

        logger.debug(f"OpenAI formatted request: {payload}")
        return payload

    def convert_from_provider_response(
        self, provider_response: Any, original_request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        """Converts an OpenAI-specific response to a generic ChatCompletionResponse."""
        # Handle both dictionary and Pydantic model responses
        if isinstance(provider_response, dict):
            # Dictionary response
            if not provider_response.get("choices"):
                raise LLMIntegrationError("OpenAI response did not contain 'choices'.")

            choices_list = []
            for choice in provider_response["choices"]:
                message_data = choice["message"]

                # Handle tool_calls if present
                parsed_tool_calls = None
                if message_data.get("tool_calls"):
                    parsed_tool_calls = [
                        {
                            "id": tc["id"],
                            "type": tc["type"],
                            "function": {
                                "name": tc["function"]["name"],
                                "arguments": tc["function"]["arguments"],
                            },
                        }
                        for tc in message_data["tool_calls"]
                    ]

                choices_list.append(
                    ChatCompletionChoice(
                        message=Message(
                            role=message_data.get("role") or "assistant",
                            content=message_data.get("content")
                            or "",  # Ensure content is not None
                            tool_calls=parsed_tool_calls,
                        ),
                        finish_reason=choice.get("finish_reason"),
                        index=choice.get("index"),
                    )
                )

            usage_data = None
            if provider_response.get("usage"):
                usage_data = Usage(
                    prompt_tokens=provider_response["usage"]["prompt_tokens"],
                    completion_tokens=provider_response["usage"]["completion_tokens"],
                    total_tokens=provider_response["usage"]["total_tokens"],
                )

            return ChatCompletionResponse(
                id=provider_response.get("id"),
                choices=choices_list,
                created=provider_response.get("created"),
                model=provider_response.get(
                    "model"
                ),  # This is the model OpenAI actually used
                object="chat.completion",
                system_fingerprint=provider_response.get("system_fingerprint"),
                usage=usage_data,
            )
        else:
            # Pydantic model response
            if not provider_response.choices:
                raise LLMIntegrationError("OpenAI response did not contain 'choices'.")

            choices_list = []
            for choice in provider_response.choices:
                message_data = choice.message

                # Handle tool_calls if present
                parsed_tool_calls = None
                if message_data.tool_calls:
                    parsed_tool_calls = [
                        {
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in message_data.tool_calls
                    ]

                choices_list.append(
                    ChatCompletionChoice(
                        message=Message(
                            role=message_data.role or "assistant",
                            content=message_data.content
                            or "",  # Ensure content is not None
                            tool_calls=parsed_tool_calls,
                        ),
                        finish_reason=choice.finish_reason,
                        index=choice.index,
                    )
                )

            usage_data = None
            if provider_response.usage:
                usage_data = Usage(
                    prompt_tokens=provider_response.usage.prompt_tokens,
                    completion_tokens=provider_response.usage.completion_tokens,
                    total_tokens=provider_response.usage.total_tokens,
                )

            return ChatCompletionResponse(
                id=provider_response.id,
                choices=choices_list,
                created=provider_response.created,
                model=provider_response.model,  # This is the model OpenAI actually used
                object="chat.completion",
                system_fingerprint=provider_response.system_fingerprint,
                usage=usage_data,
            )

    def convert_from_provider_stream_chunk(
        self, provider_chunk: Any, original_request: ChatCompletionRequest
    ) -> ChatCompletionChunk:
        """Converts an OpenAI-specific streaming chunk to a generic ChatCompletionChunk."""
        # provider_chunk is a dictionary
        if not provider_chunk.get("choices"):
            # This can happen with preamble chunks or other events, decide how to handle
            # For now, let's create a mostly empty chunk if no choices, or raise error
            # It might be better to filter these out before they reach this conversion method.
            return ChatCompletionChunk(
                id=provider_chunk.get("id") or f"empty-chunk-{uuid.uuid4()}",
                choices=[],
                created=provider_chunk.get("created") or int(time.time()),
                model=provider_chunk.get("model") or original_request.model,
                object="chat.completion.chunk",
                system_fingerprint=provider_chunk.get("system_fingerprint"),
            )

        chunk_choices_list = []
        for choice in provider_chunk["choices"]:
            delta = choice.get("delta", {})
            parsed_tool_calls = None
            if delta.get("tool_calls"):
                # OpenAI streams tool calls incrementally. Need to handle assembly if function args are streamed.
                # For now, a direct mapping. Complex tool call streaming might need more state.
                parsed_tool_calls = []
                for tc_chunk in delta["tool_calls"]:
                    # tc_chunk is a dictionary with index, id, type, function (name, arguments)
                    # Arguments might be partial here.
                    parsed_tool_calls.append(
                        {
                            "index": tc_chunk.get("index"),  # Important for reassembly
                            "id": tc_chunk.get("id"),
                            "type": tc_chunk.get("type"),
                            "function": {
                                "name": tc_chunk.get("function", {}).get("name"),
                                "arguments": tc_chunk.get("function", {}).get(
                                    "arguments"
                                ),
                            },
                        }
                    )

            chunk_choices_list.append(
                ChatCompletionChunkChoice(
                    delta=ChoiceDelta(
                        content=delta.get("content"),
                        role=delta.get("role"),
                        tool_calls=parsed_tool_calls,
                    ),
                    finish_reason=choice.get("finish_reason"),
                    index=choice.get("index"),
                )
            )

        return ChatCompletionChunk(
            id=provider_chunk.get("id"),
            choices=chunk_choices_list,
            created=provider_chunk.get("created"),
            model=provider_chunk.get("model"),  # Model OpenAI used for this chunk
            object="chat.completion.chunk",
            system_fingerprint=provider_chunk.get("system_fingerprint"),
        )

    async def chat_completion(
        self, request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        """Processes a chat completion request and returns a standard response."""
        if request.stream:
            # This method is for non-streaming. The service layer should direct to stream_chat_completion.
            raise APIRequestError(
                "chat_completion called with stream=True. Use stream_chat_completion for streaming."
            )

        provider_payload = self.convert_to_provider_request(request)

        # Use the async APIClient from self.api_client
        raw_response = await self.api_client.make_openai_chat_completion_request(
            provider_payload, stream=False
        )
        return self.convert_from_provider_response(raw_response, request)

    async def stream_chat_completion(
        self, request: ChatCompletionRequest
    ) -> AsyncGenerator[ChatCompletionChunk, None]:
        """Processes a streaming chat completion request and yields standard chunks."""
        if not request.stream:
            # This method is for streaming.
            # Could technically call the non-streaming one and adapt, but less efficient.
            logger.warning(
                "stream_chat_completion called with stream=False. Forcing stream=True."
            )
            request.stream = True  # Ensure stream is true for the payload

        provider_payload = self.convert_to_provider_request(request)

        # Use the async APIClient from self.api_client
        stream_response = await self.api_client.make_openai_chat_completion_request(
            provider_payload, stream=True
        )

        async for provider_chunk in stream_response:
            # Process all chunks that have choices
            choices = provider_chunk.get("choices", [])
            if choices:
                # Only yield if the chunk has meaningful content (delta with content/role/tool_calls)
                # or is a final chunk (has finish_reason)
                choice = choices[0]
                if choice.get("delta") or choice.get("finish_reason"):
                    yield self.convert_from_provider_stream_chunk(
                        provider_chunk, request
                    )
            # else: (Optional: log discarded chunks)
            # logger.debug(f"Discarding OpenAI stream chunk without choices: {provider_chunk}")
