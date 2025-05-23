FROM alpine:3.18

# Install bash and curl with --no-cache to prevent caching of index
RUN apk add --no-cache bash curl

WORKDIR /app
COPY . .

CMD ["bash"]