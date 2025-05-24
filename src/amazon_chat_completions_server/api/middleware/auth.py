from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader
import os

# Load API_KEY from environment variable, with a fallback that matches test setup for consistency if .env not loaded
API_KEY = os.getenv("API_KEY", "your-secret-api-key")
API_KEY_NAME = "X-API-Key"

api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

def is_valid_api_key(api_key: str) -> bool:
    # Check if the API_KEY is the default fallback, indicating it might not be properly configured.
    if API_KEY == "your-secret-api-key" and os.getenv("API_KEY") is None:
        # This means the .env file was likely not loaded or API_KEY is not set in the environment.
        # For a real production server, this is a misconfiguration.
        # For testing, this fallback allows tests to run without a .env if they use the same fallback.
        print("Warning: Server API_KEY is using the default fallback value. Ensure API_KEY is set in .env for production.")
    return api_key == API_KEY

async def verify_api_key(api_key: str = Security(api_key_header)):
    if not api_key:
        # Consistent error structure as per custom http_exception_handler
        raise HTTPException(
            status_code=403, 
            detail="Not authenticated"
        )
    if not is_valid_api_key(api_key):
        # Consistent error structure
        raise HTTPException(
            status_code=403, 
            detail="Invalid API key"
        )
    return api_key 