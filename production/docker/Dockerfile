# Production Trading Bot Dockerfile
# Lightweight container for VPS deployment

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (minimal)
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copy production requirements and install
COPY production/requirements.txt /app/production/requirements.txt
RUN pip install --no-cache-dir -r /app/production/requirements.txt

# Copy production runner
COPY production/runner/ /app/production/runner/

# Copy core engines (only what's needed)
COPY engines/__init__.py /app/engines/__init__.py
COPY engines/regime/ /app/engines/regime/

# Copy utilities
COPY utils/ /app/utils/

# Copy models base
COPY models/__init__.py /app/models/__init__.py
COPY models/base.py /app/models/base.py

# Copy exported models (will be populated during build)
COPY production/models/ /app/models/

# Copy production config template
COPY production/configs/ /app/configs/

# Create directories for data, logs
RUN mkdir -p /app/data/equities /app/data/crypto /app/logs

# Environment variables (can be overridden in docker-compose or at runtime)
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV MODE=paper
ENV LOG_LEVEL=INFO
ENV CONFIG_PATH=/app/configs/production.yaml

# Expose health check port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=5m --timeout=10s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8080/health', timeout=5)"

# Run production trading bot
CMD ["python", "-m", "production.runner.main"]
