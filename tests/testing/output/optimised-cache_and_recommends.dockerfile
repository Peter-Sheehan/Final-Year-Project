FROM debian:bullseye-slim

LABEL maintainer="your-email@example.com" \
      description="A Dockerfile with optimized build practices."

# Combine apt-get commands, use --no-install-recommends, and clean up in the same step
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Set the appropriate working directory
WORKDIR /app

# Copy files to working directory
COPY . /app

# Switch to a non-root user for increased security
RUN useradd -ms /bin/bash appuser
USER appuser

# Use a default command
CMD ["echo", "Build complete"]