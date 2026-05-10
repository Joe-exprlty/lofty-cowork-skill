# Claude Cowork + Lofty: A Complete Setup, Learning, and Best Practices Guide

A self-contained guide for connecting Claude (in Cowork mode) to the Lofty CRM API. It walks through setup, explains the things that bit us along the way, gives you working patterns for common workflows, and lays out the best practices we settled on after months of trial and error.

**Target reader:** A tech-savvy real estate agent or VA. You do not need to be a developer, but you should be comfortable installing software, editing a config file, and pasting commands into Terminal.

**A skeptical note up front.** Everything in this guide reflects one team's testing of the Lofty API. Lofty can change behavior without notice, plans differ, MLS regions differ, and your account permissions may differ. Verify every quirk in your own environment before relying on it. The patterns here are the right starting points, not eternal truths.

**A second skeptical note.** Anywhere this guide says "the Worker is at `<your-subdomain>.workers.dev`," your real URL will be different. Anywhere it says "your last name," substitute yours. Anywhere it shows a code snippet, treat it as a starting point you should read line by line, not paste blindly.

---

## Table of Contents

1. What you can do once connected
2. What you cannot do (Lofty API limitations)
3. Architecture: how the pieces fit together
4. Prerequisites
5. Setup path A: fork a working reference repo
6. Setup path B: build it from scratch
7. Step-by-step: get your Lofty API key
8. Step-by-step: configure `.env`
9. Step-by-step: verify the connection
10. Step-by-step: open the project in Cowork
11. The three ways Claude can talk to Lofty
12. Authentication model: the biggest footgun
13. The full list of API quirks
14. Common workflows with examples
15. The leads index (the most important workaround)
16. Cloudflare Workers (optional automations)
17. Best practices
18. Tips for prompting Claude about Lofty
19. Troubleshooting decision tree
20. Key rotation checklist
21. Glossary
22. A minimal Python client template (for the from-scratch path)
23. Where to look for deeper detail

---

## 1. What you can do once connected

Once Claude can reach Lofty through this setup, you can ask it in plain English to:

- Find a lead by name, even when Lofty's `keyword` parameter fails (we read from a local index instead)
- Pull a lead's full activity feed: browses, searches, favorites, info requests
- Log notes, create tasks, update lead fields
- Search active MLS listings by city, price, beds, baths, square footage
- Look up a specific listing by full address (active only, by design)
- Schedule a showing end to end: calendar invite, prefilled buyer feedback link, Lofty note, automated 2-hour pre-showing SMS to the buyer
- Cancel a queued post-showing SMS when a tour falls through
- Read your team, organization, tags, custom fields, and webhooks
- Send emails or texts (after you confirm in chat each time)

What Claude can do depends on what you build. The reference Python client covers all of the above. If you are building from scratch, you will add capabilities one method at a time.

---

## 2. What you cannot do (Lofty API limitations)

These are limits of the Lofty API itself, not of Claude or Cowork:

- **No "Log Showing" equivalent.** The Lofty UI has a Log Showing button. There is no API endpoint for it. We use a regular note with a `=== SHOWING LOG ===` header block instead.
- **No bulk activity feed.** Every cross-lead activity endpoint returns 404. Activity is per-lead. To get cross-lead notifications, subscribe to webhook list 3 and call back to enrich each event.
- **No reliable sort or keyword on `/v1.0/leads`.** Those parameters are accepted and silently dropped. Hence the leads index workaround.
- **`create_task(APPOINTMENT)` is the wrong tool for showings.** It creates a request that asks the listing agent to approve, which is rarely what you want. Use Google Calendar plus a showing-log note instead.
- **Some AI endpoints are not enabled.** `/v2.0/ai/lead-analysis` and `/v2.0/ai/call-script` return internal errors regardless.

These are documented in the quirks list (section 13) so you can plan around them.

---

## 3. Architecture: how the pieces fit together

```
┌─────────────────────────────────────────────────────────────┐
│  Claude Desktop (you ask things in plain English)           │
│  └── Cowork mode                                            │
│      ├── reads .claude/CLAUDE.md (your project context)     │
│      ├── runs Python scripts via the bash tool              │
│      └── reads/writes files in your project folder          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Your local Python client (lofty_api.py or your own)        │
│  ├── reads LOFTY_API_KEY from .env                          │
│  ├── enforces 6.5s rate limit between calls                 │
│  ├── handles auth header quirk (token, not Bearer)          │
│  └── reads from leads index instead of broken /v1.0/leads   │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴────────────────┐
              ▼                                ▼
┌──────────────────────────┐      ┌─────────────────────────────┐
│  Lofty REST API          │      │  Optional Cloudflare Workers│
│  api.lofty.com           │      │  (background automations)   │
│  10 req/min limit        │      │  - leads-index (live cache) │
│                          │      │  - showing-sms (DO alarms)  │
│                          │      │  - jotform-to-lofty         │
│                          │      │  - short-links              │
└──────────────────────────┘      └─────────────────────────────┘
```

The Workers layer is optional. You can run a basic Cowork + Python client setup without any Workers and still do most of the day-to-day work. The Workers exist to do things that would otherwise require a server running 24/7, like sending an SMS at exactly 2 hours before each showing, or keeping a live leads index without a manual refresh.

---

## 4. Prerequisites

Hard requirements (all platforms):

- Mac (macOS 14+), Windows (10 or 11), or Linux. All three are supported.
- Python 3.11 or newer
- A Lofty account that has API access enabled (Settings, API Keys section is visible)
- Claude Desktop installed with Cowork mode enabled
- A code editor that handles dotfiles correctly (VS Code, Cursor, TextEdit on Mac). On Windows, do NOT use plain Notepad; it can mangle `.env` files.
- A terminal: macOS Terminal, Windows Terminal or PowerShell, or your Linux distro's default

Platform-specific notes:

- **Mac:** check Python with `python3 --version`. Install via Homebrew (`brew install python`) or python.org.
- **Windows:** check Python with `python --version`. The command on Windows is `python` (or `py`), NOT `python3`. Install from the Microsoft Store ("Python 3.12" or newer) or python.org with "Add to PATH" checked during install. Use PowerShell or Windows Terminal, not the older Command Prompt.
- **Linux:** check Python with `python3 --version`. Use your distro's package manager.

Path conventions used throughout this guide:

- Mac / Linux: `~/Code/lofty-tools`
- Windows PowerShell: `$HOME\Code\lofty-tools`
- Windows plain text: `C:\Users\<username>\Code\lofty-tools`

Where this guide says `python3`, Windows users should substitute `python` (or `py`).

Optional (only if you want the Worker-based automations):

- A Cloudflare account
- The Cloudflare Workers Paid plan ($5/month) IF you want the showing-sms Worker (uses Durable Objects)
- A Jotform account (for the post-showing buyer feedback flow)
- An email-sending API like Resend (for the buyer recap email)
- For Worker deploys via wrangler: Node.js installed (`brew install node` on Mac, the Node installer on Windows, your distro's package on Linux), then `npm install -g wrangler`. The wrangler CLI runs on all three platforms.

If any of the hard requirements are missing, install them first. None of the optional pieces are required to get started.

### Want a Mac-like experience on Windows?

Install WSL (Windows Subsystem for Linux). One command in PowerShell as administrator:

```powershell
wsl --install
```

After reboot, you have an Ubuntu shell where every Mac/Linux command in this guide works verbatim. Most users do not need WSL; native Windows + PowerShell is simpler. Use WSL only if you want one-to-one parity with the Mac instructions or already use Linux tools day to day.

---

## 5. Setup path A: fork a working reference repo

If you have access to a reference implementation (the `saling-automation` repo or any fork of it), this is the fast path.

1. Clone the repo to your machine. Any git client works.
   ```bash
   cd ~/Code   # or wherever you keep code
   git clone <repo-url> saling-automation
   cd saling-automation
   ```
2. Copy the env template and fill in your values:
   ```bash
   cp .env.example .env
   open .env       # or use your editor
   ```
3. At minimum, set `LOFTY_API_KEY=<your-jwt-from-step-7>`.
4. Test: `python3 scripts/lofty_api.py test`. You should see your name and Lofty user ID.
5. Skip to section 9 (verify the connection).

The reference repo includes the full Python client, the Worker source files, and the docs. Anything specific to the original setup (the Cloudflare account ID, the original Worker URLs, the original last-name exclusion) you will want to swap for your own.

---

## 6. Setup path B: build it from scratch

If you do not have access to a reference repo, build a minimal version yourself. You only need three files to start.

```
~/Code/lofty-tools/
  .env              # your secrets, git-ignored
  .env.example      # template, committed if you use git
  .claude/
    CLAUDE.md       # context for Cowork
  scripts/
    lofty_api.py    # the Python client (template in section 22)
```

Steps:

1. Create the project folder: `mkdir -p ~/Code/lofty-tools/.claude ~/Code/lofty-tools/scripts && cd ~/Code/lofty-tools`
2. Create a `.gitignore` that excludes `.env` and `data/`:
   ```
   .env
   data/
   __pycache__/
   ```
3. Create `.env.example` with the variable names (no real values):
   ```
   LOFTY_API_KEY=your-lofty-jwt-here
   ```
4. Create `.env` and put your real Lofty JWT in it.
5. Create `scripts/lofty_api.py` using the minimal template in section 22 below.
6. Create `.claude/CLAUDE.md` with a short intro for Claude. A starting point:
   ```markdown
   # Lofty CRM context for Cowork

   Owner: <your name>, <your brokerage>, <your city>.
   Email: <your email> | Phone: <your phone>
   Timezone: America/Los_Angeles  (change to yours)

   Python client: scripts/lofty_api.py. Reads LOFTY_API_KEY from .env.
   Auth header is `Authorization: token <key>`, NOT `Bearer`.
   Rate limit: 10 req/min. Client enforces 6.5s spacing.
   All times: ISO 8601 with offset.
   Address format: STREET, CITY, STATE ZIP.

   Safety: confirm before sending email or SMS. Confirm before deleting.
   Exclude my own last name from lead searches.
   Exclude stages: DNC, Archived, Agents / Vendors.
   ```
7. Test: `python3 scripts/lofty_api.py test`. You should see your name and Lofty user ID.

That is enough to do the basic workflows. Add more methods to the client as you need them.

---

## 7. Step-by-step: get your Lofty API key

1. Log into Lofty in a browser.
2. Go to **Settings → Integrations → API** (Lofty's official path per the public API docs at `https://api.lofty.com/docs/`).
3. Generate a personal access token. It will be a long string starting with `eyJ` (it is a JSON Web Token, or JWT).
4. Copy it. You will paste it into `.env` next.
5. Treat this token like a password. Anyone with it can read and write everything in your Lofty account.

Two facts about this token, taken from the Lofty docs and our testing:

- **It is long-lived.** It does not expire on a schedule. It can be manually revoked.
- **The auth header is `token`, not `Bearer`.** Mixing this up returns error code 200058 ("User in token does not exist"). `Bearer` is OAuth-only.

A quick sanity check from the command line:

```bash
curl -H "Authorization: token YOUR_KEY" https://api.lofty.com/v1.0/me
```

If that returns your user record, the key works. If it returns 200058, you are sending `Bearer` instead of `token`.

---

## 8. Step-by-step: configure `.env`

Open `.env` in your editor. The minimum required variable is:

```
LOFTY_API_KEY=eyJ...
```

The other variables (Worker URLs, leads index source, Jotform tokens) are only needed if you are running the optional Worker-based automations. For a basic Python-client-only setup, you do not need them yet.

Important: never commit `.env` to git. The `.gitignore` should exclude it. Never paste it into chat.

---

## 9. Step-by-step: verify the connection

In Terminal:

```bash
cd ~/Code/saling-automation     # or wherever your project is
python3 scripts/lofty_api.py test
```

Expected output: your name, your Lofty user ID, and your team ID.

If you get an error, jump to section 19 (troubleshooting decision tree).

Other quick command-line sanity checks:

```bash
python3 scripts/lofty_api.py org           # see your organization
python3 scripts/lofty_api.py members       # see your team members
python3 scripts/lofty_api.py tags          # see all your Lofty tags
python3 scripts/lofty_api.py webhooks      # see active webhook subscriptions
```

---

## 10. Step-by-step: open the project in Cowork

In Claude Desktop with Cowork mode enabled, point Cowork at your project folder. Cowork will read `.claude/CLAUDE.md` automatically and now has the context it needs to operate.

Confirm it worked: ask Claude something like "find the client named [name of a lead you know exists]." Claude should call `find_client` from the Python client and return the lead. If it asks you to install something or says it cannot find the script, the folder is not pointed at the right project.

A "hello world" sequence that proves the whole stack works:

1. "What is my Lofty user ID?" (Claude runs `get_me()`.)
2. "Find the lead for [a known client]." (Claude runs `find_client`.)
3. "Show me the most recent activities for that lead." (Claude runs `get_lead_activities`.)
4. "Draft a note for that lead saying we discussed pricing today." (Claude drafts text and asks you to confirm before posting.)
5. You confirm, Claude calls `create_note`.

If all five work, you are fully connected.

---

## 11. The three ways Claude can talk to Lofty

There is a deliberate priority order. Use the highest-priority option that works for your situation.

### Priority 1: Python client (PRIMARY)

`scripts/lofty_api.py`. Uses your long-lived JWT, never goes through OAuth, handles all known quirks. This is what every workflow should use.

Both Claude and you can call it. Claude calls it through its bash tool. You call it from your terminal.

### Priority 2: Cloudflare Workers (for things that need to run in the background)

Workers are JavaScript code that runs in Cloudflare's infrastructure. You only need them if you want:

- A leads index that stays current automatically (no manual refresh script)
- Branded short-link redirects
- A bridge between a Jotform feedback form and Lofty
- An automated SMS to the buyer 2 hours before each showing

Each Worker is a single small JavaScript file, deployable from the Cloudflare dashboard or via the `wrangler` CLI tool. Skip this layer entirely until you actually need one of these capabilities.

### Priority 3: Lofty's MCP plugin (use only when convenient)

Lofty publishes an MCP plugin that Claude can use directly. It uses OAuth, and the OAuth tokens disconnect often. If it happens to be connected when you start a session, fine. If not, do not waste time troubleshooting it. Fall back to the Python client.

---

## 12. Authentication model: the biggest footgun

Three rules:

1. **Auth header for personal access tokens is `token`, not `Bearer`.**
   ```
   Authorization: token eyJ...
   ```
   `Bearer` is for OAuth-issued tokens. Mixing them up returns error 200058.

2. **POST and PUT requests need `Content-Type: application/json` in the headers.**
   ```
   Content-Type: application/json
   ```
   The body should be a JSON object.

3. **GET requests must NOT include `Content-Type`.** Some endpoints return 415 (Unsupported Media Type) if you send it. The reference Python client handles this automatically.

If you are calling the API directly with `curl` or another HTTP client, follow these three rules. If you are using the reference client, they are already handled.

---

## 13. The full list of API quirks

The five worst, in priority order:

1. **`Authorization: token`, not `Bearer`** for personal API keys. Mixing it up returns error 200058.

2. **`/v1.0/leads` silently ignores `sortField`, `keyword`, `startTime`, and oversized `pageSize`.** Sort always returns `leadId` DESC (creation order). `keyword` and `startTime` are dropped. Page size is hard-capped at 25. The workaround is the leads index (section 15).

3. **Activities must use v1.0.** The v2.0 activities endpoint returns empty results no matter what. Always call `/v1.0/leads/<id>/activities`.

4. **Notes endpoint is `POST /v1.0/notes`** with body `{"leadId": <number>, "content": "..."}`. No title field. The lead ID must be a number, not a string. The intuitive path `/v1.0/leads/<id>/notes` returns 404.

5. **Rate limit is 10 requests per minute.** The reference client enforces 6.5s spacing automatically.

The other ones, less common but worth knowing:

6. **GET requests must NOT send `Content-Type`.** Some endpoints return 415 if they receive it.

7. **`phones` and `emails` on a lead are plain string arrays**, not objects. Code that expects `lead.emails[0].address` will fail; the right path is just `lead.emails[0]`.

8. **`get_lead` response is wrapped in `{"lead": {...}}`.** Reference client unwraps it; if you build your own, remember to.

9. **Pagination uses `scrollId` inside `_metadata`** for pages 2+. Page size is hard-capped at 25 regardless of what you ask for.

10. **`/v1.0/listing` does not work with personal API key auth.** Use `/v2.0/listings/search` with `scope="my"` instead.

11. **All times are ISO 8601 with offset.** Pacific looks like `2026-04-15T14:00:00-07:00`. Naive timestamps without an offset get rejected or interpreted in unexpected timezones.

12. **No bulk activity feed exists.** `/v1.0/activities`, `/v2.0/activities`, `/v1.0/events`, `/v1.0/notifications`, `/v1.0/timeline`, and `/v1.0/leadActivities` all return 404. `/v1.0/systemLogs` requires a `leadId`. For cross-lead activity, subscribe to webhook list 3.

13. **Webhook list 3 payloads are pings**: `{leadId, updateTime}` only, no activity type or detail. Consumers must call `/v1.0/leads/{id}/activities` to enrich. Delivery SLA: typically under 1 minute, sometimes up to 5.

14. **Cowork's bash tool has a 45 second hard timeout.** At 6.5s rate limit spacing, that caps a single bash call at about 6 API requests. Long scans (a 650-lead index refresh runs about 3 minutes) must be run outside the bash tool, or chunked.

There are 12 webhook event types: 1 Agent, 2 Lead Info, 3 Lead Activity, 4 Listing Alert, 5 Transaction, 6 Call, 7 Email, 8 Text, 9 Note, 10 Task, 11 Appointment, 12 Pipeline Change. Call, Email, and Text webhooks fire only on MANUAL or LOGGED events, not AUTO.

**Skeptical reminder:** the list is current as of mid-2026 testing on one team's account. Lofty can change behavior. Verify in your environment before relying on a quirk.

---

## 14. Common workflows with examples

### Find a client

```python
api.find_client("Jane Smith", exclude_stages=["DNC", "Archived"])
```

This reads from the leads index (section 15), not from `/v1.0/leads` directly. That is the workaround for quirk #2.

### Find an active listing by full address

```python
api.find_listing_by_address("11513 SW BAMBI LN, Portland, OR 97223")
```

Searches active listings only, in the parsed zip. Returns a slim dict on hit, or `{"error": "address_not_found", ...}` on miss. The address format Lofty expects is `STREET, CITY, STATE ZIP`. The zip is the last 5-digit number.

If the lookup misses, the most common causes (in order) are: wrong city, wrong zip, typo, listing went off market. Confirm with the user before retrying.

### Search the MLS by criteria

```python
api.search_listings({
    "location": {"city": ["Portland"]},
    "price": "400000,650000",
    "beds": "3,",
    "baths": "2,",
    "sqft": "1500,",
    "propertyType": ["Single Family", "Condo"]
}, scope="all")
```

Range syntax: `"min,max"` for both ends, `"min,"` for "at least", `",max"` for "at most".

`scope="all"` searches the full MLS. `scope="my"` searches only your listings. `scope="office"` searches your office's listings.

### Schedule a showing (the canonical flow)

1. `api.prepare_showing(full_address, start_iso, client_name)` returns a payload with the listing, the lead, the prefilled feedback URL, the calendar invite HTML, and the showing-log note text.
2. Create a Google Calendar event using the payload (Claude has Google Calendar tools).
3. `api.create_note(lead_id, showing_note_content)` to leave the showing log on the Lofty lead.

Do NOT use `create_task(APPOINTMENT)` for showings. That creates a request that asks the listing agent to approve, which is not what you want.

### Cancel a showing's queued SMS

```python
api.cancel_showing(lead_id, full_address)
```

Removes the post-showing SMS from the queue so a cancelled tour does not still trigger a buyer feedback text. Returns `{"status": "cancelled", ...}` on success. Pair with a Lofty note like "Showing cancelled at client request."

To inspect the queue: `api.list_pending_showings(lead_id)`.

### Log a note

```python
api.create_note(lead_id, "Spoke with client today. Wants to see homes Saturday afternoon.")
```

Plain text. No title field. The Lofty UI shows the first line as a sort of de-facto title.

### Create a task

```python
api.create_task(
    lead_id=12345,
    content="Call back about pre-approval",
    start_at="2026-05-08T14:00:00-07:00",
    end_at="2026-05-08T14:30:00-07:00",
    task_way="Call",            # Call, Email, Text, Meeting, Other
    # task_type defaults to "TASK". Use "APPOINTMENT" for non-showing meetings only.
    # assigned_role is optional. Valid values: "Agent" or "Assistant".
    # timezone_code defaults to "America/Los_Angeles".
)
```

Body shape gotchas: Lofty rejects `way` (must be `taskWay`), requires `timeZoneCode`, and only accepts `"Agent"` or `"Assistant"` for `assignedRole`. Sending the wrong shape returns error code 20012, "Invalid parameter," with no hint about which key is wrong. The wrapper handles the translation. See `references/quirks.md` #17.

### Send email or SMS (CONFIRM IN CHAT FIRST)

```python
api.send_email(lead_id, subject="Re: Saturday showing", content="...")
api.send_sms(lead_id, content="Confirming 2pm tomorrow at the Bambi Lane house.")
```

Always have Claude confirm with you before calling these.

---

## 15. The leads index (the most important workaround)

Why this exists: quirk #2. Because `/v1.0/leads` cannot be sorted or keyword-searched reliably, every "find this lead" or "who has been active recently" query reads from a separate index instead.

There are two ways to populate the index. Pick one. The Worker option is preferred because it stays fresh automatically; the local file is the fallback.

### Option A: leads-index Cloudflare Worker (preferred)

A small Worker subscribes to Lofty webhook list 2 (Lead Info events). Every lead create, update, or delete event posts to the Worker, which patches its KV store. Lofty's webhook delivery SLA is 1 to 5 minutes, so the index is effectively live. No manual refresh.

To wire this up:

1. Deploy a `leads-index` Worker (source in the reference repo's `worker/` folder).
2. Create a webhook subscription on Lofty pointing to your Worker's `/webhook/<secret>` endpoint:
   ```bash
   python3 scripts/lofty_api.py webhook-create 2 \
     https://<your-subdomain>.workers.dev/webhook/<your-secret>
   ```
3. In `.env`:
   ```
   LOFTY_LEADS_INDEX_SOURCE=worker
   LEADS_INDEX_WORKER_URL=https://<your-subdomain>.workers.dev
   LEADS_INDEX_EXPORT_API_KEY=<your-bearer-token>
   ```
4. Health check:
   ```bash
   curl https://<your-subdomain>.workers.dev/stats \
     -H "Authorization: Bearer $LEADS_INDEX_EXPORT_API_KEY"
   ```
   If `eventCount` is not ticking up over a day, the webhook subscription has dropped. Re-subscribe with the same `webhook-create` command.

### Option B: Local file (fallback)

`data/leads_index.json`. Built by a refresh script that paginates through `/v1.0/leads`. The reference repo's script is `scripts/refresh_leads_index.py` and takes about 3 minutes for 650 leads (rate-limited at 10 req/min, paginated 25 per page).

The reference client falls back to the local file automatically if the Worker is unreachable. If you do not run the Worker at all, just run the refresh script every couple of weeks.

The file is git-ignored because it contains client PII (names, emails, phones). Each computer has its own copy.

The reference client warns (does not error) if the file is more than 14 days old.

---

## 16. Cloudflare Workers (optional automations)

Skip this section if you only want the basic Cowork + Python client setup. Come back when you want one of the four automations below.

The reference repo includes four Workers:

| Worker | Purpose | Deploy method |
|---|---|---|
| `leads-index` | Live leads index, webhook-fed | Dashboard paste or wrangler |
| `short-links` | Branded short-link redirector | Dashboard paste or wrangler |
| `jotform-to-lofty` | Receives Jotform feedback, writes Lofty note + emails recap + stores in D1 | Wrangler |
| `showing-sms` | Sends a 2-hour-before-showing SMS using Durable Object alarms | Wrangler ONLY (uses DOs) |

**Important: `showing-sms` requires the Cloudflare Workers Paid plan ($5/month) because it uses Durable Objects.** The other three run on the free plan.

For the Workers that use `wrangler` to deploy, you will also need:

- The `wrangler` CLI installed (`npm install -g wrangler`)
- A Cloudflare API token (`CLOUDFLARE_API_TOKEN` in `.env`) with the "Edit Cloudflare Workers" template

Each Worker has its own `wrangler.<name>.toml` config file in the reference repo's `worker/` folder. Deploy with:

```bash
cd worker
wrangler deploy -c wrangler.<name>.toml
```

The Workers each have their own runbook in the reference docs. The most common operations:

- `jotform-to-lofty`: full runbook in `docs/phase2-feedback-db-deploy.md`
- `showing-sms`: Durable Object alarms make this self-contained; cancellation is handled by the Python client's `cancel_showing` method
- `leads-index`: setup and health checks in section 15 above
- `short-links`: simple bearer-auth shortener

A skeptical note about Workers in general: every Worker URL in this guide is a placeholder. Your real URL is `https://<worker-name>.<your-subdomain>.workers.dev`. Where `<your-subdomain>` is the random string Cloudflare assigned to your account, visible in the dashboard.

---

## 17. Best practices

These are the rules we settled on after running this stack for months. Each one came from a specific mistake. Follow them and you will avoid those mistakes.

### Auth and secrets

- **Never paste your API key into chat.** Not in Claude, not in Slack, not in email. If you accidentally do, rotate it immediately (section 20).
- **One `.env` per machine.** They are not synced. Each computer that runs the client needs its own.
- **`.env` is git-ignored**, always. Verify by running `git status` after creating it; the file should not appear.
- **Rotate keys periodically.** Lofty JWTs do not expire, but a compromised key is forever. A 90-day rotation cadence is a reasonable default.

### Calling the API

- **Use the index, not raw `/v1.0/leads`.** The endpoint silently drops sort and keyword. The index is the only reliable way to find a lead by name.
- **Use v1.0 for activities.** The v2.0 endpoint returns empty.
- **Always pass times as ISO 8601 with offset.** Pacific is `-07:00` during DST, `-08:00` outside DST. The reference client handles this if you give it a `datetime` object.
- **Address format is exact: `STREET, CITY, STATE ZIP`.** No comma after the state. No "Apt #" suffixes if you can avoid them.
- **Confirm with the user before sending email or SMS.** This is non-negotiable. Claude in this stack should always draft, then ask, then send.
- **Confirm with the user before deleting anything.** Same logic.

### Data hygiene

- **Always exclude your own last name from lead searches.** Otherwise you keep matching yourself when searching tagged leads.
- **Always exclude `DNC`, `Archived`, and `Agents / Vendors` stages.** Otherwise you spam old contacts.
- **Refresh the leads index before you trust it for "today's activity."** The local file is only as fresh as the last refresh. The Worker is fresh within 5 minutes.

### Cowork-specific

- **Do not run long scans inside the Cowork bash tool.** It has a 45-second hard timeout. The 650-lead refresh takes about 3 minutes. Run it from your real terminal, or chunk it.
- **Keep `.claude/CLAUDE.md` lean.** It loads every session and consumes context. The reference repo offloads detail to `docs/` files that load on demand.
- **Trust but verify when Claude reports completion.** Ask it what specifically it changed, and spot-check one or two records in Lofty.

### Workflow

- **For showings, always Google Calendar plus a Lofty showing-log note.** Do not use `create_task(APPOINTMENT)` for showings.
- **Verify the lead before logging a note.** If you ask "find Jane Smith and add a note about today's showing," have Claude confirm the lead ID before posting. There may be more than one Jane Smith.
- **For listing lookups, always verify the address with the human if the search misses.** A miss usually means a typo.

### Skepticism

- **Verify each quirk in your own environment.** This guide is based on one team's testing. Lofty can change behavior on any deploy.
- **When something behaves unexpectedly, suspect the rate limiter first.** A burst of "this works sometimes" failures is almost always rate-limit-related.
- **When in doubt, read the response body.** The reference client returns `{"error": True, "status": <code>, "body": "..."}` on HTTP errors. The body usually says exactly what is wrong.

---

## 18. Tips for prompting Claude about Lofty

Claude is good at this stack, but better prompts give better results. A few patterns that work:

**Be specific with names and addresses.** "Find Jane Smith" is OK; "Find Jane Smith, the buyer who saw 14523 SE Steele last month" is better. The second prompt lets Claude disambiguate if there are multiple Jane Smiths.

**Ask for a dry run first.** "Tell me what you would do to schedule a showing at 11513 SW Bambi Ln on Friday at 2pm with Jane Smith, but do not execute yet." Then review the plan, then say "go ahead."

**Confirm the lead ID before any write.** "Before logging the note, tell me the lead ID and the lead's email so I can confirm we are writing to the right record."

**Ask for the exact API call when learning.** "What endpoint and body would `create_note` send for that?" This is a great way to learn the API while Claude does the work.

**For showings, give the full address and exact time.** Lofty will not match a partial address, and the calendar invite needs an exact start time with timezone offset.

**When something fails, ask Claude to read the response body.** "What did the API actually return?" The body is usually the answer.

---

## 19. Troubleshooting decision tree

Start at the top. Stop when something matches.

- **`python3 scripts/lofty_api.py test` fails with "Missing required environment variable: LOFTY_API_KEY".**
  → Your `.env` is not being loaded, or the key name is wrong. Check that `.env` is in the project root and has `LOFTY_API_KEY=eyJ...`.

- **`test` fails with "Bad credentials" or HTTP 401.**
  → The key was rotated, revoked, or copied wrong. Generate a new one in Lofty Settings, paste into `.env`, and update every other place it is stored (section 20).

- **Any call returns error 200058 ("User in token does not exist").**
  → Wrong auth header. You are sending `Bearer` instead of `token`. The reference client uses `token`; if you built your own client, check its `_request` method.

- **`find_client` raises `RuntimeError` with "no leads index file".**
  → No index exists yet. Either set `LOFTY_LEADS_INDEX_SOURCE=worker` and configure the Worker, or run the local refresh script once.

- **A search "should have" returned a lead but did not.**
  → The local index is stale, or the lead was created after the last refresh. Refresh the index, or flip to the Worker source.

- **`/v1.0/leads` returns leads, but the wrong order or filtered by something other than what you asked.**
  → Quirk #2: sort and keyword are silently dropped. Use the index instead.

- **A GET request returns 415 (Unsupported Media Type).**
  → You are sending `Content-Type` on a GET. Drop it. Quirk #6.

- **A POST to `/v1.0/leads/<id>/notes` returns 404.**
  → Wrong path. The right one is `POST /v1.0/notes` with `{"leadId": <number>, "content": "..."}`. Quirk #4.

- **An activities call returns empty even though the lead has activity.**
  → You are calling `/v2.0/activities`. Use `/v1.0/leads/<id>/activities`. Quirk #3.

- **A long-running script times out at 45 seconds when run via Claude.**
  → Cowork's bash tool has a 45s hard timeout. Run the script in your real terminal instead.

- **Worker `/stats` shows `eventCount` not changing over a day.**
  → The webhook subscription has dropped or the secret rotated. Re-subscribe.

- **The MCP plugin is disconnected.**
  → Reconnect it in Cowork settings, or just use the Python client. The plugin is not the primary path.

For anything else, read the response body. The Lofty API is usually pretty good about saying what is wrong.

---

## 20. Key rotation checklist

When `LOFTY_API_KEY` changes, update ALL of these places:

1. `.env` on every computer that runs the Python client.
2. The Cloudflare Worker secret `LOFTY_API_KEY` on every Worker that calls Lofty (typically `jotform-to-lofty` and `showing-sms`).
3. Any copy of the Python client kept outside the main repo (legacy plugin folders, archive copies, etc.).

For other secrets:

- `SHORTENER_API_KEY`: rotate in `.env` AND the `short-links` Worker secret.
- `LOFTY_PREFERENCES_API_KEY`: rotate in `.env` AND the `jotform-to-lofty` Worker secret.
- `LEADS_INDEX_EXPORT_API_KEY`: rotate in `.env` AND the `leads-index` Worker secret.
- `LOFTY_WEBHOOK_SECRET`: when this rotates, you must also re-subscribe the webhook with the new URL path.

The Lofty JWT does not expire naturally but CAN be manually revoked, so rotation is on you.

---

## 21. Glossary

- **Cowork:** Claude Desktop's mode that gives Claude file tools, a sandboxed bash shell, and the ability to read your project's CLAUDE.md.
- **CLAUDE.md:** A markdown file at the root of your project (specifically, `.claude/CLAUDE.md`) that loads into every Cowork session as context.
- **JWT:** JSON Web Token. Lofty's personal access tokens are JWTs. They look like long strings starting with `eyJ`.
- **MCP:** Model Context Protocol. The way Claude connects to external tools. Lofty has an official MCP plugin, but it is not reliable.
- **Worker:** A small JavaScript program that runs in Cloudflare's infrastructure. We use them for things that need to run in the background.
- **Durable Object (DO):** A persistent state primitive in Cloudflare Workers. The `showing-sms` Worker uses one DO per scheduled showing, with a precise alarm for send time.
- **KV:** Cloudflare's key-value store. The leads index and short-link tables both live in KV.
- **D1:** Cloudflare's SQL database. Stores buyer feedback for trend analysis.
- **Webhook list:** Lofty groups webhook event types into "lists." List 2 is Lead Info events. List 3 is Lead Activity events.
- **Stage / Pipeline:** Lofty's lead workflow states. `DNC` (do not contact), `Archived`, and `Agents / Vendors` are the stages most teams want to exclude from queries.
- **The index:** Shorthand for the leads index, the workaround for the broken `/v1.0/leads` sort and keyword parameters.
- **`scrollId`:** Lofty's pagination token. Lives in `_metadata` on lead search responses.

---

## 22. A minimal Python client template (for the from-scratch path)

If you are not forking the reference repo, this is enough to get started. It handles the auth header, the rate limit, and the most common methods. Save as `scripts/lofty_api.py` and add methods as you need them.

```python
#!/usr/bin/env python3
"""Minimal Lofty API client. Expand as needed."""
import json, os, time
import urllib.request, urllib.parse, urllib.error
from pathlib import Path

# ── .env loader (no external dependency) ──────────────────────
def _load_dotenv():
    here = Path(__file__).resolve().parent
    for candidate in [here / ".env", here.parent / ".env"]:
        if candidate.is_file():
            for line in candidate.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k and k not in os.environ:
                    os.environ[k] = v
            return

_load_dotenv()

BASE_URL = "https://api.lofty.com"
RATE_LIMIT_DELAY = 6.5  # seconds between calls (10 req/min)


class LoftyAPI:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get("LOFTY_API_KEY")
        if not self.api_key:
            raise RuntimeError(
                "Missing LOFTY_API_KEY. Add it to .env at the project root."
            )
        self._last_call = 0

    def _rate_limit(self):
        elapsed = time.time() - self._last_call
        if elapsed < RATE_LIMIT_DELAY:
            time.sleep(RATE_LIMIT_DELAY - elapsed)
        self._last_call = time.time()

    def _request(self, method, path, body=None, query_params=None):
        self._rate_limit()
        url = f"{BASE_URL}{path}"
        if query_params:
            filtered = {k: str(v) for k, v in query_params.items()
                        if v is not None and v != ""}
            if filtered:
                url += "?" + urllib.parse.urlencode(filtered)
        headers = {"Authorization": f"token {self.api_key}"}
        data = None
        if body and method in ("POST", "PUT"):
            headers["Content-Type"] = "application/json"
            data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    return raw
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8") if e.fp else ""
            except Exception:
                pass
            return {"error": True, "status": e.code, "body": body}

    # ── Common methods (add more as needed) ──────────────────
    def get_me(self):
        return self._request("GET", "/v1.0/me")

    def search_leads(self, page=1, page_size=25):
        # Note: Lofty silently ignores keyword and sort. For lead lookups,
        # use a leads index instead of this method.
        return self._request("GET", "/v1.0/leads", query_params={
            "page": page, "pageSize": page_size,
        })

    def get_lead(self, lead_id):
        result = self._request("GET", f"/v1.0/leads/{lead_id}")
        if isinstance(result, dict) and "lead" in result:
            return result["lead"]
        return result

    def get_lead_activities(self, lead_id, limit=20):
        # v1.0 only. v2.0 returns empty.
        return self._request("GET", f"/v1.0/leads/{lead_id}/activities",
                             query_params={"limit": limit})

    def create_note(self, lead_id, content):
        # POST /v1.0/notes with leadId in the body. /v1.0/leads/<id>/notes is 404.
        return self._request("POST", "/v1.0/notes",
                             body={"leadId": int(lead_id), "content": content})

    def get_notes(self, lead_id, page=1, page_size=25):
        return self._request("GET", "/v1.0/notes",
                             query_params={"leadId": lead_id,
                                           "page": page, "pageSize": page_size})


if __name__ == "__main__":
    import sys
    api = LoftyAPI()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "test"
    if cmd == "test":
        me = api.get_me()
        print(json.dumps(me, indent=2))
    elif cmd == "lead":
        print(json.dumps(api.get_lead(sys.argv[2]), indent=2))
    elif cmd == "activities":
        print(json.dumps(api.get_lead_activities(sys.argv[2]), indent=2))
    else:
        print(f"Unknown command: {cmd}")
```

This is intentionally minimal. The reference client is several hundred lines because it covers showing scheduling, the leads index, the Worker integrations, and the helpers around them. Expand this template gradually as you need more capability.

---

## 23. Where to look for deeper detail

If you have access to the reference repo, the following docs go deeper than this guide:

- `docs/api-reference.md`: full Python client method list, endpoint tables, listing search pattern, calendar invite template
- `docs/lofty-quirks.md`: the complete known-quirks list (longer than the top 5)
- `docs/architecture.md`: what each Worker does, what is on the roadmap, the project file tree
- `docs/troubleshooting.md`: debugging flow, key rotation checklist
- `docs/local-leads-index.md`: index build, refresh, staleness rules
- `docs/phase2-feedback-db-deploy.md`: Jotform-to-Lofty Worker runbook

If you are building from scratch, the official Lofty API docs at `https://api.lofty.com/docs/index.html` are partial but useful as a starting point. Expect to learn most of what you need by trial and error against the live API, which is exactly how the quirks list above came to be.

---

## Final checklist

Before you call this setup "done":

- [ ] `python3 scripts/lofty_api.py test` returns your name and Lofty user ID
- [ ] `.env` is git-ignored (run `git status`, the file should not appear)
- [ ] You can find a known lead by name from Cowork
- [ ] You can pull that lead's recent activities
- [ ] You can post a test note (then delete it from Lofty if you want)
- [ ] You have read the top 5 quirks and the best practices section
- [ ] If you are running Workers, all four health checks pass

When all of those are checked, you are good to go.

---

*This guide is meant to be customized and extended. The setup paths are starting points, not prescriptions. The quirks and best practices are based on real testing against the Lofty API, but they are not infallible. When in doubt, verify in your own environment, read the response body, and ask Claude to walk you through what it is about to do before it does it.*
