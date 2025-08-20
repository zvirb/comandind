# Reasoning Service Dockerfile
# Multi-stage build for production optimization

FROM python:3.12-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    PYTHONPATH=/app:/app/shared \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash reasoning
WORKDIR /home/reasoning/app


# Development stage
FROM base as development

# Install development dependencies
RUN apt-get update && apt-get install -y \
    git \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements*.txt ./
RUN pip install -r requirements.txt

# Copy source code
COPY . .

# Change ownership to non-root user
RUN chown -R reasoning:reasoning /home/reasoning
USER reasoning

# Development server command
CMD ["python", "main.py"]


# Production stage
FROM base as production

# Install only production dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Remove unnecessary files
RUN find . -name "*.pyc" -delete \
    && find . -name "__pycache__" -type d -exec rm -rf {} + \
    && rm -rf requirements.in pytest.ini \
    && rm -rf tests/

# Change ownership to non-root user
RUN chown -R reasoning:reasoning /home/reasoning
USER reasoning

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8005/health || exit 1

# Production server command
CMD ["python", "main.py"]


# Test stage
FROM development as test

# Install test dependencies
RUN pip install pytest pytest-asyncio pytest-cov httpx faker

# Copy test files
COPY tests/ tests/
COPY pytest.ini ./

# Run tests
CMD ["python", "-m", "pytest", "tests/", "-v", "--cov=.", "--cov-report=term-missing"]