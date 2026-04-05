---
name: email-classify
description: Classify an email as POLITE, BUSINESS, or IGNORE
---

# /email-classify — Classify Email

<trl>
DEFINE "email-classify" AS FUNCTION primitive.
FUNCTION email-classify SHALL REQUIRE RECORD email.
FUNCTION email-classify SHALL RESPOND 'with RECORD tier AND RECORD reason AND RECORD template.
RECORD tier 'is "POLITE" OR "BUSINESS" OR "IGNORE".
IF RECORD tier EQUALS "POLITE" THEN FUNCTION email-classify SHALL RESPOND 'with RECORD template.
IF RECORD tier EQUALS "BUSINESS" THEN FUNCTION email-classify SHALL RESPOND 'with RECORD reason.
</trl>

Given an email (from `/email-read`), classify into one tier:

**POLITE** — needs acknowledgment, not substance:
- General inquiries, meeting requests, thank-yous, introductions
- Information requests needing research before answering
- Any email where "received, will follow up" is appropriate

**BUSINESS** — involves decisions, commitments, money, or technical substance:
- Pricing, contracts, legal, technical questions
- Client complaints, partnership proposals
- First contact from unknown important person
- Any email where the response could create a commitment

**IGNORE** — no response needed:
- Marketing, automated notifications, spam, mailing lists

When in doubt, classify as BUSINESS.

```
Classification: [TIER]
Reason: WHY
Template: TEMPLATE_NAME (if POLITE)
```
