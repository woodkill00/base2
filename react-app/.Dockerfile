# Dockerfile for React App
# Build stage for React application with environment variable support

ARG NODE_VERSION=18-alpine
FROM node:${NODE_VERSION} AS build

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install \
  && npm cache clean --force \
  && rm -rf /tmp/* /app/node_modules/.cache

# Copy application source
COPY . .

# Build arguments for environment variables
ARG REACT_APP_API_URL
ENV REACT_APP_API_URL=${REACT_APP_API_URL}

# Build the application (if needed)
# RUN npm run build

# Production stage
FROM node:${NODE_VERSION}

# Create non-root user for security
RUN addgroup -g 1001 -S nodejs && \
    adduser -S reactuser -u 1001 -G nodejs

# Set working directory
WORKDIR /app

# Copy dependencies and application from build stage
COPY --from=build --chown=reactuser:nodejs /app/node_modules ./node_modules
COPY --from=build --chown=reactuser:nodejs /app/package*.json ./
COPY --chown=reactuser:nodejs . .

# Optional: Clean up any temp/bloat files in production image
RUN rm -rf /tmp/* /app/node_modules/.cache

# Switch to non-root user
USER reactuser

# Expose port
ARG REACT_APP_PORT=3000
EXPOSE ${REACT_APP_PORT}

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD node -e "require('http').get('http://localhost:${REACT_APP_PORT}', (r) => {process.exit(r.statusCode === 200 ? 0 : 1)})"

# Start the application
CMD ["npm", "start"]
