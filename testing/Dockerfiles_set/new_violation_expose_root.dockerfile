# Violations: Uses ADD, runs as root, unnecessary EXPOSE?
FROM python:3.10-slim

RUN apt-get update && apt-get install -y --no-install-recommends netcat && rm -rf /var/lib/apt/lists/*

WORKDIR /app
# Use ADD for local files
ADD . /app

# Potentially unnecessary EXPOSE if app doesn't listen
EXPOSE 8080

# Runs as root
CMD ["nc", "-lp", "8080"] 