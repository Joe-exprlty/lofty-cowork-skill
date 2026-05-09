# Lofty CRM API: A Practical Guide for Real Estate Agents Who Code a Little

This is a working agent's field manual for Lofty's API, built from real production use. It tells you what works, what is broken, what is silently broken (the worst kind), and the architecture pattern you'll want to copy if you plan to drive your own automations with Claude.

If you can read Python, run a curl command, and paste a Cloudflare Worker, you have everything you need.

---

## What you actually get from the Lofty API

Lofty exposes most of what you see in the UI: leads (contacts), notes, activities, tasks and appointments, the MLS listings feed, calls, emails, SMS, transactions, team data, tags, custom fields, webhooks, and a calendar. You can drive your CRM with code, and you can let Claude drive it for you in plain English.

What you cannot get: a "Log Showing" entry the way the UI does it (no public endpoint), the AI lead-analysis routes (not enabled), and reliable cross-lead activity feeds (more on that below).

Base URL: `https://api.lofty.com`
Partial public docs: `https://api.lofty.com/docs/index.html` (the partial part is the problem you're about to read 1500 words about)

---

## Authentication: the first thing that bites everyone

Lofty supports two auth methods, and only one of them works the way you think.

**Personal API key (recommended, never expires).** Generate it from your Lofty account settings. Send it on every request as:

```
Authorization: token YOUR_API_KEY
```

Yes, the literal word `token`. Not `Bearer`. If you use `Bearer` with a personal key you'll get error code `200058` "User in token does not exist." Many hours have died on this rock.

**OAuth.** Used by the official Lofty MCP plugin. Disconnects often, requires re-auth, and is a pain to script against. If you have a personal API key, just use it.

On writes (POST, PUT, DELETE) you also need:

```
Content-Type: application/json
```

On GETs, do NOT send `Content-Type`. Some endpoints return 415 if you do. This is one of those things you'll forget once and waste an hour debugging.

A minimal working call:

```bash
curl -H "Authorization: token YOUR_API_KEY" \
  https://api.lofty.com/v1.0/me
```

If that returns your profile, you're in.

---

## Rate limits and pagination

**10 requests per minute.** Hard cap. Pace your client at roughly 6.5 seconds per request and you'll never trip it. If you blow past it, you get throttled, not banned, but you'll waste a lot of wall-clock time.

**Page size is hard-capped at 25** on `/v1.0/leads`, regardless of what you ask for. The response metadata will echo `limit: 25` even if you asked for 100.

**Pagination uses `scrollId`, not `page`.** This is critical. The `page` query parameter on `/v1.0/leads` is silently ignored. Calling `page=2` returns the same first 25 leads as `page=1`. To get the next 25, look in the response for `_metadata.scrollId` and pass that value back as a query param.

```python
# Correct pagination
resp = api.get("/v1.0/leads", {"pageSize": 25})
results = resp["leads"]
scroll_id = resp.get("_metadata", {}).get("scrollId")

while scroll_id:
    resp = api.get("/v1.0/leads", {"pageSize": 25, "scrollId": scroll_id})
    results += resp["leads"]
    scroll_id = resp.get("_metadata", {}).get("scrollId")
```

For 650 leads at 6.5s spacing, expect a full scan to take about 3 minutes.

---

## The 15 quirks you need to know

Read these once. Tattoo number 2, 3, 4, and 15 onto your forearm. They are the silent failures that will eat days of your life if you don't know about them.

**1. Auth header is `token`, not `Bearer`.** Covered above. Error 200058 means you got this wrong.

**2. `/v1.0/leads` silently ignores `sortField`, `keyword`, `startTime`, and oversized `pageSize`.** This is the worst quirk in the whole API. The endpoint accepts these params, returns 200 OK, and just pretends you never sent them. Sort always returns leadId DESC (newest first). Keyword search returns the whole book. Page size caps at 25. The fix: build a local index of leads (see the Architecture section below) and search client-side.

**3. Notes use a flat endpoint with leadId in the body.**
```bash
# Correct
curl -X POST https://api.lofty.com/v1.0/notes \
  -H "Authorization: token KEY" \
  -H "Content-Type: application/json" \
  -d '{"leadId": 12345, "content": "Showed 123 Main St today"}'

# Returns 404
curl -X POST https://api.lofty.com/v1.0/leads/12345/notes ...
```
There is no `title` field. `leadId` must be a number, not a string.

**4. Activities must use v1.0.** The v2.0 endpoint exists and returns 200 OK with empty results. Use `/v1.0/leads/<id>/activities`.

**5. GET requests: do not send `Content-Type`.** Some endpoints return 415 if you do. POST/PUT/DELETE require it. GET endpoints reject it.

**6. Lead phones and emails are plain string arrays**, not objects.
```json
{
  "phones": ["5035551234"],
  "emails": ["client@example.com"]
}
```
Not `[{"number": "...", "primary": true}]` like you might expect.

**7. `get_lead` response is wrapped.** `GET /v1.0/leads/<id>` returns `{"lead": {...}}`. Unwrap before use.

**8. Pagination is `scrollId`, not `page`.** Covered above. Worth repeating because it's invisible: page=2 just returns page 1 again with no error.

**9. Rate limit: 10 req/min.** Pace yourself.

**10. `/v1.0/listing` (your own listings) doesn't work with API key auth.** Use `POST /v2.0/listings/search` with `scope="my"` instead.

**11. All times: ISO 8601 with offset.**
```
2026-04-15T14:00:00-07:00   (Pacific, correct)
2026-04-15T14:00:00         (no offset, will be misinterpreted)
2026-04-15 14:00            (wrong format, rejected)
```

**12. There is no bulk activity feed.** Every cross-lead activity endpoint you might guess at returns 404: `/v1.0/activities`, `/v2.0/activities`, `/v1.0/events`, `/v1.0/notifications`, `/v1.0/timeline`, `/v1.0/leadActivities`. The `/v1.0/systemLogs` endpoint requires a `leadId`. If you want to know what's happening across all leads, you must subscribe to webhooks.

**13. Webhook list 3 (Lead Activity) payloads are pings only.** The body is just `{leadId, updateTime}` with no activity type, address, or detail. To get the actual activity you have to call `/v1.0/leads/<id>/activities` and find the matching one. Webhook delivery SLA is typically 1 minute, up to 5.

**14. (Cowork-specific) bash tools have a 45s hard timeout.** At 6.5s spacing, a single bash call caps at about 6 API requests. Long scans need to run as standalone scripts, not in-line.

**15. The `page` parameter on `/v1.0/leads` is silently ignored.** Already covered in pagination. This deserves its own number because it is so quietly wrong. Default sort is createTime DESC, which is actually useful for finding the most recently added lead that hasn't synced into your local index yet.

**Bonus, not numbered: things that look like they should work but don't.**
| What you might try | What actually works |
|---|---|
| `/v1.0/leads/<id>/notes` | 404. Use `/v1.0/notes` with leadId in body. |
| `/v2.0/leads/<id>/activities` | Empty. Use `/v1.0/leads/<id>/activities`. |
| `/v1.0/listing` | Auth error. Use `/v2.0/listings/search` with `scope="my"`. |
| `/v2.0/ai/lead-analysis` | Internal error. Not enabled. |
| `/v2.0/ai/call-script` | Internal error. Not enabled. |

---

## Endpoint reference

These are confirmed working as of mid-2026.

| Endpoint | Method | What it does |
|---|---|---|
| `/v1.0/me` | GET | Your user profile |
| `/v1.0/leads` | GET | Search/list leads (sort and keyword silently ignored) |
| `/v1.0/leads/<id>` | GET | Single lead, wrapped in `{"lead": {...}}` |
| `/v1.0/leads` | POST | Create a lead |
| `/v1.0/leads/<id>` | PUT | Update a lead |
| `/v1.0/leads/<id>` | DELETE | Delete a lead |
| `/v1.0/leads/<id>/activities` | GET | Activity timeline (v1.0 only) |
| `/v1.0/leads/<id>/activities` | POST | Add an activity |
| `/v1.0/notes` | POST | Create a note (leadId + content in body) |
| `/v1.0/notes?leadId=X` | GET | Get notes for a lead |
| `/v1.0/notes/<id>` | PUT | Update a note |
| `/v1.0/notes/<id>` | DELETE | Delete a note |
| `/v2.0/calendar` | GET/POST | Tasks and appointments |
| `/v2.0/calendar/<id>/finish` | POST | Mark task complete |
| `/v2.0/calendar/meetings/available` | GET | Available meeting slots |
| `/v2.0/listings/search` | POST | Search MLS listings |
| `/v1.0/message/email/send` | POST | Send email |
| `/v1.0/message/sms/send` | POST | Send SMS |
| `/v1.0/members` | GET | Team members |
| `/v1.0/org` | GET | Organization details |
| `/v1.0/teamFeatures/listTag` | GET | All tags |
| `/v1.0/teamFeatures/listCustomField` | GET | All custom fields |
| `/v1.0/webhooks` | GET | List webhook subscriptions |
| `/v1.0/webhooks` | POST | Create a webhook subscription |
| `/v1.0/webhooks/<id>` | DELETE | Remove a subscription |

---

## Common workflows with examples

### Find a lead by name (the hard problem)

Because keyword search on `/v1.0/leads` is silently ignored, you cannot find a lead by name through the API directly. You have three options:

**Option A: brute force.** Page through every lead with scrollId, filter client-side. Slow, simple, works.

**Option B: build a local index.** Run a one-time scan, save names + IDs to a JSON file, search the file. Fast once built. The file goes stale.

**Option C: live index via webhooks.** Subscribe to webhook list 2 (Lead Info) with a Cloudflare Worker. Worker keeps a KV store fresh on every create/update/delete event. Always current. This is the option I run in production. See the Architecture section.

Recommended for any serious automation: start with B, graduate to C when you outgrow staleness.

### Create a note

```bash
curl -X POST https://api.lofty.com/v1.0/notes \
  -H "Authorization: token KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "leadId": 12345,
    "content": "=== SHOWING LOG ===\n123 Main St, Portland, OR 97214\n2026-05-08 2:00 PM\nClient feedback: liked the kitchen, hated the basement."
  }'
```

I use a structured `=== SHOWING LOG ===` block so I can grep for them later. Lofty doesn't give you a "showing" object type, but a tagged note is searchable and visible in the UI timeline.

### Schedule a task or appointment

```bash
curl -X POST https://api.lofty.com/v2.0/calendar \
  -H "Authorization: token KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "TASK",
    "content": "Follow up on offer",
    "leadId": 12345,
    "startAt": "2026-05-10T14:00:00-07:00",
    "endAt": "2026-05-10T14:30:00-07:00",
    "way": "Call"
  }'
```

`type` is `TASK` or `APPOINTMENT`. `way` is `Call`, `Email`, `Text`, `Meeting`, or `Other`. Avoid `APPOINTMENT` for showings, it generates a request that pings the listing agent for approval, which is rarely what you want.

### Search MLS listings

```bash
curl -X POST https://api.lofty.com/v2.0/listings/search \
  -H "Authorization: token KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "filterConditions": {
      "location": {"city": ["Portland"]},
      "price": "400000,650000",
      "beds": "3,",
      "baths": "2,",
      "sqft": "1500,",
      "propertyType": ["Single Family", "Condo"],
      "listingStatus": ["Active"]
    },
    "sortFields": ["MLS_LIST_DATE_L_DESC"],
    "page": 1,
    "pageSize": 25,
    "scope": "all"
  }'
```

`scope` options: `all` (full MLS), `my` (your own listings), `office` (your office's listings).

`listingStatus` cannot be combined in one call, you must run separate calls for `["Active"]`, `["Pending"]`, `["Sold"]` if you want all three.

### Find a listing by address (the address pattern)

There is no keyword or streetAddress filter on listing search. The reliable way:

1. Parse the zip from the address string (last 5-digit number).
2. Search by `listingStatus: ["Active"]` and `location.zipCode: [zip]`.
3. Filter the returned listings client-side by uppercase streetAddress substring match.
4. The `siteDetailLink` field on the listing is the public-facing URL on whichever site is configured.

Don't fall through to Pending or Sold if Active misses, you'll mask typos. Just return an error and ask the user to confirm the address.

### Send an email or SMS (carefully)

```bash
curl -X POST https://api.lofty.com/v1.0/message/sms/send \
  -H "Authorization: token KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "leadId": 12345,
    "content": "Hi, just confirming our showing tomorrow at 2."
  }'
```

If Claude is driving, ALWAYS confirm with the human before sending email or SMS. Do not let an LLM hit the send endpoint without a human in the loop.

---

## Webhooks: the only way to know what's happening

Because there is no bulk activity feed, webhooks are how you stay current. There are 12 event types:

| ID | Event |
|---|---|
| 1 | Agent |
| 2 | Lead Info (create/update/delete) |
| 3 | Lead Activity |
| 4 | Listing Alert |
| 5 | Transaction |
| 6 | Call (manual + logged only, not auto) |
| 7 | Email (manual + logged only) |
| 8 | Text (manual + logged only) |
| 9 | Note |
| 10 | Task |
| 11 | Appointment |
| 12 | Pipeline Change |

Subscribe with:

```bash
curl -X POST https://api.lofty.com/v1.0/webhooks \
  -H "Authorization: token KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "listId": 2,
    "url": "https://your-worker.example.workers.dev/webhook/your-secret"
  }'
```

The URL receives POSTs from Lofty's IPs. Body shape varies by list. List 2 (Lead Info) is rich, you get the full lead. List 3 (Lead Activity) is a ping only, body is just `{leadId, updateTime}` and you must call back to enrich. The other lists are in between.

Delivery is 1 to 5 minutes typical, not real-time. Plan accordingly.

---

## The architecture pattern: leads index + Workers

This is the part most agents miss. The Lofty API is too rate-limited and too quirky to drive a real-time automation directly. You need a layer in front of it.

Here's the pattern I run in production. Steal it freely.

```
+------------------+         +-------------------+         +----------------+
|   Lofty CRM      |  webhook|  Cloudflare       |  read   |   Your code    |
|                  +-------->+  Worker (KV/D1)   +<--------+   (Claude,     |
|                  |         |                   |  write  |   scripts,     |
|                  +<--------+                   +-------->+   automations) |
+------------------+   API   +-------------------+   API   +----------------+
```

**Why a Worker in the middle?**

1. **Local indexes go stale.** A JSON file on your laptop is fine for a one-off, but it's 14 days old by the time you remember to refresh it.
2. **Webhooks need somewhere to land.** Lofty pushes events. Your laptop is offline half the day. A Worker is always on, costs $5/month for the paid plan, and processes webhooks in milliseconds.
3. **Cloudflare KV and D1 are cheap.** A KV namespace stores your leads index. A D1 database stores client preferences, feedback, anything you want to query later.
4. **Workers can run scheduled tasks** without you touching cron on a laptop.

**The four Workers I run:**

- **`leads-index`**: subscribes to webhook list 2 (Lead Info), patches a KV store on every create/update/delete. Exposes `/export` (auth: Bearer key) for the Python client to read. Always-fresh leads index, replaces the local JSON file.
- **`jotform-to-lofty`**: receives Jotform submissions from a post-showing feedback form, writes a note to the Lofty lead, sends a recap email via Resend, and writes a row to D1 for trend analysis. After 3 submissions, the recap email gets a "what we're learning about your preferences" section.
- **`short-links`**: 6-character branded short links for SMS, redirects to long URLs. KV-backed.
- **`showing-sms`**: schedules a post-showing SMS at the showing time. Uses Cloudflare Durable Object alarms (not cron), one DO per showing. The DO sleeps until the alarm fires, sends the SMS via Lofty, marks the KV index `sent`, and deletes its own state. Cancellable via `DELETE /cancel`.

**Why Durable Objects instead of cron?** A cron Worker that runs every minute polls the queue every minute. A DO with `setAlarm()` wakes up at exact UTC time, fires once, goes back to sleep. Cleaner, cheaper, and validated at 162ms precision in production.

**Worker layout (one wrangler.toml per worker, all in `worker/`):**
```
worker/
  leads_index_worker.js        wrangler.leads-index.toml
  jotform_to_lofty_worker.js   wrangler.jotform.toml
  short_links_worker.js        wrangler.short-links.toml
  showing_sms_worker.js        wrangler.showing-sms.toml
```

Deploy with `wrangler deploy -c wrangler.<name>.toml`.

---

## A Python client you can adapt

This is the structure I use. It handles auth, rate limiting, pagination, the unwrap quirk, and a few common operations. Drop it into any project.

```python
import json
import os
import time
import urllib.parse
from urllib.request import Request, urlopen
from urllib.error import HTTPError

class LoftyAPI:
    BASE = "https://api.lofty.com"
    SPACING = 6.5  # seconds between requests, stays under 10/min

    def __init__(self):
        self.key = os.environ.get("LOFTY_API_KEY")
        if not self.key:
            raise RuntimeError("Set LOFTY_API_KEY in your environment")
        self._last_call = 0

    def _wait(self):
        delta = time.time() - self._last_call
        if delta < self.SPACING:
            time.sleep(self.SPACING - delta)
        self._last_call = time.time()

    def _headers(self, write=False):
        h = {"Authorization": f"token {self.key}"}
        if write:
            h["Content-Type"] = "application/json"
        return h

    def get(self, path, params=None):
        self._wait()
        url = self.BASE + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        req = Request(url, headers=self._headers(write=False))
        with urlopen(req) as resp:
            return json.loads(resp.read())

    def post(self, path, body):
        self._wait()
        req = Request(
            self.BASE + path,
            data=json.dumps(body).encode(),
            headers=self._headers(write=True),
            method="POST",
        )
        with urlopen(req) as resp:
            return json.loads(resp.read())

    # Common operations

    def get_lead(self, lead_id):
        resp = self.get(f"/v1.0/leads/{lead_id}")
        return resp.get("lead", resp)  # auto-unwrap

    def create_note(self, lead_id, content):
        return self.post("/v1.0/notes", {
            "leadId": int(lead_id),
            "content": content,
        })

    def get_activities(self, lead_id, limit=50):
        return self.get(
            f"/v1.0/leads/{lead_id}/activities",
            {"pageSize": limit},
        )

    def search_leads_paged(self, page_size=25):
        """Generator that yields all leads via scrollId pagination."""
        params = {"pageSize": page_size}
        while True:
            resp = self.get("/v1.0/leads", params)
            for lead in resp.get("leads", []):
                yield lead
            scroll_id = resp.get("_metadata", {}).get("scrollId")
            if not scroll_id:
                break
            params = {"pageSize": page_size, "scrollId": scroll_id}
```

Usage:

```python
api = LoftyAPI()
me = api.get("/v1.0/me")
print(me["firstName"])

api.create_note(12345, "Followed up by phone, voicemail")

for lead in api.search_leads_paged():
    if "Smith" in lead.get("lastName", ""):
        print(lead["id"], lead["firstName"], lead["lastName"])
        break
```

---

## Using this with Claude

If you're going to point Claude at this API (in Cowork, Claude Code, or via the SDK), here's what works.

**1. Give Claude the Python client.** Don't make it write curl strings every time. A method like `api.create_note(lead_id, content)` is one tool call. Curl is fragile, Python is robust.

**2. Tell Claude about the quirks up front.** Put the top 5 in your CLAUDE.md or system prompt. The auth header, the silent ignores, the v1.0 vs v2.0 split, the pagination, the rate limit. Otherwise Claude will read the API docs (which are partial) and confidently write broken code.

**3. Use the leads index, not raw search.** If Claude has to find a lead by name, point it at your local `leads_index.json` or the `leads-index` Worker, not `/v1.0/leads?keyword=Smith`. The API call returns garbage.

**4. Hard rules for sends.** `send_email` and `send_sms` should always require a human confirm step. Lofty doesn't give you a "draft" mode, once you call send it's gone. Have Claude print the message and wait for "go".

**5. Claude is good at writing the note format.** Give it your structured-note template (`=== SHOWING LOG ===`, etc.) and let it fill in the details. Notes are searchable in the Lofty UI, so a consistent format pays off when you scroll through a lead's history six months later.

**6. Consider a "skill" or context file.** If you're using Cowork, a skill folder with `SKILL.md`, references, and examples makes Claude vastly more accurate than dumping everything into one prompt. The skill becomes the source of truth for how to use the API.

---

## Safety rules for any automation

These are the rules I run by. Adopt or adapt.

1. CONFIRM with a human before sending email, sending SMS, or deleting anything.
2. Exclude yourself from lead searches (filter on lastName).
3. Exclude stages you don't want to action: `DNC`, `Archived`, `Agents / Vendors`.
4. Never paste API keys into a chat window. If a key is exposed, rotate it immediately and update every Worker, every laptop, every CI secret.
5. Sign drafts with your name so a leaked LLM message is obviously not from your team.

---

## Known gaps and roadmap ideas

A few things Lofty's API does not currently give you, in case you were planning around them:

- No "log a showing" public endpoint. The UI's "Log Showing" is internal. Use a tagged note instead.
- No bulk activity feed (covered above). Per-lead only, plus webhooks.
- No native preferences object on leads. If you want to track a buyer's must-haves and dealbreakers across showings, you'll roll your own (D1 + a feedback form is what I do).
- No reliable webhook for AUTO-logged calls/emails/texts. Only manually-logged ones fire the webhook.
- No real-time webhook for pipeline stage changes that includes the previous stage. The list 12 event has the new stage only.

The pattern that solves these: webhook into a Worker, write your own enriched record into D1, query D1 for trends. That's where you should focus your build.

---

## Quick reference card

Copy this into your editor. It's 90% of what you'll do day to day.

```
Auth:    Authorization: token YOUR_KEY
Base:    https://api.lofty.com
Limit:   10 req/min, pace at 6.5s
Times:   ISO 8601 with offset, e.g. 2026-05-08T14:00:00-07:00
Address: STREET, CITY, STATE ZIP

Find a lead:        local index, NOT /v1.0/leads?keyword=
Get a lead:         GET /v1.0/leads/<id>      (unwrap "lead")
Create a note:      POST /v1.0/notes          (leadId + content, no title)
Get activities:     GET /v1.0/leads/<id>/activities    (v1.0 only)
Create task:        POST /v2.0/calendar       (type=TASK or APPOINTMENT)
Search MLS:         POST /v2.0/listings/search
Send email:         POST /v1.0/message/email/send      (CONFIRM FIRST)
Send SMS:           POST /v1.0/message/sms/send        (CONFIRM FIRST)
Pagination:         scrollId from _metadata, NOT page=
Webhooks:           list 2 = leads, list 3 = activity (ping only)

Auth fail 200058:   you used Bearer instead of token
Empty results:      check if you used v2.0 instead of v1.0
404 on notes:       use /v1.0/notes, not /v1.0/leads/X/notes
415 on GET:         remove Content-Type header from GETs
Same page twice:    page= is ignored, use scrollId
```

---

## Replicating my stable Claude + Lofty setup

Quick clarifier: what I run is a Cowork Skill, not a traditional MCP server. Same outcome though. Claude understands Lofty, has a Python client to call it, knows the quirks, and can do real work without me hand-holding it through every API call. Here's how to get to the same place.

**The fast path: install my skill.**

1. Open `https://github.com/Joe-exprlty/lofty-cowork-skill/releases/latest` in a browser.
2. Download `lofty-cowork-helper.skill` (about 42 KB).
3. Double-click the file. Claude Desktop opens and asks "Add lofty-cowork-helper to your library?" Click Add to library.
4. Open a new Cowork conversation and say "Set up Lofty for the first time." The skill walks you through getting your Lofty API key, picking a project folder, and writing a `.env` file with your credentials. Total time: about 15 minutes.

That's it. After setup, anything you say to Claude that mentions Lofty (find a lead, log a note, schedule a showing, summarize activity) auto-activates the skill, and Claude calls the bundled Python client to do the work.

**What's actually inside the skill, in plain terms.**

A Cowork Skill is a folder with a few files that Claude reads when triggered. Mine has:

- A `SKILL.md` describing what the skill does and when to activate it. The first 200ish lines load into context the moment a Lofty phrase is detected, so Claude knows the basics immediately without reading anything else.
- A bundled `lofty_api.py` Python client (the one shown earlier in this guide, plus more methods). Claude calls into this rather than writing curl strings.
- A `references/` folder with deeper docs (full guide, quirks, workflows, extending) that Claude reads only when needed. This is the "progressive disclosure" pattern, the body stays small and Claude pulls more context on demand.
- An `assets/` folder with starter files (Python client, env template, CLAUDE.md template) that get copied into the user's workspace during setup.
- A `setup_check.py` script that runs after setup to confirm the API key works and prints a friendly success or fix-this message.

The skill is read-only. The user owns their own copy of the Python client and `.env` file in their workspace. The skill just brings the knowledge.

**If you want to fork mine and make your own version.**

Clone the repo at `github.com/Joe-exprlty/lofty-cowork-skill`. The folder structure is:

```
lofty-cowork-skill/
  README.md          (distributor overview)
  INSTALL.md         (recipient setup steps)
  PACKAGING.md       (how to build the .skill file)
  lofty-cowork-helper/
    SKILL.md         (the skill body, loads on trigger)
    scripts/
      setup_check.py
    references/      (deep docs, loaded on demand)
    assets/          (files copied into user's workspace)
```

Edit anything you want, then run Anthropic's `package_skill.py` script (covered in `PACKAGING.md`) to build a `.skill` file you can ship. Distribute it however you like: direct download, GitHub release, email attachment, or a private plugin marketplace. The recipient just double-clicks the file.

**Beyond the skill: the Workers.**

The skill alone gets you a working Claude + Lofty setup. The four Cloudflare Workers (covered in the Architecture section above) are an upgrade path, not a requirement. Run the skill standalone first. When you outgrow it (the leads-index goes stale, you want post-showing SMS, you want a feedback database), spin up the Workers one at a time. Each one is independently useful.

Order I'd recommend if you're building from scratch:

1. Skill installed, Python client working, can find leads and log notes. Stop here for a week and use it on real work.
2. Add the `leads-index` Worker so `find_client` is always fresh.
3. Add the `short-links` Worker (it's a 50-line Worker, takes 20 minutes).
4. Add the `showing-sms` Worker once you have a Cloudflare Workers Paid plan ($5/month) for Durable Objects.
5. Add the `jotform-to-lofty` Worker if you want a post-showing feedback loop into a D1 database.

Each Worker is in `worker/` in my repo with a `wrangler.<name>.toml`. Deploy with `wrangler deploy -c wrangler.<name>.toml`.

---

## Final advice

Lofty's API will get you 90% of the way there if you accept the constraints. The other 10% you build yourself with webhooks, a Worker, and a small database.

Start with the Python client. Get one note created end to end. Then list a lead's activities. Then walk the leads paginator. Once those three work, you can build anything.

If you get stuck, the error code 200058 with a personal API key is always the auth header. The empty array on activities is always v2.0. The "I can't find Sarah Smith" is always the keyword silent-ignore.

Good luck. The hard part is knowing the gotchas. The easy part is everything after.
