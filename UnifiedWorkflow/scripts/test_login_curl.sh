#!/bin/bash

# Test login with admin credentials
echo "Testing admin login..."

response=$(curl -X POST https://aiwfe.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "TestPassword123!"
  }' \
  -c cookies.txt \
  -w "\n{\"http_status\": %{http_code}}" \
  -s)

echo "$response" | head -n -1 | jq .
http_status=$(echo "$response" | tail -n 1 | jq -r .http_status)

if [ "$http_status" = "200" ]; then
    echo "✓ Login successful!"
    
    # Test authenticated endpoint
    echo -e "\nTesting authenticated endpoint..."
    curl -X GET https://aiwfe.com/api/auth/me \
      -b cookies.txt \
      -w "\nHTTP Status: %{http_code}\n" \
      -s | jq .
else
    echo "✗ Login failed (HTTP $http_status)"
fi