---
layout: default
title: Getting Started
nav_order: 2
description: "Quick start guide for Amazon Chat Completions Server"
---

# Getting Started
{: .no_toc }

This guide will help you get the Amazon Chat Completions Server up and running quickly.
{: .fs-6 .fw-300 }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Prerequisites

Before you begin, ensure you have:

- **Python 3.8+** installed
- **uv** package manager (recommended) or pip
- **API keys** for the services you want to use:
  - OpenAI API key (for OpenAI models)
  - AWS credentials (for Bedrock models)

### Installing uv

If you don't have `uv` installed:

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or with pip
pip install uv
```

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/teabranch/amazon-chat-completions-server.git
cd amazon-chat-completions-server
```

### 2. Install the Package

```bash
# Install in development mode
uv pip install -e .

# Or with pip
pip install -e .
```

### 3. Verify Installation

```bash
amazon-chat --version
```

---

## Configuration

### Interactive Configuration

The easiest way to configure the server is using the interactive setup:

```bash
amazon-chat config set
```

This will prompt you for:

- **OpenAI API Key** (for OpenAI models)
- **Server API Key** (for authentication)
- **AWS Credentials** (for Bedrock models)
- **Default Settings** (model, region, etc.)

### Manual Configuration

Alternatively, create a `.env` file in your project directory:

```env
# Required
OPENAI_API_KEY=sk-your_openai_api_key
API_KEY=your-server-api-key

# AWS Configuration (choose one method)
# Method 1: Static credentials
AWS_ACCESS_KEY_ID=your_aws_access_key_id
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
AWS_REGION=us-east-1

# Method 2: AWS Profile
AWS_PROFILE=your_aws_profile
AWS_REGION=us-east-1

# Optional settings
DEFAULT_OPENAI_MODEL=gpt-4o-mini
LOG_LEVEL=INFO
```

### AWS Authentication Options

The server supports multiple AWS authentication methods:

1. **Static Credentials** - Direct access key and secret
2. **AWS Profile** - Use AWS CLI profiles
3. **Role Assumption** - Assume IAM roles
4. **Instance Profiles** - For EC2/ECS deployments
5. **Web Identity Tokens** - For Kubernetes/OIDC

For detailed AWS authentication setup, see the [AWS Authentication Guide](guides/aws-authentication).

---

## Starting the Server

### Basic Server Start

```bash
amazon-chat serve
```

This starts the server on `http://localhost:8000`.

### Production Server Start

```bash
amazon-chat serve --host 0.0.0.0 --port 8000 --workers 4
```

### Development Server Start

```bash
amazon-chat serve --reload --log-level debug
```

---

## First API Call

Once the server is running, test it with a simple API call:

### Using curl

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [
      {"role": "user", "content": "Hello! How are you?"}
    ],
    "stream": false
  }'
```

### Using Python

```python
import requests

response = requests.post(
    "http://localhost:8000/v1/chat/completions",
    headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer your-api-key"
    },
    json={
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "user", "content": "Hello! How are you?"}
        ],
        "stream": False
    }
)

print(response.json())
```

---

## Interactive Chat

Try the built-in chat interface:

```bash
amazon-chat chat --model gpt-4o-mini
```

This starts an interactive chat session where you can:

- Chat with the AI
- Switch models with `/model <model-name>`
- Change settings with `/settings`
- Save conversations with `/save <filename>`
- Get help with `/help`

---

## Testing Different Formats

The unified endpoint supports multiple input/output formats:

### OpenAI Format (Default)

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

### Bedrock Claude Format

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "anthropic_version": "bedrock-2023-05-31",
    "model": "anthropic.claude-3-haiku-20240307-v1:0",
    "max_tokens": 1000,
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

### Format Conversion

Convert between formats using the `target_format` parameter:

```bash
# OpenAI input → Bedrock Claude output
curl -X POST "http://localhost:8000/v1/chat/completions?target_format=bedrock_claude" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

---

## Health Checks

Verify the server is running properly:

```bash
# General health check
curl http://localhost:8000/health

# Unified endpoint health check
curl http://localhost:8000/v1/chat/completions/health

# List available models
curl -H "Authorization: Bearer your-api-key" \
     http://localhost:8000/v1/models
```

---

## Next Steps

Now that you have the server running:

1. **Explore the API** - Check out the [API Reference](api-reference) for complete documentation
2. **Use the CLI** - Learn more CLI commands in the [CLI Reference](cli-reference)
3. **Integrate with your app** - See programming examples in the [Usage Guide](guides/usage)
4. **Configure AWS** - Set up Bedrock access with the [AWS Authentication Guide](guides/aws-authentication)
5. **Understand the architecture** - Learn how it works in the [Architecture Guide](guides/architecture)

---

## Troubleshooting

### Common Issues

**Server won't start:**
- Check that the port isn't already in use
- Verify your configuration with `amazon-chat config show`
- Check logs for specific error messages

**API calls fail:**
- Verify your API key is correct
- Check that the server is running on the expected port
- Ensure your request format is valid

**AWS/Bedrock errors:**
- Verify AWS credentials are configured correctly
- Check that you have the necessary IAM permissions
- Ensure the AWS region is set correctly

### Getting Help

- Check the [API Reference](api-reference) for detailed endpoint documentation
- Review the [CLI Reference](cli-reference) for command-line usage
- Look at the [Usage Guide](guides/usage) for programming examples
- Open an issue on [GitHub](https://github.com/teabranch/amazon-chat-completions-server/issues) if you need help

---

## Configuration Reference

For a complete list of configuration options, see your `.env` file or run:

```bash
amazon-chat config show
```

Key configuration variables:

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key | For OpenAI models |
| `API_KEY` | Server authentication key | Yes |
| `AWS_REGION` | AWS region | For Bedrock models |
| `AWS_PROFILE` | AWS profile name | Alternative to static credentials |
| `DEFAULT_OPENAI_MODEL` | Default OpenAI model | No |
| `LOG_LEVEL` | Logging level | No | 