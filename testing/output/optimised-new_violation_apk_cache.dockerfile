# Use specific version tag for base image
FROM alpine:3.18

# Set working directory
WORKDIR /app

# Update, install and clean up in one layer to optimize image size
RUN apk add --no-cache bash curl

# Copy application code
COPY . .

# Use a non-root user
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
USER appuser

# Default command to run
CMD ["bash"]