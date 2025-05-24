# Amazon Chat Completions Server - Documentation

Welcome to the documentation for the Amazon Chat Completions Server. This library provides a unified interface for interacting with Large Language Models (LLMs) from different providers, primarily focusing on OpenAI and AWS Bedrock.

## Purpose

The main goal of this library is to abstract the complexities of using multiple LLM APIs, allowing developers to write consistent code regardless of the backend LLM provider. It facilitates:

*   **OpenAI to Bedrock Conversion:** Adapting requests and responses between OpenAI's Chat Completions API schema and various AWS Bedrock model interfaces (e.g., Claude, Titan).
*   **Streaming Support:** Handling streaming data consistently across providers.
*   **Unified Interface:** Providing a single `AbstractLLMService` that can be used to interact with any supported LLM.
*   **Extensibility:** Designed with a strategy pattern to easily add support for new models within Bedrock or even new LLM providers.

## Key Features from Research

This implementation is heavily based on the principles outlined in the research paper "A Comprehensive Approach to Cross-Platform LLM API Integration: OpenAI and AWS Bedrock." Key features derived from this research include:

*   **Adapter Pattern:** `OpenAIAdapter` and `BedrockAdapter` translate requests and responses.
*   **Strategy Pattern:** Within `BedrockAdapter`, specific strategies (`ClaudeStrategy`, `TitanStrategy`) handle model-family-specific logic.
*   **Factory Pattern:** `LLMServiceFactory` provides instances of LLM services.
*   **Abstract Base Classes:** `AbstractLLMService` and `BaseLLMAdapter` define clear contracts.
*   **Robust Error Handling:** Custom exceptions and retry mechanisms (`APIClient` with `tenacity`).
*   **Configuration Management:** Centralized configuration loading from `.env` files (`AppConfig`).
*   **Structured Logging:** Consistent logging throughout the application.
*   **Pydantic Models:** Clear data validation and serialization for API interactions.

## Navigating the Documentation

*   **[Architecture](architecture.md):** A high-level overview of the system design.
*   **[Core Modules](modules/core.md):** Details on Pydantic models, custom exceptions.
*   **[Adapters](modules/adapters.md):** Explanation of the adapter and strategy patterns used.
    *   **[OpenAI Adapter](modules/openai_adapter.md)**
    *   **[Bedrock Adapter](modules/bedrock_adapter.md)** (including Claude and Titan strategies)
*   **[Services](modules/services.md):** Information on the `AbstractLLMService` and the `LLMServiceFactory`.
*   **[Utilities](modules/utils.md):** Details on `APIClient`, `ConfigLoader`, and `LoggerSetup`.
*   **[Server and CLI](server_and_cli.md):** Implementation plan for FastAPI server and CLI components.
*   **[Usage Guide](usage.md):** How to use the library with code examples.
*   **[Extending the Library](extending.md):** How to add new models or providers.
*   **[Testing](testing.md):** Information on running tests.

## Getting Started

Refer to the main [README.md](../../README.md) for installation and basic setup instructions. 