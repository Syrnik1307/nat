#!/bin/bash
# Test simple reset API
cd /var/www/teaching_panel

echo "=== Testing simple-reset endpoint ==="

# Test 1: nonexistent user (should return 404)
echo "Test 1: Nonexistent user"
curl -s -X POST http://127.0.0.1:8000/api/accounts/simple-reset/ \
  -H "Content-Type: application/json" \
  -d '{"email":"nonexistent@test.com","new_password":"Test1234"}'
echo ""

# Test 2: Missing email (should return 400)
echo "Test 2: Missing email"
curl -s -X POST http://127.0.0.1:8000/api/accounts/simple-reset/ \
  -H "Content-Type: application/json" \
  -d '{"new_password":"Test1234"}'
echo ""

# Test 3: Weak password (should return 400)
echo "Test 3: Weak password"
curl -s -X POST http://127.0.0.1:8000/api/accounts/simple-reset/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","new_password":"weak"}'
echo ""

echo "=== Tests complete ==="
