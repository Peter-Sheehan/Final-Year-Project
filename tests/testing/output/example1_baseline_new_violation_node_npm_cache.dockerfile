FROM node:18-alpine

WORKDIR /usr/src/app

# Copy package files
COPY package*.json ./

# Install dependencies and clean cache
RUN npm ci --ignore-scripts --no-audit && npm cache clean --force

# Copy app source
COPY . .

EXPOSE 3000
CMD [ "node", "server.js" ]