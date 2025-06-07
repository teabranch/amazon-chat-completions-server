from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .routes import health, chat, models, files
from .errors import http_exception_handler
from .middleware.logging import RequestLoggingMiddleware

app = FastAPI(
    title="Amazon Chat Completions API",
    description="Unified API for interacting with various LLM providers via OpenAI-compatible endpoint with file management",
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
