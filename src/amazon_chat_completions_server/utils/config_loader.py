import os
import logging
from dotenv import load_dotenv
from ..core.exceptions import ConfigurationError
from typing import Optional, List

logger = logging.getLogger(__name__)

# Load .env file from the project root. 
# Adjust the path if your .env file is located elsewhere relative to this script.
# Assuming this script is in src/amazon_chat_completions_server/utils, .env is two levels up.
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env') 

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
        project_root_dotenv = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
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
            logger.info("No .env file found in project root or CWD. Relying on existing environment variables.")

        if loaded_from:
            logger.info(f"Loaded environment variables from: {loaded_from}")

        # OpenAI Configuration
        self.OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
        self.OPENAI_ORG_ID: Optional[str] = os.getenv("OPENAI_ORG_ID") # Optional

        # AWS Bedrock Configuration
        self.AWS_ACCESS_KEY_ID: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID")
        self.AWS_SECRET_ACCESS_KEY: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.AWS_SESSION_TOKEN: Optional[str] = os.getenv("AWS_SESSION_TOKEN") # For temporary credentials
        self.AWS_REGION: Optional[str] = os.getenv("AWS_REGION")
        self.AWS_PROFILE: Optional[str] = os.getenv("AWS_PROFILE") # New: for profile-based auth

        # Application Configuration
        self.LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

        # Default Model Parameters
        self.DEFAULT_MAX_TOKENS_OPENAI: int = int(os.getenv("DEFAULT_MAX_TOKENS_OPENAI", "1024"))
        self.DEFAULT_TEMPERATURE_OPENAI: float = float(os.getenv("DEFAULT_TEMPERATURE_OPENAI", "0.7"))

        self.DEFAULT_MAX_TOKENS_CLAUDE: int = int(os.getenv("DEFAULT_MAX_TOKENS_CLAUDE", "2048")) # Increased for Claude
        self.DEFAULT_TEMPERATURE_CLAUDE: float = float(os.getenv("DEFAULT_TEMPERATURE_CLAUDE", "0.7"))

        self.DEFAULT_MAX_TOKENS_TITAN: int = int(os.getenv("DEFAULT_MAX_TOKENS_TITAN", "512")) # Titan usually has smaller default
        self.DEFAULT_TEMPERATURE_TITAN: float = float(os.getenv("DEFAULT_TEMPERATURE_TITAN", "0.7"))
        
        # Add more model families as needed
        # self.DEFAULT_MAX_TOKENS_LLAMA: int = int(os.getenv("DEFAULT_MAX_TOKENS_LLAMA", "2048"))
        # self.DEFAULT_TEMPERATURE_LLAMA: float = float(os.getenv("DEFAULT_TEMPERATURE_LLAMA", "0.7"))

        # Retry Mechanism Configuration
        self.RETRY_MAX_ATTEMPTS: int = int(os.getenv("RETRY_MAX_ATTEMPTS", "3"))
        self.RETRY_WAIT_MIN_SECONDS: int = int(os.getenv("RETRY_WAIT_MIN_SECONDS", "1"))
        self.RETRY_WAIT_MAX_SECONDS: int = int(os.getenv("RETRY_WAIT_MAX_SECONDS", "10"))

        self._validate_config()

    def _validate_config(self):
        """Basic validation for essential configurations."""
        if not self.OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY is not set. OpenAI functionalities will be unavailable.")

        aws_static_keys_present = self.AWS_ACCESS_KEY_ID and self.AWS_SECRET_ACCESS_KEY
        aws_profile_present = bool(self.AWS_PROFILE)
        
        if not (aws_static_keys_present or aws_profile_present):
            logger.warning(
                "Neither AWS static credentials (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY) "
                "nor AWS_PROFILE are set. AWS Bedrock functionalities will be unavailable "
                "unless the environment is configured for IAM role instance profile or other implicit auth."
            )
        elif aws_static_keys_present and aws_profile_present:
            logger.info(
                "Both AWS static credentials and AWS_PROFILE are set. "
                "Static credentials will take precedence if used directly by Boto3 session before client creation."
                " APIClient logic will prioritize static keys, then profile, then default Boto3 chain."
            )

        if (aws_static_keys_present or aws_profile_present) and not self.AWS_REGION:
            logger.warning("AWS credentials/profile are set, but AWS_REGION is not. Bedrock calls may fail or use default region.")
        
        # If neither OpenAI nor AWS is configured for any use:
        if not self.OPENAI_API_KEY and not (aws_static_keys_present or aws_profile_present) :
            logger.error(
                "CRITICAL: No API keys or AWS configuration found for either OpenAI or AWS Bedrock. "
                "The LLM integration library will not be able to connect to any services."
            )
        
        log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.LOG_LEVEL not in log_levels:
            logger.warning(f"Invalid LOG_LEVEL '{self.LOG_LEVEL}'. Defaulting to INFO. Valid levels are: {log_levels}")
            self.LOG_LEVEL = "INFO"

# Global instance of AppConfig
app_config = AppConfig()

# Example of how to use it elsewhere:
# from .config_loader import app_config
# api_key = app_config.OPENAI_API_KEY 