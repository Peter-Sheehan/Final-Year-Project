FROM debian:bullseye

# Bad: Not cleaning apt cache in the same layer
RUN apt-get update && apt-get install -y curl

# Bad: Not using --no-install-recommends
RUN apt-get install -y vim-tiny

# Bad: Cache not cleaned up
# RUN rm -rf /var/lib/apt/lists/*

COPY . /app
WORKDIR /app

CMD ["echo", "Build complete"] 