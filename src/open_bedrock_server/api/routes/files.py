import logging

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)

from ...core.exceptions import ConfigurationError, ServiceApiError
from ...services.file_service import FileService
from ..middleware.auth import verify_api_key
from ..schemas.file_schemas import FileUploadResponse

logger = logging.getLogger(__name__)
router = APIRouter()


# Initialize file service (will be created once and reused)
_file_service: FileService | None = None


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
                detail=f"File service configuration error: {str(e)}",
            )
    return _file_service


@router.post(
    "/v1/files",
    dependencies=[Depends(verify_api_key)],
    response_model=FileUploadResponse,
)
async def upload_file(
    file: UploadFile = File(..., description="The file to upload"),
    purpose: str = Form(
        ...,
        description="The purpose of the file (e.g., 'fine-tune', 'assistants', 'batch')",
    ),
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
            detail="Missing required field: 'file'",
        )

    if not purpose:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required field: 'purpose'",
        )

    # Validate file
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="File must have a filename"
        )

    try:
        # Get file service
        file_service = get_file_service()

        # Read file content
        logger.info(f"Processing file upload: {file.filename}, purpose: {purpose}")
        file_content = await file.read()

        if not file_content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="File is empty"
            )

        # Determine content type
        content_type = file.content_type or "application/octet-stream"

        # Upload file to S3
        metadata = await file_service.upload_file(
            file_content=file_content,
            filename=file.filename,
            purpose=purpose,
            content_type=content_type,
        )

        # Create OpenAI-compatible response
        response = FileUploadResponse.create_response(
            file_id=metadata.file_id,
            filename=metadata.filename,
            purpose=metadata.purpose,
            file_size=metadata.file_size,
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
            detail=f"Server configuration error: {str(e)}",
        )
    except ServiceApiError as e:
        logger.error(f"Service error during file upload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File upload failed: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Unexpected error during file upload: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during file upload",
        )
    finally:
        # Ensure file is closed
        await file.close()


@router.get("/health")
async def files_health():
    """Health check endpoint for the files service."""
    try:
        file_service = get_file_service()
        # Simple check that the service is configured
        return {
            "status": "healthy",
            "service": "files",
            "s3_configured": file_service.s3_bucket is not None,
        }
    except Exception as e:
        return {"status": "unhealthy", "service": "files", "error": str(e)}


@router.get("/v1/files/health")
async def files_health_v1():
    """Health check endpoint for the files service - v1 API."""
    try:
        file_service = get_file_service()

        # Validate AWS credentials if possible
        try:
            await file_service.validate_credentials()
            credentials_valid = True
        except Exception:
            credentials_valid = False

        return {
            "status": "healthy",
            "service": "files",
            "s3_bucket_configured": file_service.s3_bucket is not None,
            "aws_region": getattr(file_service, "AWS_REGION", "us-east-1"),
            "credentials_valid": credentials_valid,
        }
    except Exception as e:
        logger.error(f"Failed to get file health: {e}")
        return {"status": "unhealthy", "service": "files", "error": str(e)}


@router.get("/v1/files")
async def list_files(
    purpose: str | None = Query(None, description="Filter files by purpose"),
    limit: int = Query(20, ge=1, le=100, description="Number of files to retrieve"),
):
    """List files with optional filtering."""
    try:
        file_service = get_file_service()
        files = await file_service.list_files(purpose=purpose, limit=limit)

        # Convert to OpenAI-compatible format
        return {
            "object": "list",
            "data": [
                {
                    "id": file.file_id,
                    "object": "file",
                    "bytes": file.file_size,
                    "created_at": file.created_at,
                    "filename": file.filename,
                    "purpose": file.purpose,
                    "status": "processed",  # Assuming all files are processed
                }
                for file in files
            ],
        }
    except Exception as e:
        logger.error(f"Failed to list files: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")


@router.get("/v1/files/{file_id}")
async def get_file(file_id: str):
    """Retrieve metadata for a specific file."""
    try:
        file_service = get_file_service()
        metadata = await file_service.get_file_metadata(file_id)

        if not metadata:
            raise HTTPException(status_code=404, detail=f"File {file_id} not found")

        # Return OpenAI-compatible format
        return {
            "id": metadata.file_id,
            "object": "file",
            "bytes": metadata.file_size,
            "created_at": metadata.created_at,
            "filename": metadata.filename,
            "purpose": metadata.purpose,
            "status": "processed",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get file {file_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve file: {str(e)}"
        )


@router.get("/v1/files/{file_id}/content")
async def get_file_content(file_id: str):
    """Download file content."""
    try:
        file_service = get_file_service()

        # Get metadata first to check if file exists and get content type
        metadata = await file_service.get_file_metadata(file_id)
        if not metadata:
            raise HTTPException(status_code=404, detail=f"File {file_id} not found")

        # Get file content
        content = await file_service.get_file_content(file_id)
        if content is None:
            raise HTTPException(
                status_code=404, detail=f"File content for {file_id} not found"
            )

        # Return file content with appropriate headers
        return Response(
            content=content,
            media_type=metadata.content_type,
            headers={
                "Content-Disposition": f"attachment; filename={metadata.filename}",
                "Content-Length": str(len(content)),
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get file content for {file_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve file content: {str(e)}"
        )


@router.delete("/v1/files/{file_id}")
async def delete_file(file_id: str):
    """Delete a file."""
    try:
        file_service = get_file_service()

        # Check if file exists first
        metadata = await file_service.get_file_metadata(file_id)
        if not metadata:
            raise HTTPException(status_code=404, detail=f"File {file_id} not found")

        # Delete the file
        success = await file_service.delete_file_by_id(file_id)
        if not success:
            raise HTTPException(
                status_code=500, detail=f"Failed to delete file {file_id}"
            )

        return {"id": file_id, "object": "file", "deleted": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete file {file_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")
