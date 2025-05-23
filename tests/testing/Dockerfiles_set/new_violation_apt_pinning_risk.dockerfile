# Violations: Pins versions on latest tag (risky)
FROM debian:latest

# Update
RUN apt-get update

# Install specific versions - might break if latest changes significantly
RUN apt-get install -y --no-install-recommends \
    python3=3.9.1-1 \
    curl=7.74.0-1.3+deb11u1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

CMD ["python3", "app.py"] 