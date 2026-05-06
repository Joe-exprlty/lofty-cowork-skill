---
name: lofty-cowork-helper
description: Connect Claude to the Lofty CRM API and operate it day to day for real estate agents and VAs. Use this skill whenever the user mentions Lofty, Lofty CRM, Lofty API, connecting Cowork to Lofty, finding a lead in Lofty, logging a Lofty note, scheduling a showing, post-showing SMS, leads index, jotform feedback, error 200058, Lofty webhooks, or any Lofty automation task. Trigger on first-time setup phrases like "set up Lofty," "connect my CRM," "I just installed this," and on workflow questions like "how do I find a lead," "log a showing," "log a note for," "search the MLS," "schedule a showing for." Trigger on troubleshooting phrases like "Lofty error," "200058," "auth failed," "this Lofty call returned." Trigger even when the user mentions Lofty casually or in passing, such as "the Lofty thing," "my CRM is Lofty," or "in Lofty." Do NOT trigger for general real estate questions that have nothing to do with the Lofty API or Lofty CRM.
---

# Lofty CRM Helper for Claude Cowork

This skill turns Claude into a working Lofty CRM operator for real estate agents and VAs. It handles first-time setup, common workflows (finding leads, logging notes, scheduling showings, searching the MLS), and troubleshooting the API's well-known quirks. The skill ships with a working starter Python client; the user does not need to write code.

## Decide what the user needs first

Before doing anything, figure out where the user is:

- **No `.env` file in their workspace** → first-time setup. Use the "First-time setup" section below.
- **`.env` exists but `python3 scripts/lofty_api.py test` has not been run yet** → finish setup. Run the test and report the result.
- **A specific Lofty task in mind** ("find a lead," "log a note," "schedule a showing") → use the "Common workflows" section, which points at `references/workflows.md` for full recipes.
- **An error or unexpected behavior** → use "When something behaves unexpectedly" below, which points at `references/quirks.md` and the troubleshooting decision tree in `references/full-guide.md` (section 19).

If the user mentions Lofty in passing without a clear task, ask one short clarifying question: "Are you setting up Lofty for the first time, or is there a specific task you want help with?"

## First-time setup

Run through these steps in order. Stop at the first failure and help the user fix it before moving on.

### 1. Confirm prerequisites and detect OS

First, figure out the user's OS. Ask "Are you on Mac, Windows, or Linux?" if you cannot tell from context. The Python command differs by platform:

- **Mac / Linux:** `python3` (and `python3 --version` to check)
- **Windows:** `python` (and `python --version` to check). If `python` does not work, try `py`.

Throughout setup, where instructions say `python3 ...`, substitute `python ...` for Windows users. The starter Python client itself is identical on all three platforms.

Then confirm with the user:

- Python 3.11 or newer is installed
- A Lofty account with API access (Settings, API Keys section is visible)
- A project folder selected in Cowork (this is where setup will install files)
- On Windows: they are using PowerShell or Windows Terminal, not the older Command Prompt

Workspace path conventions used below:
- Mac / Linux: `~/Code/lofty-tools`
- Windows PowerShell: `$HOME\Code\lofty-tools`
- Windows plain text: `C:\Users\<username>\Code\lofty-tools`

If any prerequisite is missing, give the user install steps before continuing. For Python on Windows, the easiest path is the Microsoft Store (search "Python 3.12" or newer) or python.org with "Add to PATH" checked during install.

### 2. Get a Lofty API key

Tell the user:

> Log into Lofty in your browser. Go to Settings, then API Keys. Click Generate. Copy the long string starting with `eyJ`. That's your token. Treat it like a password.

Do NOT ask the user to paste the key into chat. They paste it into `.env` in the next step.

### 3. Install the starter files

In the user's workspace, create the structure:

```
<workspace>/
  .claude/
    CLAUDE.md       (from assets/CLAUDE.md.template)
  scripts/
    lofty_api.py    (from assets/lofty_api.py)
  .env              (from assets/env-template, then user pastes their key)
  .gitignore        (excludes .env)
```

The asset files are bundled with this skill. Copy them from the skill's `assets/` folder into the user's workspace. If you cannot find the skill's path, ask the user to look in the Cowork plugin directory for `lofty-cowork-helper/assets/`.

For the `.gitignore`, write:
```
.env
data/
__pycache__/
```

### 4. Customize CLAUDE.md

Open `<workspace>/.claude/CLAUDE.md`. It has placeholders like `<Your Name>`, `<your-email>`, etc. Walk the user through each one and replace it with their actual info. The most important fields:

- Owner name, email, phone, brokerage, city, timezone
- Their Lofty user ID and team ID (they can get these from `python3 scripts/lofty_api.py test` once setup is done)
- Their last name (used to exclude themselves from lead searches)

### 5. Set the API key

Open `<workspace>/.env`. Find the line `LOFTY_API_KEY=your-lofty-jwt-here`. Ask the user to paste their key in place of `your-lofty-jwt-here`. Save the file.

### 6. Test the connection

Run the test from the workspace folder:

- Mac / Linux: `python3 scripts/lofty_api.py test`
- Windows: `python scripts/lofty_api.py test` (or `py scripts/lofty_api.py test` if `python` is not on PATH)

Expected output: a JSON object with their name, Lofty user ID, and team ID.

If it fails:
- "Missing LOFTY_API_KEY" → the `.env` file is not where the script expects it. Confirm it sits in the workspace root, not in `scripts/`.
- "Bad credentials" or HTTP 401 → the key is wrong or revoked. They need to generate a new one in Lofty Settings.
- Error 200058 → wrong auth header. The starter client does not have this bug, but check that they did not edit `lofty_api.py`.
- "python is not recognized" (Windows) → Python is not on PATH. They can reinstall from python.org with "Add to PATH" checked, or use `py` instead.
- "command not found: python3" (Mac) → Python 3 is not installed. Install via Homebrew (`brew install python`) or python.org.

### 7. Confirm and hand off

Tell the user setup is done and list what they can ask for now:

- "Find the lead for [name]"
- "Show me [name]'s recent activity"
- "Log a note on lead [ID] saying [content]"
- "Pull my recent leads" (returns the most recent 25)
- "Show me my Lofty team" / "tags" / "webhooks"

For showings, MLS search, the leads index, and Cloudflare Workers, see `references/extending.md` for what to build next.

## Common workflows

For each workflow below, the full recipe (with edge cases) lives in `references/workflows.md`. Read that file before executing if you are unsure of any step.

- **Find a client by name.** Starter client uses `search_leads()` (paginated, recent-first). For real lookup by name in a large CRM, build a leads index (see "Building on this skill" below).
- **Log a note.** `api.create_note(lead_id, content)`. Always confirm the lead ID with the user before posting.
- **Get activity feed.** `api.get_lead_activities(lead_id)`. Use v1.0; v2.0 returns empty.
- **Schedule a showing.** Requires extending the starter (see `references/extending.md`). The canonical flow is: prepare_showing helper → Google Calendar event → Lofty showing-log note. Do NOT use `create_task(APPOINTMENT)`; that triggers listing-agent approval.
- **Send email or SMS.** ALWAYS confirm content with the user before calling `send_email` or `send_sms`. This is non-negotiable.

## Top quirks (memorize these)

The five worst, in order of how often they bite:

1. **Auth header is `token`, not `Bearer`.** Mixing it up returns error 200058. The starter client uses the right one.
2. **`/v1.0/leads` silently ignores `keyword` and `sortField`.** Sort always returns `leadId` DESC. For real lead search, build a leads index. Section 15 of `references/full-guide.md` has the pattern.
3. **Activities must use v1.0.** `/v2.0/leads/<id>/activities` returns empty.
4. **Notes go to `POST /v1.0/notes`** with `{"leadId": <number>, "content": "..."}`. The intuitive `/v1.0/leads/<id>/notes` returns 404. `leadId` must be a number, not a string.
5. **Rate limit is 10 requests per minute.** Starter client enforces 6.5s spacing.

The full quirks list (14 documented quirks) lives in `references/quirks.md`. Read it when a Lofty call behaves unexpectedly.

## Safety rules (always)

These rules came from real mistakes. Do not skip them.

- **Confirm with the user before sending any email or SMS.**
- **Confirm before deleting anything.**
- **Never paste the API key into chat.** Treat it like a password.
- **Always exclude the user's own last name from lead searches.** This is set in `.claude/CLAUDE.md`. Use it.
- **Always exclude these stages from queries:** `DNC`, `Archived`, `Agents / Vendors`.
- **Verify the lead ID before logging a note.** A name match could be the wrong person; confirm with the user first.
- **Do not run long scans inside Cowork's bash tool.** It has a 45-second hard timeout. Anything longer (like a leads index refresh, ~3 minutes for 650 leads) needs to run from the user's terminal.
- **Times use ISO 8601 with offset.** Pacific is `-07:00` in DST, `-08:00` outside.
- **Address format Lofty expects:** `STREET, CITY, STATE ZIP`.

## When something behaves unexpectedly

Order of investigation:

1. Read the response body. The starter client returns `{"error": True, "status": <code>, "body": "..."}` on HTTP errors. The body usually says exactly what is wrong.
2. Match the error against `references/quirks.md`.
3. If still stuck, walk the troubleshooting decision tree in `references/full-guide.md` section 19.

## Building on this skill

The starter client covers leads, notes, and activities. For more, see `references/extending.md`:

- Adding showing scheduling helpers (`prepare_showing`, `find_listing_by_address`)
- Building a leads index for real name search
- Adding MLS search (`search_listings` with full filter syntax)
- Adding tasks, email, SMS
- Deploying the four Cloudflare Workers (leads-index, short-links, jotform-to-lofty, showing-sms)
- Subscribing to webhooks for live updates

Each addition has a pattern in the full guide. Use the same `_request` plumbing the starter client provides; do not reinvent it.

## Skeptical reminders

- The quirks documented here are based on one team's testing of the Lofty API in mid-2026. Lofty can change behavior. When in doubt, verify in the user's environment.
- The Worker subdomain examples in `references/full-guide.md` are placeholders; the user's real URLs will be different.
- Trust but verify. When the user reports something worked, ask them to spot-check one record in Lofty's UI before moving on.

## File map

- `SKILL.md` (this file) - what to do, when, in plain prose
- `assets/lofty_api.py` - the starter Python client to install in the user's workspace
- `assets/env-template` - `.env` template
- `assets/CLAUDE.md.template` - Cowork context file template
- `scripts/setup_check.py` - quick sanity check that runs from the user's workspace and reports what is and is not configured
- `references/full-guide.md` - comprehensive setup, learning, and best practices guide (~850 lines)
- `references/quirks.md` - full quirks list with workarounds
- `references/workflows.md` - step-by-step recipes for common tasks
- `references/extending.md` - how to add capability beyond the starter
