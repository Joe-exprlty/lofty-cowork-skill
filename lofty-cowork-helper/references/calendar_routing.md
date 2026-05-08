# Calendar Routing

How Claude routes calendar events to the right backend based on the agent's setup choice. Read this whenever a workflow needs to put a showing, follow-up, or appointment on the agent's calendar.

The agent picks ONE provider at setup. The choice is stored in `CLAUDE.md` as `CALENDAR_PROVIDER`. Four valid values:

- `google`
- `outlook`
- `lofty`
- `skip`

Always read the value before creating an event. Never assume.

---

## The two flows for every showing

A showing produces two separate calendar artifacts:

1. **Agent's internal reminder.** Goes on the agent's chosen calendar. Just for them.
2. **Buyer-facing invite.** A polished invite the buyer can click. Always delivered by email; sometimes by SMS as a maps link.

These flows are independent. The agent's `CALENDAR_PROVIDER` choice ONLY affects flow 1. Flow 2 (buyer invite) is handled the same way regardless, with a small twist: when the agent is on Google or Outlook, the calendar provider's native attendee-invite already emails the buyer, so we skip the separate `.ics` send to avoid duplicates.

A showing also always produces a third artifact: the **Lofty showing-log note** via `api.create_note(lead_id, ...)`. That happens regardless of `CALENDAR_PROVIDER`, including `skip`.

---

## Provider: google

Use the Google Calendar MCP (`mcp__a3caf83a-55c5-4144-a996-303f3d83e660__create_event`).

Required params:

- `summary`: e.g. "Showing: 1234 Main St with Jane Smith"
- `startTime`: ISO 8601, e.g. `2026-05-15T14:00:00-07:00`
- `endTime`: ISO 8601, 30 minutes after start by default

Recommended params:

- `description`: HTML allowed. Include property details (price, beds/baths/sqft), the buyer's contact info, the prefilled feedback form URL, and the agent signature.
- `location`: Full street address (`1234 Main St, Portland, OR 97214`). Google geocodes this for the calendar's map link.
- `timeZone`: `America/Los_Angeles` (or whatever the agent has in `CLAUDE.md`).
- `attendeeEmails`: `[lead.email]` if the lead has an email.
- `notificationLevel`: `EXTERNAL_ONLY` so Google emails the buyer the invite but doesn't ping the agent (the agent already knows about the showing). If the agent doesn't want to send the buyer an invite at all, use `NONE`.
- `overrideReminders`: `[{"method": "popup", "minutes": 120}, {"method": "popup", "minutes": 30}]` for the 2-hour and 30-minute pre-showing nudges.

Buyer-invite handling: Google sends the polished invite when `attendeeEmails` is set and `notificationLevel` is `EXTERNAL_ONLY` or `ALL`. Do NOT also call `ics_builder.build_ics(...)` or send a separate Lofty email; the buyer would get duplicates. If the lead has no email, fall through to SMS-only with a Google Maps link.

---

## Provider: outlook

Beta in v1 of Phase 2. Use the Microsoft 365 connector's calendar tools. Verify the exact tool names in the agent's installed connector before relying on this path.

Plan: same conceptual flow as Google. The M365 connector drafts an Outlook appointment with attendees; the user reviews and sends from Outlook's native form. Buyer gets the invite from Outlook directly, so we skip the separate `.ics` send.

If the connector isn't installed, the skill should refuse to set `CALENDAR_PROVIDER=outlook` and ask the agent to install it first or pick a different provider.

Until validated end-to-end, treat this provider as beta and verify behavior in your own account before relying on it for client-facing work.

---

## Provider: lofty

Use the v1.2.0 Python method `api.create_task(...)` from `lofty_api.py`.

Mapping:

```python
api.create_task(
    lead_id=<lead.id>,
    content=f"Showing: {listing.streetAddress} with {lead.firstName}",
    start_at=<ISO start>,
    end_at=<ISO end>,
    task_way="Meeting",
    # task_type defaults to "TASK". Do NOT use "APPOINTMENT" here, even
    # though Lofty exposes it. Appointment type triggers listing-agent
    # approval workflow which is wrong for buyer-side showings.
)
```

Limitations the agent should know about (warned at setup):

- No HTML in the reminder. Just the content string.
- No map link.
- No buyer-as-attendee. Lofty's calendar is for the AGENT only.
- No native invite to the buyer.

Buyer-invite handling: because Lofty doesn't email the buyer, ALWAYS run the buyer flow:

1. Build the invite with `ics_builder.build_ics(...)`.
2. Send the buyer an email via `api.send_email(lead_id, subject, content)` with the `.ics` text included as part of the message body or as an attachment (see ics_builder docstring for both patterns).
3. Optionally send an SMS via `api.send_sms(lead_id, content)` with a Google Maps link to the property.

---

## Provider: skip

No calendar event is created at all. Use this when the agent manages their schedule somewhere outside any of the supported providers and just wants Claude to handle the lead-side artifacts.

Behavior:

- No `create_event` call. No `create_task` call.
- ALWAYS still write the Lofty showing-log note via `api.create_note(...)`.
- ALWAYS still run the buyer-invite flow (`ics_builder.build_ics` + `api.send_email` with `.ics`, optional SMS with maps link).

The agent's lead history stays accurate even though the calendar reminder is on them.

---

## The buyer-invite flow (for lofty and skip paths)

```python
from ics_builder import build_ics

ics_text = build_ics(
    uid=f"showing-{lead_id}-{int(start_at.timestamp())}@<your-domain>",
    summary=f"Showing: {listing.streetAddress}",
    description=invite_description_html,   # property details + agent contact
    location=f"{listing.streetAddress}, {listing.city}, {listing.state} {listing.zip}",
    start_iso=start_at_iso,
    end_iso=end_at_iso,
    organizer_name=agent.full_name,
    organizer_email=agent.email,
    attendee_name=lead.full_name,
    attendee_email=lead.email,
)

# Email the buyer
api.send_email(
    lead_id=lead.id,
    subject=f"Showing confirmed: {listing.streetAddress}",
    content=email_html_body_with_ics_attached_or_inlined,
)

# Optional SMS with maps link
api.send_sms(
    lead_id=lead.id,
    content=f"Confirmed: {listing.streetAddress} at {time_local}. Map: https://maps.google.com/?q={url_encoded_address}. - {agent.first_name}",
)
```

The `ics_builder.build_ics` returns a multi-line iCal string. To attach it to a Lofty email, base64-encode it and reference it as a `text/calendar` MIME attachment (the wrapper around `api.send_email` may need an `attachments` field added in a future version; for v1, inline the `.ics` content into the email body in a fenced code block and tell the user "save this block as showing.ics").

---

## When the agent has no email or no phone for the lead

Lofty leads can have either email or phone or both. Before running the buyer flow, check what's available.

- Email present: send the polished email, skip SMS unless the agent says otherwise.
- Email missing, phone present: send SMS only with the maps link and the time. Skip the `.ics`.
- Both missing: write the Lofty note as usual but flag the lead in the note: "No reachable contact info for buyer; remember to confirm in person."

Never invent contact info. Never use the agent's own contact for the buyer slot.

---

## Setup-time validation

When the agent picks `CALENDAR_PROVIDER` at setup:

- `google`: verify the Google Calendar MCP is installed (Cowork's Google Calendar tools should be visible). If not, tell the agent to install it before continuing.
- `outlook`: verify the Microsoft 365 connector is installed. If not, tell the agent to install it or pick a different provider.
- `lofty`: no extra check. Always available.
- `skip`: no extra check.

If the chosen provider's tools aren't reachable at runtime, fall back to writing the Lofty note and tell the agent calmly: "I couldn't reach your calendar provider, so I logged the showing in Lofty and didn't create an event. Want me to retry, switch providers, or skip the calendar entry for this one?"
