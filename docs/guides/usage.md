---
layout: default
title: Usage Guide
parent: Guides
nav_order: 1
description: "Programming examples and integration patterns for Amazon Chat Completions Server"
---

# Usage Guide
{: .no_toc }

This guide provides practical examples for using the Amazon Chat Completions Server library in your Python projects.
{: .fs-6 .fw-300 }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

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
from src.open_amazon_chat_completions_server.core.models import Message
from src.open_amazon_chat_completions_server.services.llm_service_factory import LLMServiceFactory
from src.open_amazon_chat_completions_server.core.exceptions import LLMIntegrationError

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
                        "url": "https://example.com/image.jpg"
                    }
                }
            ]
        )
    ]

    response = await openai_service.chat_completion(
        messages=messages,
        max_tokens=200
    )
    
    print(f"Image analysis: {response.choices[0].message.content}")

asyncio.run(image_analysis())
```

### Cross-Provider Usage

```python
async def cross_provider_example():
    """Example showing how to use different providers for different tasks"""
    
    # Use OpenAI for general chat
    openai_messages = [
        Message(role="user", content="Explain quantum computing in simple terms")
    ]
    
    openai_response = await openai_service.chat_completion(
        messages=openai_messages,
        max_tokens=150
    )
    
    print("OpenAI Response:")
    print(openai_response.choices[0].message.content)
    print()
    
    # Use Bedrock Claude for analysis
    bedrock_messages = [
        Message(role="user", content="Analyze the pros and cons of remote work")
    ]
    
    bedrock_response = await bedrock_service.chat_completion(
        messages=bedrock_messages,
        max_tokens=200
    )
    
    print("Bedrock Claude Response:")
    print(bedrock_response.choices[0].message.content)

asyncio.run(cross_provider_example())
```

## Error Handling

### Comprehensive Error Handling

```python
from src.open_amazon_chat_completions_server.core.exceptions import (
    LLMIntegrationError,
    AuthenticationError,
    RateLimitError,
    ModelNotFoundError
)

async def robust_chat_completion():
    messages = [
        Message(role="user", content="Hello, how are you?")
    ]
    
    try:
        response = await openai_service.chat_completion(
            messages=messages,
            max_tokens=100
        )
        return response.choices[0].message.content
        
    except AuthenticationError as e:
        print(f"Authentication failed: {e}")
        # Handle invalid API key
        return None
        
    except RateLimitError as e:
        print(f"Rate limit exceeded: {e}")
        # Implement backoff strategy
        await asyncio.sleep(60)
        return await robust_chat_completion()  # Retry
        
    except ModelNotFoundError as e:
        print(f"Model not available: {e}")
        # Fallback to different model
        return None
        
    except LLMIntegrationError as e:
        print(f"LLM service error: {e}")
        # Log error and handle gracefully
        return None
        
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

# Usage
result = asyncio.run(robust_chat_completion())
if result:
    print(f"Success: {result}")
else:
    print("Request failed")
```

### Retry Logic with Exponential Backoff

```python
import random
from typing import Optional

async def chat_with_retry(
    service,
    messages: list[Message],
    max_retries: int = 3,
    base_delay: float = 1.0
) -> Optional[str]:
    """Chat completion with exponential backoff retry logic"""
    
    for attempt in range(max_retries + 1):
        try:
            response = await service.chat_completion(
                messages=messages,
                max_tokens=100
            )
            return response.choices[0].message.content
            
        except RateLimitError:
            if attempt == max_retries:
                print("Max retries exceeded")
                return None
                
            # Exponential backoff with jitter
            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
            print(f"Rate limited. Retrying in {delay:.2f} seconds...")
            await asyncio.sleep(delay)
            
        except Exception as e:
            print(f"Non-retryable error: {e}")
            return None
    
    return None

# Usage
messages = [Message(role="user", content="Hello!")]
result = await chat_with_retry(openai_service, messages)
```

## Best Practices

### 1. Connection Management

```python
class ChatService:
    """Example service class with proper resource management"""
    
    def __init__(self):
        self.openai_service = LLMServiceFactory.get_service("openai", "gpt-4o-mini")
        self.bedrock_service = LLMServiceFactory.get_service("bedrock", "anthropic.claude-3-haiku-20240307-v1:0")
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Cleanup resources if needed
        pass
    
    async def chat(self, messages: list[Message], provider: str = "openai") -> str:
        service = self.openai_service if provider == "openai" else self.bedrock_service
        
        response = await service.chat_completion(
            messages=messages,
            max_tokens=150
        )
        
        return response.choices[0].message.content

# Usage
async def main():
    async with ChatService() as chat_service:
        messages = [Message(role="user", content="Hello!")]
        response = await chat_service.chat(messages)
        print(response)

asyncio.run(main())
```

### 2. Configuration Management

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class ChatConfig:
    """Configuration class for chat parameters"""
    max_tokens: int = 150
    temperature: float = 0.7
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stream: bool = False

class ConfigurableChat:
    def __init__(self, config: ChatConfig):
        self.config = config
        self.service = LLMServiceFactory.get_service("openai", "gpt-4o-mini")
    
    async def chat(self, messages: list[Message]) -> str:
        response = await self.service.chat_completion(
            messages=messages,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            top_p=self.config.top_p,
            frequency_penalty=self.config.frequency_penalty,
            presence_penalty=self.config.presence_penalty,
            stream=self.config.stream
        )
        
        return response.choices[0].message.content

# Usage
config = ChatConfig(max_tokens=200, temperature=0.8)
chat = ConfigurableChat(config)

messages = [Message(role="user", content="Tell me a joke")]
response = await chat.chat(messages)
```

### 3. Conversation Management

```python
class Conversation:
    """Manage conversation history and context"""
    
    def __init__(self, system_prompt: Optional[str] = None):
        self.messages: list[Message] = []
        if system_prompt:
            self.messages.append(Message(role="system", content=system_prompt))
        
        self.service = LLMServiceFactory.get_service("openai", "gpt-4o-mini")
    
    def add_user_message(self, content: str):
        """Add a user message to the conversation"""
        self.messages.append(Message(role="user", content=content))
    
    def add_assistant_message(self, content: str):
        """Add an assistant message to the conversation"""
        self.messages.append(Message(role="assistant", content=content))
    
    async def get_response(self, max_tokens: int = 150) -> str:
        """Get AI response and add it to conversation history"""
        response = await self.service.chat_completion(
            messages=self.messages,
            max_tokens=max_tokens
        )
        
        assistant_message = response.choices[0].message.content
        self.add_assistant_message(assistant_message)
        
        return assistant_message
    
    def clear_history(self, keep_system: bool = True):
        """Clear conversation history"""
        if keep_system and self.messages and self.messages[0].role == "system":
            self.messages = [self.messages[0]]
        else:
            self.messages = []
    
    def get_token_count(self) -> int:
        """Estimate token count (simplified)"""
        total_chars = sum(len(msg.content) for msg in self.messages)
        return total_chars // 4  # Rough estimate

# Usage
conversation = Conversation("You are a helpful coding assistant.")

conversation.add_user_message("How do I create a list in Python?")
response1 = await conversation.get_response()
print(f"Assistant: {response1}")

conversation.add_user_message("Can you show me an example?")
response2 = await conversation.get_response()
print(f"Assistant: {response2}")

print(f"Conversation has ~{conversation.get_token_count()} tokens")
```

### 4. Batch Processing

```python
async def batch_process_messages(
    messages_list: list[list[Message]],
    max_concurrent: int = 5
) -> list[str]:
    """Process multiple conversations concurrently"""
    
    semaphore = asyncio.Semaphore(max_concurrent)
    service = LLMServiceFactory.get_service("openai", "gpt-4o-mini")
    
    async def process_single(messages: list[Message]) -> str:
        async with semaphore:
            try:
                response = await service.chat_completion(
                    messages=messages,
                    max_tokens=100
                )
                return response.choices[0].message.content
            except Exception as e:
                return f"Error: {str(e)}"
    
    # Process all conversations concurrently
    tasks = [process_single(messages) for messages in messages_list]
    results = await asyncio.gather(*tasks)
    
    return results

# Usage
conversations = [
    [Message(role="user", content="What is Python?")],
    [Message(role="user", content="What is JavaScript?")],
    [Message(role="user", content="What is Go?")],
]

results = await batch_process_messages(conversations)
for i, result in enumerate(results):
    print(f"Conversation {i+1}: {result}")
```

## Integration Examples

### FastAPI Integration

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class ChatRequest(BaseModel):
    message: str
    model: str = "gpt-4o-mini"

class ChatResponse(BaseModel):
    response: str
    model: str

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        service = LLMServiceFactory.get_service("openai", request.model)
        messages = [Message(role="user", content=request.message)]
        
        response = await service.chat_completion(
            messages=messages,
            max_tokens=150
        )
        
        return ChatResponse(
            response=response.choices[0].message.content,
            model=request.model
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Django Integration

```python
# views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import asyncio

@csrf_exempt
async def chat_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            message = data.get('message')
            
            service = LLMServiceFactory.get_service("openai", "gpt-4o-mini")
            messages = [Message(role="user", content=message)]
            
            response = await service.chat_completion(
                messages=messages,
                max_tokens=150
            )
            
            return JsonResponse({
                'response': response.choices[0].message.content,
                'status': 'success'
            })
            
        except Exception as e:
            return JsonResponse({
                'error': str(e),
                'status': 'error'
            }, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)
```

---

This usage guide provides comprehensive examples for integrating the Amazon Chat Completions Server into your applications. For more specific use cases or advanced configurations, refer to the other guides in this documentation. 