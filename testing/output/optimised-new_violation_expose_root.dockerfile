# Use multi-stage builder pattern
FROM python:3.10-slim AS base

# Set work directory
WORKDIR /app

# Copy application files
COPY . /app

# Update and install netcat then clean up
RUN apt-get update && \
    apt-get install -y --no-install-recommends netcat && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user and set permissions
RUN groupadd -r appuser && useradd -r -g appuser appuser && chown -R appuser:appuser /app
USER appuser

# Expose necessary port
EXPOSE 8080

# Use CMD to start the server
CMD ["nc", "-lp", "8080"]