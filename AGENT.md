# AGENT.md — Xepayac MCP Servers

<trl>
DEFINE "xepayac_mcp" AS NAMESPACE.
NAMESPACE xepayac_mcp CONTAINS MODULE servers AND MODULE skills AND MODULE shared AND MODULE tests.
NAMESPACE xepayac_mcp IMPLEMENTS INTERFACE mcp.
</trl>

## What This Repository Is

`Xepayac/MCP` ships Model Context Protocol (MCP) servers that bridge Claude Code — and any MCP-compatible client — to local, privacy-preserving capabilities. Each subdirectory under `servers/` is an independent MCP server that exposes a bounded set of tools: browser automation (Playwright), email over IMAP/SMTP, GIMP image ops, Inkscape SVG, LibreOffice conversion, and Tesseract OCR. Six servers, 53 tools, zero cloud dependencies beyond your own mail host.

The sibling `skills/` directory holds Claude Code skills (email triage, classify, respond, etc.) that are authored against these servers. `shared/` holds cross-server helpers.

This is a Xepayac LLC repo, not a TRUGS-LLC repo — it consumes the TRUGS ecosystem but is not part of the specification.

## Repository Structure

| Path | Content |
|------|---------|
| `servers/` | Six MCP server implementations (browser, email, gimp, inkscape, libreoffice, tesseract) |
| `skills/` | Claude Code skills that call into the servers |
| `shared/` | Shared utilities across servers (env loading, etc.) |
| `tests/` | Smoke tests for server imports and behavior |
| `folder.trug.json` | Structural truth for this repo |
| `README.md` | Human quickstart — install + MCP client configuration |

## Rules for This Repository

<trl>
AGENT claude MAY READ FILE folder.trug.json 'for RECORD structure.
AGENT claude MAY READ FILE README.md 'for DATA install_and_config.
AGENT claude SHALL DEFINE RESOURCE branch FROM ENDPOINT main THEN WRITE ALL DATA TO RESOURCE branch.
AGENT claude SHALL_NOT MERGE ANY RESOURCE TO ENDPOINT main.
PARTY human SHALL APPROVE ALL RESOURCE THEN MERGE RESULT TO ENDPOINT main.
</trl>

Start with `folder.trug.json` for machine-readable structure. `README.md` is the human quickstart with install commands and MCP client JSON. Project workflow rules (branch + PR, HITM merge) live in `CLAUDE.md`.

## Companion Repositories

- [TRUGS-LLC/TRUGS-TOOLS](https://github.com/TRUGS-LLC/TRUGS-TOOLS) — the `tg` CLI. Some future MCP servers here will wrap `tg` subcommands.
- [TRUGS-LLC/TRUGS-AGENT](https://github.com/TRUGS-LLC/TRUGS-AGENT) — LLM development framework (TRL + AAA + EPIC + Memory) that consumes MCP servers like these.
- [TRUGS-LLC/TRUGS](https://github.com/TRUGS-LLC/TRUGS) — the canonical TRUGS specification.

## License + Status

MIT — Xepayac LLC. Alpha (`Development Status :: 3 - Alpha` in `pyproject.toml`). Used daily by the owner; interfaces may still shift.
