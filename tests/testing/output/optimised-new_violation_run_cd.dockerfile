FROM debian:12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/mydata

RUN curl -o data.txt https://example.com/data

FROM debian:12-slim

WORKDIR /opt/mydata

COPY --from=builder /opt/mydata/data.txt .

USER nobody

CMD ["cat", "data.txt"]