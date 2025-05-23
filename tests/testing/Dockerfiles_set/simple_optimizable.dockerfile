# Dockerfile: simple_optimizable.dockerfile
FROM python:3.9

RUN pip install flask
RUN pip install requests

COPY . /app
WORKDIR /app

CMD ["python", "app.py"] 