# Dockerfile: optimized.dockerfile
FROM python:3.12-slim

# Install only necessary packages without recommended ones and clean up afterwards
RUN apt-get update && apt-get install -y --no-install-recommends nano \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy source code
COPY . .

# Use a non-root user for security
RUN useradd -m -d /app appuser
USER appuser

# Ensure CMD uses JSON format for better signal handling
CMD ["python", "app.py"]