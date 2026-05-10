---
name: lofty-cowork-helper
description: Connect Claude to the Lofty CRM API for real estate agents and VAs. Use whenever the user mentions Lofty, Lofty CRM, Lofty API, connecting Cowork to Lofty, finding a lead, logging a note, scheduling a showing, post-showing SMS, leads index, jotform feedback, error 200058, or Lofty webhooks. Trigger on setup phrases ("set up Lofty," "connect my CRM," "I just installed this"), on Tier 2 deploy phrases ("set up Tier 2," "set up post-showing feedback," "deploy the Worker," "deploy the post-showing feedback Worker," "set up the JotForm Worker," "wire up the showing feedback form"), on workflow questions ("how do I find a lead," "log a showing," "log a note for," "search the MLS," "schedule a showing for"), and on troubleshooting phrases ("Lofty error," "200058," "auth failed," "this Lofty call returned"). Trigger even on casual mentions ("the Lofty thing," "my CRM is Lofty," "in Lofty"). Do NOT trigger for general real estate questions unrelated to Lofty.
---

# Lofty CRM Helper for Claude Cowork

This skill turns Claude into a working Lofty CRM operator for real estate agents and VAs. It handles first-time setup, common workflows (finding leads, logging notes, scheduling showings, searching the MLS), and troubleshooting the API's well-known quirks. It defaults to Easy Mode so non-technical users can finish setup and get to their first lead lookup in under 15 minutes.

## How to start a session

When the skill activates, decide which path the user is on:

- **No `.env` file in their workspace** → first-time setup. Run **Easy Mode** (the default).
- **`.env` exists but no successful test connection yet** → finish setup. Run the connection test, report result.
- **A specific Lofty task in mind** ("find a lead," "log a note," "schedule a showing") → use the "Common workflows" section, which points at `references/workflows.md` for full recipes.
- **A Tier 2 deploy in mind** ("set up Tier 2," "deploy the Worker," "set up post-showing feedback") → jump to "Tier 2 setup: post-showing feedback Worker" below.
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

Use the bash `open` (Mac) or `start` (Windows) command to open `~/Code/lofty-tools/.env` in the user's default text editor. Wait for the user to confirm they saved. **Do NOT read the `.env` file back to validate the key.** Reading it would pull the user's API key into Claude's context unnecessarily. Validation happens in step 8 by running the connection test, which exercises the key locally and only reports success or failure to Claude (never the key itself).

If the user reports they cannot find or open the file, you may use `cat ~/Code/lofty-tools/.env | grep -c "your-lofty-jwt-here"` to count occurrences of the placeholder string only. A count of `0` means they replaced the placeholder; a count of `1` means they did not. This check returns only a number, never the key value.

### 7. Ask for personal info, one question at a time

Ask each of these as a separate question. Wait for an answer. Update `~/Code/lofty-tools/.claude/CLAUDE.md` after each answer (replace placeholders silently).

1. "What's your full name?" → owner name
2. "What's your brokerage name?" → e.g., "eXp Realty"
3. "What city or area do you serve?" → e.g., "Portland, Oregon"
4. "What's the best phone number for clients to reach you?" → owner phone
5. "What's your work email address?" → owner email
6. "What's your last name? I'll use this so Claude doesn't mistake you for a lead when searching." → for lead-search exclusion
7. "What's your timezone? Like 'Pacific' or 'Eastern.'" → convert to America/Los_Angeles, America/New_York, etc.
8. "Where do you want showing reminders to go on YOUR calendar? Pick one." → CALENDAR_PROVIDER. Offer four plain-English options:
   - "Google Calendar (Gmail or Google Workspace)" → `google`. Quietly verify the Google Calendar MCP is installed; if missing, tell the user how to add it before continuing.
   - "Microsoft Outlook or 365" → `outlook`. Quietly verify the Microsoft 365 connector is installed; if missing, tell the user how to add it before continuing. Mention this is a beta path and ask them to flag any issues.
   - "Just use Lofty's built-in tasks" → `lofty`. Add a one-line note: "The Lofty reminder is text-only, no map link. The buyer still gets a polished email invite separately, so this is fine for most agents."
   - "I'll handle reminders myself" → `skip`. Confirm: "Got it. I'll skip the calendar entry, but I'll still write the showing-log note in Lofty and send the buyer their invite by email."

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

## Tier 2 setup: post-showing feedback Worker

Trigger this section when the user says any of:

- "set up Tier 2"
- "set up post-showing feedback"
- "deploy the Worker"
- "deploy the post-showing feedback Worker"
- "set up the JotForm Worker" or "set up the Jotform Worker"
- "wire up the showing feedback form"
- any close paraphrase referencing Tier 2, the post-showing feedback flow, the JotForm Worker, or the D1 database for showings

Tier 2 stands up one Cloudflare Worker (`jotform-to-lofty`), one D1 database (`showing_feedback`), and a Jotform form pointed at the Worker. Free Cloudflare tier covers it. The full deploy runbook lives in `references/workers_setup.md`. This section just routes the user to the right walkthrough in that file.

### Step 1: Confirm prereqs (silent)

Before picking a mode, check:

- `.env` has `LOFTY_API_KEY` (Tier 1 finished). If not, route them to the Easy Mode setup above first.
- `.env` has `CLOUDFLARE_API_TOKEN`. If missing, walk them through `dash.cloudflare.com/profile/api-tokens` using the "Edit Cloudflare Workers" template, paste the token, save the file. Wait for confirmation.
- `node --version && npm --version` both return versions. Real estate agents commonly don't have Node installed. If missing, walk them through the install in plain English: on macOS with Homebrew, `brew install node`; on macOS without Homebrew, download the LTS `.pkg` from `https://nodejs.org/en/download` and run it, then open a NEW terminal window so PATH picks up the new install; on Windows, download the LTS Windows installer from the same page. Re-check `node --version` and `npm --version` after they confirm install. Do NOT skip this check; without Node, wrangler can't run.
- `wrangler --version` returns a version, OR `npx wrangler --version` works (npx downloads on demand, no global install required). For one-off deploys, prefer `npx wrangler` over `npm install -g wrangler` since it sidesteps global PATH issues.
- The user has a Jotform account. If not, point them at `jotform.com` (free tier is fine), wait, then continue.
- Cloudflare MCP and Jotform MCP both connected. Easy Mode requires both. If either is missing and the user does not want to install it, route to Power User Mode.

### Step 2: Ask which mode

Use the AskUserQuestion tool. Two options:

- **Easy Mode (recommended).** Claude builds the Jotform form via MCP, creates and migrates D1 via Cloudflare MCP, fills `wrangler.jotform.toml`, generates `PREFERENCES_API_KEY` silently, pushes secrets, deploys the Worker, wires the Jotform webhook, and runs the smoke test. About 5 minutes. The user only answers two questions: brand colors and an optional logo, plus whether they want Resend.
- **Power User Mode.** The user runs the shell commands and clicks the Jotform UI themselves. About 15 minutes. Useful for users who want to see exactly what is happening or who do not want the MCPs. Claude stays engaged and answers questions inline.

If neither MCP is connected and the user does not want to install them, default to Power User Mode without asking.

### Step 3: Run the chosen path

- **Easy Mode:** follow steps 1 through 12 of the "Easy Mode walkthrough" in `references/workers_setup.md` verbatim. Step 2 of that walkthrough is the branding step (locked: do not skip). Ask for primary text color, accent color, and an optional logo URL even if the user says "I don't care, just go." The defaults (black text, gold accent, no logo) are fine if they accept them; the form must still get a coherent look. After step 12, hand off in one line: "Tier 2 is live. Submissions will land on the lead's timeline as a Lofty note and in D1."
- **Power User Mode:** point the user at the "Power User Mode walkthrough" section of `references/workers_setup.md`. As they work through each numbered step, surface the relevant snippet, answer their questions inline, and read back any error output to diagnose. Don't run their commands for them; they picked Power User Mode so they could drive.

### When something fails

1. Report the exact error in plain English.
2. Match it against the "Common errors" table in `references/workers_setup.md`.
3. Offer to roll back the partial deploy using the "Roll back" section. ONLY roll back with explicit user consent.
4. If after two attempts the same step still fails, stop and surface `github.com/Joe-exprlty/lofty-cowork-skill`.

### After a successful deploy

- Add `JOTFORM_WORKER_URL=<deployed-url>` to `.env` so `api.get_buyer_preferences(lead_id)` works from Python.
- Confirm `LOFTY_PREFERENCES_API_KEY` is in `.env` (Easy Mode step 7, Power User step 6).
- Tell the user what they just unlocked: `api.get_buyer_preferences(lead_id)` from Python, the optional buyer profile Cowork artifact, and the per-buyer trend section that appears in recap emails after 3+ submissions from the same lead.
- Tier 3 (the showing-reminder SMS Worker) is a separate v1.6 deploy that requires Cloudflare Workers Paid ($5/mo). Don't bundle it with Tier 2.

---

## Common workflows

For each workflow below, the full recipe (with edge cases) lives in `references/workflows.md`. Read that file before executing if you are unsure of any step.

- **Find a client by name.** Starter client uses `search_leads()` (paginated, recent-first). For real lookup by name in a large CRM, build a leads index (see `references/extending.md`).
- **Log a note.** `api.create_note(lead_id, content)`. Always confirm the lead ID with the user before posting.
- **Get activity feed.** `api.get_lead_activities(lead_id)`. Use v1.0; v2.0 returns empty.
- **Search the MLS.** `api.search_listings(filter_conditions, sort_fields)` posts to `/v2.0/listings/search`. Use comma-separated min,max for ranges (`"price": "400000,650000"`), lists for multi-value (`"propertyType": ["Single Family", "Condo"]`), and a nested `location` object for city/zip. Scope is `"all"` (full MLS), `"my"` (your listings), or `"office"`. Always pass `"listingStatus": ["Active"]` when looking up a real address; falling through to Pending or Sold masks typos.
- **Create a task or follow-up reminder.** `api.create_task(lead_id, content, start_at, end_at, way="Call")` posts to `/v2.0/calendar` with `type_="TASK"`. Times must be ISO 8601 with offset. Do NOT pass `type_="APPOINTMENT"` for showings; that triggers listing-agent approval. For showings, use the prepare_showing pattern in `references/extending.md`.
- **Put an event on the agent's calendar.** Read `CALENDAR_PROVIDER` from `CLAUDE.md` and route to the right backend (Google Calendar MCP, Microsoft 365 connector, Lofty's calendar via `api.create_task`, or skip). Full routing rules in `references/calendar_routing.md`. Always also write the Lofty showing-log note via `api.create_note` regardless of which provider is chosen.
- **Build a buyer-facing .ics invite.** When `CALENDAR_PROVIDER` is `lofty` or `skip`, the chosen calendar can't email the buyer. Use `assets/ics_builder.py` (`build_ics(...)`) to generate an iCalendar string and send it through `api.send_email` so the buyer can drop the showing into their own calendar. Skip this step on the `google` and `outlook` paths because their native attendee-invite already emails the buyer; sending an .ics on top would duplicate.
- **Send email.** `api.send_email(lead_id, subject, content)`. ALWAYS draft the subject and body, show them to the user, and get explicit confirmation before calling. The Python wrapper does not gate the send. This is non-negotiable.
- **Send SMS.** `api.send_sms(lead_id, content)`. Same rule: draft, confirm, then send. Keep texts short. Sign with the agent's first name only (e.g. "Jane", not "Jane Smith, Acme Realty").

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

The v1.2.0 starter covers leads, notes, activities, MLS search, tasks, email, and SMS. For deeper capability, see `references/extending.md`:

- Adding showing scheduling helpers (`prepare_showing`, `find_listing_by_address`)
- Building a leads index for real name search across the full CRM
- Deploying the post-showing feedback Worker (`jotform-to-lofty` + D1) - see "Tier 2 setup: post-showing feedback Worker" above for the full picker; `references/workers_setup.md` has the deploy walkthrough
- Other Cloudflare Workers (leads-index, short-links, showing-sms) ship in v1.6 and v1.7
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
- `assets/ics_builder.py` - buyer-facing .ics generator for the lofty and skip calendar paths
- `assets/post_showing_questions.yaml` - the recommended question pack the agent forks at setup; drives the post-showing JotForm and the lead-update mapping
- `assets/jotform_form_template.md` - read at runtime by Easy Mode Tier 2 setup; the natural-language `create_form` prompt and `JOTFORM_FIELD_MAP` build procedure
- `scripts/setup_check.py` - quick sanity check script for advanced users
- `scripts/refresh_leads_index.py` - rebuild `data/leads_index.json` for the file-fallback lead lookup
- `scripts/test_worker_parsers.mjs` - smoke test for the Tier 2 Worker's submission parser; run with `node scripts/test_worker_parsers.mjs`
- `workers/jotform_to_lofty_worker.js` - the Tier 2 Worker source; deploys to Cloudflare via wrangler
- `workers/wrangler.jotform.toml` - wrangler config template for the Tier 2 Worker (placeholders get filled in at deploy time)
- `workers/migrations/001_showing_feedback.sql` - D1 schema for the `showing_feedback` table; idempotent
- `references/full-guide.md` - comprehensive setup, learning, and best practices guide
- `references/quirks.md` - full quirks list with workarounds
- `references/workflows.md` - step-by-step recipes for common tasks
- `references/extending.md` - how to add capability beyond the starter
- `references/calendar_routing.md` - which calendar provider to call based on the agent's setup choice
- `references/workers_setup.md` - Tier 2 deploy runbook with Easy Mode and Power User Mode walkthroughs
