# Utilities (`src.llm_integrations.utils`)

The `utils` module provides shared functionalities like API communication, configuration management, and logging setup.

## 1. API Client (`utils.api_client.APIClient`)

This class is central to making actual HTTP/S calls to the LLM provider APIs. It is designed to be robust and handle common API interaction challenges.

*   **Provider-Specific Methods:**
    *   `make_openai_chat_completion_request(...)`: Handles requests to the OpenAI Chat Completions API (both streaming and non-streaming).
    *   `make_bedrock_request(...)`: Handles requests to AWS Bedrock (`invoke_model` and `invoke_model_with_response_stream`).
*   **Client Initialization (`get_openai_client`, `get_bedrock_runtime_client`):**
    *   Lazily initializes and reuses `openai.AsyncOpenAI` and `boto3.client('bedrock-runtime')` clients.
    *   `get_openai_client`: Checks for `app_config.OPENAI_API_KEY`.
    *   `get_bedrock_runtime_client`: 
        *   Checks for AWS configuration (`app_config.AWS_REGION` is essential).
        *   Prioritizes authentication methods for Bedrock client creation in the following order:
            1.  Static Credentials: `app_config.AWS_ACCESS_KEY_ID` and `app_config.AWS_SECRET_ACCESS_KEY` (and optional `AWS_SESSION_TOKEN`).
            2.  AWS Profile: `app_config.AWS_PROFILE` (uses the named profile from `~/.aws/credentials` or `~/.aws/config`).
            3.  Default Boto3 Chain: If neither static keys nor a profile name is provided, it relies on Boto3's default credential resolution chain (e.g., IAM instance profiles, ECS task roles, environment variables like `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN` if set directly in the environment rather than `.env`).
        *   Raises `ConfigurationError` if essential configurations (like region, or if all auth methods fail) are missing or invalid.
*   **Retry Logic (`tenacity`):**
    *   Both request methods are decorated with `@retry` from the `tenacity` library.
    *   Retry configuration (`retry_config`) includes:
        *   `stop_after_attempt`: Based on `app_config.RETRY_MAX_ATTEMPTS`.
        *   `wait_exponential`: With min/max wait times from `app_config`.
        *   `retry_if_exception_type`: Retries on specific exceptions like `openai.APIConnectionError`, `openai.RateLimitError`, `openai.InternalServerError`, and generic `botocore.exceptions.ClientError` (which can be refined for Bedrock).
        *   Logging before sleep on retry attempts.
*   **Error Mapping:**
    *   Catches provider-specific exceptions (e.g., `openai.RateLimitError`, `botocore.exceptions.ClientError` with specific error codes like `ThrottlingException`, `AccessDeniedException`).
    *   Maps these to the library's custom exceptions defined in `core.exceptions.py` (e.g., `RateLimitError`, `AuthenticationError`, `APIServerError`, `APIRequestError`). This provides a consistent error vocabulary for higher layers.
*   **Bedrock Stream Handling:**
    *   `_handle_bedrock_stream(...)`: An async generator that processes the `EventStream` returned by Bedrock for streaming responses. It decodes chunks, yields JSON data, and handles potential errors within the stream.
*   **JSON Serialization/Deserialization:** Handles conversion of request bodies to JSON and parsing of JSON responses.

## 2. Configuration Loader (`utils.config_loader.py`)

This module is responsible for loading and providing access to application configuration.

*   **`AppConfig` Class:**
    *   Loads environment variables from a `.env` file located in the project root (using `python-dotenv`). It also checks the current working directory for `.env` as a fallback.
    *   Provides typed attributes for accessing configuration values (e.g., `app_config.OPENAI_API_KEY`, `app_config.AWS_REGION`, `app_config.AWS_PROFILE`, `app_config.DEFAULT_MAX_TOKENS_OPENAI`, `app_config.RETRY_MAX_ATTEMPTS`).
    *   Includes default values for many settings if not found in the environment or `.env` file.
    *   Performs basic validation on initialization, logging warnings or errors for missing critical configurations. Checks for OpenAI key, and for AWS, it checks for either static keys OR a profile name along with the region.
*   **`app_config` Instance:** A global instance of `AppConfig` is created when the module is imported, making configuration readily available throughout the library.

## 3. Logger Setup (`utils.logger_setup.py`)

This module configures logging for the entire application upon import.

*   **`setup_logging()` Function:**
    *   Called automatically when the module is imported.
    *   Configures Python's standard `logging` module.
    *   Sets the global logging level based on `app_config.LOG_LEVEL` (defaults to INFO).
    *   Uses `logging.basicConfig` to set up a console handler (`StreamHandler` to `sys.stdout`) with a standard format (`%(asctime)s - %(name)s - %(levelname)s - %(message)s`).
    *   Includes commented-out examples for adding file handlers (e.g., `FileHandler`, `RotatingFileHandler`) for production scenarios.
    *   Logs a message indicating the configured log level.

By importing `logger_setup` (e.g., in `main.py` or top-level `__init__.py`), logging is consistently configured across all modules that use `logging.getLogger(__name__)`. 