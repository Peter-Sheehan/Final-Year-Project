# Use a specific node version instead of latest, for stability
FROM node:18 AS builder

WORKDIR /usr/src/app

# Copy package files first for better use of cached layers
COPY package*.json ./

# Install dependencies and clean up npm cache to reduce image size
RUN npm install && npm cache clean --force

# Copy only the essential source files
COPY . .

# Use a smaller base image for production
FROM node:18-alpine as production

WORKDIR /usr/src/app

# Copy only necessary files from the build stage
COPY --from=builder /usr/src/app /usr/src/app

EXPOSE 3000
CMD ["node", "server.js"]

# Use non-root user for security
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
USER appuser