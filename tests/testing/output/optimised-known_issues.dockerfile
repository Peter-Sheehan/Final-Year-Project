# Dockerfile: optimized.dockerfile
FROM python:3.9-slim AS builder

LABEL maintainer="Your Name <your.email@example.com>"

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.9-slim

LABEL maintainer="Your Name <your.email@example.com>"

COPY --from=builder /app /app
WORKDIR /app

COPY . .

RUN apt-get update && \
    apt-get install -y --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

ENV APP_ENV=production

RUN useradd -m myappuser
USER myappuser

CMD ["python", "app.py"]