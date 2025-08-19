# Multi-stage build for production optimization
FROM node:20-alpine AS builder

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies with production optimizations
RUN npm ci --only=production --no-audit --no-fund && \
    npm cache clean --force

# Copy source code
COPY . .

# Build production application
RUN npm run build

# Production stage - minimal nginx image
FROM nginx:1.25-alpine AS production

# Install health check utilities
RUN apk add --no-cache curl jq

# Create necessary directories and set permissions
RUN mkdir -p /var/cache/nginx/client_temp \
             /var/cache/nginx/proxy_temp \
             /var/cache/nginx/fastcgi_temp \
             /var/cache/nginx/uwsgi_temp \
             /var/cache/nginx/scgi_temp \
             /var/run \
             /tmp \
             /var/log/nginx && \
    chown -R nginx:nginx /var/cache/nginx \
                         /var/run \
                         /tmp \
                         /var/log/nginx

# Copy custom nginx configuration
COPY deployment/nginx/nginx.conf /etc/nginx/nginx.conf
COPY deployment/nginx/default.conf /etc/nginx/conf.d/default.conf

# Copy built application from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy health check script
COPY deployment/scripts/health-check.sh /usr/local/bin/health-check.sh
RUN chmod +x /usr/local/bin/health-check.sh

# Set permissions for existing nginx user
RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chown -R nginx:nginx /etc/nginx/conf.d && \
    chown nginx:nginx /usr/local/bin/health-check.sh

# Switch to non-root user
USER nginx

# Expose port
EXPOSE 8080

# Health check configuration
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD /usr/local/bin/health-check.sh

# Start nginx
CMD ["nginx", "-g", "daemon off;"]