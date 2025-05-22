# Violations: Manual download/extract instead of ADD url
FROM alpine:latest

# Install tools
RUN apk add --no-cache wget tar

WORKDIR /download

# Manual download and extraction (less cache efficient than ADD url)
RUN wget https://example.com/some_archive.tar.gz && \
    tar -xzf some_archive.tar.gz && \
    rm some_archive.tar.gz

# Assume extracted content is used later
# CMD [...] depends on archive content 