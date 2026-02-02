#!/bin/bash
# Test login timing
time curl -s -w "\nTotal time: %{time_total}s\n" \
  -X POST https://lectio.tw1.ru/api/jwt/token/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"Test1234"}'
