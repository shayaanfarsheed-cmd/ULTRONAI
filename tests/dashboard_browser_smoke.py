from __future__ import annotations

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
VIEW_NAMES = (
    "overview",
    "learning",
    "data",
    "ask",
    "math",
    "activity",
    "control",
    "devices",
    "servers",
    "checkpoints",
    "settings",
)
VIEWPORTS = (
    (320, 800),
    (360, 800),
    (390, 844),
    (768, 1024),
    (1024, 768),
    (1366, 900),
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    handler = partial(SimpleHTTPRequestHandler, directory=str(ROOT))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    server_thread = Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}/dashboard/"

    page_errors: list[str] = []
    external_requests: list[str] = []
    console_errors: list[str] = []

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            context = browser.new_context(
                viewport={"width": 390, "height": 844},
                is_mobile=True,
                has_touch=True,
            )
            page = context.new_page()
            page.on("pageerror", lambda error: page_errors.append(str(error)))
            page.on(
                "console",
                lambda message: console_errors.append(message.text)
                if message.type == "error"
                else None,
            )

            def restrict_network(route) -> None:
                if route.request.url.startswith(base_url):
                    route.continue_()
                else:
                    external_requests.append(route.request.url)
                    route.abort()

            page.route("**/*", restrict_network)
            response = page.goto(base_url, wait_until="networkidle")
            require(response is not None and response.status == 200, "Dashboard did not return HTTP 200.")
            require(page.title().startswith("ULTRON"), "Dashboard title is missing.")
            require(page.locator("#view-overview").is_visible(), "Public overview did not load.")
            require(page.locator("#ownerSignInButton").is_visible(), "Owner sign-in control is not visible.")
            require(not page.locator("#ownerSignOutButton").is_visible(), "Guest Mode unexpectedly shows sign-out.")

            # Every navigation item must reveal its matching page and update aria-current.
            for view in VIEW_NAMES:
                button = page.locator(f'[data-view="{view}"]')
                button.click()
                section = page.locator(f"#view-{view}")
                require(section.is_visible(), f"Navigation failed to open {view}.")
                require(button.get_attribute("aria-current") == "page", f"{view} navigation lacks aria-current.")

            # RAM preference is local, persists after reload, and explicitly does not control hosted memory.
            page.locator('[data-view="settings"]').click()
            slider = page.locator("#ramLimitSlider")
            slider.evaluate(
                "(element) => { element.value = '7.5'; element.dispatchEvent(new Event('input', { bubbles: true })); }"
            )
            require(page.locator("#ramLimitValue").inner_text() == "7.5 GB", "RAM slider value did not update.")
            require(
                "Saved as 7.5 GB in this browser only" in page.locator("#ramLimitStatus").inner_text(),
                "RAM preference disclosure is missing.",
            )
            stored_ram = page.evaluate(
                "() => Object.entries(localStorage).find(([key]) => /ram/i.test(key))?.[1] || null"
            )
            require(stored_ram == "7.5", "RAM preference was not saved in browser storage.")
            page.reload(wait_until="networkidle")
            require(page.locator("#ramLimitSlider").input_value() == "7.5", "RAM preference did not persist.")

            # Owner sign-in remains optional for public browsing and the dialog can be dismissed.
            page.locator("#ownerSignInButton").click()
            require(
                page.locator("#ownerSignInDialog").evaluate("(dialog) => dialog.open"),
                "Owner sign-in dialog did not open.",
            )
            page.locator("#ownerCancelButton").click()
            require(
                not page.locator("#ownerSignInDialog").evaluate("(dialog) => dialog.open"),
                "Owner sign-in dialog did not close.",
            )

            # Compact header controls must remain usable touch targets.
            for selector in ("#ownerSignInButton", "#themeToggle"):
                height = page.locator(selector).evaluate("(element) => element.getBoundingClientRect().height")
                require(height >= 44, f"{selector} touch target is below 44px ({height}px).")

            before_theme = page.locator("body").get_attribute("data-theme")
            page.locator("#themeToggle").click()
            after_theme = page.locator("body").get_attribute("data-theme")
            require(before_theme != after_theme, "Theme toggle did not change the theme.")

            # Check key pages at phone, tablet and desktop widths for horizontal overflow.
            for view in ("overview", "devices", "settings", "control"):
                page.locator(f'[data-view="{view}"]').click()
                for width, height in VIEWPORTS:
                    page.set_viewport_size({"width": width, "height": height})
                    dimensions = page.evaluate(
                        "() => ({ viewport: window.innerWidth, document: document.documentElement.scrollWidth })"
                    )
                    require(
                        dimensions["document"] <= dimensions["viewport"] + 1,
                        f"{view} overflows horizontally at {width}px: {dimensions}",
                    )

            require(not page_errors, f"Browser page errors: {page_errors}")
            require(not console_errors, f"Browser console errors: {console_errors}")
            require(not external_requests, f"Guest Mode made unexpected external requests: {external_requests}")

            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=2)

    print("Dashboard browser smoke passed: public Guest Mode, all navigation pages, RAM persistence, optional owner dialog, theme toggle, 44px touch targets, six viewport widths, no JS/console errors, and no external requests.")


if __name__ == "__main__":
    main()
