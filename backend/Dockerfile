# Dockerfile
FROM python:3.11-slim

RUN useradd -m myuser && mkdir /app && chown myuser:myuser /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

USER myuser
WORKDIR /app

# Default command (overridden when the container runs a script)
CMD ["bash"]
