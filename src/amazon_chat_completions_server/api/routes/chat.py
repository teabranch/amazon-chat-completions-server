from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException, status
from ..schemas.requests import ChatCompletionRequest as APIRequest # API layer schema
from ..middleware.auth import verify_api_key
from src.amazon_chat_completions_server.services.llm_service_factory import LLMServiceFactory
# Import custom exceptions from the service layer and core
from src.amazon_chat_completions_server.core.exceptions import (
    ConfigurationError, 
    ModelNotFoundError,
    ServiceAuthenticationError, 
    ServiceModelNotFoundError, 
    ServiceApiError,
    ServiceUnavailableError
)
from src.amazon_chat_completions_server.core.models import Message as CoreMessage # Service layer model
import json
import logging
import os

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/v1/chat/completions", dependencies=[Depends(verify_api_key)])
async def chat_completions(
    request: APIRequest,
):
    try:
        llm_service = LLMServiceFactory.get_service_for_model(request.model)
    except ModelNotFoundError as e: # From Factory if model alias is unknown
        logger.warning(f"Model not found via factory for '{request.model}': {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ConfigurationError as e: # From Service init (e.g. missing API key)
        logger.error(f"Configuration error for model '{request.model}': {e}")
        # This is a server-side configuration issue, so 500 is appropriate.
        # Could argue for 503 if it's a temporary config issue preventing service start.
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Server configuration error: {str(e)}")
    except NotImplementedError as e: # From Factory if service not implemented
        logger.error(f"Service not implemented for model '{request.model}': {e}")
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(e))
    except Exception as e: # Catch any other unexpected errors during service retrieval
        logger.error(f"Unexpected error getting LLM service for model '{request.model}': {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error obtaining LLM service: {str(e)}")

    core_messages = [CoreMessage(**msg.model_dump()) for msg in request.messages]
    
    try:
        response_data = await llm_service.chat_completion(
            messages=core_messages,
            model_id=request.model,
            stream=False,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            # Pass other relevant parameters from request if your service method accepts them
            # e.g., tools=request.tools, tool_choice=request.tool_choice
        )
        return response_data
    except ServiceAuthenticationError as e:
        logger.error(f"Service Authentication Error for model {request.model}: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except ServiceModelNotFoundError as e: # From Service if model not found by provider
        logger.error(f"Service Model Not Found Error for model {request.model}: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ServiceUnavailableError as e:
        logger.error(f"Service Unavailable Error for model {request.model}: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except ServiceApiError as e: # Generic API error from the service
        logger.error(f"Service API Error for model {request.model}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except ValueError as e: # e.g. if model_id was somehow None in service call, or other validation
        logger.warning(f"ValueError during chat completion for model {request.model}: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e: # Catch-all for other unexpected errors during the call
        logger.error(f"Unexpected error during non-streaming chat completion for model {request.model}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"LLM service error: {str(e)}")

@router.websocket("/v1/chat/completions/stream")
async def chat_completion_stream(websocket: WebSocket):
    await websocket.accept()
    llm_service = None
    request_model_id = None # Initialize to avoid UnboundLocalError in finally if init fails
    
    try:
        initial_data_text = await websocket.receive_text()
        initial_data = json.loads(initial_data_text)

        server_api_key = os.getenv("API_KEY")
        client_sent_api_key = initial_data.pop("api_key", None)

        if not server_api_key or client_sent_api_key != server_api_key:
            logger.warning("WebSocket authentication failed: Invalid or missing API key.")
            await websocket.send_json({"error": "Authentication failed", "code": status.WS_1008_POLICY_VIOLATION}) # Use standard code
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        request_model_id = initial_data.get("model")
        api_messages = initial_data.get("messages", [])
        if not request_model_id or not api_messages:
            logger.warning("WebSocket request missing model or messages.")
            await websocket.send_json({"error": "Missing model or messages in request", "code": status.WS_1003_UNSUPPORTED_DATA}) # Or 1007 for invalid format
            await websocket.close(code=status.WS_1003_UNSUPPORTED_DATA)
            return
        
        # Validate messages format if necessary, e.g. using Pydantic models
        # For simplicity, direct conversion is shown.
        core_messages = [CoreMessage(**msg) for msg in api_messages]

        llm_service = LLMServiceFactory.get_service_for_model(request_model_id)
        
        # Get the streaming response generator
        stream_response = await llm_service.chat_completion(
            messages=core_messages, 
            model_id=request_model_id, 
            stream=True,
            temperature=initial_data.get("temperature"),
            max_tokens=initial_data.get("max_tokens")
            # Pass other relevant params from initial_data
        )
        
        # Ensure we got an async generator
        if not hasattr(stream_response, '__aiter__'):
            logger.error(f"Expected async generator from chat_completion, got {type(stream_response)}")
            await websocket.send_json({"error": "Internal server error", "code": status.WS_1011_INTERNAL_ERROR})
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
            return

        # Stream the chunks to the client
        async for chunk in stream_response:
            await websocket.send_json(chunk.model_dump())
        
        # Normal closure after streaming all chunks
        await websocket.close(code=status.WS_1000_NORMAL_CLOSURE)

    except WebSocketDisconnect:
        logger.info(f"Client disconnected from WebSocket (model: {request_model_id}).")
    except json.JSONDecodeError:
        logger.warning("WebSocket received invalid JSON.")
        # Try to send error, then close. Websocket might already be closing.
        try:
            await websocket.send_json({"error": "Invalid JSON format", "code": status.WS_1007_INVALID_FRAME_PAYLOAD_DATA})
        except Exception: pass
        try:
            await websocket.close(code=status.WS_1007_INVALID_FRAME_PAYLOAD_DATA)
        except Exception: pass
    except (ModelNotFoundError, ServiceModelNotFoundError) as e:
        logger.warning(f"WebSocket: Model not found for '{request_model_id}': {e}")
        error_payload = {"error": f"Model not found: {str(e)}", "code": 4004} # Custom app code
        try: await websocket.send_json(error_payload)
        except Exception: pass
        try: await websocket.close(code=status.WS_1008_POLICY_VIOLATION) # Model not found could be policy issue
        except Exception: pass
    except (ConfigurationError, ServiceAuthenticationError) as e:
        logger.error(f"WebSocket: Configuration or Auth Error for model '{request_model_id}': {e}")
        error_payload = {"error": f"Configuration or Authentication Error: {str(e)}", "code": 4003} # Custom app code
        try: await websocket.send_json(error_payload)
        except Exception: pass
        try: await websocket.close(code=status.WS_1008_POLICY_VIOLATION) # Auth/config issues are policy
        except Exception: pass
    except (ServiceApiError, ServiceUnavailableError, NotImplementedError) as e:
        logger.error(f"WebSocket: Service API/Unavailable/NotImplemented Error for model '{request_model_id}': {e}")
        error_payload = {"error": f"LLM Service Error: {str(e)}", "code": 5003} # Custom app code for general service issues
        try: await websocket.send_json(error_payload)
        except Exception: pass
        try: await websocket.close(code=status.WS_1011_INTERNAL_ERROR) # Service error is internal
        except Exception: pass
    except Exception as e: # Generic catch-all for other errors
        logger.error(f"Generic WebSocket Error (model: {request_model_id}): {type(e).__name__} - {e}")
        error_payload = {"error": f"Unexpected WebSocket error: {str(e)}", "code": 5000} # Custom general error
        try:
            await websocket.send_json(error_payload)
        except Exception: pass # Websocket might already be closed
    finally:
        # Ensure graceful closure if not already closed
        if websocket.client_state != websocket.client_state.DISCONNECTED:
            try:
                await websocket.close(code=status.WS_1001_GOING_AWAY if llm_service else status.WS_1011_INTERNAL_ERROR)
            except RuntimeError: # Already closed
                pass 