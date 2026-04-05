---
name: email-triage
description: Triage inbox — auto-respond polite emails, draft business emails for HITM review
---

# /email-triage — Inbox Triage (Compound Skill)

<trl>
DEFINE "email-triage" AS FUNCTION compound.
FUNCTION email-triage CONTAINS FUNCTION email-fetch THEN FUNCTION email-read THEN FUNCTION email-classify THEN FUNCTION email-respond THEN FUNCTION email-draft.
FUNCTION email-fetch SHALL READ ALL RECORD email 'where RECORD status EQUALS "unread".
FUNCTION email-read SHALL READ EACH RECORD email BY RECORD uid.
FUNCTION email-classify SHALL CLASSIFY EACH RECORD email AS RECORD tier.
RECORD hitm_gate SHALL REQUIRE PARTY human APPROVE EACH RECORD tier 'before CONTINUE.
IF RECORD tier EQUALS "POLITE" THEN FUNCTION email-respond SHALL EXECUTE.
IF RECORD tier EQUALS "BUSINESS" THEN FUNCTION email-draft SHALL EXECUTE.
IF RECORD tier EQUALS "IGNORE" THEN SKIP.
FUNCTION email-triage SHALL RESPOND 'with RECORD report TO PARTY human.
</trl>

**Primitives used:** email-fetch, email-read, email-classify, email-respond, email-draft

Triage unread emails across configured accounts. Classify each email, auto-respond to polite-tier, draft business-tier for human review.

## Setup

Requires the email MCP server running. Configure accounts in `~/.config/mcp/email_accounts.json`.

## Step 1: Fetch Unread

For each account, search for unread emails:

```
email_list(unread_only=true)
```

Present a summary:

```
## Inbox Triage

### Unread Emails
1. [ACCOUNT] From: NAME <email> — Subject: SUBJECT (DATE)
2. ...

Classifying...
```

## Step 2: Classify Each Email

Read each email with `email_read`. Classify into one of three tiers:

### Tier 1: POLITE (auto-send)
Emails that need a professional acknowledgment but no substantive response:
- General inquiries ("I'm interested in your product")
- Meeting requests ("Can we schedule a call?")
- Thank you / follow-up ("Thanks for sending that")
- Introduction emails ("I'd like to introduce...")
- Information requests that need research before answering
- Newsletter replies, event RSVPs
- Any email where the appropriate response is "received, will follow up"

### Tier 2: BUSINESS (draft for HITM)
Emails that involve decisions, commitments, money, or technical substance:
- Pricing questions or negotiations
- Contract / NDA / legal documents
- Technical questions about products
- Scope or deliverable discussions
- Client complaints or issues
- Partnership or collaboration proposals
- First contact from unknown important person
- Any email where the response could create a commitment

### Tier 3: IGNORE (skip)
- Marketing / promotional (should be filtered already)
- Automated notifications (GitHub, CI, billing receipts)
- Spam that got through
- Mailing list digests

Present classification:

```
### Classification
1. [POLITE] From: NAME — Subject: SUBJECT
   → Will auto-respond with: TEMPLATE_NAME
2. [BUSINESS] From: NAME — Subject: SUBJECT
   → Will draft for your review: REASON
3. [IGNORE] From: NAME — Subject: SUBJECT
   → Skipping: REASON

Proceed with auto-responses? (y/n/edit)
```

**HITM GATE:** Wait for approval before sending ANY auto-responses. The human can reclassify any email before proceeding.

## Step 3: Send Polite Responses

For each POLITE email, select the appropriate template and send via `email_send`.

**CRITICAL:** Every polite email MUST include the AI disclosure line.

### Templates

All templates follow this structure:
- Professional tone
- AI disclosure in closing
- Specific to the business context (match the account the email came to)

#### Template: ACKNOWLEDGE_INQUIRY
```
Subject: Re: {original_subject}

Dear {sender_name},

Thank you for reaching out. I have received your message and will review it promptly. You can expect a detailed response within one business day.

If this matter is time-sensitive, please reply to this email and it will be prioritized.

Best regards,
{business_name}

---
This email was composed and sent by an AI assistant on behalf of {owner_name}. A personal follow-up will be provided as needed.
```

#### Template: ACKNOWLEDGE_MEETING_REQUEST
```
Subject: Re: {original_subject}

Dear {sender_name},

Thank you for your interest in scheduling a meeting. I am reviewing the calendar for available times and will follow up shortly with proposed options.

If you have preferred dates or times, please share them and I will do my best to accommodate.

Best regards,
{business_name}

---
This email was composed and sent by an AI assistant on behalf of {owner_name}. Meeting confirmations will be sent with calendar invitations.
```

#### Template: ACKNOWLEDGE_INTRODUCTION
```
Subject: Re: {original_subject}

Dear {sender_name},

Thank you for the introduction. I appreciate you taking the time to connect. I will review the details and follow up with next steps.

Best regards,
{business_name}

---
This email was composed and sent by an AI assistant on behalf of {owner_name}. A personal follow-up will be provided as needed.
```

#### Template: ACKNOWLEDGE_THANK_YOU
```
Subject: Re: {original_subject}

Dear {sender_name},

Thank you for your message. I appreciate the follow-up and have noted the information.

Best regards,
{business_name}

---
This email was composed and sent by an AI assistant on behalf of {owner_name}.
```

#### Template: ACKNOWLEDGE_INFORMATION_REQUEST
```
Subject: Re: {original_subject}

Dear {sender_name},

Thank you for your inquiry. I am gathering the relevant information and will provide a comprehensive response within one business day.

If you have any additional context that would help me address your question more effectively, please do not hesitate to share.

Best regards,
{business_name}

---
This email was composed and sent by an AI assistant on behalf of {owner_name}. A detailed response will follow.
```

#### Template: ACKNOWLEDGE_FOLLOWUP
```
Subject: Re: {original_subject}

Dear {sender_name},

Thank you for following up. Your message has been received and is being reviewed. I will provide an update shortly.

Best regards,
{business_name}

---
This email was composed and sent by an AI assistant on behalf of {owner_name}.
```

### Template Variables

Configure these in your email accounts config:

| Variable | Description |
|----------|-------------|
| `{business_name}` | Your business or personal name |
| `{owner_name}` | The human behind the AI assistant |
| `{sender_name}` | Extracted from email From field |

## Step 4: Draft Business Responses

For each BUSINESS email, create a draft via `email_draft` with:
1. Context about what the email is about
2. Suggested response (best attempt)
3. Mark as needing review

Present to user:

```
### Business Drafts Created
1. Draft: Re: {subject} — From: {sender}
   Context: {why this needs human review}
   Draft summary: {1-line summary of proposed response}

Review drafts in your email client, edit as needed, then send manually.
```

## Step 5: Report

```
### Triage Complete
- Polite auto-responses sent: N
- Business drafts created: N
- Ignored: N
- Total processed: N
```

## Rules

1. **Never send a business-tier email automatically.** Always draft.
2. **Every auto-sent email includes the AI disclosure line.** No exceptions.
3. **When in doubt, classify as BUSINESS.** False positive (unnecessary draft) is better than false negative (auto-sent commitment).
4. **Use reply threading.** Always reply to keep conversation threads intact.
5. **Match the account.** Respond from the account the email was sent to. Never cross-brand.
6. **First contact from unknown sender = BUSINESS.** Even if the content looks polite, the first response to a new person should be human-reviewed.
