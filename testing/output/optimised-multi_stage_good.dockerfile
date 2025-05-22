# Stage 1: Build environment
FROM python:3.11-slim AS builder
WORKDIR /app

# Install build dependencies
RUN pip install --no-cache-dir wheel

COPY requirements.txt .
# Build wheels and minimize layer size by combining apt-get update and install
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# Stage 2: Production environment
FROM python:3.11-alpine
WORKDIR /app

# Install necessary runtime dependencies
RUN apk add --no-cache libstdc++ \
    && apk add --no-cache --virtual .build-deps gcc musl-dev \
    && apk add --no-cache python3-dev libffi-dev openssl-dev

# Copy only necessary artifacts from builder stage
COPY --from=builder /wheels /wheels
COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache-dir /wheels/* \
    && apk del .build-deps

COPY . /app

# Create non-root user
RUN adduser -D appuser
USER appuser

CMD ["python", "app.py"]