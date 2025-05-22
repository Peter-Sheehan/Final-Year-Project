# Violations: uses latest tag, doesn't clean apk cache
FROM alpine:latest

# Update and install but without --no-cache or cleanup
RUN apk update
RUN apk add bash curl

WORKDIR /app
COPY . .

CMD ["bash"] 