from abc import ABC, abstractmethod
from typing import Any

from ...core.models import (
    ChatCompletionChunk,
    ChatCompletionRequest,
    ChatCompletionResponse,
    Message,
)


class BedrockAdapterStrategy(ABC):
    """Abstract base class for Bedrock model-specific strategies."""

    @abstractmethod
    def __init__(self, model_id: str, get_default_param_func: callable):
        self.model_id = model_id
        self._get_default_param = get_default_param_func

    @abstractmethod
    def prepare_request_payload(
        self, request: ChatCompletionRequest, adapter_config_kwargs: dict[str, Any]
    ) -> dict[str, Any]:
        """Prepares the model-specific request body for Bedrock."""
        pass

    @abstractmethod
    def parse_response(
        self, provider_response: dict[str, Any], original_request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        """Parses the Bedrock model-specific response into a standard ChatCompletionResponse."""
        pass

    @abstractmethod
    async def handle_stream_chunk(
        self,
        chunk_data: dict[str, Any],
        original_request: ChatCompletionRequest,
        response_id: str,
        created_timestamp: int,
    ) -> ChatCompletionChunk:
        """Handles a single streaming chunk from Bedrock and converts it to ChatCompletionChunk."""
        pass

    def _map_finish_reason(self, provider_reason: str) -> str:
        """Maps provider-specific finish/stop reasons to OpenAI-like reasons."""
        # Default mapping, can be overridden by specific strategies
        mapping = {
            # Claude
            "end_turn": "stop",
            "max_tokens": "length",
            "stop_sequence": "stop",
            # Titan
            "FINISH": "stop",
            "LENGTH": "length",
            "CONTENT_FILTERED": "content_filter",  # Or a custom one
            # Add other common reasons from different models
        }
        return mapping.get(
            provider_reason, provider_reason
        )  # Return original if not in map

    def _extract_system_prompt_and_messages(
        self, messages: list[Message]
    ) -> tuple[str | None, list[Message]]:
        """Extracts and combines all system messages, and returns remaining messages."""
        system_prompts = []
        processed_messages = []

        for message in messages:
            if message.role == "system":
                content = message.content
                if not isinstance(content, str):
                    # Handle cases where system prompt might be complex
                    if isinstance(content, list) and all(
                        isinstance(item, dict) and item.get("type") == "text"
                        for item in content
                    ):
                        content = " ".join(item.get("text", "") for item in content)
                    else:
                        content = str(content)
                system_prompts.append(content)
            else:
                processed_messages.append(message)

        system_prompt = "\n".join(system_prompts) if system_prompts else None
        return system_prompt, processed_messages
