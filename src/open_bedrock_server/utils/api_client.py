import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

import boto3
import botocore.config
import botocore.exceptions
import openai
from botocore.exceptions import ClientError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..core.exceptions import (
    APIConnectionError,
    APIRequestError,
    APIServerError,
    AuthenticationError,
    ConfigurationError,
    LLMIntegrationError,
    RateLimitError,
    StreamingError,
)
from .config_loader import app_config

logger = logging.getLogger(__name__)

# --- Tenacity Retry Configuration ---
DEFAULT_RETRY_EXCEPTIONS = (
    openai.APIConnectionError,
    openai.RateLimitError,
    openai.InternalServerError,
    # Add relevant botocore exceptions for retry, e.g., ThrottlingException, ServiceUnavailable
    # ClientError subclasses that are retryable need to be identified carefully.
    # For now, we can make a generic ClientError retryable and then refine.
    ClientError,  # This is broad; specific ClientErrors might be better.
)

retry_config = {
    "stop": stop_after_attempt(app_config.RETRY_MAX_ATTEMPTS),
    "wait": wait_exponential(
        multiplier=1,
        min=app_config.RETRY_WAIT_MIN_SECONDS,
        max=app_config.RETRY_WAIT_MAX_SECONDS,
    ),
    "retry": retry_if_exception_type(DEFAULT_RETRY_EXCEPTIONS),
    "before_sleep": lambda retry_state: logger.warning(
        f"Retrying API call {retry_state.fn.__name__ if hasattr(retry_state.fn, '__name__') else 'unknown_function'} due to {type(retry_state.outcome.exception())}, attempt #{retry_state.attempt_number}"
    ),
}

# --- OpenAI Client --- #
_openai_client = None


def get_openai_client():
    global _openai_client
    if not app_config.OPENAI_API_KEY:
        logger.warning(
            "OpenAI API key is not configured. OpenAI client will not be initialized."
        )
        return None
    if _openai_client is None:
        _openai_client = openai.AsyncOpenAI(api_key=app_config.OPENAI_API_KEY)
    return _openai_client


# --- Bedrock Runtime Client --- #
_bedrock_runtime_client = None


def get_bedrock_runtime_client():
    global _bedrock_runtime_client
    if not (
        app_config.AWS_ACCESS_KEY_ID
        and app_config.AWS_SECRET_ACCESS_KEY
        and app_config.AWS_REGION
    ):
        logger.warning(
            "AWS credentials or region not fully configured. Bedrock client may not be initialized or may fail."
        )
        # Depending on how boto3 handles missing creds (e.g. IAM roles), this might still work in some envs
    if _bedrock_runtime_client is None:
        try:
            _bedrock_runtime_client = boto3.client(
                service_name="bedrock-runtime",
                region_name=app_config.AWS_REGION,
                aws_access_key_id=app_config.AWS_ACCESS_KEY_ID
                or None,  # Pass None if empty to allow boto3 to use other credential sources
                aws_secret_access_key=app_config.AWS_SECRET_ACCESS_KEY or None,
            )
            # Perform a simple test call to check credentials early, e.g., list_foundation_models (requires bedrock:ListFoundationModels permission)
            # This can be added if aggressive credential validation is desired on init.
            # try:
            #     _bedrock_runtime_client.list_foundation_models(byProvider='Amazon') # Example call
            #     logger.info("Bedrock client initialized and basic connectivity test passed.")
            # except ClientError as e:
            #     logger.error(f"Bedrock client initialized, but connectivity test failed: {e}. Check permissions and AWS configuration.")
            #     # Depending on severity, you might want to set _bedrock_runtime_client to None here
            logger.info(
                f"Bedrock runtime client initialized for region: {app_config.AWS_REGION}"
            )
        except (
            Exception
        ) as e:  # Catches potential boto3 setup errors beyond ClientError
            logger.error(f"Failed to initialize Bedrock runtime client: {e}")
            _bedrock_runtime_client = None  # Ensure it's None if init fails
    return _bedrock_runtime_client


class APIClient:
    """Handles making API calls with retry logic and error mapping."""

    def __init__(self):
        self.openai_client: openai.AsyncOpenAI | None = None
        self.bedrock_runtime_client: Any | None = (
            None  # boto3 client, type hinted as Any for simplicity
        )
        self.app_config = app_config  # Use the global app_config instance

    def get_openai_client(self) -> openai.AsyncOpenAI:
        if not self.app_config.OPENAI_API_KEY:
            raise ConfigurationError("OpenAI API key is not configured.")
        if self.openai_client is None:
            self.openai_client = openai.AsyncOpenAI(
                api_key=self.app_config.OPENAI_API_KEY
            )
        return self.openai_client

    def get_bedrock_runtime_client(self) -> Any:
        """Lazily initializes and returns a Bedrock runtime client."""
        if self.bedrock_runtime_client is None:
            logger.debug("Initializing Bedrock runtime client.")

            # Check for AWS credentials and region
            static_keys_present = (
                self.app_config.AWS_ACCESS_KEY_ID
                and self.app_config.AWS_SECRET_ACCESS_KEY
            )
            profile_name_present = bool(self.app_config.AWS_PROFILE)
            role_arn_present = bool(self.app_config.AWS_ROLE_ARN)
            web_identity_present = bool(self.app_config.AWS_WEB_IDENTITY_TOKEN_FILE)
            region_present = bool(self.app_config.AWS_REGION)

            if not region_present:
                # Log a warning but proceed; Boto3 might pick up region from shared config or env var AWS_DEFAULT_REGION
                logger.warning(
                    "AWS_REGION is not set in AppConfig. Boto3 will attempt to find it in the environment "
                    "or shared AWS config. Bedrock calls may fail if region is not discoverable."
                )

            if not (
                static_keys_present
                or profile_name_present
                or role_arn_present
                or web_identity_present
            ):
                # This check is important because Boto3 can sometimes pick up credentials from other sources
                # (e.g. EC2 instance profile, ECS task role). We want to be explicit if no config is provided via .env
                logger.warning(
                    "No AWS authentication method configured (static credentials, profile, role ARN, or web identity). "
                    "Boto3 will attempt to find credentials using its default chain "
                    "(e.g., environment variables, shared credentials file, IAM roles, instance profiles)."
                )
                # Attempt to create a session without explicit creds, relying on Boto3's default credential resolution.
                session = boto3.Session(region_name=self.app_config.AWS_REGION)
            elif static_keys_present:
                logger.info(
                    "Using static AWS credentials (key ID and secret key) for Bedrock client."
                )
                session = boto3.Session(
                    aws_access_key_id=self.app_config.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=self.app_config.AWS_SECRET_ACCESS_KEY,
                    aws_session_token=self.app_config.AWS_SESSION_TOKEN,  # Will be None if not set, which is fine
                    region_name=self.app_config.AWS_REGION,
                )
            elif profile_name_present:  # Static keys not present, but profile name is
                logger.info(
                    f"Using AWS profile '{self.app_config.AWS_PROFILE}' for Bedrock client."
                )
                try:
                    session = boto3.Session(
                        profile_name=self.app_config.AWS_PROFILE,
                        region_name=self.app_config.AWS_REGION,
                    )
                    # Test credentials by getting caller identity to fail early if profile is bad
                    sts_client = session.client("sts")
                    sts_client.get_caller_identity()
                    logger.info(
                        f"Successfully initialized session with AWS profile '{self.app_config.AWS_PROFILE}'."
                    )
                except (
                    botocore.exceptions.ProfileNotFound,
                    botocore.exceptions.NoCredentialsError,
                    botocore.exceptions.ClientError,
                ) as e:
                    logger.error(
                        f"Failed to initialize Boto3 session with profile '{self.app_config.AWS_PROFILE}'. Error: {e}. "
                        "Falling back to Boto3 default credential resolution chain."
                    )
                    # Fallback to default session if profile fails
                    session = boto3.Session(region_name=self.app_config.AWS_REGION)
            elif role_arn_present:  # Role ARN present, use assume role
                logger.info(
                    f"Using AWS role assumption with ARN '{self.app_config.AWS_ROLE_ARN}' for Bedrock client."
                )
                try:
                    # Create a base session to assume the role
                    base_session = boto3.Session(region_name=self.app_config.AWS_REGION)
                    sts_client = base_session.client("sts")

                    # Prepare assume role parameters
                    assume_role_params = {
                        "RoleArn": self.app_config.AWS_ROLE_ARN,
                        "RoleSessionName": self.app_config.AWS_ROLE_SESSION_NAME,
                        "DurationSeconds": self.app_config.AWS_ROLE_SESSION_DURATION,
                    }

                    # Add external ID if provided
                    if self.app_config.AWS_EXTERNAL_ID:
                        assume_role_params["ExternalId"] = (
                            self.app_config.AWS_EXTERNAL_ID
                        )
                        logger.info("Using external ID for role assumption.")

                    # Assume the role
                    response = sts_client.assume_role(**assume_role_params)
                    credentials = response["Credentials"]

                    # Create session with assumed role credentials
                    session = boto3.Session(
                        aws_access_key_id=credentials["AccessKeyId"],
                        aws_secret_access_key=credentials["SecretAccessKey"],
                        aws_session_token=credentials["SessionToken"],
                        region_name=self.app_config.AWS_REGION,
                    )

                    logger.info(
                        f"Successfully assumed role '{self.app_config.AWS_ROLE_ARN}'. "
                        f"Session expires at: {credentials['Expiration']}"
                    )
                except (
                    botocore.exceptions.ClientError,
                    botocore.exceptions.NoCredentialsError,
                ) as e:
                    logger.error(
                        f"Failed to assume role '{self.app_config.AWS_ROLE_ARN}'. Error: {e}. "
                        "Falling back to Boto3 default credential resolution chain."
                    )
                    # Fallback to default session if role assumption fails
                    session = boto3.Session(region_name=self.app_config.AWS_REGION)
            elif web_identity_present:  # Web identity token present
                logger.info(
                    f"Using AWS web identity token from '{self.app_config.AWS_WEB_IDENTITY_TOKEN_FILE}' for Bedrock client."
                )
                try:
                    # For web identity, we rely on boto3's built-in support
                    # Set the environment variables that boto3 expects
                    import os

                    original_env = {}

                    # Temporarily set environment variables for boto3
                    env_vars = {
                        "AWS_WEB_IDENTITY_TOKEN_FILE": self.app_config.AWS_WEB_IDENTITY_TOKEN_FILE,
                        "AWS_ROLE_ARN": self.app_config.AWS_ROLE_ARN or "",
                        "AWS_ROLE_SESSION_NAME": self.app_config.AWS_ROLE_SESSION_NAME,
                    }

                    for key, value in env_vars.items():
                        if value:
                            original_env[key] = os.environ.get(key)
                            os.environ[key] = value

                    try:
                        session = boto3.Session(region_name=self.app_config.AWS_REGION)
                        # Test the session
                        sts_client = session.client("sts")
                        sts_client.get_caller_identity()
                        logger.info(
                            "Successfully initialized session with web identity token."
                        )
                    finally:
                        # Restore original environment
                        for key in env_vars:
                            if original_env.get(key) is not None:
                                os.environ[key] = original_env[key]
                            elif key in os.environ:
                                del os.environ[key]

                except Exception as e:
                    logger.error(
                        f"Failed to initialize session with web identity token. Error: {e}. "
                        "Falling back to Boto3 default credential resolution chain."
                    )
                    # Fallback to default session
                    session = boto3.Session(region_name=self.app_config.AWS_REGION)
            else:  # Should not be reached due to outer conditional, but as a safeguard
                logger.info(
                    "Unexpected credential state. Falling back to default Boto3 session initialization for Bedrock."
                )
                session = boto3.Session(region_name=self.app_config.AWS_REGION)

            try:
                self.bedrock_runtime_client = session.client(
                    "bedrock-runtime",
                    config=botocore.config.Config(
                        retries={
                            "max_attempts": 0,
                            "mode": "standard",
                        }  # We use tenacity for retries at a higher level
                    ),
                )
                logger.info(
                    f"Bedrock runtime client initialized successfully for region: {session.region_name or 'Default'}."
                )
            except Exception as e:
                logger.error(
                    f"Failed to create Bedrock runtime client: {e}", exc_info=True
                )
                raise ConfigurationError(
                    "Failed to initialize AWS Bedrock runtime client. "
                    "Ensure AWS credentials and region are correctly configured or discoverable by Boto3. "
                    f"Error: {e}"
                ) from e

        return self.bedrock_runtime_client

    @retry(**retry_config)
    async def make_openai_chat_completion_request(
        self, request_payload: dict[str, Any], stream: bool = False
    ) -> (
        openai.types.chat.ChatCompletion
        | AsyncGenerator[openai.types.chat.ChatCompletionChunk, None]
    ):
        """Makes a request to OpenAI Chat Completions API."""
        client = self.get_openai_client()

        try:
            logger.debug(
                f"OpenAI Request: model={request_payload.get('model')}, stream={stream}, messages[:1]={request_payload.get('messages', [])[:1]}"
            )
            response = await client.chat.completions.create(
                **request_payload, stream=stream
            )
            logger.debug("OpenAI API call successful.")
            return response
        except openai.APIConnectionError as e:
            logger.error(f"OpenAI API Connection Error: {e}")
            raise APIConnectionError(f"OpenAI: {e}") from e
        except openai.RateLimitError as e:
            logger.error(f"OpenAI API Rate Limit Error: {e}")
            raise RateLimitError(f"OpenAI: {e}") from e
        except openai.AuthenticationError as e:
            logger.error(f"OpenAI API Authentication Error: {e}")
            raise AuthenticationError(f"OpenAI: {e}") from e
        except openai.BadRequestError as e:
            logger.error(f"OpenAI API Bad Request Error: {e}")
            raise APIRequestError(f"OpenAI: {e}") from e
        except openai.APIStatusError as e:  # Catches other status errors like 5xx
            logger.error(
                f"OpenAI API Status Error (status: {e.status_code}): {e.message}"
            )
            if 500 <= e.status_code < 600:
                raise APIServerError(
                    f"OpenAI Server Error (status: {e.status_code}): {e.message}"
                ) from e
            else:
                raise LLMIntegrationError(
                    f"OpenAI API Status Error (status: {e.status_code}): {e.message}"
                ) from e
        except Exception as e:
            logger.error(f"An unexpected error occurred with OpenAI API: {e}")
            raise LLMIntegrationError(f"OpenAI Unexpected Error: {e}") from e

    @retry(**retry_config)
    async def make_bedrock_request(
        self, model_id: str, body: dict[str, Any], stream: bool = False
    ) -> dict[str, Any] | AsyncGenerator[dict[str, Any], None]:
        """Makes a request to AWS Bedrock, handling streaming if specified."""

        # Ensure client is initialized (which also checks credentials/profile)
        try:
            client = self.get_bedrock_runtime_client()
            if (
                not client.meta.region_name
            ):  # Should have been set or warned during client init
                raise ConfigurationError(
                    "AWS region not configured or discoverable for Bedrock client."
                )
        except (
            ConfigurationError
        ) as e:  # Catch error from get_bedrock_runtime_client specifically
            logger.error(f"Bedrock client configuration error: {e}")
            raise  # Re-raise the ConfigurationError to be handled by the caller

        serialized_body = json.dumps(body)

        try:
            logger.debug(
                f"Bedrock Request: model_id={model_id}, stream={stream}, body_keys={body.keys()}"
            )
            if stream:
                response = client.invoke_model_with_response_stream(
                    modelId=model_id,
                    body=serialized_body,
                    contentType="application/json",
                    accept="*/*",  # Common practice, but can be model specific
                )
                logger.debug(
                    f"Bedrock invoke_model_with_response_stream called for {model_id}."
                )
                return self._handle_bedrock_stream(response.get("body"))
            else:
                response = client.invoke_model(
                    modelId=model_id,
                    body=serialized_body,
                    contentType="application/json",
                    accept="*/*",
                )
                logger.debug(f"Bedrock invoke_model successful for {model_id}.")
                response_body = json.loads(response.get("body").read().decode("utf-8"))
                return response_body
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            error_message = e.response.get("Error", {}).get("Message", str(e))
            status_code = e.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            logger.error(
                f"Bedrock API ClientError: Code={error_code}, Message={error_message}, Status={status_code}"
            )

            if error_code == "AccessDeniedException":
                raise AuthenticationError(
                    f"Bedrock Access Denied: {error_message}"
                ) from e
            if error_code == "ThrottlingException":
                raise RateLimitError(f"Bedrock Throttled: {error_message}") from e
            if error_code == "ValidationException":
                raise APIRequestError(
                    f"Bedrock Validation Error: {error_message}"
                ) from e
            if error_code == "ResourceNotFoundException":
                raise APIRequestError(
                    f"Bedrock Resource Not Found (e.g. model ID): {error_message}"
                ) from e
            if status_code and 500 <= status_code < 600:
                raise APIServerError(
                    f"Bedrock Server Error (status: {status_code}): {error_message}"
                ) from e
            # Fallback for other ClientErrors
            raise APIConnectionError(f"Bedrock ClientError: {error_message}") from e
        except Exception as e:
            logger.error(f"An unexpected error occurred with Bedrock API: {e}")
            raise LLMIntegrationError(f"Bedrock Unexpected Error: {e}") from e

    async def _handle_bedrock_stream(
        self, event_stream: Any
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Helper to process Bedrock's event stream."""
        if not event_stream:
            logger.warning("Bedrock stream event_stream is None.")
            return
        try:
            for event in event_stream:
                chunk = event.get("chunk")
                if chunk:
                    chunk_data = json.loads(chunk.get("bytes").decode("utf-8"))
                    logger.debug(
                        f"Bedrock stream chunk received: {list(chunk_data.keys()) if isinstance(chunk_data, dict) else 'Non-dict chunk'}"
                    )
                    yield chunk_data
                elif (
                    "internalServerException" in event
                    or "modelStreamErrorException" in event
                    or "throttlingException" in event
                ):
                    error_details = (
                        event.get("internalServerException")
                        or event.get("modelStreamErrorException")
                        or event.get("throttlingException")
                    )
                    logger.error(f"Error in Bedrock stream: {error_details}")
                    # Decide if this should raise an exception or just log and continue/stop
                    # For now, raising an APIServerError or RateLimitError for these cases
                    if "throttlingException" in event:
                        raise RateLimitError(
                            f"Bedrock stream throttled: {error_details.get('message')}"
                        )
                    else:
                        raise APIServerError(
                            f"Error in Bedrock stream: {error_details.get('message')}"
                        )
        except Exception as e:
            logger.error(f"Error processing Bedrock stream: {e}")
            raise StreamingError(f"Failed to process Bedrock stream: {e}") from e
        finally:
            if hasattr(event_stream, "close") and callable(event_stream.close):
                event_stream.close()
            logger.debug("Bedrock event stream processing finished.")


# Example Usage (for testing within this file if needed)
async def _test_openai():
    api_client = APIClient()
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": "Hello!"}],
        "max_tokens": 5,
    }
    try:
        # Non-streaming
        # response = await api_client.make_openai_chat_completion_request(payload, stream=False)
        # print("OpenAI Non-Stream Response:", response)

        # Streaming
        print("\nOpenAI Stream Response:")
        async for chunk in await api_client.make_openai_chat_completion_request(
            payload, stream=True
        ):
            if (
                chunk.choices
                and chunk.choices[0].delta
                and chunk.choices[0].delta.content
            ):
                print(chunk.choices[0].delta.content, end="")
        print()
    except LLMIntegrationError as e:
        print(f"Error testing OpenAI: {e}")


async def _test_bedrock_claude():
    api_client = APIClient()
    # Ensure your .env has AWS creds and OPENAI_API_KEY (even if not used for this part, for config loading)
    if not get_bedrock_runtime_client():
        print("Bedrock client not available, skipping Bedrock Claude test.")
        return

    claude_model_id = (
        "anthropic.claude-3-sonnet-20240229-v1:0"  # Or another claude model
    )
    claude_payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 100,
        "messages": [{"role": "user", "content": "Hello, who are you?"}],
    }
    try:
        # Non-streaming
        # response = await api_client.make_bedrock_request(claude_model_id, claude_payload, stream=False)
        # print("Bedrock Claude Non-Stream Response:", response)

        # Streaming
        print("\nBedrock Claude Stream Response:")
        async for chunk in await api_client.make_bedrock_request(
            claude_model_id, claude_payload, stream=True
        ):
            # The structure of Bedrock stream chunks varies by model
            # For Claude 3, it's usually something like:
            # {'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'text_delta', 'text': ' some text'}}
            # {'type': 'message_delta', 'delta': {'stop_reason': 'end_turn', 'stop_sequence': None}, 'usage': {'output_tokens': 25}}
            if (
                chunk.get("type") == "content_block_delta"
                and chunk.get("delta", {}).get("type") == "text_delta"
            ):
                print(chunk["delta"]["text"], end="")
            elif (
                chunk.get("type") == "message_stop"
            ):  # For Claude 3 Haiku, Sonnet, Opus
                print(
                    f"\nStream finished. Stop Reason: {chunk.get('amazon-bedrock-invocationMetrics', {}).get('outputTokenCount')} tokens"
                )  # Metrics are in a separate chunk
        print()

    except LLMIntegrationError as e:
        print(f"Error testing Bedrock Claude: {e}")


if __name__ == "__main__":
    # This basic setup is needed for logger to work when running file directly
    logging.basicConfig(
        level=app_config.LOG_LEVEL,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    # asyncio.run(_test_openai())
    asyncio.run(_test_bedrock_claude())
