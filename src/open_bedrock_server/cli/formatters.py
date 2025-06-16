from rich.console import Console


class ChatFormatter:
    """Formats chat messages with rich styling."""

    def __init__(self, console: Console | None = None):
        self.console = console or Console()
        self.role_styles = {
            "system": "[bold yellow]System[/bold yellow]",
            "user": "[bold blue]You[/bold blue]",
            "assistant": "[bold green]Assistant[/bold green]",
            "tool": "[bold magenta]Tool[/bold magenta]",
        }

    def format_message(self, role: str, content: str) -> str:
        """Format a message with appropriate styling based on role."""
        role_display = self.role_styles.get(role, f"[bold]{role}[/bold]")
        return f"{role_display}: {content}"

    def format_code_block(self, code: str, language: str = "") -> str:
        """Format a code block with syntax highlighting."""
        if language:
            return f"```{language}\n{code}\n```"
        return f"[bold white on black]\n{code}\n[/bold white on black]"

    def format_tool_call(self, tool_name: str, arguments: str) -> str:
        """Format a tool call with appropriate styling."""
        return (
            f"[bold magenta]Tool Call:[/bold magenta] {tool_name}\n"
            f"[dim]Arguments:[/dim] {arguments}"
        )

    def print_message(self, role: str, content: str):
        """Print a formatted message."""
        self.console.print(self.format_message(role, content))

    def print_streaming_content(self, content: str, end: str = ""):
        """Print streaming content with appropriate styling."""
        self.console.print(content, end=end, highlight=False)
