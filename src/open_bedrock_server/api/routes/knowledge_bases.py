import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from ...core.exceptions import (
    ServiceApiError,
    ServiceAuthenticationError,
    ServiceUnavailableError,
)
from ...core.knowledge_base_models import (
    CreateDataSourceRequest,
    CreateKnowledgeBaseRequest,
    DataSourceInfo,
    KnowledgeBaseInfo,
    KnowledgeBaseQueryRequest,
    KnowledgeBaseQueryResponse,
    ListKnowledgeBasesResponse,
    RetrieveAndGenerateRequest,
    RetrieveAndGenerateResponse,
    SyncDataSourceRequest,
    SyncDataSourceResponse,
)
from ...services.knowledge_base_service import (
    KnowledgeBaseService,
    get_knowledge_base_service,
)
from ..middleware.auth import verify_api_key

logger = logging.getLogger(__name__)
router = APIRouter()


def get_kb_service() -> KnowledgeBaseService:
    """Get Knowledge Base service instance"""
    return get_knowledge_base_service()


# Knowledge Base Management Endpoints
@router.post(
    "/v1/knowledge-bases",
    dependencies=[Depends(verify_api_key)],
    response_model=KnowledgeBaseInfo,
    status_code=status.HTTP_201_CREATED,
)
async def create_knowledge_base(
    request: CreateKnowledgeBaseRequest,
    kb_service: KnowledgeBaseService = Depends(get_kb_service),
):
    """
    Create a new knowledge base

    This endpoint creates a new Bedrock Knowledge Base with the specified configuration.
    Requires proper IAM permissions and vector store setup.
    """
    try:
        logger.info(f"Creating knowledge base: {request.name}")
        knowledge_base = await kb_service.create_knowledge_base(request)
        logger.info(
            f"Successfully created knowledge base: {knowledge_base.knowledgeBaseId}"
        )
        return knowledge_base

    except ServiceAuthenticationError as e:
        logger.error(f"Authentication error creating knowledge base: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
        )
    except ServiceApiError as e:
        logger.error(f"API error creating knowledge base: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ServiceUnavailableError as e:
        logger.error(f"Service unavailable creating knowledge base: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error creating knowledge base: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


@router.get(
    "/v1/knowledge-bases",
    dependencies=[Depends(verify_api_key)],
    response_model=ListKnowledgeBasesResponse,
)
async def list_knowledge_bases(
    max_results: int = Query(
        default=10, ge=1, le=100, description="Maximum number of results to return"
    ),
    next_token: str | None = Query(default=None, description="Token for pagination"),
    kb_service: KnowledgeBaseService = Depends(get_kb_service),
):
    """
    List knowledge bases

    Returns a paginated list of knowledge bases accessible to the current credentials.
    """
    try:
        logger.debug(f"Listing knowledge bases (max_results={max_results})")
        response = await kb_service.list_knowledge_bases(max_results, next_token)
        return response

    except ServiceAuthenticationError as e:
        logger.error(f"Authentication error listing knowledge bases: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
        )
    except ServiceApiError as e:
        logger.error(f"API error listing knowledge bases: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error listing knowledge bases: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


@router.get(
    "/v1/knowledge-bases/{knowledge_base_id}",
    dependencies=[Depends(verify_api_key)],
    response_model=KnowledgeBaseInfo,
)
async def get_knowledge_base(
    knowledge_base_id: str, kb_service: KnowledgeBaseService = Depends(get_kb_service)
):
    """
    Get knowledge base details

    Returns detailed information about a specific knowledge base.
    """
    try:
        logger.debug(f"Getting knowledge base: {knowledge_base_id}")
        knowledge_base = await kb_service.get_knowledge_base(knowledge_base_id)
        return knowledge_base

    except ServiceAuthenticationError as e:
        logger.error(f"Authentication error getting knowledge base: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
        )
    except ServiceApiError as e:
        logger.error(f"API error getting knowledge base: {e}")
        # Check if it's a not found error
        if "ResourceNotFoundException" in str(e) or "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Knowledge base not found: {knowledge_base_id}",
            )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error getting knowledge base: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


@router.delete(
    "/v1/knowledge-bases/{knowledge_base_id}",
    dependencies=[Depends(verify_api_key)],
    status_code=status.HTTP_200_OK,
)
async def delete_knowledge_base(
    knowledge_base_id: str, kb_service: KnowledgeBaseService = Depends(get_kb_service)
):
    """
    Delete a knowledge base

    Deletes the specified knowledge base and all associated data sources.
    This operation cannot be undone.
    """
    try:
        logger.info(f"Deleting knowledge base: {knowledge_base_id}")
        result = await kb_service.delete_knowledge_base(knowledge_base_id)
        logger.info(f"Successfully deleted knowledge base: {knowledge_base_id}")
        return result

    except ServiceAuthenticationError as e:
        logger.error(f"Authentication error deleting knowledge base: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
        )
    except ServiceApiError as e:
        logger.error(f"API error deleting knowledge base: {e}")
        if "ResourceNotFoundException" in str(e) or "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Knowledge base not found: {knowledge_base_id}",
            )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error deleting knowledge base: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


# Knowledge Base Query Endpoints
@router.post(
    "/v1/knowledge-bases/{knowledge_base_id}/query",
    dependencies=[Depends(verify_api_key)],
    response_model=KnowledgeBaseQueryResponse,
)
async def query_knowledge_base(
    knowledge_base_id: str,
    query: str = Query(..., description="Query text to search in the knowledge base"),
    max_results: int = Query(
        default=10, ge=1, le=100, description="Maximum number of results"
    ),
    kb_service: KnowledgeBaseService = Depends(get_kb_service),
):
    """
    Query knowledge base directly

    Performs a retrieval-only query against the knowledge base.
    Returns relevant document chunks without generation.
    """
    try:
        logger.debug(f"Querying knowledge base {knowledge_base_id}: {query}")

        query_request = KnowledgeBaseQueryRequest(
            query=query, knowledgeBaseId=knowledge_base_id, maxResults=max_results
        )

        response = await kb_service.retrieve(query_request)
        return response

    except ServiceAuthenticationError as e:
        logger.error(f"Authentication error querying knowledge base: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
        )
    except ServiceApiError as e:
        logger.error(f"API error querying knowledge base: {e}")
        if "ResourceNotFoundException" in str(e) or "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Knowledge base not found: {knowledge_base_id}",
            )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error querying knowledge base: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


@router.post(
    "/v1/knowledge-bases/{knowledge_base_id}/retrieve-and-generate",
    dependencies=[Depends(verify_api_key)],
    response_model=RetrieveAndGenerateResponse,
)
async def retrieve_and_generate(
    knowledge_base_id: str,
    request: RetrieveAndGenerateRequest,
    kb_service: KnowledgeBaseService = Depends(get_kb_service),
):
    """
    Retrieve and generate response

    Queries the knowledge base and generates a response based on retrieved content.
    Returns generated text with citations to source documents.
    """
    try:
        logger.debug(
            f"Retrieve and generate for KB {knowledge_base_id}: {request.query}"
        )

        # Ensure the knowledge base ID matches
        request.knowledgeBaseId = knowledge_base_id

        response = await kb_service.retrieve_and_generate(request)
        return response

    except ServiceAuthenticationError as e:
        logger.error(f"Authentication error in retrieve and generate: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
        )
    except ServiceApiError as e:
        logger.error(f"API error in retrieve and generate: {e}")
        if "ResourceNotFoundException" in str(e) or "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Knowledge base not found: {knowledge_base_id}",
            )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in retrieve and generate: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


# Data Source Management Endpoints
@router.post(
    "/v1/knowledge-bases/{knowledge_base_id}/data-sources",
    dependencies=[Depends(verify_api_key)],
    response_model=DataSourceInfo,
    status_code=status.HTTP_201_CREATED,
)
async def create_data_source(
    knowledge_base_id: str,
    request: CreateDataSourceRequest,
    kb_service: KnowledgeBaseService = Depends(get_kb_service),
):
    """
    Create a data source for a knowledge base

    Adds a new data source (e.g., S3 bucket) to the specified knowledge base.
    The data source will need to be synced after creation.
    """
    try:
        logger.info(f"Creating data source for KB {knowledge_base_id}: {request.name}")

        # Ensure the knowledge base ID matches
        request.knowledgeBaseId = knowledge_base_id

        data_source = await kb_service.create_data_source(request)
        logger.info(f"Successfully created data source: {data_source.dataSourceId}")
        return data_source

    except ServiceAuthenticationError as e:
        logger.error(f"Authentication error creating data source: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
        )
    except ServiceApiError as e:
        logger.error(f"API error creating data source: {e}")
        if "ResourceNotFoundException" in str(e) or "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Knowledge base not found: {knowledge_base_id}",
            )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error creating data source: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


@router.post(
    "/v1/knowledge-bases/{knowledge_base_id}/data-sources/{data_source_id}/sync",
    dependencies=[Depends(verify_api_key)],
    response_model=SyncDataSourceResponse,
)
async def sync_data_source(
    knowledge_base_id: str,
    data_source_id: str,
    kb_service: KnowledgeBaseService = Depends(get_kb_service),
):
    """
    Sync a data source

    Starts an ingestion job to sync the data source with the knowledge base.
    This process extracts, chunks, and indexes the content from the data source.
    """
    try:
        logger.info(f"Syncing data source {data_source_id} for KB {knowledge_base_id}")

        sync_request = SyncDataSourceRequest(
            knowledgeBaseId=knowledge_base_id, dataSourceId=data_source_id
        )

        response = await kb_service.sync_data_source(sync_request)
        logger.info(f"Successfully started sync for data source: {data_source_id}")
        return response

    except ServiceAuthenticationError as e:
        logger.error(f"Authentication error syncing data source: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
        )
    except ServiceApiError as e:
        logger.error(f"API error syncing data source: {e}")
        if "ResourceNotFoundException" in str(e) or "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Knowledge base or data source not found",
            )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error syncing data source: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


# Health Check
@router.get("/v1/knowledge-bases/health")
async def knowledge_bases_health():
    """
    Health check for Knowledge Base service
    """
    try:
        # Try to create a service instance to verify configuration
        kb_service = get_kb_service()
        return {
            "status": "healthy",
            "service": "knowledge_bases",
            "aws_region": kb_service.AWS_REGION,
            "timestamp": logger.name,  # placeholder for actual timestamp
        }
    except Exception as e:
        logger.error(f"Knowledge Base service health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "service": "knowledge_bases",
                "error": str(e),
            },
        )
