FROM ubuntu:22.04

# Combine RUN commands to reduce layers and use a specific tag for reproducibility
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip git && \
    rm -rf /var/lib/apt/lists/* && \
    pip3 install --no-cache-dir flask requests

# Use COPY instead of ADD for local files and only copy what's needed
COPY . /app
WORKDIR /app

# Create a non-root user to run the app
RUN useradd -m appuser
USER appuser

# Specify command to run the application
CMD ["python3", "app.py"]