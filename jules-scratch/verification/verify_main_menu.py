from playwright.sync_api import sync_playwright

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    try:
        # Navigate to the local development server
        page.goto("http://localhost:3000/")

        # Wait for a bit to ensure everything has loaded
        page.wait_for_timeout(5000)

        # Take a screenshot of the main menu
        page.screenshot(path="jules-scratch/verification/main_menu.png")
        print("Screenshot of the main menu taken.")

        # Click on the coordinates of the "New Game" button
        page.mouse.click(640, 330)

        # Wait for a bit to ensure the game has started
        page.wait_for_timeout(2000)

        # Take a screenshot of the in-game view
        page.screenshot(path="jules-scratch/verification/in_game_view.png")
        print("Screenshot of the in-game view taken.")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Close browser
        context.close()
        browser.close()

with sync_playwright() as playwright:
    run(playwright)
