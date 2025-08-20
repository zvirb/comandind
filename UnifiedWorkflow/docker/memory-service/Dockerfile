# Memory Service Dockerfile
# AI Workflow Engine - Hybrid Memory & Knowledge Graph Microservice

FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY app/memory_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy memory service code
COPY app/memory_service/ ./memory_service/
COPY app/shared/ ./shared/

# Create necessary directories
RUN mkdir -p /data /tmp/certs-volume /etc/certs/memory-service

# Set up Python path
ENV PYTHONPATH=/app:/app/memory_service

# Create non-root user for security
RUN groupadd -r appgroup && useradd -r -g appgroup appuser
RUN chown -R appuser:appgroup /app /data
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Expose port
EXPOSE 8001

# Default command
CMD ["python", "-m", "uvicorn", "memory_service.main:app", "--host", "0.0.0.0", "--port", "8001"]