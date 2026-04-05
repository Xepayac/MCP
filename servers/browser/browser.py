"""Playwright browser manager — launch, navigate, manage session.

Async API for use within MCP server's event loop.
"""

import json
import os
import re
import time
from pathlib import Path
from urllib.parse import urlparse
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

DEFAULT_PROFILE_DIR = Path.home() / ".trugs-web" / "browser-profile"
DEFAULT_COOKIE_FILE = Path.home() / ".trugs-web" / "google-cookies.json"


class BrowserManager:
    """Manages a headless browser session (Firefox default, Chromium optional)."""

    def __init__(self, headless=True, viewport_width=1280, viewport_height=720,
                 user_data_dir: str | Path | None = None,
                 cookie_file: str | Path | None = None,
                 browser_type: str = "firefox",
                 min_request_interval: float = 2.0):
        self._headless = headless
        self._viewport = {"width": viewport_width, "height": viewport_height}
        self._user_data_dir = Path(user_data_dir) if user_data_dir else None
        self._cookie_file = Path(cookie_file) if cookie_file else DEFAULT_COOKIE_FILE
        self._browser_type = browser_type
        self._min_interval = min_request_interval
        self._last_navigate: dict[str, float] = {}  # domain -> timestamp
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    @property
    def page(self) -> Page:
        """Get the current page. Must call ensure_launched() first."""
        if self._page is None:
            raise RuntimeError("Browser not launched. Call await ensure_launched() first.")
        return self._page

    async def ensure_launched(self):
        """Launch browser if not already running."""
        if self._page is None:
            await self._launch()

    async def _launch(self):
        """Launch browser, create context and page."""
        self._playwright = await async_playwright().start()
        engine = getattr(self._playwright, self._browser_type)

        if self._user_data_dir:
            self._user_data_dir.mkdir(parents=True, exist_ok=True)
            self._context = await engine.launch_persistent_context(
                user_data_dir=str(self._user_data_dir),
                headless=self._headless,
                viewport=self._viewport,
            )
            self._page = self._context.pages[0] if self._context.pages else await self._context.new_page()
        else:
            self._browser = await engine.launch(headless=self._headless)
            self._context = await self._browser.new_context(viewport=self._viewport)
            self._page = await self._context.new_page()

        self._context.on("page", self._on_new_page)
        await self._load_cookies()

    async def _load_cookies(self):
        """Load cookies from file if it exists."""
        if self._cookie_file and self._cookie_file.exists():
            cookies = json.loads(self._cookie_file.read_text())
            if cookies:
                await self._context.add_cookies(cookies)

    def _on_new_page(self, page: Page):
        """Handle new tab/popup."""
        pass

    def _rate_limit(self, url: str):
        """Wait if needed to respect per-domain rate limit."""
        domain = urlparse(url).netloc
        if not domain or domain.startswith("localhost") or domain.startswith("127."):
            return 0
        now = time.monotonic()
        last = self._last_navigate.get(domain, 0)
        wait = self._min_interval - (now - last)
        self._last_navigate[domain] = max(now, last + self._min_interval)
        return max(0, wait)

    async def navigate(self, url: str, wait_until: str = "domcontentloaded") -> dict:
        """Navigate to URL, return page info."""
        import asyncio
        wait = self._rate_limit(url)
        if wait > 0:
            await asyncio.sleep(wait)
        await self.page.goto(url, wait_until=wait_until)
        await self._check_captcha()
        return self._page_info()

    async def back(self) -> dict:
        """Go back in history."""
        await self.page.go_back(wait_until="domcontentloaded")
        return self._page_info()

    def current_url(self) -> str:
        return self.page.url

    async def title(self) -> str:
        return await self.page.title()

    async def click(self, selector: str) -> dict:
        """Click an element, return new page state."""
        await self.page.click(selector)
        await self.page.wait_for_load_state("domcontentloaded")
        return self._page_info()

    async def type_text(self, selector: str, text: str) -> dict:
        """Type text into an element."""
        await self.page.fill(selector, text)
        return {"typed": text, "selector": selector, "url": self.page.url}

    async def submit(self) -> dict:
        """Press Enter to submit current form."""
        await self.page.keyboard.press("Enter")
        await self.page.wait_for_load_state("domcontentloaded")
        await self.page.wait_for_timeout(500)
        for _ in range(5):
            if await self._check_captcha():
                break
            await self.page.wait_for_timeout(300)
        return self._page_info()

    async def screenshot(self) -> bytes:
        """Capture viewport screenshot as PNG bytes."""
        return await self.page.screenshot(full_page=False)

    async def get_content(self, max_length: int = 5000) -> str:
        """Get cleaned text content of current page."""
        from servers.browser.dom_parser import extract_text
        html = await self.page.content()
        text = extract_text(html)
        if max_length and len(text) > max_length:
            text = text[:max_length] + "\n...(truncated)"
        return text

    async def find_elements(self, query: str) -> list[dict]:
        """Find interactive elements by CSS selector, XPath, or text pattern."""
        from servers.browser.dom_parser import find_elements
        return await find_elements(self.page, query)

    async def wait_for_content(self, timeout: int = 5000):
        """Wait for JS-rendered content to appear."""
        await self.page.wait_for_timeout(timeout)

    def get_pages(self) -> list[str]:
        """List all open page URLs."""
        return [p.url for p in self._context.pages] if self._context else []

    def switch_to_page(self, index: int) -> dict:
        """Switch to a specific page by index."""
        pages = self._context.pages
        if 0 <= index < len(pages):
            self._page = pages[index]
            return self._page_info()
        raise IndexError(f"Page index {index} out of range (0-{len(pages)-1})")

    async def close(self):
        """Shut down browser cleanly."""
        if self._context and self._user_data_dir:
            await self._context.close()
        elif self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._browser = None
        self._context = None
        self._page = None
        self._playwright = None

    async def _check_captcha(self) -> bool:
        """Detect and solve a math CAPTCHA if present."""
        try:
            question_el = self.page.locator("#captcha-question")
            if await question_el.count() == 0:
                return False

            text = await question_el.inner_text()
            match = re.search(r"What is (\d+)\s*([+\-*])\s*(\d+)", text)
            if not match:
                return False

            a, op, b = int(match.group(1)), match.group(2), int(match.group(3))
            if op == "+":
                answer = a + b
            elif op == "-":
                answer = a - b
            else:
                answer = a * b

            await self.page.fill("#captcha-input", str(answer))
            await self.page.click("#captcha-submit")
            await self.page.wait_for_load_state("domcontentloaded")
            await self.page.wait_for_timeout(500)
            return True
        except Exception:
            return False

    def _page_info(self) -> dict:
        """Return current page state (sync-safe — url only, title via await)."""
        return {
            "url": self.page.url,
        }
