import logging
import time
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from ...core.exceptions import APIRequestError, ConfigurationError, ModelNotFoundError
from ...core.models import (
    ChatCompletionChunk,
    ChatCompletionRequest,
    ChatCompletionResponse,
)
from ...utils.api_client import APIClient
from ...utils.config_loader import app_config
from ..base_adapter import BaseLLMAdapter
from .ai21_strategy import AI21Strategy
from .bedrock_adapter_strategy_abc import BedrockAdapterStrategy
from .bedrock_models import (
    get_bedrock_model_id,
)  # To map generic names to specific Bedrock IDs
from .claude_strategy import ClaudeStrategy
from .cohere_strategy import CohereStrategy
from .meta_strategy import MetaStrategy
from .mistral_strategy import MistralStrategy
from .nova_strategy import NovaStrategy
from .stability_strategy import StabilityStrategy
from .titan_strategy import TitanStrategy
from .writer_strategy import WriterStrategy

logger = logging.getLogger(__name__)


class BedrockAdapter(BaseLLMAdapter):
    """Adapter for AWS Bedrock, using a strategy pattern for different model families."""

    def __init__(self, model_id: str, **kwargs):
        # Resolve the potentially generic model_id to a specific Bedrock model ID
        # The model_id passed here could be e.g. "claude-3-sonnet" or "anthropic.claude-3-sonnet-20240229-v1:0"
        self.specific_bedrock_model_id = get_bedrock_model_id(model_id)
        super().__init__(
            self.specific_bedrock_model_id, **kwargs
        )  # Initialize BaseLLMAdapter with the specific ID

        self.api_client = APIClient()
        if not (
            app_config.AWS_ACCESS_KEY_ID
            and app_config.AWS_SECRET_ACCESS_KEY
            and app_config.AWS_REGION
        ):
            # APIClient also checks this, but good to have an early check here too.
            raise ConfigurationError(
                "AWS credentials or region not configured for BedrockAdapter."
            )

        self.strategy = self._get_strategy(self.specific_bedrock_model_id)
        logger.info(
            f"BedrockAdapter initialized for model: {model_id} (resolved to {self.specific_bedrock_model_id}) using strategy: {self.strategy.__class__.__name__}"
        )

    def _get_strategy(self, bedrock_model_id: str) -> BedrockAdapterStrategy:
        # Pass the _get_default_param method from BaseLLMAdapter to the strategy
        get_param_func = self._get_default_param

        if bedrock_model_id.startswith("anthropic.claude"):
            return ClaudeStrategy(bedrock_model_id, get_param_func)
        elif bedrock_model_id.startswith("amazon.titan"):
            # Further checks can be done here if Titan image/text/embedding models need different strategies
            if "embed" in bedrock_model_id:
                raise ModelNotFoundError(
                    f"Bedrock model {bedrock_model_id} appears to be an embedding model. This adapter is for chat completions. Use an embedding-specific adapter."
                )
            return TitanStrategy(bedrock_model_id, get_param_func)
        elif bedrock_model_id.startswith("amazon.nova"):
            return NovaStrategy(bedrock_model_id, get_param_func)
        elif bedrock_model_id.startswith("ai21."):
            return AI21Strategy(bedrock_model_id, get_param_func)
        elif bedrock_model_id.startswith("cohere."):
            return CohereStrategy(bedrock_model_id, get_param_func)
        elif bedrock_model_id.startswith("meta."):
            return MetaStrategy(bedrock_model_id, get_param_func)
        elif bedrock_model_id.startswith("mistral."):
            return MistralStrategy(bedrock_model_id, get_param_func)
        elif bedrock_model_id.startswith("stability."):
            return StabilityStrategy(bedrock_model_id, get_param_func)
        elif bedrock_model_id.startswith("writer."):
            return WriterStrategy(bedrock_model_id, get_param_func)
        else:
            supported_prefixes = [
                "anthropic.claude",
                "amazon.titan",
                "amazon.nova",
                "ai21.",
                "cohere.",
                "meta.",
                "mistral.",
                "stability.",
                "writer.",
            ]
            logger.error(
                f"Unsupported Bedrock model ID: {bedrock_model_id}. Supported prefixes: {supported_prefixes}"
            )
            raise ModelNotFoundError(
                f"No strategy found for Bedrock model ID: {bedrock_model_id}. Supported model families: {', '.join(supported_prefixes)}"
            )

    def convert_to_provider_request(
        self, request: ChatCompletionRequest
    ) -> dict[str, Any]:
        """Delegates to the strategy to convert to Bedrock-specific request body."""
        # The specific_bedrock_model_id is what the APIClient and strategy will use.
        # The original request.model might be the generic name.
        # We ensure the strategy has the specific ID it needs.
        return self.strategy.prepare_request_payload(request, self.config_kwargs)

    def convert_from_provider_response(
        self, provider_response: dict[str, Any], original_request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        """Delegates to the strategy to parse Bedrock response."""
        return self.strategy.parse_response(provider_response, original_request)

    def convert_from_provider_stream_chunk(
        self,
        provider_chunk: dict[str, Any],
        original_request: ChatCompletionRequest,
        response_id: str,
        created_timestamp: int,
    ) -> ChatCompletionChunk:
        """Delegates to the strategy to handle a Bedrock stream chunk."""
        return self.strategy.handle_stream_chunk(
            provider_chunk, original_request, response_id, created_timestamp
        )

    async def chat_completion(
        self, request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        if request.stream:
            raise APIRequestError(
                "BedrockAdapter.chat_completion called with stream=True. Use stream_chat_completion for streaming."
            )

        # Ensure the model in the request (if generic) is resolved for the strategy, though strategy uses its own model_id.
        # The main specific_bedrock_model_id is used for the API call.
        provider_payload_body = self.convert_to_provider_request(request)

        raw_response_body = await self.api_client.make_bedrock_request(
            model_id=self.specific_bedrock_model_id,
            body=provider_payload_body,
            stream=False,
        )
        # raw_response_body is already a dict from APIClient
        return self.convert_from_provider_response(raw_response_body, request)

    async def stream_chat_completion(
        self, request: ChatCompletionRequest
    ) -> AsyncGenerator[ChatCompletionChunk, None]:
        if not request.stream:
            logger.warning(
                "BedrockAdapter.stream_chat_completion called with stream=False. Forcing stream=True."
            )
            request.stream = True

        provider_payload_body = self.convert_to_provider_request(request)

        # Generate a unique ID for this whole stream response for OpenAI-like chunk structure
        # and a consistent created timestamp for all chunks in this stream
        stream_response_id = (
            f"br-{self.strategy.__class__.__name__.lower()}-{uuid.uuid4()}"
        )
        stream_created_timestamp = int(time.time())

        # The APIClient's make_bedrock_request itself returns an AsyncGenerator for streams
        provider_stream = await self.api_client.make_bedrock_request(
            model_id=self.specific_bedrock_model_id,
            body=provider_payload_body,
            stream=True,
        )

        async for (
            provider_chunk_data
        ) in provider_stream:  # provider_chunk_data is a dict from bedrock stream
            # The strategy's handle_stream_chunk will convert this to ChatCompletionChunk
            # It might return empty/minimal chunks for metadata events from Bedrock stream; filter here if needed.
            converted_chunk = await self.strategy.handle_stream_chunk(
                provider_chunk_data,
                request,
                stream_response_id,
                stream_created_timestamp,
            )
            # Only yield if the chunk has choices (i.e., it's not just a metadata chunk we decided to ignore)
            if converted_chunk and converted_chunk.choices:
                yield converted_chunk
            elif (
                converted_chunk
                and converted_chunk.choices is not None
                and len(converted_chunk.choices) == 0
                and converted_chunk.id
            ):  # Empty chunk to signal stream start etc.
                # This handles cases where a strategy might return a shell chunk for stream start/stop that isn't filtered out internally.
                # OpenAI sometimes sends empty first/last chunks.
                # We could refine this to only yield if there's content OR a finish reason.
                pass  # For now, if choices is empty list, means strategy decided it's not a data chunk for OpenAI model.
                # logger.debug(f"BedrockAdapter: Skipping yield of empty converted chunk: {converted_chunk.id}")
