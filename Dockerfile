# syntax=docker/dockerfile:1

# Multi-stage build for optimized final image
FROM python:3.12-slim AS builder

# Set Python environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install uv for faster package management
RUN pip install --no-cache-dir uv==0.6.6

# Set the working directory
WORKDIR /app

# Copy dependency files first for better layer caching
COPY pyproject.toml uv.lock ./

# Copy source code (needed for package installation)
COPY src ./src

# Create a minimal README.md for setuptools if needed
RUN echo "# Amazon Chat Completions Server" > README.md

# Install dependencies in a virtual environment
RUN uv venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
RUN uv sync --no-dev --frozen

# Install the package
RUN uv pip install --no-deps -e .

# Production stage
FROM python:3.12-slim AS production

# Set Python environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="/app"
ENV PATH="/app/.venv/bin:$PATH"

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create a non-privileged user with specific UID/GID
RUN groupadd --gid 10000 appuser && \
    useradd --uid 10000 --gid 10000 --no-create-home --shell /bin/bash appuser

# Set the working directory
WORKDIR /app

# Copy the virtual environment and application from builder stage
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv
COPY --from=builder --chown=appuser:appuser /app/src /app/src
COPY --from=builder --chown=appuser:appuser /app/README.md /app/README.md

# Define the port as build arg with default
ARG PORT=8000
ENV PORT=${PORT}

# Switch to the non-privileged user
USER appuser

# Expose the port
EXPOSE ${PORT}

# Add health check with configurable port
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Use exec form and make port configurable
CMD ["sh", "-c", "python -m uvicorn src.open_amazon_chat_completions_server.api.app:app --host 0.0.0.0 --port ${PORT}"] 