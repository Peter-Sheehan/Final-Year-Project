# Dockerfile: optimized_example.dockerfile
FROM python:3.11-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt


FROM python:3.11-slim

RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
USER appuser

WORKDIR /app
COPY --from=builder /app/.local /app/.local
COPY app.py .

ENV PATH="/app/.local/bin:${PATH}"

EXPOSE 8000
CMD ["python", "app.py"]