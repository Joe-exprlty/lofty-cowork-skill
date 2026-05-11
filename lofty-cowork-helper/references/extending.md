# Extending the Skill

The starter client covers leads, notes, and activities. This file documents how to add capability beyond that, and how to overcome the most common limitations.

Read this when the user asks for something the starter doesn't do, or when you need to explain why a capability requires extra setup.

---

## Capability ladder

The starter ships with most of what a working day needs. As of v1.4.0, almost every documented Lofty surface is covered.

1. **Lead read/write (starter)** - `search_leads`, `get_lead`, `get_lead_activities`, `create_lead`, `update_lead`, `create_note`, `get_notes`, `update_note`, `delete_note`. Day-one operating capability.

2. **MLS search (starter)** - `search_listings` with full filter syntax (city, price, beds, baths, sqft, property type, status). Needed for "show me 3-bed condos under $650k in NW Portland."

3. **Communication (starter)** - `send_email`, `send_sms`. Plus history pulls: `get_call_history`, `get_email_history`, `get_text_history`. Sends are gated by SKILL.md's confirm-before-send rule; reads are unrestricted.

4. **Tasks and calendar (starter)** - `create_task`, `get_tasks`, `update_task`, `complete_task`, `uncomplete_task`, `delete_task`, `get_available_meeting_slots`. Full lifecycle.

5. **Unified timeline (starter, v1.4.0)** - `get_system_logs(lead_id)` returns the human-readable timeline (calls, emails, texts, notes, stage transitions, manual logs) in chronological order. Reach for this BEFORE assembling per-channel pulls when Claude is asked "what's been happening with Jane lately?"

6. **Activity & alerts (starter, v1.4.0)** - `add_lead_activity` (manual log entry), `get_alerts` (saved searches the lead subscribes to), `get_transactions`, `create_transaction`.

7. **Team & schema introspection (starter, v1.4.0)** - `get_organization`, `get_members`, `get_tags`, `get_custom_fields`, `get_lead_ponds`. Use these to discover what your team has configured before reading or writing custom fields.

8. **Leads index (starter, v1.3.0)** - `find_client` reads from `data/leads_index.json` (built by `scripts/refresh_leads_index.py`), or from a Cloudflare Worker once you've deployed one. v1.4 expanded the normalizer to capture buyer/seller intent, DNC flags, pond context, and the lead's `leadPropertyList` so Claude can answer richer questions without a per-match `get_lead` round-trip.

9. **Showings (starter, v1.3.0)** - `prepare_showing`, `find_listing_by_address`, `cancel_showing`, `list_pending_showings`, plus sub-helpers (`build_jotform_url`, `shorten_url`, `enqueue_showing_sms`, `build_showing_invite`). The biggest day-to-day workflow once leads work.

10. **Buyer preferences (starter, v1.3.0)** - `get_buyer_preferences` reads the D1-backed showing-feedback rollup once you've deployed the jotform-to-lofty Worker.

11. **Webhooks (starter)** - `get_webhooks`, `create_webhook`, `delete_webhook`. Subscribe Lofty to push events to your Workers. Powers the live leads index, post-showing flows, and "notify me when X" automation.

12. **Cloudflare Workers (still optional)** - leads-index, short-links, jotform-to-lofty, showing-sms. The Python in the starter calls them when their URLs are present in `.env` and fails soft when blank.

Things deliberately left OUT of the starter:
- `delete_lead` - too dangerous to expose without strict guards. Use Lofty's UI.
- `get_lead_analysis`, `generate_call_script` - the AI endpoints are broken in 2026 (return 500 / 400). Skip until Lofty fixes them.
- Native showings or feedbacks endpoints - Lofty has no REST surface for these. The Phase 2 Workers + Jotform + D1 architecture fills the gap.

---

## Leads index (built into the starter as of v1.3.0)

Why it exists: `/v1.0/leads` silently ignores `keyword` (quirk #2). Without an index, `find_client` can only see the 25 most recently created leads. The starter solves this with a leads index that has two backends. Same `find_client(name)` API; different source under the hood.

### Backend A: local file (default)

The starter's `_load_leads_index_from_file` reads `data/leads_index.json`. Build it with:

```bash
python3 scripts/refresh_leads_index.py
```

The script paginates `/v1.0/leads` with scrollId and writes the file atomically. Re-run it periodically:

- Casual use: every couple of weeks.
- Active prospecting (lots of new leads): weekly.

Run from your real terminal, not Cowork's bash tool (45-second timeout would cap this at ~6 API calls; the full scan takes ~3 minutes for 650 leads).

The starter prints a (non-blocking) staleness warning when the file is older than `LOFTY_LEADS_INDEX_STALENESS_DAYS` (default 14).

### Backend B: Cloudflare Worker fed by webhook list 2 (live, no refresh)

Deploy a small Cloudflare Worker that subscribes to webhook list 2 (Lead Info events). Every lead create/update/delete posts to the Worker, which patches its KV store. The Worker exposes `/export` that the Python client reads.

Sketch of the Worker (JavaScript):

```javascript
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname.startsWith("/webhook/")) {
      // Verify path secret matches env.WEBHOOK_SECRET
      const body = await request.json();
      const leadId = String(body.leadId);
      // Fetch the lead from Lofty using env.LOFTY_API_KEY, store in KV
      const lead = await fetchLeadFromLofty(leadId, env);
      await env.LEADS_KV.put(leadId, JSON.stringify(lead));
      return new Response("OK");
    }
    if (url.pathname === "/export") {
      // Bearer auth using env.EXPORT_API_KEY
      const all = await env.LEADS_KV.list();
      // Build the export and return JSON
    }
    return new Response("Not Found", { status: 404 });
  }
}
```

Deploy with `wrangler deploy`. Configure two secrets: `LOFTY_API_KEY` and `EXPORT_API_KEY`. Subscribe Lofty:

```python
api.create_webhook(list_id=2, url="https://leads-index.<your-subdomain>.workers.dev/webhook/<secret>")
```

In `.env`:
```
LOFTY_LEADS_INDEX_SOURCE=worker
LEADS_INDEX_WORKER_URL=https://leads-index.<your-subdomain>.workers.dev
LEADS_INDEX_EXPORT_API_KEY=<your-bearer-token>
```

The Python client reads from `/export` instead of the local file. Lofty's webhook delivery SLA is 1 to 5 minutes, so the index is effectively live.

Cost: free tier Workers + KV is plenty for typical real estate volume.

---

## Showing scheduling (built into the starter as of v1.3.0)

Showings are the highest-leverage workflow. The kit ships an orchestration sub-skill at `skills/schedule-showing/SKILL.md` that wires every step below together. Trigger phrases like "schedule a showing at," "book a tour for," or "set up [client] at [address] at [time]" route directly into it. The notes below are for users who want to compose the primitives themselves, or who are debugging a partial run.

As of v1.3.0 the full helper ships with the starter. `prepare_showing` is a DRY-RUN: it builds payloads and queues the post-showing SMS, but it does NOT create the calendar event, post the Lofty note, or send the buyer email. The calling skill (or you, in your own code) is responsible for those side-effects, in this order:

1. Call `prepare_showing(full_address, start_datetime_iso, client_name=...)` to assemble payloads.
2. Create the calendar event yourself via your provider (Google Calendar MCP at v1; see `references/calendar_routing.md` for alternatives).
3. ONLY after the calendar event is confirmed, call `api.create_note(lead_id, showing_note_content)` to write the showing-log note. (Earlier versions wrote the note first; when the calendar step failed downstream, the note lied. The order here matters.)

`prepare_showing` accepts either `client_name=` (resolved via `find_client`) or `lead_id=` (resolved against the local leads index). Use `lead_id=` when two leads share a name or phone, so the caller can pin the exact record instead of getting a multiple-clients error.

Return shape on success:

```python
{
    "listing": {...},                     # slim MLS listing dict
    "client": {...},                      # slim client dict
    "jotform_url": "https://...",         # short link if available, long otherwise
    "calendar_invite": {
        "subject": "Home Showing: ...",
        "description_html": "...",
        "description_text": "...",
        "location": "STREET, CITY, STATE ZIP",
        "start_iso": "2026-05-15T14:00:00-07:00",
        "end_iso":   "2026-05-15T14:30:00-07:00",
        "attendee_email": "buyer@example.com",
        "calendar": "owner@example.com",  # from OWNER_EMAIL in .env
    },
    "showing_note_content": "=== SHOWING LOG ===\n...",  # paste into create_note
    "sms_queue": {...},                   # showing-sms Worker response, or None
    "sms_showing_key": "12345:11513-sw-bambi-ln",
}
```

Failure shapes:

- `{"error": "<message>"}` for missing args, listing miss, or invalid datetime.
- `{"error": "Multiple clients match. Pass lead_id= to pin one:", "candidates": [...]}` when `client_name=` resolves to more than one lead.

The five Phase 2 sub-helpers each work standalone too, in case you want to compose them differently:

- `find_listing_by_address(full_address)` - Active-only MLS lookup.
- `find_client(name, exclude_stages=[...])` - leads-index name search.
- `build_jotform_url(lead_id, ..., shorten=True)` - prefilled feedback form URL.
- `shorten_url(long_url, prefix="b")` - branded short link, falls through to long URL.
- `build_showing_invite(client_first_name, listing, start_dt, end_dt, jotform_url)` - returns subject + HTML + text + location.
- `enqueue_showing_sms(lead_id, send_at_iso, short_url, property_short_address, ...)` - POST to the showing-sms Worker. Best-effort; returns None on failure.
- `_showing_key_and_short(lead_id, listing, full_address)` - the slug builder. Both prepare and cancel use this so they cannot drift.

To cancel a queued showing (e.g. buyer reschedules):

```python
result = api.cancel_showing(lead_id, full_address)
# Returns one of:
# {"status": "cancelled", "showing_key": "...", "worker_response": {...}, "cancelled_entry": {...}}
# {"error": "no_match", "message": "...", "pending": [...]}
# {"error": "multiple_matches", "candidates": [...], "message": "..."}
```

`cancel_showing` does loose case-insensitive substring matching on the address against the queue's `property_short_address`, so the user doesn't have to type the exact format that was queued. If two queued showings match, the function returns `multiple_matches` with the candidates and you call `cancel_showing_by_key(showing_key)` directly.

To read aggregated buyer feedback after a series of showings:

```python
prefs = api.get_buyer_preferences(lead_id)
# {
#   "status": "ok",
#   "total_showings": 4,
#   "loved": [{"tag": "yard", "count": 3}, ...],
#   "dealbreakers": [{"tag": "street noise", "count": 2}, ...],
#   "average_ratings": {"first_reaction": 4.0, "daily_life_fit": 3.5, ...}
# }
```

`get_buyer_preferences` hits the jotform-to-lofty Worker's `/preferences/<leadId>` endpoint, which queries the `showing_feedback` D1 database. Use it to pre-fill calendar invite descriptions ("based on your last 4 showings, you've loved yards but flagged street noise"), build artifacts, or sanity-check how a new property compares to the buyer's signal.

---

## Adding MLS search

As of v1.2.0 `search_listings` ships with the starter. The actual body shape, verified live in May 2026:

```python
def search_listings(self, filter_conditions=None, sort_fields=None,
                    page=1, page_size=25, sold=False, scope="all"):
    return self._request("POST", "/v2.0/listings/search", body={
        "searchScope": scope,
        "soldFlag": sold,
        "filterConditions": filter_conditions or {},
        "sortFields": sort_fields or ["MLS_LIST_DATE_L_DESC"],
        "pageNum": page,
        "pageSize": page_size,
    })
```

Body key gotchas (Lofty quirk #15). Sending the obvious names returns HTTP 200 with zero results and no error, so the bug is silent:

- `searchScope`, not `scope`
- `soldFlag`, not `sold`
- `filterConditions`, not `filter`
- `sortFields`, not `sort`
- `pageNum`, not `page`

Filter conditions (nested under `filterConditions`):

- Range fields use comma-separated min,max: `"price": "400000,650000"`, `"beds": "3,"`, `"sqft": ",2500"`.
- Multi-value fields use lists: `"propertyType": ["Single Family", "Condo"]`.
- Location uses nested object: `{"location": {"city": ["Portland"], "zipCode": ["97225"]}}`.
- Status filter: `"listingStatus": ["Active"]`.

Sort options: `PRICE_DESC`, `PRICE_ASC`, `MLS_LIST_DATE_L_DESC`.

Scope: `"all"` (full MLS), `"my"` (your listings), `"office"` (your office).

Response shape (Lofty quirk #16): results land under `"listing"` (singular), not `"listings"`. Total count lives at `response["metadata"]["total"]`.

```python
resp = api.search_listings(filter_conditions={...})
items = resp.get("listing") or []
total = (resp.get("metadata") or {}).get("total")
```

The `/v1.0/listing` endpoint exists but does not work with personal API key auth (quirk #10). Always use this `/v2.0/listings/search` with `scope="my"` instead.

---

## `find_listing_by_address` (built into the starter as of v1.3.0)

Lofty's listing search does NOT support keyword or street-address filters. The starter's reliable approach:

1. Parse the zip from the full address (last 5-digit number).
2. Search `{"location": {"zipCode": [zip]}, "listingStatus": ["Active"]}` with `pageSize=100`.
3. Paginate up to 10 pages within the zip and filter client-side by uppercase street-address substring (in either direction, so `"11513 SW BAMBI LN"` matches both `"11513 SW BAMBI LN"` and `"11513 SW Bambi Ln"`).
4. Return the slim listing dict on hit, structured error on miss.

Active only by design. Don't fall through to Pending or Sold; that masks typos. If the user types a wrong zip, the function says so directly so you can confirm with them and retry.

The slim listing dict the helper returns maps Lofty's response keys to friendlier names. Watch for these renames if you write your own caller:

- `bedrooms` → `beds`
- `bathrooms` → `baths`
- `id` → `loftyListingId`

Other keys pass through unchanged: `address`, `streetAddress`, `city`, `state`, `zipCode`, `price`, `sqft`, `propertyType`, `mlsListingId`, `listingStatus`, `siteDetailLink`, `mlsOrgId`.

The `siteDetailLink` field is the agent's IDX site URL (e.g., `<your-domain>.com/listings/...`). Use it in calendar invites and showing-log notes.

## The slim client dict shape

Both `find_client` and `_client_dict_from_index` return the same slim client dict:

```python
{
    "leadId": 12345,
    "firstName": "Jane",
    "lastName": "Smith",
    "email": "jane@example.com",   # first email if multiple
    "phone": "5035551212",          # first phone if multiple
    "stage": "New Lead",
    "score": 50,
}
```

If you need the full lead record (more fields, all emails, all phones), call `api.get_lead(leadId)` separately. The slim dict is what `prepare_showing` consumes, since that's all the showing flow needs.

---

## Tasks, email, SMS (built into the starter as of v1.2.0)

These are now part of the starter's `LoftyAPI`. The endpoints, with the body shapes that actually work (verified live, May 2026):

**Tasks:** `POST /v2.0/calendar` to create, `POST /v2.0/calendar/<id>/finish` to complete, `PUT /v2.0/calendar/<id>` to update, `DELETE /v2.0/calendar/<id>` to delete, `GET /v2.0/calendar` to list. `update_task`, `complete_task`, and `delete_task` are not in the v1.2.0 starter yet; add them when needed using the same `_request` plumbing.

The create body (Lofty quirk #17):

```python
{
    "type": "TASK",                       # or "APPOINTMENT" (NOT for showings)
    "content": "Call back about pre-approval",
    "leadId": 12345,                      # number, not string
    "startAt": "2026-05-08T14:00:00-07:00",
    "endAt": "2026-05-08T14:30:00-07:00",
    "timeZoneCode": "America/Los_Angeles",  # required
    "taskWay": "Call",                    # NOT "way". Values: Call, Email, Text, Meeting, Other
    "assignedRole": "Agent",              # optional. Values: Agent, Assistant. NOT "ASSIGNED"
    "address": "..."                      # optional, for APPOINTMENT only
}
```

If you send `"way"` instead of `"taskWay"`, or use `"ASSIGNED"` as the role, Lofty returns error code 20012 "Invalid parameter" with no hint about which key is wrong.

**Email:** `POST /v1.0/message/email/send` with `{"leadId", "subject", "content"}`. Content supports HTML.

**SMS:** `POST /v1.0/message/sms/send` with `{"leadId", "content"}`.

For Email and SMS: ALWAYS confirm content with the user before sending. This is non-negotiable. The send endpoints return success even when the user wishes they hadn't.

---

## The four Cloudflare Workers

These are the optional automations. Each is a small JavaScript file. Deploy via the Cloudflare dashboard (paste the code) or `wrangler deploy` (CLI).

| Worker | Purpose | Deploy method | Cost |
|---|---|---|---|
| `leads-index` | Live leads index, fed by webhook list 2 | Dashboard or wrangler | Free |
| `short-links` | Branded short-link redirector | Dashboard or wrangler | Free |
| `jotform-to-lofty` | Bridge from Jotform feedback → Lofty note + email + D1 | Wrangler | Free (D1 free tier is generous) |
| `showing-sms` | 2-hour pre-showing SMS using Durable Object alarms | Wrangler ONLY (uses DOs) | $5/month (Workers Paid) |

`showing-sms` is the only one that requires the paid plan. The other three run on free tier indefinitely for typical real estate volume.

For each Worker, the user needs:
- A Cloudflare account
- (For wrangler deploys) `npm install -g wrangler` and a Cloudflare API token
- The Worker code (the user can adapt the patterns from the source descriptions in the full guide)

Skip all of this until the user actually needs one of the capabilities. Start with leads-index because it removes the manual refresh; add showing-sms when they start scheduling many showings; add jotform-to-lofty when they want post-showing feedback automation; add short-links when they want branded URLs.

---

## Subscribing to webhooks

After deploying a Worker that wants events:

```python
api.create_webhook(list_id=<N>, url="<your-worker-url>")
```

The 12 webhook event types are listed in `quirks.md`. The most useful:

- List 2 (Lead Info) - feeds the leads index
- List 3 (Lead Activity) - for "notify me when a lead browses or favorites" workflows. Note: pings only, you must call back to enrich (quirk #13)
- Lists 7, 8, 9 (Email, Text, Note) - for tracking team activity. Fire on manual + logged events only, NOT on automated sequence sends.

If `eventCount` on a Worker stops ticking up over a day, the subscription has dropped. Re-subscribe with the same `create_webhook` call. The user's `/stats` endpoint on each Worker should expose this.

---

## Building beyond Lofty

The same Cowork + skill pattern works for other CRMs and tools. To extend this skill into a multi-CRM helper, or to fork it for a different CRM:

1. Use `lofty_api.py` as a model. Replace base URL, auth header, and quirks with the new system's.
2. Document the new system's quirks the same way (`references/quirks.md` shape).
3. Mirror the workflows recipe structure.
4. Update `SKILL.md` triggers so it activates on the new system's name.

Real estate-adjacent systems where this skill pattern would also work: Follow Up Boss (REST API, OAuth), kvCORE (REST API, less documented), Real Geeks (REST API), Sierra Interactive (REST API). Each has its own quirk landscape.

---

## When NOT to extend

Some things look like they should be in this skill but really shouldn't be:

- **Lead scoring algorithms.** Build those as a separate skill or a Python script in the workspace; don't pollute the Lofty skill.
- **Document generation (CMA, BPO, listing agreements).** Those are their own workflows. Use the docx, pptx, or pdf skills instead.
- **MLS data analytics.** If the user wants to track market trends, that is a market-tracker skill. Different concerns.
- **Marketing automation.** Email sequences, drip campaigns, lead nurture. Lofty has its own UI for that; the API is not the right tool.

Keep this skill focused on operating the Lofty CRM through its API. When the user asks for something adjacent, suggest the right skill or workflow instead of trying to bolt it on here.
