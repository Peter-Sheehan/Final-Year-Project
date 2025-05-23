FROM python:3.10-alpine

# Create a non-root user before copying files for better cache utilization
RUN adduser -D appuser

WORKDIR /app

# Copying requirements first if you have them for better build caching
# COPY requirements.txt . 
# RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY --chown=appuser:appuser . .

USER appuser

CMD ["python", "app.py"]