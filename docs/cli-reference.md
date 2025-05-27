---
layout: default
title: CLI Reference
nav_order: 4
description: "Complete CLI reference for Amazon Chat Completions Server"
---

# CLI Reference
{: .no_toc }

Complete reference for the Amazon Chat Completions Server command-line interface.
{: .fs-6 .fw-300 }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Installation

The CLI is installed automatically when you install the package:

```bash
# Install the package
uv pip install -e .

# Verify installation
amazon-chat --version
```

## Global Options

These options are available for all commands:

```bash
amazon-chat [GLOBAL_OPTIONS] COMMAND [COMMAND_OPTIONS]
```

**Global Options:**
- `--version` - Show version and exit
- `--help` - Show help message and exit

## Commands Overview

| Command | Description |
|---------|-------------|
| `chat` | Start an interactive chat session |
| `serve` | Start the API server |
| `config` | Manage configuration settings |
| `models` | List available models |

## Chat Commands

### amazon-chat chat

Start an interactive chat session with an LLM.

```bash
amazon-chat chat [OPTIONS]
```

**Options:**
- `--model TEXT` - Model to use for chat (default: gpt-4o-mini)
- `--server-url TEXT` - Server URL (default: http://localhost:8000)
- `--api-key TEXT` - API key for authentication
- `--system-prompt TEXT` - System prompt to use
- `--temperature FLOAT` - Temperature for responses (0.0-2.0)
- `--max-tokens INTEGER` - Maximum tokens in response
- `--stream / --no-stream` - Enable/disable streaming (default: enabled)
- `--help` - Show help and exit

**Examples:**

```bash
# Basic chat with default model
amazon-chat chat

# Chat with specific model
amazon-chat chat --model gpt-4o

# Chat with custom server
amazon-chat chat --server-url https://my-server.com --api-key my-key

# Chat with custom settings
amazon-chat chat --model gpt-4o-mini --temperature 0.8 --max-tokens 500

# Chat with system prompt
amazon-chat chat --system-prompt "You are a helpful coding assistant"
```

**Interactive Commands:**

Once in a chat session, you can use these commands:

- `/help` - Show available commands
- `/clear` - Clear conversation history
- `/system <prompt>` - Set system prompt
- `/model <model>` - Switch model
- `/settings` - Show current settings
- `/save <filename>` - Save conversation to file
- `/load <filename>` - Load conversation from file
- `/exit` or `/quit` - Exit chat session

**Example Session:**

```
$ amazon-chat chat --model gpt-4o-mini
🚀 Starting chat with gpt-4o-mini
Type '/help' for commands or '/exit' to quit

You: Hello! How are you?
Assistant: Hello! I'm doing well, thank you for asking. I'm here and ready to help you with any questions or tasks you might have. How can I assist you today?

You: /system You are a helpful coding assistant
✅ System prompt updated

You: Can you help me with Python?
Assistant: Absolutely! I'd be happy to help you with Python. I can assist with:

- Writing and debugging code
- Explaining concepts and syntax
- Code reviews and optimization
- Best practices and patterns
- Specific libraries and frameworks

What would you like to work on?

You: /exit
👋 Goodbye!
```

## Server Commands

### amazon-chat serve

Start the API server.

```bash
amazon-chat serve [OPTIONS]
```

**Options:**
- `--host TEXT` - Host to bind to (default: 127.0.0.1)
- `--port INTEGER` - Port to bind to (default: 8000)
- `--reload` - Enable auto-reload for development
- `--workers INTEGER` - Number of worker processes (default: 1)
- `--env-file PATH` - Path to .env file (default: .env)
- `--log-level TEXT` - Log level (debug, info, warning, error, critical)
- `--help` - Show help and exit

**Examples:**

```bash
# Start server with defaults
amazon-chat serve

# Start server on all interfaces
amazon-chat serve --host 0.0.0.0 --port 8000

# Start with auto-reload for development
amazon-chat serve --reload

# Start with multiple workers for production
amazon-chat serve --host 0.0.0.0 --port 8000 --workers 4

# Start with custom env file
amazon-chat serve --env-file production.env

# Start with debug logging
amazon-chat serve --log-level debug
```

**Server Output:**

```
$ amazon-chat serve --host 0.0.0.0 --port 8000
🚀 Starting Amazon Chat Completions Server
📍 Server URL: http://0.0.0.0:8000
📚 API Documentation: http://0.0.0.0:8000/docs
🔑 Authentication: API key required (Authorization: Bearer header)

INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

## Configuration Commands

### amazon-chat config

Manage configuration settings.

```bash
amazon-chat config SUBCOMMAND [OPTIONS]
```

**Subcommands:**
- `set` - Set configuration values interactively
- `show` - Show current configuration
- `get KEY` - Get specific configuration value
- `unset KEY` - Remove configuration value

### amazon-chat config set

Set configuration values interactively.

```bash
amazon-chat config set [OPTIONS]
```

**Options:**
- `--key TEXT` - Specific key to set
- `--value TEXT` - Value to set (use with --key)
- `--file PATH` - Configuration file path (default: .env)
- `--help` - Show help and exit

**Interactive Setup:**

```bash
$ amazon-chat config set
🔧 Amazon Chat Completions Server Configuration

? OpenAI API Key: sk-your-openai-key
? Server API Key (for authentication): your-server-api-key
? AWS Access Key ID (optional): your-aws-access-key
? AWS Secret Access Key (optional): [hidden]
? AWS Region (default: us-east-1): us-east-1
? Default OpenAI Model (default: gpt-4o-mini): gpt-4o-mini
? Log Level (default: INFO): INFO

✅ Configuration saved to .env
```

**Set Specific Value:**

```bash
# Set specific configuration value
amazon-chat config set --key OPENAI_API_KEY --value sk-your-key

# Set with custom file
amazon-chat config set --file production.env
```

### amazon-chat config show

Show current configuration with sensitive values masked.

```bash
amazon-chat config show [OPTIONS]
```

**Options:**
- `--file PATH` - Configuration file path (default: .env)
- `--show-secrets` - Show actual secret values (use with caution)
- `--format TEXT` - Output format: table, json, yaml (default: table)
- `--help` - Show help and exit

**Example Output:**

```bash
$ amazon-chat config show
📋 Current Configuration

┌─────────────────────────┬─────────────────────────┬────────────┐
│ Key                     │ Value                   │ Source     │
├─────────────────────────┼─────────────────────────┼────────────┤
│ OPENAI_API_KEY          │ sk-*********************│ .env       │
│ API_KEY                 │ *********************   │ .env       │
│ AWS_ACCESS_KEY_ID       │ AKIA****************    │ .env       │
│ AWS_SECRET_ACCESS_KEY   │ ************************│ .env       │
│ AWS_REGION              │ us-east-1               │ .env       │
│ DEFAULT_OPENAI_MODEL    │ gpt-4o-mini             │ .env       │
│ LOG_LEVEL               │ INFO                    │ .env       │
└─────────────────────────┴─────────────────────────┴────────────┘

✅ Configuration loaded successfully
🔗 Server URL: http://localhost:8000
📚 Documentation: http://localhost:8000/docs
```

### amazon-chat config get

Get a specific configuration value.

```bash
amazon-chat config get KEY [OPTIONS]
```

**Options:**
- `--file PATH` - Configuration file path (default: .env)
- `--mask / --no-mask` - Mask sensitive values (default: enabled)
- `--help` - Show help and exit

**Examples:**

```bash
# Get specific value (masked)
amazon-chat config get OPENAI_API_KEY
# Output: sk-*********************

# Get value without masking
amazon-chat config get OPENAI_API_KEY --no-mask
# Output: sk-your-actual-key-here

# Get from custom file
amazon-chat config get AWS_REGION --file production.env
# Output: us-west-2
```

### amazon-chat config unset

Remove a configuration value.

```bash
amazon-chat config unset KEY [OPTIONS]
```

**Options:**
- `--file PATH` - Configuration file path (default: .env)
- `--confirm / --no-confirm` - Confirm before removing (default: enabled)
- `--help` - Show help and exit

**Examples:**

```bash
# Remove configuration value
amazon-chat config unset AWS_PROFILE

# Remove without confirmation
amazon-chat config unset AWS_PROFILE --no-confirm
```

## Model Commands

### amazon-chat models

List available models.

```bash
amazon-chat models [OPTIONS]
```

**Options:**
- `--server-url TEXT` - Server URL (default: http://localhost:8000)
- `--api-key TEXT` - API key for authentication
- `--provider TEXT` - Filter by provider (openai, bedrock)
- `--format TEXT` - Output format: table, json, list (default: table)
- `--help` - Show help and exit

**Examples:**

```bash
# List all models
amazon-chat models

# List models from specific server
amazon-chat models --server-url https://my-server.com --api-key my-key

# List only OpenAI models
amazon-chat models --provider openai

# Output as JSON
amazon-chat models --format json
```

**Example Output:**

```bash
$ amazon-chat models
📋 Available Models

┌─────────────────────────────────────┬──────────┬─────────────────────────┐
│ Model ID                            │ Provider │ Description             │
├─────────────────────────────────────┼──────────┼─────────────────────────┤
│ gpt-4o                              │ openai   │ Latest GPT-4 Omni       │
│ gpt-4o-mini                         │ openai   │ Efficient GPT-4 Omni    │
│ gpt-3.5-turbo                       │ openai   │ Fast and efficient      │
│ gpt-4-turbo                         │ openai   │ Advanced GPT-4          │
│ anthropic.claude-3-haiku-20240307   │ bedrock  │ Fast Claude model       │
│ anthropic.claude-3-sonnet-20240229  │ bedrock  │ Balanced Claude model   │
│ anthropic.claude-3-opus-20240229    │ bedrock  │ Most capable Claude     │
│ amazon.titan-text-express-v1        │ bedrock  │ Amazon Titan model      │
└─────────────────────────────────────┴──────────┴─────────────────────────┘

✅ Found 8 available models
```

## Examples

### Complete Workflow Example

```bash
# 1. Set up configuration
amazon-chat config set

# 2. Start the server
amazon-chat serve --host 0.0.0.0 --port 8000 &

# 3. List available models
amazon-chat models

# 4. Start a chat session
amazon-chat chat --model gpt-4o-mini

# 5. In another terminal, test API directly
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"Hello!"}]}'
```

### Development Workflow

```bash
# Start server with auto-reload
amazon-chat serve --reload --log-level debug

# In another terminal, test changes
amazon-chat chat --model gpt-4o-mini --temperature 0.8

# Check configuration
amazon-chat config show

# Test different models
amazon-chat models --provider openai
```

### Production Deployment

```bash
# Set production configuration
amazon-chat config set --file production.env

# Start production server
amazon-chat serve \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --env-file production.env \
  --log-level info
```

## Configuration Files

### .env File Format

The CLI uses `.env` files for configuration:

```bash
# Required
OPENAI_API_KEY=sk-your-openai-api-key
API_KEY=your-server-api-key

# AWS Configuration (choose one method)
# Method 1: Static credentials
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_REGION=us-east-1

# Method 2: AWS Profile
AWS_PROFILE=your-aws-profile
AWS_REGION=us-east-1

# Optional settings
DEFAULT_OPENAI_MODEL=gpt-4o-mini
LOG_LEVEL=INFO
CHAT_SERVER_URL=http://localhost:8000
```

### Environment Variable Priority

Configuration is loaded in this order (later sources override earlier ones):

1. Default values
2. `.env` file
3. Environment variables
4. Command-line options

### Configuration Validation

The CLI validates configuration on startup:

```bash
$ amazon-chat serve
❌ Configuration Error: OPENAI_API_KEY is required
💡 Run 'amazon-chat config set' to configure

$ amazon-chat config set
# ... interactive setup ...

$ amazon-chat serve
✅ Configuration valid
🚀 Starting server...
```

## Error Handling

The CLI provides helpful error messages and suggestions:

```bash
# Missing configuration
$ amazon-chat chat
❌ Error: API_KEY not configured
💡 Run 'amazon-chat config set' to set up authentication

# Server not running
$ amazon-chat chat
❌ Error: Cannot connect to server at http://localhost:8000
💡 Start the server with 'amazon-chat serve'

# Invalid model
$ amazon-chat chat --model invalid-model
❌ Error: Model 'invalid-model' not found
💡 Run 'amazon-chat models' to see available models
```

## Shell Completion

Enable shell completion for better CLI experience:

```bash
# Bash
echo 'eval "$(_AMAZON_CHAT_COMPLETE=bash_source amazon-chat)"' >> ~/.bashrc

# Zsh
echo 'eval "$(_AMAZON_CHAT_COMPLETE=zsh_source amazon-chat)"' >> ~/.zshrc

# Fish
echo '_AMAZON_CHAT_COMPLETE=fish_source amazon-chat | source' >> ~/.config/fish/completions/amazon-chat.fish
```

---

This CLI reference provides complete documentation for all commands and options. For interactive help, use `amazon-chat --help` or `amazon-chat COMMAND --help`. 