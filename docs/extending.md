# Extending the Library

This library is designed to be extensible, allowing for the addition of new LLM models, new strategies for existing Bedrock models, or even support for entirely new LLM providers.

## 1. Adding a New Bedrock Model Strategy

If AWS Bedrock adds support for a new family of models (e.g., a new provider or a new Amazon model with a distinct API) that isn't covered by existing strategies (`ClaudeStrategy`, `TitanStrategy`), you can add a new strategy.

**Steps:**

1.  **Create a New Strategy Class:**
    *   In `src/amazon_chat_completions_server/adapters/bedrock/`, create a new Python file (e.g., `new_model_strategy.py`).
    *   Define a class (e.g., `NewModelStrategy`) that inherits from `BedrockAdapterStrategy` (from `bedrock_adapter_strategy_abc.py`).
    *   Implement all the abstract methods:
        *   `__init__(self, model_id: str, get_default_param_func: callable)`
        *   `prepare_request_payload(self, request: ChatCompletionRequest, adapter_config_kwargs: Dict[str, Any]) -> Dict[str, Any]`: Convert the standard `ChatCompletionRequest` to the new model's specific input JSON body.
        *   `parse_response(self, provider_response: Dict[str, Any], original_request: ChatCompletionRequest) -> ChatCompletionResponse`: Parse the new model's JSON response into a standard `ChatCompletionResponse`.
        *   `handle_stream_chunk(self, chunk_data: Dict[str, Any], original_request: ChatCompletionRequest, response_id: str, created_timestamp: int) -> ChatCompletionChunk`: Process a streaming chunk from the new model and convert it to a `ChatCompletionChunk`.
    *   You may need to override `_map_finish_reason` if the model uses different stop reason codes.

2.  **Update `BedrockAdapter`:**
    *   Open `src/amazon_chat_completions_server/adapters/bedrock/bedrock_adapter.py`.
    *   Import your new strategy: `from .new_model_strategy import NewModelStrategy`.
    *   In the `_get_strategy` method, add a condition to instantiate your new strategy if the `bedrock_model_id` matches the prefix for the new model family.
        ```python
        # In BedrockAdapter._get_strategy(...)
        elif bedrock_model_id.startswith("prefix.for.newmodel"):
            return NewModelStrategy(bedrock_model_id, get_param_func)
        ```

3.  **Update Model Mapping (Optional but Recommended):**
    *   Open `src/amazon_chat_completions_server/adapters/bedrock/bedrock_models.py`.
    *   Add any user-friendly generic names for the new models to the `BEDROCK_MODEL_ID_MAP`.
    *   Add the new model prefixes/IDs to `SUPPORTED_BEDROCK_MODELS` if you want them to be listed as supported.

4.  **Add Default Configuration (Optional):**
    *   In `src/amazon_chat_completions_server/utils/config_loader.py` (`AppConfig` class) and `.env.example`, add any default parameters specific to this new model family (e.g., `DEFAULT_MAX_TOKENS_NEWMODEL`, `DEFAULT_TEMPERATURE_NEWMODEL`). The `_get_default_param` method in `BaseLLMAdapter` will then be able to pick these up if the provider prefix in its logic is updated or generalized.

5.  **Testing:**
    *   Write unit tests for your new strategy, mocking Bedrock API responses.
    *   Add integration tests using the `LLMServiceFactory` to ensure end-to-end functionality with your new model (mocking the actual Bedrock calls in `APIClient`).

### Future Enhancement: Dynamic Bedrock Model Discovery

A potential future enhancement for `BedrockAdapter` and `bedrock_models.py` could be to dynamically query the AWS Bedrock API (e.g., using `list_foundation_models`) to discover available models at runtime. This would reduce the need for manual updates to `BEDROCK_MODEL_ID_MAP`.

Considerations for dynamic discovery:
*   **Pros:** Always up-to-date with newly available Bedrock models.
*   **Cons:** Adds startup latency, requires careful filtering to only include compatible chat models, and might list models for which a strategy hasn't been implemented yet.
The current static map provides a curated and predictable list of supported models.

## 2. Adding Support for a New LLM Provider

If you want to add support for an entirely new LLM provider (e.g., Google Gemini, Cohere directly, etc.):

1.  **Create a New Adapter:**
    *   In `src/amazon_chat_completions_server/adapters/`, create a new Python file (e.g., `newprovider_adapter.py`).
    *   Define a class (e.g., `NewProviderAdapter`) that inherits from `BaseLLMAdapter`.
    *   Implement all the abstract methods from `BaseLLMAdapter` to handle request/response conversion and (a)synchronous chat completions for the new provider.
    *   This adapter will likely need to interact with the `APIClient` or use its own client library for the new provider.

2.  **Update `APIClient` (If Necessary):**
    *   If the new provider requires specific API call logic, authentication, or error handling not covered by generic HTTP calls, you might need to add new methods or configurations to `src/amazon_chat_completions_server/utils/api_client.py`.
    *   Add any new provider-specific exceptions to `core.exceptions.py` and map them in the `APIClient`.

3.  **Create a New Concrete Service:**
    *   In `src/amazon_chat_completions_server/services/concrete_services.py`, define a new service class (e.g., `NewProviderService`) that inherits from `ConcreteLLMService` (or directly from `AbstractLLMService` if `ConcreteLLMService` is not suitable).
        ```python
        # In concrete_services.py
        class NewProviderService(ConcreteLLMService):
            def __init__(self, adapter: BaseLLMAdapter):
                super().__init__(adapter)
                if not type(adapter).__name__ == 'NewProviderAdapter':
                    raise LLMIntegrationError("NewProviderService must be initialized with a NewProviderAdapter.")
                self.provider_name = "newprovider"
        ```

4.  **Update `LLMServiceFactory`:**
    *   Open `src/amazon_chat_completions_server/services/llm_service_factory.py`.
    *   Import your new adapter and service.
    *   In the `get_service` method, add a new condition for `provider_name`:
        ```python
        # In LLMServiceFactory.get_service(...)
        elif provider_name == "newprovider":
            if not model_id: # Or if model_id is differently used by this provider
                raise ModelNotFoundError("model_id is required for NewProvider.")
            from .concrete_services import NewProviderService # Local import
            adapter_instance = NewProviderAdapter(model_id=model_id, **kwargs)
            service_instance = NewProviderService(adapter=adapter_instance)
        ```

5.  **Add Configuration:**
    *   Update `AppConfig` in `config_loader.py` and `.env.example` with any necessary API keys or default settings for the new provider.

6.  **Documentation:**
    *   Update `docs/index.md`, `docs/architecture.md`, and create new files in `docs/modules/` to document the new provider integration.

7.  **Testing:**
    *   Implement comprehensive unit tests for the new adapter and service.
    *   Add integration tests.

## 3. Adding New Parameters or Features to Existing Models

*   **Core Models:** If the feature involves new standardized parameters, update the Pydantic models in `core.models.py` (e.g., add a new field to `ChatCompletionRequest`).
*   **Adapters/Strategies:** Modify the relevant adapter (`OpenAIAdapter`) or Bedrock strategy (`ClaudeStrategy`, `TitanStrategy`) to:
    *   Include the new parameter in `convert_to_provider_request` if it's an input.
    *   Parse it in `convert_from_provider_response` or `convert_from_provider_stream_chunk` if it's an output.
    *   Ensure the `_get_default_param` logic in `BaseLLMAdapter` or specific parameter handling in adapters/strategies can pick up defaults for this new parameter from `AppConfig` if applicable.
*   **Configuration:** Add any related default values to `AppConfig` and `.env.example`.
*   **Service Layer:** The `chat_completion` method in `ConcreteLLMService` already accepts `**kwargs`, which can pass through additional parameters. If a parameter becomes standard, consider adding it explicitly to the `ChatCompletionRequest` DTO and the `chat_completion` method signature in `AbstractLLMService` and `ConcreteLLMService`.

By following these patterns, the library can be systematically extended while maintaining its core architecture and principles. 