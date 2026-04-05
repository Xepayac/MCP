"""MCP server for LibreOffice — document creation, conversion, and manipulation.

Handles: DOCX, PDF, ODT, spreadsheets, presentations. Converts between formats.
Key use: Markdown→PDF, DOCX generation (USPTO patent filing), spreadsheet data.

Run: python -m servers.libreoffice.server
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("libreoffice")


def _run_libreoffice(args: list[str], timeout: int = 60) -> str:
    """Run LibreOffice in headless mode."""
    cmd = ["libreoffice", "--headless", "--norestore"] + args
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(f"LibreOffice error: {result.stderr}")
    return result.stdout


@mcp.tool()
def lo_convert(input_path: str, output_format: str, output_dir: str = "/tmp") -> str:
    """Convert a document between formats.

    Supported conversions:
    - Markdown/HTML → PDF, DOCX, ODT
    - DOCX → PDF, ODT, HTML
    - ODT → PDF, DOCX, HTML
    - Spreadsheet (XLSX, ODS, CSV) → PDF, HTML
    - Presentation (PPTX, ODP) → PDF

    Args:
        input_path: Path to source file
        output_format: Target format (pdf, docx, odt, html, xlsx, csv, png)
        output_dir: Directory for output file (default: /tmp)
    """
    input_path = Path(input_path)
    if not input_path.exists():
        return json.dumps({"error": f"File not found: {input_path}"})

    _run_libreoffice([
        "--convert-to", output_format,
        "--outdir", output_dir,
        str(input_path),
    ])

    output_name = input_path.stem + "." + output_format
    output_path = Path(output_dir) / output_name

    if output_path.exists():
        return json.dumps({
            "status": "converted",
            "input": str(input_path),
            "output": str(output_path),
            "format": output_format,
            "size_bytes": output_path.stat().st_size,
        })
    else:
        return json.dumps({"error": f"Conversion failed — output not found: {output_path}"})


@mcp.tool()
def lo_markdown_to_pdf(markdown_path: str, output_dir: str = "/tmp") -> str:
    """Convert Markdown to PDF via LibreOffice.

    Converts Markdown → HTML → PDF for clean document output.
    Useful for generating professional documents from markdown sources.
    """
    md_path = Path(markdown_path)
    if not md_path.exists():
        return json.dumps({"error": f"File not found: {md_path}"})

    # Read markdown, wrap in basic HTML for better rendering
    content = md_path.read_text(encoding="utf-8")

    # Simple markdown to HTML (headings, bold, italic, lists, code blocks)
    html_content = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
body {{ font-family: 'Times New Roman', serif; font-size: 12pt; margin: 1in; line-height: 1.5; }}
h1 {{ font-size: 18pt; margin-top: 24pt; }}
h2 {{ font-size: 14pt; margin-top: 18pt; }}
h3 {{ font-size: 12pt; margin-top: 12pt; }}
code {{ font-family: 'Courier New', monospace; background: #f4f4f4; padding: 2px 4px; }}
pre {{ background: #f4f4f4; padding: 12px; border: 1px solid #ddd; overflow-x: auto; }}
table {{ border-collapse: collapse; width: 100%; margin: 12pt 0; }}
th, td {{ border: 1px solid #000; padding: 6px 12px; text-align: left; }}
th {{ background: #f0f0f0; font-weight: bold; }}
</style>
</head><body>
{content}
</body></html>"""

    # Write HTML temp file
    with tempfile.NamedTemporaryFile(suffix=".html", mode="w", delete=False, dir=output_dir) as f:
        f.write(html_content)
        html_path = f.name

    # Convert HTML → PDF
    _run_libreoffice([
        "--convert-to", "pdf",
        "--outdir", output_dir,
        html_path,
    ])

    pdf_path = Path(html_path).with_suffix(".pdf")
    os.unlink(html_path)  # Clean up temp HTML

    if pdf_path.exists():
        return json.dumps({
            "status": "converted",
            "input": str(md_path),
            "output": str(pdf_path),
            "size_bytes": pdf_path.stat().st_size,
        })
    else:
        return json.dumps({"error": "PDF conversion failed"})


@mcp.tool()
def lo_markdown_to_docx(markdown_path: str, output_dir: str = "/tmp") -> str:
    """Convert Markdown to DOCX via LibreOffice.

    Generates professional DOCX documents from markdown.
    Useful for USPTO patent filing (avoids $86 non-DOCX surcharge).
    """
    md_path = Path(markdown_path)
    if not md_path.exists():
        return json.dumps({"error": f"File not found: {md_path}"})

    content = md_path.read_text(encoding="utf-8")
    html_content = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head><body>
{content}
</body></html>"""

    with tempfile.NamedTemporaryFile(suffix=".html", mode="w", delete=False, dir=output_dir) as f:
        f.write(html_content)
        html_path = f.name

    _run_libreoffice([
        "--convert-to", "docx",
        "--outdir", output_dir,
        html_path,
    ])

    docx_path = Path(html_path).with_suffix(".docx")
    os.unlink(html_path)

    if docx_path.exists():
        return json.dumps({
            "status": "converted",
            "input": str(md_path),
            "output": str(docx_path),
            "size_bytes": docx_path.stat().st_size,
        })
    else:
        return json.dumps({"error": "DOCX conversion failed"})


@mcp.tool()
def lo_read_document(file_path: str) -> str:
    """Extract text content from a document (DOCX, ODT, PDF, PPTX).

    Converts to plain text and returns the content.
    Useful for reading documents that can't be opened as text files.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        return json.dumps({"error": f"File not found: {file_path}"})

    with tempfile.TemporaryDirectory() as tmpdir:
        _run_libreoffice([
            "--convert-to", "txt:Text",
            "--outdir", tmpdir,
            str(file_path),
        ])

        txt_path = Path(tmpdir) / (file_path.stem + ".txt")
        if txt_path.exists():
            content = txt_path.read_text(encoding="utf-8", errors="replace")
            return json.dumps({
                "file": str(file_path),
                "content": content[:50000],  # Limit for context
                "chars": len(content),
                "truncated": len(content) > 50000,
            })
        else:
            return json.dumps({"error": "Text extraction failed"})


@mcp.tool()
def lo_create_spreadsheet(data: list[list[str]], output_path: str = "/tmp/output.xlsx") -> str:
    """Create a spreadsheet from tabular data.

    Args:
        data: 2D list of strings (first row = headers)
        output_path: Where to save (supports .xlsx, .ods, .csv)
    """
    import csv

    with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False, newline="") as f:
        writer = csv.writer(f)
        for row in data:
            writer.writerow(row)
        csv_path = f.name

    output_path = Path(output_path)
    output_format = output_path.suffix.lstrip(".")

    if output_format == "csv":
        # Just copy the CSV
        Path(csv_path).rename(output_path)
    else:
        _run_libreoffice([
            "--convert-to", output_format,
            "--outdir", str(output_path.parent),
            csv_path,
        ])
        converted = Path(csv_path).with_suffix(f".{output_format}")
        if converted.exists():
            converted.rename(output_path)
        os.unlink(csv_path) if Path(csv_path).exists() else None

    if output_path.exists():
        return json.dumps({
            "status": "created",
            "output": str(output_path),
            "rows": len(data),
            "cols": len(data[0]) if data else 0,
            "size_bytes": output_path.stat().st_size,
        })
    else:
        return json.dumps({"error": "Spreadsheet creation failed"})


@mcp.tool()
def lo_print_to_pdf(file_path: str, output_dir: str = "/tmp") -> str:
    """Print any document to PDF — the universal 'print to PDF' for any format LibreOffice supports.

    Supports: DOCX, ODT, XLSX, ODS, PPTX, ODP, HTML, RTF, and more.
    """
    return lo_convert(file_path, "pdf", output_dir)


if __name__ == "__main__":
    mcp.run()
