# Dockerfile for React App (Production-like)
# Build with Node, serve static build via Nginx (internal-only behind Traefik)

# Declare all ARG used in any FROM before the first FROM
ARG DOCKER_LIBRARY_REGISTRY=public.ecr.aws/docker/library
ARG NODE_VERSION=24.13.1-alpine
ARG NGINX_VERSION=1.27.3-alpine
FROM ${DOCKER_LIBRARY_REGISTRY}/node:${NODE_VERSION} AS build

WORKDIR /app

# Copy package files
COPY package*.json ./
COPY .npmrc ./
RUN npm ci --legacy-peer-deps --no-audit --no-fund && npm cache clean --force

COPY . .

# Keep production builds deterministic on small machines.
ENV CI=true
ENV GENERATE_SOURCEMAP=false

ARG REACT_APP_GOOGLE_CLIENT_ID
ENV REACT_APP_GOOGLE_CLIENT_ID=${REACT_APP_GOOGLE_CLIENT_ID}
ARG SITE_PROFILE=base2-obsidian
ENV VITE_SITE_PROFILE=${SITE_PROFILE}

# Create production build
RUN npm run build

# ---------- Runtime: Nginx to serve static build ----------
FROM ${DOCKER_LIBRARY_REGISTRY}/nginx:${NGINX_VERSION}

# Upgrade base Alpine packages and install minimal tools (drop gettext)
RUN apk update \
  && apk upgrade --no-cache \
  && apk add --no-cache wget

# Copy build artifacts to Nginx html directory
COPY --from=build /app/build /usr/share/nginx/html

# Checked-in configs are portable across the supported classic and BuildKit frontends.
COPY nginx/nginx.conf /etc/nginx/nginx.conf
COPY nginx/default.conf /etc/nginx/conf.d/default.conf

# Permissions for non-root user
RUN chown -R nginx:nginx /usr/share/nginx /var/log/nginx /var/cache/nginx /etc/nginx

# Internal-only note
RUN echo "# INTERNAL-ONLY: served behind Traefik; do not publish host ports." > /etc/nginx/conf.d/README

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD wget -q --spider http://localhost:8080/ || exit 1

# Run as root; nginx will drop privileges per config
CMD ["nginx", "-g", "daemon off;"]
