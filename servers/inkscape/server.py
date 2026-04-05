"""MCP server for Inkscape — SVG generation, conversion, and manipulation.

Run: python -m servers.inkscape.server
"""

import json
import subprocess
import tempfile
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from shared.env import clean_env

mcp = FastMCP("inkscape")


def _run_inkscape(args: list[str], timeout: int = 30) -> subprocess.CompletedProcess:
    """Run Inkscape CLI command."""
    result = subprocess.run(
        ["inkscape"] + args,
        capture_output=True, text=True, timeout=timeout,
        env=clean_env(),
    )
    if result.returncode != 0 and "WARNING" not in result.stderr:
        raise RuntimeError(f"Inkscape error: {result.stderr}")
    return result


@mcp.tool()
def svg_to_png(svg_path: str, output_path: str | None = None,
               width: int | None = None, height: int | None = None) -> str:
    """Convert SVG to PNG. Optionally specify dimensions.

    Args:
        svg_path: Path to SVG file
        output_path: Output PNG path (default: same name with .png)
        width: Output width in pixels
        height: Output height in pixels
    """
    if not output_path:
        output_path = str(Path(svg_path).with_suffix(".png"))

    args = [svg_path, "--export-filename", output_path, "--export-type", "png"]
    if width:
        args.extend(["--export-width", str(width)])
    if height:
        args.extend(["--export-height", str(height)])
    _run_inkscape(args)
    return json.dumps({"output": output_path})


@mcp.tool()
def png_to_svg(png_path: str, output_path: str | None = None) -> str:
    """Trace a PNG/bitmap to SVG using Inkscape's autotrace.

    Converts raster images to scalable vector graphics.
    """
    if not output_path:
        output_path = str(Path(png_path).with_suffix(".svg"))

    # Use potrace via Inkscape for bitmap tracing
    args = [png_path, "--export-filename", output_path, "--export-type", "svg"]
    _run_inkscape(args)
    return json.dumps({"output": output_path})


@mcp.tool()
def svg_to_pdf(svg_path: str, output_path: str | None = None) -> str:
    """Convert SVG to PDF."""
    if not output_path:
        output_path = str(Path(svg_path).with_suffix(".pdf"))

    args = [svg_path, "--export-filename", output_path, "--export-type", "pdf"]
    _run_inkscape(args)
    return json.dumps({"output": output_path})


@mcp.tool()
def svg_info(svg_path: str) -> str:
    """Get SVG dimensions and metadata."""
    result = _run_inkscape([svg_path, "--query-all"])
    elements = []
    for line in result.stdout.strip().split("\n")[:50]:
        parts = line.split(",")
        if len(parts) >= 5:
            elements.append({
                "id": parts[0],
                "x": float(parts[1]),
                "y": float(parts[2]),
                "width": float(parts[3]),
                "height": float(parts[4]),
            })

    # Get document dimensions
    w_result = _run_inkscape([svg_path, "--query-width"])
    h_result = _run_inkscape([svg_path, "--query-height"])

    return json.dumps({
        "width": float(w_result.stdout.strip()) if w_result.stdout.strip() else 0,
        "height": float(h_result.stdout.strip()) if h_result.stdout.strip() else 0,
        "element_count": len(elements),
        "elements": elements,
    })


@mcp.tool()
def svg_create(content: str, output_path: str) -> str:
    """Write SVG content to a file.

    Args:
        content: Raw SVG markup
        output_path: Where to save the SVG file
    """
    Path(output_path).write_text(content, encoding="utf-8")
    return json.dumps({"output": output_path, "size_bytes": len(content)})


@mcp.tool()
def svg_resize(svg_path: str, width: int, height: int,
               output_path: str | None = None) -> str:
    """Resize an SVG to specific pixel dimensions and export as PNG."""
    if not output_path:
        output_path = str(Path(svg_path).with_stem(
            Path(svg_path).stem + f"_{width}x{height}").with_suffix(".png"))

    args = [svg_path, "--export-filename", output_path,
            "--export-type", "png",
            "--export-width", str(width),
            "--export-height", str(height)]
    _run_inkscape(args)
    return json.dumps({"output": output_path, "width": width, "height": height})


@mcp.tool()
def svg_merge(svg_paths: str, output_path: str) -> str:
    """Merge multiple SVGs into one document (vertically stacked).

    Args:
        svg_paths: JSON array of SVG file paths
        output_path: Output SVG path
    """
    paths = json.loads(svg_paths)
    # Read all SVGs, extract viewBox info, stack them
    svgs = []
    total_height = 0
    max_width = 0

    for p in paths:
        content = Path(p).read_text(encoding="utf-8")
        # Query dimensions
        w_result = _run_inkscape([p, "--query-width"])
        h_result = _run_inkscape([p, "--query-height"])
        w = float(w_result.stdout.strip()) if w_result.stdout.strip() else 100
        h = float(h_result.stdout.strip()) if h_result.stdout.strip() else 100
        svgs.append({"path": p, "content": content, "width": w, "height": h})
        max_width = max(max_width, w)
        total_height += h

    # Build merged SVG
    merged = f'<svg xmlns="http://www.w3.org/2000/svg" width="{max_width}" height="{total_height}">\n'
    y_offset = 0
    for s in svgs:
        merged += f'  <image href="{s["path"]}" x="0" y="{y_offset}" width="{s["width"]}" height="{s["height"]}"/>\n'
        y_offset += s["height"]
    merged += '</svg>\n'

    Path(output_path).write_text(merged, encoding="utf-8")
    return json.dumps({"output": output_path, "width": max_width, "height": total_height})


if __name__ == "__main__":
    mcp.run(transport="stdio")
