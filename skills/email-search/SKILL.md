---
name: email-search
description: Search emails by criteria — from, subject, date, body
---

# /email-search — Search Emails

<trl>
DEFINE "email-search" AS FUNCTION primitive.
FUNCTION email-search SHALL REQUIRE RECORD query.
FUNCTION email-search MAY REQUIRE RECORD account AND RECORD folder AND RECORD from_addr AND RECORD subject AND RECORD since AND RECORD before.
FUNCTION email-search SHALL READ ALL RECORD email 'that MATCH RECORD query.
FUNCTION email-search SHALL RESPOND 'with EACH RECORD email 'as RECORD uid AND RECORD from AND RECORD subject AND RECORD date.
</trl>

Search emails using any combination of criteria. Call `email_search()` with the provided filters.

```
## Search Results
Query: FROM "name@example.com" SINCE 2026-04-01

1. UID: XXX — From: NAME — Subject: SUBJECT (DATE)
2. ...

Found: N results.
```
