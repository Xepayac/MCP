"""DOM parsing — HTML to clean text, element finding via Playwright locators."""

import re
from playwright.async_api import Page


def extract_text(html: str) -> str:
    """Extract clean text from HTML, stripping scripts, styles, and tags."""
    # Remove script and style blocks
    text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    # Remove HTML comments
    text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
    # Remove tags
    text = re.sub(r'<[^>]+>', ' ', text)
    # Decode common entities
    text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    text = text.replace('&quot;', '"').replace('&#39;', "'").replace('&nbsp;', ' ')
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


async def find_elements(page: Page, query: str) -> list[dict]:
    """Find elements by CSS selector, XPath, or text content pattern.

    Accepts:
    - CSS selectors: '#search-box', 'input[name=q]', '.result-item a'
    - XPath: '//button[contains(text(), "Submit")]'
    - Text patterns: 'text=Accept' (Playwright text selector)

    Returns list of {tag, text, selector, attributes} for each match.
    """
    try:
        locator = page.locator(query)
        count = await locator.count()
    except Exception:
        return []

    results = []
    for i in range(min(count, 50)):  # Cap at 50 to avoid huge responses
        try:
            el = locator.nth(i)
            tag = await el.evaluate("el => el.tagName.toLowerCase()")
            inner = await el.inner_text()
            text = inner[:200] if inner else ""
            el_id = await el.get_attribute("id")
            el_class = await el.get_attribute("class")
            el_name = await el.get_attribute("name")
            el_href = await el.get_attribute("href")
            el_type = await el.get_attribute("type")

            selector = query
            if el_id:
                selector = f"#{el_id}"

            results.append({
                "tag": tag,
                "text": text.strip(),
                "selector": selector,
                "attributes": {
                    k: v for k, v in [
                        ("id", el_id), ("class", el_class),
                        ("name", el_name), ("href", el_href),
                        ("type", el_type),
                    ] if v is not None
                }
            })
        except Exception:
            continue

    return results
