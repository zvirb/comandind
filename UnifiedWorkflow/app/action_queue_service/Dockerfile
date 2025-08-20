# Dockerfile for Action Queue Service with Celery

FROM python:3.11-slim-bullseye

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Create non-root user
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=app:app . .

# Switch to non-root user
USER app

# Environment variables
ENV PYTHONPATH=/app
ENV CELERY_APP=action_queue_service
ENV RABBITMQ_URL=amqp://admin:admin123@rabbitmq:5672//
ENV REDIS_URL=redis://redis:6379/0

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8007/health || exit 1

# Expose port
EXPOSE 8007

# Default command (can be overridden for worker)
CMD ["python", "main.py"]