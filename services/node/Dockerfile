FROM node:22-slim

WORKDIR /app

COPY services/node/package.json /app/package.json
RUN npm install

COPY contracts /app/contracts
COPY services/node/tsconfig.json /app/tsconfig.json
COPY services/node/src /app/src

RUN npm run build
