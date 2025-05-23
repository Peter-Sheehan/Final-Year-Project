# Dockerfile: optimized_multistage.dockerfile
# Stage 1: Builder
FROM python:3.9-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Final Image
FROM python:3.9-slim

WORKDIR /app
COPY --from=builder /build /app 
COPY app.py .

RUN adduser --system --no-create-home appuser
USER appuser

CMD ["python", "app.py"]