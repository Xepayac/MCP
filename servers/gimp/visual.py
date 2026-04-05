"""Visual analysis — GIMP-powered screenshot annotation and image analysis.

Uses GIMP in headless batch mode (Script-Fu) for image operations:
- Annotate screenshots with numbered bounding boxes
- Measure distances between elements
- Color extraction
- Visual diff between before/after screenshots
"""

import json
import subprocess
import tempfile
from pathlib import Path


def annotate_screenshot(
    screenshot_path: str,
    elements: list[dict],
    output_path: str | None = None,
) -> str:
    """Draw numbered bounding boxes on a screenshot using GIMP.

    Args:
        screenshot_path: Path to PNG screenshot
        elements: List of dicts with {index, tag, text, x, y, width, height}
        output_path: Output path (default: adds _annotated suffix)

    Returns:
        Path to annotated PNG
    """
    if not output_path:
        p = Path(screenshot_path)
        output_path = str(p.with_stem(p.stem + "_annotated"))

    # Build Script-Fu commands for each element
    box_commands = []
    for el in elements:
        x, y, w, h = el["x"], el["y"], el["width"], el["height"]
        idx = el["index"]
        if w <= 0 or h <= 0:
            continue

        # Draw red rectangle
        box_commands.append(f"""
  (gimp-context-set-foreground '(255 40 40))
  (gimp-context-set-line-width 2)
  (gimp-image-select-rectangle image CHANNEL-OP-REPLACE {x} {y} {w} {h})
  (gimp-edit-stroke drawable)
  (gimp-selection-none image)
""")

        # Draw number label background (white box) and text
        label_x = max(x, 0)
        label_y = max(y - 16, 0)
        box_commands.append(f"""
  (gimp-context-set-foreground '(255 255 255))
  (gimp-image-select-rectangle image CHANNEL-OP-REPLACE {label_x} {label_y} 20 14)
  (gimp-edit-fill drawable FILL-FOREGROUND)
  (gimp-selection-none image)
  (gimp-context-set-foreground '(255 40 40))
  (let* ((text-layer (car (gimp-text-fontname image drawable {label_x + 2} {label_y} "{idx}" 0 TRUE 11 UNIT-PIXEL "Sans"))))
    (gimp-floating-sel-anchor text-layer)
  )
""")

    script = f"""
(let* (
  (image (car (gimp-file-load RUN-NONINTERACTIVE "{screenshot_path}" "img.png")))
  (drawable (car (gimp-image-get-active-drawable image)))
)
  {"".join(box_commands)}
  (gimp-image-flatten image)
  (file-png-save RUN-NONINTERACTIVE image (car (gimp-image-get-active-drawable image)) "{output_path}" "annotated" 0 9 1 1 1 1 1)
  (gimp-image-delete image)
)
"""

    result = subprocess.run(
        ["gimp", "-i", "-b", script, "-b", "(gimp-quit 0)"],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"GIMP annotation failed: {result.stderr}")
    return output_path


def visual_diff(
    before_path: str,
    after_path: str,
    output_path: str | None = None,
) -> str:
    """Create a visual diff highlighting changes between two screenshots.

    Computes difference and overlays it in red on the original.
    """
    if not output_path:
        output_path = "/tmp/visual_diff.png"

    script = f"""
(let* (
  (before (car (gimp-file-load RUN-NONINTERACTIVE "{before_path}" "before.png")))
  (after (car (gimp-file-load RUN-NONINTERACTIVE "{after_path}" "after.png")))
  (before-layer (car (gimp-image-get-active-drawable before)))
  (after-layer (car (gimp-image-get-active-drawable after)))
  (diff-layer (car (gimp-layer-new-from-drawable after-layer before)))
)
  (gimp-image-insert-layer before diff-layer 0 -1)
  (gimp-layer-set-mode diff-layer LAYER-MODE-DIFFERENCE)
  (gimp-image-flatten before)
  (gimp-threshold (car (gimp-image-get-active-drawable before)) 10 255)
  (gimp-image-set-active-layer before (car (gimp-image-get-active-drawable before)))
  (file-png-save RUN-NONINTERACTIVE before (car (gimp-image-get-active-drawable before)) "{output_path}" "diff" 0 9 1 1 1 1 1)
  (gimp-image-delete before)
  (gimp-image-delete after)
)
"""

    result = subprocess.run(
        ["gimp", "-i", "-b", script, "-b", "(gimp-quit 0)"],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"GIMP diff failed: {result.stderr}")
    return output_path


def measure_spacing(elements: list[dict], idx_a: int, idx_b: int) -> dict:
    """Measure pixel distance between two elements by index."""
    a = next(e for e in elements if e["index"] == idx_a)
    b = next(e for e in elements if e["index"] == idx_b)

    # Calculate edges
    a_right = a["x"] + a["width"]
    a_bottom = a["y"] + a["height"]
    b_right = b["x"] + b["width"]
    b_bottom = b["y"] + b["height"]

    # Horizontal gap (positive = b is right of a)
    if b["x"] >= a_right:
        h_gap = b["x"] - a_right
    elif a["x"] >= b_right:
        h_gap = -(a["x"] - b_right)
    else:
        h_gap = 0  # overlapping horizontally

    # Vertical gap (positive = b is below a)
    if b["y"] >= a_bottom:
        v_gap = b["y"] - a_bottom
    elif a["y"] >= b_bottom:
        v_gap = -(a["y"] - b_bottom)
    else:
        v_gap = 0  # overlapping vertically

    return {
        "element_a": {"index": idx_a, "tag": a["tag"], "text": a.get("text", "")},
        "element_b": {"index": idx_b, "tag": b["tag"], "text": b.get("text", "")},
        "horizontal_gap_px": h_gap,
        "vertical_gap_px": v_gap,
    }


def extract_colors(screenshot_path: str, points: list[tuple[int, int]]) -> list[dict]:
    """Extract RGB colors at specific pixel coordinates using Pillow."""
    from PIL import Image
    img = Image.open(screenshot_path)
    results = []
    for x, y in points:
        if 0 <= x < img.width and 0 <= y < img.height:
            r, g, b = img.getpixel((x, y))[:3]
            results.append({
                "x": x, "y": y,
                "rgb": [r, g, b],
                "hex": f"#{r:02x}{g:02x}{b:02x}",
            })
    return results
