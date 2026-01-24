#!/bin/bash
# Fix video streaming by updating nginx config and gunicorn timeout
# Run this on the production server

set -e

echo "=== Fixing video streaming ==="

# 1. Backup current nginx config
sudo cp /etc/nginx/sites-enabled/teaching_panel /etc/nginx/sites-enabled/teaching_panel.backup.$(date +%Y%m%d_%H%M%S)

# 2. Add streaming-specific location block before general /schedule/api/
# This must come BEFORE the general /schedule/api/ block
# We use a separate location for /schedule/api/recordings/*/stream/

cat > /tmp/nginx_streaming_block.txt << 'NGINX_BLOCK'
    # Video streaming endpoint - special config for large files
    location ~ ^/schedule/api/recordings/[0-9]+/stream/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Critical for streaming - disable buffering
        proxy_buffering off;
        proxy_request_buffering off;
        
        # Large file timeouts (10 minutes for 500MB+ files)
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;
        proxy_connect_timeout 60s;
        
        # Don't try to intercept errors
        proxy_intercept_errors off;
    }
NGINX_BLOCK

echo "Created streaming config block"

# 3. Check if streaming block already exists
if grep -q "recordings.*stream" /etc/nginx/sites-enabled/teaching_panel; then
    echo "Streaming block already exists, skipping nginx update"
else
    echo "Adding streaming block to nginx config..."
    
    # Insert the streaming block before /schedule/api/ block
    # We find the line with "location /schedule/api/" and insert before it
    sudo sed -i '/location \/schedule\/api\/ {/r /tmp/nginx_streaming_block.txt' /etc/nginx/sites-enabled/teaching_panel
    
    echo "Nginx config updated"
fi

# 4. Test nginx config
echo "Testing nginx config..."
sudo nginx -t

# 5. Reload nginx
echo "Reloading nginx..."
sudo systemctl reload nginx

# 6. Update gunicorn timeout in systemd service (increase to 300s for streaming)
echo "Updating gunicorn timeout..."
if grep -q "timeout 60" /etc/systemd/system/teaching_panel.service; then
    sudo sed -i 's/--timeout 60/--timeout 300/' /etc/systemd/system/teaching_panel.service
    echo "Gunicorn timeout increased to 300s"
    
    # Reload systemd and restart service
    sudo systemctl daemon-reload
    sudo systemctl restart teaching_panel
    echo "Teaching panel service restarted"
else
    echo "Gunicorn timeout already modified or not found"
fi

echo "=== Streaming fix applied ==="
echo "Test by opening a recording in the browser"
