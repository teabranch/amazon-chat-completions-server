# Adapters (`src.amazon_chat_completions_server.adapters`)

The adapter layer is responsible for bridging the gap between the library's standardized interface (`ChatCompletionRequest`, `ChatCompletionResponse`) and the specific APIs of different LLM providers.

## 1. Base Adapter (`adapters.base_adapter.BaseLLMAdapter`)

This abstract base class (ABC) defines the contract that all provider-specific adapters must implement. It ensures that each adapter provides a consistent set of methods for the service layer to use.

Key abstract methods:

*   `__init__(self, model_id: str, **kwargs)`: Initializes the adapter with a specific model ID and any other configuration.
*   `convert_to_provider_request(self, request: ChatCompletionRequest) -> Any`: Converts the library's standard `ChatCompletionRequest` into the format expected by the provider's API.
*   `convert_from_provider_response(self, provider_response: Any, original_request: ChatCompletionRequest) -> ChatCompletionResponse`: Converts the raw response from the provider into the library's standard `ChatCompletionResponse`.
*   `chat_completion(self, request: ChatCompletionRequest) -> ChatCompletionResponse`: Processes a non-streaming chat completion request.
*   `convert_from_provider_stream_chunk(self, provider_chunk: Any, original_request: ChatCompletionRequest, response_id: str, created_timestamp: int) -> ChatCompletionChunk`: Converts a raw streaming chunk from the provider into the library's standard `ChatCompletionChunk`.
*   `stream_chat_completion(self, request: ChatCompletionRequest) -> AsyncGenerator[ChatCompletionChunk, None]`: Processes a streaming chat completion request.

It also includes a helper method `_get_default_param` to fetch default parameter values (like temperature, max_tokens) from the adapter's initialization arguments or the global application configuration (`app_config`).

## 2. OpenAI Adapter (`adapters.openai_adapter.OpenAIAdapter`)

This concrete adapter implements `BaseLLMAdapter` for interacting with OpenAI's Chat Completions API.

*   **Request Conversion:** Maps the standard `ChatCompletionRequest` (including messages, model, temperature, max_tokens, stream, tools, tool_choice) to the JSON payload expected by the OpenAI API.
*   **Response Conversion:** Parses the `openai.types.chat.ChatCompletion` object (or `openai.types.chat.ChatCompletionChunk` for streams) into the library's `ChatCompletionResponse` (or `ChatCompletionChunk`).
*   It directly uses the `APIClient` to make calls to the OpenAI API.
*   Handles OpenAI-specific parameters and tool usage formatting.

See [OpenAI Adapter Details](openai_adapter.md) for more.

## 3. Bedrock Adapter (`adapters.bedrock.bedrock_adapter.BedrockAdapter`)

This adapter implements `BaseLLMAdapter` for AWS Bedrock. Due to the variety of model APIs available through Bedrock, this adapter utilizes the **Strategy Pattern** to handle different model families.

*   **Model ID Resolution:** Uses `get_bedrock_model_id` from `bedrock_models.py` to map a generic model name (e.g., "us.anthropic.claude-3-5-haiku-20241022-v1:0") to its specific Bedrock model ID (e.g., "anthropic.us.anthropic.claude-3-5-haiku-20241022-v1:0-20240307-v1:0").
*   **Strategy Selection:** Based on the Bedrock model ID prefix (e.g., `anthropic.claude`, `amazon.titan`), it instantiates the appropriate model strategy (e.g., `ClaudeStrategy`, `TitanStrategy`).
*   **Delegation:** All conversion and processing logic (request/response mapping, stream handling) is delegated to the selected strategy.
*   Uses the `APIClient` to make calls to the Bedrock `invoke_model` or `invoke_model_with_response_stream` endpoints.

See [Bedrock Adapter Details](bedrock_adapter.md) for more.

### 3.1. Bedrock Model Strategies (`adapters.bedrock.*_strategy.py`)

These strategies implement the `BedrockAdapterStrategy` ABC (`adapters.bedrock.bedrock_adapter_strategy_abc.BedrockAdapterStrategy`).

*   **`BedrockAdapterStrategy` (ABC):** Defines the contract for Bedrock model strategies:
    *   `prepare_request_payload(...)`: Creates the JSON body for `invoke_model`.
    *   `parse_response(...)`: Parses the JSON response from `invoke_model`.
    *   `handle_stream_chunk(...)`: Processes individual chunks from `invoke_model_with_response_stream`.
    *   Includes helper methods like `_map_finish_reason` and `_extract_system_prompt_and_messages`.

*   **`ClaudeStrategy` (`adapters.bedrock.claude_strategy.ClaudeStrategy`):**
    *   Handles Anthropic Claude models (e.g., Claude 3 Sonnet, Haiku, Opus).
    *   Prepares requests according to Claude's Messages API format (including `anthropic_version`, `messages` array, `system` prompt, `tools`, `tool_choice`).
    *   Parses Claude's response structure, including text content and tool use blocks.
    *   Manages Claude-specific streaming events (`message_start`, `content_block_delta`, `message_delta`, `message_stop`, etc.).

*   **`TitanStrategy` (`adapters.bedrock.titan_strategy.TitanStrategy`):**
    *   Handles Amazon Titan Text models (e.g., Titan Text Express, Lite).
    *   Formats the conversation history (including any system prompt) into a single `inputText` string with appropriate role indicators (e.g., "User:", "Bot:").
    *   Prepares the `textGenerationConfig` with parameters like `maxTokenCount`, `temperature`.
    *   Parses Titan's response ( `results` array with `outputText` and `completionReason`).
    *   Handles Titan's simpler streaming format (chunks typically contain `outputText`).
    *   Notes that Titan models (via this strategy) do not support OpenAI-style direct tool parameters.

Adding support for other Bedrock model families (like Llama, Cohere, or Mistral on Bedrock) would involve creating a new strategy class implementing `BedrockAdapterStrategy` and updating the `_get_strategy` method in `BedrockAdapter`.

### 3.2 Bedrock Model Mapping (`adapters.bedrock.bedrock_models.py`)

*   Provides `BEDROCK_MODEL_ID_MAP` to translate user-friendly names (e.g., `claude-3-sonnet`) to the full Bedrock model identifiers.
*   Includes helper functions like `get_claude_default_params()` or `get_titan_default_params()` (though the primary default parameter handling is now in `BaseLLMAdapter._get_default_param` using `app_config`).
*   `SUPPORTED_BEDROCK_MODELS` list for validation. 