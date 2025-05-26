# Amazon Chat Completions Server

A server and CLI for interacting with various Large Language Model (LLM) providers, including OpenAI and AWS Bedrock (Claude, Titan). It offers a unified API for chat completions and model management.

## Features

- **Multi-Provider Support:** Seamlessly switch between different LLM providers.
- **Unified API:** Consistent request and response formats for chat completions.
- **Streaming Support:** Real-time streaming of LLM responses.
- **CLI:**

   - Interactive chat sessions.
   - Server management (start, configure).
   - Chat history management (list, export, delete).
   - List available models from the server.

- **Server:**

   - FastAPI-based server for robust API interactions.
   - Endpoints for health checks, chat completions, and model listing.
   - Configurable API key authentication.

- **Configuration Management:** Easy setup of API keys and server settings via a `.env` file or interactive CLI commands.

## Installation

```bash
# Create and activate a virtual environment (optional but recommended)
python -m venv .venv  # Or use: uv venv
source .venv/bin/activate

# Install with uv
uv pip install -e . # For editable install
# or
# uv pip install . # For regular install
```

## Configuration

The application uses a `.env` file in the project root to store API keys and other settings. You can configure these settings interactively using the CLI:

```bash
amazon-chat config set
```

This command will guide you through setting up:

- `API_KEY`: An API key to secure your server (used in the `X-API-Key` header).
- `LOG_LEVEL`: The server's log level (e.g., INFO, DEBUG).
- `CHAT_SERVER_URL`: The URL your CLI will use to connect to the chat server (defaults to `http://localhost:8000`).
- `CHAT_API_KEY`: The API key your CLI will use to authenticate with the server.
- **LLM Provider Keys:**
   - `OPENAI_API_KEY`: For OpenAI models.
   - `OPENAI_BASE_URL`: (Optional) For OpenAI-compatible APIs, you can set this environment variable to point to a different base URL (e.g., for Azure OpenAI or a local LLM server). The OpenAI client library will automatically use this if set.
   - `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_PROFILE`, `AWS_REGION`: For AWS Bedrock models.

Alternatively, you can manually create or edit the `.env` file in your project's root directory.

Example `.env` file:

```env
API_KEY="your-secret-server-api-key"
LOG_LEVEL="INFO"
CHAT_SERVER_URL="http://localhost:8000"
CHAT_API_KEY="your-secret-server-api-key" # Can be the same as API_KEY for local use

# --- LLM Provider Keys ---
# OpenAI
OPENAI_API_KEY="sk-your_openai_api_key"
# OPENAI_BASE_URL="your_custom_openai_compatible_endpoint" # Optional

# AWS Bedrock (choose one auth method)
# Option 1: AWS Access Keys
AWS_ACCESS_KEY_ID="YOUR_AWS_ACCESS_KEY"
AWS_SECRET_ACCESS_KEY="YOUR_AWS_SECRET_KEY"
AWS_REGION="us-east-1" # e.g., us-east-1, us-west-2
# Option 2: AWS Profile (if keys above are blank)
# AWS_PROFILE="your-aws-profile-name"
# AWS_REGION="us-east-1" # Required even with a profile for Bedrock
```

To view your current configuration (sensitive values will be masked):

```bash
amazon-chat config show
```

## Usage

### Start the server

```bash
amazon-chat serve --host 0.0.0.0 --port 8000 --reload
```

Then access the API at `http://localhost:8000`.

- Docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

The server provides the following main API endpoints:

- `GET /health`: Health check.
- `POST /v1/chat/completions`: Process chat completion requests (supports streaming via WebSockets at `ws://localhost:8000/v1/chat/completions/ws`).
- `GET /v1/models`: List available LLM models.

### CLI Usage

The `amazon-chat` CLI allows you to interact with the server and manage its configuration.

**1. Configure the CLI and Server:**
As mentioned in the Configuration section, start by setting up your API keys and server details:

```bash
amazon-chat config set
```

**2. Start an Interactive Chat Session:**

```bash
amazon-chat chat --model <model_id>
```

Replace `<model_id>` with the ID of the model you want to use (e.g., `gpt-4o-mini`, `us.anthropic.claude-3-5-haiku-20241022-v1:0`).

Example:

```bash
amazon-chat chat --model gpt-4o-mini
```

You can also specify the server URL and API key if they differ from your `.env` configuration:

```bash
amazon-chat chat --model gpt-4o-mini --server-url http://custom.server:1234 --api-key mysecretkey
```

Other chat options:

- `--no-stream`: Disable streaming responses.
- `--session <session_id>`: Continue an existing chat session.
- `--session-name "My Project Chat"`: Name a new chat session for easier identification.

**3. List Available Models:**
To see which models are available through the server:

```bash
amazon-chat models
```

**4. Manage Chat History:**

- List all chat sessions:

```bash
amazon-chat history list
```

- Export a specific chat session to JSON:

```bash
amazon-chat history export <session_id> -o chat_export.json
```

- Delete a specific chat session:

```bash
amazon-chat history delete <session_id>
```

### Server API Examples

You can interact with the server API directly using tools like `curl` or any HTTP client. Remember to include your `X-API-Key` header if you've configured an `API_KEY` on the server.

**1. Get Health Status:**

```bash
curl http://localhost:8000/health
```

**2. List Available Models:**

```bash
curl -X GET http://localhost:8000/v1/models -H "X-API-Key: your-secret-server-api-key"
```

**3. Chat Completions (Non-Streaming):**

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
     -H "Content-Type: application/json" \
     -H "X-API-Key: your-secret-server-api-key" \
     -d '{
         "model": "gpt-4o-mini",
         "messages": [
             {"role": "system", "content": "You are a helpful assistant."},
             {"role": "user", "content": "Hello! What is the capital of France?"}
         ],
         "max_tokens": 50,
         "temperature": 0.7,
         "stream": false
     }'
```

**4. Chat Completions (Streaming via WebSocket):**
You would typically use a WebSocket client for this. The CLI's `amazon-chat chat` command uses this endpoint when streaming is enabled.
The WebSocket endpoint is: `ws://localhost:8000/v1/chat/completions/ws`

The client sends a JSON message similar to the non-streaming request to initiate the connection, and the server will stream back chunks of the response.
Example initial message from client:

```json
{
    "model": "gpt-4o-mini",
    "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Tell me a story about a brave knight."}
    ],
    "max_tokens": 150,
    "temperature": 0.8,
    "stream": true,
    "api_key": "your-secret-server-api-key" // API key sent in the initial WS message
}
```

Note: For WebSocket connections, the API key can be passed in the initial JSON payload as `api_key` if not feasible to set custom headers for the WebSocket handshake in your client. The server will check for it.
