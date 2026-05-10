# Tier 2: Post-Showing Feedback Worker (v1.5)

This is the Tier 2 setup. It deploys one Cloudflare Worker (`jotform-to-lofty`) and one D1 database (`showing_feedback`), and points your Jotform post-showing form at the Worker. Once it's running, every form submission writes a Lofty note, stores a row in D1, and (optionally) sends the buyer a recap email.

Tier 2 runs entirely on the Cloudflare free tier. No paid plan required.

## What you get

- Buyers fill out one short form after each showing.
- A note lands on the matching Lofty lead with the buyer's ratings, what they loved, and any dealbreakers.
- The Worker stores one row per submission in D1 so you can ask Claude things like "what does this buyer say they care about" or "what's the most common dealbreaker across my book."
- After 3+ submissions from the same buyer, the recap email gets a "What we're learning about your preferences" section.

## Prereqs

Five to ten minutes of one-time account and tool setup before you start:

1. **Node.js installed (provides `npm` and `npx`).** Wrangler is a Node package, so without Node it can't run. Most real estate agents don't have Node out of the box; install it once and you're set.
   - Check first: `node --version && npm --version`. If both return version numbers, skip ahead to step 2.
   - **macOS with Homebrew:** `brew install node`. Verify with `node --version && npm --version`.
   - **macOS without Homebrew:** download the LTS macOS `.pkg` installer from `https://nodejs.org/en/download`, double-click, follow the prompts. Open a NEW terminal window after install (existing windows won't see the new PATH), then verify with `node --version && npm --version`.
   - **Windows:** download the LTS Windows installer from `https://nodejs.org/en/download`, run it, accept defaults. Open a new PowerShell or Command Prompt and verify with `node --version` and `npm --version`.
   - **Linux:** use your distro's package manager (e.g., `sudo apt install nodejs npm` on Debian/Ubuntu) or `nvm` if you want version control.
2. **Cloudflare account.** Free tier is fine. Sign up at `dash.cloudflare.com`. The Cloudflare MCP handles account selection, D1 creation, and migration apply; you don't need to click around the dashboard for any of those.
3. **`wrangler` available.** Two paths:
   - **Recommended for one-off deploys:** use `npx wrangler` instead of installing globally. The first call downloads wrangler to npm's cache; subsequent calls run instantly. No global install needed.
   - **Or install globally:** `npm install -g wrangler`, then verify with `wrangler --version`. If `wrangler` isn't found after the install, npm's global bin directory may not be on your `PATH`; either use `npx wrangler` or fix PATH.
   Wrangler is used for two things only: pushing Worker secrets (`wrangler secret put`) and deploying the Worker code (`wrangler deploy`). All D1 setup runs through the Cloudflare MCP instead.
4. **`CLOUDFLARE_API_TOKEN` in your `.env`.** Get from `dash.cloudflare.com/profile/api-tokens` using the "Edit Cloudflare Workers" template. This lets `wrangler` deploy without prompting.
5. **Jotform account.** Free tier is fine. Sign up at `jotform.com`.
6. **Optional, only if you want the buyer recap email to come from your own verified domain:** a Resend account at `resend.com` plus a verified sending domain matching your `OWNER_EMAIL`. Skip this and the Worker still sends the recap, just through Lofty's `send_email` endpoint instead. The Lofty path delivers to the lead's primary email on file in Lofty rather than the email the buyer typed into the form. Most users skip Resend on day 1 and add it later if they want the deliverability and the From address polish.

## Pick your path

There are two ways to deploy this. Pick whichever matches how you like to work.

### Easy Mode (Claude does it for you)

You say "set up Tier 2" or "deploy the post-showing feedback Worker." Claude prompts you for the few values it needs (which Cloudflare account, which Resend domain, etc.) and runs the rest. Target time: about 5 minutes. The full sequence Claude follows is documented under "Easy Mode walkthrough" below; you don't need to read it unless something fails.

### Power User Mode (you run the commands)

You drive the deploy yourself with the shell commands documented under "Power User Mode walkthrough" below. Target time: about 15 minutes the first time. Useful if you want to understand exactly what's getting set up, or if you're the kind of person who likes to see the wrangler output land in your terminal.

Both paths produce the same end state, and Claude can answer questions or take over partway through either path if you get stuck.

---

## Easy Mode walkthrough

This is the script Claude follows when you say "set up Tier 2." Listed here for reference; if you're going Easy Mode you don't need to type any of this yourself.

1. **Confirm the active Cloudflare account.** `accounts_list`. If you have one, set it active. If multiple, ask the user which.
2. **Capture brand inputs for the Jotform form.** Ask the user two questions before building anything:
   - "What colors do you want? Pick a primary text color and an accent color. You can answer in plain English ('black and gold', 'navy and orange') or paste hex codes ('#1a1a1a and #D4AF37'). Default is black text on white with a neutral gray accent if you skip."
   - "Do you want a logo at the top of the form? Upload one (Claude can take an image path or URL), paste a hosted image URL, or say 'skip' for no logo."
   Convert plain-English colors to hex internally (a small color name lookup is fine; for ambiguous answers, ask). Hold the resulting `accent_color`, `text_color`, and `logo_url` (may be null) values in memory for step 3.
3. **Build the Jotform form.** Follow the procedure in `assets/jotform_form_template.md` end to end. That doc has the natural-language `create_form` prompt, the post-creation `fetch` introspection, and the `JOTFORM_FIELD_MAP` build steps. Outputs of this step:
   - `form_id` saved to `.env` as `JOTFORM_FORM_ID`
   - `JOTFORM_FIELD_MAP` written to `workers/wrangler.jotform.toml` `[vars]` as a JSON-stringified `qid -> purpose` object
   - Optional follow-up `edit_form` calls to fix any fields, theme colors, or hidden fields the Jotform agent didn't pick up from the initial prompt.
4. **Create (or find) the D1 database.** Idempotent: first call `d1_databases_list` filtered by name `showing_feedback`. If a database with that name already exists, capture its `database_id` and continue. Otherwise call `d1_database_create` with `{name: "showing_feedback"}` and let Cloudflare auto-pick the region (skip `primary_location_hint` unless the user has a strong preference, in which case ask). Capture the returned `database_id`.
5. **Apply the schema migration.** Read `workers/migrations/001_showing_feedback.sql`. Run it via `d1_database_query` against the new database. The migration is wrapped in `CREATE TABLE IF NOT EXISTS` and `CREATE INDEX IF NOT EXISTS`, so re-running on an existing database is a no-op. Verify by running `SELECT COUNT(*) FROM showing_feedback` via `d1_database_query`; expect a numeric result (zero on a fresh db, the existing row count on a re-apply). If `d1_database_query` rejects multi-statement SQL, split the file on semicolons and run each statement separately.
6. **Patch `workers/wrangler.jotform.toml`.** Replace `REPLACE_WITH_D1_ID_FROM_WRANGLER_D1_CREATE` with the captured `database_id`. Replace each `OWNER_*` placeholder with the value from the user's `.env`. Don't touch `JOTFORM_FIELD_MAP`; that was already set in step 3.
7. **Generate `PREFERENCES_API_KEY` silently.** Run `python3 -c "import secrets; print(secrets.token_urlsafe(32))"` and capture the output. Append it to `.env` as `LOFTY_PREFERENCES_API_KEY=<value>` (use Edit, don't show the value to the user, don't echo it in a chat message). Hold the same value in memory for step 8 so it can be pushed to the Worker as a secret in one go. The user never has to see, type, or paste this token.
8. **Push secrets.** `wrangler secret put LOFTY_API_KEY -c workers/wrangler.jotform.toml` (value from `.env`), then `wrangler secret put PREFERENCES_API_KEY -c workers/wrangler.jotform.toml` (value from step 7's in-memory token; pipe it via stdin so the user never sees it). Ask the user "Do you want to send the buyer recap email from your own verified domain via Resend, or have it go out through Lofty's send_email (default)?" If they pick Resend, push `RESEND_API_KEY` too. Otherwise skip; the Worker uses `LOFTY_API_KEY` for the recap automatically.
9. **Deploy the Worker.** `cd workers && wrangler deploy -c wrangler.jotform.toml`. Capture the deployed URL.
10. **Wire the Jotform webhook automatically.** Call `edit_form` with the saved `JOTFORM_FORM_ID` and a description like `"Set the form's webhook URL to <deployed_worker_url>. Replace any existing webhook on this form so all submissions go to that URL."` Confirm by re-running `fetch(<form_id>)` and checking the webhook field on the response. The user never opens Jotform's UI for this step.
11. **Health check.** `curl <worker_url>/` should return `{"status":"ok","service":"jotform-to-lofty"}`.
12. **Smoke test.** Prompt the user to submit one test entry on the form. Confirm the Lofty note lands and the D1 row count went from 0 to 1.

If any step fails, Claude reports the exact error and offers to roll back (drop the D1 database, undo the Jotform changes) or to switch to Power User Mode partway.

---

## Power User Mode walkthrough

Run from the kit root unless noted. All commands are copy-paste safe.

### 1. Build the Jotform form

Easiest path: use Jotform's UI to build a form with the questions in `assets/post_showing_questions.yaml`. Field-by-field:

- 6 rating questions (1-5 scale), Unique Names: `first_reaction`, `daily_life_fit`, `neighborhood_rating`, `condition_rating`, `value_rating`, `short_list`.
- 2 text questions (long-text), Unique Names: `standout_text`, `memory_notes`.
- 2 multi-select questions, Unique Names: `loved_tags`, `dealbreaker_tags`. Use the starter tag lists from `assets/post_showing_questions.yaml`.
- 4 hidden fields prefilled by the showing link: `lead_id`, `propertyAddress`, `showingDate`, `client_name`. Plus a `buyer_email` field if you want the recap email.

Set Unique Names exactly as listed; the Worker keys off them.

**Branding.** The YAML's `header_html` block ships with a neutral gold accent (`#D4AF37`) and dark heading text. Edit those hex codes to your brand colors before pasting into Jotform's header HTML, or skip and edit the form's appearance later in Jotform's Form Designer. To add a logo, paste an `<img src="<your-hosted-logo-url>" style="max-height:64px;margin:0 auto 12px;display:block;">` line at the top of the header div, or upload a logo image in Jotform's Form Designer > Header section.

### 2. Create the D1 database

```
cd lofty-cowork-helper/workers
wrangler d1 create showing_feedback
```

Wrangler prints an `id = "..."` line. Copy it.

### 3. Paste the D1 id into wrangler config

Open `workers/wrangler.jotform.toml`. Replace `REPLACE_WITH_D1_ID_FROM_WRANGLER_D1_CREATE` with the id from step 2.

### 4. Apply the schema migration

```
wrangler d1 execute showing_feedback \
  --file migrations/001_showing_feedback.sql --remote
```

Expect "Executed 3 commands" (CREATE TABLE plus 2 CREATE INDEX).

Sanity check:

```
wrangler d1 execute showing_feedback \
  --command "SELECT COUNT(*) FROM showing_feedback" --remote
```

Should return `0`.

### 5. Fill in the OWNER_* vars

In `workers/wrangler.jotform.toml`, replace each `REPLACE_WITH_OWNER_*` placeholder with the value from your `.env`. Leave `OWNER_WEBSITE` blank if you don't want a website link in the email signature.

### 6. Generate `PREFERENCES_API_KEY`

```
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Save the output to `.env` as `LOFTY_PREFERENCES_API_KEY=<paste>`. You'll paste the same value into the Worker as a secret in the next step.

### 7. Push secrets

```
wrangler secret put LOFTY_API_KEY -c wrangler.jotform.toml
wrangler secret put PREFERENCES_API_KEY -c wrangler.jotform.toml
```

Each prompts for the value. `LOFTY_API_KEY` is the same value as in `.env`. `PREFERENCES_API_KEY` is the random string from step 6.

The buyer recap email goes out automatically using `LOFTY_API_KEY`, delivered to the lead's primary email on file in Lofty. If you'd rather have the recap come from your own verified Resend sending domain (delivered to whatever email the buyer typed into the form), also push:

```
wrangler secret put RESEND_API_KEY -c wrangler.jotform.toml
```

This step is optional. Skip it if you're fine with Lofty handling the recap.

### 8. Deploy the Worker

```
wrangler deploy -c wrangler.jotform.toml
```

Expect a "Published jotform-to-lofty" line with the URL. Copy that URL.

### 9. Wire the Jotform webhook

In Jotform, open your form. Settings > Integrations > Webhooks > add the Worker URL from step 8. Save.

### 10. Verify the deploy

See "Verify and troubleshoot" below.

---

## Verify and troubleshoot

### Health check

```
curl <your-worker-url>/
```

Should return `{"status":"ok","service":"jotform-to-lofty"}`.

### Smoke-test a submission

Submit one test entry on your form (any lead_id you can verify in Lofty afterward). Then:

- Confirm the Lofty note lands on the lead's timeline.
- Run `wrangler d1 execute showing_feedback --command "SELECT COUNT(*) FROM showing_feedback" --remote`. Should be `1`.
- Confirm the recap email arrived. If Resend is configured, it lands at the `buyer_email` from the form. If not, it lands at the lead's primary email on file in Lofty.

### Test the preferences endpoint

After a buyer has at least one submission, you can read their aggregated profile:

```
curl -H "Authorization: Bearer $LOFTY_PREFERENCES_API_KEY" \
  <your-worker-url>/preferences/<lead_id>
```

Expect JSON with `total_showings`, `loved`, `dealbreakers`, `average_ratings`. Without the Bearer header you should get a 401.

From Python, the same data is available via `api.get_buyer_preferences(lead_id)` once the Worker URL is in your `.env` as `JOTFORM_WORKER_URL`.

### Common errors

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `Lofty API 401` in Worker logs | `LOFTY_API_KEY` secret not set or wrong | Re-run `wrangler secret put LOFTY_API_KEY -c wrangler.jotform.toml` |
| Lofty note doesn't land | `lead_id` field missing on submission | Check the form's hidden fields; lead_id must be passed in via the showing link |
| `Resend API 422 The from address does not match a verified domain` | `OWNER_EMAIL` is on a domain that isn't verified in Resend | Verify the domain in Resend, or unset `RESEND_API_KEY` to fall back to the Lofty email path |
| `Lofty API 200058` on email send | Wrong auth scheme | Confirm the `LOFTY_API_KEY` secret was pushed with `wrangler secret put` and the value is the JWT-style token, not Bearer |
| Buyer didn't get the recap email (Lofty fallback path) | Lofty has the wrong primary email on the lead, or no email at all | Update the email field on the lead record in Lofty, then push a test submission again. To send to the form-submitted address instead, opt into Resend |
| `D1 binding not configured` | `database_id` in wrangler config still has the placeholder | Replace with the id from `wrangler d1 create showing_feedback` |
| 401 on `/preferences/:leadId` | Bearer token mismatch | Ensure `LOFTY_PREFERENCES_API_KEY` in `.env` matches the `PREFERENCES_API_KEY` secret pushed to the Worker |

### Roll back

Each step is reversible:

- **Drop the D1 database:** `wrangler d1 delete showing_feedback`. Wipes all stored feedback. The Worker stops writing rows but the Lofty note step keeps working.
- **Undeploy the Worker:** `wrangler delete -c wrangler.jotform.toml`. Jotform submissions stop reaching the Worker; nothing else changes.
- **Disconnect Jotform:** in form Settings > Integrations > Webhooks, remove the Worker URL. Jotform stops calling the Worker but the form keeps working.

---

## Data handling

When a buyer submits the form, the data passes through:

- **Jotform** (form host).
- **Cloudflare Workers** (your Worker, in the Cloudflare account you control).
- **Cloudflare D1** (your database, same account).
- **Lofty** (note write).
- **Resend** (only if you opted into Resend for the recap email).
- **Anthropic** (when you later ask Claude to read the data via `get_buyer_preferences`).

Confirm this fits your brokerage's data handling rules and what your buyers reasonably expect before turning the form on for live clients. The kit is provided as is. Verify behavior in your own accounts before relying on it for client-facing work.

## What comes next

Tier 2 unlocks:

- `api.get_buyer_preferences(lead_id)` from Python returns the aggregated profile.
- A "buyer profile" Cowork artifact you can ask Claude to render for any lead.
- Pre-filled Google Calendar events for follow-up showings, prefilled with the buyer's top 3 must-haves and dealbreakers.

Tier 3 (the showing-reminder SMS Worker) ships in v1.6 and requires the Cloudflare Workers Paid plan ($5/mo). Tier 3 polish (the leads-index and short-links Workers) is opt-in and ships in v1.7.
