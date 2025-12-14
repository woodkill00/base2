# Dockerfile for PostgreSQL
# INTERNAL-ONLY: This service must run behind Traefik or internal networks.
# Do NOT publish host ports; use service discovery and network-only access.
# Robust PostgreSQL configuration with environment variable support

ARG POSTGRES_VERSION=16-alpine
FROM postgres:${POSTGRES_VERSION}

# Set build arguments for environment variables
ARG POSTGRES_USER
ARG POSTGRES_PASSWORD
ARG POSTGRES_DB

# Set environment variables
ENV POSTGRES_USER=${POSTGRES_USER} \
    POSTGRES_PASSWORD=${POSTGRES_PASSWORD} \
    POSTGRES_DB=${POSTGRES_DB} \
    PGDATA=/var/lib/postgresql/data/pgdata

# Create directory for init scripts
RUN mkdir -p /docker-entrypoint-initdb.d

# Copy initialization script
COPY init.sql /docker-entrypoint-initdb.d/

# Set proper permissions
RUN chown -R postgres:postgres /docker-entrypoint-initdb.d && \
    chmod -R 755 /docker-entrypoint-initdb.d

# Configure PostgreSQL for better performance and security
RUN echo "# Custom PostgreSQL Configuration" > /usr/local/share/postgresql/postgresql.conf.sample.custom && \
    echo "listen_addresses = '*'" >> /usr/local/share/postgresql/postgresql.conf.sample.custom && \
    echo "max_connections = 100" >> /usr/local/share/postgresql/postgresql.conf.sample.custom && \
    echo "shared_buffers = 128MB" >> /usr/local/share/postgresql/postgresql.conf.sample.custom && \
    echo "effective_cache_size = 512MB" >> /usr/local/share/postgresql/postgresql.conf.sample.custom && \
    echo "maintenance_work_mem = 64MB" >> /usr/local/share/postgresql/postgresql.conf.sample.custom && \
    echo "checkpoint_completion_target = 0.9" >> /usr/local/share/postgresql/postgresql.conf.sample.custom && \
    echo "wal_buffers = 16MB" >> /usr/local/share/postgresql/postgresql.conf.sample.custom && \
    echo "default_statistics_target = 100" >> /usr/local/share/postgresql/postgresql.conf.sample.custom && \
    echo "random_page_cost = 1.1" >> /usr/local/share/postgresql/postgresql.conf.sample.custom && \
    echo "effective_io_concurrency = 200" >> /usr/local/share/postgresql/postgresql.conf.sample.custom && \
    echo "work_mem = 4MB" >> /usr/local/share/postgresql/postgresql.conf.sample.custom && \
    echo "min_wal_size = 1GB" >> /usr/local/share/postgresql/postgresql.conf.sample.custom && \
    echo "max_wal_size = 4GB" >> /usr/local/share/postgresql/postgresql.conf.sample.custom && \
    echo "log_timezone = 'UTC'" >> /usr/local/share/postgresql/postgresql.conf.sample.custom && \
    echo "datestyle = 'iso, mdy'" >> /usr/local/share/postgresql/postgresql.conf.sample.custom && \
    echo "timezone = 'UTC'" >> /usr/local/share/postgresql/postgresql.conf.sample.custom && \
    echo "lc_messages = 'en_US.utf8'" >> /usr/local/share/postgresql/postgresql.conf.sample.custom && \
    echo "lc_monetary = 'en_US.utf8'" >> /usr/local/share/postgresql/postgresql.conf.sample.custom && \
    echo "lc_numeric = 'en_US.utf8'" >> /usr/local/share/postgresql/postgresql.conf.sample.custom && \
    echo "lc_time = 'en_US.utf8'" >> /usr/local/share/postgresql/postgresql.conf.sample.custom

# Expose PostgreSQL port
ARG POSTGRES_PORT=5432
EXPOSE ${POSTGRES_PORT}

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB} || exit 1

# Use the default entrypoint and command from the base image
# ENTRYPOINT and CMD are inherited from postgres base image
