FROM python:3.10-alpine AS builder

WORKDIR /app

COPY . .

RUN apk add --no-cache --virtual .build-deps gcc musl-dev \
    && pip install --user -r requirements.txt \
    && apk del .build-deps

FROM python:3.10-alpine

COPY --from=builder /root/.local /root/.local
COPY . /app

WORKDIR /app

RUN apk add --no-cache curl \
    && adduser -D appuser \
    && chown -R appuser:appuser /app

ENV PATH=/root/.local/bin:$PATH

USER appuser

CMD ["python", "app.py"]