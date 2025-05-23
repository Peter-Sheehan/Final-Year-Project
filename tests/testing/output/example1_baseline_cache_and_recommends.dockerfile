FROM debian:bullseye

# Optimize: Combine apt-get commands and clean up cache in the same layer
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    vim-tiny && \
    rm -rf /var/lib/apt/lists/*

COPY . /app
WORKDIR /app

CMD ["echo", "Build complete"]