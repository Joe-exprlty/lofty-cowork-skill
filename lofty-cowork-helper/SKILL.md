---
name: lofty-cowork-helper
description: Connect Claude to the Lofty CRM API and operate it day to day for real estate agents and VAs. Use this skill whenever the user mentions Lofty, Lofty CRM, Lofty API, connecting Cowork to Lofty, finding a lead in Lofty, logging a Lofty note, scheduling a showing, post-showing SMS, leads index, jotform feedback, error 200058, Lofty webhooks, or any Lofty automation task. Trigger on first-time setup phrases like "set up Lofty," "connect my CRM," "I just installed this," and on workflow questions like "how do I find a lead," "log a showing," "log a note for," "search the MLS," "schedule a showing for." Trigger on troubleshooting phrases like "Lofty error," "200058," "auth failed," "this Lofty call returned." Trigger even when the user mentions Lofty casually or in passing, such as "the Lofty thing," "my CRM is Lofty," or "in Lofty." Do NOT trigger for general real estate questions that have nothing to do with the Lofty API or Lofty CRM.
---

# Lofty CRM Helper for Claude Cowork

This skill turns Claude into a working Lofty CRM operator for real estate agents and VAs. It handles first-time setup, common workflows (finding leads, logging notes, scheduling showings, searching the MLS), and troubleshooting the API's well-known quirks. It defaults to Easy Mode so non-technical users can finish setup and get to their first lead lookup in under 15 minutes.

## How to start a session

When the skill activates, decide which path the user is on:

- **No `.env` file in their workspace** → first-time setup. Run **Easy Mode** (the default).
- **`.env` exists but no successful test connection yet** → finish setup. Run the connection test, report result.
- **A specific Lofty task in mind** ("find a lead," "log a note," "schedule a showing") → use the "Common workflows" section, which points at `references/workflows.md` for full recipes.
- **An error or unexpected behavior** → use "When something behaves unexpectedly" below, which points at `references/quirks.md` and the troubleshooting decision tree in `references/full-guide.md`.

If the user mentions Lofty in passing without a clear task, ask one short clarifying question: "Are you setting up Lofty for the first time, or is there a specific task you want help with?"

## Two modes for setup

**Easy Mode** is the default. Use it when a user asks to set up Lofty and you have no signal that they are technical. It uses plain English (no `.env`, no "JWT," no "scripts folder"), runs everything possible automatically using the bash tool, asks for personal info one short question at a time, and ends with a guided demo using their real data.

**Power User Mode** is the fast path. Use it ONLY if the user explicitly says one of: "I'm technical," "skip ahead," "fast version," "I know what I'm doing," "Power User Mode," or similar. It uses precise terminology, batches questions, and skips the guided demo at the end. The exact Power User Mode steps are documented below.

If you cannot tell which mode to use, default to Easy Mode. Better to over-explain than to confuse a non-technical user.

---

## Easy Mode setup (the default)

Walk through these steps in order. Stop at the first failure and help the user fix it before moving on. Use plain English throughout. Never mention `.env`, `JWT`, "your scripts folder," "command line," "terminal," or "config file" unless the user uses those words first.

### 1. Greet and check the room

Say something like:

> "Hi. I can help you connect Claude to your Lofty CRM. This takes about 15 minutes. I'll do most of the work, and I'll ask you a few simple questions along the way. Ready to start?"

Wait for a yes. If they say they are technical or want the fast version, switch to Power User Mode below.

### 2. Detect their operating system silently

Run a quick bash command to detect the OS. Don't ask the user. Use this to know which Python command to use later:

- macOS or Linux: `python3`
- Windows: `python` (or `py` if `python` isn't on PATH)

If the bash tool isn't available for some reason, ask "Are you on a Mac, a Windows computer, or Linux?" but only if necessary.

### 3. Check that Python is installed

Run a quick check (silently) using bash. If Python 3.11 or newer is available, move on to step 4 without comment.

If Python is missing or too old, tell the user:

> "I need a small program called Python on your computer to make this work. It's free and safe. I'll open the download page in your browser. Click the button to download Python for [their OS], then run the installer. When it asks 'Add Python to PATH' or 'Install Now,' click that. Tell me when it's installed and we'll keep going."

Open https://www.python.org/downloads/ in their browser if possible. After they confirm install, re-check Python silently.

### 4. Get their Lofty API key

Tell the user:

> "Now I need a special code from Lofty so Claude can talk to it. Here's how to get it. Open Lofty in your web browser. Click your profile picture in the top right corner of Lofty. Click 'Personal Settings.' On the left side menu, click 'Integrations.' Scroll all the way to the bottom of the page until you see a section called 'API Keys.' On the right side of that section, click the '+ Create API Key' button. Lofty will show you a long code. Copy the whole code. Tell me when you have it copied."

If they say Lofty doesn't have an API Keys section, tell them:

> "It looks like your Lofty plan doesn't have API access turned on. Reach out to Lofty support and ask them to enable API access for your account. Once they do, come back and we'll finish setting this up."

Stop the setup at that point. There is nothing more to do until Lofty support turns it on.

Important: do NOT ask the user to paste the API key into chat. They will paste it into a settings file in step 6.

### 5. Pick a workspace folder and install the starter files

Default workspace folder: `~/Code/lofty-tools`. Create it silently if it doesn't exist. Use the bash tool to:

- Create the folder structure: `~/Code/lofty-tools/.claude/`, `~/Code/lofty-tools/scripts/`, `~/Code/lofty-tools/data/` (data folder for the leads index later).
- Copy `assets/lofty_api.py` from this skill's folder into `~/Code/lofty-tools/scripts/lofty_api.py`.
- Copy `assets/env-template` into `~/Code/lofty-tools/.env`.
- Copy `assets/CLAUDE.md.template` into `~/Code/lofty-tools/.claude/CLAUDE.md`.
- Write a `.gitignore` in `~/Code/lofty-tools/` containing `.env`, `data/`, `__pycache__/`.

Tell the user once when done:

> "I've set up your project folder at `~/Code/lofty-tools`. You don't need to open it. I'll handle everything from here."

In Claude Desktop, point Cowork at that folder. If Cowork isn't already pointed there, tell the user how to point it: "In Claude Desktop, click the folder icon (or your project picker) and pick `~/Code/lofty-tools`."

### 6. Save their Lofty code

Tell the user:

> "Now let's save your Lofty code so Claude can use it. I'll open the file where it goes. When it opens, you'll see a line that says `LOFTY_API_KEY=your-lofty-jwt-here`. Replace `your-lofty-jwt-here` with the long code you copied from Lofty. Save the file (Cmd+S on Mac, Ctrl+S on Windows). Tell me when you've saved it."

Use the bash `open` (Mac) or `start` (Windows) command to open `~/Code/lofty-tools/.env` in the user's default text editor. After they confirm save, validate the key was set (read the file, check for non-placeholder value).

### 7. Ask for personal info, one question at a time

Ask each of these as a separate question. Wait for an answer. Update `~/Code/lofty-tools/.claude/CLAUDE.md` after each answer (replace placeholders silently).

1. "What's your full name?" → owner name
2. "What's your brokerage name?" → e.g., "eXp Realty"
3. "What city or area do you serve?" → e.g., "Portland, Oregon"
4. "What's the best phone number for clients to reach you?" → owner phone
5. "What's your work email address?" → owner email
6. "What's your last name? I'll use this so Claude doesn't mistake you for a lead when searching." → for lead-search exclusion
7. "What's your timezone? Like 'Pacific' or 'Eastern.'" → convert to America/Los_Angeles, America/New_York, etc.

Do NOT ask for: Lofty user ID, team ID, MLS agent codes. Those will fill in later from the connection test.

After all answers, write the customized `CLAUDE.md` to disk.

### 8. Run the connection test

Run `python3 scripts/lofty_api.py test` (or `python` on Windows) from the workspace folder using the bash tool. Capture the output.

If it returns the user's name and Lofty user ID:

> "You're connected. Your Lofty account is now talking to Claude."

Also extract the user ID and team ID from the response and update `CLAUDE.md` silently.

If it fails:

- "Bad credentials" or HTTP 401: "The code you copied from Lofty isn't being accepted. Let's try once more. In Lofty, go back to Personal Settings, then Integrations, then API Keys. Generate a new code (you can revoke the old one first). Replace the code in our settings file. Tell me when you've saved it."
- Other errors: tell the user "Something didn't work. Check the help section on the website for help: github.com/Joe-exprlty/lofty-cowork-skill" and stop. Do not loop on errors more than twice.

### 9. Guided demo

Once connected, do a real demo using their data. This is the moment that makes them excited about what they have.

Say:

> "Let's try it together. What's the name of one of your leads? Just first and last name is fine."

When they answer, run `find_client` (or `search_leads` filtered) to look up that person. Show them the result clearly:

> "Found her. Jane Smith, in your pipeline at the [stage] stage. Here's her phone, email, and when you last heard from her: ..."

Then offer next steps:

> "Now you can ask me things like:
> - 'Show me Jane's recent activity' to see what she's been browsing on your site
> - 'Log a note on Jane's lead saying we discussed pricing today' (I'll draft and ask you before I post)
> - 'Pull my recent leads' to see your 25 most recent ones
> - 'Find another lead' to look up someone else
>
> Try one. I'll be here."

### 10. Hand-off

After the demo, tell them:

> "You're all set up. The skill stays installed, so any time you start a new chat with Claude and mention Lofty, I'll be ready. Save my number for later: github.com/Joe-exprlty/lofty-cowork-skill is the help page."

---

## Power User Mode setup

Use this only if the user explicitly says they're technical or asks for the fast version. Skip the warm-up and condense everything.

1. Confirm OS, Python version, and that they have a Lofty API key already in hand (or pause for them to grab one from Lofty Personal Settings → Integrations → API Keys → Create).
2. In one message, list what you'll do: create `~/Code/lofty-tools/{scripts,.claude,data}`, drop the starter Python client, the `.env` template, and `CLAUDE.md.template`, write a `.gitignore`.
3. Tell them to paste their key into `.env` and save. Wait.
4. Ask them to paste the customizations they want in `CLAUDE.md` as a single message (name, brokerage, city, phone, email, last name, timezone). Update the file in one go.
5. Run `python3 scripts/lofty_api.py test`. Confirm.
6. Skip the guided demo. Just hand off: "Connected. Try `api.find_client('name')` or ask me a workflow question."

---

## Common workflows

For each workflow below, the full recipe (with edge cases) lives in `references/workflows.md`. Read that file before executing if you are unsure of any step.

- **Find a client by name.** Starter client uses `search_leads()` (paginated, recent-first). For real lookup by name in a large CRM, build a leads index (see `references/extending.md`).
- **Log a note.** `api.create_note(lead_id, content)`. Always confirm the lead ID with the user before posting.
- **Get activity feed.** `api.get_lead_activities(lead_id)`. Use v1.0; v2.0 returns empty.
- **Schedule a showing.** Requires extending the starter (see `references/extending.md`). The canonical flow is: prepare_showing helper → Google Calendar event → Lofty showing-log note. Do NOT use `create_task(APPOINTMENT)`; that triggers listing-agent approval.
- **Send email or SMS.** ALWAYS confirm content with the user before calling `send_email` or `send_sms`. This is non-negotiable.

---

## Top quirks (memorize these)

The five worst, in order of how often they bite:

1. **Auth header is `token`, not `Bearer`.** Mixing it up returns error 200058. The starter client uses the right one.
2. **`/v1.0/leads` silently ignores `keyword` and `sortField`.** Sort always returns `leadId` DESC. For real lead search, build a leads index. See `references/extending.md`.
3. **Activities must use v1.0.** `/v2.0/leads/<id>/activities` returns empty.
4. **Notes go to `POST /v1.0/notes`** with `{"leadId": <number>, "content": "..."}`. The intuitive `/v1.0/leads/<id>/notes` returns 404. `leadId` must be a number, not a string.
5. **Rate limit is 10 requests per minute.** Starter client enforces 6.5s spacing.

The full quirks list (14 documented quirks) lives in `references/quirks.md`. Read it when a Lofty call behaves unexpectedly.

---

## Safety rules (always)

These rules apply on every interaction in BOTH modes. They came from real mistakes.

- **Confirm with the user before sending any email or SMS.** Every time, both modes. No exceptions.
- **Confirm before deleting anything.** Every time.
- **Never paste the API key into chat.** Treat it like a password.
- **Always exclude the user's own last name from lead searches.** Read this from their `CLAUDE.md`.
- **Always exclude these stages from queries:** `DNC`, `Archived`, `Agents / Vendors`.
- **Verify the lead ID before logging a note.** Show the user the matched lead's name, email, phone first. Confirm it's the right person before writing.
- **Don't run long scans inside Cowork's bash tool.** It has a 45-second hard timeout. Long scans (like the leads index refresh, ~3 minutes for 650 leads) need to run from the user's terminal.
- **Times use ISO 8601 with offset.** Pacific is `-07:00` in DST, `-08:00` outside.
- **Address format Lofty expects:** `STREET, CITY, STATE ZIP`.

In Easy Mode, phrase confirmations in plain English: "I've drafted this note: [content]. Want me to post it on Jane's lead?" rather than "Confirm POST /v1.0/notes with leadId=12345?"

---

## When something behaves unexpectedly

Order of investigation:

1. Read the response body. The starter client returns `{"error": True, "status": <code>, "body": "..."}` on HTTP errors. The body usually says exactly what is wrong.
2. Match the error against `references/quirks.md`.
3. If still stuck, walk the troubleshooting decision tree in `references/full-guide.md`.
4. If you hit a wall (two failed attempts at the same step), tell the user in plain English: "I'm stuck on this step. Check the help section at github.com/Joe-exprlty/lofty-cowork-skill for troubleshooting steps." Do not loop on the same error.

---

## Building on this skill

The starter client covers leads, notes, and activities. For more, see `references/extending.md`:

- Adding showing scheduling helpers (`prepare_showing`, `find_listing_by_address`)
- Building a leads index for real name search
- Adding MLS search (`search_listings` with full filter syntax)
- Adding tasks, email, SMS
- Deploying the four Cloudflare Workers (leads-index, short-links, jotform-to-lofty, showing-sms)
- Subscribing to webhooks for live updates

Each addition has a pattern in the full guide. Use the same `_request` plumbing the starter client provides; do not reinvent it.

---

## Skeptical reminders

- The quirks documented here are based on one team's testing of the Lofty API in mid-2026. Lofty can change behavior. When in doubt, verify in the user's environment.
- Trust but verify. When the user reports something worked, ask them to spot-check one record in Lofty's UI before moving on.

---

## File map

- `SKILL.md` (this file) - what to do, when, in plain prose
- `assets/lofty_api.py` - the starter Python client to install in the user's workspace
- `assets/env-template` - settings file template
- `assets/CLAUDE.md.template` - Cowork context file template (gets customized in step 7 of Easy Mode)
- `scripts/setup_check.py` - quick sanity check script for advanced users
- `references/full-guide.md` - comprehensive setup, learning, and best practices guide
- `references/quirks.md` - full quirks list with workarounds
- `references/workflows.md` - step-by-step recipes for common tasks
- `references/extending.md` - how to add capability beyond the starter
