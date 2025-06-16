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


class MetaStrategy(BedrockAdapterStrategy):
    """Strategy for handling Meta Llama models on Bedrock."""

    def __init__(self, model_id: str, get_default_param_func: callable):
        super().__init__(model_id, get_default_param_func)
        logger.info(f"MetaStrategy initialized for model: {self.model_id}")

    def _format_messages_to_llama_prompt(
        self, messages: list[Message], system_prompt: str | None
    ) -> str:
        """Formats messages into Llama's expected prompt format with special tokens."""
        formatted_parts = []

        # Llama uses special tokens for chat format
        if system_prompt:
            formatted_parts.append(f"<s>[INST] <<SYS>>\n{system_prompt}\n<</SYS>>\n\n")
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
                formatted_parts.append(f" {msg.content} </s>")
            elif msg.role == "tool":
                logger.warning(
                    f"Meta Llama model {self.model_id} received tool role. Formatting as user message."
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
            raise UnsupportedFeatureError(
                "Meta Llama models do not support OpenAI-style 'tools' or 'tool_choice' parameters."
            )

        system_prompt, processed_messages = self._extract_system_prompt_and_messages(
            request.messages
        )
        prompt = self._format_messages_to_llama_prompt(
            processed_messages, system_prompt
        )

        # Meta Llama parameters
        max_gen_len = (
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
            "max_gen_len": max_gen_len,  # Llama uses max_gen_len instead of max_tokens
            "temperature": temperature,
        }

        # Add optional Llama-specific parameters
        llama_params = {
            "top_p": "top_p",
        }

        for generic_param, llama_param in llama_params.items():
            value = None
            if (
                hasattr(request, generic_param)
                and getattr(request, generic_param) is not None
            ):
                value = getattr(request, generic_param)
            elif generic_param in adapter_config_kwargs:
                value = adapter_config_kwargs[generic_param]

            if value is not None:
                payload[llama_param] = value

        logger.debug(f"Meta Llama formatted request payload: {payload}")
        return payload

    def parse_response(
        self, provider_response: dict[str, Any], original_request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        # Meta Llama response structure: {"generation": "...", "prompt_token_count": N, "generation_token_count": M, "stop_reason": "..."}
        output_text = provider_response.get("generation", "")
        stop_reason = provider_response.get("stop_reason", "unknown")
        finish_reason = self._map_finish_reason(stop_reason)

        message = Message(role="assistant", content=output_text)
        choice = ChatCompletionChoice(
            message=message,
            finish_reason=finish_reason,
            index=0,
        )

        # Meta Llama token usage
        prompt_tokens = provider_response.get("prompt_token_count", 0)
        completion_tokens = provider_response.get("generation_token_count", 0)
        total_tokens = prompt_tokens + completion_tokens

        return ChatCompletionResponse(
            id=f"bedrock-meta-{uuid.uuid4()}",
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
        # Meta Llama streaming format
        delta_content = None
        finish_reason = None

        if "generation" in chunk_data:
            delta_content = chunk_data["generation"]

        if "stop_reason" in chunk_data:
            finish_reason = self._map_finish_reason(chunk_data["stop_reason"])

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
        """Maps Meta Llama-specific finish reasons to OpenAI format."""
        mapping = {
            "stop": "stop",
            "length": "length",
            "max_gen_len": "length",
        }
        return mapping.get(provider_reason.lower(), provider_reason)
