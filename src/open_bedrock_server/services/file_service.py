import logging
import os
import uuid

import boto3
import botocore.config
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    NoCredentialsError,
    PartialCredentialsError,
)

from ..api.schemas.file_schemas import FileMetadata
from ..core.exceptions import ConfigurationError, ServiceApiError
from ..utils.config_loader import app_config

logger = logging.getLogger(__name__)


class FileService:
    """Service for managing file uploads to S3 with OpenAI-compatible interface."""

    def __init__(
        self,
        s3_bucket: str | None = None,
        AWS_REGION: str | None = None,
        AWS_PROFILE: str | None = None,
        AWS_ROLE_ARN: str | None = None,
        AWS_EXTERNAL_ID: str | None = None,
        AWS_ROLE_SESSION_NAME: str | None = None,
        AWS_WEB_IDENTITY_TOKEN_FILE: str | None = None,
        validate_credentials: bool = True,
    ):
        """Initialize the file service with S3 configuration."""
        # Use provided parameters or fall back to config
        self.s3_bucket = s3_bucket or app_config.S3_FILES_BUCKET
        self.AWS_REGION = AWS_REGION or app_config.AWS_REGION
        self.AWS_PROFILE = AWS_PROFILE or app_config.AWS_PROFILE
        self.AWS_ROLE_ARN = AWS_ROLE_ARN or app_config.AWS_ROLE_ARN
        self.AWS_EXTERNAL_ID = AWS_EXTERNAL_ID or app_config.AWS_EXTERNAL_ID
        self.AWS_ROLE_SESSION_NAME = (
            AWS_ROLE_SESSION_NAME or app_config.AWS_ROLE_SESSION_NAME
        )
        self.AWS_WEB_IDENTITY_TOKEN_FILE = (
            AWS_WEB_IDENTITY_TOKEN_FILE or app_config.AWS_WEB_IDENTITY_TOKEN_FILE
        )
        self.validate_credentials = validate_credentials

        # Validate required configuration
        if not self.s3_bucket:
            logger.warning(
                "S3_FILES_BUCKET not configured. File uploads will fail. "
                "Please set S3_FILES_BUCKET in your environment variables."
            )

        if not self.AWS_REGION:
            logger.warning(
                "AWS_REGION not provided or found in environment. S3 calls may fail or use default region."
            )

        try:
            session = self._create_aws_session()

            # Validate credentials early if requested
            if self.validate_credentials:
                sts_client = session.client("sts")
                try:
                    caller_identity = sts_client.get_caller_identity()
                    logger.info(
                        f"AWS STS GetCallerIdentity successful for FileService. Account: {caller_identity.get('Account')}, "
                        f"User/Role: {caller_identity.get('Arn')}"
                    )
                except (NoCredentialsError, PartialCredentialsError) as e:
                    logger.error(
                        f"AWS credentials not found or incomplete for FileService: {e}"
                    )
                    raise ConfigurationError(
                        f"AWS credentials not found or incomplete for FileService: {e}"
                    )
                except ClientError as e:
                    error_code = e.response.get("Error", {}).get("Code")
                    if error_code in ["InvalidClientTokenId", "SignatureDoesNotMatch"]:
                        logger.error(
                            f"AWS STS authentication failure for FileService: {e}"
                        )
                        raise ConfigurationError(
                            f"AWS authentication failed (STS) for FileService: {e}"
                        )
                    logger.warning(
                        f"AWS STS GetCallerIdentity warning for FileService: {e}"
                    )
            else:
                logger.info(
                    "Skipping AWS credential validation for FileService (validate_credentials=False)"
                )

            # Create S3 client
            self.s3_client = session.client(
                "s3",
                config=botocore.config.Config(
                    retries={
                        "max_attempts": 3,
                        "mode": "standard",
                    }
                ),
            )
            logger.info("FileService initialized with S3 client.")

        except ConfigurationError:
            raise
        except (NoCredentialsError, PartialCredentialsError) as e:
            logger.error(
                f"AWS credentials issue during FileService S3 client initialization: {e}"
            )
            raise ConfigurationError(
                f"AWS credentials not found or incomplete for FileService S3: {e}"
            )
        except BotoCoreError as e:
            logger.error(
                f"BotoCoreError during FileService S3 client initialization: {e}"
            )
            raise ConfigurationError(
                f"AWS SDK (BotoCore) error during FileService init: {e}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize FileService S3 client: {e}")
            raise ConfigurationError(
                f"Failed to initialize AWS S3 client for FileService: {e}"
            )

    def _create_aws_session(self) -> boto3.Session:
        """Create an AWS session using the configured authentication method."""
        # Reuse the same authentication logic as BedrockService
        static_keys_present = bool(
            app_config.AWS_ACCESS_KEY_ID and app_config.AWS_SECRET_ACCESS_KEY
        )
        profile_present = bool(self.AWS_PROFILE)
        role_arn_present = bool(self.AWS_ROLE_ARN)
        web_identity_present = bool(self.AWS_WEB_IDENTITY_TOKEN_FILE)

        # Check if this is an AWS SSO role that cannot assume itself
        is_sso_role = role_arn_present and "AWSReservedSSO" in self.AWS_ROLE_ARN

        logger.info(
            f"AWS authentication methods detected for FileService - Static keys: {static_keys_present}, "
            f"Profile: {profile_present}, Role ARN: {role_arn_present}, "
            f"Web identity: {web_identity_present}, SSO Role: {is_sso_role}"
        )

        # Priority order: static credentials > profile > role ARN > web identity > default
        if static_keys_present:
            logger.info(
                "Creating boto3 session with static AWS credentials for FileService."
            )
            return boto3.Session(
                aws_access_key_id=app_config.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=app_config.AWS_SECRET_ACCESS_KEY,
                aws_session_token=app_config.AWS_SESSION_TOKEN,
                region_name=self.AWS_REGION,
            )
        elif profile_present and is_sso_role:
            logger.info(
                f"Creating boto3 session with AWS SSO profile for FileService: {self.AWS_PROFILE}"
            )
            return boto3.Session(
                profile_name=self.AWS_PROFILE, region_name=self.AWS_REGION
            )
        elif profile_present:
            logger.info(
                f"Creating boto3 session with profile for FileService: {self.AWS_PROFILE}"
            )
            return boto3.Session(
                profile_name=self.AWS_PROFILE, region_name=self.AWS_REGION
            )
        elif role_arn_present:
            logger.info(
                f"Creating boto3 session with role assumption for FileService: {self.AWS_ROLE_ARN}"
            )
            return self._create_assume_role_session()
        elif web_identity_present:
            logger.info(
                f"Creating boto3 session with web identity token for FileService: {self.AWS_WEB_IDENTITY_TOKEN_FILE}"
            )
            return self._create_web_identity_session()
        else:
            logger.info(
                f"Creating boto3 session with default credentials for FileService and region: {self.AWS_REGION}"
            )
            return boto3.Session(region_name=self.AWS_REGION)

    def _create_assume_role_session(self) -> boto3.Session:
        """Create a session by assuming a role."""
        try:
            base_session = boto3.Session(region_name=self.AWS_REGION)
            sts_client = base_session.client("sts")

            # Test base credentials
            try:
                sts_client.get_caller_identity()
                logger.info(
                    "Base credentials validated for FileService role assumption."
                )
            except (NoCredentialsError, PartialCredentialsError) as e:
                logger.error(
                    f"No base credentials available for FileService role assumption: {e}"
                )
                raise ConfigurationError(
                    f"FileService role assumption requires base AWS credentials: {e}"
                )

            # Prepare assume role parameters
            assume_role_params = {
                "RoleArn": self.AWS_ROLE_ARN,
                "RoleSessionName": self.AWS_ROLE_SESSION_NAME,
                "DurationSeconds": app_config.AWS_ROLE_SESSION_DURATION,
            }

            if self.AWS_EXTERNAL_ID:
                assume_role_params["ExternalId"] = self.AWS_EXTERNAL_ID

            # Assume the role
            response = sts_client.assume_role(**assume_role_params)
            credentials = response["Credentials"]

            logger.info(
                f"Successfully assumed role for FileService: {self.AWS_ROLE_ARN}"
            )

            return boto3.Session(
                aws_access_key_id=credentials["AccessKeyId"],
                aws_secret_access_key=credentials["SecretAccessKey"],
                aws_session_token=credentials["SessionToken"],
                region_name=self.AWS_REGION,
            )

        except ConfigurationError:
            raise
        except Exception as e:
            logger.error(f"FileService role assumption failed: {e}")
            raise ConfigurationError(f"FileService role assumption error: {e}")

    def _create_web_identity_session(self) -> boto3.Session:
        """Create a session using web identity token."""
        try:
            original_env = {}

            env_vars = {
                "AWS_WEB_IDENTITY_TOKEN_FILE": self.AWS_WEB_IDENTITY_TOKEN_FILE,
                "AWS_ROLE_ARN": self.AWS_ROLE_ARN or "",
                "AWS_ROLE_SESSION_NAME": self.AWS_ROLE_SESSION_NAME,
            }

            if not self.AWS_WEB_IDENTITY_TOKEN_FILE:
                raise ConfigurationError(
                    "AWS_WEB_IDENTITY_TOKEN_FILE is required for FileService web identity authentication"
                )

            if not os.path.exists(self.AWS_WEB_IDENTITY_TOKEN_FILE):
                raise ConfigurationError(
                    f"FileService web identity token file not found: {self.AWS_WEB_IDENTITY_TOKEN_FILE}"
                )

            # Set environment variables temporarily
            for key, value in env_vars.items():
                if value:
                    original_env[key] = os.environ.get(key)
                    os.environ[key] = value

            try:
                session = boto3.Session(region_name=self.AWS_REGION)
                sts_client = session.client("sts")
                caller_identity = sts_client.get_caller_identity()
                logger.info(
                    f"Successfully initialized FileService session with web identity token. Account: {caller_identity.get('Account')}"
                )
                return session
            finally:
                # Restore original environment
                for key in env_vars:
                    if original_env.get(key) is not None:
                        os.environ[key] = original_env[key]
                    elif key in os.environ:
                        del os.environ[key]

        except ConfigurationError:
            raise
        except Exception as e:
            logger.error(f"FileService web identity authentication failed: {e}")
            raise ConfigurationError(
                f"FileService web identity authentication error: {e}"
            )

    def generate_file_id(self) -> str:
        """Generate a unique file ID in OpenAI format."""
        return f"file-{uuid.uuid4().hex}"

    def generate_s3_key(self, file_id: str, original_filename: str) -> str:
        """Generate a unique S3 key for file storage."""
        # Use a format like: files/{file_id}-{filename}
        return f"files/{file_id}-{original_filename}"

    async def upload_file(
        self,
        file_content: bytes,
        filename: str,
        purpose: str,
        content_type: str = "application/octet-stream",
    ) -> FileMetadata:
        """
        Upload a file to S3 and return metadata.

        Args:
            file_content: The file content as bytes
            filename: Original filename
            purpose: Purpose of the file (e.g., "fine-tune", "assistants")
            content_type: MIME type of the file

        Returns:
            FileMetadata: Metadata about the uploaded file

        Raises:
            ConfigurationError: If S3 bucket is not configured
            ServiceApiError: If S3 upload fails
        """
        if not self.s3_bucket:
            raise ConfigurationError(
                "S3_FILES_BUCKET is not configured. Cannot upload files."
            )

        # Generate unique identifiers
        file_id = self.generate_file_id()
        s3_key = self.generate_s3_key(file_id, filename)

        try:
            # Upload to S3
            logger.info(
                f"Uploading file {filename} to S3 bucket {self.s3_bucket} with key {s3_key}"
            )

            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=s3_key,
                Body=file_content,
                ContentType=content_type,
                Metadata={
                    "file_id": file_id,
                    "original_filename": filename,
                    "purpose": purpose,
                    "uploaded_by": "open-bedrock-server",
                },
            )

            logger.info(f"Successfully uploaded file {filename} with ID {file_id}")

            # Create and return metadata
            metadata = FileMetadata(
                file_id=file_id,
                filename=filename,
                purpose=purpose,
                s3_bucket=self.s3_bucket,
                s3_key=s3_key,
                content_type=content_type,
                file_size=len(file_content),
                created_at=int(__import__("time").time()),
            )

            return metadata

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            error_message = e.response.get("Error", {}).get("Message", str(e))

            logger.error(
                f"S3 upload failed for file {filename}: {error_code} - {error_message}"
            )

            if error_code == "NoSuchBucket":
                raise ServiceApiError(f"S3 bucket '{self.s3_bucket}' does not exist")
            elif error_code == "AccessDenied":
                raise ServiceApiError(
                    f"Access denied to S3 bucket '{self.s3_bucket}'. Check IAM permissions."
                )
            else:
                raise ServiceApiError(f"S3 upload failed: {error_message}")

        except Exception as e:
            logger.error(f"Unexpected error during file upload: {e}")
            raise ServiceApiError(f"File upload failed: {str(e)}")

    def get_file_url(self, s3_key: str, expires_in: int = 3600) -> str:
        """Generate a presigned URL for file access."""
        try:
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.s3_bucket, "Key": s3_key},
                ExpiresIn=expires_in,
            )
            return url
        except Exception as e:
            logger.error(f"Failed to generate presigned URL for {s3_key}: {e}")
            raise ServiceApiError(f"Failed to generate file access URL: {str(e)}")

    def delete_file(self, s3_key: str) -> bool:
        """Delete a file from S3."""
        try:
            self.s3_client.delete_object(Bucket=self.s3_bucket, Key=s3_key)
            logger.info(f"Successfully deleted file {s3_key} from S3")
            return True
        except Exception as e:
            logger.error(f"Failed to delete file {s3_key} from S3: {e}")
            return False

    async def get_file_metadata(self, file_id: str) -> FileMetadata | None:
        """
        Retrieve metadata for a file by its ID.

        Args:
            file_id: The file ID to retrieve

        Returns:
            FileMetadata if found, None otherwise

        Raises:
            ServiceApiError: If S3 operation fails
        """
        if not self.s3_bucket:
            raise ConfigurationError(
                "S3_FILES_BUCKET is not configured. Cannot retrieve files."
            )

        try:
            # List objects with the file_id prefix to find the file
            response = self.s3_client.list_objects_v2(
                Bucket=self.s3_bucket, Prefix=f"files/{file_id}-"
            )

            if "Contents" not in response or not response["Contents"]:
                logger.info(f"File {file_id} not found in S3")
                return None

            # Get the first (and should be only) matching file
            s3_object = response["Contents"][0]
            s3_key = s3_object["Key"]

            # Get detailed metadata
            head_response = self.s3_client.head_object(
                Bucket=self.s3_bucket, Key=s3_key
            )

            # Extract original filename from S3 key or metadata
            original_filename = head_response.get("Metadata", {}).get(
                "original_filename"
            )
            if not original_filename:
                # Extract from S3 key format: files/{file_id}-{filename}
                original_filename = s3_key.split("-", 1)[1] if "-" in s3_key else s3_key

            metadata = FileMetadata(
                file_id=file_id,
                filename=original_filename,
                purpose=head_response.get("Metadata", {}).get("purpose", "unknown"),
                s3_bucket=self.s3_bucket,
                s3_key=s3_key,
                content_type=head_response.get(
                    "ContentType", "application/octet-stream"
                ),
                file_size=head_response.get("ContentLength", 0),
                created_at=int(head_response.get("LastModified").timestamp())
                if head_response.get("LastModified")
                else 0,
            )

            return metadata

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code == "NoSuchKey" or error_code == "404":
                return None
            logger.error(f"Failed to retrieve file metadata for {file_id}: {e}")
            raise ServiceApiError(f"Failed to retrieve file metadata: {str(e)}")
        except Exception as e:
            logger.error(
                f"Unexpected error retrieving file metadata for {file_id}: {e}"
            )
            raise ServiceApiError(f"Failed to retrieve file metadata: {str(e)}")

    async def get_file_content(self, file_id: str) -> bytes | None:
        """
        Retrieve the content of a file by its ID.

        Args:
            file_id: The file ID to retrieve

        Returns:
            File content as bytes if found, None otherwise

        Raises:
            ServiceApiError: If S3 operation fails
        """
        if not self.s3_bucket:
            raise ConfigurationError(
                "S3_FILES_BUCKET is not configured. Cannot retrieve files."
            )

        try:
            # First get the metadata to find the S3 key
            metadata = await self.get_file_metadata(file_id)
            if not metadata:
                return None

            # Download the file content
            response = self.s3_client.get_object(
                Bucket=self.s3_bucket, Key=metadata.s3_key
            )

            return response["Body"].read()

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code == "NoSuchKey" or error_code == "404":
                return None
            logger.error(f"Failed to retrieve file content for {file_id}: {e}")
            raise ServiceApiError(f"Failed to retrieve file content: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error retrieving file content for {file_id}: {e}")
            raise ServiceApiError(f"Failed to retrieve file content: {str(e)}")

    async def list_files(
        self, purpose: str | None = None, limit: int = 20
    ) -> list[FileMetadata]:
        """
        List files with optional filtering by purpose.

        Args:
            purpose: Optional purpose filter
            limit: Maximum number of files to return

        Returns:
            List of FileMetadata objects

        Raises:
            ServiceApiError: If S3 operation fails
        """
        if not self.s3_bucket:
            raise ConfigurationError(
                "S3_FILES_BUCKET is not configured. Cannot list files."
            )

        try:
            # List all files in the files/ prefix
            response = self.s3_client.list_objects_v2(
                Bucket=self.s3_bucket, Prefix="files/", MaxKeys=limit
            )

            if "Contents" not in response:
                return []

            files = []
            for s3_object in response["Contents"]:
                s3_key = s3_object["Key"]

                # Extract file_id from S3 key format: files/{file_id}-{filename}
                # File IDs start with "file-" so we need to be careful with splitting
                key_without_prefix = s3_key.replace("files/", "")

                # Find the file ID by looking for the pattern "file-XXXXXXXX-"
                # where XXXXXXXX is the unique part of the file ID
                if not key_without_prefix.startswith("file-"):
                    continue  # Skip malformed keys

                # Split after the file ID pattern: file-{unique_id}-{filename}
                # We need to find the second dash after "file-"
                parts = key_without_prefix.split("-")
                if (
                    len(parts) < 3
                ):  # Should have at least: ['file', 'uniqueid', 'filename']
                    continue  # Skip malformed keys

                # Reconstruct file_id as "file-{unique_id}"
                file_id = f"{parts[0]}-{parts[1]}"

                try:
                    # Get detailed metadata
                    head_response = self.s3_client.head_object(
                        Bucket=self.s3_bucket, Key=s3_key
                    )

                    file_purpose = head_response.get("Metadata", {}).get(
                        "purpose", "unknown"
                    )

                    # Apply purpose filter if specified
                    if purpose and file_purpose != purpose:
                        continue

                    # Get original filename from metadata or reconstruct from key
                    original_filename = head_response.get("Metadata", {}).get(
                        "original_filename"
                    )
                    if not original_filename:
                        # Reconstruct filename from remaining parts
                        original_filename = "-".join(parts[2:])

                    metadata = FileMetadata(
                        file_id=file_id,
                        filename=original_filename,
                        purpose=file_purpose,
                        s3_bucket=self.s3_bucket,
                        s3_key=s3_key,
                        content_type=head_response.get(
                            "ContentType", "application/octet-stream"
                        ),
                        file_size=head_response.get("ContentLength", 0),
                        created_at=int(head_response.get("LastModified").timestamp())
                        if head_response.get("LastModified")
                        else 0,
                    )

                    files.append(metadata)

                except Exception as e:
                    logger.warning(f"Failed to get metadata for {s3_key}: {e}")
                    continue

            # Sort by creation time (newest first)
            files.sort(key=lambda x: x.created_at, reverse=True)

            return files

        except Exception as e:
            logger.error(f"Failed to list files: {e}")
            raise ServiceApiError(f"Failed to list files: {str(e)}")

    async def delete_file_by_id(self, file_id: str) -> bool:
        """
        Delete a file by its ID.

        Args:
            file_id: The file ID to delete

        Returns:
            True if deleted successfully, False if not found

        Raises:
            ServiceApiError: If S3 operation fails
        """
        metadata = await self.get_file_metadata(file_id)
        if not metadata:
            return False

        return self.delete_file(metadata.s3_key)


# Global instance
_file_service: FileService | None = None


def get_file_service() -> FileService:
    """Get the global file service instance."""
    global _file_service

    if _file_service is None:
        from ..utils.config_loader import app_config

        _file_service = FileService(
            s3_bucket=app_config.S3_FILES_BUCKET,
            AWS_REGION=app_config.AWS_REGION,
            AWS_PROFILE=app_config.AWS_PROFILE,
            AWS_ROLE_ARN=app_config.AWS_ROLE_ARN,
            AWS_EXTERNAL_ID=app_config.AWS_EXTERNAL_ID,
            AWS_ROLE_SESSION_NAME=app_config.AWS_ROLE_SESSION_NAME,
            AWS_WEB_IDENTITY_TOKEN_FILE=app_config.AWS_WEB_IDENTITY_TOKEN_FILE,
            validate_credentials=True,
        )

    return _file_service
