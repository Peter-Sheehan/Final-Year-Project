# Use a minimal base image for security and performance
FROM debian:bullseye-slim

# Install necessary package with version pinning
RUN apt-get update && apt-get install -y --no-install-recommends \
    figlet && \
    rm -rf /var/lib/apt/lists/* # Removed version pins by post-processor for compatibility

# Set a non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser
USER appuser

# Command to run the application
CMD ["figlet", "Hello"]