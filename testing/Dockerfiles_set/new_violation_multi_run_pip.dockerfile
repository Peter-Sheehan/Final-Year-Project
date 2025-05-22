# Violations: Multiple RUN commands for pip install
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .

# Bad: Multiple layers for installs
RUN pip install --no-cache-dir flask
RUN pip install --no-cache-dir gunicorn
RUN pip install --no-cache-dir requests

COPY . .

CMD ["gunicorn", "app:app"] 