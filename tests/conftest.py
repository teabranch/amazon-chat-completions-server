import os

import pytest

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


# Knowledge Base specific fixtures
@pytest.fixture
def sample_kb_config():
    """Sample Knowledge Base configuration for testing."""
    return {
        "name": "test-kb",
        "description": "Test knowledge base",
        "role_arn": "arn:aws:iam::123456789012:role/test-role",
        "storage_configuration": {
            "type": "OPENSEARCH_SERVERLESS",
            "opensearchServerlessConfiguration": {
                "collectionArn": "arn:aws:aoss:us-east-1:123456789012:collection/test-collection",
                "vectorIndexName": "test-index",
                "fieldMapping": {
                    "vectorField": "vector",
                    "textField": "text",
                    "metadataField": "metadata",
                },
            },
        },
    }


@pytest.fixture
def mock_aws_credentials():
    """Mock AWS credentials for testing."""
    import os

    original_values = {}

    # Set test credentials
    test_env = {
        "AWS_REGION": "us-east-1",
        "AWS_ACCESS_KEY_ID": "test-access-key",
        "AWS_SECRET_ACCESS_KEY": "test-secret-key",
    }

    # Backup original values
    for key in test_env:
        original_values[key] = os.environ.get(key)
        os.environ[key] = test_env[key]

    yield test_env

    # Restore original values
    for key, value in original_values.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


@pytest.fixture(autouse=True, scope="function")
def kb_test_cleanup():
    """Automatically cleanup KB test resources after each test."""
    # This fixture runs before each test
    yield

    # This runs after each test - cleanup would go here
    # Since we're using mocks, no real cleanup needed for unit tests
    # But in integration tests, you would cleanup real resources here
    pass


@pytest.fixture
def kb_test_markers():
    """Provide pytest markers for KB tests."""
    return {
        "unit": "knowledge_base and unit",
        "integration": "knowledge_base and integration",
        "service": "knowledge_base and service",
        "api": "knowledge_base and api",
        "cli": "knowledge_base and cli",
        "detector": "knowledge_base and detector",
    }
