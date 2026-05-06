# Extending the Skill

The starter client covers leads, notes, and activities. This file documents how to add capability beyond that, and how to overcome the most common limitations.

Read this when the user asks for something the starter doesn't do, or when you need to explain why a capability requires extra setup.

---

## Capability ladder

Roughly in the order most agents add features:

1. **Starter (out of the box)** - leads (read), get_lead, activities, notes, tags, members, webhooks. Enough to answer "find a recent lead, log a note, see their activity."

2. **Leads index** - the workaround for `/v1.0/leads` keyword and sort being broken. After this, "find Jane Smith" works against the full database.

3. **Showings** - `prepare_showing`, `find_listing_by_address`, MLS lookup, calendar invite, post-showing SMS. The biggest day-to-day workflow once leads work.

4. **MLS search** - full filter syntax (city, price, beds, baths, sqft, property type). Needed for "show me 3-bed condos under $650k in NW Portland."

5. **Communication** - `send_email`, `send_sms`, plus history pulls. Use only with confirmation.

6. **Tasks and calendar** - `create_task`, `update_task`, `complete_task`. Useful for follow-ups.

7. **Webhooks** - subscribe Lofty to push events to your Workers. Powers the leads index, post-showing flows, and any "notify me when X" automation.

8. **Cloudflare Workers** - leads-index, short-links, jotform-to-lofty, showing-sms. Background automations.

Add features in roughly this order. Each layer builds on the one below.

---

## Adding a leads index (the most important upgrade)

Why: `/v1.0/leads` silently ignores `keyword` (quirk #2). Without an index, you cannot reliably search the full database by name.

Two options. Pick one.

### Option A: local file (simple, manual refresh)

Add a refresh script that paginates through `/v1.0/leads` and writes the result to `data/leads_index.json`.

Sketch:

```python
def refresh_leads_index(api, output_path):
    all_leads = []
    scroll_id = None
    while True:
        params = {"pageSize": 25}
        if scroll_id:
            params["scrollId"] = scroll_id
        resp = api._request("GET", "/v1.0/leads", query_params=params)
        leads = resp.get("leads", [])
        all_leads.extend(leads)
        scroll_id = resp.get("_metadata", {}).get("scrollId")
        if not scroll_id or not leads:
            break
    with open(output_path, "w") as f:
        json.dump({"leads": all_leads, "refreshedAt": time.time()}, f)
```

Then `find_client(name)` reads `data/leads_index.json` and filters in memory.

Refresh cadence: every couple of weeks for casual use, weekly for active prospecting. Run from a terminal, not Cowork bash (it would hit the 45s timeout).

Time cost: ~3 minutes for 650 leads at 6.5s rate-limit spacing.

### Option B: Cloudflare Worker fed by webhook list 2 (live, no refresh)

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

## Adding showing scheduling

Showings are the highest-leverage workflow. The full helper does five things in one call:

1. Look up the listing by full address (`find_listing_by_address`).
2. Look up the lead by name (`find_client`).
3. Build a prefilled buyer-feedback URL (Jotform or your form provider) and shorten it.
4. Build the calendar invite HTML and the showing-log note text.
5. Optionally enqueue a 2-hour-before-showing SMS via the `showing-sms` Worker.

Pseudocode:

```python
def prepare_showing(self, full_address, start_iso, client_name, duration_min=30):
    listing = self.find_listing_by_address(full_address)
    if listing.get("error"):
        return {"error": listing["error"], "message": listing["message"]}
    lead = self.find_client(client_name)
    if not lead:
        return {"error": "client_not_found", "message": f"No lead named {client_name}"}
    feedback_url = self.build_jotform_url(lead, listing)
    short_url = self.shorten_url(feedback_url)
    calendar_invite = build_calendar_invite_html(listing, lead, start_iso, duration_min)
    showing_note_content = build_showing_log_note(listing, start_iso)
    if SHOWING_SMS_BASE_URL:
        self.enqueue_showing_sms(lead["leadId"], start_iso, short_url, listing["streetAddress"])
    return {
        "listing": listing,
        "lead": lead,
        "jotform_url": feedback_url,
        "short_url": short_url,
        "calendar_invite": calendar_invite,
        "showing_note_content": showing_note_content,
    }
```

Each helper (`build_jotform_url`, `shorten_url`, `enqueue_showing_sms`) is its own method. The full implementation is in `references/full-guide.md` section 14.

---

## Adding MLS search

The starter doesn't include `search_listings`. Add it:

```python
def search_listings(self, filter_conditions=None, sort_fields=None,
                    page=1, page_size=25, sold=False, scope="all"):
    body = {
        "page": page,
        "pageSize": page_size,
        "scope": scope,
        "sold": sold,
        "filter": filter_conditions or {},
    }
    if sort_fields:
        body["sort"] = sort_fields
    return self._request("POST", "/v2.0/listings/search", body=body)
```

Filter syntax (the slightly weird parts):

- Range fields use comma-separated min,max: `"price": "400000,650000"`, `"beds": "3,"`, `"sqft": ",2500"`.
- Multi-value fields use lists: `"propertyType": ["Single Family", "Condo"]`.
- Location uses nested object: `{"location": {"city": ["Portland"], "zipCode": ["97225"]}}`.

Sort options: `PRICE_DESC`, `PRICE_ASC`, `MLS_LIST_DATE_L_DESC`.

Scope: `"all"` (full MLS), `"my"` (your listings), `"office"` (your office).

The `/v1.0/listing` endpoint exists but does not work with personal API key auth (quirk #10). Always use this `/v2.0/listings/search` with `scope="my"` instead.

---

## Adding `find_listing_by_address`

Lofty's listing search does NOT support keyword or street-address filters. The reliable approach:

1. Parse the zip from the full address (last 5-digit number).
2. Search `{"location": {"zipCode": [zip]}, "listingStatus": ["Active"]}`.
3. Filter the returned listings client-side by uppercase street-address substring match.
4. Return the first hit, or `{"error": "address_not_found"}` on miss.

Active only by design. Don't fall through to Pending or Sold; that masks typos.

The `siteDetailLink` field on a returned listing is the user's IDX site URL (e.g., `<your-domain>.com/listings/...`). Use it in calendar invites.

---

## Adding tasks, email, SMS

The endpoints:

- Tasks: `POST /v2.0/calendar` to create, `POST /v2.0/calendar/<id>/finish` to complete, `GET /v2.0/calendar` to list.
- Email: `POST /v1.0/message/email/send` with `{leadId, subject, content}`.
- SMS: `POST /v1.0/message/sms/send` with `{leadId, content}`.

For Tasks, the body shape:

```python
{
    "type": "TASK" or "APPOINTMENT",
    "leadId": <number>,
    "content": "...",
    "startAt": "2026-05-08T14:00:00-07:00",
    "endAt": "2026-05-08T14:30:00-07:00",
    "way": "Call" / "Email" / "Text" / "Meeting" / "Other",
    "assignedRole": "ASSIGNED"
}
```

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
