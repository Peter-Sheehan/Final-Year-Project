# Dockerfile: simple_optimizable.dockerfile
FROM python:3.9-slim

# Install dependencies in a single RUN layer to reduce image size
RUN pip install --no-cache-dir flask requests

# Copy only necessary files to avoid unnecessary excess weight
COPY app.py /app/app.py

WORKDIR /app

CMD ["python", "app.py"]