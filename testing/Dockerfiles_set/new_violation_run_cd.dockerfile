# Violations: Uses RUN cd instead of WORKDIR
FROM ubuntu:22.04

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Create dir
RUN mkdir /opt/mydata

# Bad: Change directory within RUN
RUN cd /opt/mydata && \
    curl -o data.txt https://example.com/data

WORKDIR /opt/mydata
CMD ["cat", "data.txt"] 