import logging
import os
from typing import Any

import boto3
from botocore.exceptions import ClientError

from ..core.exceptions import (
    ConfigurationError,
    ServiceApiError,
    ServiceAuthenticationError,
    ServiceRateLimitError,
    ServiceUnavailableError,
)
from ..core.knowledge_base_models import (
    Citation,
    CreateDataSourceRequest,
    CreateKnowledgeBaseRequest,
    DataSourceInfo,
    KnowledgeBaseInfo,
    KnowledgeBaseQueryRequest,
    KnowledgeBaseQueryResponse,
    KnowledgeBaseStatus,
    ListKnowledgeBasesResponse,
    RetrievalResult,
    RetrieveAndGenerateRequest,
    RetrieveAndGenerateResponse,
    SyncDataSourceRequest,
    SyncDataSourceResponse,
)

logger = logging.getLogger(__name__)


class KnowledgeBaseService:
    """
    Service for managing AWS Bedrock Knowledge Bases

    Handles:
    - Knowledge Base creation, management, and deletion
    - Data source management and synchronization
    - Retrieval operations (retrieve-only and retrieve-and-generate)
    - Integration with existing AWS authentication patterns
    """

    def __init__(
        self,
        AWS_REGION: str | None = None,
        AWS_PROFILE: str | None = None,
        AWS_ROLE_ARN: str | None = None,
        AWS_EXTERNAL_ID: str | None = None,
        AWS_ROLE_SESSION_NAME: str | None = None,
        AWS_WEB_IDENTITY_TOKEN_FILE: str | None = None,
        validate_credentials: bool = True,
        **kwargs,
    ):
        self.AWS_REGION = AWS_REGION or os.getenv("AWS_REGION")
        self.AWS_PROFILE = AWS_PROFILE or os.getenv("AWS_PROFILE")
        self.AWS_ROLE_ARN = AWS_ROLE_ARN or os.getenv("AWS_ROLE_ARN")
        self.AWS_EXTERNAL_ID = AWS_EXTERNAL_ID or os.getenv("AWS_EXTERNAL_ID")
        self.AWS_ROLE_SESSION_NAME = AWS_ROLE_SESSION_NAME or os.getenv(
            "AWS_ROLE_SESSION_NAME", "kb-service-session"
        )
        self.AWS_WEB_IDENTITY_TOKEN_FILE = AWS_WEB_IDENTITY_TOKEN_FILE or os.getenv(
            "AWS_WEB_IDENTITY_TOKEN_FILE"
        )
        self.validate_credentials = validate_credentials

        if not self.AWS_REGION:
            logger.warning(
                "AWS_REGION not provided. Knowledge Base operations may fail."
            )

        try:
            session = self._create_aws_session()

            # Initialize Bedrock Agent clients for Knowledge Base operations
            self.bedrock_agent_client = session.client("bedrock-agent")
            self.bedrock_agent_runtime_client = session.client("bedrock-agent-runtime")

            # Also keep bedrock-runtime for model operations
            self.bedrock_runtime_client = session.client("bedrock-runtime")

            logger.info("KnowledgeBaseService initialized with Bedrock Agent clients.")

        except Exception as e:
            logger.error(f"Failed to initialize KnowledgeBaseService: {e}")
            raise ConfigurationError(
                f"Failed to initialize Knowledge Base service: {e}"
            )

    def _create_aws_session(self) -> boto3.Session:
        """Create AWS session using existing authentication patterns from BedrockService"""
        static_keys_present = bool(
            os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY")
        )
        profile_present = bool(self.AWS_PROFILE)
        role_arn_present = bool(self.AWS_ROLE_ARN)
        web_identity_present = bool(self.AWS_WEB_IDENTITY_TOKEN_FILE)

        is_sso_role = role_arn_present and "AWSReservedSSO" in self.AWS_ROLE_ARN

        logger.info(
            f"KB Service auth methods - Static keys: {static_keys_present}, "
            f"Profile: {profile_present}, Role ARN: {role_arn_present}, SSO Role: {is_sso_role}"
        )

        if static_keys_present:
            logger.info("Creating KB session with static AWS credentials.")
            return boto3.Session(
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                aws_session_token=os.getenv("AWS_SESSION_TOKEN"),
                region_name=self.AWS_REGION,
            )
        elif profile_present and is_sso_role:
            logger.info(f"Creating KB session with AWS SSO profile: {self.AWS_PROFILE}")
            return boto3.Session(
                profile_name=self.AWS_PROFILE, region_name=self.AWS_REGION
            )
        elif profile_present:
            logger.info(f"Creating KB session with profile: {self.AWS_PROFILE}")
            return boto3.Session(
                profile_name=self.AWS_PROFILE, region_name=self.AWS_REGION
            )
        elif role_arn_present and not is_sso_role:
            logger.info(
                f"Creating KB session with role assumption: {self.AWS_ROLE_ARN}"
            )
            return self._create_assume_role_session()
        elif web_identity_present:
            logger.info("Creating KB session with web identity token.")
            return self._create_web_identity_session()
        else:
            logger.info("Creating KB session with default AWS credentials.")
            return boto3.Session(region_name=self.AWS_REGION)

    def _create_assume_role_session(self) -> boto3.Session:
        """Create session with role assumption"""
        try:
            base_session = boto3.Session(
                profile_name=self.AWS_PROFILE, region_name=self.AWS_REGION
            )
            sts_client = base_session.client("sts")

            assume_role_kwargs = {
                "RoleArn": self.AWS_ROLE_ARN,
                "RoleSessionName": self.AWS_ROLE_SESSION_NAME,
            }

            if self.AWS_EXTERNAL_ID:
                assume_role_kwargs["ExternalId"] = self.AWS_EXTERNAL_ID

            response = sts_client.assume_role(**assume_role_kwargs)
            credentials = response["Credentials"]

            return boto3.Session(
                aws_access_key_id=credentials["AccessKeyId"],
                aws_secret_access_key=credentials["SecretAccessKey"],
                aws_session_token=credentials["SessionToken"],
                region_name=self.AWS_REGION,
            )
        except Exception as e:
            logger.error(f"Failed to assume role {self.AWS_ROLE_ARN}: {e}")
            raise ConfigurationError(f"Role assumption failed: {e}")

    def _create_web_identity_session(self) -> boto3.Session:
        """Create session with web identity token"""
        try:
            base_session = boto3.Session(region_name=self.AWS_REGION)
            sts_client = base_session.client("sts")

            with open(self.AWS_WEB_IDENTITY_TOKEN_FILE) as token_file:
                token = token_file.read().strip()

            response = sts_client.assume_role_with_web_identity(
                RoleArn=self.AWS_ROLE_ARN,
                RoleSessionName=self.AWS_ROLE_SESSION_NAME,
                WebIdentityToken=token,
            )
            credentials = response["Credentials"]

            return boto3.Session(
                aws_access_key_id=credentials["AccessKeyId"],
                aws_secret_access_key=credentials["SecretAccessKey"],
                aws_session_token=credentials["SessionToken"],
                region_name=self.AWS_REGION,
            )
        except Exception as e:
            logger.error(f"Failed to assume role with web identity: {e}")
            raise ConfigurationError(f"Web identity authentication failed: {e}")

    def _handle_bedrock_error(self, e: ClientError, operation: str) -> None:
        """Handle Bedrock API errors consistently"""
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_message = e.response.get("Error", {}).get("Message", str(e))

        logger.error(
            f"Bedrock Knowledge Base {operation} error - Code: {error_code}, Message: {error_message}"
        )

        if error_code in [
            "UnauthorizedOperation",
            "AccessDenied",
            "InvalidUserID.NotFound",
        ]:
            raise ServiceAuthenticationError(
                f"Authentication failed for {operation}: {error_message}"
            )
        elif error_code in ["ResourceNotFoundException", "ValidationException"]:
            raise ServiceApiError(f"Invalid request for {operation}: {error_message}")
        elif error_code in ["ThrottlingException", "TooManyRequestsException"]:
            raise ServiceRateLimitError(
                f"Rate limit exceeded for {operation}: {error_message}"
            )
        elif error_code in ["ServiceUnavailableException", "InternalServerException"]:
            raise ServiceUnavailableError(
                f"Bedrock service unavailable for {operation}: {error_message}"
            )
        else:
            raise ServiceApiError(f"Bedrock {operation} failed: {error_message}")

    # Knowledge Base Management Methods
    async def create_knowledge_base(
        self, request: CreateKnowledgeBaseRequest
    ) -> KnowledgeBaseInfo:
        """Create a new knowledge base"""
        try:
            logger.info(f"Creating knowledge base: {request.name}")

            create_request = {
                "name": request.name,
                "roleArn": request.roleArn,
                "knowledgeBaseConfiguration": {
                    "type": request.knowledgeBaseConfiguration.type,
                    "vectorKnowledgeBaseConfiguration": {
                        "embeddingModelArn": request.knowledgeBaseConfiguration.vectorKnowledgeBaseConfiguration.embeddingModelArn
                    },
                },
            }

            if request.description:
                create_request["description"] = request.description

            if request.storageConfiguration:
                create_request["storageConfiguration"] = {
                    "type": request.storageConfiguration.type.value
                }
                if request.storageConfiguration.opensearchServerlessConfiguration:
                    create_request["storageConfiguration"][
                        "opensearchServerlessConfiguration"
                    ] = {
                        "collectionArn": request.storageConfiguration.opensearchServerlessConfiguration.collectionArn,
                        "vectorIndexName": request.storageConfiguration.opensearchServerlessConfiguration.vectorIndexName,
                        "fieldMapping": {
                            "textField": request.storageConfiguration.opensearchServerlessConfiguration.fieldMapping.textField,
                            "metadataField": request.storageConfiguration.opensearchServerlessConfiguration.fieldMapping.metadataField,
                            "vectorField": request.storageConfiguration.opensearchServerlessConfiguration.fieldMapping.vectorField,
                        },
                    }

            if request.tags:
                create_request["tags"] = request.tags

            response = self.bedrock_agent_client.create_knowledge_base(**create_request)
            kb_data = response["knowledgeBase"]

            return KnowledgeBaseInfo(
                knowledgeBaseId=kb_data["knowledgeBaseId"],
                name=kb_data["name"],
                description=kb_data.get("description"),
                knowledgeBaseArn=kb_data["knowledgeBaseArn"],
                status=KnowledgeBaseStatus(kb_data["status"]),
                roleArn=kb_data["roleArn"],
                knowledgeBaseConfiguration=request.knowledgeBaseConfiguration,
                storageConfiguration=request.storageConfiguration,
                failureReasons=kb_data.get("failureReasons"),
                createdAt=kb_data["createdAt"],
                updatedAt=kb_data["updatedAt"],
            )

        except ClientError as e:
            self._handle_bedrock_error(e, "create_knowledge_base")
        except Exception as e:
            logger.error(f"Unexpected error creating knowledge base: {e}")
            raise ServiceApiError(f"Failed to create knowledge base: {e}")

    async def get_knowledge_base(self, knowledge_base_id: str) -> KnowledgeBaseInfo:
        """Get knowledge base details"""
        try:
            logger.debug(f"Getting knowledge base: {knowledge_base_id}")

            response = self.bedrock_agent_client.get_knowledge_base(
                knowledgeBaseId=knowledge_base_id
            )
            kb_data = response["knowledgeBase"]

            return KnowledgeBaseInfo(
                knowledgeBaseId=kb_data["knowledgeBaseId"],
                name=kb_data["name"],
                description=kb_data.get("description"),
                knowledgeBaseArn=kb_data["knowledgeBaseArn"],
                status=KnowledgeBaseStatus(kb_data["status"]),
                roleArn=kb_data["roleArn"],
                knowledgeBaseConfiguration=kb_data["knowledgeBaseConfiguration"],
                storageConfiguration=kb_data.get("storageConfiguration"),
                failureReasons=kb_data.get("failureReasons"),
                createdAt=kb_data["createdAt"],
                updatedAt=kb_data["updatedAt"],
            )

        except ClientError as e:
            self._handle_bedrock_error(e, "get_knowledge_base")
        except Exception as e:
            logger.error(f"Unexpected error getting knowledge base: {e}")
            raise ServiceApiError(f"Failed to get knowledge base: {e}")

    async def list_knowledge_bases(
        self, max_results: int = 10, next_token: str | None = None
    ) -> ListKnowledgeBasesResponse:
        """List knowledge bases"""
        try:
            logger.debug("Listing knowledge bases")

            request_params = {"maxResults": max_results}
            if next_token:
                request_params["nextToken"] = next_token

            response = self.bedrock_agent_client.list_knowledge_bases(**request_params)

            kb_summaries = []
            for kb in response.get("knowledgeBaseSummaries", []):
                kb_summaries.append(
                    KnowledgeBaseInfo(
                        knowledgeBaseId=kb["knowledgeBaseId"],
                        name=kb["name"],
                        description=kb.get("description"),
                        knowledgeBaseArn=kb.get("knowledgeBaseArn", ""),
                        status=KnowledgeBaseStatus(kb["status"]),
                        roleArn=kb.get("roleArn", ""),
                        knowledgeBaseConfiguration=kb.get(
                            "knowledgeBaseConfiguration", {}
                        ),
                        createdAt=kb["updatedAt"],  # Using updatedAt as fallback
                        updatedAt=kb["updatedAt"],
                    )
                )

            return ListKnowledgeBasesResponse(
                knowledgeBaseSummaries=kb_summaries, nextToken=response.get("nextToken")
            )

        except ClientError as e:
            self._handle_bedrock_error(e, "list_knowledge_bases")
        except Exception as e:
            logger.error(f"Unexpected error listing knowledge bases: {e}")
            raise ServiceApiError(f"Failed to list knowledge bases: {e}")

    async def delete_knowledge_base(self, knowledge_base_id: str) -> dict[str, Any]:
        """Delete a knowledge base"""
        try:
            logger.info(f"Deleting knowledge base: {knowledge_base_id}")

            response = self.bedrock_agent_client.delete_knowledge_base(
                knowledgeBaseId=knowledge_base_id
            )

            return {
                "knowledgeBaseId": response["knowledgeBaseId"],
                "status": response["status"],
            }

        except ClientError as e:
            self._handle_bedrock_error(e, "delete_knowledge_base")
        except Exception as e:
            logger.error(f"Unexpected error deleting knowledge base: {e}")
            raise ServiceApiError(f"Failed to delete knowledge base: {e}")

    # Query and Retrieval Methods
    async def retrieve(
        self, request: KnowledgeBaseQueryRequest
    ) -> KnowledgeBaseQueryResponse:
        """Retrieve information from knowledge base"""
        try:
            logger.debug(
                f"Retrieving from KB {request.knowledgeBaseId}: {request.query}"
            )

            retrieve_request = {
                "knowledgeBaseId": request.knowledgeBaseId,
                "retrievalQuery": {"text": request.query},
            }

            if request.retrievalConfiguration:
                retrieve_request["retrievalConfiguration"] = (
                    request.retrievalConfiguration
                )

            response = self.bedrock_agent_runtime_client.retrieve(**retrieve_request)

            retrieval_results = []
            for result in response.get("retrievalResults", []):
                content = result.get("content", {})
                text_content = content.get("text", "")

                retrieval_results.append(
                    RetrievalResult(
                        content=text_content,
                        metadata=result.get("metadata", {}),
                        location=result.get("location", {}),
                        score=result.get("score"),
                    )
                )

            return KnowledgeBaseQueryResponse(
                retrievalResults=retrieval_results, nextToken=response.get("nextToken")
            )

        except ClientError as e:
            self._handle_bedrock_error(e, "retrieve")
        except Exception as e:
            logger.error(f"Unexpected error retrieving from knowledge base: {e}")
            raise ServiceApiError(f"Failed to retrieve from knowledge base: {e}")

    async def retrieve_and_generate(
        self, request: RetrieveAndGenerateRequest
    ) -> RetrieveAndGenerateResponse:
        """Retrieve and generate response from knowledge base"""
        try:
            logger.debug(
                f"Retrieve and generate from KB {request.knowledgeBaseId}: {request.query}"
            )

            retrieve_generate_request = {
                "input": {"text": request.query},
                "retrieveAndGenerateConfiguration": {
                    "type": "KNOWLEDGE_BASE",
                    "knowledgeBaseConfiguration": {
                        "knowledgeBaseId": request.knowledgeBaseId,
                        "modelArn": request.modelArn,
                    },
                },
            }

            if request.retrievalConfiguration:
                retrieve_generate_request["retrieveAndGenerateConfiguration"][
                    "knowledgeBaseConfiguration"
                ]["retrievalConfiguration"] = request.retrievalConfiguration

            if request.generationConfiguration:
                retrieve_generate_request["retrieveAndGenerateConfiguration"][
                    "knowledgeBaseConfiguration"
                ]["generationConfiguration"] = request.generationConfiguration

            if request.sessionId:
                retrieve_generate_request["sessionId"] = request.sessionId

            response = self.bedrock_agent_runtime_client.retrieve_and_generate(
                **retrieve_generate_request
            )

            citations = []
            for citation in response.get("citations", []):
                citations.append(
                    Citation(
                        generatedResponsePart=citation.get("generatedResponsePart", {}),
                        retrievedReferences=citation.get("retrievedReferences", []),
                    )
                )

            return RetrieveAndGenerateResponse(
                output=response["output"]["text"],
                citations=citations,
                sessionId=response.get("sessionId"),
                guardrailAction=response.get("guardrailAction"),
            )

        except ClientError as e:
            self._handle_bedrock_error(e, "retrieve_and_generate")
        except Exception as e:
            logger.error(f"Unexpected error in retrieve and generate: {e}")
            raise ServiceApiError(f"Failed to retrieve and generate: {e}")

    # Data Source Management Methods
    async def create_data_source(
        self, request: CreateDataSourceRequest
    ) -> DataSourceInfo:
        """Create a data source for a knowledge base"""
        try:
            logger.info(
                f"Creating data source: {request.name} for KB: {request.knowledgeBaseId}"
            )

            create_request = {
                "knowledgeBaseId": request.knowledgeBaseId,
                "name": request.name,
                "dataSourceConfiguration": {
                    "type": request.dataSourceConfiguration.type.value
                },
            }

            if request.description:
                create_request["description"] = request.description

            if request.dataSourceConfiguration.s3Configuration:
                create_request["dataSourceConfiguration"]["s3Configuration"] = {
                    "bucketArn": request.dataSourceConfiguration.s3Configuration.bucketArn
                }
                if request.dataSourceConfiguration.s3Configuration.inclusionPrefixes:
                    create_request["dataSourceConfiguration"]["s3Configuration"][
                        "inclusionPrefixes"
                    ] = request.dataSourceConfiguration.s3Configuration.inclusionPrefixes
                if request.dataSourceConfiguration.s3Configuration.exclusionPrefixes:
                    create_request["dataSourceConfiguration"]["s3Configuration"][
                        "exclusionPrefixes"
                    ] = request.dataSourceConfiguration.s3Configuration.exclusionPrefixes

            if request.vectorIngestionConfiguration:
                create_request["vectorIngestionConfiguration"] = (
                    request.vectorIngestionConfiguration.dict(exclude_none=True)
                )

            response = self.bedrock_agent_client.create_data_source(**create_request)
            ds_data = response["dataSource"]

            return DataSourceInfo(
                dataSourceId=ds_data["dataSourceId"],
                knowledgeBaseId=ds_data["knowledgeBaseId"],
                name=ds_data["name"],
                description=ds_data.get("description"),
                dataSourceConfiguration=request.dataSourceConfiguration,
                status=ds_data["status"],
                createdAt=ds_data["createdAt"],
                updatedAt=ds_data["updatedAt"],
            )

        except ClientError as e:
            self._handle_bedrock_error(e, "create_data_source")
        except Exception as e:
            logger.error(f"Unexpected error creating data source: {e}")
            raise ServiceApiError(f"Failed to create data source: {e}")

    async def sync_data_source(
        self, request: SyncDataSourceRequest
    ) -> SyncDataSourceResponse:
        """Sync a data source"""
        try:
            logger.info(
                f"Syncing data source: {request.dataSourceId} for KB: {request.knowledgeBaseId}"
            )

            response = self.bedrock_agent_client.start_ingestion_job(
                knowledgeBaseId=request.knowledgeBaseId,
                dataSourceId=request.dataSourceId,
            )

            return SyncDataSourceResponse(
                executionId=response["ingestionJob"]["ingestionJobId"]
            )

        except ClientError as e:
            self._handle_bedrock_error(e, "sync_data_source")
        except Exception as e:
            logger.error(f"Unexpected error syncing data source: {e}")
            raise ServiceApiError(f"Failed to sync data source: {e}")


# Service instance creation function following existing patterns
def get_knowledge_base_service(**kwargs) -> KnowledgeBaseService:
    """Get Knowledge Base service instance"""
    return KnowledgeBaseService(**kwargs)
