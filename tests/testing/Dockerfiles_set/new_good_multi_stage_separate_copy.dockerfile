# Multi-stage, reasonably good, but uses individual COPY
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt
COPY app.py .
COPY utils.py .

FROM python:3.11-alpine
WORKDIR /app
COPY --from=builder /wheels /wheels
RUN pip install --no-cache /wheels/*
# Copies files individually from builder
COPY --from=builder /app/app.py .
COPY --from=builder /app/utils.py .

RUN adduser -D appuser
USER appuser
CMD ["python", "app.py"] 