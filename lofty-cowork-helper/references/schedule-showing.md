---
name: schedule-showing
description: Schedule one or more home showings end-to-end for an existing Lofty client. Use whenever the user says "schedule a showing", "book a showing", "set up a tour", "schedule [address] for [time]", "tour [address] tomorrow", or any variation of putting a confirmed showing on the agent's calendar for an existing Lofty client. Also trigger when the user gives a client name and one or more addresses with times, even when phrased casually like "set Jane up at [address] at 4:30 then [address] at 5:00". This skill MUST be used because it pins the right Lofty lead when names collide, runs prepare_showing once per stop, creates calendar events with feedback links, posts showing notes, and verifies the post-showing SMS got queued. Without it the workflow takes 4x longer and the note ordering bug leaves notes that lie about whether the calendar invite was actually sent.
---

# Schedule a Showing

## Purpose

Agents who run buyer tours often book multiple showings back-to-back. This skill turns "schedule Jane at 1234 NW Main at 4:30 then 1500 NW Oak at 5:00 tomorrow" into a clean run that:

1. Pins the right Lofty lead (handles duplicates automatically)
2. Looks up each MLS listing
3. Queues the post-showing feedback SMS (only if the Tier 3 SMS Worker is deployed)
4. Creates the calendar event with the feedback link baked in
5. Posts a SHOWING LOG note on the lead with the calendar event ID appended
6. Verifies the SMS queue landed

The skill ALWAYS uses the `prepare_showing(lead_id=...)` path so name collisions never block the run.

## When to use this

The user is scheduling one or more confirmed showings for an existing Lofty client. Typical triggers:

1. "Schedule Jane Smith for tomorrow at 4:30 at 1234 NW Main Portland"
2. "Book a showing with the Smiths Saturday 10am at [address]"
3. Multi-stop tour: client name + 2 to 4 addresses with times
4. Reschedule (same workflow, the SMS queue upserts on the same showing_key)

Do NOT use this skill for:

- A first showing with a brand-new buyer who has not had a buyer consult. That is a different workflow (the buyer-consult helpers, not orchestration).
- Scheduling internal tasks, calendar blocks, or non-showing appointments.

## Inputs to collect

Before doing any work, confirm these. If anything is missing, ask via `AskUserQuestion` in a SINGLE batched prompt, not one question at a time.

1. **Client name** (or partial name). Always passes through `find_client` to resolve.
2. **Each address** in the format `STREET, CITY, STATE ZIP`. The user typically gives short form like "1234 NW Main St Portland", reformat before passing to the API.
3. **Each start time**. Usually relative ("tomorrow at 4:30"). Convert to ISO 8601 with the agent's timezone offset (read the timezone from the workspace `CLAUDE.md`, e.g. `America/Los_Angeles` resolves to `-07:00` in DST and `-08:00` outside).
4. **Showing duration**. Default 30 min unless the user says otherwise.

If the user gives a string of addresses with times (multi-stop), parse them in order and treat the gap between stops as travel time the user already accepted. Do NOT add buffer or change times unless the user asks.

## Prerequisites

Check before starting. If anything is missing, surface it before the run, not mid-run.

1. `LOFTY_API_KEY` in `.env` (the Python client errors clearly if missing).
2. The showing helpers are present in `scripts/lofty_api.py` (`prepare_showing`, `find_client`, `find_listing_by_address`). They ship in the v1.3.0+ starter; no extension needed.
3. Local leads index at `data/leads_index.json`. If `find_client` errors with a setup message, run `python3 scripts/refresh_leads_index.py` first.
4. Calendar backend matches `CALENDAR_PROVIDER` in `CLAUDE.md`. For `google`, the Google Calendar MCP must be connected. For `outlook`, the Microsoft 365 connector. For `lofty` or `skip`, no external MCP needed.
5. **Tier 3 SMS Worker (optional but recommended).** If `SHOWING_SMS_WORKER_URL` is set in `.env`, `prepare_showing` queues the post-showing feedback SMS. Without it, the rest of the flow still works but Step 7 will report no queue entries.

## The workflow

Run these steps in order.

### Step 1: Resolve the client (ONCE, even for multi-stop)

Call `find_client(name)` once at the start. Three outcomes:

1. **Single match**, capture `leadId`, move on.
2. **Multiple candidates**, present them via `AskUserQuestion` and capture the chosen `leadId`. Same client across all stops, do not re-ask per address.
3. **None**, tell the user "No Lofty lead found for X" and stop. Do NOT create a new lead.

Stage filter: exclude DNC, Archived, Agents / Vendors. The agent's own record is auto-excluded via the `<your last name in lowercase>` value in `CLAUDE.md`.

### Step 2: Convert times to ISO 8601 with offset

For each stop, build `start_datetime_iso` as `YYYY-MM-DDTHH:MM:SS±HH:MM` using the agent's timezone from `CLAUDE.md`. Today's date and the user's relative time anchor this. Examples (assuming `America/Los_Angeles`):

- "tomorrow at 4:30" on 2026-05-06 PDT becomes `2026-05-07T16:30:00-07:00`
- "Saturday at 10am", resolve the next Saturday in PDT or PST as appropriate
- "next Tuesday 2:15pm", resolve the date

If the offset is ambiguous (around DST boundary), use the IANA timezone name (e.g. `America/Los_Angeles`) in the calendar event `timeZone` field and let the calendar provider handle it. The ISO offset still has to be valid, so look at the date.

### Step 3: Run prepare_showing for each stop

For each address, call:

```python
api.prepare_showing(
    full_address="STREET, CITY, STATE ZIP",
    start_datetime_iso="2026-05-07T16:30:00-07:00",
    lead_id=<resolved_lead_id>,
    duration_min=30,
)
```

ALWAYS pass `lead_id=`, not `client_name=`. This is the whole point of this skill: it bypasses the name-collision failure mode.

Capture the returned `listing`, `jotform_url`, `calendar_invite`, `showing_note_content`, `sms_queue`, `sms_showing_key`. The SMS is enqueued as a side effect of this call (only if Tier 3 is deployed).

If the result has `error`:

- `Could not find MLS listing`, the address does not match an Active listing. Confirm the address (often a wrong city or zip) with the user and retry. Do not proceed to calendar.
- `No lead with id ...`, the lead is not in the local index. Run `refresh_leads_index.py` and retry.
- Anything else, surface and stop.

### Step 4: Confirm calendar invite handling (BATCHED, ONCE)

Before creating any calendar events, confirm with `AskUserQuestion` in a single prompt how the invite should be handled. Default option (recommended): invite the client at the email returned by `prepare_showing`. Alternative: skip attendee, calendar-only.

If the user has previously answered this in the same conversation, do NOT re-ask.

### Step 5: Create calendar events (parallel where possible)

Read `CALENDAR_PROVIDER` from `CLAUDE.md` and route to the right backend (full routing rules in `references/calendar_routing.md`).

For each stop, call the appropriate calendar tool with:

- `summary`: `Home Showing: <full_address>`
- `startTime` / `endTime`: from the prepared invite
- `timeZone`: the agent's IANA timezone from `CLAUDE.md`
- `location`: full address
- `calendarId` (Google) or equivalent: the agent's email from `CLAUDE.md`
- `attendeeEmails`: `[<client_email>]` (if the user opted to invite the client)
- `notificationLevel`: `ALL` (only if attendee is included)
- `description`: the `description_html` from the prepared invite

Send all events in a single message with multiple tool calls so they fire in parallel.

Capture each event's `id` and `htmlLink` (or provider equivalent).

If `CALENDAR_PROVIDER` is `lofty` or `skip`, fall back to writing the buyer-facing .ics via `assets/ics_builder.py` and emailing it through `api.send_email`. The Lofty showing-log note still gets written in Step 6.

### Step 6: Post the showing note (with event ID appended)

For each stop, build the final note by appending the calendar event details to `showing_note_content`:

```
<showing_note_content from prepare_showing>
Calendar invite sent to: <client_email or "(no attendee)">
Calendar event: <htmlLink>
```

Then call `api.create_note(lead_id, final_note)`. Run all `create_note` calls in a single Python invocation to keep them under the 6.5s rate-limit pacing.

### Step 7: Verify SMS queue

If `SHOWING_SMS_WORKER_URL` is set in `.env`, call `api.list_pending_showings(lead_id)` once and confirm an entry exists for each `sms_showing_key` returned in Step 3. If any are missing, tell the user so they can investigate, do not silently retry.

If `SHOWING_SMS_WORKER_URL` is not set, skip this step. The Tier 3 SMS Worker is opt-in; running without it is supported.

### Step 8: Report results

Give the user a tight summary, one line per stop, including:

- Address, time, beds/baths/sqft/price
- Calendar event link
- A practical note if relevant (e.g., back-to-back stops with tight drive time)

Do NOT include emojis. Do NOT use em-dash characters; use commas, periods, or hyphens.

## Idempotency

Reschedules and re-runs are safe to a point:

- The SMS queue uses `<lead>:<address-slug>` as a stable key, so it upserts cleanly.
- Lofty notes do NOT dedupe; re-running creates duplicate notes. Before re-running for the same showing, ask whether to skip the note creation.
- Calendar events do NOT dedupe. Before re-running, ask whether to delete the prior event first or accept the duplicate.

## Common failures

- **"Multiple clients match. Pass lead_id= to pin one"**: This skill should never produce this error because Step 1 always resolves a single `leadId` first. If you see it, you skipped Step 1 or passed `client_name=` in Step 3 by mistake.
- **"Could not find MLS listing"**: Listing is off-market or the address has the wrong city or zip. Confirm with the user.
- **Calendar event creates but `attendeeEmails` not honored**: The calendar provider returns the event but the attendee may show `responseStatus: needsAction`. That is normal; the invite email is on its way.
- **`list_pending_showings` returns fewer entries than expected**: The Tier 3 Worker may be lagging. Wait a few seconds and re-call once.

## Reference: full prepare_showing return shape

```
{
  "listing": {address, streetAddress, city, state, zipCode, price, beds, baths,
              sqft, propertyType, mlsListingId, loftyListingId, listingStatus,
              siteDetailLink, mlsOrgId},
  "client":  {leadId, firstName, lastName, email, phone, stage, score},
  "jotform_url": "https://<short-links-domain-or-direct-jotform-url>/b/...",
  "calendar_invite": {subject, description_html, description_text, location,
                      start_iso, end_iso, attendee_email, calendar},
  "showing_note_content": "=== SHOWING LOG ===\n...",
  "sms_queue": {status, showing_key, kv_key},
  "sms_showing_key": "<lead>:<address-slug>",
}
```

The `jotform_url` is a direct Jotform link by default. If the optional short-links Worker is deployed, the prepared URL routes through it for branding.

## Safety rules (from CLAUDE.md, repeated for emphasis)

- CONFIRM with the user before sending any email or SMS, or deleting anything.
- Sign casual texts with the agent's first name only (from `CLAUDE.md`).
- No em-dash characters anywhere; use commas, periods, or hyphens.
- Exclude DNC, Archived, Agents / Vendors stages from lead searches.
- Never share API keys in chat.
