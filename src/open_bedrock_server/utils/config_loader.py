import logging
import os
from pathlib import Path
from typing import Dict, Optional

from dotenv import load_dotenv
import boto3
from botocore.exceptions import NoCredentialsError

logger = logging.getLogger(__name__)

# Load .env file from the project root.
# Adjust the path if your .env file is located elsewhere relative to this script.
# Assuming this script is in src/open_bedrock_server/utils, .env is two levels up.
dotenv_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env")

if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
    logger.info(f".env file loaded from {dotenv_path}")
elif os.path.exists(".env"):
    load_dotenv()
    logger.info(".env file loaded from current working directory")
else:
    logger.warning(".env file not found. Relying solely on environment variables.")


class AppConfig:
    """Loads application configuration from .env file and environment variables."""

    def __init__(self):
        # Try loading from .env in project root (common for local dev)
        project_root_dotenv = os.path.join(
            os.path.dirname(__file__), "..", "..", ".env"
        )
        # Try loading from .env in current working directory (flexible for different run locations)
        cwd_dotenv = os.path.join(os.getcwd(), ".env")

        loaded_from = None
        if os.path.exists(project_root_dotenv):
            load_dotenv(dotenv_path=project_root_dotenv, override=True)
            loaded_from = project_root_dotenv
        elif os.path.exists(cwd_dotenv):
            load_dotenv(dotenv_path=cwd_dotenv, override=True)
            loaded_from = cwd_dotenv
        else:
            # If no .env file found in typical locations, load_dotenv will try to find .env in CWD or project root by default.
            # We call it here to ensure environment variables can still be picked up even if .env is elsewhere or not used.
            load_dotenv(override=True)
            logger.info(
                "No .env file found in project root or CWD. Relying on existing environment variables."
            )

        if loaded_from:
            logger.info(f"Loaded environment variables from: {loaded_from}")

        # OpenAI Configuration
        self.OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
        self.OPENAI_ORG_ID: str | None = os.getenv("OPENAI_ORG_ID")  # Optional

        # AWS Bedrock Configuration
        self.AWS_ACCESS_KEY_ID: str | None = os.getenv("AWS_ACCESS_KEY_ID")
        self.AWS_SECRET_ACCESS_KEY: str | None = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.AWS_SESSION_TOKEN: str | None = os.getenv(
            "AWS_SESSION_TOKEN"
        )  # For temporary credentials
        self.AWS_REGION: str | None = os.getenv("AWS_REGION")
        self.AWS_PROFILE: str | None = os.getenv(
            "AWS_PROFILE"
        )  # New: for profile-based auth

        # Enhanced AWS Role Support
        self.AWS_ROLE_ARN: str | None = os.getenv("AWS_ROLE_ARN")  # For assume role
        self.AWS_EXTERNAL_ID: str | None = os.getenv(
            "AWS_EXTERNAL_ID"
        )  # For assume role with external ID
        self.AWS_ROLE_SESSION_NAME: str | None = os.getenv(
            "AWS_ROLE_SESSION_NAME", "bedrock-server-session"
        )  # Session name for assume role
        self.AWS_WEB_IDENTITY_TOKEN_FILE: str | None = os.getenv(
            "AWS_WEB_IDENTITY_TOKEN_FILE"
        )  # For OIDC/web identity
        self.AWS_ROLE_SESSION_DURATION: int = int(
            os.getenv("AWS_ROLE_SESSION_DURATION", "3600")
        )  # Session duration in seconds

        # S3 Configuration for File Storage
        self.S3_FILES_BUCKET: str | None = os.getenv(
            "S3_FILES_BUCKET"
        )  # S3 bucket for file uploads

        # Application Configuration
        self.LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

        # Default Model Parameters
        self.DEFAULT_MAX_TOKENS_OPENAI: int = int(
            os.getenv("DEFAULT_MAX_TOKENS_OPENAI", "1024")
        )
        self.DEFAULT_TEMPERATURE_OPENAI: float = float(
            os.getenv("DEFAULT_TEMPERATURE_OPENAI", "0.7")
        )

        self.DEFAULT_MAX_TOKENS_CLAUDE: int = int(
            os.getenv("DEFAULT_MAX_TOKENS_CLAUDE", "2048")
        )  # Increased for Claude
        self.DEFAULT_TEMPERATURE_CLAUDE: float = float(
            os.getenv("DEFAULT_TEMPERATURE_CLAUDE", "0.7")
        )

        self.DEFAULT_MAX_TOKENS_TITAN: int = int(
            os.getenv("DEFAULT_MAX_TOKENS_TITAN", "512")
        )  # Titan usually has smaller default
        self.DEFAULT_TEMPERATURE_TITAN: float = float(
            os.getenv("DEFAULT_TEMPERATURE_TITAN", "0.7")
        )

        # Add more model families as needed
        self.DEFAULT_MAX_TOKENS_AI21: int = int(
            os.getenv("DEFAULT_MAX_TOKENS_AI21", "2048")
        )
        self.DEFAULT_TEMPERATURE_AI21: float = float(
            os.getenv("DEFAULT_TEMPERATURE_AI21", "0.7")
        )

        self.DEFAULT_MAX_TOKENS_COHERE: int = int(
            os.getenv("DEFAULT_MAX_TOKENS_COHERE", "2048")
        )
        self.DEFAULT_TEMPERATURE_COHERE: float = float(
            os.getenv("DEFAULT_TEMPERATURE_COHERE", "0.7")
        )

        self.DEFAULT_MAX_TOKENS_META: int = int(
            os.getenv("DEFAULT_MAX_TOKENS_META", "2048")
        )
        self.DEFAULT_TEMPERATURE_META: float = float(
            os.getenv("DEFAULT_TEMPERATURE_META", "0.7")
        )

        self.DEFAULT_MAX_TOKENS_MISTRAL: int = int(
            os.getenv("DEFAULT_MAX_TOKENS_MISTRAL", "4096")
        )
        self.DEFAULT_TEMPERATURE_MISTRAL: float = float(
            os.getenv("DEFAULT_TEMPERATURE_MISTRAL", "0.7")
        )

        self.DEFAULT_MAX_TOKENS_STABILITY: int = int(
            os.getenv("DEFAULT_MAX_TOKENS_STABILITY", "2048")
        )
        self.DEFAULT_TEMPERATURE_STABILITY: float = float(
            os.getenv("DEFAULT_TEMPERATURE_STABILITY", "0.7")
        )

        self.DEFAULT_MAX_TOKENS_WRITER: int = int(
            os.getenv("DEFAULT_MAX_TOKENS_WRITER", "2048")
        )
        self.DEFAULT_TEMPERATURE_WRITER: float = float(
            os.getenv("DEFAULT_TEMPERATURE_WRITER", "0.7")
        )

        self.DEFAULT_MAX_TOKENS_NOVA: int = int(
            os.getenv("DEFAULT_MAX_TOKENS_NOVA", "4096")
        )
        self.DEFAULT_TEMPERATURE_NOVA: float = float(
            os.getenv("DEFAULT_TEMPERATURE_NOVA", "0.7")
        )

        # Retry Mechanism Configuration
        self.RETRY_MAX_ATTEMPTS: int = int(os.getenv("RETRY_MAX_ATTEMPTS", "3"))
        self.RETRY_WAIT_MIN_SECONDS: int = int(os.getenv("RETRY_WAIT_MIN_SECONDS", "1"))
        self.RETRY_WAIT_MAX_SECONDS: int = int(
            os.getenv("RETRY_WAIT_MAX_SECONDS", "10")
        )

        self._validate_config()

    def _validate_config(self):
        """Basic validation for essential configurations."""
        if not self.OPENAI_API_KEY:
            logger.warning(
                "OPENAI_API_KEY is not set. OpenAI functionalities will be unavailable."
            )

        aws_static_keys_present = self.AWS_ACCESS_KEY_ID and self.AWS_SECRET_ACCESS_KEY
        aws_profile_present = bool(self.AWS_PROFILE)
        aws_role_arn_present = bool(self.AWS_ROLE_ARN)
        aws_web_identity_present = bool(self.AWS_WEB_IDENTITY_TOKEN_FILE)

        if not (
            aws_static_keys_present
            or aws_profile_present
            or aws_role_arn_present
            or aws_web_identity_present
        ):
            logger.warning(
                "No AWS authentication method configured (static credentials, profile, role ARN, or web identity). "
                "AWS Bedrock functionalities will be unavailable unless the environment is configured for "
                "IAM role instance profile, ECS task role, or other implicit authentication."
            )
        elif (
            sum(
                [
                    bool(aws_static_keys_present),
                    bool(aws_profile_present),
                    bool(aws_role_arn_present),
                    bool(aws_web_identity_present),
                ]
            )
            > 1
        ):
            logger.info(
                "Multiple AWS authentication methods are configured. "
                "Priority order: static credentials > profile > role ARN > web identity > default boto3 chain."
            )

        if aws_role_arn_present and not self.AWS_REGION:
            logger.warning(
                "AWS_ROLE_ARN is set but AWS_REGION is not. Role assumption may fail without a region."
            )

        if (
            aws_static_keys_present
            or aws_profile_present
            or aws_role_arn_present
            or aws_web_identity_present
        ) and not self.AWS_REGION:
            logger.warning(
                "AWS credentials/profile/role are set, but AWS_REGION is not. Bedrock calls may fail or use default region."
            )

        # S3 file storage validation
        if not self.S3_FILES_BUCKET:
            logger.warning(
                "S3_FILES_BUCKET is not set. File upload functionality will be unavailable."
            )

        # If neither OpenAI nor AWS is configured for any use:
        if not self.OPENAI_API_KEY and not (
            aws_static_keys_present
            or aws_profile_present
            or aws_role_arn_present
            or aws_web_identity_present
        ):
            logger.error(
                "CRITICAL: No API keys or AWS configuration found for either OpenAI or AWS Bedrock. "
                "The LLM integration library will not be able to connect to any services."
            )

        log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.LOG_LEVEL not in log_levels:
            logger.warning(
                f"Invalid LOG_LEVEL '{self.LOG_LEVEL}'. Defaulting to INFO. Valid levels are: {log_levels}"
            )
            self.LOG_LEVEL = "INFO"


# Global instance of AppConfig
app_config = AppConfig()

# Example of how to use it elsewhere:
# from .config_loader import app_config
# api_key = app_config.OPENAI_API_KEY

# Assuming this script is in src/open_bedrock_server/utils, .env is two levels up.
DEFAULT_ENV_PATH = Path(__file__).parent.parent.parent.parent / ".env"

def load_environment_config(env_file_path: Optional[str] = None) -> Dict[str, str]:
    """
    Load environment variables from .env file and return as dict.
    
    Args:
        env_file_path: Optional path to .env file. If None, uses default path.
        
    Returns:
        Dict containing all environment variables
    """
    if env_file_path:
        env_path = Path(env_file_path)
    else:
        env_path = DEFAULT_ENV_PATH
    
    if env_path.exists():
        load_dotenv(env_path)
    
    # Return all environment variables as dict
    return dict(os.environ)

def get_aws_session() -> boto3.Session:
    """
    Create and return an AWS session using the configured authentication method.
    
    Returns:
        boto3.Session: Configured AWS session
        
    Raises:
        NoCredentialsError: If no valid AWS credentials are found
    """
    # Try different authentication methods in priority order
    
    # 1. Check for role assumption
    role_arn = os.getenv("AWS_ROLE_ARN")
    if role_arn:
        return _assume_role_session(role_arn)
    
    # 2. Check for web identity token
    web_identity_token_file = os.getenv("AWS_WEB_IDENTITY_TOKEN_FILE")
    if web_identity_token_file:
        return _web_identity_session(web_identity_token_file, role_arn)
    
    # 3. Use AWS profile if specified
    aws_profile = os.getenv("AWS_PROFILE")
    if aws_profile:
        return boto3.Session(profile_name=aws_profile)
    
    # 4. Use static credentials if provided
    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    session_token = os.getenv("AWS_SESSION_TOKEN")
    
    if access_key and secret_key:
        return boto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            aws_session_token=session_token
        )
    
    # 5. Fall back to default credential chain
    return boto3.Session()

def _assume_role_session(role_arn: str) -> boto3.Session:
    """
    Create a session by assuming an IAM role.
    
    Args:
        role_arn: ARN of the role to assume
        
    Returns:
        boto3.Session: Session with assumed role credentials
    """
    # First, get a base session to assume the role
    base_session = _get_base_session_for_role_assumption()
    
    sts_client = base_session.client("sts")
    
    # Prepare assume role parameters
    assume_role_params = {
        "RoleArn": role_arn,
        "RoleSessionName": os.getenv("AWS_ROLE_SESSION_NAME", "bedrock-server-session"),
    }
    
    # Add optional parameters if they exist
    external_id = os.getenv("AWS_EXTERNAL_ID")
    if external_id:
        assume_role_params["ExternalId"] = external_id
    
    session_duration = os.getenv("AWS_ROLE_SESSION_DURATION")
    if session_duration:
        assume_role_params["DurationSeconds"] = int(session_duration)
    
    # Assume the role
    response = sts_client.assume_role(**assume_role_params)
    credentials = response["Credentials"]
    
    # Create new session with assumed role credentials
    return boto3.Session(
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"]
    )

def _get_base_session_for_role_assumption() -> boto3.Session:
    """
    Get base session for role assumption.
    Role assumption requires existing credentials to assume the role.
    """
    # Try AWS profile first
    aws_profile = os.getenv("AWS_PROFILE")
    if aws_profile:
        return boto3.Session(profile_name=aws_profile)
    
    # Try static credentials
    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    session_token = os.getenv("AWS_SESSION_TOKEN")
    
    if access_key and secret_key:
        return boto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            aws_session_token=session_token
        )
    
    # Try default credential chain
    session = boto3.Session()
    try:
        # Test if credentials are available
        session.get_credentials()
        return session
    except NoCredentialsError:
        raise NoCredentialsError(
            "Role assumption requires base AWS credentials. "
            "Please set AWS_PROFILE, AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY, "
            "or configure default AWS credentials."
        )

def _web_identity_session(token_file: str, role_arn: Optional[str]) -> boto3.Session:
    """
    Create a session using web identity token (OIDC/IRSA).
    
    Args:
        token_file: Path to the web identity token file
        role_arn: ARN of the role to assume (required for web identity)
        
    Returns:
        boto3.Session: Session with web identity credentials
    """
    if not role_arn:
        role_arn = os.getenv("AWS_ROLE_ARN")
        if not role_arn:
            raise ValueError(
                "AWS_ROLE_ARN is required when using web identity tokens"
            )
    
    # Create STS client without credentials (will use web identity)
    sts_client = boto3.client("sts")
    
    # Read the token file
    with open(token_file, 'r') as f:
        token = f.read().strip()
    
    # Assume role with web identity
    response = sts_client.assume_role_with_web_identity(
        RoleArn=role_arn,
        RoleSessionName=os.getenv("AWS_ROLE_SESSION_NAME", "bedrock-server-session"),
        WebIdentityToken=token
    )
    
    credentials = response["Credentials"]
    
    return boto3.Session(
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"]
    )

def test_aws_configuration() -> Dict[str, str]:
    """
    Test the current AWS configuration and return status information.
    
    Returns:
        Dict containing configuration test results
    """
    result = {
        "status": "unknown",
        "identity": None,
        "region": None,
        "auth_method": "unknown",
        "error": None
    }
    
    try:
        session = get_aws_session()
        
        # Determine auth method
        if os.getenv("AWS_ROLE_ARN"):
            if os.getenv("AWS_WEB_IDENTITY_TOKEN_FILE"):
                result["auth_method"] = "web_identity"
            else:
                result["auth_method"] = "role_assumption"
        elif os.getenv("AWS_PROFILE"):
            result["auth_method"] = "aws_profile"
        elif os.getenv("AWS_ACCESS_KEY_ID"):
            result["auth_method"] = "static_credentials"
        else:
            result["auth_method"] = "default_chain"
        
        # Test credentials by getting caller identity
        sts = session.client("sts")
        identity = sts.get_caller_identity()
        result["identity"] = identity
        
        # Get region
        region = session.region_name or os.getenv("AWS_REGION", "us-east-1")
        result["region"] = region
        
        result["status"] = "success"
        
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
    
    return result
