"""MCP server for Tesseract OCR — read text from images.

Run: python -m servers.tesseract.server
"""

import json
import subprocess
import tempfile
from pathlib import Path

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("tesseract")


def _run_tesseract(image_path: str, lang: str = "eng", psm: int = 3,
                   extra_args: list[str] | None = None) -> str:
    """Run Tesseract on an image, return extracted text."""
    cmd = ["tesseract", image_path, "stdout", "-l", lang, "--psm", str(psm)]
    if extra_args:
        cmd.extend(extra_args)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"Tesseract error: {result.stderr}")
    return result.stdout.strip()


@mcp.tool()
def ocr_read(image_path: str, lang: str = "eng") -> str:
    """Read all text from an image.

    Args:
        image_path: Path to image file (PNG, JPG, TIFF, BMP)
        lang: Language code (eng, fra, deu, spa, etc.)

    Returns extracted text.
    """
    text = _run_tesseract(image_path, lang=lang)
    return json.dumps({"text": text, "source": image_path})


@mcp.tool()
def ocr_single_line(image_path: str, lang: str = "eng") -> str:
    """Read a single line of text from an image. Best for CAPTCHAs, labels, buttons.

    Uses PSM 7 (treat image as a single text line).
    """
    text = _run_tesseract(image_path, lang=lang, psm=7)
    return json.dumps({"text": text, "source": image_path})


@mcp.tool()
def ocr_single_word(image_path: str, lang: str = "eng") -> str:
    """Read a single word from an image. Best for short CAPTCHAs.

    Uses PSM 8 (treat image as a single word).
    """
    text = _run_tesseract(image_path, lang=lang, psm=8)
    return json.dumps({"text": text, "source": image_path})


@mcp.tool()
def ocr_digits(image_path: str) -> str:
    """Read only digits from an image. Best for numeric CAPTCHAs, prices, counts.

    Uses PSM 7 with digit whitelist.
    """
    text = _run_tesseract(image_path, psm=7,
                          extra_args=["-c", "tessedit_char_whitelist=0123456789"])
    return json.dumps({"text": text, "source": image_path})


@mcp.tool()
def ocr_to_tsv(image_path: str, lang: str = "eng") -> str:
    """Read text with position data — returns each word with its bounding box.

    Useful for mapping extracted text back to pixel coordinates.
    """
    cmd = ["tesseract", image_path, "stdout", "-l", lang, "--psm", "3", "tsv"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"Tesseract error: {result.stderr}")

    words = []
    for line in result.stdout.strip().split("\n")[1:]:  # skip header
        parts = line.split("\t")
        if len(parts) >= 12 and parts[11].strip():
            words.append({
                "text": parts[11],
                "x": int(parts[6]),
                "y": int(parts[7]),
                "width": int(parts[8]),
                "height": int(parts[9]),
                "confidence": float(parts[10]),
            })
    return json.dumps({"words": words, "count": len(words)})


@mcp.tool()
def ocr_languages() -> str:
    """List available Tesseract language packs."""
    result = subprocess.run(["tesseract", "--list-langs"],
                            capture_output=True, text=True, timeout=10)
    langs = [l.strip() for l in result.stdout.strip().split("\n")[1:] if l.strip()]
    return json.dumps({"languages": langs})


if __name__ == "__main__":
    mcp.run(transport="stdio")
