# Dockerfile – BRAIN Backend Image (Root)

FROM python:3.11-slim

# ---------------------------
# System packages
# ---------------------------
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
  && rm -rf /var/lib/apt/lists/*

# ---------------------------
# Working directory
# ---------------------------
WORKDIR /app

# ---------------------------
# Python Dependencies
# ---------------------------
# requirements.txt liegt im Root (für Backend)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---------------------------
# Application Code
# ---------------------------
# Wir kopieren das komplette Repo ins Image – PYTHONPATH=/app
COPY . .

# ---------------------------
# Exposed Port
# ---------------------------
EXPOSE 8000

# ---------------------------
# Environment Defaults
# ---------------------------
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    REDIS_URL=redis://redis:6379/0

# ---------------------------
# Start Command
# ---------------------------
# backend/main.py enthält: app = FastAPI()
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
