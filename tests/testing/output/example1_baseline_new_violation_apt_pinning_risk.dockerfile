FROM debian:bullseye-slim

# Update and install dependencies in a single step
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    python3=3.9.2-3 \
    curl=7.74.0-1.3+deb11u7 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

CMD ["python3", "app.py"]