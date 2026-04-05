---
name: email-respond
description: Send a templated polite response with AI disclosure
---

# /email-respond — Send Polite Response

<trl>
DEFINE "email-respond" AS FUNCTION primitive.
FUNCTION email-respond SHALL REQUIRE RECORD uid AND RECORD template AND RECORD account.
FUNCTION email-respond SHALL READ RECORD email BY RECORD uid.
FUNCTION email-respond SHALL WRITE RECORD reply FROM RECORD template 'with RECORD variables.
FUNCTION email-respond SHALL SEND RECORD reply TO RECORD sender.
EACH RECORD reply SHALL CONTAIN RECORD ai_disclosure.
</trl>

Send a reply to an email using a named template. Every response MUST include the AI disclosure line.

### Templates

| Template | When |
|----------|------|
| ACKNOWLEDGE_INQUIRY | General questions |
| ACKNOWLEDGE_MEETING_REQUEST | Scheduling requests |
| ACKNOWLEDGE_INTRODUCTION | New introductions |
| ACKNOWLEDGE_THANK_YOU | Thank you / follow-ups |
| ACKNOWLEDGE_INFORMATION_REQUEST | Needs research first |
| ACKNOWLEDGE_FOLLOWUP | Follow-up messages |

### Template Structure

```
Subject: Re: {original_subject}

Dear {sender_name},

[Template body]

Best regards,
{business_name}

---
This email was composed and sent by an AI assistant on behalf of {owner_name}. [Context-specific note.]
```

### Variables

| Variable | Source |
|----------|--------|
| `{sender_name}` | Extracted from email From field |
| `{business_name}` | From account config |
| `{owner_name}` | From account config |
| `{original_subject}` | From email Subject header |

Call `email_reply(uid=UID, body=RENDERED_TEMPLATE)` to send.
