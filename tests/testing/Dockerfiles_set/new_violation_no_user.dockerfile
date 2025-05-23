# Violations: Does not switch to a non-root user
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Missing USER instruction

CMD ["python", "app.py"] 