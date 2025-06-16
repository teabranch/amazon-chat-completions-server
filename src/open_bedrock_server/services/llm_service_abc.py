from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator

from ..core.models import ChatCompletionChunk, ChatCompletionResponse, Message


class AbstractLLMService(ABC):
    """Abstract base class for a consistent LLM service interface."""

    @abstractmethod
    async def chat_completion(
        self,
        messages: list[Message],
        model_id: str
        | None = None,  # Model ID might be inherent to the service instance or passed per call
        stream: bool = False,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs,  # For other provider-specific parameters
    ) -> ChatCompletionResponse | AsyncGenerator[ChatCompletionChunk, None]:
        """
        Sends a chat completion request to the LLM.

        Args:
            messages: A list of Message objects representing the conversation history.
            model_id: The specific model to use (if not inherent to the service).
            stream: Whether to stream the response.
            temperature: The sampling temperature.
            max_tokens: The maximum number of tokens to generate.
            **kwargs: Additional provider-specific parameters.

        Returns:
            If stream is False, returns a ChatCompletionResponse object.
            If stream is True, returns an AsyncGenerator yielding ChatCompletionChunk objects.
        """
        pass

    # Potentially add other common LLM operations here, e.g.:
    # @abstractmethod
    # async def generate_embeddings(self, texts: List[str], model_id: Optional[str] = None, **kwargs) -> Any:
    #     pass
