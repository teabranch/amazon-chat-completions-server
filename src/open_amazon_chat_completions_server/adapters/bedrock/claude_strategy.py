import logging
import time
import uuid
from typing import Any

from ...core.exceptions import APIRequestError
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
from ...utils.config_loader import app_config
from .bedrock_adapter_strategy_abc import BedrockAdapterStrategy

logger = logging.getLogger(__name__)


class ClaudeStrategy(BedrockAdapterStrategy):
    """Strategy for handling Anthropic Claude models on Bedrock."""

    def __init__(self, model_id: str, get_default_param_func: callable):
        super().__init__(model_id, get_default_param_func)
        self.anthropic_version = "bedrock-2023-05-31"  # Required for Claude 3 models
        logger.info(
            f"ClaudeStrategy initialized for model: {self.model_id} with anthropic_version: {self.anthropic_version}"
        )

    def prepare_request_payload(
        self, request: ChatCompletionRequest, adapter_config_kwargs: dict[str, Any]
    ) -> dict[str, Any]:
        system_prompt, processed_messages = self._extract_system_prompt_and_messages(
            request.messages
        )

        bedrock_messages = []
        for msg in processed_messages:
            if msg.role == "tool":
                if isinstance(msg.content, str):
                    bedrock_messages.append({"role": "user", "content": msg.content})
            elif msg.role == "assistant" and msg.tool_calls:
                content_blocks = []
                if msg.content:
                    content_blocks.append({"type": "text", "text": msg.content})
                for tool_call in msg.tool_calls:
                    content_blocks.append(
                        {
                            "type": "tool_use",
                            "id": tool_call["id"],
                            "name": tool_call["function"]["name"],
                            "input": tool_call["function"]["arguments"],
                        }
                    )
                bedrock_messages.append(
                    {"role": "assistant", "content": content_blocks}
                )
            elif msg.role == "user" and isinstance(msg.content, list):
                bedrock_messages.append({"role": msg.role, "content": msg.content})
            else:
                bedrock_messages.append({"role": msg.role, "content": msg.content})

        payload = {
            "anthropic_version": self.anthropic_version,
            "messages": bedrock_messages,
        }

        if system_prompt:
            payload["system"] = system_prompt

        max_tokens = (
            request.max_tokens
            if request.max_tokens is not None
            else self._get_default_param(
                "max_tokens", default_value=app_config.DEFAULT_MAX_TOKENS_CLAUDE
            )
        )
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        else:
            raise APIRequestError("max_tokens is required for Claude models.")

        temperature = (
            request.temperature
            if request.temperature is not None
            else self._get_default_param(
                "temperature", default_value=app_config.DEFAULT_TEMPERATURE_CLAUDE
            )
        )
        if temperature is not None:
            payload["temperature"] = temperature

        if request.tools:
            payload["tools"] = request.tools

        if request.tool_choice:
            payload["tool_choice"] = request.tool_choice

        return payload

    def parse_response(
        self, provider_response: dict[str, Any], original_request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        response_id = provider_response.get("id", f"bedrock-claude-{uuid.uuid4()}")
        model_used = provider_response.get("model", self.model_id)
        stop_reason = self._map_finish_reason(
            provider_response.get("stop_reason", "unknown")
        )

        output_content_blocks = provider_response.get("content", [])
        full_text_content = ""
        assistant_tool_calls = []

        for block in output_content_blocks:
            if block.get("type") == "text":
                text_part = block.get("text", "")
                if text_part:  # Only process non-empty text
                    full_text_content += text_part
            elif block.get("type") == "tool_use":
                tool_call_data = {
                    "id": block["id"],
                    "type": "function",
                    "function": {"name": block["name"], "arguments": block["input"]},
                }
                assistant_tool_calls.append(tool_call_data)
                if stop_reason != "tool_calls" and (
                    provider_response.get("stop_reason") == "tool_use"
                    or assistant_tool_calls
                    and stop_reason != "length"
                ):
                    stop_reason = "tool_calls"

        message = Message(
            role="assistant",
            content=full_text_content,
            tool_calls=assistant_tool_calls if assistant_tool_calls else None,
        )

        choice = ChatCompletionChoice(
            message=message, finish_reason=stop_reason, index=0
        )

        usage_data = provider_response.get("usage", {})
        prompt_tokens = usage_data.get("input_tokens", 0)
        completion_tokens = usage_data.get("output_tokens", 0)
        total_tokens = prompt_tokens + completion_tokens

        return ChatCompletionResponse(
            id=response_id,
            choices=[choice],
            created=int(time.time()),
            model=model_used,
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
        chunk_type = chunk_data.get("type")
        delta_content: str | None = None
        finish_reason: str | None = None
        delta_role: str | None = None
        chunk_tool_calls: list[dict[str, Any]] | None = None
        index = chunk_data.get("index", 0)

        if chunk_type == "content_block_delta":
            delta_info = chunk_data.get("delta", {})
            if (
                delta_info.get("type") == "text"
                or delta_info.get("type") == "text_delta"
            ):  # Handle both text and text_delta types
                delta_content = delta_info.get("text", "")
                delta_role = "assistant"
        elif chunk_type == "message_delta":
            delta_info = chunk_data.get("delta", {})
            stop_reason = delta_info.get("stop_reason")
            if stop_reason:
                finish_reason = self._map_finish_reason(stop_reason)
                delta_content = ""
                delta_role = "assistant"
        elif chunk_type == "message_stop":
            # Handle message_stop type for final chunk
            finish_reason = "stop"
            delta_content = ""
            delta_role = "assistant"

        # Create choice delta
        choice_delta_params = {}
        if delta_content is not None:
            choice_delta_params["content"] = delta_content
        if delta_role:
            choice_delta_params["role"] = delta_role
        if chunk_tool_calls:
            choice_delta_params["tool_calls"] = chunk_tool_calls

        choice_delta = ChoiceDelta(**choice_delta_params)

        chunk_choice = ChatCompletionChunkChoice(
            delta=choice_delta, finish_reason=finish_reason, index=index
        )

        return ChatCompletionChunk(
            id=response_id,
            choices=[chunk_choice],
            created=created_timestamp,
            model=original_request.model,
            object="chat.completion.chunk",
        )
