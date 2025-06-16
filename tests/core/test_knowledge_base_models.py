from datetime import datetime

import pytest
from pydantic import ValidationError

from src.open_bedrock_server.core.knowledge_base_models import (
    ChunkingConfiguration,
    Citation,
    CreateDataSourceRequest,
    CreateKnowledgeBaseRequest,
    DataSourceConfiguration,
    DataSourceType,
    EmbeddingModelConfiguration,
    FieldMapping,
    KnowledgeBaseConfiguration,
    KnowledgeBaseInfo,
    KnowledgeBaseQueryRequest,
    KnowledgeBaseQueryResponse,
    KnowledgeBaseStatus,
    OpenSearchServerlessConfiguration,
    RetrievalResult,
    RetrieveAndGenerateRequest,
    RetrieveAndGenerateResponse,
    S3Configuration,
    StorageConfiguration,
    VectorIngestionConfiguration,
    VectorKnowledgeBaseConfiguration,
    VectorStoreType,
)


@pytest.mark.knowledge_base
@pytest.mark.unit
class TestKnowledgeBaseModels:
    """Test Knowledge Base model validation and serialization."""

    def test_create_knowledge_base_request_creation(self):
        """Test CreateKnowledgeBaseRequest model creation and validation."""
        # First create the nested configurations
        embedding_config = EmbeddingModelConfiguration(
            dimensions=1536, embeddingDataType="FLOAT32"
        )

        vector_config = VectorKnowledgeBaseConfiguration(
            embeddingModelArn="arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v1",
            embeddingModelConfiguration=embedding_config,
        )

        kb_config = KnowledgeBaseConfiguration(
            type="VECTOR", vectorKnowledgeBaseConfiguration=vector_config
        )

        field_mapping = FieldMapping(
            vectorField="vector", textField="text", metadataField="metadata"
        )

        opensearch_config = OpenSearchServerlessConfiguration(
            collectionArn="arn:aws:aoss:us-east-1:123456789012:collection/test-collection",
            vectorIndexName="test-index",
            fieldMapping=field_mapping,
        )

        storage_config = StorageConfiguration(
            type=VectorStoreType.OPENSEARCH_SERVERLESS,
            opensearchServerlessConfiguration=opensearch_config,
        )

        # Now create the main request
        request = CreateKnowledgeBaseRequest(
            name="test-kb",
            description="Test knowledge base",
            roleArn="arn:aws:iam::123456789012:role/test-role",
            knowledgeBaseConfiguration=kb_config,
            storageConfiguration=storage_config,
            tags={"environment": "test", "project": "chat-completions"},
        )

        assert request.name == "test-kb"
        assert request.description == "Test knowledge base"
        assert request.roleArn == "arn:aws:iam::123456789012:role/test-role"
        assert request.knowledgeBaseConfiguration.type == "VECTOR"
        assert request.tags == {"environment": "test", "project": "chat-completions"}

    def test_create_knowledge_base_request_minimal(self):
        """Test CreateKnowledgeBaseRequest with minimal required fields."""
        vector_config = VectorKnowledgeBaseConfiguration(
            embeddingModelArn="arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v1"
        )

        kb_config = KnowledgeBaseConfiguration(
            vectorKnowledgeBaseConfiguration=vector_config
        )

        request = CreateKnowledgeBaseRequest(
            name="minimal-kb",
            roleArn="arn:aws:iam::123456789012:role/test-role",
            knowledgeBaseConfiguration=kb_config,
        )

        assert request.name == "minimal-kb"
        assert request.description is None
        assert request.storageConfiguration is None

    def test_create_knowledge_base_request_validation_errors(self):
        """Test CreateKnowledgeBaseRequest validation errors."""
        # Missing required fields
        with pytest.raises(ValidationError) as exc_info:
            CreateKnowledgeBaseRequest()

        errors = exc_info.value.errors()
        required_fields = {
            error["loc"][0] for error in errors if error["type"] == "missing"
        }
        assert "name" in required_fields
        assert "roleArn" in required_fields
        assert "knowledgeBaseConfiguration" in required_fields

    def test_data_source_request_creation(self):
        """Test CreateDataSourceRequest model."""
        s3_config = S3Configuration(
            bucketArn="arn:aws:s3:::test-bucket",
            inclusionPrefixes=["documents/"],
            exclusionPrefixes=["temp/"],
        )

        ds_config = DataSourceConfiguration(
            type=DataSourceType.S3, s3Configuration=s3_config
        )

        chunking_config = ChunkingConfiguration(
            chunkingStrategy="FIXED_SIZE",
            fixedSizeChunkingConfiguration={"maxTokens": 300, "overlapPercentage": 20},
        )

        vector_ingestion = VectorIngestionConfiguration(
            chunkingConfiguration=chunking_config
        )

        request = CreateDataSourceRequest(
            name="test-datasource",
            description="Test data source",
            knowledgeBaseId="kb-123456789",
            dataSourceConfiguration=ds_config,
            vectorIngestionConfiguration=vector_ingestion,
        )

        assert request.name == "test-datasource"
        assert request.knowledgeBaseId == "kb-123456789"
        assert request.dataSourceConfiguration.type == DataSourceType.S3

    def test_knowledge_base_query_request(self):
        """Test KnowledgeBaseQueryRequest model."""
        request = KnowledgeBaseQueryRequest(
            query="What is machine learning?",
            knowledgeBaseId="kb-123456789",
            maxResults=5,
            retrievalConfiguration={
                "vectorSearchConfiguration": {
                    "numberOfResults": 5,
                    "overrideSearchType": "SEMANTIC",
                }
            },
        )

        assert request.query == "What is machine learning?"
        assert request.knowledgeBaseId == "kb-123456789"
        assert request.maxResults == 5

    def test_retrieve_and_generate_request(self):
        """Test RetrieveAndGenerateRequest model."""
        request = RetrieveAndGenerateRequest(
            query="Explain quantum computing",
            knowledgeBaseId="kb-123456789",
            modelArn="arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-haiku-20240307-v1:0",
            retrievalConfiguration={
                "vectorSearchConfiguration": {
                    "numberOfResults": 3,
                    "overrideSearchType": "SEMANTIC",
                }
            },
            generationConfiguration={"maxTokens": 500, "temperature": 0.7, "topP": 0.9},
            sessionId="session-123",
        )

        assert request.query == "Explain quantum computing"
        assert request.knowledgeBaseId == "kb-123456789"
        assert request.sessionId == "session-123"

    def test_knowledge_base_info_model(self):
        """Test KnowledgeBaseInfo response model."""
        vector_config = VectorKnowledgeBaseConfiguration(
            embeddingModelArn="arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v1"
        )

        kb_config = KnowledgeBaseConfiguration(
            vectorKnowledgeBaseConfiguration=vector_config
        )

        info = KnowledgeBaseInfo(
            knowledgeBaseId="kb-123456789",
            name="test-kb",
            description="Test knowledge base",
            knowledgeBaseArn="arn:aws:bedrock:us-east-1:123456789012:knowledge-base/kb-123456789",
            status=KnowledgeBaseStatus.ACTIVE,
            roleArn="arn:aws:iam::123456789012:role/test-role",
            knowledgeBaseConfiguration=kb_config,
            createdAt=datetime.now(),
            updatedAt=datetime.now(),
        )

        assert info.knowledgeBaseId == "kb-123456789"
        assert info.status == KnowledgeBaseStatus.ACTIVE
        assert isinstance(info.createdAt, datetime)

    def test_retrieval_result_model(self):
        """Test RetrievalResult model."""
        result = RetrievalResult(
            content="Machine learning is a subset of artificial intelligence...",
            metadata={"source": "ml_textbook.pdf", "page": 1},
            location={
                "type": "S3",
                "s3Location": {"uri": "s3://test-bucket/ml_textbook.pdf"},
            },
            score=0.95,
        )

        assert (
            result.content
            == "Machine learning is a subset of artificial intelligence..."
        )
        assert result.score == 0.95
        assert result.metadata["source"] == "ml_textbook.pdf"

    def test_citation_model(self):
        """Test Citation model."""
        citation = Citation(
            generatedResponsePart={
                "textResponsePart": {
                    "text": "Machine learning is a subset of artificial intelligence",
                    "span": {"start": 0, "end": 52},
                }
            },
            retrievedReferences=[
                {
                    "content": {
                        "text": "Machine learning is a subset of artificial intelligence..."
                    },
                    "location": {
                        "type": "S3",
                        "s3Location": {"uri": "s3://test-bucket/ml_textbook.pdf"},
                    },
                    "metadata": {"source": "ml_textbook.pdf", "page": 1},
                }
            ],
        )

        assert (
            "Machine learning is a subset"
            in citation.generatedResponsePart["textResponsePart"]["text"]
        )
        assert len(citation.retrievedReferences) == 1

    def test_query_response_model(self):
        """Test KnowledgeBaseQueryResponse model."""
        result = RetrievalResult(
            content="ML content...",
            score=0.9,
            metadata={"source": "doc.pdf"},
            location={"type": "S3", "s3Location": {"uri": "s3://bucket/doc.pdf"}},
        )

        response = KnowledgeBaseQueryResponse(
            retrievalResults=[result], nextToken="next-token-123"
        )

        assert len(response.retrievalResults) == 1
        assert response.nextToken == "next-token-123"

    def test_rag_response_model(self):
        """Test RetrieveAndGenerateResponse model."""
        citation = Citation(
            generatedResponsePart={"textResponsePart": {"text": "Generated text"}},
            retrievedReferences=[{"content": {"text": "Reference text"}}],
        )

        response = RetrieveAndGenerateResponse(
            output="Machine learning is a powerful technology...",
            citations=[citation],
            sessionId="session-123",
        )

        assert response.output == "Machine learning is a powerful technology..."
        assert len(response.citations) == 1
        assert response.sessionId == "session-123"

    def test_enum_validations(self):
        """Test enum validations."""
        # Test KnowledgeBaseStatus
        assert KnowledgeBaseStatus.ACTIVE == "ACTIVE"
        assert KnowledgeBaseStatus.CREATING == "CREATING"

        # Test DataSourceType
        assert DataSourceType.S3 == "S3"
        assert DataSourceType.WEB == "WEB"

        # Test VectorStoreType
        assert VectorStoreType.OPENSEARCH_SERVERLESS == "OPENSEARCH_SERVERLESS"
        assert VectorStoreType.PINECONE == "PINECONE"

    def test_model_serialization(self):
        """Test that models can be properly serialized to dict and JSON."""
        vector_config = VectorKnowledgeBaseConfiguration(
            embeddingModelArn="arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v1"
        )

        kb_config = KnowledgeBaseConfiguration(
            vectorKnowledgeBaseConfiguration=vector_config
        )

        request = CreateKnowledgeBaseRequest(
            name="test-kb",
            roleArn="arn:aws:iam::123456789012:role/test-role",
            knowledgeBaseConfiguration=kb_config,
        )

        # Test dict serialization
        request_dict = request.model_dump()
        assert isinstance(request_dict, dict)
        assert request_dict["name"] == "test-kb"

        # Test JSON serialization
        request_json = request.model_dump_json()
        assert isinstance(request_json, str)
        assert "test-kb" in request_json

    def test_model_deserialization(self):
        """Test that models can be properly deserialized from dict."""
        request_data = {
            "name": "test-kb",
            "roleArn": "arn:aws:iam::123456789012:role/test-role",
            "knowledgeBaseConfiguration": {
                "type": "VECTOR",
                "vectorKnowledgeBaseConfiguration": {
                    "embeddingModelArn": "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v1"
                },
            },
        }

        request = CreateKnowledgeBaseRequest.model_validate(request_data)
        assert request.name == "test-kb"
        assert request.knowledgeBaseConfiguration.type == "VECTOR"
