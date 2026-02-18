#!/bin/bash
# Build AXEllm Image locally and push to GHCR
# Run this on the server or any machine with Docker

set -e

echo "🚀 Building AXEllm Image..."

# Configuration
IMAGE_NAME="ghcr.io/satoshiflow/brain/axellm"
TAG="latest"

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    echo "❌ Error: main.py not found. Please run from services/axellm/ directory"
    exit 1
fi

# Docker Login (will prompt for token)
echo ""
echo "🔐 Docker Login to GHCR required"
echo "Get token from: https://github.com/settings/tokens (scopes: write:packages, read:packages)"
echo ""
read -p "Enter GitHub Token: " GITHUB_TOKEN
echo ""

echo "$GITHUB_TOKEN" | docker login ghcr.io -u satoshiflow --password-stdin

# Build image
echo ""
echo "🔨 Building image..."
docker build -t ${IMAGE_NAME}:${TAG} .

# Push image
echo ""
echo "📤 Pushing to GHCR..."
docker push ${IMAGE_NAME}:${TAG}

# Verify
echo ""
echo "✅ Image built and pushed successfully!"
echo ""
echo "Image: ${IMAGE_NAME}:${TAG}"
echo ""
echo "Next steps:"
echo "1. Make package public: https://github.com/users/satoshiflow/packages"
echo "2. Deploy in Coolify with docker-compose"
