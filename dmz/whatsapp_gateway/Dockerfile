FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY *.py ./

# Health check endpoint port
EXPOSE 8002

# Run gateway
CMD ["python", "-u", "gateway.py"]
