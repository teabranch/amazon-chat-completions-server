import pytest
import os
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from io import BytesIO

from src.open_amazon_chat_completions_server.api.app import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_file_service():
    """Mock the FileService to avoid actual S3 calls during testing."""
    with patch('src.open_amazon_chat_completions_server.api.routes.files.FileService') as mock_service:
        # Mock the service instance
        mock_instance = MagicMock()
        mock_service.return_value = mock_instance
        
        # Mock the upload_file method as async
        mock_metadata = MagicMock()
        mock_metadata.file_id = "file-abc123def456"
        mock_metadata.filename = "test.json"
        mock_metadata.purpose = "fine-tune"
        mock_metadata.file_size = 140
        
        # Create an async mock
        async def mock_upload_file(*args, **kwargs):
            return mock_metadata
        
        mock_instance.upload_file = mock_upload_file
        mock_instance.s3_bucket = "test-bucket"
        mock_instance.AWS_REGION = "us-east-1"
        
        yield mock_instance


@pytest.fixture
def auth_headers():
    """Provide authentication headers for testing."""
    return {"Authorization": "Bearer test-api-key"}


class TestFilesEndpoint:
    """Test cases for the /v1/files endpoint."""

    @patch.dict(os.environ, {"API_KEY": "test-api-key", "S3_FILES_BUCKET": "test-bucket"})
    def test_upload_file_success(self, client, mock_file_service, auth_headers):
        """Test successful file upload."""
        # Mock the get_file_service function to return our mock
        with patch('src.open_amazon_chat_completions_server.api.routes.files.get_file_service') as mock_get_service:
            mock_get_service.return_value = mock_file_service
            
            # Prepare test file
            test_content = b'{"prompt": "Hello", "completion": "Hi there!"}'
            files = {"file": ("test.json", BytesIO(test_content), "application/json")}
            data = {"purpose": "fine-tune"}
            
            # Make request
            response = client.post("/v1/files", files=files, data=data, headers=auth_headers)
            
            # Verify response
            assert response.status_code == 200
            response_data = response.json()
            
            assert response_data["id"] == "file-abc123def456"
            assert response_data["object"] == "file"
            assert response_data["filename"] == "test.json"
            assert response_data["purpose"] == "fine-tune"
            assert response_data["bytes"] == 140
            assert response_data["status"] == "uploaded"
            assert "created_at" in response_data

    @patch.dict(os.environ, {"API_KEY": "test-api-key"})
    def test_upload_file_missing_file(self, client, auth_headers):
        """Test upload with missing file field."""
        data = {"purpose": "fine-tune"}
        
        response = client.post("/v1/files", data=data, headers=auth_headers)
        
        assert response.status_code == 422  # FastAPI validation error for missing file

    @patch.dict(os.environ, {"API_KEY": "test-api-key"})
    def test_upload_file_missing_purpose(self, client, auth_headers):
        """Test upload with missing purpose field."""
        test_content = b'{"prompt": "Hello", "completion": "Hi there!"}'
        files = {"file": ("test.json", BytesIO(test_content), "application/json")}
        
        response = client.post("/v1/files", files=files, headers=auth_headers)
        
        assert response.status_code == 422  # FastAPI validation error for missing purpose

    @patch.dict(os.environ, {"API_KEY": "test-api-key"})
    def test_upload_file_empty_file(self, client, mock_file_service, auth_headers):
        """Test upload with empty file."""
        files = {"file": ("empty.txt", BytesIO(b""), "text/plain")}
        data = {"purpose": "fine-tune"}
        
        response = client.post("/v1/files", files=files, data=data, headers=auth_headers)
        
        assert response.status_code == 400
        response_data = response.json()
        # The error handler formats the response as {'error': {'message': ...}}
        assert "error" in response_data
        assert "File is empty" in response_data["error"]["message"]

    def test_upload_file_unauthorized(self, client):
        """Test upload without authentication."""
        test_content = b'{"prompt": "Hello", "completion": "Hi there!"}'
        files = {"file": ("test.json", BytesIO(test_content), "application/json")}
        data = {"purpose": "fine-tune"}
        
        response = client.post("/v1/files", files=files, data=data)
        
        assert response.status_code == 403  # Forbidden (auth middleware returns 403)

    @patch.dict(os.environ, {"API_KEY": "test-api-key", "S3_FILES_BUCKET": "test-bucket"})
    def test_files_health_endpoint(self, client, mock_file_service):
        """Test the files health endpoint."""
        # Mock the get_file_service function to return our mock
        with patch('src.open_amazon_chat_completions_server.api.routes.files.get_file_service') as mock_get_service:
            mock_get_service.return_value = mock_file_service
            
            response = client.get("/v1/files/health")
            
            assert response.status_code == 200
            response_data = response.json()
            
            assert response_data["status"] == "healthy"
            assert response_data["service"] == "files"
            assert response_data["s3_bucket_configured"] is True
            assert response_data["aws_region"] == "us-east-1"

    @patch.dict(os.environ, {"API_KEY": "test-api-key"})
    def test_files_health_endpoint_no_bucket(self, client):
        """Test the files health endpoint when S3 bucket is not configured."""
        # Mock a file service with no bucket configured
        with patch('src.open_amazon_chat_completions_server.api.routes.files.get_file_service') as mock_get_service:
            mock_service = MagicMock()
            mock_service.s3_bucket = None
            mock_service.AWS_REGION = "us-east-1"
            mock_get_service.return_value = mock_service
            
            response = client.get("/v1/files/health")
            
            assert response.status_code == 200
            response_data = response.json()
            
            # Should still return healthy but indicate bucket is not configured
            assert response_data["service"] == "files"
            assert response_data["s3_bucket_configured"] is False


@pytest.mark.integration
class TestFilesEndpointIntegration:
    """Integration tests that require actual AWS configuration."""

    @pytest.mark.skipif(
        not (os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("S3_FILES_BUCKET")),
        reason="AWS credentials and S3 bucket required for integration test"
    )
    def test_real_file_upload(self, client, auth_headers):
        """Test actual file upload to S3 (requires real AWS credentials)."""
        # This test would only run if AWS credentials are available
        test_content = b'{"test": "data"}'
        files = {"file": ("integration_test.json", BytesIO(test_content), "application/json")}
        data = {"purpose": "fine-tune"}
        
        response = client.post("/v1/files", files=files, data=data, headers=auth_headers)
        
        # Should succeed if AWS is properly configured
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["object"] == "file"
        assert response_data["filename"] == "integration_test.json" 