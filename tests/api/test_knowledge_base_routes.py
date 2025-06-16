from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient

from src.open_bedrock_server.api.app import app
from src.open_bedrock_server.core.knowledge_base_models import (
    Citation,
    DataSourceInfo,
    KnowledgeBaseInfo,
    KnowledgeBaseQueryResponse,
    ListDataSourcesResponse,
    ListKnowledgeBasesResponse,
    RetrievalResult,
    RetrieveAndGenerateResponse,
)


@pytest.mark.knowledge_base
@pytest.mark.integration
@pytest.mark.kb_api
class TestKnowledgeBaseRoutes:
    """Test Knowledge Base API routes."""

    @pytest.fixture(scope="module")
    async def client(self):
        """Create test client for the FastAPI app."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac

    @pytest.fixture
    def auth_headers(self, test_api_key):
        """Provide authentication headers for tests."""
        return {"Authorization": f"Bearer {test_api_key}"}

    @pytest.fixture
    def mock_kb_service(self):
        """Mock KnowledgeBaseService for testing."""
        with patch(
            "src.open_bedrock_server.api.routes.knowledge_bases.KnowledgeBaseService"
        ) as mock_service:
            mock_instance = Mock()
            mock_service.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def sample_knowledge_base(self):
        """Sample knowledge base for testing."""
        return KnowledgeBaseInfo(
            knowledgeBaseId="kb-123456789",
            name="test-kb",
            description="Test knowledge base",
            knowledgeBaseArn="arn:aws:bedrock:us-east-1:123456789012:knowledge-base/kb-123456789",
            roleArn="arn:aws:iam::123456789012:role/test-role",
            knowledgeBaseConfiguration={
                "type": "VECTOR",
                "vectorKnowledgeBaseConfiguration": {
                    "embeddingModelArn": "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v1"
                }
            },
            storageConfiguration={
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
            status="ACTIVE",
            createdAt=datetime.now(),
            updatedAt=datetime.now(),
        )

    @pytest.mark.asyncio
    async def test_create_knowledge_base_success(
        self, client: AsyncClient, auth_headers, mock_kb_service, sample_knowledge_base
    ):
        """Test successful knowledge base creation."""
        # Mock the service response
        mock_kb_service.create_knowledge_base.return_value = sample_knowledge_base

        payload = {
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

        response = await client.post(
            "/v1/knowledge-bases", json=payload, headers=auth_headers
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["knowledgeBaseId"] == "kb-123456789"
        assert data["name"] == "test-kb"
        assert data["status"] == "ACTIVE"

        # Verify service was called
        mock_kb_service.create_knowledge_base.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_knowledge_base_validation_error(
        self, client: AsyncClient, auth_headers
    ):
        """Test knowledge base creation with validation error."""
        # Missing required fields
        payload = {
            "name": "test-kb"
            # Missing role_arn and storage_configuration
        }

        response = await client.post(
            "/v1/knowledge-bases", json=payload, headers=auth_headers
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_create_knowledge_base_service_error(
        self, client: AsyncClient, auth_headers, mock_kb_service
    ):
        """Test knowledge base creation with service error."""
        # Mock service to raise exception
        mock_kb_service.create_knowledge_base.side_effect = Exception(
            "AWS service error"
        )

        payload = {
            "name": "test-kb",
            "role_arn": "arn:aws:iam::123456789012:role/test-role",
            "storage_configuration": {},
        }

        response = await client.post(
            "/v1/knowledge-bases", json=payload, headers=auth_headers
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "error" in data

    @pytest.mark.asyncio
    async def test_get_knowledge_base_success(
        self, client: AsyncClient, auth_headers, mock_kb_service, sample_knowledge_base
    ):
        """Test successful knowledge base retrieval."""
        mock_kb_service.get_knowledge_base.return_value = sample_knowledge_base

        response = await client.get(
            "/v1/knowledge-bases/kb-123456789", headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["knowledgeBaseId"] == "kb-123456789"
        assert data["name"] == "test-kb"

        mock_kb_service.get_knowledge_base.assert_called_once_with("kb-123456789")

    @pytest.mark.asyncio
    async def test_get_knowledge_base_not_found(
        self, client: AsyncClient, auth_headers, mock_kb_service
    ):
        """Test knowledge base not found."""
        mock_kb_service.get_knowledge_base.side_effect = Exception(
            "Knowledge base not found"
        )

        response = await client.get(
            "/v1/knowledge-bases/kb-nonexistent", headers=auth_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "error" in data

    @pytest.mark.asyncio
    async def test_list_knowledge_bases_success(
        self, client: AsyncClient, auth_headers, mock_kb_service, sample_knowledge_base
    ):
        """Test successful knowledge base listing."""
        kb_list = ListKnowledgeBasesResponse(
            knowledgeBaseSummaries=[sample_knowledge_base], nextToken=None
        )
        mock_kb_service.list_knowledge_bases.return_value = kb_list

        response = await client.get("/v1/knowledge-bases", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "knowledgeBaseSummaries" in data
        assert len(data["knowledgeBaseSummaries"]) == 1
        assert data["knowledgeBaseSummaries"][0]["knowledgeBaseId"] == "kb-123456789"

        mock_kb_service.list_knowledge_bases.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_knowledge_bases_with_pagination(
        self, client: AsyncClient, auth_headers, mock_kb_service
    ):
        """Test knowledge base listing with pagination."""
        kb_list = ListKnowledgeBasesResponse(knowledgeBaseSummaries=[], nextToken="next-page-token")
        mock_kb_service.list_knowledge_bases.return_value = kb_list

        response = await client.get(
            "/v1/knowledge-bases?limit=10&next_token=some-token", headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["nextToken"] == "next-page-token"

        mock_kb_service.list_knowledge_bases.assert_called_once_with(
            limit=10, next_token="some-token"
        )

    @pytest.mark.asyncio
    async def test_update_knowledge_base_success(
        self, client: AsyncClient, auth_headers, mock_kb_service, sample_knowledge_base
    ):
        """Test successful knowledge base update."""
        updated_kb = sample_knowledge_base.model_copy()
        updated_kb.description = "Updated description"
        mock_kb_service.update_knowledge_base.return_value = updated_kb

        payload = {"description": "Updated description"}

        response = await client.put(
            "/v1/knowledge-bases/kb-123456789", json=payload, headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["description"] == "Updated description"

        mock_kb_service.update_knowledge_base.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_knowledge_base_success(
        self, client: AsyncClient, auth_headers, mock_kb_service
    ):
        """Test successful knowledge base deletion."""
        mock_kb_service.delete_knowledge_base.return_value = True

        response = await client.delete(
            "/v1/knowledge-bases/kb-123456789", headers=auth_headers
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        mock_kb_service.delete_knowledge_base.assert_called_once_with("kb-123456789")

    @pytest.mark.asyncio
    async def test_delete_knowledge_base_failure(
        self, client: AsyncClient, auth_headers, mock_kb_service
    ):
        """Test knowledge base deletion failure."""
        mock_kb_service.delete_knowledge_base.side_effect = Exception(
            "Cannot delete knowledge base"
        )

        response = await client.delete(
            "/v1/knowledge-bases/kb-123456789", headers=auth_headers
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "error" in data

    @pytest.mark.asyncio
    async def test_query_knowledge_base_success(
        self, client: AsyncClient, auth_headers, mock_kb_service
    ):
        """Test successful knowledge base query."""
        query_response = KnowledgeBaseQueryResponse(
            query_text="What is machine learning?",
            retrieval_results=[
                RetrievalResult(
                    content="Machine learning is a subset of AI...",
                    score=0.95,
                    metadata={"source": "ml_book.pdf"},
                    location={
                        "type": "S3",
                        "s3Location": {"uri": "s3://bucket/ml_book.pdf"},
                    },
                )
            ],
            citations=[],
        )
        mock_kb_service.query_knowledge_base.return_value = query_response

        payload = {
            "query_text": "What is machine learning?",
            "retrieval_config": {"vector_search_config": {"numberOfResults": 5}},
        }

        response = await client.post(
            "/v1/knowledge-bases/kb-123456789/query", json=payload, headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["query_text"] == "What is machine learning?"
        assert len(data["retrieval_results"]) == 1
        assert data["retrieval_results"][0]["score"] == 0.95

        mock_kb_service.query_knowledge_base.assert_called_once()

    @pytest.mark.asyncio
    async def test_retrieve_and_generate_success(
        self, client: AsyncClient, auth_headers, mock_kb_service
    ):
        """Test successful retrieve and generate."""
        rag_response = RAGResponse(
            query_text="Explain machine learning",
            generated_text="Machine learning is a powerful technology...",
            retrieval_results=[
                RetrievalResult(
                    content="ML definition...",
                    score=0.9,
                    metadata={"source": "textbook.pdf"},
                    location={
                        "type": "S3",
                        "s3Location": {"uri": "s3://bucket/textbook.pdf"},
                    },
                )
            ],
            citations=[
                Citation(
                    generated_response_part="Machine learning is",
                    retrieved_references=[
                        {
                            "content": "ML definition...",
                            "location": {
                                "type": "S3",
                                "s3Location": {"uri": "s3://bucket/textbook.pdf"},
                            },
                            "metadata": {"source": "textbook.pdf"},
                        }
                    ],
                )
            ],
        )
        mock_kb_service.retrieve_and_generate.return_value = rag_response

        payload = {
            "query_text": "Explain machine learning",
            "generation_config": {"max_tokens": 100, "temperature": 0.7},
        }

        response = await client.post(
            "/v1/knowledge-bases/kb-123456789/retrieve-generate",
            json=payload,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["generated_text"] == "Machine learning is a powerful technology..."
        assert len(data["retrieval_results"]) == 1
        assert len(data["citations"]) == 1

        mock_kb_service.retrieve_and_generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_data_source_success(
        self, client: AsyncClient, auth_headers, mock_kb_service
    ):
        """Test successful data source creation."""
        data_source = DataSource(
            data_source_id="ds-123456789",
            knowledge_base_id="kb-123456789",
            name="test-datasource",
            description="Test data source",
            data_source_configuration={
                "type": "S3",
                "s3Configuration": {"bucketArn": "arn:aws:s3:::test-bucket"},
            },
            status="AVAILABLE",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_kb_service.create_data_source.return_value = data_source

        payload = {
            "name": "test-datasource",
            "description": "Test data source",
            "data_source_configuration": {
                "type": "S3",
                "s3Configuration": {"bucketArn": "arn:aws:s3:::test-bucket"},
            },
        }

        response = await client.post(
            "/v1/knowledge-bases/kb-123456789/data-sources",
            json=payload,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["data_source_id"] == "ds-123456789"
        assert data["name"] == "test-datasource"

        mock_kb_service.create_data_source.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_data_source_success(
        self, client: AsyncClient, auth_headers, mock_kb_service
    ):
        """Test successful data source retrieval."""
        data_source = DataSource(
            data_source_id="ds-123456789",
            knowledge_base_id="kb-123456789",
            name="test-datasource",
            status="AVAILABLE",
        )
        mock_kb_service.get_data_source.return_value = data_source

        response = await client.get(
            "/v1/knowledge-bases/kb-123456789/data-sources/ds-123456789",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data_source_id"] == "ds-123456789"

        mock_kb_service.get_data_source.assert_called_once_with(
            "kb-123456789", "ds-123456789"
        )

    @pytest.mark.asyncio
    async def test_list_data_sources_success(
        self, client: AsyncClient, auth_headers, mock_kb_service
    ):
        """Test successful data source listing."""
        data_source = DataSource(
            data_source_id="ds-123456789",
            knowledge_base_id="kb-123456789",
            name="test-datasource",
            status="AVAILABLE",
        )
        ds_list = DataSourceList(data_sources=[data_source], next_token=None)
        mock_kb_service.list_data_sources.return_value = ds_list

        response = await client.get(
            "/v1/knowledge-bases/kb-123456789/data-sources", headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["data_sources"]) == 1
        assert data["data_sources"][0]["data_source_id"] == "ds-123456789"

        mock_kb_service.list_data_sources.assert_called_once_with("kb-123456789")

    @pytest.mark.asyncio
    async def test_delete_data_source_success(
        self, client: AsyncClient, auth_headers, mock_kb_service
    ):
        """Test successful data source deletion."""
        mock_kb_service.delete_data_source.return_value = True

        response = await client.delete(
            "/v1/knowledge-bases/kb-123456789/data-sources/ds-123456789",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        mock_kb_service.delete_data_source.assert_called_once_with(
            "kb-123456789", "ds-123456789"
        )

    @pytest.mark.asyncio
    async def test_start_ingestion_job_success(
        self, client: AsyncClient, auth_headers, mock_kb_service
    ):
        """Test successful ingestion job start."""
        mock_kb_service.start_ingestion_job.return_value = {
            "ingestionJobId": "job-123456789",
            "status": "STARTING",
        }

        response = await client.post(
            "/v1/knowledge-bases/kb-123456789/data-sources/ds-123456789/ingestion-jobs",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["ingestionJobId"] == "job-123456789"
        assert data["status"] == "STARTING"

        mock_kb_service.start_ingestion_job.assert_called_once_with(
            "kb-123456789", "ds-123456789"
        )

    @pytest.mark.asyncio
    async def test_get_ingestion_job_status(
        self, client: AsyncClient, auth_headers, mock_kb_service
    ):
        """Test getting ingestion job status."""
        mock_kb_service.get_ingestion_job.return_value = {
            "ingestionJobId": "job-123456789",
            "status": "COMPLETE",
            "statistics": {
                "numberOfDocumentsScanned": 100,
                "numberOfNewDocumentsIndexed": 50,
            },
        }

        response = await client.get(
            "/v1/knowledge-bases/kb-123456789/data-sources/ds-123456789/ingestion-jobs/job-123456789",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "COMPLETE"
        assert data["statistics"]["numberOfDocumentsScanned"] == 100

        mock_kb_service.get_ingestion_job.assert_called_once_with(
            "kb-123456789", "ds-123456789", "job-123456789"
        )

    @pytest.mark.asyncio
    async def test_health_check_success(
        self, client: AsyncClient, auth_headers, mock_kb_service
    ):
        """Test successful health check."""
        health = KnowledgeBaseHealth(
            knowledge_base_id="kb-123456789",
            status="HEALTHY",
            last_updated=datetime.now(),
            details={"status": "ACTIVE", "document_count": 1000},
        )
        mock_kb_service.health_check.return_value = health

        response = await client.get(
            "/v1/knowledge-bases/kb-123456789/health", headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "HEALTHY"
        assert data["details"]["document_count"] == 1000

        mock_kb_service.health_check.assert_called_once_with("kb-123456789")

    @pytest.mark.asyncio
    async def test_unauthorized_access(self, client: AsyncClient):
        """Test unauthorized access to knowledge base endpoints."""
        # Test without authentication headers
        response = await client.get("/v1/knowledge-bases")
        assert response.status_code == status.HTTP_403_FORBIDDEN

        response = await client.post("/v1/knowledge-bases", json={})
        assert response.status_code == status.HTTP_403_FORBIDDEN

        response = await client.get("/v1/knowledge-bases/kb-123456789")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_invalid_api_key(self, client: AsyncClient):
        """Test access with invalid API key."""
        headers = {"Authorization": "Bearer invalid-key"}

        response = await client.get("/v1/knowledge-bases", headers=headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN

        data = response.json()
        assert "error" in data
        assert data["error"]["message"] == "Invalid API key"

    @pytest.mark.asyncio
    async def test_malformed_request_body(self, client: AsyncClient, auth_headers):
        """Test handling of malformed request body."""
        # Send invalid JSON
        response = await client.post(
            "/v1/knowledge-bases",
            content="invalid json",
            headers={**auth_headers, "Content-Type": "application/json"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_concurrent_requests(
        self, client: AsyncClient, auth_headers, mock_kb_service, sample_knowledge_base
    ):
        """Test handling of concurrent requests."""
        import asyncio

        mock_kb_service.get_knowledge_base.return_value = sample_knowledge_base

        # Make multiple concurrent requests
        tasks = [
            client.get("/v1/knowledge-bases/kb-123456789", headers=auth_headers)
            for _ in range(5)
        ]

        responses = await asyncio.gather(*tasks)

        # All requests should succeed
        for response in responses:
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["knowledge_base_id"] == "kb-123456789"

        # Service should be called for each request
        assert mock_kb_service.get_knowledge_base.call_count == 5

    @pytest.mark.asyncio
    async def test_large_payload_handling(
        self, client: AsyncClient, auth_headers, mock_kb_service, sample_knowledge_base
    ):
        """Test handling of large payloads."""
        mock_kb_service.create_knowledge_base.return_value = sample_knowledge_base

        # Create a large payload
        large_description = "x" * 10000  # 10KB description
        payload = {
            "name": "test-kb",
            "description": large_description,
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

        response = await client.post(
            "/v1/knowledge-bases", json=payload, headers=auth_headers
        )

        assert response.status_code == status.HTTP_201_CREATED
        mock_kb_service.create_knowledge_base.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_response_format(
        self, client: AsyncClient, auth_headers, mock_kb_service
    ):
        """Test that error responses follow the expected format."""
        mock_kb_service.get_knowledge_base.side_effect = Exception("Test error")

        response = await client.get(
            "/v1/knowledge-bases/kb-123456789", headers=auth_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()

        # Check error response structure
        assert "error" in data
        assert "error_code" in data["error"]
        assert "message" in data["error"]
        assert data["error"]["message"] == "Test error"
