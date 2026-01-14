# Dockerfile for React App (Production-like)
# Build with Node, serve static build via Nginx (internal-only behind Traefik)

# Declare all ARG used in any FROM before the first FROM
ARG NODE_VERSION=20-alpine
ARG NGINX_VERSION=1.27.3-alpine
FROM node:${NODE_VERSION} AS build

WORKDIR /app

# Copy package files
COPY package*.json ./
COPY scripts/postinstall.js ./scripts/postinstall.js
COPY patches ./patches
RUN npm ci --legacy-peer-deps --no-audit --no-fund && npm cache clean --force

COPY . .

# Speed up CRA production builds on small machines
ENV GENERATE_SOURCEMAP=false

# Create production build
RUN npm run build

# ---------- Runtime: Nginx to serve static build ----------
FROM nginx:${NGINX_VERSION}

# Upgrade base Alpine packages and install minimal tools (drop gettext)
RUN apk update \
  && apk upgrade --no-cache \
  && apk add --no-cache wget

# Copy build artifacts to Nginx html directory
COPY --from=build /app/build /usr/share/nginx/html

# Minimal Nginx main config to run workers as non-root user
RUN printf "user nginx;\nworker_processes auto;\nerror_log /dev/stderr warn;\npid /var/run/nginx.pid;\n\nevents { worker_connections 1024; }\n\nhttp {\n  include /etc/nginx/mime.types;\n  default_type application/octet-stream;\n  sendfile on;\n  keepalive_timeout 65;\n  include /etc/nginx/conf.d/*.conf;\n}\n" > /etc/nginx/nginx.conf

# Minimal Nginx site config for SPA (listen on 8080 for non-root)
RUN cat <<'EOF' > /etc/nginx/conf.d/default.conf
server {
  listen 8080;
  server_name _;

  root /usr/share/nginx/html;
  index index.html;

  location / {
    try_files $uri $uri/ /index.html;
  }

  location ~* \.(?:js|css|png|jpg|jpeg|gif|ico|svg|webp|ttf|woff|woff2)$ {
    try_files $uri =404;
    expires 1y;
    add_header Cache-Control "public, immutable";
    access_log off;
  }

  add_header X-Content-Type-Options nosniff;
  add_header X-Frame-Options SAMEORIGIN;
  add_header Referrer-Policy strict-origin-when-cross-origin;
  add_header X-XSS-Protection "1; mode=block";
}
EOF

# Permissions for non-root user
RUN chown -R nginx:nginx /usr/share/nginx /var/log/nginx /var/cache/nginx /etc/nginx

# Internal-only note
RUN echo "# INTERNAL-ONLY: served behind Traefik; do not publish host ports." > /etc/nginx/conf.d/README

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD wget -q --spider http://localhost:8080/ || exit 1

# Run as root; nginx will drop privileges per config
CMD ["nginx", "-g", "daemon off;"]
