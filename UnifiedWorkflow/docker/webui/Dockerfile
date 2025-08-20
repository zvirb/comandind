# webui/Dockerfile
# ==================================
# Stage 1: The Builder - Security Hardened
# This stage correctly handles the monorepo structure with security enhancements.
# ==================================
FROM node:20-alpine AS builder

# Create non-root user for build process
RUN addgroup -g 1001 -S nodejs && \
    adduser -S webui -u 1001 -G nodejs

# Set the working directory for the build.
WORKDIR /app

# Change ownership to non-root user
RUN chown -R webui:nodejs /app
USER webui

# Copy only the package files from the 'webui' subdirectory first.
# This is the most critical fix.
COPY package*.json ./

# Switch back to root to install system packages
USER root

# Install git with security considerations
RUN apk --no-cache add git && \
    apk upgrade && \
    rm -rf /var/cache/apk/*

# Switch back to webui user
USER webui

# Set npm configuration for faster and more secure installs
RUN npm config set registry https://registry.npmjs.org/ && \
    npm config set fetch-retries 3 && \
    npm config set fetch-retry-factor 10 && \
    npm config set fetch-retry-mintimeout 10000 && \
    npm config set fetch-retry-maxtimeout 60000 && \
    npm config set audit-level moderate

# Install dependencies with security checks (using npm ci for deterministic builds)
RUN npm ci --prefer-offline --progress=false

# Now, copy the rest of the SvelteKit source code from the 'webui' subdirectory.
COPY . .

# Accept API base URL as build argument - critical for frontend-backend communication
ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

# Set Node.js memory limit and build with optimizations
ENV NODE_OPTIONS="--max-old-space-size=4096"
ENV VITE_BUILD_SOURCEMAP=false

# Log API configuration for build debugging
RUN echo "Building with API Base URL: ${VITE_API_BASE_URL:-'(empty - using relative URLs)'}"

# Run the build script with timeout protection
RUN timeout 300 npm run build || (echo "Build timed out after 5 minutes" && exit 1)

# Skip prune step for faster builds - we'll copy everything from builder stage
# USER root
# RUN chown -R webui:nodejs /app && npm prune --production
# USER webui

# ==================================
# Stage 2: The Runtime - Security Hardened
# This stage creates the final, lean, and secure production image.
# ==================================
FROM node:20-alpine

# Create non-root user for runtime
RUN addgroup -g 1001 -S nodejs && \
    adduser -S webui -u 1001 -G nodejs

# Install security updates and su-exec for privilege dropping
RUN apk upgrade && \
    apk --no-cache add dumb-init su-exec && \
    rm -rf /var/cache/apk/*

WORKDIR /app

# Set secure environment variables
ENV NODE_ENV=production
ENV NODE_OPTIONS="--max-old-space-size=1024"
ENV NPM_CONFIG_AUDIT_LEVEL=moderate

# Change ownership to non-root user
RUN chown -R webui:nodejs /app

# Copy the successfully built application from the builder stage with proper ownership
COPY --from=builder --chown=webui:nodejs /app/build ./build
COPY --from=builder --chown=webui:nodejs /app/node_modules ./node_modules
COPY --from=builder --chown=webui:nodejs /app/package.json ./package.json

# Switch to non-root user
USER webui

# Expose the port the Node server will run on (non-privileged port)
EXPOSE 3000

# Add health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD node -e "require('http').get('http://localhost:3000/health', (res) => process.exit(res.statusCode === 200 ? 0 : 1)).on('error', () => process.exit(1))" || \
    wget --no-verbose --tries=1 --spider http://localhost:3000/health || exit 1

# Use dumb-init to handle signals properly and start the application
ENTRYPOINT ["dumb-init", "--"]
CMD [ "node", "build/index.js" ]