import time

from pydantic import BaseModel, Field


class FileUploadResponse(BaseModel):
    """OpenAI-compatible file upload response schema."""

    id: str = Field(
        ..., description="Unique identifier for the file (e.g., file-xxxxxxxxxxxxxxxxx)"
    )
    object: str = Field(default="file", description="Type of object, always 'file'")
    bytes: int = Field(..., description="Size of the uploaded file in bytes")
    created_at: int = Field(
        ..., description="Unix timestamp of when the file was uploaded"
    )
    filename: str = Field(..., description="Original filename provided by the user")
    purpose: str = Field(
        ..., description="Purpose of the file as specified in the request"
    )
    status: str = Field(
        default="uploaded", description="Status of the file, typically 'uploaded'"
    )
    status_details: str | None = Field(
        None, description="Additional details about the file status"
    )

    @classmethod
    def create_response(
        cls, file_id: str, filename: str, purpose: str, file_size: int
    ) -> "FileUploadResponse":
        """Factory method to create a file upload response."""
        return cls(
            id=file_id,
            bytes=file_size,
            created_at=int(time.time()),
            filename=filename,
            purpose=purpose,
        )


class FileMetadata(BaseModel):
    """Internal file metadata model for storage and tracking."""

    file_id: str
    filename: str
    purpose: str
    s3_bucket: str
    s3_key: str
    content_type: str
    file_size: int
    created_at: int
    status: str = "uploaded"
