import asyncio
import json
import os  # For path operations

import click
import requests
import uvicorn
from dotenv import dotenv_values, load_dotenv, set_key  # For .env file management
from rich.console import Console
from rich.prompt import InvalidResponse, Prompt
from rich.table import Table

from .chat_history import ChatHistoryManager, ChatSession
from .error_handling import CLIErrorHandler, make_api_request
from .formatters import ChatFormatter

# --- Configuration for .env file ---
# By default, store .env in the project's root directory.
# For a packaged application, a more robust approach might use platformdirs to find user config locations.
# However, for server-side keys used during local development, a project .env is common.
DOTENV_PATH = os.path.join(os.getcwd(), ".env")
VALID_LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

# Keys that the 'configure' command will manage in the .env file
CONFIGURABLE_KEYS = [
    # For the server itself (FastAPI app)
    {
        "name": "API_KEY",
        "prompt": "API key for securing the server (Authorization: Bearer header)",
        "default": "your-secret-api-key",
        "sensitive": True,
    },
    {
        "name": "LOG_LEVEL",
        "prompt": f"Server log level ({', '.join(VALID_LOG_LEVELS)})",
        "default": "INFO",
        "validator": lambda x: x.upper() in VALID_LOG_LEVELS,
        "error_msg": f"Must be one of {', '.join(VALID_LOG_LEVELS)}",
    },
    # For the CLI client to connect to the server
    {
        "name": "CHAT_SERVER_URL",
        "prompt": "URL for the Open Bedrock Server (CLI client use)",
        "default": "http://localhost:8000",
    },
    {
        "name": "CHAT_API_KEY",
        "prompt": "API key for the Open Bedrock Server (CLI client use)",
        "default": "your-secret-api-key",
        "sensitive": True,
    },
    # LLM Provider Keys (used by the server)
    {
        "name": "OPENAI_API_KEY",
        "prompt": "OpenAI API Key (leave blank if not using OpenAI)",
        "sensitive": True,
    },
    {
        "name": "AWS_ACCESS_KEY_ID",
        "prompt": "AWS Access Key ID (leave blank if using AWS_PROFILE or IAM role)",
        "sensitive": False,
    },
    {
        "name": "AWS_SECRET_ACCESS_KEY",
        "prompt": "AWS Secret Access Key (leave blank if using AWS_PROFILE or IAM role)",
        "sensitive": True,
    },
    {
        "name": "AWS_PROFILE",
        "prompt": "AWS Profile Name (e.g., default, my-profile; used if AWS keys above are blank)",
        "sensitive": False,
    },
    {"name": "AWS_REGION", "prompt": "AWS Region Name for Bedrock (e.g., us-east-1)"},
    # S3 Configuration for File Storage
    {
        "name": "S3_FILES_BUCKET",
        "prompt": "S3 bucket name for file uploads (leave blank to disable file upload functionality)",
        "sensitive": False,
    },
    # Enhanced AWS Role Support
    {
        "name": "AWS_ROLE_ARN",
        "prompt": "AWS Role ARN to assume (e.g., arn:aws:iam::123456789012:role/MyRole; leave blank if not using role assumption)",
        "sensitive": False,
    },
    {
        "name": "AWS_EXTERNAL_ID",
        "prompt": "AWS External ID for role assumption (leave blank if not required)",
        "sensitive": False,
    },
    {
        "name": "AWS_ROLE_SESSION_NAME",
                    "prompt": "AWS Role Session Name (default: bedrock-server-session)",
            "default": "bedrock-server-session",
        "sensitive": False,
    },
    {
        "name": "AWS_WEB_IDENTITY_TOKEN_FILE",
        "prompt": "AWS Web Identity Token File path (for OIDC/Kubernetes service accounts; leave blank if not using)",
        "sensitive": False,
    },
    {
        "name": "AWS_ROLE_SESSION_DURATION",
        "prompt": "AWS Role Session Duration in seconds (default: 3600)",
        "default": "3600",
        "validator": lambda x: x.isdigit() and 900 <= int(x) <= 43200,
        "error_msg": "Must be a number between 900 and 43200 seconds (15 minutes to 12 hours)",
    },
    # Add other server or LLM related keys as needed
]
# --- End Configuration for .env file ---

# Load .env file at the start of CLI. This makes env vars available to Click options if needed.
load_dotenv(DOTENV_PATH)

# This will be used as the default for --api-key if CHAT_API_KEY is set in .env
# It needs to be defined after load_dotenv and before it's used in @click.option
EXPECTED_SERVER_API_KEY = os.getenv("CHAT_API_KEY", "your-api-key")


@click.group()
def cli():
    """Open Bedrock Server CLI"""
    pass


@cli.group("config")
def config_group():
    """Manage CLI and server configuration."""
    pass


@config_group.command("set")
@click.argument("key", required=False)
@click.argument("value", required=False)
def configure_set_command(key=None, value=None):
    """Configure API keys and settings. Can be used interactively or with direct key-value pairs."""
    console = Console()

    # If key and value are provided, set directly
    if key and value:
        if not os.path.exists(DOTENV_PATH):
            try:
                open(DOTENV_PATH, "a").close()
            except OSError as e:
                console.print(
                    f"[bold red]Error:[/bold red] Could not create .env file at {DOTENV_PATH}. {e}",
                    style="bold red",
                )
                return

        # Find the key info if it exists
        key_info = next((k for k in CONFIGURABLE_KEYS if k["name"] == key), None)
        if not key_info:
            console.print(
                f"[bold red]Error:[/bold red] Unknown configuration key: {key}",
                style="bold red",
            )
            return

        # Validate if needed
        validator = key_info.get("validator")
        if validator and not validator(value.upper()):
            console.print(
                f"[bold red]Error:[/bold red] {key_info.get('error_msg', 'Invalid value.')}",
                style="bold red",
            )
            return

        if set_key(DOTENV_PATH, key, value, quote_mode="never"):
            display_value = (
                "********" if key_info.get("sensitive", False) and value else value
            )
            console.print(f"Set {key} to: {display_value}", style="green")
            return
        else:
            console.print(f"[bold red]Error[/bold red] saving {key}.")
            return

    # If no key-value pair provided, run interactive mode
    console.print(
        "Configuring settings... These will be saved to:",
        DOTENV_PATH,
        style="bold yellow",
    )
    console.print(
        "Press Enter to keep the current value (if any), or enter a new value."
    )
    console.print("For AWS, provide Access Key/Secret Key OR an AWS Profile Name.")

    if os.path.exists(DOTENV_PATH):
        existing_values = dotenv_values(DOTENV_PATH)
    else:
        existing_values = {}
        try:
            open(DOTENV_PATH, "a").close()
            console.print(f"Created .env file at {DOTENV_PATH}", style="italic green")
        except OSError as e:
            console.print(
                f"[bold red]Error:[/bold red] Could not create .env file at {DOTENV_PATH}. {e}",
                style="bold red",
            )
            return

    for key_info in CONFIGURABLE_KEYS:
        key_name = key_info["name"]
        prompt_text = key_info["prompt"]
        current_value = existing_values.get(key_name)
        default_for_prompt = (
            current_value if current_value is not None else key_info.get("default", "")
        )
        is_sensitive = key_info.get("sensitive", False)
        validator = key_info.get("validator")
        error_msg = key_info.get("error_msg", "Invalid input.")

        display_default_for_prompt = (
            "********"
            if current_value and is_sensitive and current_value
            else default_for_prompt
        )

        while True:
            try:
                user_input = Prompt.ask(
                    f"{prompt_text} [italic]({key_name})[/italic]",
                    default=display_default_for_prompt,
                    password=is_sensitive,
                )
                # If input is same as masked default, it means user didn't change a sensitive existing value.
                if is_sensitive and current_value and user_input == "********":
                    final_value = current_value
                    console.print(
                        f"Keeping existing value for {key_name}", style="italic dim"
                    )
                    break  # Skip validation for unchanged sensitive field

                # Allow empty input to clear a non-default value or use an empty default
                if not user_input.strip() and default_for_prompt != "":
                    if current_value:
                        final_value = ""  # User explicitly cleared it
                        if set_key(
                            DOTENV_PATH, key_name, final_value, quote_mode="never"
                        ):
                            console.print(f"Cleared {key_name}.", style="green")
                        else:
                            console.print(
                                f"[bold red]Error[/bold red] clearing {key_name}."
                            )
                        break  # Value cleared and set
                    else:  # No current value, and user entered nothing for a field that has a non-empty default
                        # This means they are accepting the displayed default (which might be empty string if key_info default is empty)
                        # Or if current_value was None, and default_for_prompt was empty, they entered nothing.
                        final_value = default_for_prompt  # Could be "" from key_info.get("default", "")
                        # no validation needed if empty and default is empty
                        if (
                            validator
                            and final_value
                            and not validator(final_value.upper())
                        ):
                            raise InvalidResponse(error_msg)
                        break
                else:  # User provided some input or accepted non-empty default
                    final_value = user_input.strip()
                    if validator and not validator(final_value.upper()):
                        raise InvalidResponse(error_msg)
                break
            except InvalidResponse as e:
                console.print(str(e), style="bold red")

        # Update logic: only set_key if value has actually changed from what's in .env or if it's new
        if final_value != current_value:
            if set_key(DOTENV_PATH, key_name, final_value, quote_mode="never"):
                display_saved_value = (
                    "********" if is_sensitive and final_value else final_value
                )
                console.print(
                    f"Set {key_name} to: {display_saved_value}", style="green"
                )
            else:
                console.print(f"[bold red]Error[/bold red] saving {key_name}.")
        elif (
            final_value == current_value
            and user_input != display_default_for_prompt
            and not (is_sensitive and user_input == "********")
        ):
            # This case means current_value was None, user input matched key_info default.
            # Effectively a new value, so save it.
            if set_key(DOTENV_PATH, key_name, final_value, quote_mode="never"):
                display_saved_value = (
                    "********" if is_sensitive and final_value else final_value
                )
                console.print(
                    f"Set {key_name} to default: {display_saved_value}", style="green"
                )
            else:
                console.print(
                    f"[bold red]Error[/bold red] saving {key_name} to default."
                )
        # No explicit message if value is kept and was already set, unless it was cleared above.

    console.print("\nConfiguration saved.", style="bold green")
    console.print(
        "If you configured server-side keys, restart 'bedrock-chat serve' for changes to take effect.",
        style="yellow",
    )


@config_group.command("show")
def configure_show_command():
    """Show current configuration from the .env file (masks sensitive values)."""
    console = Console()
    console.print("Current configuration from:", DOTENV_PATH, style="bold yellow")
    if not os.path.exists(DOTENV_PATH):
        console.print(
            ".env file not found. Run 'bedrock-chat config set' to create one.",
            style="red",
        )
        return

    config_values = dotenv_values(DOTENV_PATH)
    if not config_values:
        console.print(".env file is empty or could not be read.", style="yellow")
        return

    console.print("--- Server Settings ---")
    for key_info in CONFIGURABLE_KEYS:
        if key_info["name"] in [
            "API_KEY",
            "LOG_LEVEL",
            "CHAT_SERVER_URL",
            "CHAT_API_KEY",
        ]:
            value = config_values.get(key_info["name"])
            is_sensitive = key_info.get("sensitive", False)
            display_value = (
                "********"
                if value and is_sensitive
                else value
                if value is not None
                else "(not set)"
            )
            console.print(f"{key_info['name']}: {display_value}")

    console.print("\n--- LLM Provider Keys (Server-Side) ---")
    for key_info in CONFIGURABLE_KEYS:
        if key_info["name"] not in [
            "API_KEY",
            "LOG_LEVEL",
            "CHAT_SERVER_URL",
            "CHAT_API_KEY",
        ]:
            value = config_values.get(key_info["name"])
            is_sensitive = key_info.get("sensitive", False)
            display_value = (
                "********"
                if value and is_sensitive
                else value
                if value is not None
                else "(not set)"
            )
            console.print(f"{key_info['name']}: {display_value}")


@cli.command()
@click.option("--host", default="0.0.0.0", help="Host to bind to")
@click.option("--port", default=8000, type=int, help="Port to bind to")
@click.option("--reload", is_flag=True, help="Enable auto-reload")
@click.option(
    "--env-file",
    default=DOTENV_PATH,
    help="Path to .env file to load.",
    type=click.Path(),
)
def serve(host: str, port: int, reload: bool, env_file: str):
    """Start the FastAPI server."""
    # Uvicorn will automatically load a .env file if present in the working directory,
    # or we can specify it. This ensures it uses the one managed by `configure`.
    uvicorn.run(
        "src.open_bedrock_server.api.app:app",
        host=host,
        port=port,
        reload=reload,
        env_file=None,  # Don't pass env_file to match test expectations
    )


@cli.group("history")
def history_group():
    """Manage chat history."""
    pass


@history_group.command("list")
def list_history():
    """List all chat sessions."""
    console = Console()
    manager = ChatHistoryManager()
    sessions = manager.list_sessions()

    if not sessions:
        console.print("No chat sessions found.", style="yellow")
        return

    table = Table(show_header=True)
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("Model")
    table.add_column("Messages")
    table.add_column("Last Updated")

    for session in sessions:
        table.add_row(
            session.id,
            session.name or "(unnamed)",
            session.model,
            str(len(session.messages)),
            session.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
        )
    console.print(table)


@history_group.command("export")
@click.argument("session_id")
@click.option("--output", "-o", type=click.Path(), help="Output file path")
def export_history(session_id: str, output: str):
    """Export a chat session to a file."""
    console = Console()
    manager = ChatHistoryManager()
    try:
        session = manager.load_session(session_id)
        output = output or f"chat_export_{session_id}.json"
        with open(output, "w") as f:
            json.dump(session.to_dict(), f, indent=2)
        console.print(f"Session exported to: {output}", style="green")
    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
    except OSError as e:
        console.print(f"[bold red]Error writing file:[/bold red] {str(e)}")


@history_group.command("delete")
@click.argument("session_id")
def delete_history(session_id: str):
    """Delete a chat session."""
    console = Console()
    manager = ChatHistoryManager()
    try:
        manager.delete_session(session_id)
        console.print(f"Session {session_id} deleted.", style="green")
    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")


@cli.command()
@click.option("--model", default="test-model", help="Model to use for chat.")
@click.option(
    "--server-url",
    default=lambda: os.getenv("CHAT_SERVER_URL", "http://localhost:8000"),
    help="URL of the chat completions server.",
    show_default=True,
)
@click.option(
    "--api-key",
    default=lambda: os.getenv("CHAT_API_KEY", EXPECTED_SERVER_API_KEY),
    help="API key for the server.",
    show_default=True,
)
@click.option(
    "--stream/--no-stream", default=True, help="Enable/disable streaming responses"
)
@click.option("--session", help="Continue an existing chat session")
@click.option("--session-name", help="Name for the new chat session")
def chat(
    model: str,
    server_url: str,
    api_key: str,
    stream: bool,
    session: str,
    session_name: str,
):
    """Start an interactive chat session."""
    asyncio.run(_async_chat(model, server_url, api_key, stream, session, session_name))


async def _async_chat(
    model: str,
    server_url: str,
    api_key: str,
    stream: bool,
    session: str,
    session_name: str,
):
    """Async implementation of the chat command."""
    console = Console()
    formatter = ChatFormatter(console)
    error_handler = CLIErrorHandler(console)
    history_manager = ChatHistoryManager()

    # Load or create session
    chat_session = None
    if session:
        try:
            chat_session = history_manager.load_session(session)
            console.print(
                f"Continuing chat session: {chat_session.name or chat_session.id}",
                style="green",
            )
        except ValueError as e:
            console.print(f"[bold red]Error:[/bold red] {str(e)}")
            return
    else:
        chat_session = ChatSession.create_new(model, session_name)
        history_manager.save_session(chat_session)

    console.print("Starting interactive chat session...", style="bold green")
    console.print(f"Targeting server: {server_url}, Model: {model}")
    console.print("Type 'exit' or 'quit' to end the session.")

    if not api_key:
        console.print(
            "[bold red]Error: API key is not configured. Please run 'bedrock-chat config set' or set CHAT_API_KEY environment variable.[/bold red]"
        )
        return

    async def stream_response(server_url: str, payload: dict, headers: dict):
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    f"{server_url}/v1/chat/completions",
                    json=payload,
                    headers=headers,
                ) as response:
                    if response.status_code != 200:
                        console.print(
                            f"\n[bold red]HTTP Error:[/bold red] {response.status_code} - {response.text}"
                        )
                        return None

                    console.print("[b green]Assistant[/b green]: ", end="")
                    response_content = ""
                    async for chunk in response.aiter_text():
                        if chunk.strip():
                            # Parse SSE format: "data: {json}\n\n"
                            if chunk.startswith("data: "):
                                json_data = chunk[6:].strip()  # Remove "data: " prefix
                                if json_data and json_data != "[DONE]":
                                    try:
                                        chunk_data = json.loads(json_data)
                                        if chunk_data.get("choices") and chunk_data[
                                            "choices"
                                        ][0].get("delta", {}).get("content"):
                                            content = chunk_data["choices"][0]["delta"][
                                                "content"
                                            ]
                                            formatter.print_streaming_content(
                                                content, end=""
                                            )
                                            response_content += content
                                    except json.JSONDecodeError:
                                        pass  # Skip invalid JSON chunks
                    console.print()  # New line after streaming
                    return response_content
        except Exception as e:
            console.print(f"\n[bold red]Streaming Error:[/bold red] {str(e)}")
            return None

    while True:
        try:
            user_input = Prompt.ask("[b blue]You[/b blue]")
            if user_input.lower() in ["exit", "quit"]:
                console.print("Exiting chat session.", style="bold red")
                break

            chat_session.messages.append({"role": "user", "content": user_input})

            payload = {
                "model": model,
                "messages": chat_session.messages,
                "stream": stream,
            }

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            if stream:
                response_content = await stream_response(server_url, payload, headers)
                if response_content:
                    chat_session.messages.append(
                        {"role": "assistant", "content": response_content}
                    )
            else:
                try:
                    response = make_api_request(
                        f"{server_url}/v1/chat/completions",
                        method="POST",
                        json=payload,
                        headers=headers,
                    )
                    response.raise_for_status()
                    response_data = response.json()
                    assistant_message = response_data.get("choices", [{}])[0].get(
                        "message", {}
                    )

                    # Handle tool calls if present
                    if "tool_calls" in assistant_message:
                        formatter.print_message(
                            "assistant", "I need to use some tools to help you."
                        )
                        tool_responses = []
                        for tool_call in assistant_message["tool_calls"]:
                            formatter.print_tool_call(
                                tool_call["function"]["name"],
                                tool_call["function"]["arguments"],
                            )
                            tool_response = Prompt.ask(
                                "[b magenta]Tool Response[/b magenta]"
                            )
                            tool_responses.append(
                                {
                                    "role": "tool",
                                    "name": tool_call["function"]["name"],
                                    "content": tool_response,
                                    "tool_call_id": tool_call["id"],
                                }
                            )
                        chat_session.messages.extend(tool_responses)

                        # Make a follow-up request with tool responses
                        payload["messages"] = chat_session.messages
                        response = make_api_request(
                            f"{server_url}/v1/chat/completions",
                            method="POST",
                            json=payload,
                            headers=headers,
                        )
                        response.raise_for_status()
                        response_data = response.json()
                        assistant_message = response_data.get("choices", [{}])[0].get(
                            "message", {}
                        )

                    assistant_content = assistant_message.get(
                        "content", "Sorry, I couldn't get a response."
                    )
                    formatter.print_message("assistant", assistant_content)
                    chat_session.messages.append(
                        {"role": "assistant", "content": assistant_content}
                    )

                except requests.exceptions.HTTPError as e:
                    error_handler.handle_http_error(e)
                    if (
                        chat_session.messages
                        and chat_session.messages[-1]["role"] == "user"
                    ):
                        chat_session.messages.pop()
                except requests.exceptions.RequestException as e:
                    error_handler.handle_connection_error(e)
                    if (
                        chat_session.messages
                        and chat_session.messages[-1]["role"] == "user"
                    ):
                        chat_session.messages.pop()
                except json.JSONDecodeError:
                    console.print(
                        "[bold red]Error[/bold red]: Could not decode JSON response from server."
                    )
                    if (
                        chat_session.messages
                        and chat_session.messages[-1]["role"] == "user"
                    ):
                        chat_session.messages.pop()

            # Save session after each exchange
            history_manager.update_session(chat_session)

        except KeyboardInterrupt:
            console.print("\nExiting chat session.", style="bold red")
            break
        except Exception as e:
            console.print(f"[bold red]Unexpected error:[/bold red] {str(e)}")
            continue


@cli.command("models")
@click.option(
    "--server-url",
    default=lambda: os.getenv("CHAT_SERVER_URL", "http://localhost:8000"),
    help="URL of the chat completions server. Reads from CHAT_SERVER_URL env var.",
    show_default=True,
)
@click.option(
    "--api-key",
    default=lambda: os.getenv("CHAT_API_KEY", EXPECTED_SERVER_API_KEY),
    help="API key for the server. Reads from CHAT_API_KEY env var.",
    show_default=True,
)
def list_models_command(server_url: str, api_key: str):
    """List available models from the server."""
    console = Console()
    console.print(f"Fetching models from {server_url}...", style="bold yellow")

    if not api_key:
        console.print(
            "[bold red]Error: API key is not configured. Please run 'bedrock-chat config set' or set CHAT_API_KEY environment variable.[/bold red]"
        )
        return

    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        response = requests.get(f"{server_url}/v1/models", headers=headers)
        response.raise_for_status()
        response_data = response.json()
        if response_data.get("object") == "list" and "data" in response_data:
            console.print("Available models:", style="bold green")
            for model_info in response_data["data"]:
                console.print(
                    f"- ID: {model_info.get('id')}, Owner: {model_info.get('owned_by')}, Created: {model_info.get('created')}"
                )
        else:
            console.print(
                "[bold red]Error[/bold red]: Unexpected response format from server.",
                response_data,
            )
    except requests.exceptions.HTTPError as e:
        console.print(
            f"[bold red]API Error[/bold red]: {e.response.status_code} - {e.response.text}"
        )
    except requests.exceptions.RequestException as e:
        console.print(f"[bold red]Request Error[/bold red]: {e}")
    except json.JSONDecodeError:
        console.print(
            "[bold red]Error[/bold red]: Could not decode JSON response from server."
        )


@cli.group("kb")
def kb_group():
    """Manage Bedrock Knowledge Bases."""
    pass


@kb_group.command("list")
@click.option(
    "--server-url",
    default=lambda: os.getenv("CHAT_SERVER_URL", "http://localhost:8000"),
    help="URL of the chat completions server.",
    show_default=True,
)
@click.option(
    "--api-key",
    default=lambda: os.getenv("CHAT_API_KEY", EXPECTED_SERVER_API_KEY),
    help="API key for the server.",
    show_default=True,
)
@click.option(
    "--max-results", default=10, type=int, help="Maximum number of results to return"
)
def list_knowledge_bases(server_url: str, api_key: str, max_results: int):
    """List available knowledge bases."""
    console = Console()

    try:
        url = f"{server_url.rstrip('/')}/v1/knowledge-bases"
        headers = {"Authorization": f"Bearer {api_key}"}
        params = {"max_results": max_results}

        response = make_api_request("GET", url, headers=headers, params=params)

        if not response.get("knowledgeBaseSummaries"):
            console.print("No knowledge bases found.", style="yellow")
            return

        table = Table(title="Knowledge Bases")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Name", style="green")
        table.add_column("Status", style="yellow")
        table.add_column("Created", style="blue")

        for kb in response["knowledgeBaseSummaries"]:
            table.add_row(
                kb.get("knowledgeBaseId", "N/A"),
                kb.get("name", "N/A"),
                kb.get("status", "N/A"),
                kb.get("updatedAt", "N/A")[:10]
                if kb.get("updatedAt")
                else "N/A",  # Just the date part
            )

        console.print(table)

    except Exception as e:
        CLIErrorHandler.handle_error(e, console)


@kb_group.command("get")
@click.argument("knowledge_base_id")
@click.option(
    "--server-url",
    default=lambda: os.getenv("CHAT_SERVER_URL", "http://localhost:8000"),
    help="URL of the chat completions server.",
    show_default=True,
)
@click.option(
    "--api-key",
    default=lambda: os.getenv("CHAT_API_KEY", EXPECTED_SERVER_API_KEY),
    help="API key for the server.",
    show_default=True,
)
def get_knowledge_base(knowledge_base_id: str, server_url: str, api_key: str):
    """Get details of a specific knowledge base."""
    console = Console()

    try:
        url = f"{server_url.rstrip('/')}/v1/knowledge-bases/{knowledge_base_id}"
        headers = {"Authorization": f"Bearer {api_key}"}

        response = make_api_request("GET", url, headers=headers)

        console.print("[bold green]Knowledge Base Details[/bold green]")
        console.print(f"ID: {response.get('knowledgeBaseId', 'N/A')}")
        console.print(f"Name: {response.get('name', 'N/A')}")
        console.print(f"Description: {response.get('description', 'N/A')}")
        console.print(f"Status: {response.get('status', 'N/A')}")
        console.print(f"ARN: {response.get('knowledgeBaseArn', 'N/A')}")
        console.print(f"Role ARN: {response.get('roleArn', 'N/A')}")
        console.print(f"Created: {response.get('createdAt', 'N/A')}")
        console.print(f"Updated: {response.get('updatedAt', 'N/A')}")

        if response.get("failureReasons"):
            console.print("[bold red]Failure Reasons:[/bold red]")
            for reason in response["failureReasons"]:
                console.print(f"  - {reason}")

    except Exception as e:
        CLIErrorHandler.handle_error(e, console)


@kb_group.command("query")
@click.argument("knowledge_base_id")
@click.argument("query")
@click.option(
    "--server-url",
    default=lambda: os.getenv("CHAT_SERVER_URL", "http://localhost:8000"),
    help="URL of the chat completions server.",
    show_default=True,
)
@click.option(
    "--api-key",
    default=lambda: os.getenv("CHAT_API_KEY", EXPECTED_SERVER_API_KEY),
    help="API key for the server.",
    show_default=True,
)
@click.option(
    "--max-results", default=5, type=int, help="Maximum number of results to return"
)
def query_knowledge_base(
    knowledge_base_id: str, query: str, server_url: str, api_key: str, max_results: int
):
    """Query a knowledge base directly (retrieve-only)."""
    console = Console()

    try:
        url = f"{server_url.rstrip('/')}/v1/knowledge-bases/{knowledge_base_id}/query"
        headers = {"Authorization": f"Bearer {api_key}"}
        params = {"query": query, "max_results": max_results}

        response = make_api_request("POST", url, headers=headers, params=params)

        if not response.get("retrievalResults"):
            console.print("No results found for your query.", style="yellow")
            return

        console.print(f"[bold green]Query Results for:[/bold green] {query}")
        console.print()

        for i, result in enumerate(response["retrievalResults"], 1):
            console.print(f"[bold cyan]Result {i}[/bold cyan]")
            console.print(f"Content: {result.get('content', 'N/A')}")

            if result.get("score"):
                console.print(f"Relevance Score: {result['score']:.3f}")

            if result.get("metadata"):
                console.print(f"Metadata: {json.dumps(result['metadata'], indent=2)}")

            console.print("-" * 50)

    except Exception as e:
        CLIErrorHandler.handle_error(e, console)


@kb_group.command("chat")
@click.argument("knowledge_base_id")
@click.option(
    "--model",
    default="anthropic.claude-3-5-haiku-20241022-v1:0",
    help="Model to use for generation.",
)
@click.option(
    "--server-url",
    default=lambda: os.getenv("CHAT_SERVER_URL", "http://localhost:8000"),
    help="URL of the chat completions server.",
    show_default=True,
)
@click.option(
    "--api-key",
    default=lambda: os.getenv("CHAT_API_KEY", EXPECTED_SERVER_API_KEY),
    help="API key for the server.",
    show_default=True,
)
@click.option("--session", help="Continue an existing chat session")
@click.option("--session-name", help="Name for the new chat session")
def kb_chat(
    knowledge_base_id: str,
    model: str,
    server_url: str,
    api_key: str,
    session: str,
    session_name: str,
):
    """Start an interactive chat with a knowledge base (RAG-enhanced)."""
    asyncio.run(
        _async_kb_chat(
            knowledge_base_id, model, server_url, api_key, session, session_name
        )
    )


async def _async_kb_chat(
    knowledge_base_id: str,
    model: str,
    server_url: str,
    api_key: str,
    session: str,
    session_name: str,
):
    """Async implementation of knowledge base chat."""
    console = Console()
    history_manager = ChatHistoryManager()
    error_handler = CLIErrorHandler()

    # Load or create session
    if session:
        try:
            chat_session = history_manager.load_session(session)
            console.print(
                f"Continuing session: {chat_session.name} (ID: {session})",
                style="green",
            )
        except FileNotFoundError:
            console.print(
                f"Session {session} not found. Creating new session.", style="yellow"
            )
            chat_session = ChatSession(
                name=session_name or f"KB Chat {knowledge_base_id}"
            )
    else:
        chat_session = ChatSession(name=session_name or f"KB Chat {knowledge_base_id}")

    console.print("[bold green]Knowledge Base Chat[/bold green]")
    console.print(f"Knowledge Base ID: {knowledge_base_id}")
    console.print(f"Model: {model}")
    console.print(f"Session: {chat_session.name} (ID: {chat_session.id})")
    console.print("Type 'exit' or 'quit' to end the conversation.")
    console.print()

    # Print conversation history if continuing a session
    if chat_session.messages:
        console.print("[bold yellow]Conversation History:[/bold yellow]")
        for msg in chat_session.messages:
            if msg["role"] == "user":
                console.print(f"[bold blue]You:[/bold blue] {msg['content']}")
            elif msg["role"] == "assistant":
                console.print(f"[bold green]Assistant:[/bold green] {msg['content']}")
        console.print()

    try:
        while True:
            user_input = Prompt.ask("[bold blue]You[/bold blue]").strip()

            if user_input.lower() in ["exit", "quit"]:
                break

            if not user_input:
                continue

            # Add user message to session
            chat_session.add_message("user", user_input)

            # Prepare request payload
            payload = {
                "model": model,
                "messages": chat_session.messages,
                "knowledge_base_id": knowledge_base_id,
                "auto_kb": True,
                "stream": False,
                "citation_format": "openai",
            }

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            try:
                url = f"{server_url.rstrip('/')}/v1/chat/completions"
                response = make_api_request("POST", url, headers=headers, json=payload)

                if response.get("choices") and len(response["choices"]) > 0:
                    assistant_message = response["choices"][0]["message"]["content"]

                    # Display assistant response
                    console.print(
                        f"[bold green]Assistant:[/bold green] {assistant_message}"
                    )

                    # Show KB metadata if available
                    if response.get("kb_metadata", {}).get("knowledge_base_used"):
                        metadata = response["kb_metadata"]
                        console.print(
                            f"[dim]✓ Knowledge base used • {metadata.get('citations_count', 0)} citations[/dim]"
                        )

                    console.print()

                    # Add assistant message to session
                    chat_session.add_message("assistant", assistant_message)

                    # Save session
                    history_manager.save_session(chat_session)
                else:
                    console.print(
                        "[bold red]No response received from server[/bold red]"
                    )

            except Exception as e:
                error_handler.handle_error(e, console)
                continue

    except KeyboardInterrupt:
        console.print("\n[yellow]Chat interrupted by user[/yellow]")

    finally:
        # Save session before exit
        history_manager.save_session(chat_session)
        console.print(f"Session saved as: {chat_session.id}")


if __name__ == "__main__":
    cli()
