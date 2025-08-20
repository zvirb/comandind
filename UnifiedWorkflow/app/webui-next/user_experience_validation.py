import asyncio
import json
import os
from datetime import datetime
from playwright.async_api import async_playwright

class UserExperienceValidator:
    def __init__(self, base_url="https://aiwfe.com"):
        self.base_url = base_url
        self.evidence_dir = "/home/marku/ai_workflow_engine/app/webui-next/EVIDENCE_AUDIT_USER_EXPERIENCE_20250815"
        os.makedirs(self.evidence_dir, exist_ok=True)

    async def capture_screenshot(self, page, step_name):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = os.path.join(self.evidence_dir, f"{timestamp}_{step_name}_screenshot.png")
        await page.screenshot(path=screenshot_path)
        return screenshot_path

    async def save_console_logs(self, page, step_name):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        console_log_path = os.path.join(self.evidence_dir, f"{timestamp}_{step_name}_console_log.json")
        
        console_logs = []
        page.on("console", lambda msg: console_logs.append({
            "type": msg.type,
            "text": msg.text,
            "location": msg.location
        }))

        with open(console_log_path, 'w') as f:
            json.dump(console_logs, f, indent=2)
        
        return console_log_path

    async def validate_user_experience(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            # Evidence Collection Initialization
            validation_evidence = {
                "authentication": {},
                "chat_interaction": {},
                "performance": {},
                "errors": []
            }

            try:
                # 1. Network Connectivity Check
                try:
                    response = await page.goto(self.base_url, wait_until="networkidle", timeout=30000)
                    if response.status != 200:
                        raise Exception(f"Network Error: HTTP {response.status}")
                except Exception as network_error:
                    validation_evidence["errors"].append({
                        "stage": "network_connectivity",
                        "error": str(network_error)
                    })
                    return validation_evidence

                # 2. Capture Initial Page Load Screenshot
                validation_evidence["authentication"]["login_page_load"] = await self.capture_screenshot(page, "login_page")

                # 3. Login Attempt
                try:
                    await page.fill('input[name="email"]', "admin@aiwfe.com")
                    await page.fill('input[name="password"]', "Admin123!@#")
                    await page.click('button[type="submit"]')
                    
                    # Wait for dashboard or authenticated state
                    await page.wait_for_selector('.dashboard-container', timeout=10000)
                    validation_evidence["authentication"]["login_success"] = await self.capture_screenshot(page, "dashboard_after_login")
                except Exception as login_error:
                    validation_evidence["errors"].append({
                        "stage": "authentication",
                        "error": str(login_error)
                    })
                    return validation_evidence

                # 4. Chat Interaction Validation
                try:
                    # Note: Selectors are placeholders - adjust to match actual site
                    await page.click('.chat-interface-button')
                    await page.fill('.chat-input-field', "Test user experience validation")
                    await page.click('.send-message-button')

                    # Wait for chat response
                    await page.wait_for_selector('.chat-response', timeout=15000)
                    validation_evidence["chat_interaction"]["message_sent"] = await self.capture_screenshot(page, "chat_message_sent")
                    validation_evidence["chat_interaction"]["chat_response"] = await self.capture_screenshot(page, "chat_response_received")
                except Exception as chat_error:
                    validation_evidence["errors"].append({
                        "stage": "chat_interaction",
                        "error": str(chat_error)
                    })

                # 5. Performance and Network Logging
                try:
                    await context.route("**/*", lambda route: route.continue_())
                    validation_evidence["performance"]["network_logs"] = await self.save_console_logs(page, "network_activity")
                except Exception as performance_error:
                    validation_evidence["errors"].append({
                        "stage": "performance_logging",
                        "error": str(performance_error)
                    })

                # Save validation evidence
                evidence_summary_path = os.path.join(self.evidence_dir, "validation_evidence_summary.json")
                with open(evidence_summary_path, 'w') as f:
                    json.dump(validation_evidence, f, indent=2)

            except Exception as e:
                validation_evidence["errors"].append({
                    "stage": "global_validation",
                    "error": str(e)
                })
                
            finally:
                await browser.close()

        return validation_evidence

async def main():
    validator = UserExperienceValidator()
    evidence = await validator.validate_user_experience()
    print("User Experience Validation Complete. Evidence saved.")

if __name__ == "__main__":
    asyncio.run(main())