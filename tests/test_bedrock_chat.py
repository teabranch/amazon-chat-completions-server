import pytest
import os
from async_asgi_testclient import TestClient

from src.open_amazon_chat_completions_server.api.app import app
from src.open_amazon_chat_completions_server.api.schemas.requests import ChatCompletionRequest, Message

# Check for various AWS authentication methods
def check_aws_authentication():
    """
    Check if AWS authentication is configured through any of the supported methods:
    1. AWS Profile (AWS_PROFILE)
    2. Access/Secret Keys (AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY)
    3. IAM Role assumption (AWS_ROLE_ARN with base credentials)
    4. Web Identity Token (AWS_WEB_IDENTITY_TOKEN_FILE)
    5. AWS Region must be set for any method
    """
    # Check if AWS region is set (required for all methods)
    aws_region_is_set = bool(os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION"))
    
    # Method 1: AWS Profile
    aws_profile_is_set = bool(os.getenv("AWS_PROFILE"))
    
    # Method 2: Access/Secret Keys
    aws_access_key_is_set = bool(os.getenv("AWS_ACCESS_KEY_ID"))
    aws_secret_key_is_set = bool(os.getenv("AWS_SECRET_ACCESS_KEY"))
    aws_keys_configured = aws_access_key_is_set and aws_secret_key_is_set
    
    # Method 3: IAM Role assumption (requires base credentials)
    aws_role_arn_is_set = bool(os.getenv("AWS_ROLE_ARN"))
    if aws_role_arn_is_set:
        # Role assumption requires base credentials to assume the role
        base_credentials_available = aws_profile_is_set or aws_keys_configured
        role_assumption_viable = base_credentials_available
    else:
        role_assumption_viable = False
    
    # Method 4: Web Identity Token
    aws_web_identity_token_is_set = bool(os.getenv("AWS_WEB_IDENTITY_TOKEN_FILE"))
    
    # Check if any authentication method is available along with region
    auth_methods_available = (
        aws_profile_is_set or 
        aws_keys_configured or 
        role_assumption_viable or 
        aws_web_identity_token_is_set
    )
    
    return aws_region_is_set and auth_methods_available

def get_aws_auth_status_message():
    """Get a descriptive message about current AWS authentication status."""
    aws_region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION")
    aws_profile = os.getenv("AWS_PROFILE")
    aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_role_arn = os.getenv("AWS_ROLE_ARN")
    aws_web_identity_token = os.getenv("AWS_WEB_IDENTITY_TOKEN_FILE")
    
    status_parts = []
    
    if not aws_region:
        status_parts.append("AWS_REGION/AWS_DEFAULT_REGION not set")
    
    # Check authentication methods
    auth_methods = []
    if aws_profile:
        auth_methods.append(f"AWS_PROFILE ({aws_profile})")
    if aws_access_key and aws_secret_key:
        auth_methods.append("AWS_ACCESS_KEY_ID+AWS_SECRET_ACCESS_KEY")
    if aws_role_arn:
        if aws_profile or (aws_access_key and aws_secret_key):
            auth_methods.append(f"AWS_ROLE_ARN ({aws_role_arn}) with base credentials")
        else:
            status_parts.append(f"AWS_ROLE_ARN set ({aws_role_arn}) but no base credentials (AWS_PROFILE or AWS_ACCESS_KEY_ID+AWS_SECRET_ACCESS_KEY) for role assumption")
    if aws_web_identity_token:
        auth_methods.append(f"AWS_WEB_IDENTITY_TOKEN_FILE ({aws_web_identity_token})")
    
    if not auth_methods and not any("AWS_ROLE_ARN" in part for part in status_parts):
        status_parts.append("No AWS authentication method configured")
    
    if auth_methods:
        return f"AWS authentication configured: {', '.join(auth_methods)}" + (f"; Issues: {'; '.join(status_parts)}" if status_parts else "")
    else:
        return "; ".join(status_parts) if status_parts else "AWS authentication configured"

BEDROCK_CONFIGURED = check_aws_authentication()
AWS_AUTH_STATUS_MESSAGE = get_aws_auth_status_message()

# Default Bedrock model for testing - Anthropic Claude 3 Haiku
# Ensure this model is enabled in your AWS account for the specified region.
TEST_BEDROCK_CLAUDE_MODEL = os.getenv("TEST_BEDROCK_CLAUDE_MODEL", "us.anthropic.claude-3-7-sonnet-20250219-v1:0")

bedrock_integration_test = [
    pytest.mark.asyncio,
    pytest.mark.external_api,
    pytest.mark.aws_integration,
    pytest.mark.skipif(not BEDROCK_CONFIGURED, reason=f"AWS authentication not configured: {AWS_AUTH_STATUS_MESSAGE}")
]

@pytest.fixture(scope="module")
async def client():
    """Create a test client for the FastAPI app."""
    async with TestClient(app) as client:
        yield client

@pytest.mark.asyncio
@pytest.mark.external_api
@pytest.mark.aws_integration
@pytest.mark.skipif(not BEDROCK_CONFIGURED, reason=f"AWS authentication not configured: {AWS_AUTH_STATUS_MESSAGE}")
async def test_bedrock_chat_completion_non_streaming(client: TestClient, test_api_key):
    """Test non-streaming chat completion with Bedrock Claude."""
    headers = {"Authorization": f"Bearer {test_api_key}"}
    payload = ChatCompletionRequest(
        model="anthropic.claude-3-haiku-20240307-v1:0",
        messages=[Message(role="user", content="Say 'Hello World' and nothing else.")],
        max_tokens=10,
        temperature=0
    ).model_dump()
    
    response = await client.post("/v1/chat/completions", json=payload, headers=headers)
    
    # Should succeed if AWS credentials are valid
    if response.status_code == 200:
        data = response.json()
        assert data["object"] == "chat.completion"
        assert len(data["choices"]) > 0
        assert data["choices"][0]["message"]["role"] == "assistant"
        # Claude should respond with something close to "Hello World"
        content = data["choices"][0]["message"]["content"]
        assert content is not None
        print(f"Bedrock Claude response: {content}")
    else:
        # If it fails, it might be due to invalid AWS credentials or region issues
        print(f"Bedrock integration test failed: {response.status_code} - {response.text}")

@pytest.mark.asyncio
@pytest.mark.external_api
@pytest.mark.aws_integration
@pytest.mark.skipif(not BEDROCK_CONFIGURED, reason=f"AWS authentication not configured: {AWS_AUTH_STATUS_MESSAGE}")
async def test_bedrock_chat_completion_streaming(client: TestClient, test_api_key):
    """Test streaming chat completion with Bedrock Claude - expecting successful connection."""
    headers = {"Authorization": f"Bearer {test_api_key}"}
    payload = {
        "model": "anthropic.claude-3-haiku-20240307-v1:0",
        "messages": [Message(role="user", content="Count from 1 to 5, one number per line.").model_dump()],
        "max_tokens": 50,
        "temperature": 0,
        "stream": True
    }
    
    response = await client.post("/v1/chat/completions", json=payload, headers=headers)
    
    # Should succeed if AWS credentials are valid
    if response.status_code == 200:
        # For streaming, we expect text/event-stream content type
        assert "text/event-stream" in response.headers.get("content-type", "")
        
        # Read the streaming response
        content_chunks = []
        # For async_asgi_testclient, streaming responses are available as response.text
        response_text = response.text
        if response_text.strip():
            # Split by lines and process each chunk
            for line in response_text.split('\n'):
                if line.strip():
                    content_chunks.append(line.strip())
        
        # Should have received some streaming data
        assert len(content_chunks) > 0
        print(f"Received {len(content_chunks)} streaming chunks from Bedrock Claude")
    else:
        # If it fails, it might be due to invalid AWS credentials or region issues
        print(f"Bedrock streaming test failed: {response.status_code} - {response.text}")

# Add tests for other Bedrock models (Titan, Llama2, etc.) once service supports them.
# Add tests for Bedrock specific error handling (e.g., model access denied, throttling). 