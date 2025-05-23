FROM python:3.10-alpine

RUN apk add --no-cache curl

COPY . /app
WORKDIR /app

RUN adduser -D appuser
USER appuser

CMD ["python", "app.py"] 