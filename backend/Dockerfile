FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy entire backend directory structure
COPY . .

# Copy and make entrypoint scripts executable
COPY worker-entrypoint.sh /app/worker-entrypoint.sh
COPY beat-entrypoint.sh /app/beat-entrypoint.sh
RUN chmod +x /app/worker-entrypoint.sh /app/beat-entrypoint.sh

EXPOSE 8000

# Use unified entry point (v0.3.0+)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
