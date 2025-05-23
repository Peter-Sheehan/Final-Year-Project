FROM python:3.9-slim AS builder

WORKDIR /app

# Combine pip installs into a single command and include requirements file
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create a non-root user to run the application
RUN useradd -m myapp && chown -R myapp:myapp /app
USER myapp

# Final stage to reduce image size
FROM python:3.9-slim

WORKDIR /app

# Copy only the necessary artifacts from the builder stage
COPY --from=builder /app /app

USER myapp

CMD ["gunicorn", "app:app"]