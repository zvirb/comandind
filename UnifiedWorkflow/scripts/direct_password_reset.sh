#!/bin/bash
# Direct password reset via database

set -e

echo "Resetting admin password to: SecureAdmin2025!"

# Hash the password using Python in Docker container
NEW_HASH=$(docker exec ai_workflow_engine-api-1 python -c "
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
print(pwd_context.hash('SecureAdmin2025!'))
")

# Update in database
docker exec ai_workflow_engine-postgres-1 psql -U app_user -d ai_workflow_db -c "
UPDATE users 
SET hashed_password = '$NEW_HASH'
WHERE email = 'admin@example.com';
"

# Update secrets file
echo "SecureAdmin2025!" > secrets/admin_password.txt

echo "✅ Password reset complete!"
echo "Email: admin@example.com"
echo "Password: SecureAdmin2025!"