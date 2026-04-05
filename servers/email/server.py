"""MCP server for email management — IMAP/SMTP, zero cloud dependency.

Read, compose, send, search, organize email across multiple accounts.
Works alongside browser_mcp.py and gimp_mcp.py.

Config: ~/.config/trugs/email_accounts.json
Run: python -m servers.email.server
"""

import email
import email.mime.text
import email.mime.multipart
import email.mime.base
import email.utils
import imaplib
import json
import os
import smtplib
import ssl
from datetime import datetime, timezone
from email.header import decode_header
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("email")

# ─── Config ───────────────────────────────────────────────────────────────────

CONFIG_PATH = Path.home() / ".config" / "mcp" / "email_accounts.json"


def _load_config() -> dict[str, Any]:
    """Load account config from disk."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"Email config not found at {CONFIG_PATH}. "
            "Create it with account credentials. See #1261 for format."
        )
    with open(CONFIG_PATH) as f:
        return json.load(f)


def _get_account(name: str | None = None) -> dict[str, Any]:
    """Get a specific account config, or the first one if name is None."""
    config = _load_config()
    accounts = config.get("accounts", {})
    if not accounts:
        raise ValueError("No accounts configured.")
    if name is None:
        name = next(iter(accounts))
    if name not in accounts:
        raise ValueError(f"Account '{name}' not found. Available: {list(accounts.keys())}")
    return accounts[name]


def _get_password(account: dict[str, Any]) -> str:
    """Resolve password from env var or direct value."""
    if "password_env" in account:
        env_var = account["password_env"]
        pw = os.environ.get(env_var)
        if pw is None:
            raise ValueError(f"Environment variable '{env_var}' not set for account '{account.get('email', '?')}'")
        return pw
    if "password" in account:
        return account["password"]
    raise ValueError(f"No password or password_env configured for '{account.get('email', '?')}'")


# ─── IMAP Helpers ─────────────────────────────────────────────────────────────

def _imap_connect(account: dict[str, Any]) -> imaplib.IMAP4_SSL:
    """Connect and authenticate to IMAP server."""
    host = account.get("imap_host", "imap.gmail.com")
    port = account.get("imap_port", 993)
    ctx = ssl.create_default_context()
    conn = imaplib.IMAP4_SSL(host, port, ssl_context=ctx)
    conn.login(account["email"], _get_password(account))
    return conn


def _decode_header_value(raw: str | None) -> str:
    """Decode RFC 2047 encoded header."""
    if raw is None:
        return ""
    parts = decode_header(raw)
    decoded = []
    for data, charset in parts:
        if isinstance(data, bytes):
            decoded.append(data.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(data)
    return " ".join(decoded)


def _parse_envelope(msg: email.message.Message, uid: str) -> dict[str, Any]:
    """Extract key headers from a parsed email message."""
    return {
        "uid": uid,
        "from": _decode_header_value(msg.get("From")),
        "to": _decode_header_value(msg.get("To")),
        "subject": _decode_header_value(msg.get("Subject")),
        "date": msg.get("Date", ""),
        "message_id": msg.get("Message-ID", ""),
    }


def _get_body(msg: email.message.Message) -> dict[str, str]:
    """Extract text and/or HTML body from a message."""
    text_body = ""
    html_body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            disp = str(part.get("Content-Disposition", ""))
            if "attachment" in disp:
                continue
            payload = part.get_payload(decode=True)
            if payload is None:
                continue
            charset = part.get_content_charset() or "utf-8"
            decoded = payload.decode(charset, errors="replace")
            if ct == "text/plain" and not text_body:
                text_body = decoded
            elif ct == "text/html" and not html_body:
                html_body = decoded
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            decoded = payload.decode(charset, errors="replace")
            if msg.get_content_type() == "text/html":
                html_body = decoded
            else:
                text_body = decoded
    return {"text": text_body, "html": html_body}


def _list_attachments(msg: email.message.Message) -> list[dict[str, str]]:
    """List attachment filenames and types."""
    attachments = []
    if msg.is_multipart():
        for part in msg.walk():
            disp = str(part.get("Content-Disposition", ""))
            if "attachment" in disp:
                filename = part.get_filename() or "unnamed"
                attachments.append({
                    "filename": _decode_header_value(filename),
                    "content_type": part.get_content_type(),
                    "size": len(part.get_payload(decode=True) or b""),
                })
    return attachments


# ─── SMTP Helpers ─────────────────────────────────────────────────────────────

def _smtp_connect(account: dict[str, Any]) -> smtplib.SMTP:
    """Connect and authenticate to SMTP server."""
    host = account.get("smtp_host", "smtp.gmail.com")
    port = account.get("smtp_port", 587)
    conn = smtplib.SMTP(host, port)
    conn.ehlo()
    conn.starttls(context=ssl.create_default_context())
    conn.ehlo()
    conn.login(account["email"], _get_password(account))
    return conn


# ─── MCP Tools: Read ─────────────────────────────────────────────────────────

@mcp.tool()
def email_accounts() -> str:
    """List all configured email accounts.

    Returns array of account names and email addresses.
    """
    config = _load_config()
    accounts = config.get("accounts", {})
    result = [{"name": k, "email": v.get("email", "")} for k, v in accounts.items()]
    return json.dumps(result)


@mcp.tool()
def email_folders(account: str = "") -> str:
    """List all folders/mailboxes for an account.

    Args:
        account: Account name from config. Empty string for default account.

    Returns array of folder names with message counts.
    """
    acct = _get_account(account or None)
    conn = _imap_connect(acct)
    try:
        status, folders = conn.list()
        result = []
        if status == "OK" and folders:
            import re
            list_pattern = re.compile(r'\(.*?\)\s+"(.+?)"\s+"(.+?)"')
            for f in folders:
                if isinstance(f, bytes):
                    decoded = f.decode("utf-8", errors="replace")
                    match = list_pattern.search(decoded)
                    if match:
                        folder_name = match.group(2)
                    else:
                        continue
                    # Skip non-selectable folders
                    if "\\Noselect" in decoded:
                        continue
                    # Get message count
                    try:
                        st, data = conn.select(f'"{folder_name}"', readonly=True)
                        count = int(data[0]) if st == "OK" else 0
                    except Exception:
                        count = 0
                    result.append({"name": folder_name, "messages": count})
        return json.dumps(result)
    finally:
        conn.logout()


@mcp.tool()
def email_list(
    account: str = "",
    folder: str = "INBOX",
    limit: int = 20,
    unread_only: bool = False,
) -> str:
    """List messages in a folder.

    Args:
        account: Account name from config. Empty string for default.
        folder: Mailbox folder name (default: INBOX).
        limit: Max messages to return (default: 20, most recent first).
        unread_only: If true, only show unread messages.

    Returns array of {uid, from, to, subject, date, message_id}.
    """
    acct = _get_account(account or None)
    conn = _imap_connect(acct)
    try:
        conn.select(f'"{folder}"', readonly=True)
        criteria = "UNSEEN" if unread_only else "ALL"
        status, data = conn.uid("search", None, criteria)
        if status != "OK" or not data[0]:
            return json.dumps([])
        uids = data[0].split()
        # Most recent first, apply limit
        uids = uids[-limit:][::-1]

        results = []
        for uid in uids:
            status, msg_data = conn.uid("fetch", uid, "(RFC822.HEADER)")
            if status == "OK" and msg_data[0]:
                raw = msg_data[0][1] if isinstance(msg_data[0], tuple) else msg_data[0]
                msg = email.message_from_bytes(raw)
                results.append(_parse_envelope(msg, uid.decode()))
        return json.dumps(results)
    finally:
        conn.logout()


@mcp.tool()
def email_read(account: str = "", uid: str = "", folder: str = "INBOX") -> str:
    """Read a specific email message by UID.

    Args:
        account: Account name from config. Empty string for default.
        uid: Message UID (from email_list results).
        folder: Mailbox folder (default: INBOX).

    Returns {uid, from, to, subject, date, message_id, body_text, body_html, attachments}.
    """
    if not uid:
        return json.dumps({"error": "uid is required"})
    acct = _get_account(account or None)
    conn = _imap_connect(acct)
    try:
        conn.select(f'"{folder}"', readonly=True)
        status, msg_data = conn.uid("fetch", uid, "(RFC822)")
        if status != "OK" or not msg_data[0]:
            return json.dumps({"error": f"Message {uid} not found"})
        raw = msg_data[0][1] if isinstance(msg_data[0], tuple) else msg_data[0]
        msg = email.message_from_bytes(raw)
        envelope = _parse_envelope(msg, uid)
        body = _get_body(msg)
        attachments = _list_attachments(msg)
        return json.dumps({
            **envelope,
            "body_text": body["text"],
            "body_html": body["html"],
            "attachments": attachments,
        })
    finally:
        conn.logout()


# ─── MCP Tools: Search ───────────────────────────────────────────────────────

@mcp.tool()
def email_search(
    account: str = "",
    folder: str = "INBOX",
    query: str = "",
    from_addr: str = "",
    to_addr: str = "",
    since: str = "",
    before: str = "",
    subject: str = "",
    limit: int = 20,
) -> str:
    """Search emails using IMAP SEARCH criteria.

    Args:
        account: Account name. Empty for default.
        folder: Mailbox folder (default: INBOX).
        query: Full-text body search term.
        from_addr: Filter by sender address.
        to_addr: Filter by recipient address.
        since: Messages after this date (YYYY-MM-DD).
        before: Messages before this date (YYYY-MM-DD).
        subject: Filter by subject text.
        limit: Max results (default: 20).

    Returns array of {uid, from, to, subject, date, message_id}.
    """
    acct = _get_account(account or None)
    conn = _imap_connect(acct)
    try:
        conn.select(f'"{folder}"', readonly=True)
        criteria_parts = []
        if from_addr:
            criteria_parts.append(f'FROM "{from_addr}"')
        if to_addr:
            criteria_parts.append(f'TO "{to_addr}"')
        if subject:
            criteria_parts.append(f'SUBJECT "{subject}"')
        if since:
            # IMAP date format: DD-Mon-YYYY
            dt = datetime.strptime(since, "%Y-%m-%d")
            criteria_parts.append(f'SINCE {dt.strftime("%d-%b-%Y")}')
        if before:
            dt = datetime.strptime(before, "%Y-%m-%d")
            criteria_parts.append(f'BEFORE {dt.strftime("%d-%b-%Y")}')
        if query:
            criteria_parts.append(f'BODY "{query}"')
        if not criteria_parts:
            criteria_parts.append("ALL")

        search_str = " ".join(criteria_parts)
        status, data = conn.uid("search", None, search_str)
        if status != "OK" or not data[0]:
            return json.dumps([])

        uids = data[0].split()
        uids = uids[-limit:][::-1]

        results = []
        for uid in uids:
            status, msg_data = conn.uid("fetch", uid, "(RFC822.HEADER)")
            if status == "OK" and msg_data[0]:
                raw = msg_data[0][1] if isinstance(msg_data[0], tuple) else msg_data[0]
                msg = email.message_from_bytes(raw)
                results.append(_parse_envelope(msg, uid.decode()))
        return json.dumps(results)
    finally:
        conn.logout()


# ─── MCP Tools: Write ────────────────────────────────────────────────────────

@mcp.tool()
def email_send(
    account: str = "",
    to: str = "",
    subject: str = "",
    body: str = "",
    cc: str = "",
    bcc: str = "",
    attachments: str = "",
) -> str:
    """Send a new email.

    Args:
        account: Account name. Empty for default.
        to: Recipient email address(es), comma-separated.
        subject: Email subject.
        body: Plain text email body.
        cc: CC recipients, comma-separated.
        bcc: BCC recipients, comma-separated.
        attachments: Comma-separated file paths to attach.

    Returns {status, message_id}.
    """
    if not to or not subject:
        return json.dumps({"error": "to and subject are required"})
    acct = _get_account(account or None)
    from_addr = acct["email"]

    if attachments:
        msg = email.mime.multipart.MIMEMultipart()
        msg.attach(email.mime.text.MIMEText(body, "plain"))
        for filepath in [p.strip() for p in attachments.split(",") if p.strip()]:
            path = Path(filepath)
            if not path.exists():
                return json.dumps({"error": f"Attachment not found: {filepath}"})
            with open(path, "rb") as f:
                part = email.mime.base.MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
            email.encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename={path.name}")
            msg.attach(part)
    else:
        msg = email.mime.text.MIMEText(body, "plain")

    msg["From"] = from_addr
    msg["To"] = to
    msg["Subject"] = subject
    if cc:
        msg["Cc"] = cc
    msg["Date"] = email.utils.formatdate(localtime=True)
    msg["Message-ID"] = email.utils.make_msgid(domain=from_addr.split("@")[1])

    all_recipients = [a.strip() for a in to.split(",")]
    if cc:
        all_recipients += [a.strip() for a in cc.split(",")]
    if bcc:
        all_recipients += [a.strip() for a in bcc.split(",")]

    smtp = _smtp_connect(acct)
    try:
        smtp.sendmail(from_addr, all_recipients, msg.as_string())
        return json.dumps({"status": "sent", "message_id": msg["Message-ID"]})
    finally:
        smtp.quit()


@mcp.tool()
def email_reply(
    account: str = "",
    uid: str = "",
    folder: str = "INBOX",
    body: str = "",
    reply_all: bool = False,
) -> str:
    """Reply to an email by UID.

    Args:
        account: Account name. Empty for default.
        uid: UID of the message to reply to.
        folder: Folder containing the message (default: INBOX).
        body: Reply body text.
        reply_all: If true, reply to all recipients.

    Returns {status, message_id}.
    """
    if not uid or not body:
        return json.dumps({"error": "uid and body are required"})
    acct = _get_account(account or None)
    from_addr = acct["email"]

    # Fetch original message
    conn = _imap_connect(acct)
    try:
        conn.select(f'"{folder}"', readonly=True)
        status, msg_data = conn.uid("fetch", uid, "(RFC822)")
        if status != "OK" or not msg_data[0]:
            return json.dumps({"error": f"Message {uid} not found"})
        raw = msg_data[0][1] if isinstance(msg_data[0], tuple) else msg_data[0]
        original = email.message_from_bytes(raw)
    finally:
        conn.logout()

    # Build reply
    reply = email.mime.text.MIMEText(body, "plain")
    orig_subject = _decode_header_value(original.get("Subject", ""))
    if not orig_subject.lower().startswith("re:"):
        reply["Subject"] = f"Re: {orig_subject}"
    else:
        reply["Subject"] = orig_subject
    reply["From"] = from_addr
    reply["In-Reply-To"] = original.get("Message-ID", "")
    reply["References"] = original.get("Message-ID", "")
    reply["Date"] = email.utils.formatdate(localtime=True)
    reply["Message-ID"] = email.utils.make_msgid(domain=from_addr.split("@")[1])

    # Determine recipients
    reply_to = original.get("Reply-To") or original.get("From", "")
    recipients = [reply_to]
    if reply_all:
        to_addrs = original.get("To", "")
        cc_addrs = original.get("Cc", "")
        all_addrs = [a.strip() for a in (to_addrs + "," + cc_addrs).split(",") if a.strip()]
        recipients += [a for a in all_addrs if from_addr not in a]
    reply["To"] = ", ".join(recipients)

    smtp = _smtp_connect(acct)
    try:
        smtp.sendmail(from_addr, recipients, reply.as_string())
        return json.dumps({"status": "sent", "message_id": reply["Message-ID"]})
    finally:
        smtp.quit()


@mcp.tool()
def email_draft(
    account: str = "",
    to: str = "",
    subject: str = "",
    body: str = "",
) -> str:
    """Save an email draft to the Drafts folder via IMAP APPEND.

    Args:
        account: Account name. Empty for default.
        to: Recipient email address.
        subject: Email subject.
        body: Plain text body.

    Returns {status, folder}.
    """
    if not to or not subject:
        return json.dumps({"error": "to and subject are required"})
    acct = _get_account(account or None)
    from_addr = acct["email"]

    msg = email.mime.text.MIMEText(body, "plain")
    msg["From"] = from_addr
    msg["To"] = to
    msg["Subject"] = subject
    msg["Date"] = email.utils.formatdate(localtime=True)

    conn = _imap_connect(acct)
    try:
        # Try common draft folder names
        for drafts_folder in ['"[Gmail]/Drafts"', '"Drafts"', '"INBOX.Drafts"']:
            try:
                conn.append(drafts_folder, "\\Draft", None, msg.as_bytes())
                return json.dumps({"status": "draft_saved", "folder": drafts_folder.strip('"')})
            except imaplib.IMAP4.error:
                continue
        return json.dumps({"error": "Could not find Drafts folder"})
    finally:
        conn.logout()


# ─── MCP Tools: Organize ─────────────────────────────────────────────────────

@mcp.tool()
def email_move(
    account: str = "",
    uids: str = "",
    source_folder: str = "INBOX",
    target_folder: str = "",
) -> str:
    """Move messages to a different folder.

    Args:
        account: Account name. Empty for default.
        uids: Comma-separated UIDs to move.
        source_folder: Current folder (default: INBOX).
        target_folder: Destination folder.

    Returns {moved_count, target_folder}.
    """
    if not uids or not target_folder:
        return json.dumps({"error": "uids and target_folder are required"})
    acct = _get_account(account or None)
    uid_list = [u.strip() for u in uids.split(",") if u.strip()]

    conn = _imap_connect(acct)
    try:
        conn.select(f'"{source_folder}"')
        moved = 0
        for uid in uid_list:
            try:
                status, _ = conn.uid("copy", uid, f'"{target_folder}"')
                if status == "OK":
                    conn.uid("store", uid, "+FLAGS", "(\\Deleted)")
                    moved += 1
            except imaplib.IMAP4.error:
                continue
        conn.expunge()
        return json.dumps({"moved_count": moved, "target_folder": target_folder})
    finally:
        conn.logout()


@mcp.tool()
def email_delete(
    account: str = "",
    uids: str = "",
    folder: str = "INBOX",
    confirm: bool = False,
) -> str:
    """Delete messages by UID. Dry-run by default — set confirm=true to actually delete.

    Args:
        account: Account name. Empty for default.
        uids: Comma-separated UIDs to delete.
        folder: Folder containing messages (default: INBOX).
        confirm: If false (default), only reports what would be deleted. Set true to execute.

    Returns {action, count, uids} where action is 'dry_run' or 'deleted'.
    """
    if not uids:
        return json.dumps({"error": "uids is required"})
    uid_list = [u.strip() for u in uids.split(",") if u.strip()]

    if not confirm:
        return json.dumps({
            "action": "dry_run",
            "count": len(uid_list),
            "uids": uid_list,
            "message": "Set confirm=true to actually delete these messages.",
        })

    acct = _get_account(account or None)
    conn = _imap_connect(acct)
    try:
        conn.select(f'"{folder}"')
        deleted = 0
        for uid in uid_list:
            try:
                conn.uid("store", uid, "+FLAGS", "(\\Deleted)")
                deleted += 1
            except imaplib.IMAP4.error:
                continue
        conn.expunge()
        return json.dumps({"action": "deleted", "count": deleted, "uids": uid_list})
    finally:
        conn.logout()


@mcp.tool()
def email_flag(
    account: str = "",
    uids: str = "",
    folder: str = "INBOX",
    flag: str = "\\Flagged",
    add: bool = True,
) -> str:
    """Flag or unflag messages.

    Args:
        account: Account name. Empty for default.
        uids: Comma-separated UIDs.
        folder: Folder (default: INBOX).
        flag: IMAP flag (default: \\Flagged). Others: \\Seen, \\Answered, \\Draft.
        add: True to add flag, False to remove.

    Returns {flagged_count, flag, action}.
    """
    if not uids:
        return json.dumps({"error": "uids is required"})
    uid_list = [u.strip() for u in uids.split(",") if u.strip()]
    acct = _get_account(account or None)
    action = "+FLAGS" if add else "-FLAGS"

    conn = _imap_connect(acct)
    try:
        conn.select(f'"{folder}"')
        count = 0
        for uid in uid_list:
            try:
                conn.uid("store", uid, action, f"({flag})")
                count += 1
            except imaplib.IMAP4.error:
                continue
        return json.dumps({
            "flagged_count": count,
            "flag": flag,
            "action": "added" if add else "removed",
        })
    finally:
        conn.logout()


# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run(transport="stdio")
