import logging
import time
import uuid
from typing import Any

from ...core.exceptions import APIRequestError, UnsupportedFeatureError
from ...core.models import (
    ChatCompletionChoice,
    ChatCompletionChunk,
    ChatCompletionChunkChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChoiceDelta,
    Message,
    Usage,
)
from .bedrock_adapter_strategy_abc import BedrockAdapterStrategy

logger = logging.getLogger(__name__)


class CohereStrategy(BedrockAdapterStrategy):
    """Strategy for handling Cohere Command models on Bedrock."""

    def __init__(self, model_id: str, get_default_param_func: callable):
        super().__init__(model_id, get_default_param_func)
        logger.info(f"CohereStrategy initialized for model: {self.model_id}")

    def _format_messages_to_cohere_prompt(
        self, messages: list[Message], system_prompt: str | None
    ) -> str:
        """Formats messages into Cohere's expected prompt format."""
        formatted_parts = []

        if system_prompt:
            formatted_parts.append(f"System: {system_prompt}")

        for msg in messages:
            if msg.role == "system":
                continue  # Already handled above
            elif msg.role == "user":
                formatted_parts.append(f"User: {msg.content}")
            elif msg.role == "assistant":
                formatted_parts.append(f"Chatbot: {msg.content}")
            elif msg.role == "tool":
                logger.warning(
                    f"Cohere model {self.model_id} received tool role. Formatting as user message."
                )
                formatted_parts.append(f"User (Tool Response): {msg.content}")

        # Add prompt for chatbot response
        if formatted_parts and not formatted_parts[-1].startswith("Chatbot:"):
            formatted_parts.append("Chatbot:")

        return "\n\n".join(formatted_parts)

    def prepare_request_payload(
        self, request: ChatCompletionRequest, adapter_config_kwargs: dict[str, Any]
    ) -> dict[str, Any]:
        if request.tools or request.tool_choice:
            raise UnsupportedFeatureError(
                "Cohere Command models do not support OpenAI-style 'tools' or 'tool_choice' parameters."
            )

        system_prompt, processed_messages = self._extract_system_prompt_and_messages(
            request.messages
        )
        prompt = self._format_messages_to_cohere_prompt(
            processed_messages, system_prompt
        )

        # Cohere Command parameters
        max_tokens = (
            request.max_tokens
            if request.max_tokens is not None
            else self._get_default_param("max_tokens", default_value=2048)
        )

        temperature = (
            request.temperature
            if request.temperature is not None
            else self._get_default_param("temperature", default_value=0.7)
        )

        payload = {
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        # Add optional Cohere-specific parameters
        cohere_params = {
            "top_p": "p",  # Cohere uses 'p' instead of 'top_p'
            "top_k": "k",  # Cohere uses 'k' instead of 'top_k'
            "stop_sequences": "stop_sequences",
        }

        for generic_param, cohere_param in cohere_params.items():
            value = None
            if (
                hasattr(request, generic_param)
                and getattr(request, generic_param) is not None
            ):
                value = getattr(request, generic_param)
            elif generic_param in adapter_config_kwargs:
                value = adapter_config_kwargs[generic_param]

            if value is not None:
                payload[cohere_param] = value

        logger.debug(f"Cohere formatted request payload: {payload}")
        return payload

    def parse_response(
        self, provider_response: dict[str, Any], original_request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        # Cohere response structure: {"generations": [{"text": "...", "finish_reason": "..."}]}
        generations = provider_response.get("generations", [])
        if not generations:
            raise APIRequestError("Cohere response did not contain valid generations.")

        generation = generations[0]
        output_text = generation.get("text", "")
        finish_reason_str = generation.get("finish_reason", "unknown")
        finish_reason = self._map_finish_reason(finish_reason_str)

        message = Message(role="assistant", content=output_text)
        choice = ChatCompletionChoice(
            message=message,
            finish_reason=finish_reason,
            index=0,
        )

        # Cohere token usage
        prompt_tokens = (
            provider_response.get("meta", {})
            .get("billed_units", {})
            .get("input_tokens", 0)
        )
        completion_tokens = (
            provider_response.get("meta", {})
            .get("billed_units", {})
            .get("output_tokens", 0)
        )
        total_tokens = prompt_tokens + completion_tokens

        return ChatCompletionResponse(
            id=f"bedrock-cohere-{uuid.uuid4()}",
            choices=[choice],
            created=int(time.time()),
            model=self.model_id,
            object="chat.completion",
            system_fingerprint=None,
            usage=Usage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            ),
        )

    async def handle_stream_chunk(
        self,
        chunk_data: dict[str, Any],
        original_request: ChatCompletionRequest,
        response_id: str,
        created_timestamp: int,
    ) -> ChatCompletionChunk:
        # Cohere streaming format
        delta_content = None
        finish_reason = None

        if "text" in chunk_data:
            delta_content = chunk_data["text"]

        if "finish_reason" in chunk_data:
            finish_reason = self._map_finish_reason(chunk_data["finish_reason"])

        choice_delta = ChoiceDelta(
            content=delta_content,
            role="assistant" if delta_content else None,
        )

        chunk_choice = ChatCompletionChunkChoice(
            index=0,
            delta=choice_delta,
            finish_reason=finish_reason,
        )

        return ChatCompletionChunk(
            id=response_id,
            choices=[chunk_choice],
            created=created_timestamp,
            model=self.model_id,
            object="chat.completion.chunk",
        )

    def _map_finish_reason(self, provider_reason: str) -> str:
        """Maps Cohere-specific finish reasons to OpenAI format."""
        mapping = {
            "COMPLETE": "stop",
            "MAX_TOKENS": "length",
            "ERROR": "stop",
            "ERROR_TOXIC": "content_filter",
        }
        return mapping.get(provider_reason.upper(), provider_reason)
