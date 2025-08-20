import asyncio
import os
import sys
import json
from datetime import datetime
from playwright.async_api import async_playwright
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[
    logging.StreamHandler(sys.stdout),
    logging.FileHandler('/app/user_experience_validation.log')
])

LOG_FILE = '/app/user_experience_validation.log'

class UserExperienceValidator:
    def __init__(self, base_url='https://aiwfe.com'):
        self.base_url = base_url
        self.evidence_dir = '/home/marku/ai_workflow_engine/.claude/audit_reports/user_experience'
        os.makedirs(self.evidence_dir, exist_ok=True)

    async def capture_screenshot(self, page, name):
        """Capture screenshot with timestamp and descriptive name."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = os.path.join(self.evidence_dir, f'{timestamp}_{name}.png')
        await page.screenshot(path=screenshot_path)
        return screenshot_path

    async def log_interaction(self, interaction_type, details):
        """Log user interaction details."""
        log_path = os.path.join(self.evidence_dir, 'interaction_log.json')
        timestamp = datetime.now().isoformat()
        
        log_entry = {
            'timestamp': timestamp,
            'type': interaction_type,
            'details': details
        }
        
        try:
            with open(log_path, 'r+') as f:
                try:
                    logs = json.load(f)
                except json.JSONDecodeError:
                    logs = []
                logs.append(log_entry)
                f.seek(0)
                json.dump(logs, f, indent=2)
        except FileNotFoundError:
            with open(log_path, 'w') as f:
                json.dump([log_entry], f, indent=2)

    async def validate_user_journey(self):
        logging.info(f'Starting user journey validation on {self.base_url}')
        final_results = {}
        """Comprehensive user journey validation."""
        async with async_playwright() as p:
            # Test across different browsers
            browser_types = [
                {'type': p.chromium, 'name': 'chromium'},
                {'type': p.firefox, 'name': 'firefox'},
                {'type': p.webkit, 'name': 'webkit'}
            ]
            
            results = {}
            
            for browser_config in browser_types:
                browser = await browser_config['type'].launch()
                context = await browser.new_context()
                page = await context.new_page()
                
                try:
                    # Navigate to site
                    await page.goto(self.base_url)
                    try:
                        screenshot_path = await self.capture_screenshot(page, f'{browser_config["name"]}_homepage_load')
                        logging.info(f'Screenshot captured: {screenshot_path}')
                    except Exception as screenshot_error:
                        logging.error(f'Screenshot capture failed: {screenshot_error}')
                    try:
                        await self.log_interaction('page_load', {'url': self.base_url, 'browser': browser_config['name']})
                        logging.info(f'Page load interaction logged for {browser_config["name"]}')
                    except Exception as interaction_error:
                        logging.error(f'Page load interaction logging failed: {interaction_error}')
                    
                    # Login process
                    await page.fill('input[name="email"]', 'admin@aiwfe.com')
                    await page.fill('input[name="password"]', 'Admin123!@#')
                    await page.click('button[type="submit"]')
                    
                    # Wait for login and dashboard
                    await page.wait_for_selector('.dashboard-container', timeout=10000)
                    await self.capture_screenshot(page, f'{browser_config["name"]}_dashboard_login')
                    await self.log_interaction('login', {'status': 'success', 'browser': browser_config['name']})
                    
                    # Test chat functionality
                    await page.click('.chat-input-area')
                    await page.type('.chat-input-area', 'Hello, system validation test')
                    await page.press('.chat-input-area', 'Enter')
                    
                    # Wait for chat response
                    await page.wait_for_selector('.chat-response', timeout=15000)
                    await self.capture_screenshot(page, f'{browser_config["name"]}_chat_interaction')
                    await self.log_interaction('chat_test', {'status': 'message_sent_and_received', 'browser': browser_config['name']})
                    
                    # Collect browser console logs
                    console_logs = []
                    page.on('console', lambda msg: console_logs.append({
                        'type': msg.type,
                        'text': msg.text,
                        'location': msg.location
                    }))
                    
                    results[browser_config['name']] = {
                        'login_status': 'success',
                        'chat_status': 'functional',
                        'console_logs': console_logs
                    }
                
                except Exception as e:
                    results[browser_config['name']] = {
                        'login_status': 'failed',
                        'error': str(e)
                    }
                    await self.log_interaction('test_failure', {'browser': browser_config['name'], 'error': str(e)})
                
                finally:
                    await browser.close()
            
            # Generate comprehensive test report
            report_path = os.path.join(self.evidence_dir, 'user_experience_validation_report.json')
            with open(report_path, 'w') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'base_url': self.base_url,
                    'results': results
                }, f, indent=2)
            
            return results

    async def main(self):
        """Main execution method."""
        try:
            results = await self.validate_user_journey()
            logging.info('User experience validation completed successfully')
            return results
        except Exception as main_error:
            logging.error(f'User experience validation failed: {main_error}')
            raise

if __name__ == '__main__':
    try:
        validator = UserExperienceValidator()
        results = asyncio.run(validator.main())
        sys.exit(0 if all('success' in str(result).lower() for result in results.values()) else 1)
    except Exception as e:
        logging.error(f'Critical validation failure: {e}')
        sys.exit(1)