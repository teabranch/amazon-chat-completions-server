import pytest
from click.testing import CliRunner
from src.amazon_chat_completions_server.cli.main import cli
import os
import tempfile
import json
from unittest.mock import patch, MagicMock

@pytest.fixture
def runner():
    return CliRunner()

@pytest.fixture
def mock_env_file():
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write('API_KEY=test-key\n')
        f.write('OPENAI_API_KEY=test-openai-key\n')
        f.write('AWS_REGION_NAME=us-east-1\n')
    yield f.name
    os.unlink(f.name)

def test_config_show(runner, mock_env_file):
    with patch('src.amazon_chat_completions_server.cli.main.DOTENV_PATH', mock_env_file):
        result = runner.invoke(cli, ['config', 'show'])
        assert result.exit_code == 0
        assert 'API_KEY' in result.output
        assert 'OPENAI_API_KEY' in result.output
        assert '********' in result.output  # Sensitive values should be masked

def test_config_set(runner):
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        env_file = f.name
    
    try:
        with patch('src.amazon_chat_completions_server.cli.main.DOTENV_PATH', env_file):
            # Test setting individual values
            result = runner.invoke(cli, ['config', 'set', 'API_KEY', 'test-key'])
            assert result.exit_code == 0
            
            # Verify the file was created with correct value
            with open(env_file) as f:
                content = f.read()
                assert 'API_KEY=test-key' in content
    finally:
        os.unlink(env_file)

@patch('requests.post')
def test_chat_command(mock_post, runner):
    # Setup mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{
            "message": {
                "content": "Hello! How can I help you?"
            }
        }]
    }
    mock_post.return_value = mock_response
    
    # Test single message exchange with explicit API key
    result = runner.invoke(cli, ['chat', '--model', 'test-model', '--api-key', 'test-key'], input='Hello\nexit\n')
    
    # Verify the result
    assert result.exit_code == 0
    assert "Hello! How can I help you?" in result.output
    
    # Verify the mock was called correctly
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert kwargs['json']['messages'][0]['content'] == 'Hello'
    assert kwargs['headers']['X-API-Key'] == 'test-key'

@patch('requests.get')
def test_models_command(mock_get, runner):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "object": "list",
        "data": [
            {
                "id": "model-1",
                "owned_by": "openai"
            },
            {
                "id": "model-2",
                "owned_by": "anthropic"
            }
        ]
    }
    mock_get.return_value = mock_response
    
    result = runner.invoke(cli, ['models'])
    assert result.exit_code == 0
    assert "model-1" in result.output
    assert "model-2" in result.output

@patch('uvicorn.run')
def test_serve_command(mock_run, runner):
    # Test the serve command
    result = runner.invoke(cli, ['serve', '--host', 'localhost', '--port', '8000'])
    assert result.exit_code == 0
    
    # Verify uvicorn.run was called with correct arguments
    mock_run.assert_called_once_with(
        "src.amazon_chat_completions_server.api.app:app",
        host="localhost",
        port=8000,
        reload=False,
        env_file=None
    ) 