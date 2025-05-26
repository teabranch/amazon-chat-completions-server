# Programming Guide

> 📚 **[← Back to Documentation Hub](README.md)** | **[Main README](../README.md)**

This guide provides practical examples for using the Amazon Chat Completions Server library in your Python projects.

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [Basic Usage](#basic-usage)
- [Advanced Features](#advanced-features)
- [Error Handling](#error-handling)
- [Best Practices](#best-practices)

## Prerequisites

### Installation
```bash
# Install the package
uv pip install -e .

# Or with pip
pip install -e .
```

### Configuration
Create a `.env` file with your API credentials:

```env
# Required
OPENAI_API_KEY="sk-your_openai_api_key"
API_KEY="your-server-api-key"

# AWS Configuration (choose one method)
# Method 1: Static credentials
AWS_ACCESS_KEY_ID="your_aws_access_key_id"
AWS_SECRET_ACCESS_KEY="your_aws_secret_access_key"
AWS_REGION="us-east-1"

# Method 2: AWS Profile
AWS_PROFILE="your_aws_profile"
AWS_REGION="us-east-1"

# Optional
DEFAULT_OPENAI_MODEL="gpt-4o-mini"
LOG_LEVEL="INFO"
```

## Basic Usage

### Getting Started with Services

```python
import asyncio
from src.amazon_chat_completions_server.core.models import Message
from src.amazon_chat_completions_server.services.llm_service_factory import LLMServiceFactory
from src.amazon_chat_completions_server.core.exceptions import LLMIntegrationError

# Get service instances
openai_service = LLMServiceFactory.get_service(
    provider_name="openai", 
    model_id="gpt-4o-mini"
)

bedrock_service = LLMServiceFactory.get_service(
    provider_name="bedrock", 
    model_id="anthropic.claude-3-haiku-20240307-v1:0"
)
```

### Simple Chat Completion

```python
async def simple_chat():
    messages = [
        Message(role="system", content="You are a helpful assistant."),
        Message(role="user", content="What is the capital of France?")
    ]

    # Non-streaming request
    response = await openai_service.chat_completion(
        messages=messages,
        max_tokens=100,
        temperature=0.7
    )
    
    print(f"Response: {response.choices[0].message.content}")
    print(f"Usage: {response.usage.total_tokens} tokens")

# Run the example
asyncio.run(simple_chat())
```

### Streaming Chat Completion

```python
async def streaming_chat():
    messages = [
        Message(role="user", content="Tell me a short story about a robot.")
    ]

    print("Response: ", end="")
    async for chunk in openai_service.chat_completion(
        messages=messages,
        max_tokens=200,
        temperature=0.8,
        stream=True
    ):
        if chunk.choices and chunk.choices[0].delta.content:
            print(chunk.choices[0].delta.content, end="", flush=True)
    
    print("\n--- Stream complete ---")

asyncio.run(streaming_chat())
```

## Advanced Features

### Tool Calling (Function Calling)

```python
async def tool_calling_example():
    # Define tools
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get current weather for a location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "City name, e.g., 'London, UK'"
                        },
                        "unit": {
                            "type": "string",
                            "enum": ["celsius", "fahrenheit"],
                            "description": "Temperature unit"
                        }
                    },
                    "required": ["location"]
                }
            }
        }
    ]

    messages = [
        Message(role="user", content="What's the weather like in Tokyo?")
    ]

    response = await openai_service.chat_completion(
        messages=messages,
        tools=tools,
        tool_choice="auto",
        max_tokens=150
    )

    # Check if the model wants to call a tool
    if response.choices[0].message.tool_calls:
        tool_call = response.choices[0].message.tool_calls[0]
        print(f"Tool called: {tool_call.function.name}")
        print(f"Arguments: {tool_call.function.arguments}")
        
        # Simulate tool execution
        tool_result = {"temperature": "22°C", "condition": "sunny"}
        
        # Add tool response to conversation
        messages.extend([
            response.choices[0].message,  # Assistant's tool call
            Message(
                role="tool",
                content=str(tool_result),
                tool_call_id=tool_call.id
            )
        ])
        
        # Get final response
        final_response = await openai_service.chat_completion(
            messages=messages,
            max_tokens=100
        )
        print(f"Final response: {final_response.choices[0].message.content}")

asyncio.run(tool_calling_example())
```

### Multimodal Content (Images)

```python
async def image_analysis():
    # For models that support vision (like GPT-4o)
    messages = [
        Message(
            role="user",
            content=[
                {"type": "text", "text": "What do you see in this image?"},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD..."
                    }
                }
            ]
        )
    ]

    response = await openai_service.chat_completion(
        messages=messages,
        model_id="gpt-4o",  # Vision-capable model
        max_tokens=200
    )
    
    print(f"Image analysis: {response.choices[0].message.content}")

# asyncio.run(image_analysis())
```

### Multi-turn Conversations

```python
async def conversation_example():
    conversation = [
        Message(role="system", content="You are a helpful math tutor."),
        Message(role="user", content="Can you help me with algebra?")
    ]

    # First exchange
    response1 = await openai_service.chat_completion(
        messages=conversation,
        max_tokens=100
    )
    
    conversation.append(response1.choices[0].message)
    print(f"Assistant: {response1.choices[0].message.content}")

    # Continue conversation
    conversation.append(
        Message(role="user", content="What is the quadratic formula?")
    )

    response2 = await openai_service.chat_completion(
        messages=conversation,
        max_tokens=150
    )
    
    print(f"Assistant: {response2.choices[0].message.content}")

asyncio.run(conversation_example())
```

## Error Handling

### Comprehensive Error Handling

```python
from src.amazon_chat_completions_server.core.exceptions import (
    LLMIntegrationError,
    ConfigurationError,
    APIConnectionError,
    AuthenticationError,
    RateLimitError,
    ModelNotFoundError
)

async def robust_chat_completion():
    try:
        service = LLMServiceFactory.get_service("openai", "gpt-4o-mini")
        
        messages = [
            Message(role="user", content="Hello, world!")
        ]
        
        response = await service.chat_completion(
            messages=messages,
            max_tokens=100
        )
        
        return response.choices[0].message.content
        
    except ConfigurationError as e:
        print(f"Configuration error: {e}")
        print("Check your .env file and API keys")
        
    except AuthenticationError as e:
        print(f"Authentication failed: {e}")
        print("Verify your API keys are correct")
        
    except RateLimitError as e:
        print(f"Rate limit exceeded: {e}")
        print("Wait before making more requests")
        
    except ModelNotFoundError as e:
        print(f"Model not found: {e}")
        print("Check if the model ID is correct")
        
    except APIConnectionError as e:
        print(f"Connection error: {e}")
        print("Check your internet connection")
        
    except LLMIntegrationError as e:
        print(f"LLM integration error: {e}")
        
    except Exception as e:
        print(f"Unexpected error: {e}")
        
    return None

result = asyncio.run(robust_chat_completion())
```

### Retry Logic

```python
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def resilient_chat_completion(service, messages):
    """Chat completion with automatic retries for transient errors."""
    try:
        return await service.chat_completion(
            messages=messages,
            max_tokens=100
        )
    except (APIConnectionError, RateLimitError) as e:
        print(f"Retrying due to: {e}")
        raise  # Re-raise to trigger retry
    except (AuthenticationError, ModelNotFoundError) as e:
        print(f"Non-retryable error: {e}")
        return None  # Don't retry for these errors

# Usage
messages = [Message(role="user", content="Hello!")]
response = await resilient_chat_completion(openai_service, messages)
```

## Best Practices

### 1. Service Instance Management

```python
# ✅ Good: Reuse service instances
class ChatBot:
    def __init__(self):
        self.service = LLMServiceFactory.get_service("openai", "gpt-4o-mini")
    
    async def chat(self, message: str) -> str:
        messages = [Message(role="user", content=message)]
        response = await self.service.chat_completion(messages=messages)
        return response.choices[0].message.content

# ❌ Avoid: Creating new services for each request
async def bad_chat(message: str) -> str:
    service = LLMServiceFactory.get_service("openai", "gpt-4o-mini")  # Inefficient
    messages = [Message(role="user", content=message)]
    response = await service.chat_completion(messages=messages)
    return response.choices[0].message.content
```

### 2. Token Management

```python
async def token_aware_chat():
    messages = [
        Message(role="user", content="Write a long essay about AI.")
    ]
    
    response = await openai_service.chat_completion(
        messages=messages,
        max_tokens=500,  # Set appropriate limits
        temperature=0.7
    )
    
    if response.usage:
        print(f"Tokens used: {response.usage.total_tokens}")
        if response.usage.total_tokens > 1000:
            print("Warning: High token usage!")
    
    return response
```

### 3. Streaming for Long Responses

```python
async def efficient_long_response():
    messages = [
        Message(role="user", content="Explain quantum computing in detail.")
    ]
    
    # Use streaming for long responses to improve perceived performance
    full_response = ""
    async for chunk in openai_service.chat_completion(
        messages=messages,
        max_tokens=1000,
        stream=True
    ):
        if chunk.choices and chunk.choices[0].delta.content:
            content = chunk.choices[0].delta.content
            print(content, end="", flush=True)
            full_response += content
    
    return full_response
```

### 4. Configuration Management

```python
from src.amazon_chat_completions_server.utils.config_loader import AppConfig

# Access configuration
config = AppConfig()

# Use configuration in your application
async def configured_chat():
    model = config.DEFAULT_OPENAI_MODEL or "gpt-4o-mini"
    service = LLMServiceFactory.get_service("openai", model)
    
    messages = [Message(role="user", content="Hello!")]
    response = await service.chat_completion(messages=messages)
    
    return response
```

### 5. Logging

```python
import logging
from src.amazon_chat_completions_server.utils.logger_setup import setup_logger

# Set up logging
logger = setup_logger(__name__)

async def logged_chat_completion():
    try:
        logger.info("Starting chat completion request")
        
        messages = [Message(role="user", content="Hello!")]
        response = await openai_service.chat_completion(messages=messages)
        
        logger.info(f"Chat completion successful, tokens: {response.usage.total_tokens}")
        return response
        
    except Exception as e:
        logger.error(f"Chat completion failed: {e}")
        raise
```

## Complete Example

Here's a complete example that demonstrates multiple features:

```python
import asyncio
import logging
from src.amazon_chat_completions_server.core.models import Message
from src.amazon_chat_completions_server.services.llm_service_factory import LLMServiceFactory
from src.amazon_chat_completions_server.core.exceptions import LLMIntegrationError

class ChatAssistant:
    def __init__(self, provider="openai", model="gpt-4o-mini"):
        self.service = LLMServiceFactory.get_service(provider, model)
        self.conversation_history = []
        self.logger = logging.getLogger(__name__)
    
    async def chat(self, user_message: str, stream: bool = False) -> str:
        """Send a message and get a response."""
        # Add user message to history
        self.conversation_history.append(
            Message(role="user", content=user_message)
        )
        
        try:
            if stream:
                return await self._stream_response()
            else:
                return await self._get_response()
                
        except LLMIntegrationError as e:
            self.logger.error(f"Chat error: {e}")
            return f"Sorry, I encountered an error: {e}"
    
    async def _get_response(self) -> str:
        """Get a non-streaming response."""
        response = await self.service.chat_completion(
            messages=self.conversation_history,
            max_tokens=500,
            temperature=0.7
        )
        
        assistant_message = response.choices[0].message
        self.conversation_history.append(assistant_message)
        
        return assistant_message.content
    
    async def _stream_response(self) -> str:
        """Get a streaming response."""
        full_response = ""
        
        async for chunk in self.service.chat_completion(
            messages=self.conversation_history,
            max_tokens=500,
            temperature=0.7,
            stream=True
        ):
            if chunk.choices and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                print(content, end="", flush=True)
                full_response += content
        
        # Add to conversation history
        self.conversation_history.append(
            Message(role="assistant", content=full_response)
        )
        
        return full_response
    
    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []

# Usage example
async def main():
    assistant = ChatAssistant()
    
    # Simple chat
    response1 = await assistant.chat("Hello! What can you help me with?")
    print(f"Assistant: {response1}")
    
    # Streaming chat
    print("\nAssistant (streaming): ", end="")
    response2 = await assistant.chat("Tell me a joke.", stream=True)
    print()  # New line after streaming
    
    # Continue conversation
    response3 = await assistant.chat("Can you explain that joke?")
    print(f"Assistant: {response3}")

if __name__ == "__main__":
    asyncio.run(main())
```

This programming guide provides practical examples for integrating the Amazon Chat Completions Server into your applications. For API server usage, see the [main README](../README.md) and [API Reference](api-reference.md).