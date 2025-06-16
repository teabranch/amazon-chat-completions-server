import logging
import time
import uuid
from typing import Any

from ...core.exceptions import UnsupportedFeatureError
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


class NovaStrategy(BedrockAdapterStrategy):
    """Strategy for handling Amazon Nova models on Bedrock."""

    def __init__(self, model_id: str, get_default_param_func: callable):
        super().__init__(model_id, get_default_param_func)
        logger.info(f"NovaStrategy initialized for model: {self.model_id}")

    def _format_messages_to_nova_format(
        self, messages: list[Message], system_prompt: str | None
    ) -> list[dict[str, Any]]:
        """Formats messages into Nova's expected message format (similar to Claude)."""
        nova_messages = []

        for msg in messages:
            if msg.role == "system":
                continue  # System prompt handled separately
            elif msg.role in ["user", "assistant"]:
                nova_messages.append(
                    {
                        "role": msg.role,
                        "content": [{"text": msg.content}]
                        if isinstance(msg.content, str)
                        else msg.content,
                    }
                )
            elif msg.role == "tool":
                logger.warning(
                    f"Nova model {self.model_id} received tool role. Converting to user message."
                )
                nova_messages.append(
                    {
                        "role": "user",
                        "content": [{"text": f"Tool Response: {msg.content}"}],
                    }
                )

        return nova_messages

    def prepare_request_payload(
        self, request: ChatCompletionRequest, adapter_config_kwargs: dict[str, Any]
    ) -> dict[str, Any]:
        if request.tools or request.tool_choice:
            # Nova models may support tools in the future, but for now we'll disable
            raise UnsupportedFeatureError(
                "Amazon Nova models do not support OpenAI-style 'tools' or 'tool_choice' parameters in this implementation."
            )

        system_prompt, processed_messages = self._extract_system_prompt_and_messages(
            request.messages
        )
        nova_messages = self._format_messages_to_nova_format(
            processed_messages, system_prompt
        )

        # Nova parameters (similar to Claude but with Nova-specific naming)
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
            "messages": nova_messages,
            "maxTokens": max_tokens,  # Nova uses maxTokens
            "temperature": temperature,
        }

        # Add system prompt if present
        if system_prompt:
            payload["system"] = [{"text": system_prompt}]

        # Add optional Nova-specific parameters
        nova_params = {
            "top_p": "topP",
            "stop_sequences": "stopSequences",
        }

        for generic_param, nova_param in nova_params.items():
            value = None
            if (
                hasattr(request, generic_param)
                and getattr(request, generic_param) is not None
            ):
                value = getattr(request, generic_param)
            elif generic_param in adapter_config_kwargs:
                value = adapter_config_kwargs[generic_param]

            if value is not None:
                payload[nova_param] = value

        logger.debug(f"Nova formatted request payload: {payload}")
        return payload

    def parse_response(
        self, provider_response: dict[str, Any], original_request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        # Nova response structure (similar to Claude): {"output": {"message": {"content": [...], "role": "assistant"}}, "stopReason": "...", "usage": {...}}
        output = provider_response.get("output", {})
        message_data = output.get("message", {})
        content_blocks = message_data.get("content", [])

        # Extract text content
        full_text_content = ""
        for block in content_blocks:
            if block.get("type") == "text" or "text" in block:
                text_part = block.get("text", "")
                if text_part:
                    full_text_content += text_part

        stop_reason = provider_response.get("stopReason", "unknown")
        finish_reason = self._map_finish_reason(stop_reason)

        message = Message(role="assistant", content=full_text_content)
        choice = ChatCompletionChoice(
            message=message,
            finish_reason=finish_reason,
            index=0,
        )

        # Nova token usage
        usage_data = provider_response.get("usage", {})
        prompt_tokens = usage_data.get("inputTokens", 0)
        completion_tokens = usage_data.get("outputTokens", 0)
        total_tokens = prompt_tokens + completion_tokens

        return ChatCompletionResponse(
            id=f"bedrock-nova-{uuid.uuid4()}",
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
        # Nova streaming format (similar to Claude)
        delta_content = None
        finish_reason = None

        chunk_type = chunk_data.get("type")
        if chunk_type == "contentBlockDelta":
            delta_info = chunk_data.get("delta", {})
            if delta_info.get("type") == "textDelta":
                delta_content = delta_info.get("text", "")
        elif chunk_type == "messageStop":
            finish_reason = "stop"

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
        """Maps Nova-specific finish reasons to OpenAI format."""
        mapping = {
            "end_turn": "stop",
            "max_tokens": "length",
            "stop_sequence": "stop",
            "content_filtered": "content_filter",
        }
        return mapping.get(provider_reason.lower(), provider_reason)
