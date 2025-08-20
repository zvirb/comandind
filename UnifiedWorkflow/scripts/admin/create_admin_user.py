#!/usr/bin/env python3
"""
Create admin user with Argon2 password hash
"""
import asyncio
import asyncpg
from pwdlib.hashers.argon2 import Argon2Hasher

async def create_admin_user():
    # Database connection
    conn = await asyncpg.connect(
        host='localhost',
        port=5432,
        user='postgres',
        password='test_password',
        database='ai_workflow_engine'
    )
    
    try:
        # Create users table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email VARCHAR UNIQUE NOT NULL,
                hashed_password VARCHAR NOT NULL,
                is_active BOOLEAN DEFAULT true,
                is_superuser BOOLEAN DEFAULT false,
                role VARCHAR DEFAULT 'user',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
            )
        ''')
        
        # Read admin credentials
        with open('/home/marku/ai_workflow_engine/secrets/admin_email.txt', 'r') as f:
            email = f.read().strip()
        with open('/home/marku/ai_workflow_engine/secrets/admin_password.txt', 'r') as f:
            password = f.read().strip()
        
        # Hash password with Argon2
        hasher = Argon2Hasher()
        hashed_password = hasher.hash(password)
        
        # Insert admin user
        await conn.execute('''
            INSERT INTO users (email, hashed_password, is_active, is_superuser, role) 
            VALUES ($1, $2, true, true, 'admin')
            ON CONFLICT (email) DO UPDATE SET 
                hashed_password = EXCLUDED.hashed_password
        ''', email, hashed_password)
        
        print(f"Admin user created: {email}")
        print(f"Hash starts with: {hashed_password[:20]}...")
        
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(create_admin_user())