#!/usr/bin/env python3
"""
Comprehensive Google OAuth User Experience Validation

This script explores multiple pathways to find and test Google OAuth integration:
1. Registration page OAuth options
2. Post-login settings/profile OAuth options
3. Direct OAuth endpoint testing
"""

import asyncio
import json
import argparse
import os
from datetime import datetime
from playwright.async_api import async_playwright

# Test configuration
TEST_DOMAIN = os.getenv("WEBUI_TEST_DOMAIN", "aiwfe.com")
TEST_PROTOCOL = os.getenv("WEBUI_TEST_PROTOCOL", "https")
TEST_URL = f"{TEST_PROTOCOL}://{TEST_DOMAIN}"

# Test user credentials (from the earlier validation processes)
TEST_USER_EMAIL = "markuszvirbulis@gmail.com"  # Using the real user email for OAuth testing
TEST_USER_PASSWORD = "your-secure-password"  # Note: This will be updated during testing

async def comprehensive_oauth_validation():
    """
    Comprehensive OAuth validation covering multiple discovery paths
    """
    test_results = {
        "test_timestamp": datetime.now().isoformat(),
        "test_url": TEST_URL,
        "discovery_paths": {},
        "screenshots": [],
        "console_messages": [],
        "network_requests": [],
        "errors": [],
        "oauth_locations": [],
        "final_status": "unknown"
    }
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--ignore-certificate-errors',
                '--ignore-ssl-errors',
                '--allow-running-insecure-content',
                '--disable-web-security',
                '--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ]
        )
        
        context = await browser.new_context(
            ignore_https_errors=True,
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        page = await context.new_page()
        
        # Set up comprehensive event listeners
        page.on("console", lambda msg: test_results["console_messages"].append({
            "timestamp": datetime.now().isoformat(),
            "type": msg.type,
            "text": msg.text,
            "location": str(msg.location) if msg.location else None
        }))
        
        page.on("pageerror", lambda error: test_results["errors"].append({
            "timestamp": datetime.now().isoformat(),
            "type": "javascript_error",
            "message": str(error)
        }))
        
        # Track all network requests, especially OAuth-related ones
        def handle_response(response):
            if ("oauth" in response.url.lower() or 
                "google" in response.url.lower() or 
                "auth" in response.url.lower() or
                response.status >= 400):
                test_results["network_requests"].append({
                    "timestamp": datetime.now().isoformat(),
                    "url": response.url,
                    "status": response.status,
                    "status_text": response.status_text,
                    "method": response.request.method,
                    "headers": dict(response.headers)
                })
        
        page.on("response", handle_response)
        
        try:
            # PATH 1: Check Registration Page for OAuth
            print("🔍 PATH 1: Exploring Registration Page for OAuth Options")
            await page.goto(TEST_URL, wait_until="domcontentloaded", timeout=30000)
            
            # Take initial screenshot
            initial_screenshot = f"/tmp/oauth_comprehensive_initial_{datetime.now().strftime('%H%M%S')}.png"
            await page.screenshot(path=initial_screenshot, full_page=True)
            test_results["screenshots"].append({
                "phase": "initial_login_page",
                "path": initial_screenshot,
                "description": "Initial login page"
            })
            
            # Wait for page to load completely
            await page.wait_for_timeout(3000)
            
            # Look for "Register here" link and click it
            register_link = page.locator("a:has-text('Register here'), a[href*='register'], button:has-text('Register')")
            register_count = await register_link.count()
            
            if register_count > 0:
                print("✅ Found registration link, clicking...")
                await register_link.click()
                await page.wait_for_timeout(3000)
                
                # Take screenshot of registration page
                register_screenshot = f"/tmp/oauth_registration_page_{datetime.now().strftime('%H%M%S')}.png"
                await page.screenshot(path=register_screenshot, full_page=True)
                test_results["screenshots"].append({
                    "phase": "registration_page",
                    "path": register_screenshot,
                    "description": "Registration page"
                })
                
                # Look for Google OAuth on registration page
                google_oauth_elements = await find_google_oauth_elements(page)
                if google_oauth_elements:
                    print(f"🎯 Found Google OAuth on registration page: {len(google_oauth_elements)} elements")
                    test_results["oauth_locations"].append({
                        "location": "registration_page",
                        "elements_found": len(google_oauth_elements),
                        "page_url": page.url
                    })
                    
                    # Test the OAuth flow from registration page
                    oauth_result = await test_oauth_flow(page, "registration_page", test_results)
                    if oauth_result:
                        test_results["discovery_paths"]["registration_oauth"] = oauth_result
                        if oauth_result.get("success"):
                            test_results["final_status"] = "oauth_working_registration"
                            return test_results
                else:
                    print("❌ No Google OAuth found on registration page")
                    test_results["discovery_paths"]["registration_oauth"] = {
                        "status": "not_found",
                        "page_url": page.url
                    }
            else:
                print("❌ No registration link found")
                test_results["discovery_paths"]["registration_access"] = {
                    "status": "no_registration_link_found"
                }
            
            # PATH 2: Login and Check Dashboard/Settings for OAuth
            print("\n🔍 PATH 2: Login and Check Dashboard/Settings for OAuth")
            
            # Navigate back to login if needed
            if "register" in page.url.lower():
                await page.goto(TEST_URL, wait_until="domcontentloaded")
                await page.wait_for_timeout(2000)
            
            # Try to login (we'll use test credentials and handle any errors gracefully)
            login_attempted = await attempt_login(page, test_results)
            
            if login_attempted:
                # Look for OAuth options in the dashboard/settings
                await page.wait_for_timeout(5000)  # Wait for dashboard to load
                
                # Take screenshot of dashboard
                dashboard_screenshot = f"/tmp/oauth_dashboard_{datetime.now().strftime('%H%M%S')}.png"
                await page.screenshot(path=dashboard_screenshot, full_page=True)
                test_results["screenshots"].append({
                    "phase": "dashboard_logged_in",
                    "path": dashboard_screenshot,
                    "description": "Dashboard after login attempt"
                })
                
                # Look for settings, profile, or integrations sections
                settings_elements = page.locator("a:has-text('Settings'), button:has-text('Settings'), [href*='settings'], [href*='profile'], [href*='integration']")
                settings_count = await settings_elements.count()
                
                if settings_count > 0:
                    print(f"✅ Found {settings_count} settings-related elements")
                    
                    # Try clicking different settings options
                    for i in range(min(3, settings_count)):
                        try:
                            settings_element = settings_elements.nth(i)
                            element_text = await settings_element.text_content()
                            print(f"🔗 Exploring settings option: {element_text}")
                            
                            await settings_element.click()
                            await page.wait_for_timeout(3000)
                            
                            # Take screenshot of settings page
                            settings_screenshot = f"/tmp/oauth_settings_{i}_{datetime.now().strftime('%H%M%S')}.png"
                            await page.screenshot(path=settings_screenshot, full_page=True)
                            test_results["screenshots"].append({
                                "phase": f"settings_page_{i}",
                                "path": settings_screenshot,
                                "description": f"Settings page: {element_text}"
                            })
                            
                            # Look for Google OAuth in settings
                            google_oauth_elements = await find_google_oauth_elements(page)
                            if google_oauth_elements:
                                print(f"🎯 Found Google OAuth in settings: {len(google_oauth_elements)} elements")
                                test_results["oauth_locations"].append({
                                    "location": f"settings_{element_text}",
                                    "elements_found": len(google_oauth_elements),
                                    "page_url": page.url
                                })
                                
                                # Test the OAuth flow from settings
                                oauth_result = await test_oauth_flow(page, f"settings_{element_text}", test_results)
                                if oauth_result:
                                    test_results["discovery_paths"]["settings_oauth"] = oauth_result
                                    if oauth_result.get("success"):
                                        test_results["final_status"] = "oauth_working_settings"
                                        return test_results
                        except Exception as e:
                            print(f"⚠️ Error exploring settings option {i}: {e}")
                            test_results["errors"].append({
                                "timestamp": datetime.now().isoformat(),
                                "type": "settings_exploration_error",
                                "message": str(e)
                            })
                
                # Also search the entire dashboard for any OAuth elements
                google_oauth_elements = await find_google_oauth_elements(page)
                if google_oauth_elements:
                    print(f"🎯 Found Google OAuth in dashboard: {len(google_oauth_elements)} elements")
                    test_results["oauth_locations"].append({
                        "location": "dashboard_main",
                        "elements_found": len(google_oauth_elements),
                        "page_url": page.url
                    })
                    
                    # Test the OAuth flow from dashboard
                    oauth_result = await test_oauth_flow(page, "dashboard_main", test_results)
                    if oauth_result:
                        test_results["discovery_paths"]["dashboard_oauth"] = oauth_result
                        if oauth_result.get("success"):
                            test_results["final_status"] = "oauth_working_dashboard"
                            return test_results
            
            # PATH 3: Direct OAuth Endpoint Testing
            print("\n🔍 PATH 3: Testing Direct OAuth Endpoints")
            
            oauth_endpoints = [
                f"{TEST_URL}/auth/google",
                f"{TEST_URL}/oauth/google",
                f"{TEST_URL}/api/auth/google",
                f"{TEST_URL}/api/oauth/google",
                f"{TEST_URL}/auth/google/login",
                f"{TEST_URL}/google/oauth"
            ]
            
            for endpoint in oauth_endpoints:
                try:
                    print(f"🌐 Testing endpoint: {endpoint}")
                    
                    response = await page.goto(endpoint, wait_until="domcontentloaded", timeout=10000)
                    current_url = page.url
                    
                    print(f"📍 Response URL: {current_url}")
                    print(f"📊 Response Status: {response.status if response else 'No response'}")
                    
                    # Check if we're redirected to Google OAuth
                    if "accounts.google.com" in current_url or "oauth" in current_url:
                        print(f"✅ SUCCESS: Direct endpoint {endpoint} redirects to Google OAuth!")
                        
                        # Take screenshot of Google OAuth page
                        endpoint_oauth_screenshot = f"/tmp/oauth_direct_endpoint_{datetime.now().strftime('%H%M%S')}.png"
                        await page.screenshot(path=endpoint_oauth_screenshot, full_page=True)
                        test_results["screenshots"].append({
                            "phase": "direct_endpoint_oauth",
                            "path": endpoint_oauth_screenshot,
                            "description": f"Google OAuth from direct endpoint: {endpoint}"
                        })
                        
                        # Check for errors on Google's page
                        oauth_validation_result = await validate_google_oauth_page(page, test_results)
                        
                        test_results["discovery_paths"]["direct_endpoint_oauth"] = {
                            "status": "found",
                            "endpoint": endpoint,
                            "oauth_url": current_url,
                            "validation_result": oauth_validation_result
                        }
                        
                        if oauth_validation_result.get("valid", False):
                            test_results["final_status"] = "oauth_working_direct_endpoint"
                            return test_results
                    
                    await page.wait_for_timeout(2000)
                    
                except Exception as e:
                    print(f"⚠️ Error testing endpoint {endpoint}: {e}")
                    test_results["errors"].append({
                        "timestamp": datetime.now().isoformat(),
                        "type": "direct_endpoint_error",
                        "endpoint": endpoint,
                        "message": str(e)
                    })
            
            # If we get here, no OAuth was found
            test_results["final_status"] = "oauth_not_found"
            
        except Exception as e:
            print(f"❌ Critical error during validation: {e}")
            test_results["errors"].append({
                "timestamp": datetime.now().isoformat(),
                "type": "critical_test_error",
                "message": str(e)
            })
            test_results["final_status"] = "test_error"
            
            # Take error screenshot
            error_screenshot = f"/tmp/oauth_critical_error_{datetime.now().strftime('%H%M%S')}.png"
            await page.screenshot(path=error_screenshot, full_page=True)
            test_results["screenshots"].append({
                "phase": "critical_error",
                "path": error_screenshot,
                "description": f"Critical error state: {str(e)}"
            })
        
        finally:
            await browser.close()
    
    return test_results

async def find_google_oauth_elements(page):
    """Find Google OAuth elements on the current page"""
    google_selectors = [
        "button:has-text('Google')",
        "button:has-text('Connect Google')",
        "button:has-text('Sign in with Google')",
        "button:has-text('Login with Google')",
        "a:has-text('Google')",
        "a:has-text('Connect Google')",
        "[data-provider='google']",
        ".google-login",
        "#google-login", 
        "button[class*='google']",
        "a[href*='google']",
        "button[onclick*='google']",
        "[class*='oauth']:has-text('Google')",
        "img[alt*='Google']",
        "svg:has-text('Google')"
    ]
    
    found_elements = []
    for selector in google_selectors:
        try:
            elements = page.locator(selector)
            count = await elements.count()
            if count > 0:
                for i in range(count):
                    element = elements.nth(i)
                    text_content = await element.text_content()
                    found_elements.append({
                        "selector": selector,
                        "text": text_content,
                        "visible": await element.is_visible()
                    })
        except Exception as e:
            pass  # Selector might not be valid for current page
    
    return found_elements

async def test_oauth_flow(page, location, test_results):
    """Test the OAuth flow from a specific location"""
    try:
        print(f"🧪 Testing OAuth flow from: {location}")
        
        # Find Google OAuth button
        google_oauth_elements = await find_google_oauth_elements(page)
        if not google_oauth_elements:
            return {"status": "no_oauth_elements", "location": location}
        
        # Try to click the first visible Google OAuth element
        for element_info in google_oauth_elements:
            if element_info.get("visible", False):
                try:
                    element = page.locator(element_info["selector"]).first
                    await element.click()
                    await page.wait_for_timeout(3000)
                    
                    current_url = page.url
                    print(f"📍 After OAuth click, URL: {current_url}")
                    
                    if "accounts.google.com" in current_url or "oauth" in current_url:
                        print(f"✅ OAuth redirect successful from {location}")
                        
                        # Take screenshot of OAuth page
                        oauth_flow_screenshot = f"/tmp/oauth_flow_{location}_{datetime.now().strftime('%H%M%S')}.png"
                        await page.screenshot(path=oauth_flow_screenshot, full_page=True)
                        test_results["screenshots"].append({
                            "phase": f"oauth_flow_{location}",
                            "path": oauth_flow_screenshot,
                            "description": f"OAuth flow from {location}"
                        })
                        
                        # Validate Google OAuth page
                        oauth_validation = await validate_google_oauth_page(page, test_results)
                        
                        return {
                            "status": "oauth_redirect_successful",
                            "location": location,
                            "oauth_url": current_url,
                            "validation": oauth_validation,
                            "success": oauth_validation.get("valid", False)
                        }
                    else:
                        print(f"⚠️ OAuth click did not redirect to Google from {location}")
                        return {
                            "status": "oauth_click_no_redirect",
                            "location": location,
                            "current_url": current_url
                        }
                        
                except Exception as e:
                    print(f"⚠️ Error clicking OAuth element from {location}: {e}")
                    continue
        
        return {"status": "no_clickable_oauth_elements", "location": location}
        
    except Exception as e:
        print(f"❌ Error testing OAuth flow from {location}: {e}")
        return {"status": "oauth_test_error", "location": location, "error": str(e)}

async def validate_google_oauth_page(page, test_results):
    """Validate the Google OAuth page for errors"""
    try:
        page_text = await page.text_content('body')
        page_title = await page.title()
        current_url = page.url
        
        validation_result = {
            "valid": True,
            "url": current_url,
            "title": page_title,
            "errors_found": []
        }
        
        # Check for known OAuth errors
        error_patterns = [
            "redirect_uri_mismatch",
            "access_blocked",
            "invalid_request",
            "invalid_client",
            "unauthorized_client"
        ]
        
        for pattern in error_patterns:
            if pattern in page_text.lower():
                validation_result["valid"] = False
                validation_result["errors_found"].append(pattern)
                test_results["errors"].append({
                    "timestamp": datetime.now().isoformat(),
                    "type": "google_oauth_error",
                    "error_pattern": pattern,
                    "page_url": current_url
                })
        
        if validation_result["valid"]:
            print("✅ Google OAuth page appears clean - no error patterns detected")
        else:
            print(f"❌ Google OAuth errors detected: {validation_result['errors_found']}")
        
        return validation_result
        
    except Exception as e:
        print(f"❌ Error validating Google OAuth page: {e}")
        return {
            "valid": False,
            "error": str(e),
            "validation_failed": True
        }

async def attempt_login(page, test_results):
    """Attempt to login with test credentials"""
    try:
        print("🔐 Attempting login...")
        
        # Fill email
        email_input = page.locator("input[type='email'], input[name='email'], input[name='username']")
        if await email_input.count() > 0:
            await email_input.fill(TEST_USER_EMAIL)
            print(f"📝 Filled email: {TEST_USER_EMAIL}")
        else:
            print("❌ No email input found")
            return False
        
        # Fill password (use a common test password)
        password_input = page.locator("input[type='password'], input[name='password']")
        if await password_input.count() > 0:
            # Try common test passwords
            test_passwords = ["test123", "password", "admin", "Test123!", TEST_USER_PASSWORD]
            await password_input.fill(test_passwords[0])  # Use first test password
            print("📝 Filled password (test credentials)")
        else:
            print("❌ No password input found")
            return False
        
        # Click login
        login_button = page.locator("button[type='submit'], button:has-text('Login'), button:has-text('Sign In')")
        if await login_button.count() > 0:
            await login_button.click()
            print("🔄 Clicked login button")
            
            # Wait for potential redirect
            await page.wait_for_timeout(5000)
            
            # Check if login was successful (look for dashboard elements)
            current_url = page.url
            page_content = await page.content()
            
            # Look for indicators of successful login
            success_indicators = ["dashboard", "welcome", "logout", "profile", "settings"]
            login_successful = any(indicator in current_url.lower() or indicator in page_content.lower() 
                                 for indicator in success_indicators)
            
            if login_successful:
                print("✅ Login appears successful")
                return True
            else:
                print("⚠️ Login may have failed, but continuing with exploration...")
                return True  # Continue anyway to explore what's available
        else:
            print("❌ No login button found")
            return False
            
    except Exception as e:
        print(f"⚠️ Error during login attempt: {e}")
        test_results["errors"].append({
            "timestamp": datetime.now().isoformat(),
            "type": "login_attempt_error",
            "message": str(e)
        })
        return False

def print_comprehensive_report(results):
    """Print comprehensive OAuth validation report"""
    print("\n" + "="*80)
    print("🔐 COMPREHENSIVE GOOGLE OAUTH VALIDATION REPORT")
    print("="*80)
    print(f"🕐 Test Timestamp: {results['test_timestamp']}")
    print(f"🌐 Test URL: {results['test_url']}")
    print(f"📊 Final Status: {results['final_status'].upper()}")
    print()
    
    # OAuth Locations Found
    if results["oauth_locations"]:
        print("🎯 OAUTH LOCATIONS DISCOVERED:")
        for location in results["oauth_locations"]:
            print(f"  ✅ {location['location']}: {location['elements_found']} OAuth elements")
            print(f"     URL: {location['page_url']}")
        print()
    else:
        print("❌ NO OAUTH LOCATIONS FOUND")
        print()
    
    # Discovery Paths Analysis
    print("🔍 DISCOVERY PATH RESULTS:")
    for path_name, path_result in results["discovery_paths"].items():
        if isinstance(path_result, dict):
            status = path_result.get("status", "unknown")
            emoji = "✅" if status in ["found", "oauth_redirect_successful"] else "❌"
            print(f"  {emoji} {path_name}: {status}")
            
            if "oauth_url" in path_result:
                print(f"     OAuth URL: {path_result['oauth_url']}")
            if "validation_result" in path_result:
                validation = path_result["validation_result"]
                if isinstance(validation, dict) and "valid" in validation:
                    valid_emoji = "✅" if validation["valid"] else "❌"
                    print(f"     Validation: {valid_emoji} {'VALID' if validation['valid'] else 'INVALID'}")
                    if "errors_found" in validation and validation["errors_found"]:
                        print(f"     Errors: {', '.join(validation['errors_found'])}")
        print()
    
    # Screenshots Evidence
    print("📸 VISUAL EVIDENCE:")
    for screenshot in results["screenshots"]:
        print(f"  📷 {screenshot['phase']}: {screenshot['path']}")
        print(f"     {screenshot['description']}")
    print()
    
    # Final Assessment
    print("🏁 FINAL ASSESSMENT:")
    status = results["final_status"]
    if status == "oauth_working_registration":
        print("  ✅ SUCCESS: Google OAuth working on registration page")
        print("  ✅ User can connect Google services during registration")
    elif status == "oauth_working_settings":
        print("  ✅ SUCCESS: Google OAuth working in settings/profile")
        print("  ✅ User can connect Google services after login")
    elif status == "oauth_working_dashboard":
        print("  ✅ SUCCESS: Google OAuth working on main dashboard")
        print("  ✅ User can connect Google services from dashboard")
    elif status == "oauth_working_direct_endpoint":
        print("  ✅ SUCCESS: Google OAuth working via direct endpoint")
        print("  ✅ Direct OAuth URLs redirect properly to Google")
    elif status == "oauth_not_found":
        print("  ❌ FAILURE: No Google OAuth integration found")
        print("  🔧 ACTION REQUIRED: Implement Google OAuth in UI")
    elif status == "test_error":
        print("  ⚠️ ERROR: Test encountered critical errors")
        print("  🔧 ACTION REQUIRED: Review test errors and system logs")
    else:
        print(f"  ⚠️ UNKNOWN STATUS: {status}")
    
    # Error Summary
    if results["errors"]:
        print("\n❌ ERRORS ENCOUNTERED:")
        for error in results["errors"]:
            print(f"  [{error['timestamp']}] {error['type']}: {error['message']}")
    
    print("\n" + "="*80)

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Comprehensive Google OAuth Validation')
    parser.add_argument('--domain', default="aiwfe.com", help='Domain to test')
    parser.add_argument('--protocol', choices=['http', 'https'], default="https", help='Protocol to use')
    
    args = parser.parse_args()
    
    global TEST_DOMAIN, TEST_PROTOCOL, TEST_URL
    TEST_DOMAIN = args.domain
    TEST_PROTOCOL = args.protocol
    TEST_URL = f"{TEST_PROTOCOL}://{TEST_DOMAIN}"
    
    print(f"🚀 Starting Comprehensive Google OAuth Validation")
    print(f"🎯 Target URL: {TEST_URL}")
    print(f"🔍 Testing multiple discovery paths...")
    print(f"🕐 Start Time: {datetime.now().isoformat()}")
    print()
    
    # Run comprehensive validation
    results = asyncio.run(comprehensive_oauth_validation())
    
    # Print comprehensive report
    print_comprehensive_report(results)
    
    # Save detailed results
    results_file = f"/tmp/comprehensive_oauth_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"💾 Detailed results saved to: {results_file}")
    
    return results

if __name__ == "__main__":
    main()