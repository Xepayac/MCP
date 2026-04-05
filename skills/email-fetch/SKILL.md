---
name: email-fetch
description: List unread emails from configured accounts
---

# /email-fetch — Fetch Unread

<trl>
DEFINE "email-fetch" AS FUNCTION primitive.
FUNCTION email-fetch SHALL READ ALL RECORD email FROM EACH RECORD account 'where RECORD status EQUALS "unread".
FUNCTION email-fetch SHALL RESPOND 'with EACH RECORD email 'as RECORD uid AND RECORD from AND RECORD subject AND RECORD date AND RECORD account.
</trl>

For each configured account, call `email_list(unread_only=true)`. Return a summary table:

```
## Unread Emails
1. [ACCOUNT] From: NAME <email> — Subject: SUBJECT (DATE) — UID: XXX
2. ...

Total: N unread across M accounts.
```
