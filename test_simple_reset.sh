#!/bin/bash
# Test simple reset API
cd /var/www/teaching_panel

echo "=== Testing simple-reset endpoint ==="

# Test different paths
echo "Test 1: /accounts/api/simple-reset/"
curl -s -w "\nHTTP Status: %{http_code}\n" -X POST http://127.0.0.1:8000/accounts/api/simple-reset/ \
  -H "Content-Type: application/json" \
  -d '{"email":"nonexistent@test.com","new_password":"Test1234"}'
echo ""

echo "Test 2: /api/simple-reset/"
curl -s -w "\nHTTP Status: %{http_code}\n" -X POST http://127.0.0.1:8000/api/simple-reset/ \
  -H "Content-Type: application/json" \
  -d '{"email":"nonexistent@test.com","new_password":"Test1234"}'
echo ""

echo "=== Tests complete ==="
