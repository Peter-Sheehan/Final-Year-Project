# Violations: Installs potentially unnecessary package (git)
FROM python:3.10-alpine

# Installs git, maybe not needed?
RUN apk add --no-cache git bash

WORKDIR /app
COPY . .

# Assume app doesn't need git at runtime
CMD ["python", "app.py"] 