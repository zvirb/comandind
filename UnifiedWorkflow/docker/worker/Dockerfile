# docker/worker/Dockerfile
FROM python:3.11-slim-bookworm

# Set environment variables to prevent Python from writing .pyc files
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH=/app
# Add shared module to Python path for cross-service imports
ENV PYTHONPATH=/app:/app/shared

WORKDIR /app

# 1. Install system dependencies first. This layer is cached unless the base image changes.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gosu \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 2. Create app user for running the application
RUN groupadd -r app && useradd -r -g app app

# 3. Copy Poetry configuration files first for better caching
COPY ./pyproject.toml ./poetry.lock ./

# 4. Install Poetry and dependencies
RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-root --no-interaction --no-ansi

# 5. Copy application code. This is the most frequently changing part, so it's last.
COPY ./app/ /app/

# Set permissions
RUN chown -R app:app /app

# Add import health check script
COPY docker/worker/import_health_check.py /app/import_health_check.py

CMD ["python", "-m", "worker.main"]