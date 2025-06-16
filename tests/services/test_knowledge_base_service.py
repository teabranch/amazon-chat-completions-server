from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from src.open_bedrock_server.core.knowledge_base_models import (
    CreateDataSourceRequest,
    CreateKnowledgeBaseRequest,
    KnowledgeBaseQueryRequest,
    RetrieveAndGenerateRequest,
)
from src.open_bedrock_server.services.knowledge_base_service import (
    KnowledgeBaseService,
)


@pytest.mark.knowledge_base
@pytest.mark.integration
@pytest.mark.kb_service
class TestKnowledgeBaseService:
    """Test Knowledge Base service with mocked AWS interactions."""

    @pytest.fixture
    def mock_bedrock_client(self):
        """Mock Bedrock Agent client."""
        with patch("boto3.client") as mock_client:
            mock_bedrock = Mock()
            mock_client.return_value = mock_bedrock
            yield mock_bedrock

    @pytest.fixture
    def mock_bedrock_runtime_client(self):
        """Mock Bedrock Agent Runtime client."""
        with patch("boto3.client") as mock_client:
            mock_runtime = Mock()
            mock_client.return_value = mock_runtime
            yield mock_runtime

    @pytest.fixture
    def knowledge_base_service(self, mock_bedrock_client):
        """Create KnowledgeBaseService with mocked clients."""
        with patch(
            "src.open_bedrock_server.services.knowledge_base_service.boto3.client"
        ) as mock_client:
            mock_client.return_value = mock_bedrock_client
            service = KnowledgeBaseService(region="us-east-1")
            return service

    @pytest.fixture
    def sample_kb_data(self):
        """Sample knowledge base data for testing."""
        return {
            "knowledgeBaseId": "kb-123456789",
            "name": "test-kb",
            "description": "Test knowledge base",
            "roleArn": "arn:aws:iam::123456789012:role/test-role",
            "knowledgeBaseConfiguration": {
                "type": "VECTOR",
                "vectorKnowledgeBaseConfiguration": {
                    "embeddingModelArn": "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v1"
                },
            },
            "storageConfiguration": {
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
            "status": "ACTIVE",
            "createdAt": datetime.now(),
            "updatedAt": datetime.now(),
        }

    def test_service_initialization(self):
        """Test KnowledgeBaseService initialization."""
        with patch("boto3.client") as mock_client:
            service = KnowledgeBaseService(region="us-west-2")
            assert service.region == "us-west-2"
            # Should create both clients
            assert mock_client.call_count == 2

    def test_service_initialization_with_custom_profile(self):
        """Test service initialization with custom AWS profile."""
        with patch("boto3.Session") as mock_session, patch("boto3.client"):
            mock_session_instance = Mock()
            mock_session.return_value = mock_session_instance
            mock_session_instance.client.return_value = Mock()

            KnowledgeBaseService(region="us-east-1", profile_name="test-profile")
            mock_session.assert_called_once_with(profile_name="test-profile")

    @pytest.mark.asyncio
    async def test_create_knowledge_base_success(
        self, knowledge_base_service, mock_bedrock_client, sample_kb_data
    ):
        """Test successful knowledge base creation."""
        # Mock the create response
        mock_bedrock_client.create_knowledge_base.return_value = {
            "knowledgeBase": sample_kb_data
        }

        create_request = CreateKnowledgeBaseRequest(
            name="test-kb",
            description="Test knowledge base",
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
        )

        result = await knowledge_base_service.create_knowledge_base(create_request)

        assert result.knowledge_base_id == "kb-123456789"
        assert result.name == "test-kb"
        assert result.status == "ACTIVE"

        # Verify the client was called correctly
        mock_bedrock_client.create_knowledge_base.assert_called_once()
        call_args = mock_bedrock_client.create_knowledge_base.call_args[1]
        assert call_args["name"] == "test-kb"

    @pytest.mark.asyncio
    async def test_create_knowledge_base_failure(
        self, knowledge_base_service, mock_bedrock_client
    ):
        """Test knowledge base creation failure."""
        from botocore.exceptions import ClientError

        # Mock client error
        mock_bedrock_client.create_knowledge_base.side_effect = ClientError(
            error_response={
                "Error": {"Code": "ValidationException", "Message": "Invalid role ARN"}
            },
            operation_name="CreateKnowledgeBase",
        )

        create_request = CreateKnowledgeBaseRequest(
            name="test-kb", 
            roleArn="invalid-arn", 
            knowledgeBaseConfiguration={
                "type": "VECTOR",
                "vectorKnowledgeBaseConfiguration": {
                    "embeddingModelArn": "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v1"
                }
            }
        )

        with pytest.raises(Exception) as exc_info:
            await knowledge_base_service.create_knowledge_base(create_request)

        assert "Invalid role ARN" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_knowledge_base_success(
        self, knowledge_base_service, mock_bedrock_client, sample_kb_data
    ):
        """Test successful knowledge base retrieval."""
        mock_bedrock_client.get_knowledge_base.return_value = {
            "knowledgeBase": sample_kb_data
        }

        result = await knowledge_base_service.get_knowledge_base("kb-123456789")

        assert result.knowledge_base_id == "kb-123456789"
        assert result.name == "test-kb"
        mock_bedrock_client.get_knowledge_base.assert_called_once_with(
            knowledgeBaseId="kb-123456789"
        )

    @pytest.mark.asyncio
    async def test_get_knowledge_base_not_found(
        self, knowledge_base_service, mock_bedrock_client
    ):
        """Test knowledge base not found."""
        from botocore.exceptions import ClientError

        mock_bedrock_client.get_knowledge_base.side_effect = ClientError(
            error_response={
                "Error": {
                    "Code": "ResourceNotFoundException",
                    "Message": "Knowledge base not found",
                }
            },
            operation_name="GetKnowledgeBase",
        )

        with pytest.raises(Exception) as exc_info:
            await knowledge_base_service.get_knowledge_base("kb-nonexistent")

        assert "Knowledge base not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_list_knowledge_bases_success(
        self, knowledge_base_service, mock_bedrock_client, sample_kb_data
    ):
        """Test successful knowledge base listing."""
        mock_bedrock_client.list_knowledge_bases.return_value = {
            "knowledgeBaseSummaries": [
                {
                    "knowledgeBaseId": sample_kb_data["knowledgeBaseId"],
                    "name": sample_kb_data["name"],
                    "description": sample_kb_data["description"],
                    "status": sample_kb_data["status"],
                    "updatedAt": sample_kb_data["updatedAt"],
                }
            ]
        }

        result = await knowledge_base_service.list_knowledge_bases()

        assert len(result.knowledge_bases) == 1
        assert result.knowledge_bases[0].knowledge_base_id == "kb-123456789"
        mock_bedrock_client.list_knowledge_bases.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_knowledge_bases_with_pagination(
        self, knowledge_base_service, mock_bedrock_client
    ):
        """Test knowledge base listing with pagination."""
        mock_bedrock_client.list_knowledge_bases.return_value = {
            "knowledgeBaseSummaries": [],
            "nextToken": "next-page-token",
        }

        result = await knowledge_base_service.list_knowledge_bases(limit=10)

        assert len(result.knowledge_bases) == 0
        assert result.next_token == "next-page-token"
        mock_bedrock_client.list_knowledge_bases.assert_called_once_with(maxResults=10)

    @pytest.mark.asyncio
    async def test_update_knowledge_base_success(
        self, knowledge_base_service, mock_bedrock_client, sample_kb_data
    ):
        """Test successful knowledge base update."""
        updated_data = sample_kb_data.copy()
        updated_data["description"] = "Updated description"

        mock_bedrock_client.update_knowledge_base.return_value = {
            "knowledgeBase": updated_data
        }

        update_request = KnowledgeBaseUpdate(description="Updated description")

        result = await knowledge_base_service.update_knowledge_base(
            "kb-123456789", update_request
        )

        assert result.description == "Updated description"
        mock_bedrock_client.update_knowledge_base.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_knowledge_base_success(
        self, knowledge_base_service, mock_bedrock_client
    ):
        """Test successful knowledge base deletion."""
        mock_bedrock_client.delete_knowledge_base.return_value = {
            "knowledgeBaseId": "kb-123456789",
            "status": "DELETING",
        }

        result = await knowledge_base_service.delete_knowledge_base("kb-123456789")

        assert result is True
        mock_bedrock_client.delete_knowledge_base.assert_called_once_with(
            knowledgeBaseId="kb-123456789"
        )

    @pytest.mark.asyncio
    async def test_query_knowledge_base_success(self, knowledge_base_service):
        """Test successful knowledge base query."""
        with patch(
            "src.open_bedrock_server.services.knowledge_base_service.boto3.client"
        ) as mock_client:
            mock_runtime = Mock()
            mock_client.return_value = mock_runtime

            mock_runtime.retrieve.return_value = {
                "retrievalResults": [
                    {
                        "content": {"text": "Machine learning is a subset of AI..."},
                        "score": 0.95,
                        "location": {
                            "type": "S3",
                            "s3Location": {"uri": "s3://test-bucket/doc.pdf"},
                        },
                        "metadata": {"source": "doc.pdf"},
                    }
                ]
            }

            # Create new service with mocked runtime client
            service = KnowledgeBaseService(region="us-east-1")

            query = KnowledgeBaseQuery(
                query_text="What is machine learning?",
                retrieval_config=RetrievalConfig(),
            )

            result = await service.query_knowledge_base("kb-123456789", query)

            assert result.query_text == "What is machine learning?"
            assert len(result.retrieval_results) == 1
            assert result.retrieval_results[0].score == 0.95

    @pytest.mark.asyncio
    async def test_retrieve_and_generate_success(self, knowledge_base_service):
        """Test successful retrieve and generate."""
        with patch(
            "src.open_bedrock_server.services.knowledge_base_service.boto3.client"
        ) as mock_client:
            mock_runtime = Mock()
            mock_client.return_value = mock_runtime

            mock_runtime.retrieve_and_generate.return_value = {
                "output": {"text": "Machine learning is a powerful technology..."},
                "retrievalResults": [
                    {
                        "content": {"text": "ML definition..."},
                        "score": 0.9,
                        "location": {
                            "type": "S3",
                            "s3Location": {"uri": "s3://bucket/file.pdf"},
                        },
                        "metadata": {"source": "file.pdf"},
                    }
                ],
                "citations": [
                    {
                        "generatedResponsePart": {
                            "textResponsePart": {"text": "Machine learning is"}
                        },
                        "retrievedReferences": [
                            {
                                "content": {"text": "ML definition..."},
                                "location": {
                                    "type": "S3",
                                    "s3Location": {"uri": "s3://bucket/file.pdf"},
                                },
                                "metadata": {"source": "file.pdf"},
                            }
                        ],
                    }
                ],
            }

            service = KnowledgeBaseService(region="us-east-1")

            rag_request = RAGRequest(
                query_text="Explain machine learning",
                retrieval_config=RetrievalConfig(),
                generation_config={"max_tokens": 100},
            )

            result = await service.retrieve_and_generate("kb-123456789", rag_request)

            assert (
                result.generated_text == "Machine learning is a powerful technology..."
            )
            assert len(result.retrieval_results) == 1
            assert len(result.citations) == 1

    @pytest.mark.asyncio
    async def test_create_data_source_success(
        self, knowledge_base_service, mock_bedrock_client
    ):
        """Test successful data source creation."""
        mock_bedrock_client.create_data_source.return_value = {
            "dataSource": {
                "dataSourceId": "ds-123456789",
                "knowledgeBaseId": "kb-123456789",
                "name": "test-datasource",
                "description": "Test data source",
                "dataSourceConfiguration": {
                    "type": "S3",
                    "s3Configuration": {"bucketArn": "arn:aws:s3:::test-bucket"},
                },
                "status": "AVAILABLE",
                "createdAt": datetime.now(),
                "updatedAt": datetime.now(),
            }
        }

        create_request = DataSourceCreate(
            name="test-datasource",
            description="Test data source",
            data_source_configuration={
                "type": "S3",
                "s3Configuration": {"bucketArn": "arn:aws:s3:::test-bucket"},
            },
        )

        result = await knowledge_base_service.create_data_source(
            "kb-123456789", create_request
        )

        assert result.data_source_id == "ds-123456789"
        assert result.name == "test-datasource"
        mock_bedrock_client.create_data_source.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_data_source_success(
        self, knowledge_base_service, mock_bedrock_client
    ):
        """Test successful data source retrieval."""
        mock_bedrock_client.get_data_source.return_value = {
            "dataSource": {
                "dataSourceId": "ds-123456789",
                "knowledgeBaseId": "kb-123456789",
                "name": "test-datasource",
                "status": "AVAILABLE",
            }
        }

        result = await knowledge_base_service.get_data_source(
            "kb-123456789", "ds-123456789"
        )

        assert result.data_source_id == "ds-123456789"
        mock_bedrock_client.get_data_source.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_data_sources_success(
        self, knowledge_base_service, mock_bedrock_client
    ):
        """Test successful data source listing."""
        mock_bedrock_client.list_data_sources.return_value = {
            "dataSourceSummaries": [
                {
                    "dataSourceId": "ds-123456789",
                    "knowledgeBaseId": "kb-123456789",
                    "name": "test-datasource",
                    "status": "AVAILABLE",
                    "updatedAt": datetime.now(),
                }
            ]
        }

        result = await knowledge_base_service.list_data_sources("kb-123456789")

        assert len(result.data_sources) == 1
        assert result.data_sources[0].data_source_id == "ds-123456789"
        mock_bedrock_client.list_data_sources.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_data_source_success(
        self, knowledge_base_service, mock_bedrock_client
    ):
        """Test successful data source deletion."""
        mock_bedrock_client.delete_data_source.return_value = {
            "dataSourceId": "ds-123456789",
            "status": "DELETING",
        }

        result = await knowledge_base_service.delete_data_source(
            "kb-123456789", "ds-123456789"
        )

        assert result is True
        mock_bedrock_client.delete_data_source.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_ingestion_job_success(
        self, knowledge_base_service, mock_bedrock_client
    ):
        """Test successful ingestion job start."""
        mock_bedrock_client.start_ingestion_job.return_value = {
            "ingestionJob": {
                "knowledgeBaseId": "kb-123456789",
                "dataSourceId": "ds-123456789",
                "ingestionJobId": "job-123456789",
                "status": "STARTING",
            }
        }

        result = await knowledge_base_service.start_ingestion_job(
            "kb-123456789", "ds-123456789"
        )

        assert result["ingestionJobId"] == "job-123456789"
        assert result["status"] == "STARTING"
        mock_bedrock_client.start_ingestion_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_ingestion_job_status(
        self, knowledge_base_service, mock_bedrock_client
    ):
        """Test getting ingestion job status."""
        mock_bedrock_client.get_ingestion_job.return_value = {
            "ingestionJob": {
                "knowledgeBaseId": "kb-123456789",
                "dataSourceId": "ds-123456789",
                "ingestionJobId": "job-123456789",
                "status": "COMPLETE",
                "statistics": {
                    "numberOfDocumentsScanned": 100,
                    "numberOfNewDocumentsIndexed": 50,
                    "numberOfModifiedDocumentsIndexed": 25,
                    "numberOfDocumentsDeleted": 5,
                },
            }
        }

        result = await knowledge_base_service.get_ingestion_job(
            "kb-123456789", "ds-123456789", "job-123456789"
        )

        assert result["status"] == "COMPLETE"
        assert result["statistics"]["numberOfDocumentsScanned"] == 100
        mock_bedrock_client.get_ingestion_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_success(
        self, knowledge_base_service, mock_bedrock_client, sample_kb_data
    ):
        """Test successful health check."""
        mock_bedrock_client.get_knowledge_base.return_value = {
            "knowledgeBase": sample_kb_data
        }

        health = await knowledge_base_service.health_check("kb-123456789")

        assert health.knowledge_base_id == "kb-123456789"
        assert health.status == "HEALTHY"
        assert "status" in health.details

    @pytest.mark.asyncio
    async def test_health_check_failure(
        self, knowledge_base_service, mock_bedrock_client
    ):
        """Test health check with unhealthy knowledge base."""
        from botocore.exceptions import ClientError

        mock_bedrock_client.get_knowledge_base.side_effect = ClientError(
            error_response={
                "Error": {
                    "Code": "ResourceNotFoundException",
                    "Message": "Knowledge base not found",
                }
            },
            operation_name="GetKnowledgeBase",
        )

        health = await knowledge_base_service.health_check("kb-nonexistent")

        assert health.knowledge_base_id == "kb-nonexistent"
        assert health.status == "UNHEALTHY"
        assert "error" in health.details

    def test_error_handling_with_invalid_region(self):
        """Test error handling with invalid region."""
        with patch("boto3.client") as mock_client:
            mock_client.side_effect = Exception("Invalid region")

            with pytest.raises(Exception) as exc_info:
                KnowledgeBaseService(region="invalid-region")

            assert "Invalid region" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_query_with_custom_retrieval_config(self, knowledge_base_service):
        """Test query with custom retrieval configuration."""
        with patch(
            "src.open_bedrock_server.services.knowledge_base_service.boto3.client"
        ) as mock_client:
            mock_runtime = Mock()
            mock_client.return_value = mock_runtime

            mock_runtime.retrieve.return_value = {"retrievalResults": []}

            service = KnowledgeBaseService(region="us-east-1")

            query = KnowledgeBaseQuery(
                query_text="Test query",
                retrieval_config=RetrievalConfig(
                    vector_search_config={
                        "numberOfResults": 5,
                        "overrideSearchType": "SEMANTIC",
                    }
                ),
            )

            await service.query_knowledge_base("kb-123456789", query)

            # Verify the retrieval config was passed correctly
            call_args = mock_runtime.retrieve.call_args[1]
            assert (
                call_args["retrievalConfiguration"]["vectorSearchConfiguration"][
                    "numberOfResults"
                ]
                == 5
            )
            assert (
                call_args["retrievalConfiguration"]["vectorSearchConfiguration"][
                    "overrideSearchType"
                ]
                == "SEMANTIC"
            )

    @pytest.mark.asyncio
    async def test_concurrent_operations(
        self, knowledge_base_service, mock_bedrock_client, sample_kb_data
    ):
        """Test concurrent operations don't interfere with each other."""
        import asyncio

        mock_bedrock_client.get_knowledge_base.return_value = {
            "knowledgeBase": sample_kb_data
        }

        # Run multiple concurrent operations
        tasks = [knowledge_base_service.get_knowledge_base(f"kb-{i}") for i in range(5)]

        results = await asyncio.gather(*tasks)

        assert len(results) == 5
        for result in results:
            assert result.knowledge_base_id == "kb-123456789"

        # Verify all calls were made
        assert mock_bedrock_client.get_knowledge_base.call_count == 5


# Cleanup fixture to ensure no AWS resources are left behind
@pytest.fixture(autouse=True)
def cleanup_aws_resources():
    """Automatically cleanup any AWS resources after each test."""
    # This fixture runs before each test
    yield

    # This runs after each test - cleanup would go here
    # Since we're using mocks, no real cleanup needed
    # But in integration tests, you would cleanup real resources here
    pass
