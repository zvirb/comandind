#!/usr/bin/env python3
"""
SSL Certificate Testing Script for AI Workflow Engine WebUI

This script tests the SSL certificate configuration and ServiceWorker registration
to ensure the WebUI has proper HTTPS setup for development and production.

Usage:
    python scripts/test_webui_ssl.py [--url https://aiwfe.com] [--domain aiwfe.com] [--protocol https] [--headless]
    
Environment Variables:
    WEBUI_TEST_DOMAIN: Domain to test (default: aiwfe.com)
    WEBUI_TEST_PROTOCOL: Protocol to use - http or https (default: https)
"""

import asyncio
import argparse
import sys
import json
import os
from pathlib import Path
from playwright.async_api import async_playwright
import ssl
import socket
import requests
from urllib3.exceptions import InsecureRequestWarning

# Disable SSL warnings for testing
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Default configuration
DEFAULT_DOMAIN = os.getenv("WEBUI_TEST_DOMAIN", "aiwfe.com")
DEFAULT_PROTOCOL = os.getenv("WEBUI_TEST_PROTOCOL", "https")

class SSLTester:
    def __init__(self, url=None, headless=True):
        if url is None:
            url = f"{DEFAULT_PROTOCOL}://{DEFAULT_DOMAIN}"
        self.url = url.rstrip('/')
        self.headless = headless
        self.results = {
            "ssl_transport": False,
            "certificate_valid": False,
            "service_worker_registration": False,
            "https_redirect": False,
            "console_errors": [],
            "recommendations": []
        }
    
    async def test_ssl_transport(self):
        """Test basic SSL transport layer connectivity"""
        print("🔍 Testing SSL transport layer...")
        
        try:
            # Test with requests (ignoring certificate validation)
            response = requests.get(self.url, verify=False, timeout=10)
            if response.status_code == 200:
                self.results["ssl_transport"] = True
                print("✅ SSL transport layer working")
            else:
                print(f"❌ SSL transport failed with status: {response.status_code}")
        except Exception as e:
            print(f"❌ SSL transport failed: {e}")
    
    def test_certificate_validity(self):
        """Test certificate validity using raw socket connection"""
        print("🔍 Testing certificate validity...")
        
        try:
            hostname = self.url.replace('https://', '').split(':')[0]
            port = 443 if ':' not in self.url.replace('https://', '') else int(self.url.split(':')[-1])
            
            context = ssl.create_default_context()
            with socket.create_connection((hostname, port), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    self.results["certificate_valid"] = True
                    print("✅ Certificate validation passed")
                    print(f"   Subject: {cert.get('subject', 'Unknown')}")
                    print(f"   Issuer: {cert.get('issuer', 'Unknown')}")
                    return cert
        except ssl.SSLError as e:
            print(f"❌ Certificate validation failed: {e}")
            self.results["recommendations"].append(
                "Certificate is self-signed or not trusted. For development, this is expected."
            )
        except Exception as e:
            print(f"❌ Certificate test failed: {e}")
        
        return None
    
    async def test_browser_ssl_handling(self):
        """Test SSL handling in browser context"""
        print("🔍 Testing browser SSL handling...")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=self.headless,
                args=[
                    '--ignore-certificate-errors',
                    '--ignore-ssl-errors',
                    '--ignore-certificate-errors-spki-list',
                    '--disable-web-security',
                    '--allow-running-insecure-content'
                ]
            )
            
            try:
                context = await browser.new_context(
                    ignore_https_errors=True
                )
                page = await context.new_page()
                
                # Collect console messages
                console_messages = []
                page.on("console", lambda msg: console_messages.append({
                    "type": msg.type,
                    "text": msg.text,
                    "location": msg.location
                }))
                
                # Navigate to the application
                print(f"   Navigating to {self.url}...")
                try:
                    await page.goto(self.url, timeout=15000)
                    print("✅ Page loaded successfully")
                    
                    # Wait for JavaScript to initialize
                    await page.wait_for_timeout(3000)
                    
                    # Check for ServiceWorker registration
                    sw_registration = await page.evaluate("""
                        () => {
                            return new Promise((resolve) => {
                                if ('serviceWorker' in navigator) {
                                    navigator.serviceWorker.getRegistrations().then(registrations => {
                                        resolve({
                                            supported: true,
                                            registered: registrations.length > 0,
                                            count: registrations.length
                                        });
                                    });
                                } else {
                                    resolve({
                                        supported: false,
                                        registered: false,
                                        count: 0
                                    });
                                }
                            });
                        }
                    """)
                    
                    if sw_registration["registered"]:
                        self.results["service_worker_registration"] = True
                        print("✅ ServiceWorker registered successfully")
                    else:
                        print("❌ ServiceWorker not registered")
                        if sw_registration["supported"]:
                            self.results["recommendations"].append(
                                "ServiceWorker is supported but not registered. Check console for SSL certificate errors."
                            )
                    
                    # Collect console errors
                    ssl_errors = [msg for msg in console_messages if 
                                 "ssl" in msg["text"].lower() or 
                                 "certificate" in msg["text"].lower() or
                                 "serviceworker" in msg["text"].lower()]
                    
                    self.results["console_errors"] = ssl_errors
                    
                    if ssl_errors:
                        print("⚠️  SSL-related console errors found:")
                        for error in ssl_errors:
                            print(f"   [{error['type'].upper()}] {error['text']}")
                    
                except Exception as e:
                    print(f"❌ Browser navigation failed: {e}")
                
            finally:
                await browser.close()
    
    def test_https_redirect(self):
        """Test if HTTP redirects to HTTPS"""
        print("🔍 Testing HTTP to HTTPS redirect...")
        
        http_url = self.url.replace('https://', 'http://')
        try:
            response = requests.get(http_url, allow_redirects=False, verify=False, timeout=10)
            if response.status_code in [301, 302, 307, 308]:
                location = response.headers.get('location', '')
                if location.startswith('https://'):
                    self.results["https_redirect"] = True
                    print("✅ HTTP to HTTPS redirect working")
                else:
                    print(f"❌ Redirect location is not HTTPS: {location}")
            else:
                print(f"❌ No redirect found (status: {response.status_code})")
        except Exception as e:
            print(f"⚠️  HTTP redirect test failed: {e}")
    
    def generate_recommendations(self):
        """Generate recommendations based on test results"""
        print("\n📋 SSL Configuration Analysis:")
        print("=" * 50)
        
        if not self.results["ssl_transport"]:
            self.results["recommendations"].append(
                "SSL transport layer is not working. Check if HTTPS is enabled in Vite config."
            )
        
        if not self.results["certificate_valid"]:
            self.results["recommendations"].append(
                "Certificate validation failed. For development, this is normal with self-signed certificates."
            )
        
        if not self.results["service_worker_registration"]:
            self.results["recommendations"].append(
                "ServiceWorker registration failed. This is likely due to SSL certificate trust issues."
            )
            self.results["recommendations"].append(
                f"To fix ServiceWorker registration: Click 'Advanced' -> 'Proceed to {self.url.split('://')[1]} (unsafe)' in browser SSL warning."
            )
        
        if self.results["console_errors"]:
            self.results["recommendations"].append(
                "SSL-related console errors detected. Check browser console for detailed error messages."
            )
        
        # Print summary
        total_tests = 4
        passed_tests = sum([
            self.results["ssl_transport"],
            self.results["certificate_valid"], 
            self.results["service_worker_registration"],
            self.results["https_redirect"]
        ])
        
        print(f"Tests Passed: {passed_tests}/{total_tests}")
        print(f"SSL Transport: {'✅' if self.results['ssl_transport'] else '❌'}")
        print(f"Certificate Valid: {'✅' if self.results['certificate_valid'] else '❌'}")
        print(f"ServiceWorker: {'✅' if self.results['service_worker_registration'] else '❌'}")
        print(f"HTTPS Redirect: {'✅' if self.results['https_redirect'] else '❌'}")
        
        if self.results["recommendations"]:
            print("\n💡 Recommendations:")
            for i, rec in enumerate(self.results["recommendations"], 1):
                print(f"{i}. {rec}")
        
        # Specific guidance for development
        print("\n🛠️  Development Setup Guide:")
        print("=" * 50)
        print("1. Ensure Docker services are running:")
        print("   docker compose -f docker-compose-mtls.yml up")
        print("")
        print("2. For Vite development server with HTTPS:")
        print("   cd app/webui")
        print("   npm run dev")
        print("")
        domain = self.url.split('://')[1]
        print(f"3. Access application at: {self.url}")
        print("   - Click 'Advanced' if you see SSL warning")
        print(f"   - Click 'Proceed to {domain} (unsafe)'")
        print("   - This enables ServiceWorker registration")
        print("")
        print("4. Verify ServiceWorker in DevTools:")
        print("   - Open DevTools (F12)")
        print("   - Go to Application tab")
        print("   - Check Service Workers section")
    
    async def run_all_tests(self):
        """Run all SSL tests"""
        print("🚀 Starting SSL Certificate Configuration Tests")
        print("=" * 50)
        
        await self.test_ssl_transport()
        self.test_certificate_validity()
        await self.test_browser_ssl_handling()
        self.test_https_redirect()
        
        self.generate_recommendations()
        
        return self.results

async def main():
    parser = argparse.ArgumentParser(description='Test SSL certificate configuration for WebUI')
    parser.add_argument('--url', default=None, help=f'URL to test (default: {DEFAULT_PROTOCOL}://{DEFAULT_DOMAIN})')
    parser.add_argument('--domain', default=None, help=f'Domain to test (default: {DEFAULT_DOMAIN})')
    parser.add_argument('--protocol', choices=['http', 'https'], default=None, help=f'Protocol to use (default: {DEFAULT_PROTOCOL})')
    parser.add_argument('--headless', action='store_true', help='Run browser tests in headless mode')
    parser.add_argument('--json', action='store_true', help='Output results in JSON format')
    
    args = parser.parse_args()
    
    # Determine URL from arguments
    if args.url:
        test_url = args.url
    elif args.domain or args.protocol:
        domain = args.domain or DEFAULT_DOMAIN
        protocol = args.protocol or DEFAULT_PROTOCOL
        test_url = f"{protocol}://{domain}"
    else:
        test_url = None  # Will use default in SSLTester
    
    print(f"🚀 Testing SSL configuration at: {test_url or f'{DEFAULT_PROTOCOL}://{DEFAULT_DOMAIN}'}")
    
    tester = SSLTester(url=test_url, headless=args.headless)
    results = await tester.run_all_tests()
    
    if args.json:
        print("\n" + "=" * 50)
        print("JSON Results:")
        print(json.dumps(results, indent=2))
    
    # Exit with error code if critical tests failed
    if not results["ssl_transport"]:
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())