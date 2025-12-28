# Dockerfile for Farnsworth Fusor Web API Server
# Optimized for Cloud Run and containerized deployments

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies if needed
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file (from project root relative to this file)
COPY requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install gunicorn for production server
RUN pip install --no-cache-dir gunicorn

# Copy application code
COPY . /app/

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port (Cloud Run will set PORT env var)
EXPOSE 8080

# Environment variables (can be overridden)
ENV PORT=8080
ENV TARGET_IP=192.168.0.2
ENV TCP_COMMAND_PORT=2222
ENV UDP_DATA_PORT=12345
ENV UDP_STATUS_PORT=8888
ENV FLASK_ENV=production

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:$PORT/api/status', timeout=2)" || exit 1

# Run with gunicorn (production-ready WSGI server)
# Cloud Run will set PORT env var automatically
CMD exec gunicorn \
    --bind 0.0.0.0:$PORT \
    --workers 1 \
    --threads 8 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    web_api_server:app

