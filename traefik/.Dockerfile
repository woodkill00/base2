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
  mkdir -p /etc/traefik /etc/traefik/dynamic /etc/traefik/templates /var/log/traefik && \
    chown -R traefik:traefik /etc/traefik /var/log/traefik && \
    chmod -R 755 /etc/traefik /var/log/traefik
RUN mkdir -p /etc/traefik/acme \
  && touch /etc/traefik/acme/acme.json \
  && touch /etc/traefik/acme/acme-staging.json \
  && chmod 600 /etc/traefik/acme/acme.json /etc/traefik/acme/acme-staging.json

# Copy static traefik config template (rendered at runtime)
COPY traefik/traefik.yml /etc/traefik/templates/traefik.yml.template

# Copy dynamic config template (rendered at runtime)
COPY traefik/dynamic.yml /etc/traefik/templates/dynamic.yml.template

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
  CMD traefik --configFile=/tmp/traefik.yml healthcheck || exit 1

# Make entrypoint script executable and use it
COPY traefik/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Install runtime tools
USER root
RUN apk add --no-cache su-exec gettext

# Optional: Map logs and acme to host for persistence
VOLUME ["/var/log/traefik", "/etc/traefik/acme"]

# Run as root so entrypoint can render config + fix permissions, then drop to traefik user
ENTRYPOINT ["/entrypoint.sh"]
