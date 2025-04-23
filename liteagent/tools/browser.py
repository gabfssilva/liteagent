
from liteagent import Tools, tool

class Browser(Tools):
    from pydoll.browser.base import Browser
    from pydoll.browser.page import Page

    browser: Browser | None
    page: Page | None

    def __init__(self):
        from pydoll.browser import Chrome

        self.browser = Chrome()
        self.page = None

    @tool(emoji='🧐')
    async def inspect_visible_elements(self) -> list[dict]:
        """
        List visible elements on the page with tag, text content, and attributes.
        """
        from pydoll.constants import By

        elements = await self.page.find_elements(By.CSS_SELECTOR, "*", raise_exc=False)
        result = []

        for element in elements:
            try:
                tag = element.get_attribute("tag_name")
                text = await element.text()
                attrs = await element.attributes()
                result.append({
                    "tag": tag,
                    "text": text.strip(),
                    "attributes": attrs,
                })
            except Exception:
                continue

        return result

    @tool(emoji='🏃🏽‍♀️‍➡️')
    async def go_to(self, url: str) -> str:
        """Navigate to a URL."""
        await self._ensure_active_page()
        await self.page.go_to(url)
        return f"Navigated to {url}"

    @tool
    async def click_by_text(self, tag: str, text: str):
        """
        Click the first element with a given tag and matching text.
        """
        from pydoll.constants import By

        elements = await self.page.find_elements(By.CSS_SELECTOR, tag)
        for el in elements:
            if text.lower() in (await el.text()).lower():
                await el.click()
                return f"Clicked element with tag '{tag}' and text '{text}'"
        return "Element not found"

    @tool
    async def type_into_input(self, name_or_id: str, value: str):
        """
        Type into input fields by name or id.
        """
        try:
            from pydoll.constants import By
            el = await self.page.find_element(By.CSS_SELECTOR, f'input[name="{name_or_id}"]', raise_exc=False)
            if not el:
                el = await self.page.find_element(By.CSS_SELECTOR, f'input[id="{name_or_id}"]')
            await el.type_keys(value)
            return f"Typed '{value}' into {name_or_id}"
        except Exception as e:
            return f"Failed to type: {str(e)}"

    @tool(emoji='🧩')
    async def expect_and_bypass_cloudflare(self, url: str) -> str:
        """Navigate to a Cloudflare-protected page and solve captcha."""
        await self._ensure_active_page()
        async with self.page.expect_and_bypass_cloudflare_captcha():
            await self.page.go_to(url)
        return f"Bypassed Cloudflare captcha at {url}"

    @tool(emoji='🧩')
    async def enable_auto_cloudflare_solver(self) -> str:
        """Enable automatic Cloudflare Turnstile captcha solving."""
        await self._ensure_active_page()
        await self.page.enable_auto_solve_cloudflare_captcha()
        return "Auto Cloudflare solver enabled."

    @tool(emoji='🖱️')
    async def find_and_click(self, selector: str) -> str:
        """Click an element matching a CSS selector."""
        from pydoll.constants import By

        await self._ensure_active_page()
        element = await self.page.find_element(By.CSS_SELECTOR, selector)
        await element.click()
        return f"Clicked element '{selector}'"

    # @tool(emoji='✏️')
    # async def type(self, selector: str, text: str) -> str:
    #     """Type text into an input field with human-like typing."""
    #     from pydoll.constants import By
    #
    #     await self._ensure_session()
    #     element = await self.page.find_element(By.CSS_SELECTOR, selector)
    #     await element.type_text(text)
    #     return f"Typed '{text}' into '{selector}'"

    @tool(emoji='✏️')
    async def type_keys(self, selector: str, text: str, interval: float = 0.1) -> str:
        """Type text into a field using human-like keystroke intervals."""
        from pydoll.constants import By

        await self._ensure_active_page()
        el = await self.page.find_element(By.CSS_SELECTOR, selector)
        await el.type_keys(text, interval=interval)
        return f"Typed into '{selector}' with delay={interval}"

    @tool(emoji='🔠')
    async def get_element_text(self, selector: str) -> str:
        """Get the text content of a given element."""
        from pydoll.constants import By

        await self._ensure_active_page()
        element = await self.page.find_element(By.CSS_SELECTOR, selector)
        text = await element.get_element_text()
        return text or "No text found."

    @tool(emoji='🛠️')
    async def eval_js(self, js: str) -> str:
        """Evaluate JavaScript on the page and return the result."""
        await self._ensure_active_page()
        result = await self.page.execute_script(js)
        return f"JavaScript result: {result}"

    @tool(emoji='📸')
    async def screenshot(self) -> str:
        """Take a full-page screenshot and return the file path."""
        await self._ensure_active_page()
        path = "/tmp/screenshot.png"
        await self.page.get_screenshot(path)
        return f"Screenshot saved to {path}"

    @tool(emoji='📄')
    async def export_pdf(self) -> str:
        """Export the current page to a PDF and return the file path."""
        await self._ensure_active_page()
        path = "/tmp/page.pdf"
        await self.page.print_to_pdf(path)
        return f"PDF saved to {path}"

    @tool(emoji='📄')
    async def get_page_as_markdown(self) -> str:
        """Return the page content as markdown."""
        from markdownify import markdownify
        return markdownify(await self.page.page_source)

    @tool
    async def inspect_page(self):
        """Inspect the current page and return visible elements with basic metadata."""
        await self._ensure_active_page()

        elements = await self.page.query_selector_all("*")  # You can limit this to 'button', 'input', etc.

        results = []
        for el in elements:
            try:
                tag = await el.evaluate("e => e.tagName")
                text = await el.evaluate("e => e.innerText")
                attrs = await el.evaluate("e => Array.from(e.attributes).reduce((acc, a) => { acc[a.name] = a.value; return acc; }, {})")
                results.append({
                    "tag": tag,
                    "text": text.strip(),
                    "attributes": attrs
                })
            except:
                continue

        return results

    @tool(emoji='❌')
    async def close_browser(self) -> str:
        """Close the browser and clear state."""
        if self.browser:
            await self.browser.stop()
            self.page = None

        return "Browser session closed."

    async def _ensure_active_page(self):
        if self.page is None:
            await self.browser.start(headless=False)
            self.page = await self.browser.get_page()

browser = Browser()
