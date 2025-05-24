# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Argument for uv version
ARG UV_VERSION=0.1.40

# Install uv
RUN pip install --no-cache-dir uv==${UV_VERSION}

# Set the working directory in the container
WORKDIR /app

# Copy pyproject.toml first to leverage Docker layer caching for dependencies
COPY pyproject.toml ./

# Copy the source code and other necessary files
# The source code is in 'src' and mapped in pyproject.toml
COPY src ./src
COPY README.md .env.example .gitignore ./

# Install project dependencies using uv
# Using --system to install into the system Python, common for Docker images.
# This installs the project "amazon-chat-completions-server" and its dependencies.
RUN uv pip install --no-cache-dir --system .

# .env.example is copied, but actual .env should be provided at runtime
# For example, by mounting a .env file or using environment variables.

# Command to run the main example script when the container launches
# This demonstrates that the library is installed and working.
# Users can override this command to run their own scripts that use this library.
CMD ["python", "-m", "src.llm_integrations.main"] 