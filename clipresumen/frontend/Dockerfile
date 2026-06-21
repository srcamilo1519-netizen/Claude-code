FROM node:20-alpine

WORKDIR /app

# Install dependencies first to leverage Docker layer caching.
COPY package.json package-lock.json* ./
RUN npm install

COPY . .

EXPOSE 3000

# Dev command with hot-reload. Production build comes in Fase 7.
CMD ["npm", "run", "dev"]
