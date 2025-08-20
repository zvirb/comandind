#!/usr/bin/env python3
"""
Simple SSL Configuration Validator for AI Workflow Engine WebUI

This script validates that the SSL certificate fixes are properly implemented
without requiring additional dependencies like Playwright.

Usage:
    python scripts/validate_ssl_fix.py
"""

import os
import sys
import json
import requests
from pathlib import Path
from urllib3.exceptions import InsecureRequestWarning

# Disable SSL warnings for testing
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

def check_file_exists(file_path, description):
    """Check if a file exists and is readable"""
    path = Path(file_path)
    if path.exists() and path.is_file():
        print(f"✅ {description}: {file_path}")
        return True
    else:
        print(f"❌ {description}: {file_path} (NOT FOUND)")
        return False

def check_vite_config():
    """Check if Vite configuration has HTTPS enabled"""
    print("\n🔍 Checking Vite HTTPS Configuration...")
    
    vite_config_path = "/home/marku/ai_workflow_engine/app/webui/vite.config.js"
    
    if not os.path.exists(vite_config_path):
        print(f"❌ Vite config not found: {vite_config_path}")
        return False
    
    with open(vite_config_path, 'r') as f:
        content = f.read()
    
    # Check for HTTPS configuration
    checks = [
        ("HTTPS enabled", "config.server.https" in content),
        ("Certificate path detection", "certPaths" in content),
        ("SSL error handling", "SSL] Error setting up HTTPS" in content),
        ("Fallback mechanism", "certificatesFound" in content),
        ("Development comment", "Enable HTTPS for development" in content)
    ]
    
    all_passed = True
    for check_name, check_result in checks:
        if check_result:
            print(f"✅ {check_name}")
        else:
            print(f"❌ {check_name}")
            all_passed = False
    
    return all_passed

def check_serviceworker_config():
    """Check if ServiceWorker registration has SSL handling"""
    print("\n🔍 Checking ServiceWorker SSL Handling...")
    
    app_html_path = "/home/marku/ai_workflow_engine/app/webui/src/app.html"
    
    if not os.path.exists(app_html_path):
        print(f"❌ app.html not found: {app_html_path}")
        return False
    
    with open(app_html_path, 'r') as f:
        content = f.read()
    
    # Check for SSL-aware ServiceWorker registration
    checks = [
        ("Secure context detection", "isSecureContext" in content),
        ("SSL error handling", "SSL certificate issue detected" in content),
        ("Graceful degradation", "enableGracefulDegradation" in content),
        ("SSL notifications", "showSSLErrorNotification" in content),
        ("Certificate error detection", "certificate" in content and "SSL" in content)
    ]
    
    all_passed = True
    for check_name, check_result in checks:
        if check_result:
            print(f"✅ {check_name}")
        else:
            print(f"❌ {check_name}")
            all_passed = False
    
    return all_passed

def check_error_boundary():
    """Check if error boundary has SSL awareness"""
    print("\n🔍 Checking Error Boundary SSL Awareness...")
    
    layout_path = "/home/marku/ai_workflow_engine/app/webui/src/routes/+layout.svelte"
    
    if not os.path.exists(layout_path):
        print(f"❌ Layout file not found: {layout_path}")
        return False
    
    with open(layout_path, 'r') as f:
        content = f.read()
    
    # Check for SSL-aware error handling
    checks = [
        ("SSL error detection", "isSSLError" in content),
        ("Certificate error handling", "certificate" in content.lower()),
        ("Enhanced error messages", "SSL Certificate Issue" in content),
        ("Error prevention", "event.preventDefault()" in content)
    ]
    
    all_passed = True
    for check_name, check_result in checks:
        if check_result:
            print(f"✅ {check_name}")
        else:
            print(f"❌ {check_name}")
            all_passed = False
    
    return all_passed

def check_ssl_certificates():
    """Check if SSL certificates are available"""
    print("\n🔍 Checking SSL Certificate Files...")
    
    cert_base_path = "/home/marku/ai_workflow_engine/certs/webui"
    
    certificates = [
        ("unified-cert.pem", "Main certificate file"),
        ("unified-key.pem", "Private key file"),
        ("server.crt", "Fallback certificate"),
        ("server.key", "Fallback private key"),
        ("rootCA.pem", "Certificate Authority")
    ]
    
    all_found = True
    for cert_file, description in certificates:
        cert_path = os.path.join(cert_base_path, cert_file)
        found = check_file_exists(cert_path, description)
        if not found:
            all_found = False
    
    return all_found

def test_https_connectivity():
    """Test HTTPS connectivity to the application"""
    print("\n🔍 Testing HTTPS Connectivity...")
    
    url = "https://localhost"
    
    try:
        # Test with certificate verification disabled (expected for self-signed)
        response = requests.get(url, verify=False, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ HTTPS connectivity successful (Status: {response.status_code})")
            
            # Check if it's the correct application
            if "AI Workflow Engine" in response.text:
                print("✅ Application loaded successfully")
                return True
            else:
                print("⚠️  Response received but may not be the correct application")
                return True
        else:
            print(f"❌ HTTPS request failed (Status: {response.status_code})")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection refused - application may not be running")
        print("   Run: docker compose -f docker-compose-mtls.yml up")
        return False
    except Exception as e:
        print(f"❌ HTTPS connectivity test failed: {e}")
        return False

def generate_summary(test_results):
    """Generate a summary of all test results"""
    print("\n" + "="*60)
    print("🎯 SSL CERTIFICATE CONFIGURATION FIX VALIDATION SUMMARY")
    print("="*60)
    
    total_tests = len(test_results)
    passed_tests = sum(test_results.values())
    
    print(f"\nTests Results: {passed_tests}/{total_tests} passed")
    print("-" * 40)
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    if passed_tests == total_tests:
        print("\n🎉 ALL TESTS PASSED!")
        print("SSL certificate configuration fix is properly implemented.")
        print("\nNext Steps:")
        print("1. Start the application: docker compose -f docker-compose-mtls.yml up")
        print("2. Access: https://localhost")
        print("3. Accept certificate warning to enable ServiceWorker")
        print("4. Verify ServiceWorker in DevTools > Application > Service Workers")
        return True
    else:
        print(f"\n⚠️  {total_tests - passed_tests} TESTS FAILED")
        print("Some issues were found with the SSL configuration.")
        print("\nRecommendations:")
        
        if not test_results["Vite HTTPS Configuration"]:
            print("- Review Vite config HTTPS settings")
        if not test_results["ServiceWorker SSL Handling"]:
            print("- Check ServiceWorker registration enhancements")
        if not test_results["Error Boundary SSL Awareness"]:
            print("- Verify error boundary SSL error handling")
        if not test_results["SSL Certificates Available"]:
            print("- Ensure SSL certificates are generated and accessible")
        if not test_results["HTTPS Connectivity"]:
            print("- Start Docker services or check network connectivity")
        
        return False

def main():
    """Run all validation tests"""
    print("🚀 Validating SSL Certificate Configuration Fix")
    print("="*60)
    
    # Run all tests
    test_results = {
        "Vite HTTPS Configuration": check_vite_config(),
        "ServiceWorker SSL Handling": check_serviceworker_config(),
        "Error Boundary SSL Awareness": check_error_boundary(),
        "SSL Certificates Available": check_ssl_certificates(),
        "HTTPS Connectivity": test_https_connectivity()
    }
    
    # Generate summary
    success = generate_summary(test_results)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()