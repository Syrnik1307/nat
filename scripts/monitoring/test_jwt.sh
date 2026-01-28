#!/bin/bash
# Тест JWT логина
set -e

echo "Testing JWT login for smoke_teacher..."

# Используем внутренний URL (через gunicorn напрямую не редиректит)
result=$(curl -s -w "\n%{http_code}" -X POST https://lectio.tw1.ru/api/jwt/token/ \
  -H "Content-Type: application/json" \
  -d '{"email":"smoke_teacher@test.local","password":"SmokeTest123!"}')

http_code=$(echo "$result" | tail -1)
body=$(echo "$result" | head -n -1)

echo "HTTP Code: $http_code"
echo "Response: $body"

if [[ "$http_code" == "200" ]]; then
    echo "SUCCESS: JWT obtained"
else
    echo "FAILED: Check credentials"
fi
