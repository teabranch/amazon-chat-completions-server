# Server and CLI Implementation

This document outlines the implemented FastAPI server and CLI components for the Amazon Chat Completions Server.

## Architecture Overview

### 1. Core Components (Implemented)
- LLM Integration Services (OpenAI and AWS Bedrock)
- Configuration Management
- Logging System
- Message Models and Types
- Service Factory Pattern

### 2. Implemented Components

#### A. Web Server Component (FastAPI)
1. **FastAPI Server Structure**
   ```
   src/
   └── amazon_chat_completions_server/
       ├── api/
       │   ├── __init__.py
       │   ├── app.py           # FastAPI application instance
       │   ├── routes/
       │   │   ├── __init__.py
       │   │   ├── chat.py      # Chat completion endpoints
       │   │   ├── models.py    # Model listing endpoints
       │   │   └── health.py    # Health check endpoints
       │   ├── middleware/
       │   │   ├── __init__.py
       │   │   ├── auth.py      # Authentication middleware
       │   │   └── logging.py   # Request logging middleware
       │   ├── schemas/
       │   │   ├── __init__.py
       │   │   ├── requests.py  # Pydantic request models
       │   │   └── responses.py # Pydantic response models
       │   └── dependencies/
       │       ├── __init__.py
       │       └── services.py  # FastAPI dependencies
   ```

2. **Implemented API Endpoints**
   - `/v1/chat/completions` - Main chat completion endpoint (POST)
   - `/v1/chat/completions/stream` - WebSocket streaming endpoint
   - `/v1/models` - List available models (GET)
   - `/health` - Health check endpoint (GET)

3. **Authentication & Security**
   - API Key authentication via X-API-Key header
   - CORS configuration
   - Request validation using Pydantic models
   - Sensitive data masking in logs

4. **Monitoring & Logging**
   - Request/Response logging with timing information
   - Error tracking with detailed logging
   - Health checks for service status

#### B. CLI Component
1. **Command Structure**
   ```
   amazon-chat [COMMAND] [OPTIONS]
   ```

2. **Implemented Commands**
   - `chat` - Interactive chat session
     ```bash
     amazon-chat chat --model MODEL_NAME [--server-url URL] [--api-key KEY]
     ```
   - `models` - List available models
     ```bash
     amazon-chat models [--server-url URL] [--api-key KEY]
     ```
   - `config set` - Set up API keys and preferences interactively
     ```bash
     amazon-chat config set
     ```
   - `config show` - Display current configuration (with masked sensitive values)
     ```bash
     amazon-chat config show
     ```
   - `serve` - Start the web server
     ```bash
     amazon-chat serve [--host HOST] [--port PORT] [--reload] [--env-file PATH]
     ```

3. **Configuration Management**
   - Environment variables loaded from `.env` file
   - Secure storage of API keys and credentials
   - Interactive configuration wizard
   - Support for AWS credentials (static keys or profile)

### 3. Testing Coverage

1. **Core Tests**
   - Model validation and serialization
   - Exception handling
   - Configuration loading

2. **Adapter Tests**
   - OpenAI adapter functionality
   - Bedrock adapter strategies (Claude, Titan)
   - Error handling and retries

3. **CLI Tests**
   - Command execution
   - Configuration management
   - Input/output handling

4. **API Tests**
   - Endpoint functionality
   - Authentication
   - WebSocket streaming
   - Error responses

### 4. Running the Server

The server can be run using either the CLI command or directly with uvicorn:

```bash
# Using CLI (recommended)
amazon-chat serve --host 0.0.0.0 --port 8000 --reload

# Using uvicorn directly
uvicorn src.amazon_chat_completions_server.api.app:app --host 0.0.0.0 --port 8000 --workers 4
```

### 5. Configuration

The server and CLI can be configured using a `.env` file. Essential configuration includes:

```env
# Server Configuration
API_KEY="your-api-key"                 # Required for API authentication
LOG_LEVEL="INFO"                       # Optional, defaults to INFO
CHAT_SERVER_URL="http://localhost:8000" # For CLI client use

# LLM Provider Configuration
OPENAI_API_KEY="your-openai-key"       # Required for OpenAI

# AWS Configuration (Options)
# Option 1: Static Credentials
AWS_ACCESS_KEY_ID="your-key-id"
AWS_SECRET_ACCESS_KEY="your-secret-key"
# Option 2: AWS Profile
AWS_PROFILE="your-profile"        # Alternative to static credentials

# Required for AWS Bedrock
AWS_REGION="us-east-1"            # Required for Bedrock
```

### 6. API Documentation

FastAPI automatically generates:
- OpenAPI documentation at `/docs`
- ReDoc documentation at `/redoc`
- OpenAPI JSON schema at `/openapi.json`

### 7. Error Handling

The server implements comprehensive error handling:

1. **API Errors**
   - 400: Bad Request (invalid parameters)
   - 401: Unauthorized (invalid API key)
   - 404: Not Found (model not found)
   - 429: Too Many Requests (rate limit)
   - 500: Internal Server Error
   - 503: Service Unavailable

2. **WebSocket Errors**
   - Connection authentication
   - Message validation
   - Stream handling
   - Graceful disconnection

3. **LLM Provider Errors**
   - Connection issues
   - Rate limiting
   - Invalid requests
   - Service unavailability 