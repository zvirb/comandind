import asyncio
from playwright.async_api import async_playwright, expect

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Listen for all console events and print them
        page.on("console", lambda msg: print(f"Browser Console: {msg.text}"))

        try:
            # Set a consistent viewport size
            await page.set_viewport_size({"width": 1280, "height": 720})

            # Navigate to the game
            await page.goto("http://localhost:3000/")

            # Wait for the loading screen to disappear
            loading_screen = page.locator("#loading-screen")
            await expect(loading_screen).to_be_hidden(timeout=30000)

            # The main menu is on the canvas, so we can't use DOM selectors.
            # We need to click based on coordinates.
            # "New Game" button position from MainMenu.js:
            # x = (1280 - 300) / 2 = 490
            # y = 300
            # We click in the middle of the button.
            new_game_button_x = (1280 - 300) / 2 + 150
            new_game_button_y = 300 + 30

            await page.mouse.click(new_game_button_x, new_game_button_y)

            # Wait for the game to start (main menu to disappear)
            await page.wait_for_timeout(1000)

            # 1. Select a GDI unit (player faction)
            # The first GDI unit is created at roughly (200, 200)
            await page.mouse.click(200, 200)

            # Give a moment for the selection visual to appear
            await page.wait_for_timeout(500)

            # 2. Issue an attack command on a NOD unit (enemy faction)
            # The first NOD unit is at roughly (200, 300)
            await page.mouse.click(200, 300, button="right")

            # 3. Wait for the unit to move
            await page.wait_for_timeout(2000)

            # 4. Take a screenshot
            await page.screenshot(path="jules-scratch/verification/combat_verification.png")

            print("Verification script completed successfully.")

        except Exception as e:
            print(f"An error occurred: {e}")
            await page.screenshot(path="jules-scratch/verification/error.png")

        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
