import asyncio
import random
from typing import Optional, Literal

from playwright.async_api import async_playwright, Page, Browser as PWBrowser

from liteagent import Tools, tool


class Browser(Tools):
    def __init__(
        self,
        browser_type: Literal['chromium', 'firefox', 'webkit'] = 'chromium',
        headless: bool = True,
    ):
        self.playwright = None
        self.browser: Optional[PWBrowser] = None
        self.context = None
        self.page: Optional[Page] = None
        self.browser_type = browser_type
        self.headless = headless

    async def _ensure_active_page(self):
        """Ensures an active browser page exists or creates a new one."""
        if self.page is None:
            self.playwright = await async_playwright().start()

            match self.browser_type:
                case 'chromium':
                    self.browser = await self.playwright.chromium.launch(headless=self.headless)
                case 'firefox':
                    self.browser = await self.playwright.firefox.launch(headless=self.headless)
                case 'webkit':
                    self.browser = await self.playwright.webkit.launch(headless=self.headless)

            self.context = await self.browser.new_context()
            self.page = await self.context.new_page()

    @tool(emoji='🏃🏽‍♀️‍➡️')
    async def go_to(self, url: str) -> str:
        """Navigates the browser to a specified URL."""
        await self._ensure_active_page()
        await self.page.goto(url)
        return f"Navigated to {url}"

    @tool(emoji='🧐')
    async def inspect_visible_elements(self) -> list[dict]:
        """Returns all visible elements on the current page with their properties."""
        await self._ensure_active_page()
        elements = await self.page.query_selector_all("*")
        result = []

        for el in elements:
            try:
                visible = await el.is_visible()
                if not visible:
                    continue
                tag = await el.evaluate("e => e.tagName")
                text = await el.inner_text()
                attrs = await el.evaluate(
                    "e => Array.from(e.attributes).reduce((acc, a) => { acc[a.name] = a.value; return acc; }, {})"
                )
                result.append({
                    "tag": tag,
                    "text": text.strip(),
                    "attributes": attrs,
                })
            except Exception:
                continue

        return result

    @tool(emoji='🖱️')
    async def find_and_click(self, selector: str) -> str:
        """Finds an element by selector and clicks on it."""
        await self._ensure_active_page()
        el = await self.page.query_selector(selector)
        if el:
            await el.click()
            return f"Clicked element '{selector}'"
        return f"Element '{selector}' not found"

    @tool(emoji='✏️')
    async def type_keys(
        self,
        selector: str,
        text: str,
        speed: Literal['clearly_a_robot', 'fast', 'normal', 'slow']
    ) -> str:
        """Type text into a field using human-like keystroke intervals."""

        if speed == 'fast':
            delay = random.uniform(0.01, 0.03)
        elif speed == 'normal':
            delay = random.uniform(0.05, 0.2)
        elif speed == 'slow':
            delay = random.uniform(0.3, 1.0)
        else:
            delay = 0.0

        await self._ensure_active_page()
        el = await self.page.query_selector(selector)
        if el:
            for char in text:
                await el.type(char)
                await asyncio.sleep(delay)
            return f"Typed into '{selector}'"
        return f"Element '{selector}' not found"

    @tool(emoji='🔠')
    async def get_element_text(self, selector: str) -> str:
        """Get the text content of a given element."""

        await self._ensure_active_page()
        el = await self.page.query_selector(selector)
        if el:
            text = await el.inner_text()
            return text or "No text found."
        return f"Element '{selector}' not found"

    @tool(emoji='🛠️')
    async def eval_js(self, js: str) -> str:
        """Evaluates JavaScript code on the current page."""
        await self._ensure_active_page()
        result = await self.page.evaluate(js)
        return f"JavaScript result: {result}"

    @tool(emoji='📸')
    async def screenshot(self) -> str:
        """Takes a screenshot of the current page."""
        await self._ensure_active_page()
        path = "/tmp/screenshot.png"
        await self.page.screenshot(path=path, full_page=True)
        return f"Screenshot saved to {path}"

    @tool(emoji='📄')
    async def export_pdf(self) -> str:
        """Exports the current page as a PDF document."""
        await self._ensure_active_page()
        path = "/tmp/page.pdf"
        await self.page.pdf(path=path)
        return f"PDF saved to {path}"

    @tool(emoji='📄')
    async def get_page_as_markdown(self) -> str:
        """Converts the current page content to Markdown format."""
        from markdownify import markdownify
        await self._ensure_active_page()
        html = await self.page.content()
        return await asyncio.to_thread(markdownify, html)

    @tool(emoji='🔙')
    async def go_back(self) -> str:
        """Navigates to the previous page in browser history."""
        await self._ensure_active_page()
        await self.page.go_back()
        return "Went back to previous page"

    @tool(emoji='🔜')
    async def go_forward(self) -> str:
        """Navigates forward in browser history."""
        await self._ensure_active_page()
        await self.page.go_forward()
        return "Went forward to next page"

    @tool(emoji='🗂️')
    async def new_tab(self) -> str:
        """Opens a new browser tab and sets it as the active page."""
        await self._ensure_active_page()
        self.page = await self.context.new_page()
        return "Opened a new tab"

    @tool(emoji='🔀')
    async def switch_to_tab(self, index: int) -> str:
        """Switches to a different tab by index."""
        await self._ensure_active_page()
        pages = self.context.pages
        if 0 <= index < len(pages):
            self.page = pages[index]
            return f"Switched to tab {index}"
        return "Tab index out of range"

    @tool(emoji='🖱️')
    async def hover(self, selector: str) -> str:
        """Hovers over an element."""
        await self._ensure_active_page()
        el = await self.page.query_selector(selector)
        if el:
            await el.hover()
            return f"Hovered over '{selector}'"
        return f"Element '{selector}' not found"

    @tool(emoji='🔀')
    async def get_tabs(self):
        await self._ensure_active_page()
        pages = self.context.pages

        result = []

        for index, page in enumerate(pages):
            result.append({
                "index": index,
                "title": await page.title(),
                "url": page.url,
            })

        return result

    @tool(emoji='📦')
    async def drag_and_drop(self, source_selector: str, target_selector: str) -> str:
        """Drags an element to a target."""
        await self._ensure_active_page()
        await self.page.drag_and_drop(source_selector, target_selector)
        return f"Dragged from '{source_selector}' to '{target_selector}'"

    @tool(emoji='📋')
    async def paste_text(self, selector: str, text: str) -> str:
        """Pastes text into an input field using clipboard simulation."""
        await self._ensure_active_page()
        await self.page.set_content(f"<input id='pasteTarget'>")
        await self.page.evaluate(f"navigator.clipboard.writeText({repr(text)})")
        await self.page.click(selector)
        await self.page.keyboard.press("Control+V")
        return f"Pasted text into '{selector}'"

    @tool(emoji='✅')
    async def assert_selector_exists(self, selector: str) -> str:
        """Asserts that a selector exists on the page."""
        await self._ensure_active_page()
        exists = await self.page.query_selector(selector) is not None
        return "Selector found" if exists else "Selector not found"

    @tool(emoji='⚙️')
    async def get_performance_metrics(self) -> dict:
        """Returns performance timing metrics."""
        await self._ensure_active_page()
        return await self.page.evaluate("() => JSON.parse(JSON.stringify(window.performance.timing))")

    @tool(emoji='🔁')
    async def reload_page(self) -> str:
        """Reloads the current page."""
        await self._ensure_active_page()
        await self.page.reload()
        return "Page reloaded"

    @tool(emoji='📄')
    async def inspect_page(self) -> list[dict]:
        """Returns all elements on the page with their properties."""
        await self._ensure_active_page()
        elements = await self.page.query_selector_all("*")
        results = []
        for el in elements:
            try:
                tag = await el.evaluate("e => e.tagName")
                text = await el.inner_text()
                attrs = await el.evaluate(
                    "e => Array.from(e.attributes).reduce((acc, a) => { acc[a.name] = a.value; return acc; }, {})"
                )
                results.append({
                    "tag": tag,
                    "text": text.strip(),
                    "attributes": attrs
                })
            except Exception:
                continue
        return results

    @tool(emoji='🔤')
    async def click_by_text(self, tag: str, text: str):
        """Finds and clicks an element by its tag and contained text."""
        await self._ensure_active_page()
        elements = await self.page.query_selector_all(tag)
        for el in elements:
            try:
                if text.lower() in (await el.inner_text()).lower():
                    await el.click()
                    return f"Clicked element with tag '{tag}' and text '{text}'"
            except Exception:
                continue
        return "Element not found"

    @tool(emoji='⌨️')
    async def type_into_input(self, name_or_id: str, value: str):
        """Types text into an input field identified by name or id."""
        await self._ensure_active_page()
        selectors = [f'input[name="{name_or_id}"]', f'input[id="{name_or_id}"]']
        for selector in selectors:
            el = await self.page.query_selector(selector)
            if el:
                await el.fill(value)
                return f"Typed '{value}' into {name_or_id}"
        return f"Input field '{name_or_id}' not found"

    @tool(emoji='❌')
    async def close_browser(self) -> str:
        """Closes the browser and cleans up resources."""
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
        self.page = self.context = None
        return "Browser session closed"

    @tool(emoji='📤')
    async def submit_form(self, selector: str = "form") -> str:
        """Submits a form on the current page."""
        await self._ensure_active_page()
        form = await self.page.query_selector(selector)
        if form:
            await form.evaluate("f => f.submit()")
            return "Form submitted"
        return "Form not found"

    @tool(emoji='🖱️')
    async def scroll_to_bottom(self) -> str:
        """Scrolls to the bottom of the current page."""
        await self._ensure_active_page()
        await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        return "Scrolled to bottom of page"

    @tool(emoji='🍪')
    async def get_cookies(self) -> list[dict]:
        """Returns all cookies from the current browser context."""
        await self._ensure_active_page()
        return await self.context.cookies()

    @tool(emoji='⏳')
    async def wait_for(
        self,
        condition_type: Literal[
            "selector", "not_selector", "url_contains", "title_contains",
            "network_idle", "timeout", "js_condition"
        ],
        condition: str,
        timeout_ms: int = 5000,
    ) -> str:
        """
        Waits for a given condition:
        - 'selector': Wait for a CSS selector to appear
        - 'not_selector': Wait for a CSS selector to disappear
        - 'url_contains': Wait until URL contains a substring
        - 'title_contains': Wait until page title contains a substring
        - 'network_idle': Wait until network is idle
        - 'timeout': Wait a fixed amount of time (value = seconds)
        - 'js_condition': Wait for JS expression to return true
        """
        await self._ensure_active_page()

        try:
            if condition_type == "selector":
                await self.page.wait_for_selector(condition, timeout=timeout_ms)
                return f"Selector '{condition}' appeared."
            elif condition_type == "not_selector":
                await self.page.wait_for_selector(condition, timeout=timeout_ms, state="detached")
                return f"Selector '{condition}' disappeared."
            elif condition_type == "url_contains":
                await self.page.wait_for_function(
                    f"() => window.location.href.includes({repr(condition)})",
                    timeout=timeout_ms
                )
                return f"URL contains '{condition}'."
            elif condition_type == "title_contains":
                await self.page.wait_for_function(
                    f"() => document.title.includes({repr(condition)})",
                    timeout=timeout_ms
                )
                return f"Title contains '{condition}'."
            elif condition_type == "network_idle":
                await self.page.wait_for_load_state("networkidle", timeout=timeout_ms)
                return f"Network is idle."
            elif condition_type == "timeout":
                await asyncio.sleep(float(condition))
                return f"Slept for {condition} seconds."
            elif condition_type == "js_condition":
                await self.page.wait_for_function(condition, timeout=timeout_ms)
                return f"JS condition passed."
            else:
                return f"Invalid condition: {condition_type}"
        except Exception as e:
            return f"Timeout or error: {str(e)}"

    @tool(emoji='💾')
    async def get_local_storage(self) -> dict:
        """Retrieves all local storage items from the current page."""
        await self._ensure_active_page()
        return await self.page.evaluate(
            "() => { let s = {}; for (let i=0; i<localStorage.length; i++) { let k = localStorage.key(i); s[k] = localStorage.getItem(k); } return s; }")

    @tool(emoji='📌')
    async def get_metadata(self) -> dict:
        """Returns basic metadata about the current page."""
        await self._ensure_active_page()
        return {
            "title": await self.page.title(),
            "url": self.page.url,
        }


browser = Browser()
