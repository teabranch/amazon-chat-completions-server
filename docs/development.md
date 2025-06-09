---
layout: default
title: Development Guide
nav_order: 6
description: "Development guide for extending and customizing Amazon Chat Completions Server"
---

# Development Guide
{: .no_toc }

Guide for developers who want to extend, customize, or contribute to the Amazon Chat Completions Server.
{: .fs-6 .fw-300 }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Development Setup

### Prerequisites

- **Python 3.12+**
- **uv** package manager (recommended)
- **Git**
- **Docker** (optional, for containerized development)

### Environment Setup

```bash
# Fork and clone the repository
git clone https://github.com/teabranch/open-amazon-chat-completions-server.git
cd open-amazon-chat-completions-server

# Create virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
uv pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Configuration

Create a development `.env` file:

```env
# Development configuration
OPENAI_API_KEY=sk-your-dev-key
API_KEY=dev-api-key
AWS_REGION=us-east-1
LOG_LEVEL=DEBUG

# Development settings
ENVIRONMENT=development
DEBUG=true
```

## Project Structure

```
open-amazon-chat-completions-server/
├── src/
│   └── open_amazon_chat_completions_server/
│       ├── api/                 # FastAPI routes and endpoints
│       ├── core/                # Core models and utilities
│       ├── services/            # Business logic and integrations
│       ├── cli/                 # Command-line interface
│       └── main.py              # Application entry point
├── tests/                       # Test suite
├── docs/                        # Documentation
├── pyproject.toml              # Project configuration
└── README.md                   # Main documentation
```

## Development Workflow

### 1. Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_api.py

# Run with verbose output
pytest -v

# Run tests in parallel
pytest -n auto
```

### 2. Code Quality

```bash
# Format code
ruff format .

# Lint code
ruff check .

# Type checking
mypy src/

# Run all quality checks
pre-commit run --all-files
```

### 3. Development Server

```bash
# Start development server with auto-reload
open-amazon-chat serve --reload --log-level debug

# Or use uvicorn directly
uvicorn src.open_amazon_chat_completions_server.main:app --reload --log-level debug
```

### 4. Interactive Development

```bash
# Start interactive chat for testing
open-amazon-chat chat --model gpt-4o-mini --server-url http://localhost:8000

# Test API endpoints
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dev-api-key" \
  -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"Hello"}]}'
```

## Adding New Features

### 1. Adding a New LLM Provider

Create a new service class:

```python
# src/open_amazon_chat_completions_server/services/new_provider_service.py
from typing import AsyncGenerator, List, Optional
from ..core.models import ChatCompletionRequest, ChatCompletionResponse, Message
from ..core.exceptions import LLMIntegrationError
from .base_llm_service import BaseLLMService

class NewProviderService(BaseLLMService):
    """Service for integrating with a new LLM provider"""
    
    def __init__(self, api_key: str, base_url: Optional[str] = None):
        self.api_key = api_key
        self.base_url = base_url or "https://api.newprovider.com"
    
    async def chat_completion(
        self,
        messages: List[Message],
        model: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stream: bool = False,
        **kwargs
    ) -> ChatCompletionResponse:
        """Implement chat completion for new provider"""
        try:
            # Implementation here
            pass
        except Exception as e:
            raise LLMIntegrationError(f"New provider error: {str(e)}")
    
    async def chat_completion_stream(
        self,
        messages: List[Message],
        model: str,
        **kwargs
    ) -> AsyncGenerator[ChatCompletionResponse, None]:
        """Implement streaming for new provider"""
        # Implementation here
        pass
```

Register the service in the factory:

```python
# src/open_amazon_chat_completions_server/services/llm_service_factory.py
from .new_provider_service import NewProviderService

class LLMServiceFactory:
    @staticmethod
    def get_service(provider_name: str, model_id: str) -> BaseLLMService:
        if provider_name == "new_provider":
            api_key = os.getenv("NEW_PROVIDER_API_KEY")
            return NewProviderService(api_key=api_key)

### 2. Adding New File Processing Types

Extend the file processing service to support new file formats:

```python
# src/open_amazon_chat_completions_server/services/file_processing_service.py
from typing import Tuple

class FileProcessingService:
    """Service for processing different file types for chat context"""
    
    def process_file(self, content: bytes, filename: str, content_type: str) -> str:
        """Process file content based on type"""
        if content_type == "application/pdf":
            return self._process_pdf(content, filename)
        elif content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            return self._process_docx(content, filename)
        # Add more file types as needed
        
    def _process_pdf(self, content: bytes, filename: str) -> str:
        """Extract text from PDF files"""
        try:
            import PyPDF2
            from io import BytesIO
            
            pdf_reader = PyPDF2.PdfReader(BytesIO(content))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            
            return f"**PDF Content from {filename}:**\n{text.strip()}"
        except Exception as e:
            return f"Error processing PDF {filename}: {str(e)}"
    
    def _process_docx(self, content: bytes, filename: str) -> str:
        """Extract text from Word documents"""
        try:
            from docx import Document
            from io import BytesIO
            
            doc = Document(BytesIO(content))
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            
            return f"**Word Document Content from {filename}:**\n{text.strip()}"
        except Exception as e:
            return f"Error processing Word document {filename}: {str(e)}"
```

### 3. Extending File Storage Options

Add support for different storage backends:

```python
# src/open_amazon_chat_completions_server/services/storage/base_storage.py
from abc import ABC, abstractmethod
from typing import Optional, List, Tuple

class BaseStorageService(ABC):
    """Abstract base class for file storage services"""
    
    @abstractmethod
    async def upload_file(
        self, 
        file_content: bytes, 
        filename: str, 
        metadata: dict
    ) -> str:
        """Upload file and return file ID"""
        pass
    
    @abstractmethod
    async def get_file_content(self, file_id: str) -> Tuple[bytes, str, str]:
        """Get file content, filename, and content type"""
        pass
    
    @abstractmethod
    async def delete_file(self, file_id: str) -> bool:
        """Delete file and return success status"""
        pass
    
    @abstractmethod
    async def list_files(self, purpose: Optional[str] = None) -> List[dict]:
        """List files with optional purpose filter"""
        pass

# src/open_amazon_chat_completions_server/services/storage/local_storage.py
import os
import json
import aiofiles
from typing import Optional, List, Tuple
from .base_storage import BaseStorageService

class LocalStorageService(BaseStorageService):
    """Local filesystem storage implementation"""
    
    def __init__(self, storage_path: str = "./file_storage"):
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)
        os.makedirs(os.path.join(storage_path, "files"), exist_ok=True)
        os.makedirs(os.path.join(storage_path, "metadata"), exist_ok=True)
    
    async def upload_file(
        self, 
        file_content: bytes, 
        filename: str, 
        metadata: dict
    ) -> str:
        """Upload file to local storage"""
        file_id = f"file-{uuid.uuid4().hex[:16]}"
        
        # Save file content
        file_path = os.path.join(self.storage_path, "files", file_id)
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(file_content)
        
        # Save metadata
        metadata_path = os.path.join(self.storage_path, "metadata", f"{file_id}.json")
        metadata.update({"filename": filename, "file_id": file_id})
        async with aiofiles.open(metadata_path, "w") as f:
            await f.write(json.dumps(metadata))
        
        return file_id
```

### 4. Adding File API Endpoints

Create new API endpoints for file operations:

```python
# src/open_amazon_chat_completions_server/api/routes/files.py
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from typing import Optional

router = APIRouter()

@router.post("/v1/files/batch")
async def upload_multiple_files(
    files: List[UploadFile] = File(...),
    purpose: str = Form(...),
    current_user = Depends(verify_api_key)
):
    """Upload multiple files at once"""
    file_ids = []
    
    for file in files:
        try:
            file_content = await file.read()
            # Process upload logic
            file_id = await file_service.upload_file(
                file_content=file_content,
                filename=file.filename,
                purpose=purpose,
                content_type=file.content_type
            )
            file_ids.append(file_id)
        except Exception as e:
            # Handle partial failures
            raise HTTPException(status_code=500, detail=f"Failed to upload {file.filename}: {str(e)}")
    
    return {"uploaded_files": file_ids}

@router.get("/v1/files/search")
async def search_files(
    query: str,
    limit: int = 20,
    current_user = Depends(verify_api_key)
):
    """Search files by content or metadata"""
    # Implement file search logic
    results = await file_service.search_files(query, limit)
    return {"results": results}
```
        # ... existing providers
```

### 2. Adding New API Endpoints

Create a new router:

```python
# src/open_amazon_chat_completions_server/api/new_endpoints.py
from fastapi import APIRouter, Depends, HTTPException
from ..core.auth import verify_api_key
from ..core.models import CustomRequest, CustomResponse

router = APIRouter(prefix="/v1/custom", tags=["custom"])

@router.post("/endpoint", response_model=CustomResponse)
async def custom_endpoint(
    request: CustomRequest,
    api_key: str = Depends(verify_api_key)
):
    """Custom endpoint implementation"""
    try:
        # Implementation here
        return CustomResponse(...)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

Register the router:

```python
# src/open_amazon_chat_completions_server/main.py
from .api.new_endpoints import router as new_router

app.include_router(new_router)
```

### 3. Adding New CLI Commands

Create a new command:

```python
# src/open_amazon_chat_completions_server/cli/new_command.py
import click
from ..services.llm_service_factory import LLMServiceFactory

@click.command()
@click.option("--option", help="Command option")
def new_command(option: str):
    """New CLI command"""
    click.echo(f"Executing new command with option: {option}")
    # Implementation here
```

Register the command:

```python
# src/open_amazon_chat_completions_server/cli/main.py
from .new_command import new_command

cli.add_command(new_command)
```

## Testing

### Test Structure

```
tests/
├── unit/                    # Unit tests
│   ├── test_services/
│   ├── test_api/
│   └── test_cli/
├── integration/             # Integration tests
├── fixtures/                # Test fixtures
└── conftest.py             # Pytest configuration
```

### Writing Tests

#### Unit Tests

```python
# tests/unit/test_services/test_openai_service.py
import pytest
from unittest.mock import AsyncMock, patch
from src.open_amazon_chat_completions_server.services.openai_service import OpenAIService
from src.open_amazon_chat_completions_server.core.models import Message

@pytest.fixture
def openai_service():
    return OpenAIService(api_key="test-key")

@pytest.mark.asyncio
async def test_chat_completion(openai_service):
    """Test basic chat completion"""
    with patch('openai.AsyncOpenAI') as mock_client:
        # Setup mock
        mock_response = AsyncMock()
        mock_response.choices = [AsyncMock()]
        mock_response.choices[0].message.content = "Test response"
        mock_client.return_value.chat.completions.create.return_value = mock_response
        
        # Test
        messages = [Message(role="user", content="Hello")]
        response = await openai_service.chat_completion(messages, "gpt-4o-mini")
        
        # Assert
        assert response.choices[0].message.content == "Test response"
```

#### Integration Tests

```python
# tests/integration/test_api_integration.py
import pytest
from fastapi.testclient import TestClient
from src.open_amazon_chat_completions_server.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_chat_completions_endpoint(client):
    """Test the chat completions endpoint"""
    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer test-key"},
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "Hello"}]
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "choices" in data
    assert len(data["choices"]) > 0
```

#### CLI Tests

```python
# tests/unit/test_cli/test_chat_command.py
import pytest
from click.testing import CliRunner
from src.open_amazon_chat_completions_server.cli.main import cli

def test_chat_command():
    """Test the chat CLI command"""
    runner = CliRunner()
    result = runner.invoke(cli, ['chat', '--help'])
    
    assert result.exit_code == 0
    assert 'Start an interactive chat session' in result.output
```

### Test Configuration

```python
# tests/conftest.py
import pytest
import os
from unittest.mock import patch

@pytest.fixture(autouse=True)
def setup_test_env():
    """Setup test environment variables"""
    test_env = {
        "OPENAI_API_KEY": "test-openai-key",
        "API_KEY": "test-api-key",
        "AWS_REGION": "us-east-1",
        "LOG_LEVEL": "DEBUG"
    }
    
    with patch.dict(os.environ, test_env):
        yield

@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing"""
    with patch('openai.AsyncOpenAI') as mock:
        yield mock
```

## Documentation

### Adding Documentation

1. **API Documentation**: Use FastAPI's automatic OpenAPI generation
2. **Code Documentation**: Use docstrings following Google style
3. **User Documentation**: Add Markdown files to the `docs/` directory

#### Code Documentation Example

```python
def chat_completion(
    self,
    messages: List[Message],
    model: str,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
    stream: bool = False,
    **kwargs
) -> ChatCompletionResponse:
    """Generate a chat completion response.
    
    Args:
        messages: List of conversation messages
        model: Model identifier to use
        max_tokens: Maximum tokens to generate
        temperature: Sampling temperature (0.0 to 2.0)
        stream: Whether to stream the response
        **kwargs: Additional provider-specific parameters
    
    Returns:
        ChatCompletionResponse: The completion response
    
    Raises:
        LLMIntegrationError: If the LLM service fails
        AuthenticationError: If authentication fails
        RateLimitError: If rate limits are exceeded
    
    Example:
        >>> service = OpenAIService(api_key="sk-...")
        >>> messages = [Message(role="user", content="Hello")]
        >>> response = await service.chat_completion(messages, "gpt-4o-mini")
        >>> print(response.choices[0].message.content)
    """
```

### Building Documentation

```bash
# Install documentation dependencies
uv pip install -e ".[docs]"

# Build documentation locally
mkdocs serve

# Build for production
mkdocs build
```

## Debugging

### Logging

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Use in code
logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
```

### Debug Configuration

```python
# src/open_amazon_chat_completions_server/core/config.py
import os

DEBUG = os.getenv("DEBUG", "false").lower() == "true"

if DEBUG:
    # Enable debug features
    import logging
    logging.getLogger().setLevel(logging.DEBUG)
```

### Using Debugger

```python
# Add breakpoints in code
import pdb; pdb.set_trace()

# Or use ipdb for better experience
import ipdb; ipdb.set_trace()
```

## Performance Optimization

### Profiling

```python
# Profile code performance
import cProfile
import pstats

def profile_function():
    """Profile a specific function"""
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Your code here
    
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats()
```

### Async Best Practices

```python
import asyncio
from typing import List

# Good: Use asyncio.gather for concurrent operations
async def process_multiple_requests(requests: List[dict]) -> List[dict]:
    tasks = [process_single_request(req) for req in requests]
    return await asyncio.gather(*tasks)

# Good: Use semaphore to limit concurrency
async def limited_concurrent_processing(requests: List[dict], max_concurrent: int = 10):
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_with_limit(request):
        async with semaphore:
            return await process_single_request(request)
    
    tasks = [process_with_limit(req) for req in requests]
    return await asyncio.gather(*tasks)
```

## Contributing

### Pull Request Process

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/new-feature`
3. **Make changes and add tests**
4. **Run quality checks**: `pre-commit run --all-files`
5. **Commit changes**: `git commit -m "Add new feature"`
6. **Push to fork**: `git push origin feature/new-feature`
7. **Create pull request**

### Code Style

- Follow PEP 8 style guidelines
- Use type hints for all functions
- Write comprehensive docstrings
- Add tests for new functionality
- Keep functions small and focused

### Commit Messages

Use conventional commit format:

```
feat: add new LLM provider support
fix: resolve streaming response issue
docs: update API documentation
test: add integration tests for chat endpoint
refactor: simplify service factory logic
```

## Release Process

### Version Management

```bash
# Update version in pyproject.toml
# Create release notes
# Tag release
git tag v1.0.0
git push origin v1.0.0

# Build package
uv build

# Upload to PyPI
uv publish
```

### Deployment

```bash
# Build Docker image
docker build -t open-amazon-chat-completions-server:latest .

# Run locally
docker run -p 8000:8000 open-amazon-chat-completions-server:latest

# Deploy to production
# (Use your preferred deployment method)
```

---

This development guide provides a comprehensive overview of the development process. For specific implementation details, refer to the existing codebase and follow the established patterns. 