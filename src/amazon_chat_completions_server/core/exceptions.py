# Base exception for the application/library
class AppExceptionBase(Exception):
    """Base exception class for the application."""

    pass


# --- Configuration Errors --- #
class ConfigurationError(AppExceptionBase):
    """For errors related to application or service configuration."""

    pass


# --- Model Errors (distinct from ServiceModelNotFoundError which is provider-specific) --- #
class ModelNotFoundError(AppExceptionBase):
    """When a requested model alias is not found or not supported by the factory/config."""

    pass


# --- API Client / Low-Level Communication Errors (as used by api_client.py) --- #
class APIClientError(AppExceptionBase):
    """Base class for errors from the low-level API client."""

    pass


class APIConnectionError(APIClientError):
    """For errors establishing a connection to the provider API."""

    pass


class AuthenticationError(APIClientError):
    """For authentication failures detected at the API client level or mapped from provider."""

    pass


class RateLimitError(APIClientError):
    """When the LLM provider returns a rate limit error, mapped by APIClient."""

    pass


class APIRequestError(APIClientError):
    """Error related to forming or validating the request to the provider API, mapped by APIClient."""

    pass


class APIServerError(APIClientError):
    """For server-side errors from the LLM API (e.g., HTTP 5xx), mapped by APIClient."""

    pass


# --- Service Layer Errors (for LLM provider interactions, raised by Service classes) --- #
class ServiceError(AppExceptionBase):
    """Base class for errors originating from an LLM service interaction."""

    pass


class ServiceAuthenticationError(ServiceError):
    """For authentication failures with the LLM provider, as interpreted by the service."""

    pass


class ServiceModelNotFoundError(ServiceError):
    """When a model is not found by the LLM provider or not accessible, as interpreted by the service."""

    pass


class ServiceApiError(ServiceError):
    """For general API errors from the LLM provider not covered by specific types, as interpreted by the service."""

    pass


class ServiceUnavailableError(ServiceError):
    """When the LLM provider service is unavailable or overloaded, as interpreted by the service."""

    pass


class ServiceRateLimitError(ServiceError):
    """When the LLM provider returns a rate limit error, as interpreted by the service."""

    pass


class StreamingError(ServiceError):
    """For errors specifically related to streaming responses."""

    pass


# --- Adapter Layer Errors --- #
class AdapterError(AppExceptionBase):
    """Base class for errors originating from an adapter."""

    pass


class LLMIntegrationError(
    AdapterError
):  # Kept from existing search result, seems adapter-related. Could also be a general name for APIClientError.
    """General error for LLM integration issues, often at adapter level or generic API client issues."""

    pass


# APIRequestError is also defined under APIClientError. If adapters need their own, it should be distinct.
# For now, assuming adapters would catch APIClientError and raise their own or let them pass through.


class UnsupportedFeatureError(AdapterError):
    """When a feature is not supported by the adapter or underlying model."""

    pass
