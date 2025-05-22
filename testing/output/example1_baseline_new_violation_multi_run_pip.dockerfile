FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .

# Combine pip installs into a single RUN command
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["gunicorn", "app:app"]