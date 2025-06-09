import pytest
import os
from unittest.mock import patch, MagicMock, AsyncMock, mock_open
from fastapi.testclient import TestClient
from io import BytesIO
from datetime import datetime
import asyncio
import json

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
        mock_file_service.validate_credentials = AsyncMock()
        
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
        mock_service = MagicMock()
        mock_service.s3_bucket = None
        mock_service.AWS_REGION = "us-east-1"
        mock_service.validate_credentials = AsyncMock()
        
        with patch('src.open_amazon_chat_completions_server.api.routes.files.get_file_service') as mock_get_service:
            mock_get_service.return_value = mock_service
            
            response = client.get("/v1/files/health")
            
            assert response.status_code == 200
            response_data = response.json()
            
            # Should still return healthy but indicate bucket is not configured
            assert response_data["service"] == "files"
            assert response_data["s3_bucket_configured"] is False

    @patch('boto3.client')
    @patch.dict(os.environ, {"API_KEY": "test-api-key"})
    def test_file_upload_invalid_purpose(self, mock_boto_client, client, auth_headers):
        """Test file upload with invalid purpose."""
        # Mock S3 client
        mock_s3_client = MagicMock()
        mock_boto_client.return_value = mock_s3_client
        
        file_content = b'{"test": "data"}'
        
        response = client.post(
            "/v1/files",
            data={"purpose": "invalid_purpose"},
            files={"file": ("test.json", file_content, "application/json")},
            headers=auth_headers
        )
        
        # Should succeed with any purpose value - there's no validation restriction
        assert response.status_code == 200


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


class TestFileRetrieval:
    """Test file retrieval operations."""
    
    @patch('boto3.client')
    def test_list_files_success(self, mock_boto_client, client):
        """Test successful file listing."""
        mock_s3_client = MagicMock()
        mock_boto_client.return_value = mock_s3_client
        
        # Mock S3 list_objects_v2 response
        mock_s3_client.list_objects_v2.return_value = {
            'Contents': [
                {'Key': 'files/file-123-test.txt', 'Size': 100, 'LastModified': datetime(2024, 1, 1)},
                {'Key': 'files/file-456-data.json', 'Size': 200, 'LastModified': datetime(2024, 1, 2)}
            ]
        }
        
        # Mock head_object responses
        def mock_head_object(Bucket, Key):
            if 'file-123' in Key:
                return {
                    'ContentType': 'text/plain',
                    'ContentLength': 100,
                    'LastModified': datetime(2024, 1, 1),
                    'Metadata': {'original_filename': 'test.txt', 'purpose': 'assistants'}
                }
            else:
                return {
                    'ContentType': 'application/json',
                    'ContentLength': 200,
                    'LastModified': datetime(2024, 1, 2),
                    'Metadata': {'original_filename': 'data.json', 'purpose': 'fine-tune'}
                }
        
        mock_s3_client.head_object.side_effect = mock_head_object
        
        # Create a mock service with the mocked S3 client
        from src.open_amazon_chat_completions_server.services.file_service import FileService
        mock_service = FileService(s3_bucket="test-bucket", validate_credentials=False)
        mock_service.s3_client = mock_s3_client
        
        with patch('src.open_amazon_chat_completions_server.api.routes.files.get_file_service') as mock_get_service:
            mock_get_service.return_value = mock_service
            
            response = client.get("/v1/files")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["object"] == "list"
            assert len(data["data"]) == 2
            
            # Check first file
            file1 = data["data"][0]  # Should be sorted by creation time (newest first)
            assert file1["id"] == "file-456"
            assert file1["filename"] == "data.json"
            assert file1["purpose"] == "fine-tune"
            assert file1["bytes"] == 200
    
    @patch('boto3.client')
    def test_list_files_with_purpose_filter(self, mock_boto_client, client):
        """Test file listing with purpose filter."""
        mock_s3_client = MagicMock()
        mock_boto_client.return_value = mock_s3_client
        
        mock_s3_client.list_objects_v2.return_value = {
            'Contents': [
                {'Key': 'files/file-123-test.txt', 'Size': 100, 'LastModified': datetime(2024, 1, 1)}
            ]
        }
        
        mock_s3_client.head_object.return_value = {
            'ContentType': 'text/plain',
            'ContentLength': 100,
            'LastModified': datetime(2024, 1, 1),
            'Metadata': {'original_filename': 'test.txt', 'purpose': 'assistants'}
        }
        
        # Create a mock service with the mocked S3 client
        from src.open_amazon_chat_completions_server.services.file_service import FileService
        mock_service = FileService(s3_bucket="test-bucket", validate_credentials=False)
        mock_service.s3_client = mock_s3_client
        
        with patch('src.open_amazon_chat_completions_server.api.routes.files.get_file_service') as mock_get_service:
            mock_get_service.return_value = mock_service
            
            response = client.get("/v1/files?purpose=assistants")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["data"]) == 1
            assert data["data"][0]["purpose"] == "assistants"
    
    @patch('boto3.client')
    def test_get_file_metadata_success(self, mock_boto_client, client):
        """Test successful file metadata retrieval."""
        mock_s3_client = MagicMock()
        mock_boto_client.return_value = mock_s3_client
        
        # Mock list_objects_v2 response
        mock_s3_client.list_objects_v2.return_value = {
            'Contents': [{'Key': 'files/file-123-test.txt'}]
        }
        
        # Mock head_object response
        mock_s3_client.head_object.return_value = {
            'ContentType': 'text/plain',
            'ContentLength': 100,
            'LastModified': datetime(2024, 1, 1),
            'Metadata': {'original_filename': 'test.txt', 'purpose': 'assistants'}
        }
        
        # Create a mock service with the mocked S3 client
        from src.open_amazon_chat_completions_server.services.file_service import FileService
        mock_service = FileService(s3_bucket="test-bucket", validate_credentials=False)
        mock_service.s3_client = mock_s3_client
        
        with patch('src.open_amazon_chat_completions_server.api.routes.files.get_file_service') as mock_get_service:
            mock_get_service.return_value = mock_service
            
            response = client.get("/v1/files/file-123")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["id"] == "file-123"
            assert data["filename"] == "test.txt"
            assert data["purpose"] == "assistants"
            assert data["bytes"] == 100
            assert data["status"] == "processed"
    
    @patch('boto3.client')  
    def test_get_file_not_found(self, mock_boto_client, client):
        """Test file metadata retrieval for non-existent file."""
        mock_s3_client = MagicMock()
        mock_boto_client.return_value = mock_s3_client
        
        # Mock empty response
        mock_s3_client.list_objects_v2.return_value = {}
        
        # Create a mock service with the mocked S3 client
        from src.open_amazon_chat_completions_server.services.file_service import FileService
        mock_service = FileService(s3_bucket="test-bucket", validate_credentials=False)
        mock_service.s3_client = mock_s3_client
        
        with patch('src.open_amazon_chat_completions_server.api.routes.files.get_file_service') as mock_get_service:
            mock_get_service.return_value = mock_service
            
            response = client.get("/v1/files/file-nonexistent")
            
            assert response.status_code == 404
            response_data = response.json()
            # The error handler transforms HTTPException into this format
            assert "error" in response_data
            assert "message" in response_data["error"]
            assert "not found" in response_data["error"]["message"]
    
    @patch('boto3.client')
    def test_get_file_content_success(self, mock_boto_client, client):
        """Test successful file content retrieval."""
        mock_s3_client = MagicMock()
        mock_boto_client.return_value = mock_s3_client
        
        # Mock list_objects_v2 response
        mock_s3_client.list_objects_v2.return_value = {
            'Contents': [{'Key': 'files/file-123-test.txt'}]
        }
        
        # Mock head_object response
        mock_s3_client.head_object.return_value = {
            'ContentType': 'text/plain',
            'ContentLength': 12,
            'LastModified': datetime(2024, 1, 1),
            'Metadata': {'original_filename': 'test.txt', 'purpose': 'assistants'}
        }
        
        # Mock get_object response
        mock_body = MagicMock()
        mock_body.read.return_value = b"test content"
        mock_s3_client.get_object.return_value = {'Body': mock_body}
        
        # Create a mock service with the mocked S3 client
        from src.open_amazon_chat_completions_server.services.file_service import FileService
        mock_service = FileService(s3_bucket="test-bucket", validate_credentials=False)
        mock_service.s3_client = mock_s3_client
        
        with patch('src.open_amazon_chat_completions_server.api.routes.files.get_file_service') as mock_get_service:
            mock_get_service.return_value = mock_service
            
            response = client.get("/v1/files/file-123/content")
            
            assert response.status_code == 200
            assert response.content == b"test content"
            assert response.headers["content-type"] == "text/plain; charset=utf-8"
            assert "test.txt" in response.headers.get("content-disposition", "")
    
    @patch('boto3.client')
    def test_delete_file_success(self, mock_boto_client, client):
        """Test successful file deletion."""
        mock_s3_client = MagicMock()
        mock_boto_client.return_value = mock_s3_client
        
        # Mock list_objects_v2 response for metadata check
        mock_s3_client.list_objects_v2.return_value = {
            'Contents': [{'Key': 'files/file-123-test.txt'}]
        }
        
        # Mock head_object response
        mock_s3_client.head_object.return_value = {
            'ContentType': 'text/plain',
            'ContentLength': 100,
            'LastModified': datetime(2024, 1, 1),
            'Metadata': {'original_filename': 'test.txt', 'purpose': 'assistants'}
        }
        
        # Create a mock service with the mocked S3 client
        from src.open_amazon_chat_completions_server.services.file_service import FileService
        mock_service = FileService(s3_bucket="test-bucket", validate_credentials=False)
        mock_service.s3_client = mock_s3_client
        
        with patch('src.open_amazon_chat_completions_server.api.routes.files.get_file_service') as mock_get_service:
            mock_get_service.return_value = mock_service
            
            response = client.delete("/v1/files/file-123")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["id"] == "file-123"
            assert data["object"] == "file"
            assert data["deleted"] is True
            
            # Verify delete_object was called
            mock_s3_client.delete_object.assert_called_once()


class TestFileProcessing:
    """Test file processing service."""
    
    def test_process_text_file(self):
        """Test processing plain text files."""
        from src.open_amazon_chat_completions_server.services.file_processing_service import FileProcessingService
        
        service = FileProcessingService()
        content = b"Hello, world!\nThis is a test file."
        
        result = asyncio.run(service.process_file(content, "text/plain", "test.txt"))
        
        assert result["success"] is True
        assert result["text_content"] == "Hello, world!\nThis is a test file."
        assert result["metadata"]["character_count"] == len("Hello, world!\nThis is a test file.")
    
    def test_process_json_file(self):
        """Test processing JSON files."""
        from src.open_amazon_chat_completions_server.services.file_processing_service import FileProcessingService
        
        service = FileProcessingService()
        content = b'{"name": "test", "value": 123, "items": ["a", "b", "c"]}'
        
        result = asyncio.run(service.process_file(content, "application/json", "test.json"))
        
        assert result["success"] is True
        assert "JSON File: test.json" in result["text_content"]
        assert "Object at root with 3 keys" in result["text_content"]
        assert '"name": "test"' in result["text_content"]
    
    def test_process_csv_file(self):
        """Test processing CSV files."""
        from src.open_amazon_chat_completions_server.services.file_processing_service import FileProcessingService
        
        service = FileProcessingService()
        content = b"name,age,city\nJohn,25,NYC\nJane,30,LA"
        
        result = asyncio.run(service.process_file(content, "text/csv", "test.csv"))
        
        assert result["success"] is True
        assert "CSV File: test.csv" in result["text_content"]
        assert "Headers: name, age, city" in result["text_content"]
        assert "Total rows: 2" in result["text_content"]
    
    def test_process_unsupported_file(self):
        """Test processing unsupported file types."""
        from src.open_amazon_chat_completions_server.services.file_processing_service import FileProcessingService
        
        service = FileProcessingService()
        content = b"binary data"
        
        result = asyncio.run(service.process_file(content, "application/octet-stream", "test.bin"))
        
        assert result["success"] is False
        assert "Unsupported file type" in result["error"]
        assert result["text_content"] is None


class TestChatCompletionsWithFiles:
    """Test chat completions with file integration."""
    
    @patch('src.open_amazon_chat_completions_server.api.routes.chat.get_file_service')
    @patch('src.open_amazon_chat_completions_server.services.llm_service_factory.LLMServiceFactory.get_service_for_model')
    @patch.dict(os.environ, {"API_KEY": "test-api-key"})
    def test_chat_completion_with_files(self, mock_get_service, mock_get_file_service, client, auth_headers):
        """Test chat completion with file context."""
        # Mock file service
        mock_file_service = MagicMock()
        mock_get_file_service.return_value = mock_file_service
        mock_file_service.get_file_content.return_value = (
            "Sample file content for testing",  # content
            "test.txt",  # filename
            "text/plain"  # content_type
        )
        
        # Mock LLM service
        mock_llm_service = MagicMock()
        mock_llm_service.provider_name = "test-provider"
        mock_get_service.return_value = mock_llm_service
        
        # Import the correct model classes
        from src.open_amazon_chat_completions_server.core.models import (
            ChatCompletionResponse, 
            ChatCompletionChoice, 
            Message as ResponseMessage,
            Usage
        )
        
        # Mock LLM response
        mock_response = ChatCompletionResponse(
            id="test-response",
            choices=[
                ChatCompletionChoice(
                    message=ResponseMessage(
                        role="assistant",
                        content="I can see the file content you uploaded."
                    ),
                    index=0,
                    finish_reason="stop"
                )
            ],
            created=1234567890,
            model="test-model",
            usage=Usage(
                prompt_tokens=10,
                completion_tokens=5,
                total_tokens=15
            )
        )
        
        mock_llm_service.chat_completion_with_request = AsyncMock(return_value=mock_response)
        
        # Test request with file_ids
        request_data = {
            "model": "test-model",
            "messages": [
                {"role": "user", "content": "What's in this file?"}
            ],
            "file_ids": ["file-123"]
        }
        
        response = client.post("/v1/chat/completions", json=request_data, headers=auth_headers)
        
        assert response.status_code == 200
        response_data = response.json()
        assert "choices" in response_data
        assert len(response_data["choices"]) == 1
        assert response_data["choices"][0]["message"]["role"] == "assistant" 