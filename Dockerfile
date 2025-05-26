# syntax=docker/dockerfile:1

# ---- Builder Stage ----
# Use an official Python runtime as a parent image for the builder stage
FROM python:3.12-slim AS builder

# Argument for uv version
ARG UV_VERSION=0.1.40

# Set Python environment variables
# PYTHONDONTWRITEBYTECODE: Prevents Python from writing .pyc files to disc (improves performance and avoids clutter)
# PYTHONUNBUFFERED: Prevents Python from buffering stdout and stderr (ensures logs are sent directly to the terminal)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install uv
RUN pip install --no-cache-dir uv==${UV_VERSION}

# Set the working directory in the container
WORKDIR /app

# Copy pyproject.toml first to leverage Docker layer caching for dependencies
COPY pyproject.toml ./pyproject.toml

# Copy the source code
# The source code is in 'src' and mapped in pyproject.toml
COPY src ./src

# Install project dependencies using uv
# Using --system to install into the system Python.
# This installs the project "amazon-chat-completions-server" and its dependencies.
RUN uv pip install --no-cache-dir --system .

# Copy other necessary files that might be needed by the application or for reference
# .env.example is useful for understanding required environment variables
COPY .env.example ./.env.example


# ---- Final Stage ----
# Use a slim Python image for the final application
FROM python:3.12-slim AS final

# Set Python environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

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

# Copy the application source code from the builder stage
COPY --from=builder /app/src ./src

# Copy the .env.example file for reference
COPY --from=builder /app/.env.example ./.env.example

# Switch to the non-privileged user
USER appuser

# Define an argument for the port, with a default value
ARG PORT=8000

# Expose the port the app runs on. This uses the PORT argument.
# This line doesn't publish the port but documents which port is intended to be published.
EXPOSE ${PORT}

# Command to run the main application script when the container launches
# This runs the application as a server using uvicorn on the specified PORT.
# Users can override this command to run their own scripts that use this library.
CMD ["uvicorn", "src.amazon_chat_completions_server.main:app", "--host", "0.0.0.0", "--port", "${PORT}"] 