# Multi-stage Dockerfile for Coordination Service
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
# Add shared module to Python path for cross-service imports
ENV PYTHONPATH=/app:/app/shared

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r coordination && useradd -r -g coordination coordination

# Development stage
FROM base as development

# Install development dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy source code
COPY . .

# Change ownership to coordination user
RUN chown -R coordination:coordination /app
USER coordination

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Development command
CMD ["python", "main.py"]

# Production stage
FROM base as production

# Install only production dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy source code
COPY . .

# Remove development files
RUN rm -rf tests/ *.md requirements.txt Dockerfile* \
    && find . -name "*.pyc" -delete \
    && find . -name "__pycache__" -delete

# Change ownership to coordination user
RUN chown -R coordination:coordination /app
USER coordination

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Production command
CMD ["python", "main.py"]

# Default to production
FROM production