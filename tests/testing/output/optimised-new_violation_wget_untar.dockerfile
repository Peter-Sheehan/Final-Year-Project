# Use a specific version for the base image for consistency and security updates
FROM alpine:3.18

# Add labels to organize and add metadata
LABEL maintainer="you@example.com" \
      version="1.0" \
      description="An optimized Alpine-based Docker image for downloading and extracting archives."

# Set a non-root user for security
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

# Install required tools
RUN apk add --no-cache wget tar

# Set the working directory
WORKDIR /download

# Use ADD to download and extract the tar in one step
ADD https://example.com/some_archive.tar.gz /download/

# Ensure extracted contents are owned by the non-root user
RUN chown -R appuser:appgroup /download

# Set user to non-root
USER appuser

# Include a command to demonstrate extracted content usage (adjust as needed)
CMD ["ls", "/download"]