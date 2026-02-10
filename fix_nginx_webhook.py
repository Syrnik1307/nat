#!/usr/bin/env python3
"""Fix Nginx config to add Zoom webhook proxy location."""
import re

CONFIG_PATH = '/etc/nginx/sites-enabled/lectiospace.ru'

with open(CONFIG_PATH, 'r') as f:
    content = f.read()

# Remove any broken webhook block first
content = re.sub(
    r'    # Zoom Webhook \(recording\.completed.*?\n    \}\n\n',
    '',
    content,
    flags=re.DOTALL
)

# Build the new block
webhook_block = """    # Zoom Webhook (recording.completed events from Zoom)
    location /schedule/webhook/ {
        proxy_pass http://django_lectiospace/schedule/webhook/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 30s;
        proxy_read_timeout 60s;
    }

"""

# Insert before the '/schedule/api/' location block
target = '    # Schedule API direct path (for /schedule/api/*)\n    location /schedule/api/'
if target in content:
    content = content.replace(target, webhook_block + target)
    print('Webhook location block inserted successfully')
else:
    print('ERROR: Could not find insertion point')
    exit(1)

with open(CONFIG_PATH, 'w') as f:
    f.write(content)

print('Config written. Run: nginx -t && systemctl reload nginx')
