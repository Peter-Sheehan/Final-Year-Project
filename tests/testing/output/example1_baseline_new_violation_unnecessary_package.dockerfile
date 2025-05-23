FROM python:3.10-alpine

WORKDIR /app
COPY . .

# Remove the installation of git and bash, assuming they're not required for runtime
CMD ["python", "app.py"]