# Dockerfile: known_issues.dockerfile
FROM python:latest

RUN apt-get update
RUN apt-get install -y vim nano && rm -rf /var/lib/apt/lists/* # Should suggest --no-install-recommends, cleanup is okay but pkgs are bad
RUN mkdir /data && cd /data

ADD . /app
WORKDIR /app

ENV BAD_VAR=

USER root

CMD python app.py && echo "done" 