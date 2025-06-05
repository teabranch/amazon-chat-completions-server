import pytest
import requests
from rich.console import Console
from src.open_amazon_chat_completions_server.cli.error_handling import CLIErrorHandler, make_api_request
from unittest.mock import patch

@pytest.fixture
def error_handler():
    return CLIErrorHandler(Console())

def test_handle_auth_error(error_handler, capsys):
    """Test handling of authentication errors."""
    response = requests.Response()
    response.status_code = 401
    error = requests.HTTPError(response=response)
    error_handler.handle_http_error(error)
    captured = capsys.readouterr()
    assert "Authentication Error" in captured.out
    assert "check your API key" in captured.out

def test_handle_not_found(error_handler, capsys):
    """Test handling of not found errors."""
    response = requests.Response()
    response.status_code = 404
    error = requests.HTTPError(response=response)
    error_handler.handle_http_error(error)
    captured = capsys.readouterr()
    assert "Not Found Error" in captured.out
    assert "check the model name" in captured.out

def test_handle_rate_limit(error_handler, capsys):
    """Test handling of rate limit errors."""
    response = requests.Response()
    response.status_code = 429
    error = requests.HTTPError(response=response)
    error_handler.handle_http_error(error)
    captured = capsys.readouterr()
    assert "Rate Limit Error" in captured.out
    assert "Too many requests" in captured.out

def test_handle_server_error(error_handler, capsys):
    """Test handling of server errors."""
    response = requests.Response()
    response.status_code = 500
    error = requests.HTTPError(response=response)
    error_handler.handle_http_error(error)
    captured = capsys.readouterr()
    assert "Server Error" in captured.out
    assert "try again later" in captured.out

def test_handle_generic_error(error_handler, capsys):
    """Test handling of generic errors."""
    response = requests.Response()
    response.status_code = 418  # I'm a teapot
    error = requests.HTTPError(response=response)
    error_handler.handle_http_error(error)
    captured = capsys.readouterr()
    assert "API Error (418)" in captured.out

def test_handle_connection_error(error_handler, capsys):
    """Test handling of connection errors."""
    error = requests.ConnectionError()
    error_handler.handle_connection_error(error)
    captured = capsys.readouterr()
    assert "Connection Error" in captured.out
    assert "check your internet connection" in captured.out

def test_handle_timeout_error(error_handler, capsys):
    """Test handling of timeout errors."""
    error = requests.Timeout()
    error_handler.handle_timeout_error(error)
    captured = capsys.readouterr()
    assert "Timeout Error" in captured.out
    assert "request timed out" in captured.out

def test_make_api_request_retries():
    """Test that make_api_request retries on connection errors."""
    with patch('requests.request') as mock_request:
        mock_request.side_effect = requests.ConnectionError("Test connection error")

        with pytest.raises(requests.ConnectionError):
            make_api_request("http://test.example.com")

        assert mock_request.call_count == 3  # Should retry 3 times 