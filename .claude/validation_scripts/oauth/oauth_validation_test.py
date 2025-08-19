#!/usr/bin/env python3
"""
Google OAuth User Experience Validation Script

Specifically tests the Google OAuth flow to validate fixes for redirect_uri_mismatch errors.
"""

import asyncio
import json
import argparse
import os
from datetime import datetime
from playwright.async_api import async_playwright

# Test domain configuration
TEST_DOMAIN = os.getenv("WEBUI_TEST_DOMAIN", "aiwfe.com")
TEST_PROTOCOL = os.getenv("WEBUI_TEST_PROTOCOL", "https")
TEST_URL = f"{TEST_PROTOCOL}://{TEST_DOMAIN}"

async def validate_google_oauth_flow():
    """
    Validate the complete Google OAuth user experience flow
    """
    test_results = {
        "test_timestamp": datetime.now().isoformat(),
        "test_url": TEST_URL,
        "phases": {},
        "screenshots": [],
        "console_messages": [],
        "network_requests": [],
        "errors": [],
        "oauth_flow_status": "unknown"
    }
    
    async with async_playwright() as p:
        # Launch browser with certificate ignoring for development
        browser = await p.chromium.launch(
            headless=True,  # Use headless mode for server environment
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
        
        # Set up event listeners
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
        
        page.on("response", lambda response: test_results["network_requests"].append({
            "timestamp": datetime.now().isoformat(),
            "url": response.url,
            "status": response.status,
            "status_text": response.status_text,
            "headers": dict(response.headers) if response.status >= 400 else {}
        }) if response.status >= 400 or "oauth" in response.url.lower() or "google" in response.url.lower() else None)
        
        try:
            # Phase 1: Initial Navigation
            print(f"🌐 Phase 1: Navigating to {TEST_URL}")
            await page.goto(TEST_URL, wait_until="domcontentloaded", timeout=30000)
            
            # Take initial screenshot
            screenshot_path = f"/tmp/oauth_validation_initial_{datetime.now().strftime('%H%M%S')}.png"
            await page.screenshot(path=screenshot_path, full_page=True)
            test_results["screenshots"].append({
                "phase": "initial_navigation",
                "path": screenshot_path,
                "description": "Initial page load"
            })
            print(f"📸 Initial screenshot: {screenshot_path}")
            
            # Wait for page to stabilize
            await page.wait_for_timeout(3000)
            
            test_results["phases"]["initial_navigation"] = {
                "status": "completed",
                "url": page.url,
                "title": await page.title()
            }
            
            # Phase 2: Look for OAuth/Google Login Options
            print("🔍 Phase 2: Searching for Google OAuth login options")
            
            # Look for Google login/connect buttons
            google_selectors = [
                "button:has-text('Google')",
                "button:has-text('Connect Google')",  
                "button:has-text('Sign in with Google')",
                "a:has-text('Google')",
                "a:has-text('Connect Google')",
                "[data-provider='google']",
                ".google-login",
                "#google-login",
                "button[class*='google']",
                "a[href*='google']",
                "button[onclick*='google']"
            ]
            
            google_button = None
            google_button_selector = None
            
            for selector in google_selectors:
                try:
                    elements = page.locator(selector)
                    count = await elements.count()
                    if count > 0:
                        google_button = elements.first
                        google_button_selector = selector
                        print(f"✅ Found Google button with selector: {selector}")
                        break
                except Exception as e:
                    print(f"⚠️ Error checking selector {selector}: {e}")
            
            if not google_button:
                # Check page content for OAuth-related text
                page_content = await page.content()
                if "google" in page_content.lower() or "oauth" in page_content.lower():
                    print("🔍 Page contains OAuth/Google references, searching more broadly")
                    
                    # Take screenshot for manual analysis
                    content_screenshot = f"/tmp/oauth_search_content_{datetime.now().strftime('%H%M%S')}.png"
                    await page.screenshot(path=content_screenshot, full_page=True)
                    test_results["screenshots"].append({
                        "phase": "oauth_search",
                        "path": content_screenshot,
                        "description": "Page content during OAuth button search"
                    })
                    
                    # Look for any buttons or links that might trigger OAuth
                    all_buttons = page.locator("button, a[href*='auth'], a[href*='login'], a[href*='connect']")
                    button_count = await all_buttons.count()
                    print(f"🔍 Found {button_count} potential auth-related elements")
                    
                    if button_count > 0:
                        # Try the first few buttons
                        for i in range(min(5, button_count)):
                            try:
                                button = all_buttons.nth(i)
                                button_text = await button.text_content()
                                button_href = await button.get_attribute('href') if await button.get_attribute('href') else ''
                                print(f"🖱️ Potential button {i}: '{button_text}' href: '{button_href}'")
                                
                                if 'google' in button_text.lower() or 'oauth' in button_href.lower():
                                    google_button = button
                                    google_button_selector = f"button_index_{i}"
                                    print(f"✅ Selected potential Google OAuth button: '{button_text}'")
                                    break
                            except Exception as e:
                                print(f"⚠️ Error analyzing button {i}: {e}")
                
            if google_button:
                test_results["phases"]["oauth_button_found"] = {
                    "status": "completed",
                    "selector": google_button_selector,
                    "button_text": await google_button.text_content() if google_button else "unknown"
                }
                
                # Phase 3: Click Google OAuth Button
                print("🖱️ Phase 3: Clicking Google OAuth button")
                
                # Take screenshot before clicking
                pre_click_screenshot = f"/tmp/oauth_pre_click_{datetime.now().strftime('%H%M%S')}.png"
                await page.screenshot(path=pre_click_screenshot, full_page=True)
                test_results["screenshots"].append({
                    "phase": "pre_oauth_click",
                    "path": pre_click_screenshot,
                    "description": "Page before clicking OAuth button"
                })
                
                # Click the Google OAuth button
                await google_button.click()
                print("🔐 Clicked Google OAuth button")
                
                # Wait for navigation or popup
                await page.wait_for_timeout(3000)
                
                # Check if we're redirected to Google OAuth
                current_url = page.url
                print(f"📍 Current URL after click: {current_url}")
                
                if "accounts.google.com" in current_url or "oauth" in current_url.lower():
                    print("✅ Successfully redirected to Google OAuth!")
                    test_results["oauth_flow_status"] = "redirect_successful"
                    
                    # Take screenshot of Google OAuth page
                    oauth_screenshot = f"/tmp/oauth_google_consent_{datetime.now().strftime('%H%M%S')}.png"
                    await page.screenshot(path=oauth_screenshot, full_page=True)
                    test_results["screenshots"].append({
                        "phase": "google_oauth_consent",
                        "path": oauth_screenshot,
                        "description": "Google OAuth consent screen"
                    })
                    
                    test_results["phases"]["google_oauth_redirect"] = {
                        "status": "completed",
                        "oauth_url": current_url,
                        "redirect_successful": True
                    }
                    
                    # Check for error messages on Google's page
                    page_text = await page.text_content('body')
                    if "redirect_uri_mismatch" in page_text.lower():
                        print("❌ CRITICAL: redirect_uri_mismatch error detected!")
                        test_results["oauth_flow_status"] = "redirect_uri_mismatch_error"
                        test_results["errors"].append({
                            "timestamp": datetime.now().isoformat(),
                            "type": "oauth_error",
                            "message": "redirect_uri_mismatch detected in Google OAuth response"
                        })
                    elif "access_blocked" in page_text.lower():
                        print("❌ CRITICAL: Access blocked error detected!")
                        test_results["oauth_flow_status"] = "access_blocked_error"
                        test_results["errors"].append({
                            "timestamp": datetime.now().isoformat(),
                            "type": "oauth_error", 
                            "message": "Access blocked detected in Google OAuth response"
                        })
                    elif "invalid_request" in page_text.lower():
                        print("❌ CRITICAL: Invalid request error detected!")
                        test_results["oauth_flow_status"] = "invalid_request_error"
                        test_results["errors"].append({
                            "timestamp": datetime.now().isoformat(),
                            "type": "oauth_error",
                            "message": "Invalid request detected in Google OAuth response"
                        })
                    else:
                        print("✅ No OAuth error messages detected - consent screen appears clean")
                        if test_results["oauth_flow_status"] == "redirect_successful":
                            test_results["oauth_flow_status"] = "consent_screen_clean"
                    
                    # Wait a bit more to capture any dynamic content
                    await page.wait_for_timeout(2000)
                    
                    # Take final Google OAuth screenshot
                    final_oauth_screenshot = f"/tmp/oauth_final_google_{datetime.now().strftime('%H%M%S')}.png"
                    await page.screenshot(path=final_oauth_screenshot, full_page=True)
                    test_results["screenshots"].append({
                        "phase": "final_google_oauth",
                        "path": final_oauth_screenshot,
                        "description": "Final Google OAuth page state"
                    })
                    
                else:
                    print(f"⚠️ OAuth redirect may have failed - still on: {current_url}")
                    test_results["oauth_flow_status"] = "redirect_failed"
                    test_results["phases"]["google_oauth_redirect"] = {
                        "status": "failed",
                        "current_url": current_url,
                        "redirect_successful": False
                    }
                    
                    # Take screenshot of failed redirect
                    failed_redirect_screenshot = f"/tmp/oauth_failed_redirect_{datetime.now().strftime('%H%M%S')}.png"
                    await page.screenshot(path=failed_redirect_screenshot, full_page=True)
                    test_results["screenshots"].append({
                        "phase": "failed_oauth_redirect",
                        "path": failed_redirect_screenshot,
                        "description": "Page after failed OAuth redirect"
                    })
                
            else:
                print("❌ No Google OAuth button found")
                test_results["phases"]["oauth_button_found"] = {
                    "status": "failed",
                    "reason": "No Google OAuth button found on page"
                }
                test_results["oauth_flow_status"] = "no_oauth_button"
                
                # Take screenshot for debugging
                no_button_screenshot = f"/tmp/oauth_no_button_{datetime.now().strftime('%H%M%S')}.png"
                await page.screenshot(path=no_button_screenshot, full_page=True)
                test_results["screenshots"].append({
                    "phase": "no_oauth_button",
                    "path": no_button_screenshot,
                    "description": "Page when no OAuth button was found"
                })
            
            # Wait for any additional network requests to complete
            await page.wait_for_timeout(5000)
            
        except Exception as e:
            print(f"❌ Error during OAuth validation: {e}")
            test_results["errors"].append({
                "timestamp": datetime.now().isoformat(),
                "type": "test_error",
                "message": str(e)
            })
            
            # Take error screenshot
            error_screenshot = f"/tmp/oauth_error_{datetime.now().strftime('%H%M%S')}.png"
            await page.screenshot(path=error_screenshot, full_page=True)
            test_results["screenshots"].append({
                "phase": "error",
                "path": error_screenshot,
                "description": f"Error state: {str(e)}"
            })
            
        finally:
            await browser.close()
    
    return test_results

def print_validation_report(results):
    """Print a comprehensive validation report"""
    print("\n" + "="*80)
    print("🔐 GOOGLE OAUTH USER EXPERIENCE VALIDATION REPORT")
    print("="*80)
    print(f"🕐 Test Timestamp: {results['test_timestamp']}")
    print(f"🌐 Test URL: {results['test_url']}")
    print(f"📊 OAuth Flow Status: {results['oauth_flow_status'].upper()}")
    print()
    
    # Phase Summary
    print("📋 PHASE SUMMARY:")
    for phase_name, phase_data in results["phases"].items():
        status_emoji = "✅" if phase_data["status"] == "completed" else "❌"
        print(f"  {status_emoji} {phase_name.replace('_', ' ').title()}: {phase_data['status']}")
    print()
    
    # OAuth Flow Analysis
    print("🔍 OAUTH FLOW ANALYSIS:")
    status = results["oauth_flow_status"]
    if status == "consent_screen_clean":
        print("  ✅ SUCCESS: Google OAuth consent screen displays correctly")
        print("  ✅ SUCCESS: No redirect_uri_mismatch errors detected")
        print("  ✅ SUCCESS: No access blocked errors detected")
        print("  ✅ SUCCESS: OAuth redirect working properly")
    elif status == "redirect_successful":
        print("  ✅ SUCCESS: Redirect to Google OAuth successful")
        print("  ⚠️  WARNING: Need to check for error messages on consent screen")
    elif status == "redirect_uri_mismatch_error":
        print("  ❌ FAILURE: redirect_uri_mismatch error detected!")
        print("  🔧 ACTION REQUIRED: Fix OAuth redirect URI configuration")
    elif status == "access_blocked_error":
        print("  ❌ FAILURE: Access blocked error detected!")
        print("  🔧 ACTION REQUIRED: Check OAuth client configuration")
    elif status == "no_oauth_button":
        print("  ❌ FAILURE: No Google OAuth button found on page")
        print("  🔧 ACTION REQUIRED: Verify OAuth integration is properly implemented")
    elif status == "redirect_failed":
        print("  ❌ FAILURE: OAuth redirect failed")
        print("  🔧 ACTION REQUIRED: Debug OAuth button functionality")
    else:
        print(f"  ⚠️  UNKNOWN STATUS: {status}")
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
            print(f"  [{error['timestamp']}] {error['type']}: {error['message']}")
    else:
        print("✅ NO ERRORS DETECTED")
    print()
    
    # Console Messages Summary
    if results["console_messages"]:
        error_messages = [msg for msg in results["console_messages"] if msg["type"] == "error"]
        warning_messages = [msg for msg in results["console_messages"] if msg["type"] == "warning"]
        
        print(f"🖥️  CONSOLE SUMMARY: {len(results['console_messages'])} total messages")
        print(f"  ❌ Errors: {len(error_messages)}")
        print(f"  ⚠️  Warnings: {len(warning_messages)}")
        
        if error_messages:
            print("  Recent Console Errors:")
            for error in error_messages[-3:]:  # Show last 3 errors
                print(f"    {error['text']}")
    print()
    
    # Network Requests Summary
    oauth_requests = [req for req in results["network_requests"] if "oauth" in req["url"].lower() or "google" in req["url"].lower()]
    failed_requests = [req for req in results["network_requests"] if req["status"] >= 400]
    
    print(f"🌐 NETWORK SUMMARY: {len(results['network_requests'])} tracked requests")
    print(f"  🔐 OAuth-related requests: {len(oauth_requests)}")
    print(f"  ❌ Failed requests: {len(failed_requests)}")
    
    if failed_requests:
        print("  Recent Failed Requests:")
        for req in failed_requests[-3:]:  # Show last 3 failures
            print(f"    {req['status']} {req['url']}")
    print()
    
    print("="*80)

def main():
    """Main function with argument parsing"""
    parser = argparse.ArgumentParser(description='Validate Google OAuth User Experience')
    parser.add_argument('--domain', default="aiwfe.com", help='Domain to test (default: aiwfe.com)')
    parser.add_argument('--protocol', choices=['http', 'https'], default="https", help='Protocol to use (default: https)')
    
    args = parser.parse_args()
    
    # Update global configuration
    global TEST_DOMAIN, TEST_PROTOCOL, TEST_URL
    TEST_DOMAIN = args.domain
    TEST_PROTOCOL = args.protocol
    TEST_URL = f"{TEST_PROTOCOL}://{TEST_DOMAIN}"
    
    print(f"🚀 Starting Google OAuth Validation")
    print(f"🎯 Target URL: {TEST_URL}")
    print(f"🕐 Start Time: {datetime.now().isoformat()}")
    print()
    
    # Run validation
    results = asyncio.run(validate_google_oauth_flow())
    
    # Print comprehensive report
    print_validation_report(results)
    
    # Save detailed results to file
    results_file = f"/tmp/oauth_validation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"💾 Detailed results saved to: {results_file}")
    
    return results

if __name__ == "__main__":
    main()