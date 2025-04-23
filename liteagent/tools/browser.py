import asyncio
import random
from typing import Optional, Literal

from playwright.async_api import async_playwright, Page, Browser as PWBrowser

from liteagent import Tools, tool


class Browser(Tools):
    def __init__(self):
        self.playwright = None
        self.browser: Optional[PWBrowser] = None
        self.context = None
        self.page: Optional[Page] = None

    async def _ensure_active_page(self):
        if self.page is None:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=False)
            self.context = await self.browser.new_context()
            self.page = await self.context.new_page()

    @tool(emoji='🏃🏽‍♀️‍➡️')
    async def go_to(self, url: str) -> str:
        await self._ensure_active_page()
        await self.page.goto(url)
        return f"Navigated to {url}"

    @tool(emoji='🧐')
    async def inspect_visible_elements(self) -> list[dict]:
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
        await self._ensure_active_page()
        el = await self.page.query_selector(selector)
        if el:
            await el.click()
            return f"Clicked element '{selector}'"
        return f"Element '{selector}' not found"

    @tool(emoji='✏️')
    async def type_keys(self, selector: str, text: str,
                        speed: Literal['clearly_a_robot', 'fast', 'normal', 'slow']) -> str:
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
        await self._ensure_active_page()
        result = await self.page.evaluate(js)
        return f"JavaScript result: {result}"

    @tool(emoji='📸')
    async def screenshot(self) -> str:
        await self._ensure_active_page()
        path = "/tmp/screenshot.png"
        await self.page.screenshot(path=path, full_page=True)
        return f"Screenshot saved to {path}"

    @tool(emoji='📄')
    async def export_pdf(self) -> str:
        await self._ensure_active_page()
        path = "/tmp/page.pdf"
        await self.page.pdf(path=path)
        return f"PDF saved to {path}"

    @tool(emoji='📄')
    async def get_page_as_markdown(self) -> str:
        from markdownify import markdownify
        await self._ensure_active_page()
        html = await self.page.content()
        return await asyncio.to_thread(markdownify, html)

    @tool(emoji='📄')
    async def inspect_page(self) -> list[dict]:
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
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
        self.page = self.context = None
        return "Browser session closed"


browser = Browser()
