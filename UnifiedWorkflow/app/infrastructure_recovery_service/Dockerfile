FROM python:3.11-slim

# Set environment variables including shared module path
ENV PYTHONPATH=/app:/app/shared \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    python3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Run as root for Docker socket access
# Note: This service needs Docker access to manage containers
RUN chown -R root:root /app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8010/health || exit 1

# Expose port
EXPOSE 8010

# Start the service
CMD ["python", "main.py"]