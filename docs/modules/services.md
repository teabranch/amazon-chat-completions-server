# Services (`src.llm_integrations.services`)

The service layer provides a high-level, consistent interface for client applications to interact with LLMs, abstracting away the underlying provider and adapter details.

## 1. Abstract LLM Service (`services.llm_service_abc.AbstractLLMService`)

This abstract base class (ABC) defines the contract for all LLM services. It ensures that any service implementation, regardless of the underlying LLM provider, offers a consistent API to the rest of the application.

Key abstract methods:

*   `chat_completion(...)`: The primary method for sending chat requests. It takes a list of `Message` objects and other parameters (model_id, stream, temperature, max_tokens, etc.) and returns either a `ChatCompletionResponse` (for non-streaming) or an `AsyncGenerator[ChatCompletionChunk, None]` (for streaming).

The `model_id` parameter here allows for flexibility, but typically a service instance obtained from the factory is already configured for a specific model via its adapter.

## 2. Concrete LLM Service (`services.concrete_services.ConcreteLLMService`)

This is a generic, concrete implementation of `AbstractLLMService`. It takes an instance of `BaseLLMAdapter` in its constructor and delegates the actual LLM interaction to this adapter.

*   **Initialization**: Takes a `BaseLLMAdapter` (e.g., `OpenAIAdapter`, `BedrockAdapter`).
*   **`chat_completion(...)` Method**: 
    1.  Constructs a `ChatCompletionRequest` DTO from the input parameters.
    2.  Calls either `adapter.chat_completion(request_dto)` for non-streaming requests or `adapter.stream_chat_completion(request_dto)` for streaming requests.
    3.  Handles and logs errors, re-raising them as appropriate library exceptions.

### Specializations: `OpenAIService` and `BedrockService`

Located in `services.concrete_services.py`, these classes inherit from `ConcreteLLMService`:

*   **`OpenAIService(ConcreteLLMService)`**: Specifically initialized with an `OpenAIAdapter`.
*   **`BedrockService(ConcreteLLMService)`**: Specifically initialized with a `BedrockAdapter`.

These specializations mainly serve to provide type-specific clarity and ensure the correct adapter type is used, although `ConcreteLLMService` itself is functional with any valid adapter.

## 3. LLM Service Factory (`services.llm_service_factory.LLMServiceFactory`)

This factory class is responsible for creating and providing instances of LLM services (`OpenAIService` or `BedrockService`). This is the primary entry point for client applications to get an LLM service.

*   **`get_service(provider_name: str, model_id: Optional[str] = None, **kwargs: Any) -> AbstractLLMService`**: 
    *   Takes a `provider_name` (e.g., "openai", "bedrock") and an optional `model_id`.
    *   Instantiates the appropriate adapter (`OpenAIAdapter` or `BedrockAdapter`) based on the provider and model.
    *   Wraps the adapter in the corresponding concrete service (`OpenAIService` or `BedrockService`).
    *   Handles caching of service instances to avoid re-initializing adapters for the same provider/model/config combination.
    *   Raises `ModelNotFoundError` if the provider or model is not supported, or `ConfigurationError` if necessary configurations are missing.
*   **`clear_cache()`**: Clears the in-memory cache of service instances.

**Usage Flow:**

1.  Client requests a service: `service = LLMServiceFactory.get_service("openai", model_id="gpt-4o-mini")`
2.  Factory creates `OpenAIAdapter` for "gpt-4o-mini".
3.  Factory creates `OpenAIService`, injecting the adapter.
4.  Factory returns the `OpenAIService` instance.
5.  Client calls: `response = await service.chat_completion(messages=[...])`

This setup decouples the client code from the concrete implementations of adapters and services, allowing for easier switching between LLM providers and models. 