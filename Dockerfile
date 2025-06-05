# syntax=docker/dockerfile:1

# ---- Builder Stage ----
# Use an official Python runtime as a parent image for the builder stage
FROM python:3.12-slim AS builder

# Argument for uv version - updated to latest for better ARM support
ARG UV_VERSION=0.4.30

# Set Python environment variables
# PYTHONDONTWRITEBYTECODE: Prevents Python from writing .pyc files to disc (improves performance and avoids clutter)
# PYTHONUNBUFFERED: Prevents Python from buffering stdout and stderr (ensures logs are sent directly to the terminal)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set pip environment variables for better ARM performance
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies needed for building Python packages
# This is especially important for ARM architectures where wheels may not be available
# Added more build tools for better ARM compatibility
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    python3-dev \
    libffi-dev \
    libssl-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv - use the installer for better ARM support
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

# Set the working directory in the container
WORKDIR /app

# Copy dependency files first to leverage Docker layer caching
COPY pyproject.toml ./
COPY uv.lock ./

# Pre-install dependencies to improve caching
# Using uv sync for better dependency resolution and ARM wheel handling
RUN uv venv --system-site-packages && \
    uv pip install --system --no-deps setuptools wheel && \
    uv sync --system --no-dev --no-install-project

# Copy the source code
COPY src ./src

# Install the project itself
RUN uv pip install --system --no-deps .

# Copy other necessary files that might be needed by the application or for reference
# .env.example is useful for understanding required environment variables
# COPY .env.example ./.env.example


# ---- Final Stage ----
# Use a slim Python image for the final application
FROM python:3.12-slim AS final

# Set Python environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Install curl for health check (must be done before switching to non-privileged user)
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Create a non-privileged user that the app will run under.
# See https://docs.docker.com/go/dockerfile-user-best-practices/
ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    appuser

# Copy installed Python packages from the builder stage
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

# Copy the executable scripts from the builder stage
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy the application source code from the builder stage
COPY --from=builder /app/src ./src

# Copy the .env.example file for reference
# COPY --from=builder /app/.env.example ./.env.example

# Switch to the non-privileged user
USER appuser

# Add the current directory to Python path so src module can be found
ENV PYTHONPATH="/app:${PYTHONPATH}"

# Define an argument for the port, with a default value
ARG PORT=8000

# Set PORT as environment variable so it can be overridden at runtime
ENV PORT=${PORT}

# Expose the port the app runs on. This uses the PORT environment variable.
# This line doesn't publish the port but documents which port is intended to be published.
EXPOSE ${PORT}

# Add health check for container runtime
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Command to run the main application script when the container launches
# This runs the application as a server using the CLI command with dynamic port configuration.
# Users can override this command to run their own scripts that use this library.
CMD ["sh", "-c", "amazon-chat serve --host 0.0.0.0 --port ${PORT}"] 