# Sequential Thinking Service Dockerfile
# AI Workflow Engine - LangGraph-based Reasoning with Redis Checkpointing

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
    git \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements first for better caching
COPY app/sequentialthinking_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY app/sequentialthinking_service/ ./sequentialthinking_service/
COPY app/shared/ ./shared/

# Create necessary directories
RUN mkdir -p /data /tmp/certs-volume /etc/certs/sequentialthinking-service

# Set up Python path
ENV PYTHONPATH=/app:/app/sequentialthinking_service

# Create non-root user for security
RUN groupadd -r appgroup && useradd -r -g appgroup appuser
RUN chown -R appuser:appgroup /app /data
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

# Expose port
EXPOSE 8002

# Default command
CMD ["python", "-m", "uvicorn", "sequentialthinking_service.main:app", "--host", "0.0.0.0", "--port", "8002"]