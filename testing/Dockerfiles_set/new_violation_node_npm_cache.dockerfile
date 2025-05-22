# Violations: Uses node:latest, doesn't clean npm cache
FROM node:latest

WORKDIR /usr/src/app

# Copy package files
COPY package*.json ./

# Install dependencies without cache cleanup
RUN npm install

# Copy app source
COPY . .

EXPOSE 3000
CMD [ "node", "server.js" ] 