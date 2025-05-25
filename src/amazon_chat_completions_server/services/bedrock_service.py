import os
import json
from typing import List, AsyncGenerator, Optional, Union, Dict, Any
import boto3
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError, BotoCoreError
import asyncio

from src.amazon_chat_completions_server.core.models import (
    Message, 
    ChatCompletionResponse,
    ChatCompletionChunk,
    ModelProviderInfo,
    ChoiceDelta,
    ChatCompletionChunkChoice,
    ChatCompletionChoice as CoreChatCompletionChoice,
    BedrockClaudeMessage, # For mapping to Claude messages
    BedrockContentBlock   # For parsing Claude responses
)
from .llm_service_abc import AbstractLLMService
# Import custom exceptions
from src.amazon_chat_completions_server.core.exceptions import (
    ConfigurationError, 
    ServiceAuthenticationError, 
    ServiceModelNotFoundError, 
    ServiceApiError,
    ServiceUnavailableError,
    ServiceRateLimitError,
    StreamingError
)
import logging
import time

logger = logging.getLogger(__name__)

# Helper to determine model provider from Bedrock model ID
def get_provider_from_bedrock_model_id(model_id: str) -> str:
    if model_id.startswith("anthropic.") or model_id.startswith("us.anthropic."):
        return "anthropic"
    elif model_id.startswith("ai21.") or model_id.startswith("us.ai21."):
        return "ai21"
    elif model_id.startswith("cohere.") or model_id.startswith("us.cohere."):
        return "cohere"
    elif model_id.startswith("meta.") or model_id.startswith("us.meta."):
        return "meta"
    elif model_id.startswith("amazon.") or model_id.startswith("us.amazon."):
        return "amazon"
    return "unknown_bedrock_provider"

class BedrockService(AbstractLLMService):
    def __init__(self, AWS_REGION: Optional[str] = None, AWS_PROFILE: Optional[str] = None, **kwargs):
        self.AWS_REGION = AWS_REGION or os.getenv("AWS_REGION")
        self.AWS_PROFILE = AWS_PROFILE or os.getenv("AWS_PROFILE")
        
        if not self.AWS_REGION:
            logger.warning("AWS_REGION not provided or found in environment. Bedrock calls may fail or use default region.")
            # It might still work if a default region is configured in AWS environment/profile.
            # However, explicit configuration is better.

        try:
            if self.AWS_PROFILE:
                logger.info(f"Creating boto3 session with profile: {self.AWS_PROFILE} and region: {self.AWS_REGION}")
                session = boto3.Session(profile_name=self.AWS_PROFILE, region_name=self.AWS_REGION)
            else:
                logger.info(f"Creating boto3 session with default credentials and region: {self.AWS_REGION}")
                session = boto3.Session(region_name=self.AWS_REGION)
            
            # Test credentials early by trying to get caller identity
            sts_client = session.client("sts")
            try:
                sts_client.get_caller_identity()
                logger.info("AWS STS GetCallerIdentity successful, credentials seem valid.")
            except (NoCredentialsError, PartialCredentialsError) as e:
                logger.error(f"AWS credentials not found or incomplete: {e}")
                raise ConfigurationError(f"AWS credentials not found or incomplete: {e}")
            except ClientError as e:
                # Handle other STS ClientErrors that might indicate auth problems
                error_code = e.response.get('Error', {}).get('Code')
                if error_code == 'InvalidClientTokenId' or error_code == 'SignatureDoesNotMatch':
                    logger.error(f"AWS STS authentication failure: {e}")
                    raise ConfigurationError(f"AWS authentication failed (STS): {e}")
                logger.warning(f"AWS STS GetCallerIdentity failed with ClientError (possibly ignorable if other services work): {e}")
                # Not raising ConfigurationError here for all ClientErrors from STS, as it might be overly strict
                # if the target Bedrock region/service is accessible via other means (e.g. instance profile)

            self.bedrock_runtime_client = session.client("bedrock-runtime")
            self.bedrock_client = session.client("bedrock")
            logger.info("BedrockService initialized with Bedrock clients.")

        except ConfigurationError: # Re-raise ConfigurationError from STS check
            raise
        except (NoCredentialsError, PartialCredentialsError) as e: # Should be caught by STS check, but as fallback
            logger.error(f"AWS credentials issue during Bedrock client initialization: {e}")
            raise ConfigurationError(f"AWS credentials not found or incomplete for Bedrock: {e}")
        except BotoCoreError as e: # Catch other BotoCore errors like ProfileNotFound
            logger.error(f"BotoCoreError during Bedrock client initialization: {e}")
            raise ConfigurationError(f"AWS SDK (BotoCore) error during Bedrock init: {e}")
        except Exception as e: # General catch-all for other unexpected init errors
            logger.error(f"Failed to initialize BedrockService clients: {e}")
            raise ConfigurationError(f"Failed to initialize AWS Bedrock clients: {e}")

    def _handle_bedrock_client_error(self, e: ClientError, model_id: str):
        error_code = e.response.get('Error', {}).get('Code')
        error_message = e.response.get('Error', {}).get('Message', str(e))
        status_code = e.response.get('ResponseMetadata', {}).get('HTTPStatusCode')
        
        logger.error(f"Bedrock API ClientError: Model={model_id}, Code={error_code}, Message={error_message}, Status={status_code}")

        if error_code == 'AccessDeniedException':
            raise ServiceAuthenticationError(f"Bedrock Access Denied for model {model_id}: {error_message}")
        elif error_code == 'ResourceNotFoundException':
            raise ServiceModelNotFoundError(f"Bedrock model {model_id} not found or access denied: {error_message}")
        elif error_code == 'ThrottlingException':
            raise ServiceRateLimitError(f"Bedrock API rate limit exceeded for model {model_id}: {error_message}")
        elif error_code == 'ModelTimeoutException' or error_code == 'ServiceUnavailableException' or (status_code and status_code == 503):
            raise ServiceUnavailableError(f"Bedrock service unavailable or model timeout for {model_id}: {error_message}")
        elif error_code == 'ValidationException': # Input validation issues
            raise ServiceApiError(f"Bedrock validation error for model {model_id}: {error_message} (Request may be malformed)")
        elif status_code and 500 <= status_code < 600:
            raise ServiceApiError(f"Bedrock server error (status: {status_code}) for model {model_id}: {error_message}")
        else: # Fallback for other ClientErrors
            raise ServiceApiError(f"Bedrock API ClientError for model {model_id}: {error_message} (Code: {error_code})")

    def _prepare_anthropic_claude_messages(self, messages: List[Message]) -> List[Dict[str, Any]]:
        claude_messages = []
        system_prompt = None
        for msg in messages:
            if msg.role == "system":
                system_prompt = msg.content
                continue
            if msg.role == "user" or msg.role == "assistant":
                claude_messages.append({"role": msg.role, "content": msg.content})
        return claude_messages, system_prompt

    async def _invoke_anthropic_claude_stream(self, model_id: str, bedrock_payload: Dict[str, Any]) -> AsyncGenerator[ChatCompletionChunk, None]:
        try:
            response_stream = await asyncio.to_thread(
                self.bedrock_runtime_client.invoke_model_with_response_stream,
                modelId=model_id,
                body=json.dumps(bedrock_payload)
            )
            
            chunk_id_prefix = f"chatcmpl-br-{int(time.time())}"
            chunk_index = 0
            
            # Get the body stream
            event_stream = response_stream["body"]
            
            # Process events from the stream
            for event in event_stream:
                chunk_data = json.loads(event["chunk"]["bytes"])
                delta_content = ""
                finish_reason = None
                role = "assistant"

                if chunk_data["type"] == "content_block_delta":
                    delta_content = chunk_data.get("delta", {}).get("text", "")
                elif chunk_data["type"] == "message_delta": 
                    delta_payload = chunk_data.get("delta", {})
                    finish_reason = delta_payload.get("stop_reason")
                elif chunk_data["type"] == "message_stop":
                    # This might not have content but confirms end of message with metrics
                    # If finish_reason wasn't in message_delta, it might be inferred here or from invocation metrics
                    pass 

                yield ChatCompletionChunk(
                    id=f"{chunk_id_prefix}-{chunk_index}",
                    object="chat.completion.chunk",
                    created=int(time.time()), 
                    model=model_id,
                    choices=[
                        ChatCompletionChunkChoice(
                            index=0,
                            delta=ChoiceDelta(content=delta_content, role=role if delta_content or chunk_index == 0 else None),
                            finish_reason=finish_reason
                        )
                    ]
                )
                chunk_index += 1
                if finish_reason:
                    logger.debug(f"Bedrock stream for {model_id} finished with reason: {finish_reason}")
                    break

            # Ensure we close the stream
            event_stream.close()

        except ClientError as e:
            self._handle_bedrock_client_error(e, model_id)
        except Exception as e:
            logger.error(f"Error processing Bedrock (Claude Stream) response for {model_id}: {e}")
            raise StreamingError(f"Error during Bedrock stream processing for {model_id}: {str(e)}")

    async def _invoke_anthropic_claude_non_stream(self, model_id: str, bedrock_payload: Dict[str, Any]) -> ChatCompletionResponse:
        try:
            response = await asyncio.to_thread( # Wrap synchronous boto3 call
                self.bedrock_runtime_client.invoke_model,
                modelId=model_id,
                body=json.dumps(bedrock_payload)
            )
            response_body = json.loads(response["body"].read())
            
            assistant_content = ""
            if response_body.get("content") and isinstance(response_body["content"], list):
                for block in response_body["content"]:
                    if block["type"] == "text":
                        assistant_content += block["text"]
            
            return ChatCompletionResponse(
                id=f"chatcmpl-br-{int(time.time())}",
                object="chat.completion",
                created=int(time.time()), 
                model=model_id,
                choices=[
                    CoreChatCompletionChoice(
                        index=0,
                        message=Message(role="assistant", content=assistant_content),
                        finish_reason=response_body.get("stop_reason")
                    )
                ],
            )
        except ClientError as e:
            self._handle_bedrock_client_error(e, model_id)
        except Exception as e: # Catch-all for other errors (e.g., JSON parsing)
            logger.error(f"Error processing Bedrock (Claude Non-Stream) response for {model_id}: {type(e).__name__} - {e}")
            raise ServiceApiError(f"Unexpected error processing Bedrock response for {model_id}: {type(e).__name__} - {str(e)}")

    async def chat_completion(
        self,
        messages: List[Message],
        model_id: Optional[str] = None,
        stream: bool = False,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Union[ChatCompletionResponse, AsyncGenerator[ChatCompletionChunk, None]]:
        if not model_id:
            # This is a programming error if called without model_id from within the system
            raise ValueError("model_id must be provided for Bedrock chat completion.")

        provider = get_provider_from_bedrock_model_id(model_id)
        logger.info(f"BedrockService: chat_completion for model: {model_id} (Provider: {provider}), Stream: {stream}")

        if provider == "anthropic":
            claude_messages, system_prompt = self._prepare_anthropic_claude_messages(messages)
            payload = {
                "anthropic_version": "bedrock-2023-05-31",
                "messages": claude_messages,
            }
            if system_prompt:
                payload["system"] = system_prompt
            if max_tokens:
                payload["max_tokens"] = max_tokens
            else: 
                payload["max_tokens"] = 2048 
            if temperature is not None:
                payload["temperature"] = temperature

            if stream:
                return self._invoke_anthropic_claude_stream(model_id, payload)
            else:
                return await self._invoke_anthropic_claude_non_stream(model_id, payload)
        else:
            logger.error(f"Unsupported Bedrock provider '{provider}' for model_id '{model_id}'.")
            # This should ideally be ServiceModelNotFoundError or a more specific "UnsupportedModelError"
            raise ServiceModelNotFoundError(f"Provider '{provider}' for Bedrock model '{model_id}' is not supported or model is invalid.")

    async def list_models(self) -> List[ModelProviderInfo]:
        logger.info(f"BedrockService: Fetching foundation models from Bedrock region: {self.AWS_REGION}")
        all_bedrock_models = []
        try:
            paginator = self.bedrock_client.get_paginator('list_foundation_models')
            for page in await asyncio.to_thread(lambda: list(paginator.paginate(byInferenceType='ON_DEMAND'))):
                for model_summary in page.get("modelSummaries", []):
                    if 'TEXT' in model_summary.get("outputModalities", []):
                        all_bedrock_models.append(
                            ModelProviderInfo(
                                id=model_summary["modelId"],
                                provider="bedrock",
                                display_name=model_summary.get("modelName", model_summary["modelId"])
                            )
                        )
            logger.info(f"Found {len(all_bedrock_models)} potential Bedrock models.")
            return all_bedrock_models
        except ClientError as e:
            # Handle specific errors like AccessDeniedException if needed for list_models
            logger.error(f"Bedrock API error listing models: {e}. Ensure Bedrock model access is enabled in region {self.AWS_REGION}.")
            self._handle_bedrock_client_error(e, "list_foundation_models") # Reuses handler, model_id is just for logging context
            return [] # Or re-raise as appropriate
        except Exception as e:
            logger.error(f"Unexpected error listing Bedrock models: {e}")
            raise ServiceApiError(f"Unexpected error listing Bedrock models: {str(e)}") 