#!/bin/bash
# Quick script to fix Nginx configuration on server

echo "=== Fixing Nginx Configuration ==="

# 1. Check and fix duplicate directive in chat.conf
if [ -f "/etc/nginx/conf.d/chat.conf" ]; then
    echo "Found chat.conf - checking for duplicate directives..."

    # Backup original
    cp /etc/nginx/conf.d/chat.conf /etc/nginx/conf.d/chat.conf.backup

    # Remove the duplicate proxy_connect_timeout line at line 39
    sed -i '39{/proxy_connect_timeout/d;}' /etc/nginx/conf.d/chat.conf

    echo "Fixed duplicate directive in chat.conf"
fi

# 2. Test Nginx configuration
echo ""
echo "Testing Nginx configuration..."
nginx -t

if [ $? -eq 0 ]; then
    echo "✓ Nginx configuration is valid"

    # 3. Restart Nginx
    echo ""
    echo "Restarting Nginx..."
    systemctl restart nginx

    if [ $? -eq 0 ]; then
        echo "✓ Nginx restarted successfully"
        systemctl status nginx | head -5
    else
        echo "✗ Failed to restart Nginx"
        exit 1
    fi
else
    echo "✗ Nginx configuration has errors"
    echo "Check the errors above and fix manually"
    exit 1
fi

echo ""
echo "=== Nginx Fix Complete ==="
