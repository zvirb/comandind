#!/usr/bin/env python3
"""Fix Redis configuration in all cognitive services."""

import os
import re

def fix_redis_config(config_file):
    """Fix Redis configuration in a Python config file."""
    if not os.path.exists(config_file):
        print(f"File not found: {config_file}")
        return False
    
    with open(config_file, 'r') as f:
        content = f.read()
    
    # Check if already fixed
    if 'redis_host: str = os.getenv("REDIS_HOST"' in content:
        print(f"Already fixed: {config_file}")
        return False
    
    # Pattern to find redis_url configuration
    redis_url_pattern = r'(redis_url:?\s*[^=]*=\s*os\.getenv\([^)]+\))'
    redis_db_pattern = r'(redis_db:?\s*[^=]*=\s*[^)]+\))'
    
    # Check if file has redis configuration
    if not re.search(redis_url_pattern, content):
        print(f"No Redis config found: {config_file}")
        return False
    
    # Replace Redis URL with component-based configuration
    new_redis_config = '''    # Redis Configuration - Build URL from components
    redis_host: str = os.getenv("REDIS_HOST", "redis")
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
    redis_db: int = int(os.getenv("REDIS_DB", "0"))
    redis_user: str = os.getenv("REDIS_USER", "lwe-app")
    redis_password: str = os.getenv("REDIS_PASSWORD", "")
    
    @property
    def redis_url(self) -> str:
        """Build Redis URL from components."""
        if self.redis_password:
            from urllib.parse import quote_plus
            password = quote_plus(self.redis_password)
            return f"redis://{self.redis_user}:{password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"'''
    
    # Replace redis_url line with new config
    content = re.sub(
        r'    # Redis.*\n.*redis_url.*\n(.*redis_db.*\n)?',
        new_redis_config + '\n',
        content
    )
    
    with open(config_file, 'w') as f:
        f.write(content)
    
    print(f"Fixed: {config_file}")
    return True

# Fix all service config files
services = [
    'learning_service',
    'reasoning_service',
    'infrastructure_recovery_service'
]

for service in services:
    config_file = f'/home/marku/ai_workflow_engine/app/{service}/config.py'
    fix_redis_config(config_file)

print("Done!")