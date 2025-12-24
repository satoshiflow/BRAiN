# ============================================================================
# BRAiN DMZ - Telegram Gateway Dockerfile
# ============================================================================
#
# Minimal transport-only gateway for Telegram Bot API
# No business logic - only message forwarding to Core API
#
# Security:
#   - Runs as non-root user
#   - Minimal dependencies
#   - No persistent state
#   - ENV-based configuration only
#
# ============================================================================

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install minimal dependencies
RUN pip install --no-cache-dir \
    fastapi==0.109.0 \
    uvicorn[standard]==0.27.0 \
    httpx==0.26.0 \
    pydantic==2.5.3 \
    python-dotenv==1.0.0

# Create non-root user
RUN useradd -m -u 1000 gateway && \
    chown -R gateway:gateway /app

# Copy application code
COPY --chown=gateway:gateway main.py .

# Switch to non-root user
USER gateway

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
