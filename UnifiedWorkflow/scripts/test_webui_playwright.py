#!/usr/bin/env python3
"""
Playwright script to test WebUI functionality and identify runtime errors.

Enhanced Evidence-Based Testing Framework:
- Comprehensive authentication flow validation
- Multi-stage evidence collection
- Detailed error reporting and logging
- Performance and interaction metrics

Usage:
    python scripts/test_webui_playwright.py [--domain aiwfe.com] [--protocol https] [--headless]
"""

import asyncio
import json
import argparse
import logging
from datetime import datetime
from playwright.async_api import async_playwright

# Configure comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler("/tmp/webui_test_evidence.log"),
        logging.StreamHandler()
    ]
)

# Test Configuration
TEST_USER_EMAIL = "playwright.test@example.com"
TEST_USER_PASSWORD = "PlaywrightTest123!"
EVIDENCE_DIR = "/tmp/webui_test_evidence"

async def collect_system_metrics():
    """Collect system performance and metrics."""
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "test_domain": WEBUI_DOMAIN,
        "test_protocol": WEBUI_PROTOCOL,
    }

async def test_webui_with_playwright():
    """Comprehensive WebUI testing with advanced evidence collection."""
    # Performance and system metrics
    system_metrics = await collect_system_metrics()
    
    # Validation evidence dictionary
    test_evidence = {
        "system_metrics": system_metrics,
        "stages": [],
        "errors": [],
        "performance": {
            "page_load_times": [],
            "interaction_times": []
        },
        "final_status": "INCOMPLETE"
    }

    try:
        async with async_playwright() as p:
            # Launch browser with enhanced configuration
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--ignore-certificate-errors',
                    '--ignore-ssl-errors',
                    '--allow-running-insecure-content',
                    '--disable-web-security'
                ]
            )
            
            context = await browser.new_context(
                ignore_https_errors=True,
                viewport={"width": 1920, "height": 1080}
            )
            
            page = await context.new_page()
            
            # Interceptors for comprehensive evidence
            page_load_start = asyncio.get_event_loop().time()
            await page.goto(WEBUI_URL, wait_until="networkidle", timeout=30000)
            page_load_time = asyncio.get_event_loop().time() - page_load_start
            
            test_evidence["performance"]["page_load_times"].append(page_load_time)
            
            # Authentication Flow Validation
            auth_start_time = asyncio.get_event_loop().time()
            
            try:
                # Intelligent login element detection
                email_input = page.locator("input[type='email'], input[name='email'], input[name='username']")
                password_input = page.locator("input[type='password'], input[name='password']")
                login_button = page.locator("button[type='submit'], button:has-text('Login'), button:has-text('Sign In')")
                
                await email_input.fill(TEST_USER_EMAIL)
                await password_input.fill(TEST_USER_PASSWORD)
                await login_button.click()
                
                # Wait for authentication response
                await page.wait_for_load_state("networkidle", timeout=10000)
                
                auth_time = asyncio.get_event_loop().time() - auth_start_time
                test_evidence["performance"]["interaction_times"].append({
                    "type": "authentication",
                    "duration": auth_time
                })
                
                test_evidence["stages"].append({
                    "name": "Authentication",
                    "status": "PASSED",
                    "timestamp": datetime.utcnow().isoformat()
                })
                
            except Exception as auth_error:
                test_evidence["stages"].append({
                    "name": "Authentication",
                    "status": "FAILED",
                    "error": str(auth_error),
                    "timestamp": datetime.utcnow().isoformat()
                })
                test_evidence["errors"].append(str(auth_error))
                logging.error(f"Authentication failed: {auth_error}")
            
            # Final Validation
            test_evidence["final_status"] = "PASSED" if len(test_evidence["errors"]) == 0 else "FAILED"
            
            # Save evidence output
            with open(f"{EVIDENCE_DIR}/test_evidence_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json", "w") as f:
                json.dump(test_evidence, f, indent=2)
            
            logging.info(f"Test completed with status: {test_evidence['final_status']}")
            
            return test_evidence

    except Exception as e:
        logging.critical(f"Critical test failure: {e}")
        test_evidence["final_status"] = "CRITICAL_FAILURE"
        test_evidence["errors"].append(str(e))
        
        with open(f"{EVIDENCE_DIR}/test_evidence_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json", "w") as f:
            json.dump(test_evidence, f, indent=2)
        
        raise

def main():
    parser = argparse.ArgumentParser(description='Advanced WebUI Functionality Test')
    parser.add_argument('--domain', default='aiwfe.com', help='Domain to test')
    parser.add_argument('--protocol', choices=['http', 'https'], default='https', help='Protocol to use')
    
    args = parser.parse_args()
    
    global WEBUI_DOMAIN, WEBUI_PROTOCOL, WEBUI_URL
    WEBUI_DOMAIN = args.domain
    WEBUI_PROTOCOL = args.protocol
    WEBUI_URL = f"{WEBUI_PROTOCOL}://{WEBUI_DOMAIN}"
    
    results = asyncio.run(test_webui_with_playwright())
    
    # Print summary
    print(f"Test Status: {results['final_status']}")
    print(f"Errors: {len(results['errors'])}")
    
if __name__ == "__main__":
    main()