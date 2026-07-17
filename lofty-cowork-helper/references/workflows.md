# Lofty Workflow Recipes

Step-by-step recipes for the most common things real estate agents and VAs ask Claude to do in Lofty. Each recipe assumes the starter Python client is installed at `scripts/lofty_api.py` and the `.env` is configured with `LOFTY_API_KEY`.

---

## How the leads index stays current

The kit keeps a local file of every lead at `data/leads_index.json`. `find_client` reads it instead of polling Lofty (which silently ignores `keyword`, see quirk #2). Three layers keep it fresh, in order of cost and coverage:

**Live-scan fallback** runs inside `find_client` itself. When the local index has no match, it walks the 3 most recently created leads via the API to catch contacts created in the last few minutes. No setup required; works out of the box.

**Daily incremental** runs automatically via a Cowork scheduled task at 2am local. It pulls only page 1 of `/v1.0/leads` (the 25 newest) and merges new IDs into the local file. Under 15 seconds wall time. Set up at install via `mcp__scheduled-tasks__create_scheduled_task` calling `python3 scripts/refresh_leads_index.py --incremental`.

**Weekly full reconciliation** runs Sunday at 2am local. It re-walks every page and atomically rewrites the file, catching deletions and any drift the incremental missed. Uses `--full --resumable` so Cowork's 45-second bash limit can chunk it across multiple invocations; the script checkpoints state and Claude loops until exit 0.

If something slips past the auto-refresh, `find_client` will return a `stale_warning` key on its result when the local file is older than 2 days. The user-facing message tells the user to ask Claude to refresh. Run `python3 scripts/kit_health_check.py` for a structured status report.

Power users with very large CRMs or sub-day staleness requirements can also deploy Tier 4 (the leads-index Worker, free Cloudflare tier) for webhook-driven real-time mirroring. See `references/extending.md`.

---

## Find a client by name

The starter approach (limited):

```python
from lofty_api import LoftyAPI
api = LoftyAPI()
result = api.search_leads(page_size=25)
# Returns the 25 most recently created leads. Filter the list yourself.
matches = [
    lead for lead in result.get("leads", [])
    if "smith" in lead.get("lastName", "").lower()
]
```

This works for new or recent leads. It DOES NOT work for an old lead whose creation predates the most recent 25, because `/v1.0/leads` ignores `keyword` (quirk #2).

The real solution is a leads index. See `extending.md` section "Adding a leads index" for the full pattern. Once you have one, use:

```python
api.find_client("Jane Smith", exclude_stages=["DNC", "Archived"])
```

When the user asks "find Jane Smith" and you only have the starter, tell them honestly: "The starter client can search recent leads but not the full database. Want me to walk you through adding a leads index?"

---

## Log a note on a lead

```python
api.create_note(lead_id=12345, content="Spoke with client today. Wants to see homes Saturday afternoon.")
```

Steps:

1. **Confirm the lead.** Pull the lead first: `lead = api.get_lead(12345)`. Show the user the lead's name, email, and phone. Confirm it is the right person.
2. **Draft the note.** Plain text, no special characters. The Lofty UI shows the first line as a sort of de-facto title, so make the first line meaningful.
3. **Confirm the content.** Show the user the draft, ask if they want to change anything.
4. **Post it.** Call `create_note(lead_id, content)`.
5. **Confirm success.** Re-fetch the notes list and show them the new note.

Common mistake: posting a note to the wrong lead because the name matched two people. Always step 1.

---

## Pull a lead's activity feed

```python
activities = api.get_lead_activities(lead_id=12345, limit=20)
```

Returns recent browse, search, favorite, and request events. Use v1.0 only (quirk #3).

Useful for: "what has Jane been looking at this week?" Tell the user the addresses they have viewed, searches they have run, and properties they have favorited.

---

## Schedule a showing (full flow)

The fastest path for the typical case (one or more confirmed showings for an existing Lofty client) is the showing-orchestration workflow in `references/schedule-showing.md`. It drives the whole flow end to end: resolve the client, prepare each stop, create calendar events in parallel, post showing-log notes with the calendar event ID appended, and verify the SMS queue landed. Trigger it with phrases like "schedule a showing at," "book a tour for," or "set up [client] at [address] at [time]." Follow that workflow whenever you want one chat sentence to do the whole job.

The recipe below is the primitive-by-primitive manual fallback. Use it when the sub-skill is unavailable, when you want to drive each step yourself, or when you are debugging a partial run.

The starter client includes the showing helpers (`prepare_showing`, `find_listing_by_address`, `cancel_showing`) as of v1.3.0. No extension needed for the core flow. The `showing-sms` Cloudflare Worker (Tier 3, v1.7) is the only piece that requires additional setup; without it, `prepare_showing` still works but skips the post-showing SMS queue step.

The canonical flow:

1. `payload = api.prepare_showing(full_address, start_iso, client_name)` returns the listing details, the lead, a prefilled feedback URL, the calendar invite HTML, and the showing-log note text.
2. If `payload.get("error")`: tell the user what went wrong (most often: address not found in the parsed zip; could be wrong city or wrong zip).
3. Create a Google Calendar event using the payload. Cowork has Google Calendar tools available.
4. `api.create_note(lead_id, payload["showing_note_content"])` to leave the showing log on the Lofty side.
5. Confirm everything to the user: the calendar event, the note, the prefilled feedback URL.

Critical: do NOT use `create_task(APPOINTMENT)` for showings. That creates a request that asks the listing agent to approve, which is not what you want.

If the user has the `showing-sms` Cloudflare Worker deployed, `prepare_showing` also queues a 2-hour-before-showing SMS to the buyer. If they cancel the tour, call `api.cancel_showing(lead_id, full_address)` to dequeue it.

---

## Cancel a queued showing SMS

```python
result = api.cancel_showing(lead_id=12345, full_address="11513 SW BAMBI LN, Portland, OR 97223")
```

Returns:
- `{"status": "cancelled", ...}` on success
- `{"error": "no_match", ...}` if no queued SMS matches that lead and address
- `{"error": "multiple_matches", ...}` if multiple queued entries match

Pair the cancellation with a Lofty note like "Showing cancelled at client request."

---

## Search the MLS

Requires extending the starter client (`search_listings` is not in the minimal version).

```python
result = api.search_listings({
    "location": {"city": ["Portland"]},
    "price": "400000,650000",
    "beds": "3,",
    "baths": "2,",
    "sqft": "1500,",
    "propertyType": ["Single Family", "Condo"]
}, scope="all", page_size=25)
```

Range syntax: `"min,max"` for both ends, `"min,"` for "at least," `",max"` for "at most."

Scope:
- `all` - full MLS
- `my` - the user's own listings (works around quirk #10)
- `office` - the user's office's listings

Sort: `PRICE_DESC`, `PRICE_ASC`, `MLS_LIST_DATE_L_DESC`.

---

## Look up a single listing by full address

Requires `find_listing_by_address` (not in starter; see `extending.md`).

```python
result = api.find_listing_by_address("11513 SW BAMBI LN, Portland, OR 97223")
```

Searches active listings only by design. Returns either a slim listing dict on hit, or `{"error": "address_not_found", ...}` on miss.

If it misses, the most common causes (in order):
1. Wrong city
2. Wrong zip
3. Typo in the street name
4. Listing went off market

Always confirm the address with the user before retrying. Do not silently broaden the search to Pending or Sold; that masks typos.

Address format: `STREET, CITY, STATE ZIP`. Zip is the last 5-digit number.

---

## Send an email or SMS

```python
api.send_email(lead_id=12345, subject="Re: Saturday showing", content="...")
api.send_sms(lead_id=12345, content="Confirming 2pm tomorrow at the Bambi Lane house.")
```

The non-negotiable rule: ALWAYS confirm content with the user before calling either. Show them the draft, ask "Send this?", wait for an explicit "yes." Then send.

This rule exists because emails and SMS go to real clients. A wrong message lands in the wrong inbox and there is no undo.

---

## Create a task

```python
api.create_task(
    lead_id=12345,
    content="Call back about pre-approval",
    start_at="2026-05-08T14:00:00-07:00",
    end_at="2026-05-08T14:30:00-07:00",
    task_way="Call",              # Call, Email, Text, Meeting, Other
    # task_type defaults to "TASK"
    # assigned_role is optional; valid values are "Agent" or "Assistant"
)
```

Times use ISO 8601 with offset. Pacific is `-07:00` in DST, `-08:00` outside.

Lofty body shape gotchas (quirk #17): the API field is `taskWay` not `way`, `timeZoneCode` is required (the wrapper supplies America/Los_Angeles by default), and `assignedRole` accepts `"Agent"` or `"Assistant"` only (not `"ASSIGNED"`).

Reminder: do NOT use `task_type="APPOINTMENT"` for showings (triggers listing-agent approval).

---

## List webhooks / refresh subscriptions

```python
api.get_webhooks()
```

Lists all active webhook subscriptions. If the user has set up a leads-index Worker, the subscription on webhook list 2 should be visible here.

To create a new subscription:

```python
api.create_webhook(list_id=2, url="https://leads-index.<your-subdomain>.workers.dev/webhook/<secret>")
```

To delete one: `api.delete_webhook(subscribe_id)`.

---

## Tag a lead safely

ALWAYS use the v1.10 wrappers, never `update_lead(tags=...)` directly. The naive call REPLACES the entire tag list (silently deleting every existing tag) and treats integer tagIds as new tag NAMES (polluting the team library). See quirks #38 and #39.

```python
# Add a tag without destroying existing ones:
api.add_tag(lead_id, "Acreage")

# Remove just one tag:
api.remove_tag(lead_id, "Buyer")

# Explicit replace (use only when you really mean "clear and reset"):
api.set_tags(lead_id, ["Active", "Hot"])
```

Each call reads the current tag names, applies the change, writes back, and pushes a `tag_change` event to `data/.kit-history.jsonl` with the before and after lists. If a tag change ever seems wrong, run `python3 scripts/kit_history.py 20` to inspect the recent trail.

---

## Read a lead's segments

Segments are read-only via the public API. To add or remove segments, use the Lofty web UI; see quirk #40 for why.

```python
# Slim form, just the segments list:
segments = api.get_lead_segments(lead_id)

# Or via find_client (segments are now part of the slim match dict):
result = api.find_client("Jane Smith")
if "match" in result:
    print(result["match"]["segments"])
```

---

## Check kit health

When the user asks "is everything working?" or "is my Lofty integration healthy?":

```
python3 scripts/kit_health_check.py
```

Three-line human summary by default. Add `--json` for a structured report Claude can parse. Exit code 0 = all OK, 1 = needs attention. Also push a record to `data/.kit-history.jsonl` every run so we have a trail.

For deeper debugging, read the history directly:

```
python3 scripts/kit_history.py 20    # last 20 events
```

The history captures health checks, tag changes, and any other kit event worth tracking.

---

## Confirmations and safety reminders

Apply these on every workflow:

- For email or SMS: draft, show the user, ask before sending.
- For deletes: confirm twice. The Lofty UI doesn't have an undo.
- For lead-targeted writes (notes, tasks): confirm the lead ID first.
- For long scans: don't run them in Cowork's bash tool (45s timeout). Tell the user to run from their terminal.

The user can override these for a specific case by saying "go ahead" or "send it." But the default is always: draft, confirm, then act.
