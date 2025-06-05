import pytest
from fastapi.testclient import TestClient
from src.open_amazon_chat_completions_server.api.app import app # Adjusted import path

client = TestClient(app)

@pytest.mark.unit
def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"} 