"""Screenshot capture and encoding for MCP responses."""

import base64


async def capture_screenshot(page) -> str:
    """Capture viewport screenshot, return as base64-encoded PNG."""
    png_bytes = await page.screenshot(full_page=False)
    return base64.b64encode(png_bytes).decode("ascii")


def screenshot_to_data_uri(b64_png: str) -> str:
    """Convert base64 PNG to data URI for embedding."""
    return f"data:image/png;base64,{b64_png}"
