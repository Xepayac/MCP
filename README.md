# Xepayac MCP Servers

6 MCP servers, 53 tools. Plug into Claude Code, Cursor, or any MCP-compatible client.

## Servers

| Server | Tools | What It Does | System Dependency |
|--------|-------|-------------|-------------------|
| **browser** | 15 | Navigate, click, type, screenshot, eval JS — headless Chromium/Firefox | playwright |
| **email** | 11 | Read, search, send, reply, draft, organize — IMAP/SMTP, zero cloud | None |
| **gimp** | 8 | Annotate screenshots, visual diff, color extract, threshold, crop | GIMP |
| **inkscape** | 7 | SVG create, convert, resize, merge, info, PNG/PDF export | Inkscape |
| **libreoffice** | 6 | Convert between formats, Markdown→PDF/DOCX, read documents, spreadsheets | LibreOffice |
| **tesseract** | 6 | OCR — read text, single line, single word, digits, with positions | Tesseract |

## Install

```bash
pip install -e .                    # Base (all servers)
pip install -e ".[browser]"         # + Playwright for browser server
pip install -e ".[gimp]"            # + Pillow for GIMP color extraction
pip install -e ".[all]"             # Everything
```

System dependencies (install via your package manager):
```bash
sudo apt install gimp inkscape libreoffice tesseract-ocr
npx playwright install firefox      # For browser server
```

## Configure in Claude Code

Add to your MCP settings:

```json
{
  "browser": {
    "command": "python",
    "args": ["-m", "servers.browser.server"],
    "cwd": "/path/to/MCP"
  },
  "email": {
    "command": "python",
    "args": ["-m", "servers.email.server"],
    "cwd": "/path/to/MCP"
  },
  "gimp": {
    "command": "python",
    "args": ["-m", "servers.gimp.server"],
    "cwd": "/path/to/MCP"
  },
  "inkscape": {
    "command": "python",
    "args": ["-m", "servers.inkscape.server"],
    "cwd": "/path/to/MCP"
  },
  "libreoffice": {
    "command": "python",
    "args": ["-m", "servers.libreoffice.server"],
    "cwd": "/path/to/MCP"
  },
  "tesseract": {
    "command": "python",
    "args": ["-m", "servers.tesseract.server"],
    "cwd": "/path/to/MCP"
  }
}
```

## Email Configuration

Create `~/.config/mcp/email_accounts.json`:

```json
{
  "accounts": {
    "work": {
      "email": "you@example.com",
      "password_env": "EMAIL_PASSWORD",
      "imap_host": "imap.gmail.com",
      "imap_port": 993,
      "smtp_host": "smtp.gmail.com",
      "smtp_port": 587
    }
  }
}
```

## License

MIT — Xepayac LLC
