"""MCP server for GIMP image analysis — visual tools for screenshots and images.

Works alongside the browser MCP. Browser captures, GIMP analyzes.

Run: python -m servers.gimp.server
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from servers.gimp.visual import annotate_screenshot, visual_diff, measure_spacing, extract_colors

mcp = FastMCP("gimp")

# Shared state — element boxes from last annotation
_last_elements: list[dict] = []


def _run_gimp_script(script: str, timeout: int = 30) -> str:
    """Run a Script-Fu script in GIMP headless mode."""
    result = subprocess.run(
        ["gimp", "-i", "-b", script, "-b", "(gimp-quit 0)"],
        capture_output=True, text=True, timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(f"GIMP error: {result.stderr}")
    return result.stdout


@mcp.tool()
def gimp_annotate(screenshot_path: str, elements_json: str) -> str:
    """Annotate a screenshot with numbered bounding boxes on interactive elements.

    Args:
        screenshot_path: Path to PNG screenshot (from browser_screenshot saved to disk)
        elements_json: JSON array of elements with {index, tag, text, x, y, width, height}

    Returns path to annotated PNG.
    """
    global _last_elements
    elements = json.loads(elements_json)
    _last_elements = elements
    output = str(Path(screenshot_path).with_stem(Path(screenshot_path).stem + "_annotated"))
    result = annotate_screenshot(screenshot_path, elements, output)
    return json.dumps({"annotated_path": result, "element_count": len(elements)})


@mcp.tool()
def gimp_measure(element_a_index: int, element_b_index: int) -> str:
    """Measure pixel distance between two elements by their annotation index.

    Uses elements from the last gimp_annotate call.
    """
    if not _last_elements:
        return json.dumps({"error": "No elements loaded. Run gimp_annotate first."})
    result = measure_spacing(_last_elements, element_a_index, element_b_index)
    return json.dumps(result)


@mcp.tool()
def gimp_diff(before_path: str, after_path: str) -> str:
    """Create a visual diff between two screenshots, highlighting all changes.

    Returns path to diff image where changed pixels are white on black.
    """
    output = visual_diff(before_path, after_path)
    return json.dumps({"diff_path": output})


@mcp.tool()
def gimp_colors(screenshot_path: str, points_json: str) -> str:
    """Extract RGB/hex colors at specific pixel coordinates.

    Args:
        screenshot_path: Path to PNG
        points_json: JSON array of [x, y] coordinate pairs

    Returns color values at each point.
    """
    points = json.loads(points_json)
    colors = extract_colors(screenshot_path, [tuple(p) for p in points])
    return json.dumps({"colors": colors})


@mcp.tool()
def gimp_threshold(image_path: str, low: int = 128, high: int = 255) -> str:
    """Apply threshold to an image — useful for CAPTCHA text extraction.

    Converts to grayscale, then thresholds: pixels below low become black,
    above become white. Cleans up noisy CAPTCHA text.
    """
    output = str(Path(image_path).with_stem(Path(image_path).stem + "_threshold"))

    script = f"""
(let* (
  (image (car (gimp-file-load RUN-NONINTERACTIVE "{image_path}" "img.png")))
  (drawable (car (gimp-image-get-active-drawable image)))
)
  (gimp-image-convert-grayscale image)
  (set! drawable (car (gimp-image-get-active-drawable image)))
  (gimp-threshold drawable {low} {high})
  (file-png-save RUN-NONINTERACTIVE image (car (gimp-image-get-active-drawable image)) "{output}" "threshold" 0 9 1 1 1 1 1)
  (gimp-image-delete image)
)
"""
    _run_gimp_script(script)
    return json.dumps({"threshold_path": output})


@mcp.tool()
def gimp_edge_detect(image_path: str) -> str:
    """Run edge detection on an image — useful for finding shapes in CAPTCHAs.

    Uses Sobel edge detection to highlight boundaries.
    """
    output = str(Path(image_path).with_stem(Path(image_path).stem + "_edges"))

    script = f"""
(let* (
  (image (car (gimp-file-load RUN-NONINTERACTIVE "{image_path}" "img.png")))
  (drawable (car (gimp-image-get-active-drawable image)))
)
  (plug-in-edge RUN-NONINTERACTIVE image drawable 1 0 0)
  (gimp-image-flatten image)
  (file-png-save RUN-NONINTERACTIVE image (car (gimp-image-get-active-drawable image)) "{output}" "edges" 0 9 1 1 1 1 1)
  (gimp-image-delete image)
)
"""
    _run_gimp_script(script)
    return json.dumps({"edges_path": output})


@mcp.tool()
def gimp_denoise(image_path: str, radius: int = 3) -> str:
    """Denoise an image — removes noise from CAPTCHA images before analysis.

    Uses Gaussian blur followed by sharpen to clean up artifacts.
    """
    output = str(Path(image_path).with_stem(Path(image_path).stem + "_clean"))

    script = f"""
(let* (
  (image (car (gimp-file-load RUN-NONINTERACTIVE "{image_path}" "img.png")))
  (drawable (car (gimp-image-get-active-drawable image)))
)
  (plug-in-gauss RUN-NONINTERACTIVE image drawable {radius} {radius} 0)
  (plug-in-unsharp-mask RUN-NONINTERACTIVE image drawable 2.0 0.5 0)
  (gimp-image-flatten image)
  (file-png-save RUN-NONINTERACTIVE image (car (gimp-image-get-active-drawable image)) "{output}" "clean" 0 9 1 1 1 1 1)
  (gimp-image-delete image)
)
"""
    _run_gimp_script(script)
    return json.dumps({"clean_path": output})


@mcp.tool()
def gimp_crop(image_path: str, x: int, y: int, width: int, height: int) -> str:
    """Crop a region from an image. Useful for isolating CAPTCHA areas or elements."""
    output = str(Path(image_path).with_stem(Path(image_path).stem + f"_crop_{x}_{y}"))

    script = f"""
(let* (
  (image (car (gimp-file-load RUN-NONINTERACTIVE "{image_path}" "img.png")))
)
  (gimp-image-crop image {width} {height} {x} {y})
  (gimp-image-flatten image)
  (file-png-save RUN-NONINTERACTIVE image (car (gimp-image-get-active-drawable image)) "{output}" "crop" 0 9 1 1 1 1 1)
  (gimp-image-delete image)
)
"""
    _run_gimp_script(script)
    return json.dumps({"crop_path": output})


if __name__ == "__main__":
    mcp.run(transport="stdio")
