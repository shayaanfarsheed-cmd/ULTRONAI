from __future__ import annotations

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import os
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
    origin = f"http://127.0.0.1:{server.server_port}"
    base_url = origin + "/dashboard/"

    page_errors: list[str] = []
    external_requests: list[str] = []
    console_errors: list[str] = []

    try:
        with sync_playwright() as playwright:
            browser_name = os.environ.get("ULTRON_BROWSER", "chromium").lower()
            if browser_name not in {"chromium", "webkit"}:
                raise ValueError(f"Unsupported browser: {browser_name}")
            browser_type = getattr(playwright, browser_name)
            browser = browser_type.launch()
            context = browser.new_context(
                viewport={"width": 390, "height": 844},
                is_mobile=(browser_name == "chromium"),
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
                if route.request.url == origin + "/favicon.ico":
                    route.fulfill(status=204, body="")
                elif route.request.url.startswith(origin + "/"):
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

            # The conversational shell must solve, verify, clarify, and reset in a real browser.
            page.locator('[data-view="math"]').click()
            page.locator("#mathConversationInput").fill("What is 12 + 5?")
            page.locator("#mathConversationSend").click()
            require(page.locator(".conversation-answer").inner_text() == "17", "Conversational arithmetic returned the wrong answer.")
            require(
                "INDEPENDENT CHECK PASSED" in page.locator(".conversation-verification").inner_text(),
                "Conversational arithmetic did not show independent verification.",
            )
            require(
                "integer_arithmetic" in page.locator(".conversation-reasoning-summary").inner_text(),
                "Conversation did not display its structured problem representation.",
            )
            page.locator("#mathConversationInput").fill("Can you help me with this homework?")
            page.locator("#mathConversationSend").click()
            require(
                "Clarification needed" in page.locator("#mathConversationStatus").inner_text(),
                "Ambiguous conversation input did not request clarification.",
            )
            page.locator("#mathConversationReset").click()
            require(
                "Conversation reset" in page.locator("#mathConversationTranscript").inner_text(),
                "Conversation reset did not clear the transcript.",
            )

            # Stage 3 tutor: hints, independent checking, session mastery and axiom research.
            require(page.locator("#tutorQuestion").is_visible(), "Guided practice panel did not load.")
            tutor_runtime = page.evaluate("""() => ({ready: document.readyState, agent: !!window.ULTRON_MATH_AGENT, tutor: !!window.ULTRON_MATH_TUTOR, reasoning: !!window.ULTRON_REASONING, panel: !!document.getElementById("mathTutorPanel")})""")
            require("foundation difficulty" in page.locator("#tutorTopic").inner_text().lower(), "Tutor difficulty disclosure is missing: topic=" + page.locator("#tutorTopic").inner_text() + "; feedback=" + page.locator("#tutorFeedback").inner_text() + "; globals=" + str(tutor_runtime) + "; pageErrors=" + str(page_errors) + "; consoleErrors=" + str(console_errors))
            require("Related axioms" in page.locator("#tutorAxiomContext").inner_text(), "Tutor did not show topic-scoped axiom context.")
            page.locator("#tutorHintButton").click()
            require("HINT 1" in page.locator("#tutorHint").inner_text(), "Progressive tutor hint did not appear.")
            question = page.locator("#tutorQuestion").inner_text()
            topic_label = page.locator("#tutorTopic").inner_text()
            topic = page.evaluate("(label) => Object.entries(ULTRON_MATH_AGENT.TOPICS).find(([, value]) => label.startsWith(value.label))?.[0]", topic_label)
            expected = page.evaluate("({topic, question}) => ULTRON_MATH_AGENT.solve(topic, question).answer", {"topic": topic, "question": question})
            page.locator("#tutorAnswer").fill(expected)
            page.locator("#tutorAnswerForm button[type=submit]").click()
            require("Correct" in page.locator("#tutorFeedback").inner_text(), "Tutor did not accept independently verified correct answer.")
            require("100%" in page.locator("#tutorMastery").inner_text(), "Tutor mastery did not update after a correct attempt.")
            page.locator("#tutorNextButton").click()
            page.locator("#tutorAnswer").fill("not-the-answer")
            page.locator("#tutorWorking").fill("I combined the numerators and denominators.")
            page.locator("#tutorAnswerForm button[type=submit]").click()
            require("does not yet classify" in page.locator("#tutorFeedback").inner_text(), "Tutor invented a misconception diagnosis from unparsed working.")
            page.locator("#tutorResetButton").click()
            require("Session turn 0" in page.locator("#tutorSessionStatus").inner_text(), "Tutor reset did not clear session mastery.")

            page.locator("#axiomSearch").fill("Kolmogorov")
            require("3 /" in page.locator("#axiomCount").inner_text(), "Axiom bank search did not find the three probability axioms.")
            page.locator("#axiomResults").get_by_role("button", name="PROB-03").click()
            require("pairwise-disjoint" in page.locator("#axiomDetail").inner_text(), "Axiom detail omitted the disjointness condition.")
            require("Research source" in page.locator("#axiomDetail").inner_text(), "Axiom research references are missing.")
            page.locator("#axiomSearch").fill("not-a-real-axiom")
            require("No matching axioms" in page.locator("#axiomResults").inner_text(), "Axiom bank empty search state is missing.")

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
            for view in ("overview", "devices", "math", "settings", "control"):
                page.locator(f'[data-view="{view}"]').click()
                for width, height in VIEWPORTS:
                    page.set_viewport_size({"width": width, "height": height})
                    dimensions = page.evaluate(
                        """() => ({
                            viewport: window.innerWidth,
                            document: document.documentElement.scrollWidth,
                            offenders: [...document.querySelectorAll("body *")].map((element) => {
                                const rect = element.getBoundingClientRect();
                                return {
                                    tag: element.tagName,
                                    id: element.id,
                                    className: typeof element.className === "string" ? element.className : "",
                                    left: Math.round(rect.left),
                                    right: Math.round(rect.right),
                                    width: Math.round(rect.width),
                                    scrollWidth: element.scrollWidth,
                                };
                            }).filter((item) => item.right > window.innerWidth + 1 || item.left < -1).slice(0, 12),
                        })"""
                    )
                    require(
                        dimensions["document"] <= dimensions["viewport"] + 1,
                        f"{view} overflows horizontally at {width}px: {dimensions}",
                    )
                    if view == "settings":
                        ram_geometry = page.evaluate(
                            """() => {
                                const panel = document.querySelector(".ram-panel");
                                const slider = document.querySelector("#ramLimitSlider");
                                if (!panel || !slider) return null;
                                const panelRect = panel.getBoundingClientRect();
                                const sliderRect = slider.getBoundingClientRect();
                                return {
                                    viewport: window.innerWidth,
                                    panelLeft: Math.round(panelRect.left),
                                    panelRight: Math.round(panelRect.right),
                                    sliderLeft: Math.round(sliderRect.left),
                                    sliderRight: Math.round(sliderRect.right),
                                };
                            }"""
                        )
                        require(
                            ram_geometry is not None
                            and ram_geometry["panelLeft"] >= -1
                            and ram_geometry["panelRight"] <= width + 1
                            and ram_geometry["sliderLeft"] >= -1
                            and ram_geometry["sliderRight"] <= width + 1,
                            f"Settings RAM controls exceed the {width}px viewport: {ram_geometry}",
                        )

            require(not page_errors, f"Browser page errors: {page_errors}")
            require(not console_errors, f"Browser console errors: {console_errors}")
            require(not external_requests, f"Guest Mode made unexpected external requests: {external_requests}")

            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=2)

    print("Dashboard browser smoke passed: public Guest Mode, all navigation pages, RAM persistence, optional owner dialog, theme toggle, 44px touch targets, six viewport widths, RAM panel/slider fit checks, no JS/console errors, and no external requests.")


if __name__ == "__main__":
    main()
