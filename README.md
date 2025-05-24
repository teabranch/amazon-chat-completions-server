# Amazon Chat Completions Server

A server and CLI for interacting with various LLM providers.

## Installation

```bash
# Create and activate a virtual environment (optional but recommended)
python -m venv .venv  # Or use: uv venv
source .venv/bin/activate

# Install with uv
uv pip install -e . # For editable install
# or
# uv pip install . # For regular install
```

## Usage

### Start the server

```bash
amazon-chat serve --host 0.0.0.0 --port 8000 --reload
```

Then access the API at `http://localhost:8000`.
- Docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
