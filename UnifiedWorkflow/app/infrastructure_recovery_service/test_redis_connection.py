#!/usr/bin/env python3
"""Test Redis connection with environment variables"""
import os
import redis.asyncio as redis
import asyncio

async def test_redis_connections():
    """Test Redis connection with different URL formats"""
    
    # Get environment variables
    redis_host = os.environ.get('REDIS_HOST', 'localhost')
    redis_port = int(os.environ.get('REDIS_PORT', '6379'))
    redis_db = int(os.environ.get('REDIS_DB', '4'))
    redis_user = os.environ.get('REDIS_USER', 'default')
    redis_password = os.environ.get('REDIS_PASSWORD', '')
    
    print(f"Environment variables:")
    print(f"  REDIS_HOST: {redis_host}")
    print(f"  REDIS_PORT: {redis_port}")
    print(f"  REDIS_DB: {redis_db}")
    print(f"  REDIS_USER: {redis_user}")
    print(f"  REDIS_PASSWORD: {'*' * len(redis_password) if redis_password else 'NOT SET'}")
    
    # Test different Redis URL formats
    test_urls = [
        f"redis://{redis_host}:{redis_port}/{redis_db}",
        f"redis://{redis_user}:{redis_password}@{redis_host}:{redis_port}/{redis_db}",
        f"redis://localhost:6379/4",  # This is what was failing
    ]
    
    for i, url in enumerate(test_urls, 1):
        print(f"\nTest {i}: {url[:50]}{'...' if len(url) > 50 else ''}")
        try:
            client = redis.from_url(url, decode_responses=True)
            await client.ping()
            print(f"  ✓ SUCCESS: Connected and pinged")
            await client.close()
        except Exception as e:
            print(f"  ✗ FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(test_redis_connections())