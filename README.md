# Open Bedrock Server

A unified, provider-agnostic chat completions API server that seamlessly integrates OpenAI and AWS Bedrock through a single endpoint with intelligent format detection and conversion.

## 🚀 Key Features

- **🔄 Unified Endpoint**: Single `/v1/chat/completions` endpoint handles all providers and formats
- **🧠 Smart Format Detection**: Automatically detects OpenAI, Bedrock Claude, and Bedrock Titan formats
- **🔀 Seamless Conversion**: Convert between any format combination (OpenAI ↔ Bedrock Claude ↔ Bedrock Titan)
- **⚡ Model-Based Routing**: Automatic provider selection based on model ID patterns
- **📁 File Query System**: Upload, process, and query files in chat completions with automatic content extraction
- **🌊 Streaming Support**: Real-time streaming with format preservation
- **🛡️ Enterprise Ready**: Authentication, logging, error handling, and monitoring
- **💻 Full CLI**: Interactive chat, server management, and configuration tools
- **📚 OpenAI Compatible**: Drop-in replacement for OpenAI Chat Completions API

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Unified Endpoint](#unified-endpoint)
- [File Query System](#file-query-system)
- [Format Support](#format-support)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage Examples](#usage-examples)
- [CLI Reference](#cli-reference)
- [API Documentation](#api-documentation)
- [Architecture](#architecture)
- [Contributing](#contributing)

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/teabranch/open-bedrock-server.git
cd open-bedrock-server

# Install with uv (recommended)
uv pip install -e .

# Or with pip
pip install -e .
```

### 2. Configuration

```bash
# Interactive configuration setup
bedrock-chat config set

# Or manually create .env file
# Create .env file with your configuration
# Edit .env with your API keys
```

### 3. Start Server

```bash
# Start the server
bedrock-chat serve --host 0.0.0.0 --port 8000

# Server will be available at:
# 🌐 API: http://localhost:8000
# 📚 Docs: http://localhost:8000/docs
```

### 4. Test the Unified Endpoint

```bash
# OpenAI format → OpenAI response
curl -X POST "http://localhost:8000/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [
      {"role": "user", "content": "Hello!"}
    ]
  }'

# OpenAI format → Bedrock Claude response
curl -X POST "http://localhost:8000/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "model": "anthropic.claude-3-haiku-20240307-v1:0",
    "messages": [
      {"role": "user", "content": "Hello!"}
    ]
  }'

# Bedrock Claude format → OpenAI response
curl -X POST "http://localhost:8000/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "anthropic_version": "bedrock-2023-05-31",
    "model": "anthropic.claude-3-haiku-20240307-v1:0",
    "max_tokens": 1000,
    "messages": [
      {"role": "user", "content": "Hello!"}
    ]
  }'
```

## 🔄 Unified Endpoint

### Single Endpoint for Everything

The `/v1/chat/completions` endpoint is the **only endpoint you need**. It:

1. **Auto-detects** your input format (OpenAI, Bedrock Claude, Bedrock Titan)
2. **Routes** to the appropriate provider based on model ID
3. **Converts** between formats as needed
4. **Streams** responses in real-time when requested
5. **Returns** responses in your preferred format

### How It Works

```mermaid
graph LR
    A[Any Format Request] --> B[Format Detection]
    B --> C[Model-Based Routing]
    C --> D[Provider API Call]
    D --> E[Format Conversion]
    E --> F[Unified Response]
    
    style A fill:#e1f5fe
    style F fill:#e8f5e8
```

### Model-Based Routing

The server automatically routes requests based on model ID patterns:

| Model Pattern | Provider | Examples |
|---------------|----------|----------|
| `gpt-*` | OpenAI | `gpt-4o-mini`, `gpt-3.5-turbo` |
| `text-*` | OpenAI | `text-davinci-003` |
| `dall-e-*` | OpenAI | `dall-e-3` |
| `anthropic.*` | Bedrock | `anthropic.claude-3-haiku-20240307-v1:0` |
| `amazon.*` | Bedrock | `amazon.titan-text-express-v1` |
| `ai21.*`, `cohere.*`, `meta.*` | Bedrock | Various Bedrock models |

## 📁 File Query System

### Overview

Upload, process, and query files directly in your chat completions. The system automatically extracts and formats content from various file types, making file data available as context for your AI conversations.

### Quick Example

```bash
# 1. Upload a file
curl -X POST "http://localhost:8000/v1/files" \
  -H "Authorization: Bearer your-api-key" \
  -F "file=@data.csv" \
  -F "purpose=assistants"

# Response: {"id": "file-abc123", "filename": "data.csv", ...}

# 2. Query the file in chat
curl -X POST "http://localhost:8000/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [
      {"role": "user", "content": "Analyze the data in this file"}
    ],
    "file_ids": ["file-abc123"]
  }'
```

### Supported File Types

| Format | MIME Type | Auto-Processing |
|--------|-----------|-----------------|
| Text | `text/plain` | ✅ Full content |
| CSV | `text/csv` | ✅ Structured data with headers |
| JSON | `application/json` | ✅ Formatted structure |
| HTML | `text/html` | ✅ Text extraction |
| XML | `application/xml` | ✅ Formatted structure |
| Markdown | `text/markdown` | ✅ Full content |

### File Operations

#### Upload Files
```bash
POST /v1/files
```
Upload files to S3 storage with metadata extraction.

#### List Files
```bash
GET /v1/files
GET /v1/files?purpose=assistants
```
List uploaded files with optional filtering.

#### Get File Metadata
```bash
GET /v1/files/{file_id}
```
Retrieve file information and metadata.

#### Download File Content
```bash
GET /v1/files/{file_id}/content
```
Download original file content.

#### Delete Files
```bash
DELETE /v1/files/{file_id}
```
Remove files from storage.

### Chat Integration

Add `file_ids` to any chat completion request to include file content as context:

```json
{
  "model": "gpt-4o-mini",
  "messages": [
    {"role": "user", "content": "What patterns do you see in this data?"}
  ],
  "file_ids": ["file-abc123", "file-def456"]
}
```

The system automatically:
1. **Retrieves** file content from S3
2. **Processes** content based on file type
3. **Formats** for optimal AI consumption
4. **Prepends** to your user message as context

### Configuration

Add S3 configuration to your `.env` file:

```env
# Required for file operations
S3_FILES_BUCKET=your-s3-bucket-name
AWS_REGION=us-east-1

# AWS authentication (choose one method)
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
# OR
AWS_PROFILE=your-aws-profile
```

### File Processing Examples

**CSV Data Processing:**
```
=== UPLOADED FILES CONTEXT ===

📄 **File: sales_data.csv** (text/csv, 1.2KB)
Created: 2024-12-09T14:23:01Z

**Processed Content:**
Date,Product,Sales,Revenue
2024-01-01,Widget A,150,$1500.00
2024-01-02,Widget B,200,$2000.00
...
```

**JSON Configuration:**
```
=== UPLOADED FILES CONTEXT ===

📄 **File: config.json** (application/json, 500B)
Created: 2024-12-09T14:23:01Z

**Processed Content:**
{
  "database": {
    "host": "localhost",
    "port": 5432
  },
  "features": ["auth", "logging"]
}
```

### Health Check

Monitor file service status:

```bash
curl "http://localhost:8000/v1/files/health"
```

Response includes S3 connectivity and credential validation.

## 🔀 Format Support

### All Format Combinations Supported

| Input Format | Output Format | Use Case | Streaming |
|-------------|---------------|----------|-----------|
| OpenAI | OpenAI | Standard OpenAI usage | ✅ |
| OpenAI | Bedrock Claude | OpenAI clients → Claude responses | ✅ |
| OpenAI | Bedrock Titan | OpenAI clients → Titan responses | ✅ |
| Bedrock Claude | OpenAI | Claude clients → OpenAI responses | ✅ |
| Bedrock Claude | Bedrock Claude | Native Claude usage | ✅ |
| Bedrock Titan | OpenAI | Titan clients → OpenAI responses | ✅ |
| Bedrock Titan | Bedrock Titan | Native Titan usage | ✅ |

### Format Examples

**OpenAI Format:**
```json
{
  "model": "gpt-4o-mini",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"}
  ],
  "temperature": 0.7,
  "max_tokens": 1000,
  "stream": false
}
```

**Bedrock Claude Format:**
```json
{
  "anthropic_version": "bedrock-2023-05-31",
  "model": "anthropic.claude-3-haiku-20240307-v1:0",
  "max_tokens": 1000,
  "messages": [{"role": "user", "content": "Hello!"}],
  "temperature": 0.7,
  "stream": false
}
```

**Bedrock Titan Format:**
```json
{
  "model": "amazon.titan-text-express-v1",
  "inputText": "User: Hello!\n\nBot:",
  "textGenerationConfig": {
    "maxTokenCount": 1000,
    "temperature": 0.7
  }
}
```

## 📦 Installation

### Prerequisites

- Python 3.12+
- OpenAI API key (for OpenAI models)
- AWS credentials (for Bedrock models)

### Install Options

```bash
# Option 1: Development installation
git clone https://github.com/teabranch/open-bedrock-server.git
cd open-bedrock-server
uv pip install -e .

# Option 2: Direct from GitHub
pip install git+https://github.com/teabranch/open-bedrock-server.git

# Option 3: Local wheel
pip install dist/open_bedrock_server-*.whl
```

### Verify Installation

```bash
# Check CLI is available
bedrock-chat --help

# Check version
bedrock-chat config show
```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file with your configuration:

```env
# Required: Server Authentication
API_KEY=your-secret-api-key

# Required: OpenAI (if using OpenAI models)
OPENAI_API_KEY=sk-your-openai-api-key

# Required: S3 File Storage (if using file query features)
S3_FILES_BUCKET=your-s3-bucket-name

# Required: AWS (if using Bedrock models)
# Option 1: Static credentials
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_REGION=us-east-1

# Option 2: AWS Profile (alternative to static credentials)
AWS_PROFILE=your-aws-profile
AWS_REGION=us-east-1

# Option 3: AWS Role Assumption (for cross-account access or enhanced security)
AWS_ROLE_ARN=arn:aws:iam::123456789012:role/MyBedrockRole
AWS_EXTERNAL_ID=your-external-id  # Optional, for cross-account role assumption
AWS_ROLE_SESSION_NAME=bedrock-server-session  # Optional
AWS_ROLE_SESSION_DURATION=3600  # Optional, session duration in seconds
AWS_REGION=us-east-1

# Option 4: Web Identity Token (for OIDC/Kubernetes service accounts)
AWS_WEB_IDENTITY_TOKEN_FILE=/var/run/secrets/eks.amazonaws.com/serviceaccount/token
AWS_ROLE_ARN=arn:aws:iam::123456789012:role/MyWebIdentityRole
AWS_REGION=us-east-1

# Optional: Defaults
DEFAULT_OPENAI_MODEL=gpt-4o-mini
LOG_LEVEL=INFO
CHAT_SERVER_URL=http://localhost:8000
CHAT_API_KEY=your-secret-api-key
```

### AWS Authentication Methods

The server supports multiple AWS authentication methods with automatic detection and fallback. Choose the method that best fits your deployment scenario:

#### 1. Static Credentials (Development/Testing)
Direct AWS access keys - simplest but least secure:
```env
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_SESSION_TOKEN=your-session-token  # Optional, for temporary credentials
AWS_REGION=us-east-1
```

**Use cases:** Local development, testing, CI/CD pipelines
**Security:** ⚠️ Store securely, rotate regularly

#### 2. AWS Profile (Local Development)
Uses AWS CLI configured profiles:
```env
AWS_PROFILE=your-aws-profile
AWS_REGION=us-east-1
```

**Setup:**
```bash
# Configure AWS CLI profile
aws configure --profile your-aws-profile
# Or use AWS SSO
aws configure sso --profile your-aws-profile
```

**Use cases:** Local development with multiple AWS accounts
**Security:** ✅ Credentials managed by AWS CLI

#### 3. Role Assumption (Cross-Account/Enhanced Security)
Assume an IAM role using base credentials:
```env
# Base credentials (required for role assumption)
AWS_PROFILE=base-profile
# OR
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY

# Role to assume
AWS_ROLE_ARN=arn:aws:iam::123456789012:role/BedrockAccessRole
AWS_EXTERNAL_ID=unique-external-id  # Optional, for cross-account scenarios
AWS_ROLE_SESSION_NAME=bedrock-server-session  # Optional
AWS_ROLE_SESSION_DURATION=3600  # Optional, 900-43200 seconds (default: 3600)
AWS_REGION=us-east-1
```

**Role Trust Policy Example:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::SOURCE-ACCOUNT:user/username"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "sts:ExternalId": "unique-external-id"
        }
      }
    }
  ]
}
```

**Use cases:** Cross-account access, temporary elevated permissions, security compliance
**Security:** ✅ Time-limited sessions, audit trail, least privilege

#### 4. Web Identity Token (OIDC/Kubernetes)
For containerized environments with OIDC providers:
```env
AWS_WEB_IDENTITY_TOKEN_FILE=/var/run/secrets/eks.amazonaws.com/serviceaccount/token
AWS_ROLE_ARN=arn:aws:iam::123456789012:role/EKSBedrockRole
AWS_ROLE_SESSION_NAME=bedrock-server-session  # Optional
AWS_REGION=us-east-1
```

**Kubernetes ServiceAccount Example:**
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: bedrock-server
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/EKSBedrockRole
```

**Use cases:** EKS, GitHub Actions, GitLab CI, other OIDC providers
**Security:** ✅ No long-term credentials, automatic rotation

#### 5. Instance Profile/Default Chain (Production)
No configuration needed - uses AWS default credential chain:
```env
# Only region required
AWS_REGION=us-east-1
```

**Credential Chain Order:**
1. Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
2. Shared credentials file (`~/.aws/credentials`)
3. Shared config file (`~/.aws/config`)
4. IAM instance profiles (EC2)
5. ECS task roles
6. EKS service account roles

**Use cases:** EC2 instances, ECS tasks, Lambda functions
**Security:** ✅ No credential management, automatic rotation

### Authentication Priority and Fallback

The server uses this priority order for authentication:

1. **Static Credentials** (`AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY`)
2. **AWS Profile** (`AWS_PROFILE`)
3. **Role Assumption** (`AWS_ROLE_ARN` with base credentials)
4. **Web Identity Token** (`AWS_WEB_IDENTITY_TOKEN_FILE`)
5. **Default Credential Chain** (instance profiles, etc.)

### AWS Authentication Troubleshooting

#### Common Issues and Solutions

**❌ "Role assumption requires base AWS credentials"**
```bash
# Problem: AWS_ROLE_ARN set but no base credentials
# Solution: Add base credentials
AWS_PROFILE=your-profile  # OR
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
```

**❌ "The config profile (profile-name) could not be found"**
```bash
# Problem: Profile doesn't exist
# Solution: Configure the profile
aws configure --profile profile-name
# Or check existing profiles
aws configure list-profiles
```

**❌ "Access denied when assuming role"**
```bash
# Problem: Role trust policy or permissions issue
# Solution: Check role trust policy allows your principal
# Verify role has bedrock:* permissions
```

**❌ "Web identity token file not found"**
```bash
# Problem: Token file path incorrect
# Solution: Verify the token file exists
ls -la /var/run/secrets/eks.amazonaws.com/serviceaccount/token
```

**❌ "You must specify a region"**
```bash
# Problem: AWS_REGION not set
# Solution: Set the region
AWS_REGION=us-east-1
```

#### Testing Authentication

```bash
# Test your AWS configuration
bedrock-chat config test-aws

# Or manually test with AWS CLI
aws sts get-caller-identity --profile your-profile
aws bedrock list-foundation-models --region us-east-1
```

### Required AWS Permissions

Your AWS credentials need these minimum permissions for Bedrock:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream",
        "bedrock:ListFoundationModels"
      ],
      "Resource": "*"
    }
  ]
}
```

For role assumption, also add:
```json
{
  "Effect": "Allow",
  "Action": "sts:AssumeRole",
  "Resource": "arn:aws:iam::*:role/YourBedrockRole"
}
```

### Interactive Configuration

```bash
# Run interactive setup
bedrock-chat config set

# View current configuration (sensitive values masked)
bedrock-chat config show

# Set specific values
bedrock-chat config set --key OPENAI_API_KEY --value sk-your-key

# Test AWS authentication
bedrock-chat config test-aws
```

> 📖 **For detailed AWS authentication documentation, see [AWS Authentication Guide](docs/AWS_AUTHENTICATION.md)**

## 💡 Usage Examples

### Basic Chat Completion

```python
import httpx

# OpenAI format request
response = httpx.post(
    "http://localhost:8000/v1/chat/completions",
    headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer your-api-key"
    },
    json={
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": "Hello!"}]
    }
)

print(response.json())
```

### Format Conversion

```python
# Send OpenAI format, get Bedrock Claude response
response = httpx.post(
    "http://localhost:8000/v1/chat/completions?target_format=bedrock_claude",
    headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer your-api-key"
    },
    json={
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": "Hello!"}]
    }
)

# Response will be in Bedrock Claude format
claude_response = response.json()
print(claude_response["content"][0]["text"])
```

### Streaming

```python
import httpx

# Streaming request
with httpx.stream(
    "POST",
    "http://localhost:8000/v1/chat/completions",
    headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer your-api-key"
    },
    json={
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": "Tell me a story"}],
        "stream": True
    }
) as response:
    for line in response.iter_lines():
        if line.startswith("data: "):
            data = line[6:]  # Remove "data: " prefix
            if data != "[DONE]":
                chunk = json.loads(data)
                if chunk["choices"][0]["delta"].get("content"):
                    print(chunk["choices"][0]["delta"]["content"], end="")
```

### Tool Calling

```python
# Tool calling with OpenAI format
response = httpx.post(
    "http://localhost:8000/v1/chat/completions",
    headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer your-api-key"
    },
    json={
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": "What's the weather in London?"}],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get current weather",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {"type": "string"}
                        },
                        "required": ["location"]
                    }
                }
            }
        ],
        "tool_choice": "auto"
    }
)

# Check for tool calls in response
if response.json()["choices"][0]["message"].get("tool_calls"):
    print("Model wants to call a tool!")
```

## 💻 CLI Reference

### Core Commands

```bash
# Interactive chat session
bedrock-chat chat --model gpt-4o-mini

# Start server
bedrock-chat serve --host 0.0.0.0 --port 8000

# Configuration management
bedrock-chat config set
bedrock-chat config show

# List available models
bedrock-chat models

# Get help
bedrock-chat --help
bedrock-chat COMMAND --help
```

### Chat Session

```bash
# Start interactive chat
bedrock-chat chat --model gpt-4o-mini --stream

# Chat with custom settings
bedrock-chat chat \
  --model anthropic.claude-3-haiku-20240307-v1:0 \
  --temperature 0.8 \
  --max-tokens 500

# Chat with custom server
bedrock-chat chat \
  --server-url https://my-server.com \
  --api-key my-key
```

### Server Management

```bash
# Development server with auto-reload
bedrock-chat serve --reload --log-level debug

# Production server
bedrock-chat serve \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --env-file production.env
```

## 📚 API Documentation

### Interactive Documentation

When the server is running, visit:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

### Available Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/chat/completions` | POST | **Unified chat completions endpoint** |
| `/v1/models` | GET | List available models |
| `/health` | GET | General health check |
| `/v1/chat/completions/health` | GET | Unified endpoint health check |

### Authentication

All endpoints require authentication via the `Authorization` Bearer token:

```bash
curl -H "Authorization: Bearer your-api-key" http://localhost:8000/v1/models
```

## 🏗️ Architecture

### Unified Architecture Overview

```mermaid
graph TD
    A[Client Request] --> B[/v1/chat/completions]
    B --> C{Format Detection}
    
    C --> D1[OpenAI Format]
    C --> D2[Bedrock Claude Format]
    C --> D3[Bedrock Titan Format]
    
    D1 --> E{Model-Based Routing}
    D2 --> F[Format Conversion] --> E
    D3 --> F
    
    E --> G1[OpenAI Service]
    E --> G2[Bedrock Service]
    
    G1 --> H1[OpenAI API]
    G2 --> H2[AWS Bedrock API]
    
    H1 --> I[Response Processing]
    H2 --> I
    
    I --> J{Target Format?}
    J --> K1[OpenAI Response]
    J --> K2[Bedrock Claude Response]
    J --> K3[Bedrock Titan Response]
    
    K1 --> L[Client Response]
    K2 --> L
    K3 --> L
```

### Key Components

1. **Format Detection**: Automatically identifies input format
2. **Model-Based Routing**: Routes to appropriate provider based on model ID
3. **Service Layer**: Abstracts provider-specific implementations
4. **Adapter Layer**: Handles format conversions
5. **Strategy Pattern**: Manages different model families within providers

### Design Principles

- **Single Responsibility**: Each component has a clear, focused purpose
- **Open/Closed**: Easy to extend with new providers or formats
- **Dependency Inversion**: High-level modules don't depend on low-level details
- **Interface Segregation**: Clean, minimal interfaces between components

## 🧪 Testing

### Test Categories

The project includes several categories of tests:

- **Unit Tests**: Fast, isolated tests that don't make external API calls
- **Integration Tests**: Tests that make real API calls to external services
- **External API Tests**: Tests marked with `external_api` that are skipped in CI

### Running Tests

```bash
# Run all tests (excluding external API tests)
uv run pytest

# Run all tests including external API tests (requires credentials)
uv run pytest -m "not external_api or external_api"

# Run only unit tests (no external API calls)
uv run pytest -m "not external_api"

# Run only OpenAI integration tests (requires OPENAI_API_KEY)
uv run pytest -m "openai_integration"

# Run only AWS/Bedrock integration tests (requires AWS credentials)
uv run pytest -m "aws_integration"

# Run all external API tests (requires all credentials)
uv run pytest -m "external_api"

# Run with coverage
uv run pytest --cov=src --cov-report=html

# Run specific test categories
uv run pytest tests/cli/  # CLI tests
uv run pytest tests/core/ # Core functionality tests
uv run pytest tests/adapters/ # Adapter tests
uv run pytest tests/utils/ # Utility tests
```

### External API Test Configuration

External API tests require real credentials and are automatically skipped when:

- **OpenAI Tests**: `OPENAI_API_KEY` environment variable is not set
- **AWS/Bedrock Tests**: AWS authentication is not configured (no `AWS_REGION`, `AWS_PROFILE`, or `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`)

#### Setting up OpenAI Integration Tests

```bash
export OPENAI_API_KEY="sk-your-openai-api-key"
export TEST_OPENAI_MODEL="gpt-4o"  # Optional, defaults to gpt-4o
uv run pytest -m "openai_integration"
```

#### Setting up AWS/Bedrock Integration Tests

```bash
# Option 1: Using AWS Profile
export AWS_PROFILE="your-aws-profile"
export AWS_REGION="us-east-1"

# Option 2: Using Access Keys
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_REGION="us-east-1"

# Option 3: Using Role Assumption
export AWS_PROFILE="your-base-profile"
export AWS_ROLE_ARN="arn:aws:iam::123456789012:role/YourRole"
export AWS_EXTERNAL_ID="your-external-id"  # Optional
export AWS_REGION="us-east-1"

# Run AWS tests
uv run pytest -m "aws_integration"
```

### GitHub Actions CI/CD

- **Regular CI**: Runs unit tests only (`pytest -m "not external_api"`)
- **Integration Tests**: Manual workflow for running external API tests with credentials
  - Can be triggered manually from GitHub Actions tab
  - Supports running OpenAI tests, AWS tests, or both
  - Uses repository secrets for API keys and credentials

### Test Coverage

- ✅ **152 tests passing** with comprehensive coverage
- ✅ **Format detection** and conversion
- ✅ **Model-based routing** logic
- ✅ **Streaming** functionality
- ✅ **Error handling** and edge cases
- ✅ **Authentication** and security
- ✅ **CLI commands** and configuration
- ✅ **External API integration** (when credentials available)

## 🚀 Deployment

### Docker Deployment

```bash
# Build image
docker build -t open-bedrock-server .

# Run container
docker run -p 8000:8000 \
  -e API_KEY=your-api-key \
  -e OPENAI_API_KEY=sk-your-key \
  open-bedrock-server
```

### Production Considerations

- **Environment Variables**: Use secure secret management
- **Load Balancing**: Multiple server instances behind a load balancer
- **Monitoring**: Implement health checks and metrics collection
- **Rate Limiting**: Configure appropriate rate limits for your use case
- **SSL/TLS**: Use HTTPS in production environments

## 🤝 Contributing

We welcome contributions! Please see our [Development Guide](docs/development.md) for details on how to extend, customize, or contribute to the project.

### Development Setup

```bash
# Clone and setup
git clone https://github.com/teabranch/open-bedrock-server.git
cd open-bedrock-server

# Install development dependencies
uv pip install -e ".[dev]"

# Run tests
python -m pytest

# Run linting
ruff check src tests
mypy src
```

### Adding New Providers

1. Implement `AbstractLLMService` interface
2. Add model ID patterns to `LLMServiceFactory`
3. Create format conversion adapters
4. Add comprehensive tests
5. Update documentation

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Links

- **Documentation**: [docs/](docs/)
- **API Reference**: [docs/api-reference.md](docs/api-reference.md)
- **CLI Reference**: [docs/cli-reference.md](docs/cli-reference.md)
- **Architecture Guide**: [docs/architecture.md](docs/architecture.md)
- **Issues**: [GitHub Issues](https://github.com/teabranch/open-bedrock-server/issues)

---

**Open Bedrock Server** - Unifying LLM providers through intelligent format detection and seamless conversion. 🚀
