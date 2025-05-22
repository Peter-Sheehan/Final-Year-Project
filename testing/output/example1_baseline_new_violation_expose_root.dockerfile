FROM python:3.10-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends netcat && \
    rm -rf /var/lib/apt/lists/*

# Create and use a non-root user
RUN useradd -m appuser
USER appuser

WORKDIR /app
# Use COPY instead of ADD for local files
COPY . /app

# Remove EXPOSE if the application doesn't require it
# EXPOSE 8080

CMD ["nc", "-lp", "8080"]