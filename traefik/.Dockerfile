# Dockerfile for Traefik
# Robust Traefik configuration with environment variable support

ARG TRAEFIK_VERSION=v3.0
FROM traefik:${TRAEFIK_VERSION}

# Set build arguments for environment variables
ARG TRAEFIK_LOG_LEVEL
ARG TRAEFIK_PORT
ARG TRAEFIK_API_PORT
ARG TRAEFIK_API_ENTRYPOINT
ARG TRAEFIK_DOCKER_NETWORK
ARG TRAEFIK_EXPOSED_BY_DEFAULT

# Install envsubst for environment variable substitution
USER root
RUN apk add --no-cache gettext

# Create traefik user and necessary directories
RUN addgroup -g 1000 traefik 2>/dev/null || true && \
    adduser -D -u 1000 -G traefik traefik 2>/dev/null || true && \
    mkdir -p /etc/traefik /var/log/traefik && \
    chown -R traefik:traefik /etc/traefik /var/log/traefik && \
    chmod -R 755 /etc/traefik /var/log/traefik

RUN mkdir -p /etc/traefik/acme \
  && touch /etc/traefik/acme/acme.json \
  && chmod 600 /etc/traefik/acme/acme.json

# Copy traefik configuration template
COPY traefik.yml /etc/traefik/templates/traefik.yml.template

# Create startup script for environment variable substitution
RUN echo '#!/bin/sh' > /docker-entrypoint.sh && \
    echo 'set -e' >> /docker-entrypoint.sh && \
    echo 'envsubst "\$TRAEFIK_PORT \$TRAEFIK_API_PORT \$TRAEFIK_LOG_LEVEL \$TRAEFIK_DOCKER_NETWORK \$TRAEFIK_EXPOSED_BY_DEFAULT" < /etc/traefik/templates/traefik.yml.template > /etc/traefik/traefik.yml' >> /docker-entrypoint.sh && \
    echo 'exec /entrypoint.sh "$@"' >> /docker-entrypoint.sh && \
    chmod +x /docker-entrypoint.sh

# Set environment variables
ENV TRAEFIK_LOG_LEVEL=${TRAEFIK_LOG_LEVEL:-INFO} \
    TRAEFIK_PORT=${TRAEFIK_PORT:-80} \
    TRAEFIK_API_PORT=${TRAEFIK_API_PORT:-8082} \
    TRAEFIK_API_ENTRYPOINT=${TRAEFIK_API_ENTRYPOINT:-api} \
    TRAEFIK_DOCKER_NETWORK=${TRAEFIK_DOCKER_NETWORK:-base2_network} \
    TRAEFIK_EXPOSED_BY_DEFAULT=${TRAEFIK_EXPOSED_BY_DEFAULT:-false}

# Expose ports
EXPOSE ${TRAEFIK_PORT} ${TRAEFIK_API_PORT}

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD traefik healthcheck --ping || exit 1

# Switch to non-root user
USER traefik

# Start traefik with environment variable substitution and config file
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["traefik", "--configFile=/etc/traefik/traefik.yml"]
