FROM node:18-alpine AS frontend_build
WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

FROM nginx:1.25-alpine

COPY docker/nginx/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=frontend_build /app/frontend/build /usr/share/nginx/html

EXPOSE 80
