import requests
from rich.console import Console
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


class CLIErrorHandler:
    """Handles CLI-specific error cases with rich formatting."""

    def __init__(self, console: Console | None = None):
        self.console = console or Console()

    def handle_http_error(self, error: requests.HTTPError):
        """Handle HTTP errors with appropriate messaging."""
        status_code = error.response.status_code
        error_handlers = {
            401: self._handle_auth_error,
            403: self._handle_auth_error,
            404: self._handle_not_found,
            429: self._handle_rate_limit,
            500: self._handle_server_error,
        }
        handler = error_handlers.get(status_code, self._handle_generic_error)
        handler(error)

    def _handle_auth_error(self, error: requests.HTTPError):
        self.console.print("[bold red]Authentication Error[/bold red]")
        self.console.print("Please check your API key or run 'bedrock-chat config set'")

    def _handle_not_found(self, error: requests.HTTPError):
        self.console.print("[bold red]Not Found Error[/bold red]")
        self.console.print(
            "The requested resource was not found. Please check the model name or server URL."
        )

    def _handle_rate_limit(self, error: requests.HTTPError):
        self.console.print("[bold red]Rate Limit Error[/bold red]")
        self.console.print(
            "Too many requests. Please wait a moment before trying again."
        )

    def _handle_server_error(self, error: requests.HTTPError):
        self.console.print("[bold red]Server Error[/bold red]")
        self.console.print("The server encountered an error. Please try again later.")

    def _handle_generic_error(self, error: requests.HTTPError):
        self.console.print(
            f"[bold red]API Error ({error.response.status_code})[/bold red]"
        )
        self.console.print(f"Error details: {error.response.text}")

    def handle_connection_error(self, error: requests.ConnectionError):
        """Handle connection errors."""
        self.console.print("[bold red]Connection Error[/bold red]")
        self.console.print(
            "Could not connect to the server. Please check your internet connection and server URL."
        )

    def handle_timeout_error(self, error: requests.Timeout):
        """Handle timeout errors."""
        self.console.print("[bold red]Timeout Error[/bold red]")
        self.console.print("The request timed out. Please try again.")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type(requests.exceptions.ConnectionError),
    reraise=True,
)
def make_api_request(url: str, method: str = "GET", **kwargs) -> requests.Response:
    """Make an API request with retries on connection errors."""
    response = requests.request(method, url, **kwargs)
    response.raise_for_status()
    return response
