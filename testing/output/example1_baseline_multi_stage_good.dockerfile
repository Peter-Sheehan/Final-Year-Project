# Stage 1: Build environment
FROM python:3.11-slim AS builder
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir wheel

COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# Stage 2: Production environment
FROM python:3.11-alpine
WORKDIR /app

# Install production dependencies
RUN apk add --no-cache libstdc++

# Copy only necessary artifacts from builder stage
COPY --from=builder /wheels /wheels
COPY --from=builder /app/requirements.txt .

RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

COPY . /app

# Create non-root user
RUN adduser -D -s /bin/sh appuser
USER appuser

CMD ["python", "app.py"]