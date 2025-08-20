#!/usr/bin/env python3
"""
Production Google OAuth Validation

Tests the actual implemented Google OAuth endpoints at aiwfe.com to validate
that the redirect_uri_mismatch fixes are working correctly.
"""

import asyncio
import json
import argparse
import os
from datetime import datetime
from playwright.async_api import async_playwright

# Test configuration
TEST_DOMAIN = "aiwfe.com"
TEST_PROTOCOL = "https"
TEST_URL = f"{TEST_PROTOCOL}://{TEST_DOMAIN}"

# Test user credentials for real authentication
TEST_USER_EMAIL = "markuszvirbulis@gmail.com"
TEST_USER_PASSWORD = "your-actual-password"  # This would need to be the real password

async def validate_production_oauth():
    """
    Validate Google OAuth in production environment
    """
    test_results = {
        "test_timestamp": datetime.now().isoformat(),
        "test_url": TEST_URL,
        "validation_phases": {},
        "screenshots": [],
        "console_messages": [],
        "network_requests": [],
        "errors": [],
        "oauth_endpoints_tested": [],
        "final_status": "unknown"
    }
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--ignore-certificate-errors',
                '--ignore-ssl-errors',
                '--allow-running-insecure-content',
                '--disable-web-security'
            ]
        )
        
        context = await browser.new_context(ignore_https_errors=True)
        page = await context.new_page()
        
        # Set up event listeners
        page.on("console", lambda msg: test_results["console_messages"].append({
            "timestamp": datetime.now().isoformat(),
            "type": msg.type,
            "text": msg.text
        }))
        
        page.on("pageerror", lambda error: test_results["errors"].append({
            "timestamp": datetime.now().isoformat(),
            "type": "javascript_error",
            "message": str(error)
        }))
        
        def handle_response(response):
            if ("oauth" in response.url.lower() or 
                "google" in response.url.lower() or 
                "auth" in response.url.lower() or
                response.status >= 400 or
                "accounts.google.com" in response.url.lower()):
                test_results["network_requests"].append({
                    "timestamp": datetime.now().isoformat(),
                    "url": response.url,
                    "status": response.status,
                    "method": response.request.method,
                    "redirect_chain": [r.url for r in response.request.redirect_chain] if hasattr(response.request, 'redirect_chain') else []
                })
        
        page.on("response", handle_response)
        
        try:
            # PHASE 1: Test OAuth Configuration Endpoints (No Auth Required)
            print("🔍 PHASE 1: Testing OAuth Configuration Endpoints")
            
            config_endpoints = [
                "/api/v1/oauth/google/config/check"
            ]
            
            for endpoint in config_endpoints:
                full_url = f"{TEST_URL}{endpoint}"
                print(f"🌐 Testing configuration endpoint: {full_url}")
                
                try:
                    response = await page.goto(full_url, wait_until="domcontentloaded", timeout=10000)
                    status = response.status if response else "No response"
                    current_url = page.url
                    
                    print(f"📊 Status: {status}, URL: {current_url}")
                    
                    test_results["oauth_endpoints_tested"].append({
                        "endpoint": endpoint,
                        "status": status,
                        "url": current_url,
                        "phase": "configuration"
                    })
                    
                    # Take screenshot
                    screenshot_path = f"/tmp/oauth_config_endpoint_{endpoint.replace('/', '_')}_{datetime.now().strftime('%H%M%S')}.png"
                    await page.screenshot(path=screenshot_path, full_page=True)
                    test_results["screenshots"].append({
                        "phase": f"config_endpoint_{endpoint}",
                        "path": screenshot_path,
                        "description": f"Configuration endpoint: {endpoint}"
                    })
                    
                except Exception as e:
                    print(f"❌ Error testing config endpoint {endpoint}: {e}")
                    test_results["errors"].append({
                        "timestamp": datetime.now().isoformat(),
                        "type": "config_endpoint_error",
                        "endpoint": endpoint,
                        "message": str(e)
                    })
            
            test_results["validation_phases"]["configuration"] = "completed"
            
            # PHASE 2: Test Direct OAuth Connect Endpoints (Requires Auth)
            print("\n🔍 PHASE 2: Testing Direct OAuth Connect Endpoints")
            
            # Available Google services based on the enum
            google_services = ["calendar", "drive", "gmail"]
            
            for service in google_services:
                endpoint = f"/api/v1/oauth/google/connect/{service}"
                full_url = f"{TEST_URL}{endpoint}"
                print(f"🌐 Testing OAuth connect endpoint: {full_url}")
                
                try:
                    response = await page.goto(full_url, wait_until="domcontentloaded", timeout=15000)
                    status = response.status if response else "No response"
                    current_url = page.url
                    
                    print(f"📊 Status: {status}, URL: {current_url}")
                    print(f"📍 Final URL after navigation: {current_url}")
                    
                    # Check if we're redirected to Google OAuth
                    if "accounts.google.com" in current_url:
                        print(f"✅ SUCCESS: {service} OAuth redirects to Google!")
                        
                        # Take screenshot of Google OAuth consent screen
                        oauth_screenshot = f"/tmp/oauth_google_consent_{service}_{datetime.now().strftime('%H%M%S')}.png"
                        await page.screenshot(path=oauth_screenshot, full_page=True)
                        test_results["screenshots"].append({
                            "phase": f"google_oauth_{service}",
                            "path": oauth_screenshot,
                            "description": f"Google OAuth consent screen for {service}"
                        })
                        
                        # Validate Google OAuth page for errors
                        page_content = await page.content()
                        oauth_errors = []
                        
                        error_patterns = [
                            "redirect_uri_mismatch",
                            "access_blocked",
                            "invalid_request",
                            "invalid_client",
                            "unauthorized_client"
                        ]
                        
                        for pattern in error_patterns:
                            if pattern in page_content.lower():
                                oauth_errors.append(pattern)
                                print(f"❌ OAuth Error Detected: {pattern}")
                        
                        if not oauth_errors:
                            print(f"✅ {service} OAuth consent screen is clean - no errors detected")
                            test_results["final_status"] = "oauth_working"
                        else:
                            print(f"❌ {service} OAuth has errors: {oauth_errors}")
                            test_results["final_status"] = "oauth_errors_detected"
                            test_results["errors"].extend([{
                                "timestamp": datetime.now().isoformat(),
                                "type": "google_oauth_error",
                                "service": service,
                                "error_pattern": error
                            } for error in oauth_errors])
                        
                        test_results["oauth_endpoints_tested"].append({
                            "endpoint": endpoint,
                            "service": service,
                            "status": "redirected_to_google",
                            "final_url": current_url,
                            "oauth_errors": oauth_errors,
                            "phase": "oauth_redirect"
                        })
                        
                    elif current_url == f"{TEST_URL}/":
                        print(f"⚠️ {service} OAuth redirected to home page - likely requires authentication")
                        test_results["oauth_endpoints_tested"].append({
                            "endpoint": endpoint,
                            "service": service,
                            "status": "redirected_to_home",
                            "final_url": current_url,
                            "phase": "requires_auth"
                        })
                    elif status == 401:
                        print(f"🔐 {service} OAuth requires authentication (401)")
                        test_results["oauth_endpoints_tested"].append({
                            "endpoint": endpoint,
                            "service": service,
                            "status": "requires_authentication",
                            "final_url": current_url,
                            "phase": "auth_required"
                        })
                    else:
                        print(f"❓ {service} OAuth unexpected response: {status}")
                        test_results["oauth_endpoints_tested"].append({
                            "endpoint": endpoint,
                            "service": service,
                            "status": f"unexpected_{status}",
                            "final_url": current_url,
                            "phase": "unexpected"
                        })
                    
                    await page.wait_for_timeout(2000)  # Wait before next test
                    
                except Exception as e:
                    print(f"❌ Error testing OAuth endpoint {endpoint}: {e}")
                    test_results["errors"].append({
                        "timestamp": datetime.now().isoformat(),
                        "type": "oauth_endpoint_error",
                        "endpoint": endpoint,
                        "service": service,
                        "message": str(e)
                    })
            
            test_results["validation_phases"]["oauth_endpoints"] = "completed"
            
            # PHASE 3: Test OAuth Callback URL Format
            print("\n🔍 PHASE 3: Testing OAuth Callback URL Format")
            
            # Test the callback URL format that should be in Google OAuth configuration
            callback_endpoint = "/api/v1/oauth/google/callback"
            callback_url = f"{TEST_URL}{callback_endpoint}"
            
            print(f"🌐 Testing OAuth callback endpoint: {callback_url}")
            
            try:
                response = await page.goto(callback_url, wait_until="domcontentloaded", timeout=10000)
                status = response.status if response else "No response"
                current_url = page.url
                
                print(f"📊 Callback Status: {status}, URL: {current_url}")
                
                # Take screenshot
                callback_screenshot = f"/tmp/oauth_callback_endpoint_{datetime.now().strftime('%H%M%S')}.png"
                await page.screenshot(path=callback_screenshot, full_page=True)
                test_results["screenshots"].append({
                    "phase": "oauth_callback",
                    "path": callback_screenshot,
                    "description": "OAuth callback endpoint"
                })
                
                test_results["oauth_endpoints_tested"].append({
                    "endpoint": callback_endpoint,
                    "status": status,
                    "url": current_url,
                    "phase": "callback"
                })
                
            except Exception as e:
                print(f"❌ Error testing callback endpoint: {e}")
                test_results["errors"].append({
                    "timestamp": datetime.now().isoformat(),
                    "type": "callback_endpoint_error",
                    "message": str(e)
                })
            
            test_results["validation_phases"]["callback_endpoint"] = "completed"
            
            # Final Status Determination
            if test_results["final_status"] == "unknown":
                # Determine status based on results
                oauth_redirects = [endpoint for endpoint in test_results["oauth_endpoints_tested"] 
                                 if endpoint.get("status") == "redirected_to_google"]
                
                if oauth_redirects:
                    # Check if any had OAuth errors
                    has_oauth_errors = any(endpoint.get("oauth_errors") for endpoint in oauth_redirects)
                    if has_oauth_errors:
                        test_results["final_status"] = "oauth_errors_detected"
                    else:
                        test_results["final_status"] = "oauth_working"
                else:
                    test_results["final_status"] = "no_oauth_redirects"
            
        except Exception as e:
            print(f"❌ Critical error during validation: {e}")
            test_results["errors"].append({
                "timestamp": datetime.now().isoformat(),
                "type": "critical_test_error",
                "message": str(e)
            })
            test_results["final_status"] = "test_error"
        
        finally:
            await browser.close()
    
    return test_results

def print_production_oauth_report(results):
    """Print comprehensive production OAuth validation report"""
    print("\n" + "="*80)
    print("🔐 PRODUCTION GOOGLE OAUTH VALIDATION REPORT")
    print("="*80)
    print(f"🕐 Test Timestamp: {results['test_timestamp']}")
    print(f"🌐 Test URL: {results['test_url']}")
    print(f"📊 Final Status: {results['final_status'].upper()}")
    print()
    
    # Validation Phases Summary
    print("📋 VALIDATION PHASES:")
    for phase_name, phase_status in results["validation_phases"].items():
        status_emoji = "✅" if phase_status == "completed" else "❌"
        print(f"  {status_emoji} {phase_name.replace('_', ' ').title()}: {phase_status}")
    print()
    
    # OAuth Endpoints Results
    if results["oauth_endpoints_tested"]:
        print("🎯 OAUTH ENDPOINTS TESTED:")
        for endpoint in results["oauth_endpoints_tested"]:
            service = endpoint.get("service", "N/A")
            status = endpoint.get("status", "unknown")
            phase = endpoint.get("phase", "unknown")
            
            if status == "redirected_to_google":
                emoji = "✅"
                oauth_errors = endpoint.get("oauth_errors", [])
                error_text = f" (Errors: {', '.join(oauth_errors)})" if oauth_errors else " (Clean)"
            elif status in ["requires_authentication", "redirected_to_home"]:
                emoji = "🔐"
                error_text = " (Auth Required)"
            elif str(status).startswith("unexpected"):
                emoji = "❓"
                error_text = f" (Status: {status})"
            else:
                emoji = "❌"
                error_text = f" (Status: {status})"
            
            print(f"  {emoji} {endpoint['endpoint']}")
            print(f"     Service: {service}, Phase: {phase}{error_text}")
            if "final_url" in endpoint:
                print(f"     Final URL: {endpoint['final_url']}")
        print()
    
    # Final Assessment
    print("🏁 FINAL ASSESSMENT:")
    status = results["final_status"]
    if status == "oauth_working":
        print("  ✅ SUCCESS: Google OAuth is working correctly")
        print("  ✅ OAuth redirects to Google consent screen successfully")
        print("  ✅ No redirect_uri_mismatch or access_blocked errors detected")
        print("  🎯 RESULT: OAuth fixes are working in production")
    elif status == "oauth_errors_detected":
        print("  ❌ PARTIAL SUCCESS: OAuth redirects work but errors detected")
        print("  ⚠️ Some OAuth flows have issues that need attention")
        print("  🔧 ACTION REQUIRED: Review specific error patterns in results")
    elif status == "no_oauth_redirects":
        print("  ❌ FAILURE: No OAuth endpoints successfully redirect to Google")
        print("  🔧 ACTION REQUIRED: Verify OAuth implementation and configuration")
    elif status == "test_error":
        print("  ⚠️ ERROR: Test encountered critical errors")
        print("  🔧 ACTION REQUIRED: Review test errors and system connectivity")
    else:
        print(f"  ⚠️ UNKNOWN STATUS: {status}")
    print()
    
    # Screenshots Evidence
    print("📸 VISUAL EVIDENCE:")
    for screenshot in results["screenshots"]:
        print(f"  📷 {screenshot['phase']}: {screenshot['path']}")
        print(f"     {screenshot['description']}")
    print()
    
    # Error Summary
    if results["errors"]:
        print("❌ ERRORS DETECTED:")
        for error in results["errors"]:
            error_type = error.get('type', 'unknown')
            message = error.get('message', 'No message')
            print(f"  [{error['timestamp']}] {error_type}: {message}")
    else:
        print("✅ NO CRITICAL ERRORS DETECTED")
    print()
    
    print("="*80)

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Production Google OAuth Validation')
    parser.add_argument('--domain', default="aiwfe.com", help='Domain to test')
    parser.add_argument('--protocol', choices=['http', 'https'], default="https", help='Protocol to use')
    
    args = parser.parse_args()
    
    global TEST_DOMAIN, TEST_PROTOCOL, TEST_URL
    TEST_DOMAIN = args.domain
    TEST_PROTOCOL = args.protocol
    TEST_URL = f"{TEST_PROTOCOL}://{TEST_DOMAIN}"
    
    print(f"🚀 Starting Production Google OAuth Validation")
    print(f"🎯 Target URL: {TEST_URL}")
    print(f"🔍 Testing actual OAuth implementation endpoints...")
    print(f"🕐 Start Time: {datetime.now().isoformat()}")
    print()
    
    # Run production OAuth validation
    results = asyncio.run(validate_production_oauth())
    
    # Print comprehensive report
    print_production_oauth_report(results)
    
    # Save detailed results
    results_file = f"/tmp/production_oauth_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"💾 Detailed results saved to: {results_file}")
    
    return results

if __name__ == "__main__":
    main()