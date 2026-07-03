FROM node:22-bookworm-slim

WORKDIR /frontend
COPY package*.json ./
RUN npm ci --registry=https://registry.npmmirror.com --fetch-timeout=20000 --fetch-retries=2
COPY . .
RUN npm run build

EXPOSE 4173
CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0", "--port", "4173"]
