# Multi-stage Docker build for Perception Service
# Optimized for production deployment with minimal attack surface

# Stage 1: Build stage with full development dependencies
FROM python:3.12-slim-bookworm AS builder

# Set build arguments
ARG BUILD_DATE=unknown
ARG VCS_REF=unknown
ARG VERSION=1.0.0

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r perception && useradd -r -g perception -d /app -s /bin/bash perception

# Set working directory
WORKDIR /app

# Copy requirements first for better Docker layer caching
COPY requirements.txt .
COPY requirements.in* .

# Install Python dependencies
RUN python -m pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Install the application in development mode
RUN pip install -e .

# Create necessary directories
RUN mkdir -p /app/logs /app/tmp && \
    chown -R perception:perception /app

# Stage 2: Production stage with minimal dependencies
FROM python:3.12-slim-bookworm AS production

# Set build metadata
LABEL org.opencontainers.image.created=$BUILD_DATE \
      org.opencontainers.image.authors="AIWFE Team" \
      org.opencontainers.image.url="https://github.com/aiwfe/aiwfe" \
      org.opencontainers.image.documentation="https://docs.aiwfe.com" \
      org.opencontainers.image.source="https://github.com/aiwfe/aiwfe" \
      org.opencontainers.image.version=$VERSION \
      org.opencontainers.image.revision=$VCS_REF \
      org.opencontainers.image.vendor="AIWFE" \
      org.opencontainers.image.title="Perception Service" \
      org.opencontainers.image.description="AI-powered image analysis and vector generation service"

# Install minimal runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get autoremove -y \
    && apt-get clean

# Create non-root user
RUN groupadd -r perception && useradd -r -g perception -d /app -s /bin/bash perception

# Set working directory
WORKDIR /app

# Copy Python environment from builder stage
COPY --from=builder /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --from=builder --chown=perception:perception /app /app

# Create required directories with proper permissions
RUN mkdir -p /app/logs /app/tmp /app/data && \
    chown -R perception:perception /app && \
    chmod -R 755 /app

# Switch to non-root user
USER perception

# Set environment variables
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Expose port
EXPOSE 8001

# Default command
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--log-level", "info"]

# Development stage for local development
FROM builder AS development

# Install development dependencies
RUN pip install --no-cache-dir \
    pytest \
    pytest-asyncio \
    pytest-cov \
    black \
    flake8 \
    mypy \
    isort

# Set development environment
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PERCEPTION_DEBUG=true \
    PERCEPTION_LOG_LEVEL=DEBUG

# Switch to non-root user
USER perception

# Development command with auto-reload
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--reload", "--log-level", "debug"]