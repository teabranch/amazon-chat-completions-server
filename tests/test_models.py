import pytest
import os
from httpx import AsyncClient, ASGITransport
from fastapi import status

from src.open_amazon_chat_completions_server.api.app import app # Main FastAPI app

# Use the test API key from conftest.py
OPENAI_API_KEY_IS_SET = bool(os.getenv("OPENAI_API_KEY"))

openai_integration_test = [
    pytest.mark.asyncio,
    pytest.mark.external_api,
    pytest.mark.openai_integration,
    pytest.mark.skipif(not OPENAI_API_KEY_IS_SET, reason="OPENAI_API_KEY not set, skipping integration tests for models.")
]

pytestmark = openai_integration_test

@pytest.fixture(scope="module")
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

async def test_list_models_success(client: AsyncClient, test_api_key):
    """Test successful listing of models, expecting OpenAI models."""
    headers = {"Authorization": f"Bearer {test_api_key}"}
    response = await client.get("/v1/models", headers=headers)
    
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["object"] == "list"
    assert isinstance(response_data["data"], list)
    
    # Check if at least one model is returned (assuming OpenAI key is valid and has access)
    assert len(response_data["data"]) > 0 
    
    # Check structure of a model item
    if response_data["data"]:
        model_item = response_data["data"][0]
        assert "id" in model_item
        assert model_item["object"] == "model"
        assert model_item["owned_by"] == "openai" # Since we are testing OpenAI path

async def test_list_models_unauthorized_missing_key(client: AsyncClient):
    """Test listing models with missing API key."""
    response = await client.get("/v1/models")
    assert response.status_code == status.HTTP_403_FORBIDDEN
    content = response.json()
    # Expecting the new dictionary structure for detail
    error_content = content["error"]
    assert error_content["message"] == "Not authenticated"
    assert error_content["type"] == "api_error"
    assert error_content["code"] == 403

async def test_list_models_unauthorized_invalid_key(client: AsyncClient):
    """Test listing models with an invalid API key."""
    headers = {"Authorization": "Bearer invalid-api-key"}
    response = await client.get("/v1/models", headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    content = response.json()
    # Expecting the new dictionary structure for detail
    error_content = content["error"]
    assert error_content["message"] == "Invalid API key"
    assert error_content["type"] == "api_error"
    assert error_content["code"] == 403 