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


class MistralStrategy(BedrockAdapterStrategy):
    """Strategy for handling Mistral models on Bedrock."""

    def __init__(self, model_id: str, get_default_param_func: callable):
        super().__init__(model_id, get_default_param_func)
        logger.info(f"MistralStrategy initialized for model: {self.model_id}")

    def _format_messages_to_mistral_prompt(
        self, messages: list[Message], system_prompt: str | None
    ) -> str:
        """Formats messages into Mistral's expected prompt format with special tokens."""
        formatted_parts = []

        # Mistral uses special tokens similar to Llama but with different format
        if system_prompt:
            formatted_parts.append(f"<s>[INST] {system_prompt}\n\n")
        else:
            formatted_parts.append("<s>[INST] ")

        conversation_started = False
        for _i, msg in enumerate(messages):
            if msg.role == "system":
                continue  # Already handled above
            elif msg.role == "user":
                if conversation_started:
                    formatted_parts.append(f"<s>[INST] {msg.content} [/INST]")
                else:
                    formatted_parts.append(f"{msg.content} [/INST]")
                    conversation_started = True
            elif msg.role == "assistant":
                formatted_parts.append(f" {msg.content}</s>")
            elif msg.role == "tool":
                logger.warning(
                    f"Mistral model {self.model_id} received tool role. Formatting as user message."
                )
                if conversation_started:
                    formatted_parts.append(
                        f"<s>[INST] Tool Response: {msg.content} [/INST]"
                    )
                else:
                    formatted_parts.append(f"Tool Response: {msg.content} [/INST]")
                    conversation_started = True

        # If the last message wasn't from assistant, we need to prompt for response
        if messages and messages[-1].role != "assistant":
            if not formatted_parts[-1].endswith("[/INST]"):
                formatted_parts.append(" [/INST]")

        return "".join(formatted_parts)

    def prepare_request_payload(
        self, request: ChatCompletionRequest, adapter_config_kwargs: dict[str, Any]
    ) -> dict[str, Any]:
        if request.tools or request.tool_choice:
            # Some Mistral models support tools, but for simplicity we'll disable for now
            raise UnsupportedFeatureError(
                "Mistral models do not support OpenAI-style 'tools' or 'tool_choice' parameters in this implementation."
            )

        system_prompt, processed_messages = self._extract_system_prompt_and_messages(
            request.messages
        )
        prompt = self._format_messages_to_mistral_prompt(
            processed_messages, system_prompt
        )

        # Mistral parameters
        max_tokens = (
            request.max_tokens
            if request.max_tokens is not None
            else self._get_default_param("max_tokens", default_value=4096)
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

        # Add optional Mistral-specific parameters
        mistral_params = {
            "top_p": "top_p",
            "top_k": "top_k",
            "stop_sequences": "stop",
        }

        for generic_param, mistral_param in mistral_params.items():
            value = None
            if (
                hasattr(request, generic_param)
                and getattr(request, generic_param) is not None
            ):
                value = getattr(request, generic_param)
            elif generic_param in adapter_config_kwargs:
                value = adapter_config_kwargs[generic_param]

            if value is not None:
                payload[mistral_param] = value

        logger.debug(f"Mistral formatted request payload: {payload}")
        return payload

    def parse_response(
        self, provider_response: dict[str, Any], original_request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        # Mistral response structure: {"outputs": [{"text": "...", "stop_reason": "..."}]}
        outputs = provider_response.get("outputs", [])
        if not outputs:
            raise APIRequestError("Mistral response did not contain valid outputs.")

        output = outputs[0]
        output_text = output.get("text", "")
        stop_reason = output.get("stop_reason", "unknown")
        finish_reason = self._map_finish_reason(stop_reason)

        message = Message(role="assistant", content=output_text)
        choice = ChatCompletionChoice(
            message=message,
            finish_reason=finish_reason,
            index=0,
        )

        # Mistral token usage
        prompt_tokens = provider_response.get("usage", {}).get("prompt_tokens", 0)
        completion_tokens = provider_response.get("usage", {}).get(
            "completion_tokens", 0
        )
        total_tokens = prompt_tokens + completion_tokens

        return ChatCompletionResponse(
            id=f"bedrock-mistral-{uuid.uuid4()}",
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
        # Mistral streaming format
        delta_content = None
        finish_reason = None

        if "outputs" in chunk_data and chunk_data["outputs"]:
            output = chunk_data["outputs"][0]
            delta_content = output.get("text", "")

            if "stop_reason" in output:
                finish_reason = self._map_finish_reason(output["stop_reason"])

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
        """Maps Mistral-specific finish reasons to OpenAI format."""
        mapping = {
            "stop": "stop",
            "length": "length",
            "model_length": "length",
        }
        return mapping.get(provider_reason.lower(), provider_reason)
