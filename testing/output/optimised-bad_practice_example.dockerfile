# Start with a slim Ubuntu version
FROM ubuntu:22.04

LABEL maintainer="Maintainer Name <maintainer@example.com>"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Combine apt-get update and install, use --no-install-recommends, and clean up
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    python3=3.10.6-1~22.04 \
    python3-pip=22.0.2+dfsg-1ubuntu0.4 \
    git=1:2.34.1-1ubuntu1.9 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Use COPY instead of ADD
COPY . /app

# Install Python dependencies
RUN pip3 install --no-cache-dir flask requests

# Create a non-root user and switch to it
RUN useradd -ms /bin/bash appuser
USER appuser

# CMD as an array format for entry point
CMD ["python3", "app.py"]