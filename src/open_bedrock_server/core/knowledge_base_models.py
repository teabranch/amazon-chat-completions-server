from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class KnowledgeBaseStatus(str, Enum):
    CREATING = "CREATING"
    ACTIVE = "ACTIVE"
    DELETING = "DELETING"
    UPDATING = "UPDATING"
    FAILED = "FAILED"
    DELETE_UNSUCCESSFUL = "DELETE_UNSUCCESSFUL"


class DataSourceType(str, Enum):
    S3 = "S3"
    WEB = "WEB"
    CONFLUENCE = "CONFLUENCE"
    SHAREPOINT = "SHAREPOINT"
    SALESFORCE = "SALESFORCE"


class VectorStoreType(str, Enum):
    OPENSEARCH_SERVERLESS = "OPENSEARCH_SERVERLESS"
    PINECONE = "PINECONE"
    REDIS_ENTERPRISE_CLOUD = "REDIS_ENTERPRISE_CLOUD"
    RDS = "RDS"


class EmbeddingModelConfiguration(BaseModel):
    dimensions: int | None = Field(None, description="Vector dimensions")
    embeddingDataType: Literal["FLOAT32", "BINARY"] | None = Field(
        None, description="Embedding data type"
    )


class VectorKnowledgeBaseConfiguration(BaseModel):
    embeddingModelArn: str = Field(..., description="ARN of the embedding model")
    embeddingModelConfiguration: EmbeddingModelConfiguration | None = None


class KnowledgeBaseConfiguration(BaseModel):
    type: Literal["VECTOR"] = Field(default="VECTOR", description="Knowledge base type")
    vectorKnowledgeBaseConfiguration: VectorKnowledgeBaseConfiguration


class FieldMapping(BaseModel):
    textField: str = Field(..., description="Text field name")
    metadataField: str = Field(..., description="Metadata field name")
    vectorField: str = Field(..., description="Vector field name")


class OpenSearchServerlessConfiguration(BaseModel):
    collectionArn: str = Field(..., description="OpenSearch Serverless collection ARN")
    vectorIndexName: str = Field(..., description="Vector index name")
    fieldMapping: FieldMapping


class StorageConfiguration(BaseModel):
    type: VectorStoreType = Field(..., description="Vector store type")
    opensearchServerlessConfiguration: OpenSearchServerlessConfiguration | None = None


class S3Configuration(BaseModel):
    bucketArn: str = Field(..., description="S3 bucket ARN")
    inclusionPrefixes: list[str] | None = Field(None, description="Inclusion prefixes")
    exclusionPrefixes: list[str] | None = Field(None, description="Exclusion prefixes")


class DataSourceConfiguration(BaseModel):
    type: DataSourceType = Field(..., description="Data source type")
    s3Configuration: S3Configuration | None = None


class ChunkingConfiguration(BaseModel):
    chunkingStrategy: Literal["FIXED_SIZE", "NONE"] = Field(default="FIXED_SIZE")
    fixedSizeChunkingConfiguration: dict[str, Any] | None = None


class ParsingConfiguration(BaseModel):
    parsingStrategy: Literal["BEDROCK_FOUNDATION_MODEL"] = Field(
        default="BEDROCK_FOUNDATION_MODEL"
    )
    bedrockFoundationModelConfiguration: dict[str, Any] | None = None


class VectorIngestionConfiguration(BaseModel):
    chunkingConfiguration: ChunkingConfiguration | None = None
    parsingConfiguration: ParsingConfiguration | None = None


# Request Models
class CreateKnowledgeBaseRequest(BaseModel):
    name: str = Field(..., description="Name of the knowledge base")
    description: str | None = Field(
        None, description="Description of the knowledge base"
    )
    roleArn: str = Field(..., description="IAM role ARN for the knowledge base")
    knowledgeBaseConfiguration: KnowledgeBaseConfiguration
    storageConfiguration: StorageConfiguration | None = None
    tags: dict[str, str] | None = Field(None, description="Tags for the knowledge base")


class CreateDataSourceRequest(BaseModel):
    name: str = Field(..., description="Name of the data source")
    description: str | None = Field(None, description="Description of the data source")
    knowledgeBaseId: str = Field(..., description="Knowledge base ID")
    dataSourceConfiguration: DataSourceConfiguration
    vectorIngestionConfiguration: VectorIngestionConfiguration | None = None


class KnowledgeBaseQueryRequest(BaseModel):
    query: str = Field(..., description="Query text")
    knowledgeBaseId: str = Field(..., description="Knowledge base ID")
    maxResults: int | None = Field(
        default=10, ge=1, le=100, description="Maximum number of results"
    )
    retrievalConfiguration: dict[str, Any] | None = Field(
        None, description="Retrieval configuration"
    )


class RetrieveAndGenerateRequest(BaseModel):
    query: str = Field(..., description="Query text")
    knowledgeBaseId: str = Field(..., description="Knowledge base ID")
    modelArn: str = Field(..., description="Model ARN for generation")
    retrievalConfiguration: dict[str, Any] | None = Field(
        None, description="Retrieval configuration"
    )
    generationConfiguration: dict[str, Any] | None = Field(
        None, description="Generation configuration"
    )
    sessionId: str | None = Field(
        None, description="Session ID for conversation continuity"
    )


# Response Models
class KnowledgeBaseInfo(BaseModel):
    knowledgeBaseId: str = Field(..., description="Knowledge base ID")
    name: str = Field(..., description="Knowledge base name")
    description: str | None = Field(None, description="Knowledge base description")
    knowledgeBaseArn: str = Field(..., description="Knowledge base ARN")
    status: KnowledgeBaseStatus = Field(..., description="Knowledge base status")
    roleArn: str = Field(..., description="IAM role ARN")
    knowledgeBaseConfiguration: KnowledgeBaseConfiguration
    storageConfiguration: StorageConfiguration | None = None
    failureReasons: list[str] | None = Field(
        None, description="Failure reasons if status is FAILED"
    )
    createdAt: datetime = Field(..., description="Creation timestamp")
    updatedAt: datetime = Field(..., description="Last update timestamp")


class DataSourceInfo(BaseModel):
    dataSourceId: str = Field(..., description="Data source ID")
    knowledgeBaseId: str = Field(..., description="Knowledge base ID")
    name: str = Field(..., description="Data source name")
    description: str | None = Field(None, description="Data source description")
    dataSourceConfiguration: DataSourceConfiguration
    status: str = Field(..., description="Data source status")
    createdAt: datetime = Field(..., description="Creation timestamp")
    updatedAt: datetime = Field(..., description="Last update timestamp")


class RetrievalResult(BaseModel):
    content: str = Field(..., description="Retrieved content")
    metadata: dict[str, Any] | None = Field(None, description="Content metadata")
    location: dict[str, Any] | None = Field(None, description="Source location")
    score: float | None = Field(None, description="Relevance score")


class Citation(BaseModel):
    generatedResponsePart: dict[str, Any] = Field(
        ..., description="Generated response part with span"
    )
    retrievedReferences: list[dict[str, Any]] = Field(
        ..., description="Retrieved references"
    )


class KnowledgeBaseQueryResponse(BaseModel):
    retrievalResults: list[RetrievalResult] = Field(
        ..., description="Retrieval results"
    )
    nextToken: str | None = Field(None, description="Next token for pagination")


class RetrieveAndGenerateResponse(BaseModel):
    output: str = Field(..., description="Generated response")
    citations: list[Citation] = Field(..., description="Citations")
    sessionId: str | None = Field(None, description="Session ID")
    guardrailAction: str | None = Field(None, description="Guardrail action")


class ListKnowledgeBasesResponse(BaseModel):
    knowledgeBaseSummaries: list[KnowledgeBaseInfo] = Field(
        ..., description="Knowledge base summaries"
    )
    nextToken: str | None = Field(None, description="Next token for pagination")


class ListDataSourcesResponse(BaseModel):
    dataSourceSummaries: list[DataSourceInfo] = Field(
        ..., description="Data source summaries"
    )
    nextToken: str | None = Field(None, description="Next token for pagination")


class SyncDataSourceRequest(BaseModel):
    knowledgeBaseId: str = Field(..., description="Knowledge base ID")
    dataSourceId: str = Field(..., description="Data source ID")


class SyncDataSourceResponse(BaseModel):
    executionId: str = Field(..., description="Sync execution ID")


# Extended Chat Completion Models for KB Integration
class KnowledgeBaseEnhancedChatRequest(BaseModel):
    """Extended chat completion request with knowledge base support"""

    model: str = Field(..., description="Model ID")
    messages: list[dict[str, str]] = Field(..., description="Chat messages")
    knowledge_base_id: str | None = Field(None, description="Knowledge base ID for RAG")
    auto_kb: bool = Field(
        default=False, description="Auto-detect when to use knowledge base"
    )
    max_tokens: int | None = Field(None, description="Maximum tokens in response")
    temperature: float | None = Field(None, description="Temperature for generation")
    stream: bool = Field(default=False, description="Whether to stream the response")
    retrieval_config: dict[str, Any] | None = Field(
        None, description="Knowledge base retrieval configuration"
    )
    citation_format: Literal["openai", "bedrock"] = Field(
        default="openai", description="Citation format preference"
    )
