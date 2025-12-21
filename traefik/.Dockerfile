
# --- Multi-stage build ---

# Stage 1: Render dynamic.yml using Python
FROM python:3.11-alpine AS renderer
WORKDIR /render
COPY ../render_traefik_dynamic.py ./render_traefik_dynamic.py
COPY ../.env ./.env
COPY dynamic.yml ./traefik/dynamic.template.yml
RUN pip install python-dotenv
RUN python3 render_traefik_dynamic.py

# Stage 2: Final Traefik image
ARG TRAEFIK_VERSION=v3.1
FROM traefik:${TRAEFIK_VERSION}

# Set build arguments for environment variables
ARG TRAEFIK_LOG_LEVEL
ARG TRAEFIK_PORT
ARG TRAEFIK_API_PORT
ARG TRAEFIK_API_ENTRYPOINT
ARG TRAEFIK_DOCKER_NETWORK
ARG TRAEFIK_EXPOSED_BY_DEFAULT

# Create traefik user and necessary directories
USER root
RUN addgroup -g 1000 traefik 2>/dev/null || true && \
    adduser -D -u 1000 -G traefik traefik 2>/dev/null || true && \
    mkdir -p /etc/traefik /var/log/traefik && \
    chown -R traefik:traefik /etc/traefik /var/log/traefik && \
    chmod -R 755 /etc/traefik /var/log/traefik
RUN mkdir -p /etc/traefik/acme \
  && touch /etc/traefik/acme/acme.json \
  && touch /etc/traefik/acme/acme-staging.json \
  && chmod 600 /etc/traefik/acme/acme.json /etc/traefik/acme/acme-staging.json

# Copy static traefik config
COPY traefik.yml /etc/traefik/traefik.yml
# Copy rendered dynamic config from builder
COPY --from=renderer /render/traefik/dynamic.yml /etc/traefik/dynamic/dynamic.yml

# Set environment variables
ENV TRAEFIK_LOG_LEVEL=${TRAEFIK_LOG_LEVEL:-INFO} \
    TRAEFIK_PORT=${TRAEFIK_PORT:-80} \
    TRAEFIK_API_PORT=${TRAEFIK_API_PORT:-8082} \
    TRAEFIK_API_ENTRYPOINT=${TRAEFIK_API_ENTRYPOINT:-api} \
    TRAEFIK_DOCKER_NETWORK=${TRAEFIK_DOCKER_NETWORK:-base2_network} \
    TRAEFIK_EXPOSED_BY_DEFAULT=${TRAEFIK_EXPOSED_BY_DEFAULT:-false}

# Expose ports
EXPOSE ${TRAEFIK_PORT} 443 ${TRAEFIK_API_PORT}

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD traefik healthcheck --ping || exit 1

# Make entrypoint script executable and use it
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Install su-exec for privilege dropping
USER root
RUN apk add --no-cache su-exec

# Optional: Map logs and acme to host for persistence
VOLUME ["/var/log/traefik", "/etc/traefik/acme"]

# Run as root so entrypoint can fix permissions, then drop to traefik user
ENTRYPOINT ["/entrypoint.sh"]
