import pytest
from fastapi import FastAPI, Depends, HTTPException
from fastapi.testclient import TestClient

from src.open_amazon_chat_completions_server.api.middleware.auth import verify_api_key
from src.open_amazon_chat_completions_server.api.errors import http_exception_handler

# Create a dummy app to test the dependency
app = FastAPI()

@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request, exc):
    return await http_exception_handler(request, exc)

@app.get("/secure")
async def secure_endpoint(api_key: str = Depends(verify_api_key)):
    return {"message": "success", "api_key": api_key}

client = TestClient(app)

@pytest.mark.unit
def test_verify_api_key_valid():
    response = client.get("/secure", headers={"Authorization": "Bearer test-api-key"})
    assert response.status_code == 200
    assert response.json() == {"message": "success", "api_key": "test-api-key"}

@pytest.mark.unit
def test_verify_api_key_missing():
    response = client.get("/secure")
    assert response.status_code == 403
    assert response.json() == {
        "error": {
            "message": "Not authenticated",
            "type": "api_error",
            "code": 403
        }
    }

@pytest.mark.unit
def test_verify_api_key_invalid():
    response = client.get("/secure", headers={"Authorization": "Bearer invalid_key"})
    assert response.status_code == 403
    assert response.json() == {
        "error": {
            "message": "Invalid API key",
            "type": "api_error",
            "code": 403
        }
    } 