from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from typing import Union, Dict, Any, Optional
import json
import logging

from ..middleware.auth import verify_api_key
from ...core.bedrock_models import (
    BedrockClaudeRequest,
    BedrockTitanRequest,
    BedrockClaudeResponse,
    BedrockTitanResponse,
    BedrockClaudeStreamChunk,
    BedrockTitanStreamChunk
)
from ...core.models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionChunk
)
from ...utils.request_detector import RequestFormatDetector, RequestFormat
from ...adapters.bedrock_to_openai_adapter import BedrockToOpenAIAdapter
from ...services.llm_service_factory import LLMServiceFactory
from ...core.exceptions import (
    ConfigurationError,
    ModelNotFoundError,
    ServiceAuthenticationError,
    ServiceModelNotFoundError,
    ServiceApiError,
    ServiceUnavailableError,
    LLMIntegrationError
)

logger = logging.getLogger(__name__)
router = APIRouter()


def get_universal_service(
    request_data: Dict[str, Any],
    format_hint: Optional[str] = None,
    target_provider: Optional[str] = None,
    model_override: Optional[str] = None
):
    """Get appropriate service based on request format and routing preferences"""
    try:
        # Detect format if not provided
        if format_hint:
            if format_hint.lower() == "openai":
                detected_format = RequestFormat.OPENAI
            elif format_hint.lower() == "bedrock_claude":
                detected_format = RequestFormat.BEDROCK_CLAUDE
            elif format_hint.lower() == "bedrock_titan":
                detected_format = RequestFormat.BEDROCK_TITAN
            else:
                detected_format = RequestFormatDetector.detect_format(request_data)
        else:
            detected_format = RequestFormatDetector.detect_format(request_data)
        
        # Determine target provider and model
        if detected_format == RequestFormat.OPENAI:
            model_id = model_override or request_data.get("model", "gpt-4o-mini")
            
            if target_provider == "bedrock":
                # Force Bedrock format response even for OpenAI request
                return BedrockToOpenAIAdapter(openai_model_id=model_id), "bedrock", model_id
            else:
                # Standard OpenAI processing
                return LLMServiceFactory.get_service("openai"), "openai", model_id
        
        elif detected_format in [RequestFormat.BEDROCK_CLAUDE, RequestFormat.BEDROCK_TITAN]:
            openai_model = model_override or "gpt-4o-mini"
            
            if target_provider == "openai":
                # Force OpenAI format response for Bedrock request
                return LLMServiceFactory.get_service("openai"), "openai", openai_model
            else:
                # Reverse integration: Bedrock format → OpenAI → Bedrock format
                return BedrockToOpenAIAdapter(openai_model_id=openai_model), "bedrock", openai_model
        
        else:
            raise ValueError(f"Unsupported request format: {detected_format}")
            
    except Exception as e:
        logger.error(f"Error creating universal service: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Service creation error: {str(e)}"
        )


@router.post("/v1/completions/universal", dependencies=[Depends(verify_api_key)])
async def universal_completion(
    request_data: Dict[str, Any],
    format_hint: Optional[str] = Query(None, description="Hint for request format: openai, bedrock_claude, bedrock_titan"),
    target_provider: Optional[str] = Query(None, description="Target provider: openai, bedrock"),
    model_override: Optional[str] = Query(None, description="Override model selection")
):
    """Universal endpoint that auto-detects format and routes appropriately"""
    try:
        # Get appropriate service and response format
        service, response_format, model_id = get_universal_service(
            request_data, format_hint, target_provider, model_override
        )
        
        # Detect the input format
        detected_format = RequestFormatDetector.detect_format(request_data)
        
        if detected_format == RequestFormat.OPENAI:
            # Process as OpenAI request
            openai_request = ChatCompletionRequest(**request_data)
            
            if response_format == "bedrock":
                # Convert to Bedrock response using reverse adapter
                bedrock_response = await service.chat_completion_bedrock(
                    openai_request, original_format="claude"
                )
                return bedrock_response
            else:
                # Standard OpenAI response
                openai_response = await service.chat_completion(openai_request)
                return openai_response
        
        elif detected_format == RequestFormat.BEDROCK_CLAUDE:
            # Process as Bedrock Claude request
            claude_request = BedrockClaudeRequest(**request_data)
            
            if response_format == "openai":
                # Convert to OpenAI response - first convert to OpenAI request, then process
                openai_request = service.convert_bedrock_to_openai_request(claude_request)
                openai_response = await service.chat_completion(openai_request)
                return openai_response
            else:
                # Bedrock Claude response
                bedrock_response = await service.chat_completion_bedrock(
                    claude_request, original_format="claude"
                )
                return bedrock_response
        
        elif detected_format == RequestFormat.BEDROCK_TITAN:
            # Process as Bedrock Titan request
            titan_request = BedrockTitanRequest(**request_data)
            
            if response_format == "openai":
                # Convert to OpenAI response - first convert to OpenAI request, then process
                openai_request = service.convert_bedrock_to_openai_request(titan_request)
                openai_response = await service.chat_completion(openai_request)
                return openai_response
            else:
                # Bedrock Titan response
                bedrock_response = await service.chat_completion_bedrock(
                    titan_request, original_format="titan"
                )
                return bedrock_response
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported request format: {detected_format}"
            )
    
    except ServiceAuthenticationError as e:
        logger.error(f"Service Authentication Error: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except ServiceModelNotFoundError as e:
        logger.error(f"Service Model Not Found Error: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ServiceUnavailableError as e:
        logger.error(f"Service Unavailable Error: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except (ServiceApiError, LLMIntegrationError) as e:
        logger.error(f"Service API Error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except ValueError as e:
        logger.warning(f"ValueError during universal completion: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during universal completion: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        )


@router.post("/v1/completions/universal/stream", dependencies=[Depends(verify_api_key)])
async def universal_completion_stream(
    request_data: Dict[str, Any],
    format_hint: Optional[str] = Query(None, description="Hint for request format: openai, bedrock_claude, bedrock_titan"),
    target_provider: Optional[str] = Query(None, description="Target provider: openai, bedrock"),
    model_override: Optional[str] = Query(None, description="Override model selection")
):
    """Universal streaming endpoint that auto-detects format and routes appropriately"""
    try:
        # Get appropriate service and response format
        service, response_format, model_id = get_universal_service(
            request_data, format_hint, target_provider, model_override
        )
        
        # Detect the input format
        detected_format = RequestFormatDetector.detect_format(request_data)
        
        async def generate_universal_stream():
            try:
                if detected_format == RequestFormat.OPENAI:
                    # Process as OpenAI request
                    openai_request = ChatCompletionRequest(**request_data)
                    openai_request.stream = True  # Ensure streaming is enabled
                    
                    if response_format == "bedrock":
                        # Stream Bedrock format
                        async for chunk in service.stream_chat_completion_bedrock(
                            openai_request, original_format="claude"
                        ):
                            chunk_data = chunk.model_dump()
                            yield f"data: {json.dumps(chunk_data)}\n\n"
                    else:
                        # Stream OpenAI format - pass model_id to chat_completion
                        from ...core.models import Message
                        messages = [Message(**msg.model_dump()) for msg in openai_request.messages]
                        async for chunk in await service.chat_completion(
                            messages=messages,
                            model_id=model_id,
                            stream=True,
                            temperature=openai_request.temperature,
                            max_tokens=openai_request.max_tokens,
                            tools=openai_request.tools,
                            tool_choice=openai_request.tool_choice
                        ):
                            chunk_data = chunk.model_dump()
                            yield f"data: {json.dumps(chunk_data)}\n\n"
                
                elif detected_format == RequestFormat.BEDROCK_CLAUDE:
                    # Process as Bedrock Claude request
                    claude_request = BedrockClaudeRequest(**request_data)
                    
                    if response_format == "openai":
                        # Stream OpenAI format
                        openai_request = service.convert_bedrock_to_openai_request(claude_request)
                        openai_request.stream = True
                        from ...core.models import Message
                        messages = [Message(**msg.model_dump()) for msg in openai_request.messages]
                        async for chunk in await service.chat_completion(
                            messages=messages,
                            model_id=model_id,
                            stream=True,
                            temperature=openai_request.temperature,
                            max_tokens=openai_request.max_tokens,
                            tools=openai_request.tools,
                            tool_choice=openai_request.tool_choice
                        ):
                            chunk_data = chunk.model_dump()
                            yield f"data: {json.dumps(chunk_data)}\n\n"
                    else:
                        # Stream Bedrock format
                        async for chunk in service.stream_chat_completion_bedrock(
                            claude_request, original_format="claude"
                        ):
                            chunk_data = chunk.model_dump()
                            yield f"data: {json.dumps(chunk_data)}\n\n"
                
                elif detected_format == RequestFormat.BEDROCK_TITAN:
                    # Process as Bedrock Titan request
                    titan_request = BedrockTitanRequest(**request_data)
                    
                    if response_format == "openai":
                        # Stream OpenAI format
                        openai_request = service.convert_bedrock_to_openai_request(titan_request)
                        openai_request.stream = True
                        from ...core.models import Message
                        messages = [Message(**msg.model_dump()) for msg in openai_request.messages]
                        async for chunk in await service.chat_completion(
                            messages=messages,
                            model_id=model_id,
                            stream=True,
                            temperature=openai_request.temperature,
                            max_tokens=openai_request.max_tokens,
                            tools=openai_request.tools,
                            tool_choice=openai_request.tool_choice
                        ):
                            chunk_data = chunk.model_dump()
                            yield f"data: {json.dumps(chunk_data)}\n\n"
                    else:
                        # Stream Bedrock format
                        async for chunk in service.stream_chat_completion_bedrock(
                            titan_request, original_format="titan"
                        ):
                            chunk_data = chunk.model_dump()
                            yield f"data: {json.dumps(chunk_data)}\n\n"
                
                # Send completion signal
                yield "data: [DONE]\n\n"
                
            except Exception as e:
                logger.error(f"Error in universal streaming: {e}")
                error_data = {"error": str(e), "type": "error"}
                yield f"data: {json.dumps(error_data)}\n\n"
        
        return StreamingResponse(
            generate_universal_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
            }
        )
    except Exception as e:
        logger.error(f"Error setting up universal streaming: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Streaming setup error: {str(e)}"
        )


# Health check endpoint for universal compatibility
@router.get("/v1/completions/universal/health")
async def universal_health():
    """Health check endpoint for universal format support"""
    return {
        "status": "healthy",
        "service": "universal-format-detection",
        "supported_input_formats": ["openai", "bedrock_claude", "bedrock_titan"],
        "supported_output_formats": ["openai", "bedrock"],
        "supported_models": ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"]
    } 