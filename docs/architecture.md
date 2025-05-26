# Architecture Guide

> 📚 **[← Back to Documentation Hub](README.md)** | **[Main README](../README.md)**

This library is designed with a layered architecture to promote modularity, flexibility, and ease of maintenance, drawing heavily from the strategies outlined in the research paper "A Comprehensive Approach to Cross-Platform LLM API Integration: OpenAI and AWS Bedrock."

## Core Principles

*   **Abstraction:** Hide provider-specific details behind a common interface.
*   **Encapsulation:** Group related functionalities into distinct modules (models, adapters, services, utils).
*   **Decoupling:** Minimize dependencies between components to allow for independent development and modification.
*   **Extensibility:** Make it easy to add support for new LLM models, new features within existing models, or entirely new LLM providers.

## Layers

```mermaid
graph TD
    A[Application / Client Code] --> B{AbstractLLMService (Interface)};
    
    B --> C1[OpenAIService];
    B --> C2[BedrockService];
    
    C1 --> D1[OpenAIAdapter];
    C2 --> D2[BedrockAdapter];
    
    D1 --> E1[APIClient for OpenAI];
    D2 --> E2[APIClient for Bedrock];

    D2 --> S1{BedrockAdapterStrategy (Interface)};
    S1 --> SC[ClaudeStrategy];
    S1 --> ST[TitanStrategy];
    S1 --> SO[OtherBedrockModelStrategy ...];
    
    E1 --> F1[OpenAI API];
    E2 --> F2[AWS Bedrock API];
    
    subgraph Utils
        U1[ConfigLoader]
        U2[LoggerSetup]
        U3[CustomExceptions]
        U4[PydanticModels]
    end

    C1 -.-> U1;
    C1 -.-> U2;
    C1 -.-> U3;
    C1 -.-> U4;
    
    C2 -.-> U1;
    C2 -.-> U2;
    C2 -.-> U3;
    C2 -.-> U4;

    D1 -.-> U1;
    D1 -.-> U2;
    D1 -.-> U3;
    D1 -.-> U4;

    D2 -.-> U1;
    D2 -.-> U2;
    D2 -.-> U3;
    D2 -.-> U4;

    SC -.-> U4;
    ST -.-> U4;
    
    F[LLMServiceFactory] --> B;
    A --> F

    classDef interface fill:#E6E6FA,stroke:#B0C4DE,stroke-width:2px,color:#333;
    class B,S1 interface;
```

1.  **Service Layer (`AbstractLLMService`, `ConcreteLLMService`, `OpenAIService`, `BedrockService`):**
    *   Defines a high-level, consistent interface (`AbstractLLMService`) for interacting with any LLM provider.
    *   `ConcreteLLMService` provides a generic implementation that delegates to an adapter.
    *   Provider-specific services like `OpenAIService` and `BedrockService` (which are instances of `ConcreteLLMService`) encapsulate the logic for a particular LLM platform.
    *   Accessed via the `LLMServiceFactory`.

2.  **Adapter Layer (`BaseLLMAdapter`, `OpenAIAdapter`, `BedrockAdapter`):**
    *   The **Adapter Pattern** is key here.
    *   `BaseLLMAdapter` defines the contract for all adapters.
    *   `OpenAIAdapter` handles communication with OpenAI, converting requests and responses between the library's standard format and OpenAI's format.
    *   `BedrockAdapter` handles communication with AWS Bedrock. It internally uses the **Strategy Pattern** to manage different Bedrock model families.

3.  **Strategy Layer (within BedrockAdapter - `BedrockAdapterStrategy`, `ClaudeStrategy`, `TitanStrategy`):**
    *   `BedrockAdapterStrategy` defines the interface for model-specific logic within Bedrock.
    *   Concrete strategies like `ClaudeStrategy` and `TitanStrategy` implement this interface to handle the unique request/response formats and parameters of Anthropic Claude and Amazon Titan models, respectively.
    *   This makes adding support for new Bedrock model families (e.g., Llama, Cohere, Mistral via Bedrock) a matter of creating a new strategy class.

4.  **API Client Layer (`APIClient`):**
    *   Handles the raw HTTP/S communication with the actual LLM provider APIs (OpenAI, AWS Bedrock).
    *   Implements retry mechanisms (using `tenacity`) for transient errors (rate limits, network issues, server errors).
    *   Manages provider-specific authentication and client initialization (`get_openai_client`, `get_bedrock_runtime_client`).
    *   Maps low-level API errors to the library's custom exceptions.

5.  **Core Models & Utilities:**
    *   **`core/models.py`**: Contains Pydantic models (`Message`, `ChatCompletionRequest`, `ChatCompletionResponse`, `ChatCompletionChunk`, etc.) that define the standardized request and response structures used throughout the library. This ensures data consistency and validation.
    *   **`core/exceptions.py`**: Defines a hierarchy of custom exceptions for better error identification and handling.
    *   **`utils/config_loader.py`**: Loads configuration (API keys, default parameters) from environment variables and `.env` files.
    *   **`utils/logger_setup.py`**: Configures structured logging for the application.
    *   **`adapters/bedrock/bedrock_models.py`**: Maps generic model names to specific Bedrock model IDs and can hold default configurations for Bedrock model families.

## Data Flow (Example: Chat Completion)

1.  **Application Code:** Calls `chat_completion` on an `AbstractLLMService` instance (obtained from `LLMServiceFactory`).
2.  **Service (`OpenAIService` / `BedrockService`):**
    *   Receives the standardized `ChatCompletionRequest` (constructed from `Message` list and parameters).
    *   Delegates to its configured adapter (`OpenAIAdapter` / `BedrockAdapter`).
3.  **Adapter (`OpenAIAdapter` / `BedrockAdapter`):
    *   `convert_to_provider_request()`: Transforms the standard `ChatCompletionRequest` into the format expected by the specific LLM provider API.
        *   For `BedrockAdapter`, this step is further delegated to the active strategy (`ClaudeStrategy` or `TitanStrategy`).
    *   Calls the appropriate method on the `APIClient` (e.g., `make_openai_chat_completion_request` or `make_bedrock_request`).
4.  **APIClient:**
    *   Makes the actual HTTP/S call to the LLM API (e.g., OpenAI or AWS Bedrock).
    *   Handles retries and low-level error mapping.
5.  **(Response Path) APIClient:** Returns the raw response from the LLM provider.
6.  **Adapter (`OpenAIAdapter` / `BedrockAdapter`):
    *   `convert_from_provider_response()` (or `convert_from_provider_stream_chunk()` for streaming): Parses the provider-specific response (or stream chunk) into the library's standard `ChatCompletionResponse` (or `ChatCompletionChunk`).
        *   For `BedrockAdapter`, this is delegated to the strategy.
7.  **Service (`OpenAIService` / `BedrockService`):** Returns the standardized response/chunk to the application.

This layered approach ensures that changes in one part of the system (e.g., a Bedrock model's API details) have minimal impact on other parts, particularly the application code that consumes the `AbstractLLMService`. 