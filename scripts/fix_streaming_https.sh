#!/bin/bash
# Fix video streaming for HTTPS (lectio_tw1) config
set -e

# Backup
sudo cp /etc/nginx/sites-enabled/lectio_tw1 /etc/nginx/sites-enabled/lectio_tw1.backup.$(date +%Y%m%d_%H%M%S)

# Create streaming block
STREAMING_BLOCK='    # Video streaming endpoint - special config for large files
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
        
        # Don'\''t try to intercept errors
        proxy_intercept_errors off;
    }

'

# Check if already exists
if grep -q "recordings.*stream" /etc/nginx/sites-enabled/lectio_tw1; then
    echo "Streaming block already exists in lectio_tw1"
else
    echo "Adding streaming block to lectio_tw1..."
    # Create temp file with the block
    echo "$STREAMING_BLOCK" > /tmp/stream_block.txt
    
    # Insert before "location /schedule/api/ {"
    # Using awk for cleaner insertion
    sudo awk '/location \/schedule\/api\/ \{/{while(getline line < "/tmp/stream_block.txt"){print line}}1' \
        /etc/nginx/sites-enabled/lectio_tw1 > /tmp/lectio_tw1_new
    
    sudo cp /tmp/lectio_tw1_new /etc/nginx/sites-enabled/lectio_tw1
    
    echo "Block added"
fi

# Test and reload
echo "Testing nginx config..."
sudo nginx -t

echo "Reloading nginx..."
sudo systemctl reload nginx

echo "Done! Streaming should now work on HTTPS."
