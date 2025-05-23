# Example with several bad practices
FROM ubuntu:latest

# Bad: Using latest tag
# Bad: Separate RUN commands
RUN apt-get update
RUN apt-get install -y python3 python3-pip git
RUN pip3 install flask requests

# Bad: Using ADD for local context
ADD . /app
WORKDIR /app

# Bad: Running as root (implied, no USER instruction)
CMD ["python3", "app.py"] 