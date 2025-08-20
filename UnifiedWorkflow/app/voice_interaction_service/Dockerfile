# Multi-stage Dockerfile for Voice Interaction Service
# Optimized for both CPU and GPU inference

# Builder stage for dependencies
FROM python:3.11-slim-bullseye as builder

# Install system dependencies for audio processing
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    libffi-dev \
    libssl-dev \
    libasound2-dev \
    portaudio19-dev \
    ffmpeg \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Vosk model will be downloaded at runtime or mounted as volume

# Production stage
FROM python:3.11-slim-bullseye as production

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libasound2 \
    portaudio19-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create model directory (model will be downloaded at runtime)
RUN mkdir -p /app/models

# Create app directory
WORKDIR /app

# Create non-root user
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app
USER app

# Copy application code
COPY --chown=app:app . .

# Environment variables
ENV PYTHONPATH=/app
ENV VOSK_MODEL_PATH=/app/models/vosk-model-en-us-0.22
ENV WHISPER_MODEL=small.en

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8006/health')" || exit 1

# Expose port
EXPOSE 8006

# Start command
CMD ["python", "main.py"]