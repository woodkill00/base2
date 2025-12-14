# Dockerfile for Nginx
# Robust nginx configuration with environment variable support

ARG NGINX_VERSION=1.25-alpine
FROM nginx:${NGINX_VERSION}

# Install envsubst and curl for health checks
RUN apk add --no-cache gettext curl

# Set build arguments for environment variables
ARG NGINX_WORKER_PROCESSES=auto
ARG NGINX_WORKER_CONNECTIONS=1024
ARG NGINX_PORT=80

# Create non-root user for security
RUN addgroup -g 101 -S nginx && \
    adduser -S -D -H -u 101 -h /var/cache/nginx -s /sbin/nologin -G nginx -g nginx nginx 2>/dev/null || true

# Create necessary directories with proper permissions
RUN mkdir -p /var/cache/nginx /var/log/nginx /etc/nginx/conf.d && \
    chown -R nginx:nginx /var/cache/nginx /var/log/nginx /etc/nginx/conf.d && \
    chmod -R 755 /var/cache/nginx /var/log/nginx

# Copy nginx configuration template
COPY nginx.conf /etc/nginx/templates/nginx.conf.template

# Create startup script for environment variable substitution
# Script runs as root to generate config, then nginx handles user switching internally
RUN echo '#!/bin/sh' > /docker-entrypoint.sh && \
    echo 'set -e' >> /docker-entrypoint.sh && \
    echo '# Generate nginx config from template as root' >> /docker-entrypoint.sh && \
    echo 'envsubst "\$NGINX_WORKER_PROCESSES \$NGINX_WORKER_CONNECTIONS \$NGINX_PORT" < /etc/nginx/templates/nginx.conf.template > /etc/nginx/nginx.conf' >> /docker-entrypoint.sh && \
    echo '# Set proper permissions on generated config' >> /docker-entrypoint.sh && \
    echo 'chown nginx:nginx /etc/nginx/nginx.conf' >> /docker-entrypoint.sh && \
    echo 'chmod 644 /etc/nginx/nginx.conf' >> /docker-entrypoint.sh && \
    echo '# Start nginx (it will drop privileges based on user directive in config)' >> /docker-entrypoint.sh && \
    echo 'exec nginx -g "daemon off;"' >> /docker-entrypoint.sh && \
    chmod +x /docker-entrypoint.sh

# Set environment variables
ENV NGINX_WORKER_PROCESSES=${NGINX_WORKER_PROCESSES} \
    NGINX_WORKER_CONNECTIONS=${NGINX_WORKER_CONNECTIONS} \
    NGINX_PORT=${NGINX_PORT}

# Expose port
EXPOSE ${NGINX_PORT}

# Add health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -fsS http://localhost:${NGINX_PORT}/ >/dev/null || exit 1

# Note: Not switching to nginx user here - entrypoint runs as root to generate config
# Nginx itself will drop privileges based on the 'user' directive in nginx.conf

# Start nginx with environment variable substitution
ENTRYPOINT ["/docker-entrypoint.sh"]
