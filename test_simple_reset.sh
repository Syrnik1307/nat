#!/bin/bash
# Test simple reset API
cd /var/www/teaching_panel

echo "=== Testing simple-reset endpoint ==="

# Test with X-Forwarded-Proto header (simulating nginx proxy)
echo "Test 1: /accounts/api/simple-reset/ (via X-Forwarded-Proto)"
curl -s -w "\nHTTP Status: %{http_code}\n" -X POST http://127.0.0.1:8000/accounts/api/simple-reset/ \
  -H "Content-Type: application/json" \
  -H "X-Forwarded-Proto: https" \
  -d '{"email":"nonexistent@test.com","new_password":"Test1234"}'
echo ""

echo "Test 2: /accounts/api/simple-reset/ weak password"
curl -s -w "\nHTTP Status: %{http_code}\n" -X POST http://127.0.0.1:8000/accounts/api/simple-reset/ \
  -H "Content-Type: application/json" \
  -H "X-Forwarded-Proto: https" \
  -d '{"email":"test@test.com","new_password":"weak"}'
echo ""

echo "=== Tests complete ==="
