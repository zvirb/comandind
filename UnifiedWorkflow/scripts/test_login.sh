#!/bin/bash

# Test login with properly formatted JSON
curl -X POST 'https://aiwfe.com/api/v1/auth/login' \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@aiwfe.com","password":"Admin123!@#"}' \
  -c cookies.txt \
  -v