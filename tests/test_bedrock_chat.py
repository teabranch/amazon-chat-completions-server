import pytest
import os
import json
from async_asgi_testclient import TestClient
from httpx import HTTPStatusError, StreamClosed
from fastapi import status

from src.amazon_chat_completions_server.api.app import app
from src.amazon_chat_completions_server.api.schemas.requests import ChatCompletionRequest, Message

# Check for Bedrock config (profile and region are primary for boto3 to work)
AWS_PROFILE_IS_SET = bool(os.getenv("AWS_PROFILE"))
AWS_REGION_IS_SET = bool(os.getenv("AWS_REGION"))
BEDROCK_CONFIGURED = AWS_PROFILE_IS_SET and AWS_REGION_IS_SET

# Default Bedrock model for testing - Anthropic Claude 3 Haiku
# Ensure this model is enabled in your AWS account for the specified region.
TEST_BEDROCK_CLAUDE_MODEL = os.getenv("TEST_BEDROCK_CLAUDE_MODEL", "us.anthropic.claude-3-7-sonnet-20250219-v1:0")

bedrock_integration_test = [
    pytest.mark.asyncio,
    pytest.mark.skipif(not BEDROCK_CONFIGURED, reason="AWS_PROFILE and/or AWS_REGION not set, skipping Bedrock integration tests.")
]

@pytest.fixture(scope="module")
async def client():
    """Create a test client for the FastAPI app."""
    async with TestClient(app) as client:
        yield client

@pytest.mark.asyncio
@pytest.mark.skipif(not BEDROCK_CONFIGURED, reason="AWS_PROFILE and/or AWS_REGION not set, skipping Bedrock integration tests.")
async def test_bedrock_claude_chat_completion_non_streaming(client: TestClient, test_api_key):
    headers = {"X-API-Key": test_api_key}
    payload = ChatCompletionRequest(
        model=TEST_BEDROCK_CLAUDE_MODEL,
        messages=[Message(role="user", content="Tell me a short story about a adventurous dog.")],
        stream=False,
        max_tokens=100 
    ).model_dump()

    response = await client.post("/v1/chat/completions", json=payload, headers=headers)
    
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    
    assert response_data["id"].startswith("chatcmpl-br-") # Bedrock service uses a "br" prefix for ID
    assert response_data["object"] == "chat.completion"
    assert response_data["model"] == TEST_BEDROCK_CLAUDE_MODEL
    assert len(response_data["choices"]) > 0
    choice = response_data["choices"][0]
    assert choice["message"]["role"] == "assistant"
    assert choice["message"]["content"] is not None
    assert len(choice["message"]["content"]) > 0
    # Claude finish reasons: "end_turn", "max_tokens", "stop_sequence"
    assert choice["finish_reason"] in ["end_turn", "max_tokens", "stop_sequence"]

@pytest.mark.asyncio
@pytest.mark.skipif(not BEDROCK_CONFIGURED, reason="AWS_PROFILE and/or AWS_REGION not set, skipping Bedrock integration tests.")
async def test_bedrock_claude_chat_completion_streaming(client: TestClient, test_api_key):
    payload = {
        "api_key": test_api_key, 
        "model": TEST_BEDROCK_CLAUDE_MODEL,
        "messages": [Message(role="user", content="What is the capital of France? Stream your answer.").model_dump()],
        "stream": True,
        "max_tokens": 50
    }

    received_chunks = []
    full_content = ""
    
    async with client.websocket_connect("/v1/chat/completions/stream", headers={"X-API-Key": test_api_key}) as websocket:
        await websocket.send_json(payload)
        try:
            while True:
                try:
                    data = await websocket.receive_json()
                    received_chunks.append(data)
                    if data.get("choices") and data["choices"][0].get("delta", {}).get("content"):
                        full_content += data["choices"][0]["delta"]["content"]
                    if data.get("choices") and data["choices"][0].get("finish_reason"):
                        break
                except TimeoutError:
                    print("Timeout waiting for message, continuing...")
                    continue
        except StreamClosed:
            if not full_content:
                assert False, "WebSocket closed without receiving any content"
            print("Stream closed after receiving content")

    assert len(received_chunks) > 0, "No chunks received from Bedrock streaming endpoint"
    assert len(full_content) > 0, "No content received from stream"

    final_chunk_finish_reason = None
    for i, chunk in enumerate(received_chunks):
        assert chunk["id"].startswith("chatcmpl-br-")
        assert chunk["object"] == "chat.completion.chunk"
        assert chunk["model"] == TEST_BEDROCK_CLAUDE_MODEL
        assert len(chunk["choices"]) > 0
        if chunk["choices"][0]["finish_reason"]:
            final_chunk_finish_reason = chunk["choices"][0]["finish_reason"]
            assert i == len(received_chunks) - 1, "finish_reason should be in the last chunk"
    
    assert final_chunk_finish_reason in ["end_turn", "max_tokens", "stop_sequence"], f"Unexpected finish reason: {final_chunk_finish_reason}"

# Add tests for other Bedrock models (Titan, Llama2, etc.) once service supports them.
# Add tests for Bedrock specific error handling (e.g., model access denied, throttling). 