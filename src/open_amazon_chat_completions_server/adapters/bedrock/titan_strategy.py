import logging
import time
import uuid
from typing import Any

from ...core.exceptions import (
    APIRequestError,
    LLMIntegrationError,
    UnsupportedFeatureError,
)
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


class TitanStrategy(BedrockAdapterStrategy):
    """Strategy for handling Amazon Titan Text models on Bedrock."""

    def __init__(self, model_id: str, get_default_param_func: callable):
        super().__init__(model_id, get_default_param_func)
        logger.info(f"TitanStrategy initialized for model: {self.model_id}")

    def _format_messages_to_titan_input_text(
        self, messages: list[Message], system_prompt: str | None
    ) -> str:
        """Formats a list of messages and an optional system prompt into Titan's single inputText string."""
        formatted_parts = []
        if system_prompt:
            # Titan doesn't have a dedicated system prompt field in the same way as Claude/OpenAI.
            # It's usually prepended to the inputText or handled by a specific 'system' parameter if the model variant supports it.
            # For now, prepending to the conversation.
            formatted_parts.append(f"System: {system_prompt}")

        for msg in messages:
            role_prefix = "User: "
            if msg.role == "assistant":
                role_prefix = "Bot: "  # Or "Assistant: "
            elif msg.role == "system":  # Already handled if it was the first message
                continue
            elif msg.role == "tool":
                # Titan does not have native tool support in the same way as OpenAI/Claude 3.
                # Tool interactions would need to be formatted as part of the text prompt.
                # For example, a tool response might be formatted as "User: [Tool Result for <tool_name>] <content>"
                logger.warning(
                    f"'tool' role for Titan model ({self.model_id}) will be formatted as plain text. Ensure content is a string."
                )
                role_prefix = f"User (Tool Response - {msg.name or 'unknown_tool'}): "

            content_str = msg.content
            if isinstance(msg.content, list):
                # Titan expects string content. If multimodal, it needs specific formatting not covered here.
                # For now, concatenate text parts if it's a list of text content blocks.
                logger.warning(
                    f"Titan model {self.model_id} received list content for role {msg.role}. Joining text parts. Multimodal content not directly supported."
                )
                content_str = " ".join(
                    item.get("text", "")
                    for item in msg.content
                    if isinstance(item, dict) and item.get("type") == "text"
                )

            formatted_parts.append(f"{role_prefix}{content_str}")

        # Titan expects a final prompt for the bot to continue, e.g., ending with "\nBot:"
        if formatted_parts and not formatted_parts[-1].strip().startswith("Bot:"):
            formatted_parts.append("Bot:")  # Prompt the bot for a response
        elif not formatted_parts:  # Handle empty messages case
            formatted_parts.append("Bot:")

        return "\n".join(formatted_parts)

    def prepare_request_payload(
        self, request: ChatCompletionRequest, adapter_config_kwargs: dict[str, Any]
    ) -> dict[str, Any]:
        if request.tools or request.tool_choice:
            raise UnsupportedFeatureError(
                "Amazon Titan models do not support OpenAI-style 'tools' or 'tool_choice' parameters directly through this adapter strategy."
            )

        system_prompt, processed_messages = self._extract_system_prompt_and_messages(
            request.messages
        )
        input_text = self._format_messages_to_titan_input_text(
            processed_messages, system_prompt
        )

        text_generation_config = {}
        max_tokens = (
            request.max_tokens
            if request.max_tokens is not None
            else self._get_default_param(
                "max_tokens", default_value=app_config.DEFAULT_MAX_TOKENS_TITAN
            )
        )
        if max_tokens is not None:
            text_generation_config["maxTokenCount"] = max_tokens
        else:
            raise APIRequestError(
                "maxTokenCount (max_tokens) is required for Titan models."
            )

        temperature = (
            request.temperature
            if request.temperature is not None
            else self._get_default_param(
                "temperature", default_value=app_config.DEFAULT_TEMPERATURE_TITAN
            )
        )
        if temperature is not None:
            text_generation_config["temperature"] = temperature

        # Handle other Titan-specific parameters
        # (e.g., topP, stopSequences)
        titan_specific_params = {
            "top_p": "topP",
            "stop_sequences": "stopSequences",  # Expects List[str]
        }
        for generic_param, titan_param in titan_specific_params.items():
            value = None
            # Check request attributes first
            if (
                hasattr(request, generic_param)
                and getattr(request, generic_param) is not None
            ):
                value = getattr(request, generic_param)
            # Then check adapter_config_kwargs passed during service call or adapter init
            elif (
                generic_param in adapter_config_kwargs
                and adapter_config_kwargs[generic_param] is not None
            ):
                value = adapter_config_kwargs[generic_param]

            if value is not None:
                text_generation_config[titan_param] = value

        payload = {
            "inputText": input_text,
            "textGenerationConfig": text_generation_config,
        }
        logger.debug(f"Titan formatted request payload: {payload}")
        return payload

    def parse_response(
        self, provider_response: dict[str, Any], original_request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        # Titan response structure: {"inputTextTokenCount": N, "results": [{"tokenCount": M, "outputText": "...", "completionReason": "..."}]}
        if (
            not provider_response.get("results")
            or not isinstance(provider_response["results"], list)
            or len(provider_response["results"]) == 0
        ):
            raise LLMIntegrationError("Titan response did not contain valid 'results'.")

        result = provider_response["results"][0]
        output_text = result.get("outputText", "")
        completion_reason_str = result.get("completionReason", "UNKNOWN")
        finish_reason = self._map_finish_reason(completion_reason_str)

        message = Message(role="assistant", content=output_text)
        choice = ChatCompletionChoice(
            message=message,
            finish_reason=finish_reason,
            index=0,  # Titan typically returns one result
        )

        prompt_tokens = provider_response.get("inputTextTokenCount", 0)
        completion_tokens = result.get("tokenCount", 0)
        total_tokens = prompt_tokens + completion_tokens

        return ChatCompletionResponse(
            id=f"bedrock-titan-{uuid.uuid4()}",  # Titan doesn't provide a response ID
            choices=[choice],
            created=int(time.time()),  # Bedrock doesn't provide created timestamp
            model=self.model_id,  # The requested model ID
            object="chat.completion",
            system_fingerprint=None,  # Not provided by Titan
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
        # Titan stream chunk structure (for text models like amazontitan-text-express-v1):
        # {"outputText": "...", "index": 0, "totalOutputTextTokenCount": N, "completionReason": "...", "amazon-bedrock-invocationMetrics": {...}}
        delta_content = chunk_data.get("outputText")
        finish_reason = None
        index = chunk_data.get("index", 0)  # Titan provides an index, typically 0

        if chunk_data.get("completionReason"):
            finish_reason = self._map_finish_reason(chunk_data["completionReason"])

        # Some Titan models might send metadata or empty chunks. Filter if delta_content is None and no finish_reason
        if delta_content is None and finish_reason is None:
            logger.debug(
                f"Skipping Titan stream chunk with no content or finish reason: {chunk_data}"
            )
            # Return an empty chunk to satisfy type, it might be filtered by caller
            return ChatCompletionChunk(
                id=response_id,
                choices=[],
                created=created_timestamp,
                model=original_request.model,
                object="chat.completion.chunk",
            )

        # Ensure delta_content is not None if there's no finish_reason yet (OpenAI spec)
        if delta_content is None and not finish_reason:
            delta_content = (
                ""  # Should not happen if filtered above, but as a safeguard
            )

        choice_delta = ChoiceDelta(
            content=delta_content,
            role="assistant" if delta_content is not None else None,
        )
        chunk_choice = ChatCompletionChunkChoice(
            delta=choice_delta, finish_reason=finish_reason, index=index
        )

        return ChatCompletionChunk(
            id=response_id,
            choices=[chunk_choice],
            created=created_timestamp,
            model=original_request.model,  # Should be the model requested
            object="chat.completion.chunk",
            system_fingerprint=None,  # Not provided by Titan
        )
