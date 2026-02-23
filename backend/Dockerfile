FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Cache-bust: 2026-02-23-1029
# Fix: Set PYTHONPATH to support both import styles
ENV PYTHONPATH=/app:/app/backend

# Install system dependencies
RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy entire backend directory structure
COPY . .

EXPOSE 8000

# Use unified entry point (v0.3.0+)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
