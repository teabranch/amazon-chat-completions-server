# Core Modules (`src.llm_integrations.core`)

The `core` module forms the foundation of the library, providing essential data structures and custom exceptions.

## 1. Models (`core.models.py`)

This file defines the Pydantic models that represent the standardized data interchange format within the library, primarily mirroring OpenAI's Chat Completions API structure.

Key models include:

* **`Message`**: Represents a single message in a conversation, with `role` (system, user, assistant, tool) and `content`.
   * Supports `name` for tool calls and `tool_call_id` / `tool_calls` for tool interactions.
   * `content` can be a string or a list of content blocks for multimodal inputs (as per OpenAI and Claude 3).

* **`ChatCompletionRequest`**: The standardized request object passed to the `AbstractLLMService`.
   * Contains `messages`, `model` (generic model identifier), `temperature`, `max_tokens`, `stream`, `tools`, `tool_choice`, and other common parameters.

* **`ChatCompletionResponse`**: The standardized response object.
   * Includes `id`, `choices` (list of `ChatCompletionChoice`), `created` timestamp, `model` used, and `usage` statistics.

* __`ChatCompletionChoice`__: Represents one of the possible completions, containing a `Message` object and `finish_reason`.
* **`ChatCompletionChunk`**: Used for streaming responses.
   * Contains `id`, `choices` (list of `ChatCompletionChunkChoice`), `created`, `model`.

* __`ChatCompletionChunkChoice`__: A single choice within a stream chunk, containing `delta` (the incremental change) and `finish_reason` (if applicable).
* __`ChoiceDelta`__: The actual incremental content in a stream, with optional `role`, `content`, or `tool_calls`.
* __`Usage`__: Token usage information (`prompt_tokens`, `completion_tokens`, `total_tokens`).

The file also includes illustrative Pydantic models for Bedrock request/response bodies (e.g., `BedrockClaudeRequestBody`, `BedrockTitanRequestBody`). These are primarily for reference as the detailed mapping is handled within the adapter strategies. The adapters convert to/from these provider-specific structures and the core `ChatCompletion...` models.

Using Pydantic ensures type validation, serialization, and clear data contracts throughout the application.

## 2. Exceptions (`core.exceptions.py`)

This file defines a hierarchy of custom exceptions that inherit from a base `LLMIntegrationError`. This allows for more granular error handling by the client application.

Key exceptions:

* **`LLMIntegrationError`**: Base class for all library-specific errors.
* **`ConfigurationError`**: For issues related to missing or invalid configuration (e.g., API keys).
* **`APIConnectionError`**: For network or connectivity problems when trying to reach the LLM API.
* **`APIRequestError`**: For errors due to malformed requests or invalid parameters sent to the LLM API (e.g., HTTP 400).
* **`AuthenticationError`**: For failures related to API key validation or permissions (e.g., HTTP 401, 403).
* **`RateLimitError`**: When API rate limits are exceeded (e.g., HTTP 429).
* **`APIServerError`**: For errors originating from the LLM provider's servers (e.g., HTTP 5xx).
* **`ModelNotFoundError`**: If a specified model ID is not found or not supported by the chosen provider or adapter.
* **`StreamingError`**: For errors specifically related to processing or converting streaming responses.
* **`UnsupportedFeatureError`**: When a requested feature or parameter is not supported by the target model or provider (e.g., trying to use tools with a model that doesn't support them).

These custom exceptions help in distinguishing library-specific issues from generic Python errors and allow client code to implement more targeted error recovery or reporting strategies.