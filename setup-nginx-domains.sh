#!/bin/bash
# Complete Nginx Configuration for BRAiN v2
# Sets up:
# - chat.falklabs.de → OpenWebUI (port 8080)
# - brain.falklabs.de → Control Deck (port 3000) + API (port 8000)

echo "=== Setting up Nginx Configuration for BRAiN v2 ==="

# 1. Remove conflicting config
echo "1. Removing conflicting brain-v2.conf..."
rm -f /etc/nginx/conf.d/brain-v2.conf

# 2. Create chat.falklabs.de config (OpenWebUI)
echo "2. Creating chat.falklabs.de config..."
cat > /etc/nginx/conf.d/chat.falklabs.conf << 'EOF'
# chat.falklabs.de - OpenWebUI Interface

# Redirect HTTP to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name chat.falklabs.de;

    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS Server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name chat.falklabs.de;

    # SSL Certificates
    ssl_certificate /etc/letsencrypt/live/chat.falklabs.de/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/chat.falklabs.de/privkey.pem;

    # SSL Configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Logging
    access_log /var/log/nginx/chat-access.log;
    error_log /var/log/nginx/chat-error.log;

    # Max upload size
    client_max_body_size 100M;

    # Proxy to OpenWebUI
    location / {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;

        # Headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
}
EOF
echo "✓ Created /etc/nginx/conf.d/chat.falklabs.conf"

# 3. Create brain.falklabs.de config (Control Deck + API)
echo "3. Creating brain.falklabs.de config..."
cat > /etc/nginx/conf.d/brain.falklabs.conf << 'EOF'
# brain.falklabs.de - BRAiN Control Deck + API

# Redirect HTTP to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name brain.falklabs.de;

    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS Server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name brain.falklabs.de;

    # SSL Certificates
    ssl_certificate /etc/letsencrypt/live/brain.falklabs.de/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/brain.falklabs.de/privkey.pem;

    # SSL Configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Logging
    access_log /var/log/nginx/brain-access.log;
    error_log /var/log/nginx/brain-error.log;

    # Max upload size
    client_max_body_size 100M;

    # Proxy to Backend API
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;

        # Headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # Proxy to Control Deck Frontend
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;

        # Headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
}
EOF
echo "✓ Created /etc/nginx/conf.d/brain.falklabs.conf"

# 4. Test nginx configuration
echo ""
echo "4. Testing Nginx configuration..."
nginx -t

if [ $? -eq 0 ]; then
    echo "✓ Nginx configuration is valid"
    echo ""
    echo "5. Reloading nginx..."
    systemctl reload nginx
    echo "✓ Nginx reloaded"
    echo ""
    echo "=== Configuration Complete ==="
    echo ""
    echo "📋 Domain Setup:"
    echo "  ✅ chat.falklabs.de  → OpenWebUI (port 8080)"
    echo "  ✅ brain.falklabs.de → Control Deck (port 3000) + API (port 8000)"
    echo ""
    echo "🧪 Test URLs:"
    echo "  curl https://chat.falklabs.de"
    echo "  curl https://brain.falklabs.de"
    echo "  curl https://brain.falklabs.de/api/health"
else
    echo "✗ Nginx configuration has errors"
    echo ""
    echo "⚠️  Possible issues:"
    echo "  - SSL certificates might not exist yet"
    echo "  - Run: certbot certonly --nginx -d brain.falklabs.de"
    exit 1
fi
