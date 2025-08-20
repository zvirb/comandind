#!/usr/bin/env python3
"""
Debug the exact URL conversion issue causing sslmode parameter problems
"""
from app.shared.utils.config import get_settings
from app.shared.utils.database_setup import fix_async_database_url
from urllib.parse import urlparse, parse_qs

def debug_url_conversion():
    settings = get_settings()
    original_url = settings.database_url
    
    print(f"=== URL CONVERSION DEBUG ===")
    print(f"Original URL: {original_url}")
    print()
    
    # Parse original URL
    parsed_original = urlparse(original_url)
    print(f"Original parsed:")
    print(f"  Scheme: {parsed_original.scheme}")
    print(f"  Netloc: {parsed_original.netloc}")
    print(f"  Path: {parsed_original.path}")
    print(f"  Query: {parsed_original.query}")
    
    if parsed_original.query:
        original_params = parse_qs(parsed_original.query)
        print(f"  Query params: {original_params}")
    print()
    
    # Convert to async
    try:
        async_url = fix_async_database_url(original_url)
        print(f"Converted async URL: {async_url}")
        print()
        
        # Parse converted URL
        parsed_async = urlparse(async_url)
        print(f"Converted parsed:")
        print(f"  Scheme: {parsed_async.scheme}")
        print(f"  Netloc: {parsed_async.netloc}")  
        print(f"  Path: {parsed_async.path}")
        print(f"  Query: {parsed_async.query}")
        
        if parsed_async.query:
            async_params = parse_qs(parsed_async.query)
            print(f"  Query params: {async_params}")
            
            # Check for problematic parameters
            if 'sslmode' in async_params:
                print(f"  ❌ ERROR: sslmode parameter still present: {async_params['sslmode']}")
            else:
                print(f"  ✅ sslmode parameter successfully removed")
                
            if 'ssl' in async_params:
                print(f"  ✅ ssl parameter present: {async_params['ssl']}")
            else:
                print(f"  ❌ WARNING: ssl parameter missing")
                
        print()
        
        # Test the URL with asyncpg directly
        print("Testing asyncpg URL parsing...")
        import asyncpg.connect_utils
        
        try:
            # This should reveal the exact parameter causing issues
            addrs, params, config = asyncpg.connect_utils._parse_connect_arguments(dsn=async_url)
            print("✅ AsyncPG URL parsing successful")
            print(f"  Config: {dict(config)}")
        except Exception as e:
            print(f"❌ AsyncPG URL parsing failed: {e}")
            print("This is the exact error preventing async connections")
    
    except Exception as e:
        print(f"URL conversion failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_url_conversion()