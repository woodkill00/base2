# Dockerfile for React App (Production-like)
# Build with Node, serve static build via Nginx (internal-only behind Traefik)

# Declare all ARG used in any FROM before the first FROM
ARG NODE_VERSION=18-alpine
ARG NGINX_VERSION=1.25-alpine
FROM node:${NODE_VERSION} AS build

WORKDIR /app

# Copy package files
COPY package*.json ./
  RUN npm install && npm cache clean --force

COPY . .

# Build-time environment variables for React
ARG REACT_APP_API_URL
ENV REACT_APP_API_URL=${REACT_APP_API_URL}

# Create production build
RUN npm run build

# ---------- Runtime: Nginx to serve static build ----------
FROM nginx:${NGINX_VERSION}

# Install envsubst (optional for templating)
RUN apk add --no-cache gettext

# Copy build artifacts to Nginx html directory
COPY --from=build /app/build /usr/share/nginx/html

# Minimal Nginx main config to run workers as non-root user
RUN printf "user nginx;\nworker_processes auto;\nerror_log /var/log/nginx/error.log warn;\npid /var/run/nginx.pid;\n\nevents { worker_connections 1024; }\n\nhttp {\n  include /etc/nginx/mime.types;\n  default_type application/octet-stream;\n  sendfile on;\n  keepalive_timeout 65;\n  include /etc/nginx/conf.d/*.conf;\n}\n" > /etc/nginx/nginx.conf

# Minimal Nginx site config for SPA (listen on 8080 for non-root)
RUN printf "server {\n  listen 8080;\n  server_name _;\n\n  root /usr/share/nginx/html;\n  index index.html;\n\n  location / {\n    try_files $uri $uri/ /index.html;\n  }\n\n  location ~* \\.(?:js|css|png|jpg|jpeg|gif|ico|svg|webp|ttf|woff|woff2)$ {\n    try_files $uri =404;\n    expires 1y;\n    add_header Cache-Control \"public, immutable\";\n    access_log off;\n  }\n\n  add_header X-Content-Type-Options nosniff;\n  add_header X-Frame-Options SAMEORIGIN;\n  add_header Referrer-Policy strict-origin-when-cross-origin;\n  add_header X-XSS-Protection \"1; mode=block\";\n}\n" > /etc/nginx/conf.d/default.conf

# Permissions for non-root user
RUN chown -R nginx:nginx /usr/share/nginx /var/log/nginx /var/cache/nginx /etc/nginx

# Internal-only note
RUN echo "# INTERNAL-ONLY: served behind Traefik; do not publish host ports." > /etc/nginx/conf.d/README

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost/ || exit 1

USER nginx
CMD ["nginx", "-g", "daemon off;"]
