import pytest
import os

# Set environment variables BEFORE any imports to ensure they're available when modules load
os.environ["API_KEY"] = "test-api-key"
if not os.getenv("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = "test-openai-key"

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables before any tests run"""
    # Environment variables are already set above, but we keep this for cleanup
    yield
    
    # Cleanup after all tests
    if os.environ.get("API_KEY") == "test-api-key":
        del os.environ["API_KEY"]
    if os.environ.get("OPENAI_API_KEY") == "test-openai-key":
        del os.environ["OPENAI_API_KEY"]


@pytest.fixture(scope="session")
def test_api_key():
    """Provide the test API key for use in tests"""
    return "test-api-key" 