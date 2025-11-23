# Production Trading Bot Dockerfile
# Fast builds using pre-built base image with dependencies
#
# First time setup (or when requirements.txt changes):
#   docker build -f production/docker/Dockerfile.base -t trading-bot-base:latest .
#
# Regular builds (fast - just copies code):
#   docker build -f production/docker/Dockerfile -t trading-bot:latest .

# Use base image with all dependencies pre-installed
# Fall back to python:3.11-slim if base not available (will be slower)
ARG BASE_IMAGE=trading-bot-base:latest
FROM ${BASE_IMAGE}

# Set working directory
WORKDIR /app

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

# Copy all configs (accounts, models, profiles, etc.)
COPY configs/ /app/configs/

# Copy agent documentation
COPY production/AGENTS.md /app/AGENTS.md

# Copy VERSION file for dashboard display
COPY production/deploy/VERSION /app/VERSION

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

# Expose health check ports for multiple accounts
EXPOSE 8080 8081 8082

# Health check (checks first account)
HEALTHCHECK --interval=5m --timeout=10s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8080/health', timeout=5)"

# Set entrypoint to handle .env file creation
ENTRYPOINT ["/app/entrypoint.sh"]

# Run multi-account orchestrator (default) or single account
# Use: docker run ... trading-bot  (runs all accounts from accounts.yaml)
# Use: docker run ... trading-bot python -m production.runner.main  (single account, uses env vars)
CMD ["python", "-m", "production.runner.multi_main"]
