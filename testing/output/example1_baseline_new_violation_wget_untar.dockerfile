FROM alpine:latest

WORKDIR /download

# Use ADD to download and extract the archive in one step
ADD https://example.com/some_archive.tar.gz . 

# The tar extraction is implicit with ADD if the destination is a directory

# Specify a non-root user (security best practice)
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
USER appuser

# Specify ENTRYPOINT or CMD as needed
# CMD [...]