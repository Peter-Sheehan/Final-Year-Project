FROM ubuntu:22.04

# Set working directory
WORKDIR /opt/mydata

# Minimize layers and remove temporary files for reduced image size
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    curl -o data.txt https://example.com/data && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

CMD ["cat", "data.txt"]