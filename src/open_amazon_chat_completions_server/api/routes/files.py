from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, status
from typing import Optional
import logging

from ..middleware.auth import verify_api_key
from ..schemas.file_schemas import FileUploadResponse
from ...services.file_service import FileService
from ...core.exceptions import ConfigurationError, ServiceApiError

logger = logging.getLogger(__name__)
router = APIRouter()


# Initialize file service (will be created once and reused)
_file_service: Optional[FileService] = None


def get_file_service() -> FileService:
    """Get or create the file service instance."""
    global _file_service
    if _file_service is None:
        try:
            _file_service = FileService()
        except ConfigurationError as e:
            logger.error(f"Failed to initialize FileService: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"File service configuration error: {str(e)}"
            )
    return _file_service


@router.post("/v1/files", dependencies=[Depends(verify_api_key)], response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(..., description="The file to upload"),
    purpose: str = Form(..., description="The purpose of the file (e.g., 'fine-tune', 'assistants', 'batch')")
):
    """
    Upload a file to the server for use with OpenAI-compatible services.
    
    This endpoint mimics the OpenAI API's /v1/files upload functionality.
    Files are stored securely in Amazon S3 with appropriate metadata.
    
    Args:
        file: The file to upload (multipart/form-data)
        purpose: The intended use of the file
        
    Returns:
        FileUploadResponse: OpenAI-compatible response with file metadata
        
    Raises:
        HTTPException: 400 for bad requests, 500 for server errors
    """
    # Validate required fields
    if not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required field: 'file'"
        )
    
    if not purpose:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required field: 'purpose'"
        )
    
    # Validate file
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must have a filename"
        )
    
    try:
        # Get file service
        file_service = get_file_service()
        
        # Read file content
        logger.info(f"Processing file upload: {file.filename}, purpose: {purpose}")
        file_content = await file.read()
        
        if not file_content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is empty"
            )
        
        # Determine content type
        content_type = file.content_type or "application/octet-stream"
        
        # Upload file to S3
        metadata = await file_service.upload_file(
            file_content=file_content,
            filename=file.filename,
            purpose=purpose,
            content_type=content_type
        )
        
        # Create OpenAI-compatible response
        response = FileUploadResponse.create_response(
            file_id=metadata.file_id,
            filename=metadata.filename,
            purpose=metadata.purpose,
            file_size=metadata.file_size
        )
        
        logger.info(f"File upload completed successfully: {metadata.file_id}")
        return response
        
    except HTTPException:
        # Re-raise HTTPExceptions (like the "File is empty" error)
        raise
    except ConfigurationError as e:
        logger.error(f"Configuration error during file upload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server configuration error: {str(e)}"
        )
    except ServiceApiError as e:
        logger.error(f"Service error during file upload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File upload failed: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error during file upload: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during file upload"
        )
    finally:
        # Ensure file is closed
        await file.close()


@router.get("/v1/files/health")
async def files_health():
    """Health check endpoint for the files service."""
    try:
        file_service = get_file_service()
        # Basic health check - just verify the service can be initialized
        return {
            "status": "healthy",
            "service": "files",
            "s3_bucket_configured": bool(file_service.s3_bucket),
            "aws_region": file_service.AWS_REGION
        }
    except Exception as e:
        logger.error(f"Files health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "files",
            "error": str(e)
        } 