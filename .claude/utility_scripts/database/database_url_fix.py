#!/usr/bin/env python3
"""
Database URL Fix for Special Character Password Issue

Fixes the Invalid IPv6 URL error caused by special characters in database passwords
that are being misinterpreted as IPv6 URL delimiters during async URL conversion.

This addresses the core authentication failure issue in Phase 3.
"""

import re
import logging
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse, quote

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_async_database_url_enhanced(database_url: str) -> str:
    """
    Enhanced database URL conversion with proper handling of special characters in passwords.
    Fixes the Invalid IPv6 URL error by properly encoding password components.
    """
    logger.debug(f"Converting database URL to async: {database_url[:50]}...")
    
    # First, handle special characters in the password component
    # Pattern to extract user:password from URL
    auth_pattern = r'postgresql(?:\+psycopg2)?://([^@]+)@'
    auth_match = re.search(auth_pattern, database_url)
    
    if auth_match:
        auth_part = auth_match.group(1)  # user:password
        if ':' in auth_part:
            username, password = auth_part.split(':', 1)
            
            # URL-encode the password to handle special characters
            encoded_password = quote(password, safe='')
            encoded_auth = f"{username}:{encoded_password}"
            
            # Replace the auth part in the original URL
            safe_database_url = database_url.replace(auth_part, encoded_auth)
            logger.info(f"Encoded special characters in password for URL parsing")
        else:
            safe_database_url = database_url
    else:
        safe_database_url = database_url
    
    # Convert driver
    if 'postgresql+psycopg2://' in safe_database_url:
        async_url = safe_database_url.replace('postgresql+psycopg2://', 'postgresql+asyncpg://')
    elif 'postgresql://' in safe_database_url:
        async_url = safe_database_url.replace('postgresql://', 'postgresql+asyncpg://')
    else:
        async_url = safe_database_url
    
    # Parse URL to handle SSL parameters properly
    try:
        parsed = urlparse(async_url)
        if parsed.query:
            # Parse query parameters
            query_params = parse_qs(parsed.query, keep_blank_values=True)
            
            # Handle SSL parameters for AsyncPG compatibility
            ssl_mode = query_params.get('sslmode', [None])[0]
            
            if ssl_mode == 'disable':
                # For sslmode=disable, remove ALL SSL parameters for AsyncPG
                logger.info("Removing all SSL parameters for sslmode=disable with AsyncPG")
                ssl_params_to_remove = ['sslmode', 'sslcert', 'sslkey', 'sslrootcert', 'sslcrl', 'ssl']
                for param in ssl_params_to_remove:
                    if param in query_params:
                        logger.debug(f"Removing SSL parameter: {param}")
                        del query_params[param]
            
            elif ssl_mode in ['require', 'prefer', 'allow']:
                # Convert to AsyncPG ssl=true format
                logger.info(f"Converting sslmode='{ssl_mode}' to ssl=true for AsyncPG")
                query_params['ssl'] = ['true']
                del query_params['sslmode']
                
                # Remove certificate parameters that AsyncPG doesn't support in URL
                cert_params = ['sslcert', 'sslkey', 'sslrootcert', 'sslcrl']
                for param in cert_params:
                    if param in query_params:
                        logger.debug(f"Removing cert parameter: {param}")
                        del query_params[param]
            
            elif ssl_mode in ['verify-ca', 'verify-full']:
                # Convert to AsyncPG ssl=true with server hostname verification
                logger.info(f"Converting sslmode='{ssl_mode}' to ssl=true with verification for AsyncPG")
                query_params['ssl'] = ['true']
                if ssl_mode == 'verify-full' and parsed.hostname:
                    query_params['server_hostname'] = [parsed.hostname]
                del query_params['sslmode']
                
                # Remove certificate parameters
                cert_params = ['sslcert', 'sslkey', 'sslrootcert', 'sslcrl']
                for param in cert_params:
                    if param in query_params:
                        logger.debug(f"Removing cert parameter: {param}")
                        del query_params[param]
            
            # Rebuild query string
            if query_params:
                # Flatten single-item lists for cleaner URLs
                flattened_params = {}
                for key, values in query_params.items():
                    if len(values) == 1:
                        flattened_params[key] = values[0]
                    else:
                        flattened_params[key] = values
                
                new_query = urlencode(flattened_params, doseq=True)
                async_url = urlunparse((
                    parsed.scheme, parsed.netloc, parsed.path,
                    parsed.params, new_query, parsed.fragment
                ))
            else:
                # No query parameters left
                async_url = urlunparse((
                    parsed.scheme, parsed.netloc, parsed.path,
                    parsed.params, '', parsed.fragment
                ))
        
        # Validate the final URL by parsing it
        test_parsed = urlparse(async_url)
        if not all([test_parsed.scheme, test_parsed.netloc]):
            raise ValueError(f"URL conversion produced invalid result: {async_url}")
    
    except ValueError as ve:
        if "Invalid IPv6 URL" in str(ve):
            logger.error(f"IPv6 URL parsing error - likely special characters in password: {ve}")
            # Enhanced fallback for IPv6 parsing issues
            logger.info("Applying enhanced fallback for special character handling")
            
            # Fallback: Simple removal of problematic SSL parameters without URL parsing
            ssl_params = ['sslmode', 'sslcert', 'sslkey', 'sslrootcert', 'sslcrl']
            for param in ssl_params:
                pattern = rf'[?&]{param}=[^&]*'
                async_url = re.sub(pattern, '', async_url)
            
            # Clean up URL formatting
            async_url = re.sub(r'[?&]+$', '', async_url)  # Remove trailing ? or &
            async_url = re.sub(r'\?&', '?', async_url)     # Fix ?& to ?
            async_url = re.sub(r'&{2,}', '&', async_url)   # Fix multiple &
            
            logger.info("Enhanced fallback SSL parameter removal completed")
        else:
            raise ve
    
    except Exception as e:
        logger.error(f"Failed to parse URL for SSL parameter conversion: {e}")
        # Fallback: Simple removal of problematic SSL parameters
        ssl_params = ['sslmode', 'sslcert', 'sslkey', 'sslrootcert', 'sslcrl']
        for param in ssl_params:
            pattern = rf'[?&]{param}=[^&]*'
            async_url = re.sub(pattern, '', async_url)
        
        # Clean up URL formatting
        async_url = re.sub(r'[?&]+$', '', async_url)  # Remove trailing ? or &
        async_url = re.sub(r'\?&', '?', async_url)     # Fix ?& to ?
        async_url = re.sub(r'&{2,}', '&', async_url)   # Fix multiple &
        
        logger.warning(f"Used fallback SSL parameter removal")
    
    # Validate final result doesn't raise IPv6 error
    try:
        final_test = urlparse(async_url)
        logger.info(f"Successfully converted database URL for AsyncPG compatibility")
        logger.debug(f"Original: {database_url}")
        logger.debug(f"Converted: {async_url}")
        return async_url
    except ValueError as e:
        if "Invalid IPv6 URL" in str(e):
            # This should not happen with proper encoding, but as final safety
            logger.error(f"Final validation failed with IPv6 error: {e}")
            raise ValueError(f"Database URL conversion failed: special characters in password need proper encoding")
        else:
            raise e

def test_url_conversion():
    """Test the enhanced URL conversion with problematic password."""
    # Test URL with special characters that cause IPv6 parsing issues
    test_url = "postgresql+psycopg2://lwe-admin:y5268[695t-13htgq244t5thj[8q9grq@postgres:5432/ai_workflow_engine?sslmode=require"
    
    print("Testing URL conversion with special characters in password:")
    print(f"Original URL: {test_url}")
    
    try:
        converted_url = fix_async_database_url_enhanced(test_url)
        print(f"Converted URL: {converted_url}")
        
        # Test that the converted URL can be parsed
        parsed = urlparse(converted_url)
        print(f"✅ URL parsing successful: {parsed.scheme}://{parsed.username}:****@{parsed.hostname}:{parsed.port}{parsed.path}")
        
        return True
    except Exception as e:
        print(f"❌ URL conversion failed: {e}")
        return False

def apply_fix_to_database_setup():
    """Apply the fix to the actual database_setup.py file."""
    import sys
    sys.path.insert(0, '/home/marku/ai_workflow_engine/app')
    
    try:
        # Read the current database_setup.py file
        with open('/home/marku/ai_workflow_engine/app/shared/utils/database_setup.py', 'r') as f:
            content = f.read()
        
        # Replace the fix_async_database_url function
        function_start = content.find('def fix_async_database_url(database_url: str) -> str:')
        if function_start == -1:
            print("❌ Could not find fix_async_database_url function")
            return False
        
        # Find the end of the function
        function_end = content.find('\ndef ', function_start + 1)
        if function_end == -1:
            # Function is at the end of the file
            function_end = len(content)
        
        # Create the new function content
        new_function = '''def fix_async_database_url(database_url: str) -> str:
    """
    Enhanced database URL conversion with proper handling of special characters in passwords.
    Fixes the Invalid IPv6 URL error by properly encoding password components.
    """
    logger.debug(f"Converting database URL to async: {database_url[:50]}...")
    
    # First, handle special characters in the password component
    # Pattern to extract user:password from URL
    import re
    from urllib.parse import quote
    
    auth_pattern = r'postgresql(?:\\+psycopg2)?://([^@]+)@'
    auth_match = re.search(auth_pattern, database_url)
    
    if auth_match:
        auth_part = auth_match.group(1)  # user:password
        if ':' in auth_part:
            username, password = auth_part.split(':', 1)
            
            # URL-encode the password to handle special characters
            encoded_password = quote(password, safe='')
            encoded_auth = f"{username}:{encoded_password}"
            
            # Replace the auth part in the original URL
            safe_database_url = database_url.replace(auth_part, encoded_auth)
            logger.info(f"Encoded special characters in password for URL parsing")
        else:
            safe_database_url = database_url
    else:
        safe_database_url = database_url
    
    # Convert driver
    if 'postgresql+psycopg2://' in safe_database_url:
        async_url = safe_database_url.replace('postgresql+psycopg2://', 'postgresql+asyncpg://')
    elif 'postgresql://' in safe_database_url:
        async_url = safe_database_url.replace('postgresql://', 'postgresql+asyncpg://')
    else:
        async_url = safe_database_url
    
    # Parse URL to handle SSL parameters properly
    from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
    
    try:
        parsed = urlparse(async_url)
        if parsed.query:
            # Parse query parameters
            query_params = parse_qs(parsed.query, keep_blank_values=True)
            
            # Handle SSL parameters for AsyncPG compatibility
            ssl_mode = query_params.get('sslmode', [None])[0]
            
            if ssl_mode == 'disable':
                # For sslmode=disable, remove ALL SSL parameters for AsyncPG
                logger.info("Removing all SSL parameters for sslmode=disable with AsyncPG")
                ssl_params_to_remove = ['sslmode', 'sslcert', 'sslkey', 'sslrootcert', 'sslcrl', 'ssl']
                for param in ssl_params_to_remove:
                    if param in query_params:
                        logger.debug(f"Removing SSL parameter: {param}")
                        del query_params[param]
            
            elif ssl_mode in ['require', 'prefer', 'allow']:
                # Convert to AsyncPG ssl=true format
                logger.info(f"Converting sslmode='{ssl_mode}' to ssl=true for AsyncPG")
                query_params['ssl'] = ['true']
                del query_params['sslmode']
                
                # Remove certificate parameters that AsyncPG doesn't support in URL
                cert_params = ['sslcert', 'sslkey', 'sslrootcert', 'sslcrl']
                for param in cert_params:
                    if param in query_params:
                        logger.debug(f"Removing cert parameter: {param}")
                        del query_params[param]
            
            elif ssl_mode in ['verify-ca', 'verify-full']:
                # Convert to AsyncPG ssl=true with server hostname verification
                logger.info(f"Converting sslmode='{ssl_mode}' to ssl=true with verification for AsyncPG")
                query_params['ssl'] = ['true']
                if ssl_mode == 'verify-full' and parsed.hostname:
                    query_params['server_hostname'] = [parsed.hostname]
                del query_params['sslmode']
                
                # Remove certificate parameters
                cert_params = ['sslcert', 'sslkey', 'sslrootcert', 'sslcrl']
                for param in cert_params:
                    if param in query_params:
                        logger.debug(f"Removing cert parameter: {param}")
                        del query_params[param]
            
            # Rebuild query string
            if query_params:
                # Flatten single-item lists for cleaner URLs
                flattened_params = {}
                for key, values in query_params.items():
                    if len(values) == 1:
                        flattened_params[key] = values[0]
                    else:
                        flattened_params[key] = values
                
                new_query = urlencode(flattened_params, doseq=True)
                async_url = urlunparse((
                    parsed.scheme, parsed.netloc, parsed.path,
                    parsed.params, new_query, parsed.fragment
                ))
            else:
                # No query parameters left
                async_url = urlunparse((
                    parsed.scheme, parsed.netloc, parsed.path,
                    parsed.params, '', parsed.fragment
                ))
        
        # Validate the final URL by parsing it
        test_parsed = urlparse(async_url)
        if not all([test_parsed.scheme, test_parsed.netloc]):
            raise ValueError(f"URL conversion produced invalid result: {async_url}")
    
    except ValueError as ve:
        if "Invalid IPv6 URL" in str(ve):
            logger.error(f"IPv6 URL parsing error - likely special characters in password: {ve}")
            # Enhanced fallback for IPv6 parsing issues
            logger.info("Applying enhanced fallback for special character handling")
            
            # Fallback: Simple removal of problematic SSL parameters without URL parsing
            ssl_params = ['sslmode', 'sslcert', 'sslkey', 'sslrootcert', 'sslcrl']
            for param in ssl_params:
                pattern = rf'[?&]{param}=[^&]*'
                async_url = re.sub(pattern, '', async_url)
            
            # Clean up URL formatting
            async_url = re.sub(r'[?&]+$', '', async_url)  # Remove trailing ? or &
            async_url = re.sub(r'\\?&', '?', async_url)     # Fix ?& to ?
            async_url = re.sub(r'&{2,}', '&', async_url)   # Fix multiple &
            
            logger.info("Enhanced fallback SSL parameter removal completed")
        else:
            raise ve
    
    except Exception as e:
        logger.error(f"Failed to parse URL for SSL parameter conversion: {e}")
        # Fallback: Simple removal of problematic SSL parameters
        import re
        
        ssl_params = ['sslmode', 'sslcert', 'sslkey', 'sslrootcert', 'sslcrl']
        for param in ssl_params:
            pattern = rf'[?&]{param}=[^&]*'
            async_url = re.sub(pattern, '', async_url)
        
        # Clean up URL formatting
        async_url = re.sub(r'[?&]+$', '', async_url)  # Remove trailing ? or &
        async_url = re.sub(r'\\?&', '?', async_url)     # Fix ?& to ?
        async_url = re.sub(r'&{2,}', '&', async_url)   # Fix multiple &
        
        logger.warning(f"Used fallback SSL parameter removal")
    
    # Validate final result doesn't raise IPv6 error
    try:
        final_test = urlparse(async_url)
        logger.info(f"Successfully converted database URL for AsyncPG compatibility")
        logger.debug(f"Original: {database_url}")
        logger.debug(f"Converted: {async_url}")
        return async_url
    except ValueError as e:
        if "Invalid IPv6 URL" in str(e):
            # This should not happen with proper encoding, but as final safety
            logger.error(f"Final validation failed with IPv6 error: {e}")
            raise ValueError(f"Database URL conversion failed: special characters in password need proper encoding")
        else:
            raise e'''
        
        # Replace the function in the content
        new_content = content[:function_start] + new_function + content[function_end:]
        
        # Write the updated content back to the file
        with open('/home/marku/ai_workflow_engine/app/shared/utils/database_setup.py', 'w') as f:
            f.write(new_content)
        
        print("✅ Successfully applied fix to database_setup.py")
        return True
        
    except Exception as e:
        print(f"❌ Failed to apply fix: {e}")
        return False

if __name__ == "__main__":
    print("=" * 80)
    print("🔧 DATABASE URL FIX FOR SPECIAL CHARACTER PASSWORD ISSUE")
    print("=" * 80)
    
    # Test the conversion
    success = test_url_conversion()
    
    if success:
        print("\n🎯 Applying fix to database_setup.py...")
        apply_success = apply_fix_to_database_setup()
        
        if apply_success:
            print("\n✅ Fix applied successfully!")
            print("This should resolve the authentication failure issues in Phase 3.")
            print("\nNext steps:")
            print("1. Restart any running services")
            print("2. Re-run the database session validation")
            print("3. Test async authentication functionality")
        else:
            print("\n❌ Failed to apply fix automatically")
            print("Manual intervention required")
    else:
        print("\n❌ URL conversion test failed")
        print("Further investigation needed")
    
    print("=" * 80)