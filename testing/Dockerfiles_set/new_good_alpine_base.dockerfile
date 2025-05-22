# Simple, reasonably good Alpine base
FROM python:3.10-alpine

RUN apk add --no-cache tzdata

ENV TZ=Etc/UTC

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

RUN adduser -D appuser
USER appuser

CMD ["python", "app.py"] 