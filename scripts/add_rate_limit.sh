#!/bin/bash
# Добавляем rate limiting в nginx.conf

# Создаём временный файл с rate limit конфигом
cat > /tmp/rate_limit.conf << 'EOF'

    # ==================== RATE LIMITING ====================
    # Защита от DDoS и брутфорса
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=login_limit:10m rate=1r/s;
    limit_conn_zone $binary_remote_addr zone=conn_limit:10m;

EOF

# Вставляем после 'http {' в nginx.conf
sudo sed -i '/^http {/r /tmp/rate_limit.conf' /etc/nginx/nginx.conf

# Проверяем конфигурацию
sudo nginx -t && echo "NGINX_CONFIG_OK" || echo "NGINX_CONFIG_ERROR"

# Перезагружаем nginx
sudo systemctl reload nginx && echo "NGINX_RELOADED"
