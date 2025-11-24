# Next.js (TypeScript) frontend Dockerfile
FROM node:20-alpine
WORKDIR /app
ARG NEXT_PUBLIC_API_BASE=/api
ENV NEXT_PUBLIC_API_BASE=${NEXT_PUBLIC_API_BASE}
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
