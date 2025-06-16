from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .errors import http_exception_handler
from .middleware.logging import RequestLoggingMiddleware
from .routes import chat, files, health, knowledge_bases, models

app = FastAPI(
    title="Open Bedrock Server API",
    description="Unified API for interacting with various LLM providers via OpenAI-compatible endpoint with file management and knowledge bases",
    version="2.0.0",
)

# Add middlewares
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(HTTPException, http_exception_handler)

# Include all routers
app.include_router(health.router)
app.include_router(chat.router)  # Original unified endpoint
app.include_router(models.router)
app.include_router(files.router)  # File management endpoint
app.include_router(knowledge_bases.router)  # Knowledge Base management endpoint
