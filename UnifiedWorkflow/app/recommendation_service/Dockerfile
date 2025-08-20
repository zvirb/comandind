# Dockerfile for Recommendation Engine Service

FROM python:3.11-slim-bullseye

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    gfortran \
    libopenblas-dev \
    liblapack-dev \
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

# Create models directory
RUN mkdir -p /app/models && chown app:app /app/models

# Switch to non-root user
USER app

# Environment variables
ENV PYTHONPATH=/app
ENV KAFKA_SERVERS=kafka:9092
ENV REDIS_URL=redis://redis:6379

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8009/health || exit 1

# Expose port
EXPOSE 8009

# Start command
CMD ["python", "main.py"]