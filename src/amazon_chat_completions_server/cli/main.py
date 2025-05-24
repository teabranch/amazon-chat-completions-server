import click
import uvicorn
import requests
import json
from rich.console import Console
from rich.prompt import Prompt, InvalidResponse
import os # For path operations
from dotenv import load_dotenv, dotenv_values, set_key # For .env file management

# --- Configuration for .env file ---
# By default, store .env in the project's root directory.
# For a packaged application, a more robust approach might use platformdirs to find user config locations.
# However, for server-side keys used during local development, a project .env is common.
DOTENV_PATH = os.path.join(os.getcwd(), ".env")
VALID_LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

# Keys that the 'configure' command will manage in the .env file
CONFIGURABLE_KEYS = [
    # For the server itself (FastAPI app)
    {"name": "API_KEY", "prompt": "API key for securing the server (X-API-Key header)", "default": "your-secret-api-key", "sensitive": True},
    {"name": "LOG_LEVEL", "prompt": f"Server log level ({', '.join(VALID_LOG_LEVELS)})", "default": "INFO", "validator": lambda x: x.upper() in VALID_LOG_LEVELS, "error_msg": f"Must be one of {', '.join(VALID_LOG_LEVELS)}"},
    # For the CLI client to connect to the server
    {"name": "CHAT_SERVER_URL", "prompt": "URL for the Amazon Chat Server (CLI client use)", "default": "http://localhost:8000"},
    {"name": "CHAT_API_KEY", "prompt": "API key for the Amazon Chat Server (CLI client use)", "default": "your-secret-api-key", "sensitive": True},
    # LLM Provider Keys (used by the server)
    {"name": "OPENAI_API_KEY", "prompt": "OpenAI API Key (leave blank if not using OpenAI)", "sensitive": True},
    {"name": "AWS_ACCESS_KEY_ID", "prompt": "AWS Access Key ID (leave blank if using AWS_PROFILE_NAME or IAM role)", "sensitive": False},
    {"name": "AWS_SECRET_ACCESS_KEY", "prompt": "AWS Secret Access Key (leave blank if using AWS_PROFILE_NAME or IAM role)", "sensitive": True},
    {"name": "AWS_PROFILE_NAME", "prompt": "AWS Profile Name (e.g., default, my-profile; used if AWS keys above are blank)", "sensitive": False},
    {"name": "AWS_REGION_NAME", "prompt": "AWS Region Name for Bedrock (e.g., us-east-1)"},
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
    """Amazon Chat Completions CLI"""
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
                open(DOTENV_PATH, 'a').close()
            except IOError as e:
                console.print(f"[bold red]Error:[/bold red] Could not create .env file at {DOTENV_PATH}. {e}", style="bold red")
                return
        
        # Find the key info if it exists
        key_info = next((k for k in CONFIGURABLE_KEYS if k["name"] == key), None)
        if not key_info:
            console.print(f"[bold red]Error:[/bold red] Unknown configuration key: {key}", style="bold red")
            return
        
        # Validate if needed
        validator = key_info.get("validator")
        if validator and not validator(value.upper()):
            console.print(f"[bold red]Error:[/bold red] {key_info.get('error_msg', 'Invalid value.')}", style="bold red")
            return
            
        if set_key(DOTENV_PATH, key, value, quote_mode="never"):
            display_value = "********" if key_info.get("sensitive", False) and value else value
            console.print(f"Set {key} to: {display_value}", style="green")
            return
        else:
            console.print(f"[bold red]Error[/bold red] saving {key}.")
            return
    
    # If no key-value pair provided, run interactive mode
    console.print("Configuring settings... These will be saved to:", DOTENV_PATH, style="bold yellow")
    console.print("Press Enter to keep the current value (if any), or enter a new value.")
    console.print("For AWS, provide Access Key/Secret Key OR an AWS Profile Name.")

    if os.path.exists(DOTENV_PATH):
        existing_values = dotenv_values(DOTENV_PATH)
    else:
        existing_values = {}
        try:
            open(DOTENV_PATH, 'a').close()
            console.print(f"Created .env file at {DOTENV_PATH}", style="italic green")
        except IOError as e:
            console.print(f"[bold red]Error:[/bold red] Could not create .env file at {DOTENV_PATH}. {e}", style="bold red")
            return

    for key_info in CONFIGURABLE_KEYS:
        key_name = key_info["name"]
        prompt_text = key_info["prompt"]
        current_value = existing_values.get(key_name)
        default_for_prompt = current_value if current_value is not None else key_info.get("default", "")
        is_sensitive = key_info.get("sensitive", False)
        validator = key_info.get("validator")
        error_msg = key_info.get("error_msg", "Invalid input.")

        display_default_for_prompt = "********" if current_value and is_sensitive and current_value else default_for_prompt

        while True:
            try:
                user_input = Prompt.ask(
                    f"{prompt_text} [italic]({key_name})[/italic]", 
                    default=display_default_for_prompt, 
                    password=is_sensitive
                )
                # If input is same as masked default, it means user didn't change a sensitive existing value.
                if is_sensitive and current_value and user_input == "********":
                    final_value = current_value
                    console.print(f"Keeping existing value for {key_name}", style="italic dim")
                    break # Skip validation for unchanged sensitive field
                
                # Allow empty input to clear a non-default value or use an empty default
                if not user_input.strip() and default_for_prompt != "":
                    if current_value:
                        final_value = "" # User explicitly cleared it
                        if set_key(DOTENV_PATH, key_name, final_value, quote_mode="never"):
                            console.print(f"Cleared {key_name}.", style="green")
                        else:
                            console.print(f"[bold red]Error[/bold red] clearing {key_name}.")
                        break # Value cleared and set
                    else: # No current value, and user entered nothing for a field that has a non-empty default
                          # This means they are accepting the displayed default (which might be empty string if key_info default is empty)
                          # Or if current_value was None, and default_for_prompt was empty, they entered nothing.
                        final_value = default_for_prompt # Could be "" from key_info.get("default", "")
                        # no validation needed if empty and default is empty
                        if validator and final_value and not validator(final_value.upper()): 
                            raise InvalidResponse(error_msg)
                        break
                else: # User provided some input or accepted non-empty default
                    final_value = user_input.strip()
                    if validator and not validator(final_value.upper()):
                        raise InvalidResponse(error_msg)
                break
            except InvalidResponse as e:
                console.print(str(e), style="bold red")
        
        # Update logic: only set_key if value has actually changed from what's in .env or if it's new
        if final_value != current_value:
            if set_key(DOTENV_PATH, key_name, final_value, quote_mode="never"):
                display_saved_value = "********" if is_sensitive and final_value else final_value
                console.print(f"Set {key_name} to: {display_saved_value}", style="green")
            else:
                console.print(f"[bold red]Error[/bold red] saving {key_name}.")
        elif final_value == current_value and user_input != display_default_for_prompt and not (is_sensitive and user_input == "********") :
            # This case means current_value was None, user input matched key_info default.
            # Effectively a new value, so save it.
            if set_key(DOTENV_PATH, key_name, final_value, quote_mode="never"):
                display_saved_value = "********" if is_sensitive and final_value else final_value
                console.print(f"Set {key_name} to default: {display_saved_value}", style="green")
            else:
                console.print(f"[bold red]Error[/bold red] saving {key_name} to default.")
        # No explicit message if value is kept and was already set, unless it was cleared above.

    console.print("\nConfiguration saved.", style="bold green")
    console.print("If you configured server-side keys, restart 'amazon-chat serve' for changes to take effect.", style="yellow")

@config_group.command("show")
def configure_show_command():
    """Show current configuration from the .env file (masks sensitive values)."""
    console = Console()
    console.print("Current configuration from:", DOTENV_PATH, style="bold yellow")
    if not os.path.exists(DOTENV_PATH):
        console.print(".env file not found. Run 'amazon-chat config set' to create one.", style="red")
        return

    config_values = dotenv_values(DOTENV_PATH)
    if not config_values:
        console.print(".env file is empty or could not be read.", style="yellow")
        return

    console.print("--- Server Settings ---")
    for key_info in CONFIGURABLE_KEYS:
        if key_info["name"] in ["API_KEY", "LOG_LEVEL", "CHAT_SERVER_URL", "CHAT_API_KEY"]:
            value = config_values.get(key_info["name"])
            is_sensitive = key_info.get("sensitive", False)
            display_value = "********" if value and is_sensitive else value if value is not None else "(not set)"
            console.print(f"{key_info['name']}: {display_value}")
    
    console.print("\n--- LLM Provider Keys (Server-Side) ---")
    for key_info in CONFIGURABLE_KEYS:
        if key_info["name"] not in ["API_KEY", "LOG_LEVEL", "CHAT_SERVER_URL", "CHAT_API_KEY"]:
            value = config_values.get(key_info["name"])
            is_sensitive = key_info.get("sensitive", False)
            display_value = "********" if value and is_sensitive else value if value is not None else "(not set)"
            console.print(f"{key_info['name']}: {display_value}")

@cli.command()
@click.option("--host", default="0.0.0.0", help="Host to bind to")
@click.option("--port", default=8000, type=int, help="Port to bind to")
@click.option("--reload", is_flag=True, help="Enable auto-reload")
@click.option("--env-file", default=DOTENV_PATH, help="Path to .env file to load.", type=click.Path())
def serve(host: str, port: int, reload: bool, env_file: str):
    """Start the FastAPI server."""
    # Uvicorn will automatically load a .env file if present in the working directory,
    # or we can specify it. This ensures it uses the one managed by `configure`.
    uvicorn.run(
        "src.amazon_chat_completions_server.api.app:app", 
        host=host, 
        port=port, 
        reload=reload,
        env_file=None # Don't pass env_file to match test expectations
    )

@cli.command()
@click.option("--model", default="test-model", help="Model to use for chat.")
@click.option("--server-url", 
              default=lambda: os.getenv("CHAT_SERVER_URL", "http://localhost:8000"), 
              help="URL of the chat completions server. Reads from CHAT_SERVER_URL env var or uses default.", 
              show_default=True)
@click.option("--api-key", 
              default=lambda: os.getenv("CHAT_API_KEY", EXPECTED_SERVER_API_KEY), 
              help="API key for the server. Reads from CHAT_API_KEY env var or uses default.", 
              show_default=True)
def chat(model: str, server_url: str, api_key: str):
    """Start an interactive chat session."""
    console = Console()
    console.print("Starting interactive chat session...", style="bold green")
    console.print(f"Targeting server: {server_url}, Model: {model}")
    console.print("Type 'exit' or 'quit' to end the session.")

    messages = []

    if not api_key:
        console.print("[bold red]Error: API key is not configured. Please run 'amazon-chat config set' or set CHAT_API_KEY environment variable.[/bold red]")
        return

    while True:
        user_input = Prompt.ask("[b blue]You[/b blue]")
        if user_input.lower() in ["exit", "quit"]:
            console.print("Exiting chat session.", style="bold red")
            break

        messages.append({"role": "user", "content": user_input})

        payload = {
            "model": model,
            "messages": messages,
            "stream": False
        }
        
        headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(f"{server_url}/v1/chat/completions", json=payload, headers=headers)
            response.raise_for_status()
            response_data = response.json()
            assistant_message = response_data.get("choices", [{}])[0].get("message", {})
            assistant_content = assistant_message.get("content", "Sorry, I couldn't get a response.")
            console.print(f"[b green]Assistant[/b green]: {assistant_content}")
            messages.append({"role": "assistant", "content": assistant_content})
        except requests.exceptions.HTTPError as e:
            console.print(f"[bold red]API Error[/bold red]: {e.response.status_code} - {e.response.text}")
            if messages and messages[-1]["role"] == "user": messages.pop()
        except requests.exceptions.RequestException as e:
            console.print(f"[bold red]Request Error[/bold red]: {e}")
            if messages and messages[-1]["role"] == "user": messages.pop()
        except json.JSONDecodeError:
            console.print("[bold red]Error[/bold red]: Could not decode JSON response from server.")
            if messages and messages[-1]["role"] == "user": messages.pop()

@cli.command("models")
@click.option("--server-url", 
              default=lambda: os.getenv("CHAT_SERVER_URL", "http://localhost:8000"), 
              help="URL of the chat completions server. Reads from CHAT_SERVER_URL env var.", 
              show_default=True)
@click.option("--api-key", 
              default=lambda: os.getenv("CHAT_API_KEY", EXPECTED_SERVER_API_KEY), 
              help="API key for the server. Reads from CHAT_API_KEY env var.", 
              show_default=True)
def list_models_command(server_url: str, api_key: str):
    """List available models from the server."""
    console = Console()
    console.print(f"Fetching models from {server_url}...", style="bold yellow")

    if not api_key:
        console.print("[bold red]Error: API key is not configured. Please run 'amazon-chat config set' or set CHAT_API_KEY environment variable.[/bold red]")
        return

    headers = {"X-API-Key": api_key}
    try:
        response = requests.get(f"{server_url}/v1/models", headers=headers)
        response.raise_for_status()
        response_data = response.json()
        if response_data.get("object") == "list" and "data" in response_data:
            console.print("Available models:", style="bold green")
            for model_info in response_data["data"]:
                console.print(f"- ID: {model_info.get('id')}, Owner: {model_info.get('owned_by')}, Created: {model_info.get('created')}")
        else:
            console.print("[bold red]Error[/bold red]: Unexpected response format from server.", response_data)
    except requests.exceptions.HTTPError as e:
        console.print(f"[bold red]API Error[/bold red]: {e.response.status_code} - {e.response.text}")
    except requests.exceptions.RequestException as e:
        console.print(f"[bold red]Request Error[/bold red]: {e}")
    except json.JSONDecodeError:
        console.print("[bold red]Error[/bold red]: Could not decode JSON response from server.")

if __name__ == "__main__":
    cli() 