# Dockerfile
FROM python:3.11-slim

# Install pip and any dependencies (if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set up a working directory
WORKDIR /app

# Default command (overridden when the container runs a script)
CMD ["python", "--version"]
