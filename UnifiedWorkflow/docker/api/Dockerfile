# This is a plausible Dockerfile for the api service.
# It is based on common practices for Python applications.
FROM python:3.11-slim

# Set environment variables to prevent Python from writing .pyc files
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH=/app
# Add shared module to Python path for cross-service imports
ENV PYTHONPATH=/app:/app/shared

# Install system dependencies
# - build-essential: for compiling some Python packages
# - postgresql-client: for the `psql` command used in run-migrate.sh
# - curl & gcc: to build su-exec for privilege dropping
# - libffi-dev & libssl-dev: for bcrypt compilation
# - pkg-config: for package configuration
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    postgresql-client \
    curl \
    gcc \
    libffi-dev \
    libssl-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install su-exec, used by the entrypoint-wrapper.sh script
RUN curl -sSL https://github.com/ncopa/su-exec/archive/master.tar.gz | tar xz -C /tmp \
    && make -C /tmp/su-exec-master \
    && mv /tmp/su-exec-master/su-exec /usr/local/bin/ \
    && rm -rf /tmp/su-exec-master

# Create a non-root user and group
RUN addgroup --system app && adduser --system --ingroup app app

WORKDIR /app

# Copy the entire project
COPY . /app

# Temporary hotfix: Install critical dependencies directly with pip
RUN pip install --no-cache-dir \
    fastapi==0.111.0 \
    uvicorn[standard]==0.30.1 \
    sqlalchemy==2.0.31 \
    alembic==1.13.1 \
    psycopg2-binary==2.9.10 \
    pyjwt==2.10.1 \
    cryptography==42.0.0 \
    python-multipart==0.0.9 \
    pydantic-settings==2.3.4 \
    pwdlib[argon2]==0.2.1 \
    aiofiles==23.2.1 \
    redis==5.0.7

# Set permissions
RUN chown -R app:app /app

# Add import health check script
COPY docker/api/import_health_check.py /app/import_health_check.py