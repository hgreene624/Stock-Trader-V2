# Production Trading Bot Dockerfile
# Lightweight container for VPS deployment

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    curl \
    ca-certificates \
    nano \
    && rm -rf /var/lib/apt/lists/*

# Add Claude CLI to PATH (before installation so directory is ready)
ENV PATH="/root/.local/bin:${PATH}"

# Install Claude Code CLI - Manual download (install script doesn't work in Docker)
RUN mkdir -p /root/.local/bin && \
    VERSION=$(curl -fsSL https://storage.googleapis.com/claude-code-dist-86c565f3-f756-42ad-8dfa-d59b1c096819/claude-code-releases/stable) && \
    curl -fsSL -o /root/.local/bin/claude \
      https://storage.googleapis.com/claude-code-dist-86c565f3-f756-42ad-8dfa-d59b1c096819/claude-code-releases/${VERSION}/linux-x64/claude && \
    chmod +x /root/.local/bin/claude && \
    /root/.local/bin/claude --version

# Copy production requirements and install
COPY production/requirements.txt /app/production/requirements.txt
RUN pip install --no-cache-dir -r /app/production/requirements.txt

# Copy production runner, dashboard, and scripts
COPY production/runner/ /app/production/runner/
COPY production/scripts/ /app/production/scripts/
COPY production/dashboard.py /app/production/dashboard.py
COPY production/__init__.py /app/production/__init__.py

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

# Copy agent documentation
COPY production/AGENTS.md /app/AGENTS.md

# Copy entrypoint scripts
COPY production/docker/entrypoint.sh /app/entrypoint.sh
COPY production/docker/dashboard-entrypoint.sh /app/dashboard-entrypoint.sh
RUN chmod +x /app/entrypoint.sh /app/dashboard-entrypoint.sh

# Create directories for data, logs, and .env location
RUN mkdir -p /app/data/equities /app/data/crypto /app/logs /app/production/docker

# Copy cached historical data into the image
COPY production/docker/data/equities/*.parquet /app/data/equities/

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

# Set entrypoint to handle .env file creation
ENTRYPOINT ["/app/entrypoint.sh"]

# Run production trading bot
CMD ["python", "-m", "production.runner.main"]
