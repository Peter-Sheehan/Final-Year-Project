# Use a specific version of the Debian base image for consistency and security
FROM debian:bullseye-slim AS build

# Set a non-root user for enhanced security
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

# Install necessary packages, ensuring to clean up afterwards to reduce image size
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy application files
COPY . .

# Use a non-root user
USER appuser

# Set default command
CMD ["python3", "app.py"]