# Dockerfile for pgAdmin
# INTERNAL-ONLY: Prefer access via Traefik with auth/middleware or from trusted networks.
# Do NOT publish host ports directly.
# Robust pgAdmin configuration with environment variable support

ARG PGADMIN_VERSION=latest
FROM dpage/pgadmin4:${PGADMIN_VERSION}

# Set build arguments for environment variables
ARG PGADMIN_DEFAULT_EMAIL
ARG PGADMIN_DEFAULT_PASSWORD
ARG PGADMIN_CONFIG_SERVER_MODE

# Set environment variables
ENV PGADMIN_DEFAULT_EMAIL=${PGADMIN_DEFAULT_EMAIL} \
    PGADMIN_DEFAULT_PASSWORD=${PGADMIN_DEFAULT_PASSWORD} \
    PGADMIN_CONFIG_SERVER_MODE=${PGADMIN_CONFIG_SERVER_MODE} \
    PGADMIN_CONFIG_MASTER_PASSWORD_REQUIRED=False \
    PGADMIN_LISTEN_PORT=80


# Expose pgAdmin port
ARG PGADMIN_PORT=8080
ENV PGADMIN_LISTEN_PORT=${PGADMIN_PORT}
EXPOSE ${PGADMIN_PORT}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:${PGADMIN_PORT}/misc/ping || exit 1

# Use the default entrypoint and command from the base image
# ENTRYPOINT and CMD are inherited from dpage/pgadmin4 base image
