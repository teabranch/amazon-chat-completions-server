import pytest
from rich.console import Console
from src.open_amazon_chat_completions_server.cli.formatters import ChatFormatter

@pytest.fixture
def formatter():
    return ChatFormatter(Console())

def test_format_message(formatter):
    """Test message formatting for different roles."""
    # Test user message
    assert "[bold blue]You[/bold blue]" in formatter.format_message("user", "Hello")
    assert "Hello" in formatter.format_message("user", "Hello")
    
    # Test assistant message
    assert "[bold green]Assistant[/bold green]" in formatter.format_message("assistant", "Hi there")
    assert "Hi there" in formatter.format_message("assistant", "Hi there")
    
    # Test system message
    assert "[bold yellow]System[/bold yellow]" in formatter.format_message("system", "System message")
    assert "System message" in formatter.format_message("system", "System message")
    
    # Test tool message
    assert "[bold magenta]Tool[/bold magenta]" in formatter.format_message("tool", "Tool response")
    assert "Tool response" in formatter.format_message("tool", "Tool response")

def test_format_code_block(formatter):
    """Test code block formatting."""
    # Test with language
    code = "print('hello')"
    assert "```python" in formatter.format_code_block(code, "python")
    assert code in formatter.format_code_block(code, "python")
    
    # Test without language
    assert "[bold white on black]" in formatter.format_code_block(code)
    assert code in formatter.format_code_block(code)

def test_format_tool_call(formatter):
    """Test tool call formatting."""
    tool_name = "search"
    args = '{"query": "test"}'
    formatted = formatter.format_tool_call(tool_name, args)
    
    assert "[bold magenta]Tool Call:[/bold magenta]" in formatted
    assert tool_name in formatted
    assert "[dim]Arguments:[/dim]" in formatted
    assert args in formatted 