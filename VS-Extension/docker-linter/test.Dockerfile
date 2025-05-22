FROM ubuntu:latest
ADD . /app
RUN apt-get update
USER root 