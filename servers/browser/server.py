"""MCP server for browser automation — 14 tools for headless Chromium control.

Run: python -m servers.browser.server
"""

import json
import os
from mcp.server.fastmcp import FastMCP
from servers.browser.browser import BrowserManager, DEFAULT_PROFILE_DIR
from servers.browser.screenshot import capture_screenshot

mcp = FastMCP("browser")

# Lazy browser — started on first tool call
_browser: BrowserManager | None = None


async def _get_browser() -> BrowserManager:
    global _browser
    if _browser is None:
        profile = os.environ.get("BROWSER_PROFILE_DIR")
        engine = os.environ.get("BROWSER_ENGINE", "firefox")
        _browser = BrowserManager(
            headless=True,
            user_data_dir=profile,
            browser_type=engine,
        )
    await _browser.ensure_launched()
    return _browser


@mcp.tool()
async def browser_navigate(url: str) -> str:
    """Navigate to a URL. Returns page title, URL, and cleaned text content (truncated to 5000 chars)."""
    bm = await _get_browser()
    info = await bm.navigate(url)
    content = await bm.get_content(max_length=5000)
    return json.dumps({**info, "content": content})


@mcp.tool()
async def browser_read_page() -> str:
    """Read the full cleaned text content of the current page."""
    bm = await _get_browser()
    content = await bm.get_content(max_length=None)
    return json.dumps({
        "url": bm.current_url(),
        "title": await bm.title(),
        "content": content,
    })


@mcp.tool()
async def browser_find_elements(query: str) -> str:
    """Find interactive elements by CSS selector, XPath, or text pattern.

    Examples:
    - CSS: '#search-box', 'input[name=q]', '.result-item a'
    - XPath: '//button[contains(text(), "Submit")]'
    - Text: 'text=Accept & Continue'

    Returns list of {tag, text, selector, attributes} for each match.
    """
    bm = await _get_browser()
    elements = await bm.find_elements(query)
    return json.dumps({"count": len(elements), "elements": elements})


@mcp.tool()
async def browser_type(selector: str, text: str) -> str:
    """Type text into an element identified by selector."""
    bm = await _get_browser()
    result = await bm.type_text(selector, text)
    return json.dumps(result)


@mcp.tool()
async def browser_click(selector: str) -> str:
    """Click an element. Returns new page title, URL, and cleaned text content."""
    bm = await _get_browser()
    info = await bm.click(selector)
    content = await bm.get_content(max_length=5000)
    return json.dumps({**info, "content": content})


@mcp.tool()
async def browser_screenshot() -> str:
    """Capture a screenshot of the current viewport. Returns base64-encoded PNG."""
    bm = await _get_browser()
    b64 = await capture_screenshot(bm.page)
    return json.dumps({
        "url": bm.current_url(),
        "title": await bm.title(),
        "image_base64": b64,
    })


@mcp.tool()
async def browser_submit() -> str:
    """Press Enter to submit the current form. Returns new page state with content."""
    bm = await _get_browser()
    info = await bm.submit()
    content = await bm.get_content(max_length=5000)
    return json.dumps({**info, "content": content})


@mcp.tool()
async def browser_back() -> str:
    """Navigate back in browser history. Returns page state with content."""
    bm = await _get_browser()
    info = await bm.back()
    content = await bm.get_content(max_length=5000)
    return json.dumps({**info, "content": content})


@mcp.tool()
async def browser_click_at(x: int, y: int) -> str:
    """Click at pixel coordinates. Use with gimp_annotate to identify targets visually."""
    bm = await _get_browser()
    await bm.page.mouse.click(x, y)
    await bm.page.wait_for_load_state("domcontentloaded")
    content = await bm.get_content(max_length=5000)
    return json.dumps({"url": bm.current_url(), "title": await bm.title(), "clicked": [x, y], "content": content})


@mcp.tool()
async def browser_hover(x: int, y: int) -> str:
    """Hover at pixel coordinates. Reveals tooltips, dropdowns, hover states."""
    bm = await _get_browser()
    await bm.page.mouse.move(x, y)
    await bm.page.wait_for_timeout(300)
    return json.dumps({"url": bm.current_url(), "hovered": [x, y]})


@mcp.tool()
async def browser_drag(from_x: int, from_y: int, to_x: int, to_y: int) -> str:
    """Drag from one point to another. For drag-and-drop interfaces."""
    bm = await _get_browser()
    await bm.page.mouse.move(from_x, from_y)
    await bm.page.mouse.down()
    await bm.page.mouse.move(to_x, to_y, steps=10)
    await bm.page.mouse.up()
    return json.dumps({"dragged": {"from": [from_x, from_y], "to": [to_x, to_y]}})


@mcp.tool()
async def browser_eval(js: str) -> str:
    """Execute JavaScript on the current page. Returns the result.

    Use for reading computed styles, modifying DOM, injecting CSS, etc.
    Examples:
        - "getComputedStyle(document.querySelector('#btn')).marginTop"
        - "document.querySelector('h1').style.color = 'red'"
    """
    bm = await _get_browser()
    result = await bm.page.evaluate(js)
    return json.dumps({"result": result})


@mcp.tool()
async def browser_set_content(html: str) -> str:
    """Load raw HTML directly into the browser. No server needed.

    Use for previewing generated HTML/CSS.
    """
    bm = await _get_browser()
    await bm.page.set_content(html, wait_until="domcontentloaded")
    return json.dumps({"url": bm.current_url(), "title": await bm.title()})


@mcp.tool()
async def browser_save_screenshot(path: str) -> str:
    """Save a screenshot to disk as PNG. Use with gimp_annotate for visual analysis."""
    bm = await _get_browser()
    png = await bm.screenshot()
    with open(path, "wb") as f:
        f.write(png)
    return json.dumps({"path": path, "size_bytes": len(png)})


@mcp.tool()
async def browser_get_boxes() -> str:
    """Get bounding boxes of all interactive elements on the page.

    Returns JSON array of {index, tag, text, x, y, width, height} for use with gimp_annotate.
    """
    bm = await _get_browser()
    boxes = await bm.page.evaluate('''() => {
        const els = document.querySelectorAll("a, button, input, select, textarea, h1, h2, h3, img, [role='button'], [onclick]");
        return Array.from(els).map((el, i) => {
            const rect = el.getBoundingClientRect();
            return {
                index: i,
                tag: el.tagName.toLowerCase(),
                text: (el.textContent || el.value || el.alt || "").trim().slice(0, 60),
                x: Math.round(rect.x),
                y: Math.round(rect.y),
                width: Math.round(rect.width),
                height: Math.round(rect.height),
            };
        }).filter(e => e.width > 0 && e.height > 0);
    }''')
    return json.dumps({"count": len(boxes), "elements": boxes})


if __name__ == "__main__":
    mcp.run(transport="stdio")
