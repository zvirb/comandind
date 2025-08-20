# Learning Service Dockerfile
# Multi-stage build for production optimization

# Build stage
FROM python:3.11-slim as builder

# Set build environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Production stage
FROM python:3.11-slim as production

# Set production environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app:/app/shared \
    LEARNING_PORT=8005 \
    LEARNING_LOG_LEVEL=INFO

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r learning && useradd -r -g learning learning

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Create application directory
WORKDIR /app

# Copy application code
COPY . .

# Set ownership
RUN chown -R learning:learning /app

# Switch to non-root user
USER learning

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${LEARNING_PORT}/health || exit 1

# Expose port
EXPOSE ${LEARNING_PORT}

# Start application
CMD ["python", "-m", "uvicorn", "main_minimal:app", "--host", "0.0.0.0", "--port", "8005"]

# Development stage
FROM production as development

# Switch back to root for development tools
USER root

# Install development dependencies
RUN apt-get update && apt-get install -y \
    git \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Install development Python packages
RUN pip install \
    pytest-xdist \
    black \
    flake8 \
    mypy \
    pre-commit

# Switch back to learning user
USER learning

# Set development environment
ENV LEARNING_DEBUG=true

# Development command with hot reload
CMD ["python", "-m", "uvicorn", "main_minimal:app", "--host", "0.0.0.0", "--port", "8005", "--reload"]