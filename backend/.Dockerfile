# Dockerfile for Backend API
# Node.js Express Authentication Server

ARG NODE_VERSION=18-alpine
FROM node:${NODE_VERSION}

# Set working directory
WORKDIR /app

# Install build tools only if native modules are needed
RUN apk add --no-cache python3 make g++

# Copy package files
COPY package*.json ./

# Install production dependencies only
ENV NODE_ENV=production
RUN npm ci --omit=dev && npm cache clean --force

# Copy application code
COPY . .

# Create non-root user
RUN addgroup -g 1001 -S nodegroup && \
  adduser -S nodeuser -u 1001 -G nodegroup && \
  chown -R nodeuser:nodegroup /app

# Switch to non-root user
USER nodeuser

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD-SHELL wget --quiet --tries=1 --spider "http://localhost:${PORT:-5000}/api/health" || exit 1

CMD ["node", "server.js"]
