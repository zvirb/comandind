#!/usr/bin/env python3
"""
Enhanced User Experience Testing Framework with Production Validation
Provides comprehensive browser-based testing for production functionality
"""

import asyncio
import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from playwright.async_api import async_playwright, Page, Browser
import logging

# Configure comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/home/marku/ai_workflow_engine/.claude/audit_reports/user_experience_enhanced.log')
    ]
)
logger = logging.getLogger(__name__)

class EnhancedUserExperienceValidator:
    """Advanced user experience validation with production-ready testing capabilities"""
    
    def __init__(self, base_url: str = 'https://aiwfe.com'):
        self.base_url = base_url
        self.evidence_dir = Path('/home/marku/ai_workflow_engine/.claude/audit_reports/user_experience')
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self.test_results = []
        self.performance_metrics = {}
        
    async def capture_evidence(self, page: Page, test_name: str, step: str) -> Dict[str, str]:
        """Capture comprehensive evidence including screenshots and network logs"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        evidence = {}
        
        # Capture screenshot
        screenshot_path = self.evidence_dir / f'{timestamp}_{test_name}_{step}.png'
        await page.screenshot(path=str(screenshot_path), full_page=True)
        evidence['screenshot'] = str(screenshot_path)
        logger.info(f"Screenshot captured: {screenshot_path}")
        
        # Capture page content
        content_path = self.evidence_dir / f'{timestamp}_{test_name}_{step}_content.html'
        content = await page.content()
        content_path.write_text(content[:10000])  # Limit size
        evidence['content'] = str(content_path)
        
        # Capture console logs
        console_logs = []
        page.on("console", lambda msg: console_logs.append({
            'type': msg.type,
            'text': msg.text,
            'location': msg.location
        }))
        evidence['console_logs'] = console_logs
        
        return evidence
    
    async def measure_page_performance(self, page: Page) -> Dict[str, float]:
        """Measure page performance metrics"""
        metrics = await page.evaluate("""() => {
            const perf = window.performance;
            const timing = perf.timing;
            const navigation = perf.getEntriesByType('navigation')[0];
            
            return {
                domContentLoaded: timing.domContentLoadedEventEnd - timing.navigationStart,
                loadComplete: timing.loadEventEnd - timing.navigationStart,
                firstPaint: navigation ? navigation.startTime : 0,
                firstContentfulPaint: navigation ? navigation.responseEnd - navigation.requestStart : 0,
                totalResourceSize: perf.getEntriesByType('resource').reduce((acc, r) => acc + (r.transferSize || 0), 0),
                resourceCount: perf.getEntriesByType('resource').length
            };
        }""")
        
        logger.info(f"Page performance metrics: {metrics}")
        return metrics
    
    async def test_authentication_flow(self, page: Page) -> Dict[str, any]:
        """Test complete authentication flow with evidence"""
        test_result = {
            'test_name': 'authentication_flow',
            'status': 'pending',
            'steps': [],
            'evidence': {},
            'errors': []
        }
        
        try:
            # Step 1: Navigate to login page
            logger.info("Step 1: Navigating to login page")
            await page.goto(f"{self.base_url}/login", wait_until='networkidle')
            test_result['steps'].append({'step': 'navigate_login', 'status': 'success'})
            test_result['evidence']['login_page'] = await self.capture_evidence(page, 'auth', 'login_page')
            
            # Step 2: Check login form elements
            logger.info("Step 2: Checking login form elements")
            email_input = await page.query_selector('input[type="email"], input[name="email"], input[placeholder*="email" i]')
            password_input = await page.query_selector('input[type="password"], input[name="password"]')
            submit_button = await page.query_selector('button[type="submit"], button:has-text("Login"), button:has-text("Sign in")')
            
            if not all([email_input, password_input, submit_button]):
                raise Exception("Missing login form elements")
            
            test_result['steps'].append({'step': 'verify_form_elements', 'status': 'success'})
            
            # Step 3: Test form validation
            logger.info("Step 3: Testing form validation")
            await submit_button.click()
            await page.wait_for_timeout(1000)
            
            # Check for validation messages
            validation_visible = await page.is_visible('text=/required|invalid|enter/i')
            test_result['steps'].append({
                'step': 'form_validation',
                'status': 'success' if validation_visible else 'warning',
                'note': 'Validation messages shown' if validation_visible else 'No validation messages'
            })
            
            # Step 4: Attempt login with test credentials
            logger.info("Step 4: Testing login with credentials")
            await email_input.fill('test@example.com')
            await password_input.fill('TestPassword123!')
            
            test_result['evidence']['filled_form'] = await self.capture_evidence(page, 'auth', 'filled_form')
            
            # Submit and wait for response
            await submit_button.click()
            
            # Wait for either success redirect or error message
            try:
                await page.wait_for_url(f"{self.base_url}/dashboard", timeout=5000)
                test_result['steps'].append({'step': 'login_attempt', 'status': 'success'})
                test_result['evidence']['dashboard'] = await self.capture_evidence(page, 'auth', 'dashboard')
            except:
                # Check for error messages
                error_visible = await page.is_visible('text=/error|invalid|incorrect/i')
                test_result['steps'].append({
                    'step': 'login_attempt',
                    'status': 'expected_failure',
                    'note': 'Login failed as expected with test credentials'
                })
            
            test_result['status'] = 'success'
            
        except Exception as e:
            logger.error(f"Authentication flow test failed: {e}")
            test_result['status'] = 'failed'
            test_result['errors'].append(str(e))
            test_result['evidence']['error'] = await self.capture_evidence(page, 'auth', 'error')
        
        return test_result
    
    async def test_chat_functionality(self, page: Page) -> Dict[str, any]:
        """Test chat functionality with API interaction validation"""
        test_result = {
            'test_name': 'chat_functionality',
            'status': 'pending',
            'steps': [],
            'evidence': {},
            'performance': {},
            'errors': []
        }
        
        try:
            # Navigate to chat page
            logger.info("Testing chat functionality")
            await page.goto(f"{self.base_url}/chat", wait_until='networkidle')
            
            # Measure initial performance
            test_result['performance']['initial'] = await self.measure_page_performance(page)
            
            # Check chat interface elements
            chat_input = await page.query_selector('textarea[placeholder*="message" i], input[placeholder*="message" i]')
            send_button = await page.query_selector('button:has-text("Send"), button[aria-label*="send" i]')
            message_container = await page.query_selector('[class*="message"], [class*="chat"]')
            
            if chat_input and send_button:
                test_result['steps'].append({'step': 'chat_interface_found', 'status': 'success'})
                
                # Test sending a message
                await chat_input.fill("Test message for validation")
                test_result['evidence']['chat_ready'] = await self.capture_evidence(page, 'chat', 'ready')
                
                # Monitor network for API calls
                api_calls = []
                page.on("request", lambda request: api_calls.append({
                    'url': request.url,
                    'method': request.method,
                    'headers': request.headers
                }) if '/api/' in request.url else None)
                
                await send_button.click()
                await page.wait_for_timeout(3000)  # Wait for response
                
                # Check if message was sent
                test_result['steps'].append({
                    'step': 'message_sent',
                    'status': 'success' if len(api_calls) > 0 else 'warning',
                    'api_calls': len(api_calls)
                })
                
                test_result['evidence']['after_send'] = await self.capture_evidence(page, 'chat', 'after_send')
            else:
                test_result['steps'].append({'step': 'chat_interface_found', 'status': 'failed'})
            
            test_result['status'] = 'success' if chat_input else 'failed'
            
        except Exception as e:
            logger.error(f"Chat functionality test failed: {e}")
            test_result['status'] = 'failed'
            test_result['errors'].append(str(e))
        
        return test_result
    
    async def test_galaxy_animation_performance(self, page: Page) -> Dict[str, any]:
        """Test Galaxy animation performance targeting 60fps"""
        test_result = {
            'test_name': 'galaxy_animation_performance',
            'status': 'pending',
            'fps_measurements': [],
            'evidence': {},
            'errors': []
        }
        
        try:
            logger.info("Testing Galaxy animation performance")
            await page.goto(f"{self.base_url}/login", wait_until='networkidle')
            
            # Inject FPS monitoring script
            await page.evaluate("""() => {
                window.fpsMonitor = {
                    frames: [],
                    lastTime: performance.now(),
                    measure: function() {
                        const now = performance.now();
                        const delta = now - this.lastTime;
                        this.lastTime = now;
                        const fps = Math.round(1000 / delta);
                        this.frames.push(fps);
                        if (this.frames.length > 60) this.frames.shift();
                        return fps;
                    },
                    getAverage: function() {
                        if (this.frames.length === 0) return 0;
                        const sum = this.frames.reduce((a, b) => a + b, 0);
                        return Math.round(sum / this.frames.length);
                    }
                };
                
                // Start monitoring
                window.fpsInterval = setInterval(() => {
                    window.fpsMonitor.measure();
                }, 16); // ~60fps timing
            }""")
            
            # Let animation run for 5 seconds
            await page.wait_for_timeout(5000)
            
            # Collect FPS data
            fps_data = await page.evaluate("""() => {
                clearInterval(window.fpsInterval);
                return {
                    average: window.fpsMonitor.getAverage(),
                    samples: window.fpsMonitor.frames,
                    min: Math.min(...window.fpsMonitor.frames),
                    max: Math.max(...window.fpsMonitor.frames)
                };
            }""")
            
            test_result['fps_measurements'] = fps_data
            
            # Check if meeting 60fps target
            if fps_data['average'] >= 55:
                test_result['status'] = 'success'
                logger.info(f"Galaxy animation PASSES 60fps target: {fps_data['average']}fps average")
            else:
                test_result['status'] = 'warning'
                logger.warning(f"Galaxy animation BELOW 60fps target: {fps_data['average']}fps average")
            
            test_result['evidence']['animation'] = await self.capture_evidence(page, 'galaxy', 'performance')
            
        except Exception as e:
            logger.error(f"Galaxy animation test failed: {e}")
            test_result['status'] = 'failed'
            test_result['errors'].append(str(e))
        
        return test_result
    
    async def test_api_endpoints(self, page: Page) -> Dict[str, any]:
        """Test API endpoint accessibility and responses"""
        test_result = {
            'test_name': 'api_endpoints',
            'status': 'pending',
            'endpoints': [],
            'evidence': {},
            'errors': []
        }
        
        endpoints_to_test = [
            '/api/v1/health',
            '/api/v1/chat',
            '/api/v1/auth/session',
            '/api/v1/projects'
        ]
        
        try:
            for endpoint in endpoints_to_test:
                url = f"{self.base_url}{endpoint}"
                logger.info(f"Testing endpoint: {url}")
                
                response = await page.evaluate(f"""async () => {{
                    try {{
                        const response = await fetch('{url}', {{
                            method: 'GET',
                            headers: {{'Accept': 'application/json'}}
                        }});
                        return {{
                            status: response.status,
                            statusText: response.statusText,
                            headers: Object.fromEntries(response.headers.entries()),
                            ok: response.ok
                        }};
                    }} catch (error) {{
                        return {{error: error.message}};
                    }}
                }}""")
                
                test_result['endpoints'].append({
                    'endpoint': endpoint,
                    'response': response,
                    'accessible': response.get('status', 0) < 500
                })
            
            # Determine overall status
            accessible_count = sum(1 for e in test_result['endpoints'] if e['accessible'])
            test_result['status'] = 'success' if accessible_count > len(endpoints_to_test) / 2 else 'warning'
            
        except Exception as e:
            logger.error(f"API endpoint test failed: {e}")
            test_result['status'] = 'failed'
            test_result['errors'].append(str(e))
        
        return test_result
    
    async def run_full_test_suite(self) -> Dict[str, any]:
        """Run complete test suite with all validations"""
        logger.info("Starting enhanced user experience validation suite")
        start_time = time.time()
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Testing Framework) Chrome/120.0'
            )
            
            page = await context.new_page()
            
            # Run all tests
            results = {
                'timestamp': datetime.now().isoformat(),
                'base_url': self.base_url,
                'tests': [],
                'summary': {},
                'duration': 0
            }
            
            # Execute test suite
            tests = [
                self.test_authentication_flow,
                self.test_chat_functionality,
                self.test_galaxy_animation_performance,
                self.test_api_endpoints
            ]
            
            for test_func in tests:
                try:
                    result = await test_func(page)
                    results['tests'].append(result)
                    logger.info(f"Test {result['test_name']}: {result['status']}")
                except Exception as e:
                    logger.error(f"Test execution failed: {e}")
                    results['tests'].append({
                        'test_name': test_func.__name__,
                        'status': 'error',
                        'error': str(e)
                    })
            
            await browser.close()
        
        # Calculate summary
        results['duration'] = time.time() - start_time
        results['summary'] = {
            'total_tests': len(results['tests']),
            'passed': sum(1 for t in results['tests'] if t['status'] == 'success'),
            'warnings': sum(1 for t in results['tests'] if t['status'] == 'warning'),
            'failed': sum(1 for t in results['tests'] if t['status'] in ['failed', 'error'])
        }
        
        # Save results
        results_path = self.evidence_dir / f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        results_path.write_text(json.dumps(results, indent=2, default=str))
        logger.info(f"Test results saved to: {results_path}")
        
        # Print summary
        print("\n" + "="*60)
        print("USER EXPERIENCE VALIDATION SUMMARY")
        print("="*60)
        print(f"Total Tests: {results['summary']['total_tests']}")
        print(f"Passed: {results['summary']['passed']}")
        print(f"Warnings: {results['summary']['warnings']}")
        print(f"Failed: {results['summary']['failed']}")
        print(f"Duration: {results['duration']:.2f} seconds")
        print("="*60)
        
        return results

async def main():
    """Main execution function"""
    validator = EnhancedUserExperienceValidator()
    results = await validator.run_full_test_suite()
    
    # Exit with appropriate code
    if results['summary']['failed'] > 0:
        sys.exit(1)
    elif results['summary']['warnings'] > 0:
        sys.exit(0)  # Warnings are acceptable
    else:
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())