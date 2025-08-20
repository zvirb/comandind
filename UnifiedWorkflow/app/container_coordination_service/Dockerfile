FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Docker CLI for container management
RUN curl -fsSL https://get.docker.com | sh

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 container_coordinator && \
    chown -R container_coordinator:container_coordinator /app

USER container_coordinator

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8030/health || exit 1

EXPOSE 8030

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8030"]