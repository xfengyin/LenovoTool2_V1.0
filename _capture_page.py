from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1400, "height": 820})
    page.goto('http://localhost:8920/screenshot.png')
    page.wait_for_load_state('networkidle')
    page.screenshot(path='/workspace/page_capture.png', full_page=True)
    print("Page captured")
    browser.close()
