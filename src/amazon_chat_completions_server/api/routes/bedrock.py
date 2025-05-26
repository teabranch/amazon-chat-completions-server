from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from typing import Union
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
from ...adapters.bedrock_to_openai_adapter import BedrockToOpenAIAdapter
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


def create_reverse_service(openai_model: str) -> BedrockToOpenAIAdapter:
    """Create a reverse integration service for the specified OpenAI model"""
    try:
        return BedrockToOpenAIAdapter(openai_model_id=openai_model)
    except ConfigurationError as e:
        logger.error(f"Configuration error for reverse service with model '{openai_model}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server configuration error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error creating reverse service for model '{openai_model}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error creating service: {str(e)}"
        )


@router.post("/bedrock/claude/invoke-model", dependencies=[Depends(verify_api_key)])
async def invoke_claude_model(
    request: BedrockClaudeRequest,
    openai_model: str = Query(default="gpt-4o-mini", description="OpenAI model to use for processing")
) -> BedrockClaudeResponse:
    """Bedrock Claude-compatible endpoint that routes to OpenAI"""
    try:
        service = create_reverse_service(openai_model)
        response = await service.chat_completion_bedrock(request, original_format="claude")
        return response
    except ServiceAuthenticationError as e:
        logger.error(f"Service Authentication Error for Claude request: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except ServiceModelNotFoundError as e:
        logger.error(f"Service Model Not Found Error for Claude request: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ServiceUnavailableError as e:
        logger.error(f"Service Unavailable Error for Claude request: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except (ServiceApiError, LLMIntegrationError) as e:
        logger.error(f"Service API Error for Claude request: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except ValueError as e:
        logger.warning(f"ValueError during Claude request processing: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during Claude request processing: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        )


@router.post("/bedrock/claude/invoke-model-stream", dependencies=[Depends(verify_api_key)])
async def invoke_claude_model_stream(
    request: BedrockClaudeRequest,
    openai_model: str = Query(default="gpt-4o-mini", description="OpenAI model to use for processing")
):
    """Bedrock Claude-compatible streaming endpoint"""
    try:
        service = create_reverse_service(openai_model)
        
        async def generate_claude_stream():
            try:
                async for chunk in service.stream_chat_completion_bedrock(request, original_format="claude"):
                    # Convert chunk to JSON and format as SSE
                    if isinstance(chunk, BedrockClaudeStreamChunk):
                        chunk_data = chunk.model_dump()
                        yield f"data: {json.dumps(chunk_data)}\n\n"
                
                # Send final event to indicate completion
                yield "data: [DONE]\n\n"
                
            except Exception as e:
                logger.error(f"Error in Claude streaming: {e}")
                error_data = {"error": str(e), "type": "error"}
                yield f"data: {json.dumps(error_data)}\n\n"
        
        return StreamingResponse(
            generate_claude_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
            }
        )
    except Exception as e:
        logger.error(f"Error setting up Claude streaming: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Streaming setup error: {str(e)}"
        )


@router.post("/bedrock/titan/invoke-model", dependencies=[Depends(verify_api_key)])
async def invoke_titan_model(
    request: BedrockTitanRequest,
    openai_model: str = Query(default="gpt-4o-mini", description="OpenAI model to use for processing")
) -> BedrockTitanResponse:
    """Bedrock Titan-compatible endpoint that routes to OpenAI"""
    try:
        service = create_reverse_service(openai_model)
        response = await service.chat_completion_bedrock(request, original_format="titan")
        return response
    except ServiceAuthenticationError as e:
        logger.error(f"Service Authentication Error for Titan request: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except ServiceModelNotFoundError as e:
        logger.error(f"Service Model Not Found Error for Titan request: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ServiceUnavailableError as e:
        logger.error(f"Service Unavailable Error for Titan request: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except (ServiceApiError, LLMIntegrationError) as e:
        logger.error(f"Service API Error for Titan request: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except ValueError as e:
        logger.warning(f"ValueError during Titan request processing: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during Titan request processing: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        )


@router.post("/bedrock/titan/invoke-model-stream", dependencies=[Depends(verify_api_key)])
async def invoke_titan_model_stream(
    request: BedrockTitanRequest,
    openai_model: str = Query(default="gpt-4o-mini", description="OpenAI model to use for processing")
):
    """Bedrock Titan-compatible streaming endpoint"""
    try:
        service = create_reverse_service(openai_model)
        
        async def generate_titan_stream():
            try:
                async for chunk in service.stream_chat_completion_bedrock(request, original_format="titan"):
                    # Convert chunk to JSON and format as SSE
                    if isinstance(chunk, BedrockTitanStreamChunk):
                        chunk_data = chunk.model_dump()
                        yield f"data: {json.dumps(chunk_data)}\n\n"
                
                # Send final event to indicate completion
                yield "data: [DONE]\n\n"
                
            except Exception as e:
                logger.error(f"Error in Titan streaming: {e}")
                error_data = {"error": str(e), "type": "error"}
                yield f"data: {json.dumps(error_data)}\n\n"
        
        return StreamingResponse(
            generate_titan_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
            }
        )
    except Exception as e:
        logger.error(f"Error setting up Titan streaming: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Streaming setup error: {str(e)}"
        )


# Health check endpoint for Bedrock compatibility
@router.get("/bedrock/health")
async def bedrock_health():
    """Health check endpoint for Bedrock reverse integration"""
    return {
        "status": "healthy",
        "service": "bedrock-reverse-integration",
        "supported_formats": ["claude", "titan"],
        "supported_models": ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo", "gpt-4-turbo"]
    } 