import os

from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

security = HTTPBearer(auto_error=False)


def get_api_key() -> str:
    """Get the API key from environment variable, with fallback for testing"""
    return os.getenv("API_KEY", "your-secret-api-key")


def is_valid_api_key(api_key: str) -> bool:
    """Check if the provided API key is valid"""
    current_api_key = get_api_key()

    # Check if the API_KEY is the default fallback, indicating it might not be properly configured.
    if current_api_key == "your-secret-api-key" and os.getenv("API_KEY") is None:
        # This means the .env file was likely not loaded or API_KEY is not set in the environment.
        # For a real production server, this is a misconfiguration.
        # For testing, this fallback allows tests to run without a .env if they use the same fallback.
        print(
            "Warning: Server API_KEY is using the default fallback value. Ensure API_KEY is set in .env for production."
        )

    return api_key == current_api_key


async def verify_api_key(
    credentials: HTTPAuthorizationCredentials = Security(security),
):
    if not credentials:
        # Consistent error structure as per custom http_exception_handler
        raise HTTPException(status_code=403, detail="Not authenticated")
    if not is_valid_api_key(credentials.credentials):
        # Consistent error structure
        raise HTTPException(status_code=403, detail="Invalid API key")
    return credentials.credentials
