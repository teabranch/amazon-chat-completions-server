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


class AI21Strategy(BedrockAdapterStrategy):
    """Strategy for handling AI21 Jamba models on Bedrock."""

    def __init__(self, model_id: str, get_default_param_func: callable):
        super().__init__(model_id, get_default_param_func)
        logger.info(f"AI21Strategy initialized for model: {self.model_id}")

    def _format_messages_to_ai21_prompt(
        self, messages: list[Message], system_prompt: str | None
    ) -> str:
        """Formats messages into AI21's expected prompt format."""
        formatted_parts = []

        if system_prompt:
            formatted_parts.append(f"System: {system_prompt}")

        for msg in messages:
            if msg.role == "system":
                continue  # Already handled above
            elif msg.role == "user":
                formatted_parts.append(f"User: {msg.content}")
            elif msg.role == "assistant":
                formatted_parts.append(f"Assistant: {msg.content}")
            elif msg.role == "tool":
                logger.warning(
                    f"AI21 model {self.model_id} received tool role. Formatting as user message."
                )
                formatted_parts.append(f"User (Tool Response): {msg.content}")

        # Add prompt for assistant response
        if formatted_parts and not formatted_parts[-1].startswith("Assistant:"):
            formatted_parts.append("Assistant:")

        return "\n\n".join(formatted_parts)

    def prepare_request_payload(
        self, request: ChatCompletionRequest, adapter_config_kwargs: dict[str, Any]
    ) -> dict[str, Any]:
        if request.tools or request.tool_choice:
            raise UnsupportedFeatureError(
                "AI21 Jamba models do not support OpenAI-style 'tools' or 'tool_choice' parameters."
            )

        system_prompt, processed_messages = self._extract_system_prompt_and_messages(
            request.messages
        )
        prompt = self._format_messages_to_ai21_prompt(processed_messages, system_prompt)

        # AI21 Jamba parameters
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
            "maxTokens": max_tokens,
            "temperature": temperature,
        }

        # Add optional AI21-specific parameters
        ai21_params = {
            "top_p": "topP",
            "stop_sequences": "stopSequences",
        }

        for generic_param, ai21_param in ai21_params.items():
            value = None
            if (
                hasattr(request, generic_param)
                and getattr(request, generic_param) is not None
            ):
                value = getattr(request, generic_param)
            elif generic_param in adapter_config_kwargs:
                value = adapter_config_kwargs[generic_param]

            if value is not None:
                payload[ai21_param] = value

        logger.debug(f"AI21 formatted request payload: {payload}")
        return payload

    def parse_response(
        self, provider_response: dict[str, Any], original_request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        # AI21 response structure: {"completions": [{"data": {"text": "..."}, "finishReason": {"reason": "..."}}]}
        completions = provider_response.get("completions", [])
        if not completions:
            raise APIRequestError("AI21 response did not contain valid completions.")

        completion = completions[0]
        completion_data = completion.get("data", {})
        output_text = completion_data.get("text", "")

        finish_reason_data = completion.get("finishReason", {})
        finish_reason_str = finish_reason_data.get("reason", "unknown")
        finish_reason = self._map_finish_reason(finish_reason_str)

        message = Message(role="assistant", content=output_text)
        choice = ChatCompletionChoice(
            message=message,
            finish_reason=finish_reason,
            index=0,
        )

        # AI21 doesn't always provide token counts in the same format
        prompt_tokens = provider_response.get("prompt", {}).get("tokens", 0)
        completion_tokens = completion_data.get("tokens", 0)
        total_tokens = prompt_tokens + completion_tokens

        return ChatCompletionResponse(
            id=f"bedrock-ai21-{uuid.uuid4()}",
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
        # AI21 streaming format
        delta_content = None
        finish_reason = None

        if "completion" in chunk_data:
            completion = chunk_data["completion"]
            if "data" in completion:
                delta_content = completion["data"].get("text", "")

            if "finishReason" in completion:
                finish_reason_data = completion["finishReason"]
                if finish_reason_data.get("reason"):
                    finish_reason = self._map_finish_reason(
                        finish_reason_data["reason"]
                    )

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
        """Maps AI21-specific finish reasons to OpenAI format."""
        mapping = {
            "endoftext": "stop",
            "length": "length",
            "stop": "stop",
        }
        return mapping.get(provider_reason.lower(), provider_reason)
