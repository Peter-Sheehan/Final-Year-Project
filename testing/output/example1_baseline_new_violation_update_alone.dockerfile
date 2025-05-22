FROM ubuntu:22.04

# Combine update and install commands to reduce layers and remove cache
RUN apt-get update && \
    apt-get install -y --no-install-recommends figlet && \
    rm -rf /var/lib/apt/lists/*

CMD ["figlet", "Hello"]