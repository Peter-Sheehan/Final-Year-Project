# Violations: Runs apt-get update alone
FROM ubuntu:22.04

# Bad: update alone
RUN apt-get update

# Install something
RUN apt-get install -y --no-install-recommends figlet && rm -rf /var/lib/apt/lists/*

CMD ["figlet", "Hello"] 