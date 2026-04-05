---
name: email-draft
description: Save a draft email for human review
---

# /email-draft — Draft for Review

<trl>
DEFINE "email-draft" AS FUNCTION primitive.
FUNCTION email-draft SHALL REQUIRE RECORD uid AND RECORD account.
FUNCTION email-draft SHALL READ RECORD email BY RECORD uid.
FUNCTION email-draft SHALL WRITE RECORD draft 'with RECORD suggested_response AND RECORD context.
FUNCTION email-draft SHALL RESPOND 'with RECORD draft_summary TO PARTY human.
PARTY human SHALL REVIEW RECORD draft THEN SEND OR EDIT.
</trl>

For a BUSINESS-tier email, create a draft response:

1. Read the original email
2. Compose a suggested response (best attempt at what the human would say)
3. Save via `email_draft(to=SENDER, subject=RE_SUBJECT, body=SUGGESTED)`
4. Present to the human:

```
## Draft Created
To: SENDER
Subject: Re: SUBJECT
Context: WHY this needs human review

Draft summary: ONE_LINE_SUMMARY

Review in your email client, edit as needed, then send manually.
```

The agent NEVER sends business-tier emails. Only drafts.
