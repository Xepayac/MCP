---
name: email-read
description: Read a specific email by UID — headers, body, attachments
---

# /email-read — Read Email

<trl>
DEFINE "email-read" AS FUNCTION primitive.
FUNCTION email-read SHALL REQUIRE RECORD uid.
FUNCTION email-read MAY REQUIRE RECORD account AND RECORD folder.
FUNCTION email-read SHALL READ RECORD email BY RECORD uid THEN RESPOND 'with RECORD from AND RECORD to AND RECORD subject AND RECORD date AND RECORD body_text AND RECORD attachments.
</trl>

Call `email_read(uid=UID)`. Present the full email:

```
## Email
From: NAME <email>
To: RECIPIENT
Date: DATE
Subject: SUBJECT

BODY_TEXT

Attachments: N (filename, size)
```
