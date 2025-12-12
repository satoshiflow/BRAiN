#!/bin/bash
# Create new nginx config for BRAiN v2

cat > /etc/nginx/conf.d/brain-v2.conf << 'EOF'
# BRAiN v2 - Simple Single-Environment Configuration

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

    # SSL Certificates (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/chat.falklabs.de/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/chat.falklabs.de/privkey.pem;

    # SSL Configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Logging
    access_log /var/log/nginx/brain-v2-access.log;
    error_log /var/log/nginx/brain-v2-error.log;

    # Max upload size
    client_max_body_size 100M;

    # Proxy to control_deck frontend
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

    # Proxy to backend API
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
}
EOF

echo "✓ Created /etc/nginx/conf.d/brain-v2.conf"

# Test nginx
nginx -t

if [ $? -eq 0 ]; then
    echo "✓ Nginx configuration is valid"
    echo ""
    echo "Reloading nginx..."
    systemctl reload nginx
    echo "✓ Nginx reloaded"
    echo ""
    echo "Test it:"
    echo "  curl https://chat.falklabs.de"
else
    echo "✗ Nginx configuration has errors"
    exit 1
fi
