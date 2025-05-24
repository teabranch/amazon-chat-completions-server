import pytest
import os
import json
from async_asgi_testclient import TestClient
from httpx import HTTPStatusError, StreamClosed
from fastapi import status

from src.amazon_chat_completions_server.api.app import app
from src.amazon_chat_completions_server.api.schemas.requests import ChatCompletionRequest, Message

# Remove old synchronous TestClient related imports if any are left specifically for it.
# from fastapi.testclient import TestClient # Should not be needed anymore

# Required environment variables with defaults for testing
SERVER_API_KEY = os.getenv("API_KEY")
if not SERVER_API_KEY:
    SERVER_API_KEY = "test-api-key"
    os.environ["API_KEY"] = SERVER_API_KEY

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_KEY_IS_SET = bool(OPENAI_API_KEY)
if not OPENAI_API_KEY_IS_SET:
    print("Warning: OPENAI_API_KEY not set, some tests will be skipped")

TEST_OPENAI_MODEL = os.getenv("TEST_OPENAI_MODEL", "gpt-4o")

openai_integration_test = [
    pytest.mark.asyncio,
    pytest.mark.skipif(not OPENAI_API_KEY_IS_SET, reason="OPENAI_API_KEY not set, skipping OpenAI integration tests.")
]

@pytest.fixture(scope="module")
async def client():
    """Create a test client for the FastAPI app."""
    # Initialize with base URL and headers
    async with TestClient(app) as client:
        client.headers.update({"host": "testserver"})
        yield client

# --- Auth and Basic Validation Tests (Async) ---
@pytest.mark.asyncio
async def test_chat_unauthorized_missing_key(client: TestClient):
    payload = ChatCompletionRequest(
        model="test-model",
        messages=[Message(role="user", content="Hello")]
    ).model_dump()
    response = await client.post("/v1/chat/completions", json=payload)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    error_content = response.json()["error"]
    assert error_content["message"] == "Not authenticated"
    assert error_content["type"] == "api_error"
    assert error_content["code"] == 403

@pytest.mark.asyncio
async def test_chat_unauthorized_invalid_key(client: TestClient):
    headers = {"X-API-Key": "invalid-key"}
    payload = ChatCompletionRequest(
        model="test-model",
        messages=[Message(role="user", content="Hello")]
    ).model_dump()
    response = await client.post("/v1/chat/completions", json=payload, headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    error_content = response.json()["error"]
    assert error_content["message"] == "Invalid API key"
    assert error_content["type"] == "api_error"
    assert error_content["code"] == 403

@pytest.mark.asyncio
async def test_chat_invalid_payload_empty_messages(client: TestClient):
    headers = {"X-API-Key": SERVER_API_KEY}
    payload = {"model": "test-model", "messages": []} # Invalid: messages is empty
    response = await client.post("/v1/chat/completions", json=payload, headers=headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

# --- OpenAI Integration Tests (Async) --- 
@pytest.mark.asyncio
@pytest.mark.skipif(not OPENAI_API_KEY_IS_SET, reason="OPENAI_API_KEY not set, skipping OpenAI integration tests.")
async def test_openai_chat_completion_non_streaming(client: TestClient):
    """Test non-streaming chat completion with OpenAI."""
    headers = {"X-API-Key": SERVER_API_KEY}
    payload = ChatCompletionRequest(
        model=TEST_OPENAI_MODEL,
        messages=[Message(role="user", content="Tell me a short joke.")],
        stream=False,
        max_tokens=50
    ).model_dump()

    response = await client.post("/v1/chat/completions", json=payload, headers=headers)
    
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    
    assert response_data["id"].startswith("chatcmpl-")
    assert response_data["object"] == "chat.completion"
    assert response_data["model"].startswith(TEST_OPENAI_MODEL) 
    assert len(response_data["choices"]) > 0
    choice = response_data["choices"][0]
    assert choice["message"]["role"] == "assistant"
    assert choice["message"]["content"] is not None
    assert len(choice["message"]["content"]) > 0
    assert choice["finish_reason"] == "stop" or choice["finish_reason"] == "length"

@pytest.mark.asyncio
@pytest.mark.skipif(not OPENAI_API_KEY_IS_SET, reason="OPENAI_API_KEY not set, skipping OpenAI integration tests.")
async def test_openai_chat_completion_streaming(client: TestClient):
    """Test streaming chat completion with OpenAI - expecting successful connection."""
    path = "/v1/chat/completions/stream"
    payload = {
        "api_key": SERVER_API_KEY,  # Use the server API key for authentication
        "model": TEST_OPENAI_MODEL,
        "messages": [Message(role="user", content="Hello OpenAI! Stream a short response.").model_dump()],
        "stream": True,
        "max_tokens": 10
    }
    
    async with client.websocket_connect(path, headers={"X-API-Key": SERVER_API_KEY}) as websocket:
        await websocket.send_json(payload)
        full_content = ""
        try:
            while True:
                try:
                    received_data = await websocket.receive_json()
                    if received_data.get("choices") and received_data["choices"][0].get("delta", {}).get("content"):
                        full_content += received_data["choices"][0]["delta"]["content"]
                    if received_data.get("choices") and received_data["choices"][0].get("finish_reason"):
                        break
                except TimeoutError:
                    print("Timeout waiting for message, continuing...")
                    continue
        except StreamClosed:
            if not full_content:
                assert False, "WebSocket closed without receiving any content"
            print("Stream closed after receiving content")

    assert received_data is not None, "No data received over WebSocket"
    assert "choices" in received_data, "Received data does not contain 'choices'"
    assert len(received_data["choices"]) > 0, "'choices' list is empty"
    assert received_data["choices"][0].get("delta") is not None or received_data["choices"][0].get("message") is not None, "No delta or message in choices"
    assert len(full_content) > 0, "No content received from stream"

@pytest.mark.asyncio
@pytest.mark.skipif(not OPENAI_API_KEY_IS_SET, reason="OPENAI_API_KEY not set, skipping OpenAI integration tests.")
async def test_openai_chat_stream_auth_fail(client: TestClient):
    """Test streaming auth failure for WebSocket."""
    payload = {
        "api_key": "invalid-ws-key", 
        "model": TEST_OPENAI_MODEL,
        "messages": [Message(role="user", content="Hello").model_dump()],
        "stream": True
    }
    
    async with client.websocket_connect("/v1/chat/completions/stream") as websocket:
        await websocket.send_json(payload)
        try:
            received_error = await websocket.receive_json()
            assert received_error.get("error") == "Authentication failed", f"Unexpected error message: {received_error}"
            assert received_error.get("code") == 1008, f"Unexpected error code in JSON: {received_error}"
        except StreamClosed:
            # Expected behavior - server should close connection after auth failure
            pass

# Old synchronous tests (dummy responses) are removed as we now have async integration tests.
# If any specific synchronous unit tests for logic (not I/O) are needed, they can be added separately. 