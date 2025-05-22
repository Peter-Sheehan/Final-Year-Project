# Stage 1: Build environment
FROM python:3.11-slim AS builder
WORKDIR /app

# Install build dependencies
RUN pip install --no-cache-dir wheel

COPY requirements.txt .
# Use caching for dependencies
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# Stage 2: Production environment
FROM python:3.11-alpine
WORKDIR /app

# Copy only necessary artifacts from builder stage
COPY --from=builder /wheels /wheels
COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache /wheels/*

COPY . /app

# Create non-root user
RUN adduser -D appuser
USER appuser

CMD ["python", "app.py"] 