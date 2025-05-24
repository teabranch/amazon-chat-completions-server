# Usage Guide

This guide explains how to use the Amazon Chat Completions Server library in your Python projects.

## 1. Prerequisites

* Python 3.12+

* Installed dependencies (see `pyproject.toml` or `requirements.txt` if generated).
   You can install with `uv pip install .` in the project root.

* A `.env` file in your project root with the necessary API keys and configurations. See [.env.example](../../.env.example) for the template.

Example `.env` content for **OpenAI and AWS Bedrock (using static keys)**:

```env
OPENAI_API_KEY="sk-your_openai_api_key"
AWS_ACCESS_KEY_ID="your_aws_access_key_id"
AWS_SECRET_ACCESS_KEY="your_aws_secret_access_key"
AWS_REGION_NAME="us-east-1"
LOG_LEVEL="INFO"
```

Example `.env` content for **OpenAI and AWS Bedrock (using an AWS profile)**:

```env
OPENAI_API_KEY="sk-your_openai_api_key"
AWS_PROFILE_NAME="your_bedrock_profile"
AWS_REGION_NAME="us-east-1"
LOG_LEVEL="INFO"
```

If using `AWS_PROFILE_NAME`, ensure the profile is correctly set up in your `~/.aws/credentials` or `~/.aws/config` file. If running in an AWS environment with an IAM instance profile or task role, you might only need `AWS_REGION_NAME` for Bedrock, as Boto3 will attempt to use the role credentials automatically.

## 2. Importing and Initialization

Most interactions will start with the `LLMServiceFactory` and the `Message` model.

```python
import asyncio
from src.llm_integrations.core.models import Message
from src.llm_integrations.services.llm_service_factory import LLMServiceFactory
from src.llm_integrations.core.exceptions import LLMIntegrationError, ConfigurationError

# The config_loader and logger_setup are typically imported by other modules,
# so their setup is handled automatically when you import from the library.
# For explicit setup if needed (usually not): 
# from src.llm_integrations.utils import config_loader, logger_setup
```

## 3. Getting an LLM Service

Use the `LLMServiceFactory.get_service()` method to obtain a service instance for a specific provider and model.

```python
# For OpenAI (e.g., GPT-4o mini)
# Ensure OPENAI_API_KEY is in your .env
try:
    openai_service = LLMServiceFactory.get_service(provider_name="openai", model_id="gpt-4o-mini")
except ConfigurationError as e:
    print(f"OpenAI Config Error: {e}")
    openai_service = None

# For AWS Bedrock - Claude (e.g., Claude 3 Haiku)
# Ensure AWS credentials and region are in your .env
try:
    # You can use generic model names defined in bedrock_models.py or specific Bedrock model ARNs/IDs.
    bedrock_claude_service = LLMServiceFactory.get_service(provider_name="bedrock", model_id="claude-3-haiku")
    # Example with a more specific ID:
    # bedrock_claude_service = LLMServiceFactory.get_service(
    #     provider_name="bedrock", 
    #     model_id="anthropic.claude-3-haiku-20240307-v1:0"
    # )
except ConfigurationError as e:
    print(f"Bedrock Config Error: {e}")
    bedrock_claude_service = None

# For AWS Bedrock - Titan (e.g., Titan Text Express)
try:
    bedrock_titan_service = LLMServiceFactory.get_service(provider_name="bedrock", model_id="titan-text-express-v1")
except ConfigurationError as e:
    print(f"Bedrock Config Error: {e}")
    bedrock_titan_service = None
```

The factory caches service instances, so repeated calls with the same arguments will return the same instance.

## 4. Making Chat Completion Requests

Once you have a service instance, you can call the `chat_completion` method.

### a) Non-Streaming Request

```python
async def make_non_streaming_request(service, service_name):
    if not service:
        print(f"Skipping non-streaming request for {service_name} as service is not available.")
        return

    messages = [
        Message(role="system", content="You are a helpful assistant."),
        Message(role="user", content="What is the weather like in London today?")
    ]

    try:
        print(f"\n--- {service_name} Non-Streaming Example ---")
        response = await service.chat_completion(
            messages=messages,
            max_tokens=100,
            temperature=0.7
        )
        
        if response.choices and response.choices[0].message:
            print(f"Response from {service_name}: {response.choices[0].message.content}")
            if response.usage:
                print(f"Usage: Prompt Tokens={response.usage.prompt_tokens}, Completion Tokens={response.usage.completion_tokens}")
        else:
            print(f"Error: No valid response choices from {service_name}.")
            
    except LLMIntegrationError as e:
        print(f"LLM Error with {service_name}: {e}")
    except Exception as e:
        print(f"Unexpected error with {service_name}: {e}")

# Example calls:
# if openai_service:
#     asyncio.run(make_non_streaming_request(openai_service, "OpenAI"))
# if bedrock_claude_service:
#     asyncio.run(make_non_streaming_request(bedrock_claude_service, "Bedrock Claude"))
```

### b) Streaming Request

```python
async def make_streaming_request(service, service_name):
    if not service:
        print(f"Skipping streaming request for {service_name} as service is not available.")
        return

    messages = [
        Message(role="system", content="You are a travel planning assistant."),
        Message(role="user", content="Suggest three fun activities for a day trip to Paris.")
    ]

    try:
        print(f"\n--- {service_name} Streaming Example ---")
        print(f"Response from {service_name}: ", end="")
        full_response_content = ""
        
        async for chunk in service.chat_completion(
            messages=messages,
            max_tokens=200,
            temperature=0.8,
            stream=True
        ):
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                print(chunk.choices[0].delta.content, end="", flush=True)
                full_response_content += chunk.choices[0].delta.content
            if chunk.choices and chunk.choices[0].finish_reason:
                print(f"\nStream finished. Reason: {chunk.choices[0].finish_reason}")
        
        print(f"\nFull streamed content: {full_response_content}")
        # Note: Usage information is typically not available per chunk in streaming or 
        # might be in the final non-content chunk for some providers, or aggregated by the client if needed.
        # The standard ChatCompletionChunk does not carry cumulative usage.

    except LLMIntegrationError as e:
        print(f"LLM Error with {service_name} streaming: {e}")
    except Exception as e:
        print(f"Unexpected error with {service_name} streaming: {e}")

# Example calls:
# if openai_service:
#     asyncio.run(make_streaming_request(openai_service, "OpenAI"))
# if bedrock_claude_service:
#     asyncio.run(make_streaming_request(bedrock_claude_service, "Bedrock Claude"))
```

## 5. Tool Use (Function Calling)

For models and providers that support tool use (like OpenAI and Claude 3).

### a) Defining Tools

Define your tools according to the OpenAI tool format:

```python
my_tools = [
    {
        "type": "function",
        "function": {
            "name": "get_current_weather",
            "description": "Get the current weather in a given location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g., San Francisco, CA",
                    },
                    "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                },
                "required": ["location"],
            },
        },
    }
]
```

### b) Making a Request with Tools

Pass the `tools` and optionally `tool_choice` parameters to `chat_completion`.

```python
async def make_tool_use_request(service, service_name):
    if not service:
        print(f"Skipping tool use request for {service_name} as service is not available.")
        return

    messages = [Message(role="user", content="What's the weather like in Boston?")]
    
    try:
        print(f"\n--- {service_name} Tool Use Example ---")
        response = await service.chat_completion(
            messages=messages,
            tools=my_tools,
            tool_choice="auto" # Can be "auto", "none", or {"type": "function", "function": {"name": "my_function"}}
        )

        response_message = response.choices[0].message

        if response_message.tool_calls:
            print(f"{service_name} requested tool call(s):")
            available_functions = {"get_current_weather": lambda location, unit="fahrenheit": f"The weather in {location} is 70 {unit} and sunny."}
            
            # Extend messages with assistant's tool call request
            messages.append(response_message) 

            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                function_to_call = available_functions.get(function_name)
                try:
                    function_args = json.loads(tool_call.function.arguments)
                    print(f"  Tool Call ID: {tool_call.id}, Function: {function_name}, Args: {function_args}")
                    
                    if function_to_call:
                        function_response = function_to_call(
                            location=function_args.get("location"),
                            unit=function_args.get("unit", "fahrenheit") # Default unit
                        )
                        print(f"  Tool Response: {function_response}")
                        # Extend messages with the tool response
                        messages.append(
                            Message(
                                tool_call_id=tool_call.id,
                                role="tool",
                                name=function_name,
                                content=function_response,
                            )
                        )
                    else:
                        print(f"  Error: Function {function_name} not found.")
                        messages.append(Message(tool_call_id=tool_call.id, role="tool", name=function_name, content=f"Error: Function {function_name} not found"))

                except json.JSONDecodeError:
                    print(f"  Error: Could not decode arguments for {function_name}: {tool_call.function.arguments}")
                    messages.append(Message(tool_call_id=tool_call.id, role="tool", name=function_name, content=f"Error: Invalid arguments format for {function_name}"))
            
            # Make a second call with the tool responses included
            print(f"\n--- {service_name} Second Call with Tool Response ---")
            second_response = await service.chat_completion(messages=messages)
            if second_response.choices and second_response.choices[0].message.content:
                print(f"Final response from {service_name}: {second_response.choices[0].message.content}")
            else:
                print(f"{service_name} did not provide a final content response after tool call.")

        else:
            print(f"{service_name} Response (no tool call): {response_message.content}")
            
    except LLMIntegrationError as e:
        print(f"LLM Error with {service_name} tool use: {e}")
    except Exception as e:
        import traceback
        print(f"Unexpected error with {service_name} tool use: {e}\n{traceback.format_exc()}")

# Need to import json for the tool use example
import json 

# Example calls (OpenAI and Bedrock Claude 3 models typically support tools):
# if openai_service:
#     asyncio.run(make_tool_use_request(openai_service, "OpenAI"))
# if bedrock_claude_service: 
#     # Ensure the Bedrock Claude model chosen (e.g. Haiku, Sonnet, Opus) supports tools.
#     # Titan models do not support this tool format directly via the adapter.
#     if "claude" in bedrock_claude_service.adapter.model_id:
#         asyncio.run(make_tool_use_request(bedrock_claude_service, "Bedrock Claude"))
#     else:
#         print("Skipping tool use for selected Bedrock model as it may not be Claude or support tools.")

```

__Note on Tool Use with Bedrock Titan:__
The `TitanStrategy` currently does not support the OpenAI-style `tools` and `tool_choice` parameters. Interactions requiring tool-like behavior with Titan models would need to be formatted as part of the textual conversation prompt.

## 6. Running the Examples

The `src.llm_integrations.main` module provides runnable examples for OpenAI, Bedrock Claude, and Bedrock Titan, covering both streaming and non-streaming use cases. You can run it from the project root:

```bash
python -m src.amazon_chat_completions_server.main
```

Ensure your `.env` file is correctly set up in the project root before running.