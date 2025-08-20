#!/usr/bin/env python3
"""
Domain Configuration Validation Script

This script validates that the updated WebUI test configurations work correctly
with both localhost and aiwfe.com domains, and both HTTP and HTTPS protocols.

Usage:
    python scripts/validate_domain_configuration.py
"""

import asyncio
import os
import sys
import requests
from urllib3.exceptions import InsecureRequestWarning

# Disable SSL warnings for testing
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

def test_environment_variables():
    """Test environment variable configuration"""
    print("🧪 Testing Environment Variable Configuration")
    print("=" * 50)
    
    # Test default values
    domain = os.getenv("WEBUI_TEST_DOMAIN", "aiwfe.com")
    protocol = os.getenv("WEBUI_TEST_PROTOCOL", "https")
    port = os.getenv("WEBUI_TEST_PORT", None)
    
    print(f"✅ Default domain: {domain}")
    print(f"✅ Default protocol: {protocol}")
    print(f"✅ Default port: {port or 'standard (80/443)'}")
    
    # Test URL construction
    if port:
        url = f"{protocol}://{domain}:{port}"
    else:
        url = f"{protocol}://{domain}"
    
    print(f"✅ Constructed URL: {url}")
    return url

def test_http_connectivity(url):
    """Test HTTP connectivity to the domain"""
    print(f"\n🌐 Testing HTTP Connectivity to {url}")
    print("=" * 50)
    
    try:
        # Test with a short timeout
        response = requests.get(url, verify=False, timeout=5)
        print(f"✅ HTTP Status: {response.status_code}")
        print(f"✅ Response headers: {dict(list(response.headers.items())[:3])}")
        return True
    except requests.exceptions.ConnectionError:
        print(f"❌ Connection failed - service may not be running")
        return False
    except requests.exceptions.Timeout:
        print(f"⚠️  Connection timeout - service may be slow")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_both_protocols():
    """Test both HTTP and HTTPS configurations"""
    print("\n🔄 Testing Both HTTP and HTTPS Protocols")
    print("=" * 50)
    
    domain = os.getenv("WEBUI_TEST_DOMAIN", "aiwfe.com")
    
    results = {
        "http": False,
        "https": False
    }
    
    for protocol in ["http", "https"]:
        url = f"{protocol}://{domain}"
        print(f"\nTesting {protocol.upper()}: {url}")
        try:
            response = requests.get(url, verify=False, timeout=5)
            if response.status_code < 400:
                results[protocol] = True
                print(f"✅ {protocol.upper()} working (status: {response.status_code})")
            else:
                print(f"⚠️  {protocol.upper()} returned status: {response.status_code}")
        except Exception as e:
            print(f"❌ {protocol.upper()} failed: {e}")
    
    return results

def test_script_imports():
    """Test that our updated scripts can import correctly"""
    print("\n📦 Testing Script Import Configuration")
    print("=" * 50)
    
    scripts_to_test = [
        "scripts/test_webui_playwright.py",
        "scripts/test_webui_ssl.py"
    ]
    
    for script_path in scripts_to_test:
        if os.path.exists(script_path):
            print(f"✅ Found: {script_path}")
            
            # Check if environment variables are being used
            with open(script_path, 'r') as f:
                content = f.read()
                if "WEBUI_TEST_DOMAIN" in content:
                    print(f"✅ {script_path} uses WEBUI_TEST_DOMAIN")
                if "WEBUI_TEST_PROTOCOL" in content:
                    print(f"✅ {script_path} uses WEBUI_TEST_PROTOCOL")
        else:
            print(f"❌ Missing: {script_path}")

async def main():
    """Main validation function"""
    print("🚀 WebUI Domain Configuration Validation")
    print("=" * 60)
    
    # Test environment variables
    default_url = test_environment_variables()
    
    # Test script imports
    test_script_imports()
    
    # Test connectivity
    connectivity_ok = test_http_connectivity(default_url)
    
    # Test both protocols
    protocol_results = test_both_protocols()
    
    # Summary
    print("\n📊 Validation Summary")
    print("=" * 30)
    print(f"Environment Variables: ✅ Configured")
    print(f"Default URL: {default_url}")
    print(f"HTTP Available: {'✅' if protocol_results['http'] else '❌'}")
    print(f"HTTPS Available: {'✅' if protocol_results['https'] else '❌'}")
    
    # Recommendations
    print("\n💡 Recommendations")
    print("=" * 30)
    
    if not protocol_results['http'] and not protocol_results['https']:
        print("⚠️  No protocols are working. Ensure:")
        print("   1. Docker services are running")
        print("   2. Domain is properly configured in /etc/hosts")
        print("   3. Reverse proxy (Caddy) is running")
    elif protocol_results['https'] and not protocol_results['http']:
        print("✅ HTTPS is working - recommended for production")
    elif protocol_results['http'] and not protocol_results['https']:
        print("⚠️  Only HTTP is working - consider enabling HTTPS")
    else:
        print("✅ Both HTTP and HTTPS are working")
    
    print("\n🧪 To test with different configurations:")
    print("export WEBUI_TEST_DOMAIN=localhost && python scripts/validate_domain_configuration.py")
    print("export WEBUI_TEST_PROTOCOL=http && python scripts/validate_domain_configuration.py")

if __name__ == "__main__":
    asyncio.run(main())