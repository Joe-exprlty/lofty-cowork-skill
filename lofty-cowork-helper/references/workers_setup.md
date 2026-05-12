# Tier 2: Post-Showing Feedback Worker (v1.6.1)

This is the Tier 2 setup. It deploys one Cloudflare Worker (`jotform-to-lofty`) and one D1 database (`showing_feedback`), and points your Jotform post-showing form at the Worker. Once it's running, every form submission writes a Lofty note, stores a row in D1, and (optionally) sends the buyer a recap email.

Tier 2 runs entirely on the Cloudflare free tier. No paid plan required.

## What changed in v1.6.1

End-to-end testing on a brand new Jotform account and a brand new Cloudflare account surfaced a stack of papercuts that all hit a first-time user but never bit an experienced operator. v1.6.1 fixes them. Highlights:

- `wrangler.jotform.toml` now ships the canonical `JOTFORM_FIELD_MAP` as default, so submissions from a freshly cloned template route correctly without a per-install map. Previously the default was `"{}"` and the `memory_notes` (qid 51) field silently dropped on the floor.
- `wrangler.jotform.toml` now explicitly disables `preview_urls` and pins `workers_dev = true`, silencing the wrangler 4.x warnings and closing a real attack surface (the preview URL otherwise exposes a Worker holding `LOFTY_API_KEY`).
- Prereqs now include an explicit MCP install step (Cloudflare MCP + Jotform MCP from Customize > Connectors in Claude Desktop), a Lofty API token retrieval step, and concrete dropdown guidance for the Cloudflare "Edit Cloudflare Workers" token template on zoneless accounts.
- Easy Mode step 7 reads `LOFTY_API_KEY` directly from `.env` and pipes it into `wrangler secret put`, eliminating the manual paste.
- The Jotform import-from-URL walkthrough is rewritten for Jotform's current UI ("+ CREATE → Import form → Import from URL") and warns about the misleading "I'll turn it into a form" tagline.
- Step 9 (webhook wiring) is rewritten. The Jotform MCP cannot wire webhooks, so users wire them via Jotform's UI (Settings → Integrations → Webhooks).
- Several wrangler interactive prompts (create-Worker, register-subdomain) and the workers.dev SSL cert propagation delay are now called out so users know what to expect.

## What changed in v1.6

The Jotform form is now created by **cloning a polished public template** instead of being generated from a natural-language prompt. Click one link, get a Card Form with the right questions, the right hidden fields, and a clean header layout already in place. The previous `create_form` path produced Classic Forms with mediocre visual polish and required several follow-up edits to land a usable form. The template-clone path is the new primary; the `create_form` flow stays in the kit as a documented fallback for users who can't or won't clone a shared template.

## What you get

- Buyers fill out one short form after each showing.
- A note lands on the matching Lofty lead with the buyer's ratings, what they loved, and any dealbreakers.
- The Worker stores one row per submission in D1 so you can ask Claude things like "what does this buyer say they care about" or "what's the most common dealbreaker across my book."
- After 3+ submissions from the same buyer, the recap email gets a "What we're learning about your preferences" section.

## Prereqs

Ten to fifteen minutes of one-time account and tool setup before you start. Do these in order; skipping is fine for steps you've already done from earlier kit setup.

1. **Cloudflare MCP and Jotform MCP installed in Claude Desktop.** Open Claude Desktop, click **Customize** in the bottom-left, then **Connectors**. Find **Cloudflare** and **Jotform** in the list and install both. Authorize each one against your accounts when prompted. The Easy Mode walkthrough below assumes both MCPs are live; without them Claude can't read your Cloudflare account or your Jotform form.
2. **Node.js installed (provides `npm` and `npx`).** Wrangler is a Node package, so without Node it can't run. Most real estate agents don't have Node out of the box; install it once and you're set.
   - Check first: open **Terminal** (Applications → Utilities → Terminal on macOS) and type `node --version && npm --version`. If both print version numbers, skip ahead.
   - **macOS with Homebrew:** `brew install node`. Verify with `node --version && npm --version`.
   - **macOS without Homebrew:** download the LTS macOS `.pkg` installer from `https://nodejs.org/en/download`, double-click, follow the prompts. Open a NEW terminal window after install (existing windows won't see the new PATH), then verify with `node --version && npm --version`.
   - **Windows:** download the LTS Windows installer from `https://nodejs.org/en/download`, run it, accept defaults. Open a new PowerShell or Command Prompt and verify with `node --version` and `npm --version`.
   - **Linux:** use your distro's package manager (e.g., `sudo apt install nodejs npm` on Debian/Ubuntu) or `nvm` if you want version control.
3. **`wrangler` available.** Two paths:
   - **Recommended for one-off deploys:** use `npx wrangler` instead of installing globally. The first call downloads wrangler to npm's cache; subsequent calls run instantly. No global install needed.
   - **Or install globally:** `npm install -g wrangler`, then verify with `wrangler --version`. If `wrangler` isn't found after the install, npm's global bin directory may not be on your `PATH`; either use `npx wrangler` or fix PATH.
   Wrangler is used for two things only: pushing Worker secrets (`wrangler secret put`) and deploying the Worker code (`wrangler deploy`). All D1 setup runs through the Cloudflare MCP instead.
4. **Cloudflare account.** Free tier is fine. Sign up at `dash.cloudflare.com`. Verify the welcome email Cloudflare sends; the API tokens page is gated on email verification.
5. **`CLOUDFLARE_API_TOKEN` saved in your shell environment.** Generate the token from `dash.cloudflare.com/profile/api-tokens` using the **"Edit Cloudflare Workers"** template. New-account quirks to expect:
   - The template lands with empty Account Resources and Zone Resources dropdowns. You **must** set both before Cloudflare will let you create the token:
     - **Account Resources:** `Include` → your account name
     - **Zone Resources:** `Include` → `All zones from an account` → your account name
   - After "Create Token", Cloudflare displays the token once. Copy it immediately.
   - In your Terminal, set the token as an environment variable for the duration of the session: `export CLOUDFLARE_API_TOKEN=<paste-token-here>`. This tells `wrangler` which account to talk to without prompting.
6. **Lofty API token.** Sign into Lofty in your browser, go to **Settings → Integrations → API** (Lofty's official path; older kit docs call this "API Keys"), and generate a personal API token. It's a long string starting with `eyJ` (it's a JWT). Save it to your kit's `.env` as `LOFTY_API_KEY=<paste-token-here>`. If you already did this when you set up the Python client (Phase 1 of this kit), skip; the same key works.
7. **Jotform account.** Free tier is fine. Sign up at `jotform.com`. Heads up on the new-user UX:
   - Ignore the "SAVE 50%" / countdown-timer upsell banner on the workspace home. Free tier is sufficient for this kit.
   - Ignore the "Jotform for Claude" promo card on the workspace home. It's a different integration; this kit uses the Jotform MCP you installed in step 1.
   - If after signup your workspace URL has `?onboardingPrompt=1`, that's a one-time onboarding modal that hides the "Import form" tile. Navigate to `https://www.jotform.com/workspace/` (without the query string) before starting Easy Mode step 2.
8. **Optional, only if you want the buyer recap email to come from your own verified domain:** a Resend account at `resend.com` plus a verified sending domain matching your `OWNER_EMAIL`. Skip this and the Worker still sends the recap, just through Lofty's `send_email` endpoint instead. The Lofty path delivers to the lead's primary email on file in Lofty rather than the email the buyer typed into the form. Most users skip Resend on day 1 and add it later if they want the deliverability and the From address polish.

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
2. **Clone the post-showing form template.** Walk the user through Jotform's current import-from-URL flow:
   - Sign into Jotform.
   - Go to `https://www.jotform.com/workspace/`. If the URL still has `?onboardingPrompt=1` from signup (per prereq #7), strip it first; the onboarding modal hides the "Import form" tile.
   - Click **+ CREATE** (top-left). The "Describe your form" modal opens.
   - Below the AI prompt input, in the "Other ways to create" tiles row, click **Import form**.
   - On the next screen, click **Import from URL**.
   - Paste this URL into the input field: `https://form.jotform.com/261294238566162` (the public template form URL; the kit's canonical template id is documented in the README).
   - Click the green **Import** button. The page tagline says "Share a link, I'll turn it into a form," which sounds like AI synthesis but is actually a faithful clone of the public template (preserving qid layout, hidden fields, Card Form layout, and styling).
   - Jotform redirects to Form Builder for the new form. Capture the new form id from the URL: `https://www.jotform.com/build/<FORM_ID>`. Save as `JOTFORM_FORM_ID` in `.env`.
   - If the user gets an "Unauthorized request" error, the template owner has cloning blocked. Surface that as a setup error and route to the fallback procedure in `assets/jotform_form_template.md`.
   - The cloned form's qids 40 through 50 match the canonical `JOTFORM_FIELD_MAP` shape exactly. Qid 51 on the public template uses Jotform's auto-generated unique name `anythingElse`, but the kit's default `JOTFORM_FIELD_MAP` in `workers/wrangler.jotform.toml` maps qid 51 to the `memory_notes` purpose tag, so the routing works correctly without a per-install map. Only derive a custom map if step 11 (smoke test) shows fields landing in the wrong D1 columns.
   - **Optional theme override.** The template ships with a neutral gold accent on dark heading text. If the user wants their own brand colors or logo, ask: "Want to swap the accent color, text color, or add your logo at the top? You can paste hex codes ('navy and orange' or '#1a1a1a and #D4AF37') and a hosted image URL, or skip to keep the template defaults." If they answer with overrides, call `edit_form` on the cloned form id with a description like `"Update the form header HTML so the accent color is <accent_color>, the heading text color is <text_color>, and add an <img> tag at the top with src=<logo_url> and max-height 64px. Then update the form theme so the primary button color matches <accent_color>."` If they skip, do nothing.
3. **Create (or find) the D1 database.** Idempotent: first call `d1_databases_list` filtered by name `showing_feedback`. If a database with that name already exists, capture its `database_id` and continue. Otherwise call `d1_database_create` with `{name: "showing_feedback"}` and let Cloudflare auto-pick the region (skip `primary_location_hint` unless the user has a strong preference, in which case ask). Capture the returned `database_id`.
4. **Apply the schema migration.** Read `workers/migrations/001_showing_feedback.sql`. Run it via `d1_database_query` against the new database. The migration is wrapped in `CREATE TABLE IF NOT EXISTS` and `CREATE INDEX IF NOT EXISTS`, so re-running on an existing database is a no-op. Verify by running `SELECT COUNT(*) FROM showing_feedback` via `d1_database_query`; expect a numeric result (zero on a fresh db, the existing row count on a re-apply). If `d1_database_query` rejects multi-statement SQL, split the file on semicolons and run each statement separately.
5. **Patch `workers/wrangler.jotform.toml`.** Replace `REPLACE_WITH_D1_ID_FROM_WRANGLER_D1_CREATE` with the captured `database_id`. Replace each `OWNER_*` placeholder with the value from the user's `.env`. The default `JOTFORM_FIELD_MAP` in the file already matches the cloned template's qid layout; leave it as-is unless the smoke test (step 10) flags a mismatch.
6. **Generate `PREFERENCES_API_KEY` silently.** Run `python3 -c "import secrets; print(secrets.token_urlsafe(32))"` and capture the output. Append it to `.env` as `LOFTY_PREFERENCES_API_KEY=<value>` (use Edit, don't show the value to the user, don't echo it in a chat message). Hold the same value in memory for step 7 so it can be pushed to the Worker as a secret in one go. The user never has to see, type, or paste this token.
7. **Push secrets.** Two secrets, both auto-piped so the user never types or pastes them in chat:
   - **`LOFTY_API_KEY`** is read directly from the user's `.env` and piped to wrangler. Run:

     ```
     grep '^LOFTY_API_KEY=' .env | cut -d= -f2- | tr -d '"' | npx wrangler secret put LOFTY_API_KEY -c workers/wrangler.jotform.toml
     ```

     If `.env` is missing or the line is absent, the command errors and the user knows to populate `.env` per prereq #6 first.

   - **`PREFERENCES_API_KEY`** is piped from step 6's generated value:

     ```
     cat /path/to/the/preferences_api_key_file | npx wrangler secret put PREFERENCES_API_KEY -c workers/wrangler.jotform.toml
     ```

   - **First-secret-push prompt to expect:** if the Worker doesn't exist on the Cloudflare account yet (true on every fresh install), wrangler asks `"There doesn't seem to be a Worker called 'jotform-to-lofty'. Do you want to create a new Worker with that name and add secrets to it? (Y/n)"`. Answer `Y` and proceed; this creates an empty Worker shell so the secret can attach to it. The code lands in step 8.

   - **Optional Resend.** Ask the user: "Do you want to send the buyer recap email from your own verified domain via Resend, or have it go out through Lofty's send_email (default)?" If they pick Resend, push `RESEND_API_KEY` the same way. Otherwise skip; the Worker uses `LOFTY_API_KEY` for the recap automatically.

8. **Deploy the Worker.** `cd workers && npx wrangler deploy -c wrangler.jotform.toml`. Two interactive prompts to expect on a fresh Cloudflare account:
   - **workers.dev subdomain registration.** Wrangler warns `"You need to register a workers.dev subdomain before publishing to workers.dev"` and asks `"Would you like to register a workers.dev subdomain now? (Y/n)"`. Answer `Y`. Wrangler then asks for the subdomain name (something like `joe-test`). This is **globally unique on workers.dev and permanent for the account**; pick something the user is happy seeing in their webhook URLs forever. The Worker URL becomes `https://jotform-to-lofty.<subdomain>.workers.dev`.
   - **Wrangler 4.x default warnings.** On every deploy, wrangler may print warnings about `workers_dev` and `preview_urls` defaults. v1.6.1 of this kit sets both explicitly in `wrangler.jotform.toml` to silence the warnings (`workers_dev = true`, `preview_urls = false`); if you see them anyway, your `wrangler.jotform.toml` may be from an older kit version.

   Capture the deployed URL from wrangler's output (the line that reads `Deployed jotform-to-lofty triggers (Xs)` followed by the URL).

9. **Wire the Jotform webhook (Jotform UI).** The Jotform MCP cannot configure webhooks (its `edit_form` only handles question/field edits), so this step is hands-on. Walk the user through Jotform's UI:
   - Open the cloned form in Jotform's Form Builder (`https://www.jotform.com/build/<JOTFORM_FORM_ID>`).
   - Click **SETTINGS** in the top nav of Form Builder.
   - In the left sidebar, click **Integrations**.
   - Find and click **Webhooks** (usually under "Data Management").
   - Paste the Worker URL from step 8 into the "Add a Webhook" input field.
   - Click **Complete Integration** (or **Save**). The URL should now appear in the list with a "Connected" status.

10. **Health check.** `curl <worker_url>/` should return `{"status":"ok","service":"jotform-to-lofty"}`. On a fresh Cloudflare account that just registered a new workers.dev subdomain in step 8, the URL resolves to Cloudflare anycast IPs immediately but **the SSL certificate takes 5-15 minutes to fully propagate**. During that window, `curl` returns exit code 35 (SSL connection error) and the deployment doesn't accept traffic yet. If you hit this, wait a few minutes and retry. Don't move to step 11 until the health check passes cleanly.

11. **Smoke test.** Prompt the user to submit one test entry on the form. Build a prefill URL with a known `lead_id` from the user's Lofty (so the hidden fields land filled in, simulating a real showing link). Confirm three things:
    - The Lofty note lands on the matching lead (use `api.get_notes(<lead_id>)` to check).
    - The D1 row count went from 0 to 1 (`SELECT COUNT(*) FROM showing_feedback`).
    - Every column on the new D1 row is populated, especially `memory_notes` (the qid 51 routing test, which is the v1.6.1 fix's smoke check).

    If any field landed in the wrong D1 column, run `fetch(<form_id>)` to introspect the cloned form's qids, build a corrected `JOTFORM_FIELD_MAP`, push as a Worker variable with `wrangler secret put JOTFORM_FIELD_MAP -c workers/wrangler.jotform.toml`, and redeploy.

If any step fails, Claude reports the exact error and offers to roll back (drop the D1 database, undo the Jotform changes) or to switch to Power User Mode partway.

---

## Power User Mode walkthrough

Run from the kit root unless noted. All commands are copy-paste safe.

### 1. Build the Jotform form

**Recommended: import the public template into your Jotform account.**

1. Sign into Jotform.
2. Go to `https://www.jotform.com/workspace/`. If your URL has `?onboardingPrompt=1` from a fresh signup, strip it first, since the onboarding modal hides the "Import form" tile.
3. Click **+ CREATE** (top-left). The "Describe your form" modal opens.
4. Under the AI prompt input, in the "Other ways to create" tiles, click **Import form**, then **Import from URL**.
5. Paste `https://form.jotform.com/261294238566162` into the URL input field. (The kit's canonical template id is documented in the README.)
6. Click the green **Import** button. Jotform's tagline says "Share a link, I'll turn it into a form," but the actual behavior is a faithful clone of the public template (preserving qid layout, hidden fields, Card Form layout, and styling).
7. You land in Form Builder. Your new form id is in the URL: `https://www.jotform.com/build/<FORM_ID>`. Save it to `.env` as `JOTFORM_FORM_ID`.

The cloned form already has all the questions, hidden fields, and the polished Card layout. The Worker's default `JOTFORM_FIELD_MAP` (shipped in `wrangler.jotform.toml`) already matches the qid layout, so no per-install map is needed.

If the import returns "Unauthorized request. You do not have access to this form," the template owner has cloning blocked. Use the fallback procedure in `assets/jotform_form_template.md` instead.

**Optional brand swap.** The template ships with a neutral gold accent on dark heading text. To swap colors: open the form in Jotform's Form Designer, change the theme color, and edit the header HTML block (top question on the form) so the inline `color:` values match your brand. To add a logo, paste an `<img src="<your-hosted-logo-url>" style="max-height:64px;margin:0 auto 12px;display:block;">` line at the top of the header div.

**Fallback: build the form from scratch.** If you don't have a Jotform account willing to clone shared templates, or if the template URL is unavailable, follow the from-scratch procedure in `assets/jotform_form_template.md`. This path uses Jotform's `create_form` natural-language agent and produces a Classic Form with a few rough edges that need follow-up edits. Field list and unique names:

- 6 rating questions (1-5 scale), Unique Names: `first_reaction`, `daily_life_fit`, `neighborhood_rating`, `condition_rating`, `value_rating`, `short_list`.
- 2 text questions (long-text), Unique Names: `standout_text`, `memory_notes`.
- 2 multi-select questions, Unique Names: `loved_tags`, `dealbreaker_tags`. Use the starter tag lists from `assets/post_showing_questions.yaml`.
- 4 hidden fields prefilled by the showing link: `lead_id`, `propertyAddress`, `showingDate`, `client_name`. Plus a `buyer_email` field if you want the recap email.

Set Unique Names exactly as listed; the Worker keys off them when no `JOTFORM_FIELD_MAP` is configured.

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

---

# Tier 3 setup: showing-reminder SMS Worker

Tier 3 deploys a second Cloudflare Worker (`showing-sms`) that fires the post-showing feedback text at the exact moment a showing starts. It uses per-showing Durable Object alarms (no cron), so precision is "within seconds" rather than "within a minute" and idle wakeups are zero.

This section is parallel to the Tier 2 section above. The pre-conditions, modes, and verify-and-rollback structure are the same; the deltas live below.

## What changed in v1.7

- New Worker `showing-sms` ported from a battle-tested production implementation. 162ms alarm precision validated in production at scale.
- New wrangler config at `workers/wrangler.showing-sms.toml` with `workers_dev=true`, `preview_urls=false`, and an append-only `[[migrations]]` block that auto-creates the `ShowingTimer` Durable Object class on first deploy.
- New unit test at `scripts/test_showing_sms_worker.mjs` covering auth, KV key shape, request validation, queue entry build, and SMS body format. 36 assertions, runs in plain Node.
- New `OWNER_FIRST_NAME` env var so the SMS body says "Hi {client}, it's {your name}..." Defaults to "your agent" if unset.

## What you get

- `prepare_showing(lead_id=...)` in Python schedules a feedback SMS for the moment the showing starts. The Worker stores the entry in KV, creates a Durable Object instance, sets an alarm, and Cloudflare wakes the DO at send_at, no polling required.
- `api.list_pending_showings(lead_id)` returns everything queued for a lead.
- `api.cancel_showing(lead_id, full_address)` deletes the KV entry AND cancels the DO alarm so a cancelled tour does not still trigger the SMS.
- Audit trail: KV entries flip from `pending` to `sent` with the message body, the phone the SMS went to, and a 30-day expiration.

## Tier 3 prereqs

Same as Tier 2 prereqs, plus three additions:

1. **Cloudflare Workers Paid plan ($5/mo) enabled on the deploying account.** Durable Objects are not available on the free tier. Dashboard path: Workers & Pages → Plans → Workers Paid. The plan also bumps your daily Worker request limit from 100k to 10M.
2. **Tier 2 deployed first.** Tier 3 reuses the same `LOFTY_API_KEY` secret already pushed to your Cloudflare account in Tier 2 step 7. If Tier 2 is not yet deployed, run that first.
3. **A virtual phone number in Lofty.** Lofty's SMS endpoint requires you to have a virtual number on your account. Without one, `sendLoftySms` returns an error and the SMS never goes out. Confirm yours in Lofty under Settings → Numbers.

## Tier 3 test pyramid (the three layers)

Tier 3 ships with a three-layer test approach so you can validate the Worker without paying twice for a "staging" Cloudflare account.

**Layer 1: unit tests.** `node scripts/test_showing_sms_worker.mjs` runs 36 assertions against the deterministic helpers (auth, KV key shape, request validation, queue entry build, SMS body format). Runs in plain Node, no Cloudflare account involved, zero dollars. Run this on every code change. Catches the bulk of port-induced bugs (typos, wrong env var names, broken JSON shapes).

**Layer 2: `wrangler dev --local`.** From the `workers/` folder run `npx wrangler dev -c wrangler.showing-sms.toml --local`. Hits the HTTP routes (`/enqueue`, `/queue`, `/queue/<key>` GET and DELETE) with curl. Local dev simulates DO alarms but the timing is approximate, so this layer is "does the wiring work" not "does the alarm fire at the right second." Still free, no account needed.

**Layer 3: deploy to your existing Workers Paid account with a separate Worker name.** If you already pay for Workers Paid (because you run a different DO Worker on that account), you can validate the SMS Worker end-to-end without paying twice. Change `name = "showing-sms"` to `name = "showing-sms-staging"` in `wrangler.showing-sms.toml`, deploy, run one real showing end-to-end against your own lead ID, then `npx wrangler delete -c wrangler.showing-sms.toml --name showing-sms-staging` to tear it down. The real production Worker is untouched.

## Easy Mode walkthrough (Tier 3)

This walkthrough is what Claude follows for you. Each step is a single chat exchange. Stop the moment something errors and read the "Common errors" section below.

**Step 0: Open a terminal window.** A couple of these steps need a terminal (the black or white window with a cursor where you type commands). If you have never used one, here is how to find yours.

- **macOS:** Press and hold the Command key, tap the Space bar to open Spotlight, type "Terminal," and press Enter. A small window with a blinking cursor appears. Leave it open; you will paste commands into it.
- **Windows:** Click the Start button, type "PowerShell," and press Enter. A blue or black window with a blinking cursor appears.

You only need one terminal window open at a time. When Claude tells you to "run" a command, it means: click into that window, paste the command Claude just gave you, and press Enter.

1. **Confirm Workers Paid is enabled.** Claude calls the Cloudflare MCP to verify the account is on a paid plan. If not, Claude pauses and points you at the Workers & Pages → Plans page to upgrade.
2. **Create the KV namespace.** Claude runs `npx wrangler kv namespace create SHOWING_SMS_QUEUE -c wrangler.showing-sms.toml` and pastes the returned id into the `[[kv_namespaces]]` block.
3. **Set `OWNER_FIRST_NAME` in `wrangler.showing-sms.toml`.** Claude asks you for the first name you want in your SMS body and writes it into the `[vars]` block.
4. **Push the `LOFTY_API_KEY` secret.** Tier 2 already pushed this for the `jotform-to-lofty` Worker. The `showing-sms` Worker needs its own copy on the same key.
5. **Deploy.** `npx wrangler deploy -c wrangler.showing-sms.toml`. The first deploy auto-creates the `ShowingTimer` Durable Object class via the `[[migrations]]` block.
6. **Health check.** `curl https://showing-sms.<your-subdomain>.workers.dev/` should return `{"status":"ok","service":"showing-sms","architecture":"durable-object-alarms"}`. Fresh subdomains take 5-15 minutes for the SSL certificate to propagate; curl returns exit code 35 during that window.
7. **Smoke test.** Claude enqueues a test showing for your own lead ID, set 90 seconds in the future, and waits for the SMS to land on your phone. After it arrives, Claude cancels the entry and confirms the KV row reflects `sent`.
8. **Wire `SHOWING_SMS_WORKER_URL` into `.env`.** So `prepare_showing` in `lofty_api.py` knows where to POST.
9. **Done.** Tier 3 is live.

## Power User Mode walkthrough (Tier 3)

For users who want to run the commands themselves. Same 9 steps as Easy Mode, but you drive.

### 0. Open a terminal

If you do not already have one open: macOS users press Cmd+Space, type "Terminal," and press Enter. Windows users open PowerShell from the Start menu. Every shell snippet below runs in that window. Pasting a multi-line snippet runs each line in order; you do not need to type them one at a time.

### 1. Confirm Workers Paid

In the Cloudflare dashboard go to Workers & Pages → Plans. If the active plan is "Free," click Workers Paid and complete the $5/mo subscription. Without this, Durable Objects do not exist and deploys fail with "no such binding: SHOWING_DO."

### 2. Create the KV namespace

From `lofty-cowork-helper/workers/`:

```
npx wrangler kv namespace create SHOWING_SMS_QUEUE -c wrangler.showing-sms.toml
```

Copy the returned `id` into the `[[kv_namespaces]]` block of `wrangler.showing-sms.toml`, replacing `REPLACE_WITH_YOUR_SHOWING_SMS_QUEUE_KV_ID`.

### 3. Set `OWNER_FIRST_NAME`

Open `wrangler.showing-sms.toml` and update the `[vars]` block:

```
[vars]
OWNER_FIRST_NAME = "Jane"
```

The default is `"your agent"`. Replace with your first name. This is what shows up in the SMS body ("Hi Jack, it's Jane. Quick feedback form for ...").

### 4. Push the `LOFTY_API_KEY` secret

```
echo "$LOFTY_API_KEY" | npx wrangler secret put LOFTY_API_KEY -c wrangler.showing-sms.toml
```

Wrangler will prompt you to create the Worker if it does not exist. Confirm.

### 5. Deploy

```
npx wrangler deploy -c wrangler.showing-sms.toml
```

The first deploy creates the `ShowingTimer` Durable Object class via the `[[migrations]]` block. Subsequent deploys reuse the existing class. Never edit the `[[migrations]]` block; only append new entries for future class changes.

### 6. Health check

```
curl https://showing-sms.<your-subdomain>.workers.dev/
```

Expected:

```json
{"status":"ok","service":"showing-sms","architecture":"durable-object-alarms"}
```

If curl returns exit code 35, the SSL certificate is still propagating. Wait 5-15 minutes and retry.

### 7. Smoke test

Enqueue a test showing 90 seconds in the future against your own lead ID:

```
curl -X POST https://showing-sms.<your-subdomain>.workers.dev/enqueue \
  -H "Authorization: Bearer $LOFTY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "lead_id": <your_own_lead_id>,
    "send_at": "<now+90s as ISO 8601>",
    "short_url": "https://example.com/test",
    "property_short_address": "Tier 3 smoke test"
  }'
```

After 90 seconds, your phone should buzz with the SMS. Check the KV entry to confirm the audit trail:

```
curl https://showing-sms.<your-subdomain>.workers.dev/queue?lead_id=<your_own_lead_id> \
  -H "Authorization: Bearer $LOFTY_API_KEY"
```

The status should be `"sent"` with `sent_at`, `sent_to_phone`, and `sent_message` populated.

### 8. Wire `.env`

Add to `.env` at the repo root:

```
SHOWING_SMS_WORKER_URL=https://showing-sms.<your-subdomain>.workers.dev
```

`lofty_api.py`'s `prepare_showing`, `list_pending_showings`, and `cancel_showing` read this var.

### 9. Done

Tier 3 is live. The next showing scheduled through `prepare_showing` will trigger an SMS at the showing's start time.

## Verify and troubleshoot (Tier 3)

### Common errors (Tier 3 specific)

- **`no such binding: SHOWING_DO`** at deploy time. Workers Paid is not enabled on the account, OR the `[[migrations]]` block is missing from `wrangler.showing-sms.toml`. Confirm both.
- **`durable_objects.bindings: subrequest needed`** when calling `/enqueue`. Sometimes happens on the very first request after a fresh deploy because the DO class is still warming up. Wait 30 seconds and retry; it self-resolves.
- **SMS never arrives, KV status stays `pending`.** Check the Worker's tail log: `npx wrangler tail showing-sms -c wrangler.showing-sms.toml`. Most common cause is no virtual number on the Lofty account, which produces a Lofty 4xx error in the tail.
- **SMS arrives but says "Hi there, it's your agent..."** `OWNER_FIRST_NAME` is unset or `firstName` on the lead is empty. Confirm the env var was set in step 3, redeploy, and verify the lead's first name in Lofty.
- **Cron trigger still firing on the old deploy.** If you migrated from a cron-driven version of this Worker, the cron trigger in the dashboard does not auto-delete. Delete it manually: Workers & Pages → showing-sms → Triggers → Cron Triggers → Remove.

### Roll back

Same shape as the Tier 2 roll-back. From `workers/`:

```
npx wrangler delete -c wrangler.showing-sms.toml --name showing-sms
```

Then remove the KV namespace from the dashboard (Workers & Pages → KV → SHOWING_SMS_QUEUE → Delete). The `LOFTY_API_KEY` secret can stay; the Tier 2 Worker still uses it.

---

# Tier 4 setup: leads-index Worker (free tier, opt-in)

Tier 4 deploys a third Cloudflare Worker (`leads-index`) that keeps a live mirror of your Lofty leads inside Cloudflare KV. Lofty pushes lead create/update/delete events via webhook list 2; the Python client (`lofty_api.py`) reads from the KV mirror when `LOFTY_LEADS_INDEX_SOURCE=worker` is set. Result: `find_client` and `get_recent_visits_from_index` stay fast and accurate even for large CRMs.

This section is parallel to the Tier 3 section above. Tier 4 runs on the Cloudflare **free** plan. No Workers Paid required.

## When you need Tier 4

If your CRM has more than a few thousand leads, OR you regularly hit `find_client` for clients who are not in the 25 most-recently-created list, Tier 4 is worth deploying. The default file fallback (`data/leads_index.json` built by `scripts/refresh_leads_index.py`) is fine for small CRMs, but it only refreshes when you run that script. Tier 4 upgrades that to a live, webhook-fed mirror that updates within 1-5 minutes of any change in Lofty, with no polling.

If your CRM is small (a few hundred leads) and `find_client` always works for you, you can skip Tier 4 entirely. The kit works fine without it.

## What changed in v1.9

- New Worker `leads-index` ported from a battle-tested production implementation.
- New wrangler config at `workers/wrangler.leads-index.toml` with `workers_dev=true`, `preview_urls=false`. No Durable Objects; this Worker runs on the free tier.
- New unit test at `scripts/test_leads_index_worker.mjs` covering Bearer auth, lead/event extraction across webhook payload shapes, lead normalization, content-diff field comparison, array equality, and the safety-rule defaults. 67 assertions, runs in plain Node.
- Three Cloudflare-side secrets: `LOFTY_API_KEY` (same value Tier 2 and Tier 3 use), `WEBHOOK_SECRET` (random; the path segment on `/webhook/<secret>`), `EXPORT_API_KEY` (random; the Bearer token `lofty_api.py` uses to read `/export`).
- Write-side cost controls baked into the Worker: content-diff check (skip the KV write if no find_client-relevant field changed), stage exclusion (DNC / Archived / Agents / Vendors are never stored), `last_seen_at` timestamps, and skip metrics surfaced on `/stats`.

## What you get

- Real-time KV mirror of your Lofty leads with 1-5 minute write latency. No polling.
- `find_client` reads from KV (via `lofty_api.py` when `LOFTY_LEADS_INDEX_SOURCE=worker` is set) instead of falling back to the local file.
- Skip metrics on `/stats`: `skippedNoChange` (no-op updates), `skippedStageExcluded` (DNC / Archived / Agents-Vendors filtered at write time), `deletedViaStage` (leads moved into an excluded stage and dropped from KV), plus `eventCount`, `bootstrapCount`, and timestamps.
- Resource budget: ~1 KB per lead in KV, so 10,000 leads is ~10 MB (1% of the free 1 GB cap). Typical webhook traffic for an active agent is 50-200 events/day, well under the 1,000 KV writes/day free cap. Read traffic from `find_client` is cached client-side in `lofty_api.py`.

## Tier 4 prereqs

Same as Tier 2 prereqs, plus three additions:

1. **Tier 2 deployed first.** Tier 4 reuses the same `LOFTY_API_KEY` secret already on your Cloudflare account. If Tier 2 is not yet deployed, run that first. (Tier 3 is NOT a prereq; Tier 4 can run on a free Cloudflare account that skipped Tier 3.)
2. **Lofty plan with webhook access.** Lofty webhook list 2 (Lead Info: create / update / delete) is what feeds the Worker. Confirm under Settings → API → Webhooks in Lofty.
3. **A working `scripts/refresh_leads_index.py`.** The initial bootstrap step pushes your current leads to the Worker via `/bulk-import`. Run `python3 scripts/refresh_leads_index.py` once before Tier 4 setup to confirm it builds `data/leads_index.json` cleanly.

## Tier 4 test pyramid (the three layers)

Tier 4 ships with a three-layer test approach so you can validate the Worker before pointing live webhooks at it.

**Layer 1: unit tests.** `node scripts/test_leads_index_worker.mjs` runs 67 assertions against the deterministic helpers (auth, lead/event extraction, normalization, content diff, array equality, exclusion-set sanity). Runs in plain Node, no Cloudflare account involved, zero dollars. Run this on every code change. Catches the bulk of port-induced bugs.

**Layer 2: deploy to a staging Worker name.** Change `name = "leads-index"` to `name = "leads-index-staging"` in `wrangler.leads-index.toml`, deploy against a separate `LEADS_INDEX_STAGING` KV namespace, hit each HTTP route with curl (`/`, `/stats`, `/webhook/<secret>`, `/export`, `/lead/<id>`, `/bulk-import`), then `npx wrangler delete --name leads-index-staging` to tear it down. Your production `leads-index` Worker (if you ran a prior version) is untouched. Free tier, no extra cost.

**Layer 3: real Lofty webhook list 2.** Wire your actual Lofty webhook to the staging Worker URL, edit one real lead in the Lofty UI (change a tag or stage), confirm the KV row updates within 1-5 minutes, and confirm `api.find_client` with `LOFTY_LEADS_INDEX_SOURCE=worker` sees the change. Then unwire the webhook, tear down the staging Worker, and rewire to your production Worker.

## Easy Mode walkthrough (Tier 4)

This walkthrough is what Claude follows for you. Each step is a single chat exchange. Stop the moment something errors and read the "Common errors" section below.

**Step 0: Open a terminal window.** A couple of these steps need a terminal (the black or white window with a cursor where you type commands). If you have never used one, here is how to find yours.

- **macOS:** Press and hold the Command key, tap the Space bar to open Spotlight, type "Terminal," and press Enter. A small window with a blinking cursor appears. Leave it open; you will paste commands into it.
- **Windows:** Click the Start button, type "PowerShell," and press Enter. A blue or black window with a blinking cursor appears.

You only need one terminal window open at a time. When Claude tells you to "run" a command, it means: click into that window, paste the command Claude just gave you, and press Enter.

1. **Confirm Tier 2 is deployed.** Claude calls the Cloudflare MCP to verify the `jotform-to-lofty` Worker exists. If not, Claude pauses and routes you to the Tier 2 setup section above.
2. **Create the KV namespace.** Claude runs `npx wrangler kv namespace create LEADS_INDEX -c wrangler.leads-index.toml` and pastes the returned id into the `[[kv_namespaces]]` block.
3. **Push the three secrets.** Claude pushes `LOFTY_API_KEY` (reusing the value from your `.env`), generates random values for `WEBHOOK_SECRET` and `EXPORT_API_KEY` with `openssl rand -hex 32`, pushes both as secrets, and stores the generated values back into your `.env` so the Python client can read them.
4. **Deploy.** `npx wrangler deploy -c wrangler.leads-index.toml`.
5. **Health check.** `curl https://leads-index.<your-subdomain>.workers.dev/` should return `{"status":"ok","service":"leads-index","host":"..."}`. Fresh subdomains take 5-15 minutes for the SSL certificate to propagate; curl returns exit code 35 during that window.
6. **Bootstrap the index.** Claude runs `python3 scripts/refresh_leads_index.py --push-to-worker` to do the initial one-time `/bulk-import` of every lead from your current `data/leads_index.json`. The response tells you how many leads were imported and how many were skipped via stage exclusion.
7. **Wire Lofty webhook list 2.** Claude runs `python3 scripts/lofty_api.py webhook-create 2 https://leads-index.<your-subdomain>.workers.dev/webhook/<WEBHOOK_SECRET>` to register your Worker URL with Lofty. From this point forward, every lead create / update / delete in Lofty fires a webhook into the Worker.
8. **Wire `.env`.** Claude appends `LOFTY_LEADS_INDEX_SOURCE=worker` and `LEADS_INDEX_WORKER_URL=https://leads-index.<your-subdomain>.workers.dev` to your `.env`. From now on, `find_client` and `get_recent_visits_from_index` read from the live KV index.
9. **Done.** Tier 4 is live. Any new lead in Lofty appears in `find_client` within 1-5 minutes without a manual refresh.

## Power User Mode walkthrough (Tier 4)

Same 9 steps as Easy Mode, but you drive.

### 0. Open a terminal

If you do not already have one open: macOS users press Cmd+Space, type "Terminal," and press Enter. Windows users open PowerShell from the Start menu. Every shell snippet below runs in that window.

### 1. Confirm Tier 2 is deployed

Tier 4 reuses your Tier 2 `LOFTY_API_KEY` and assumes you have a working `.env`. From the repo root:

```
ls lofty-cowork-helper/workers/wrangler.jotform.toml
grep -q LOFTY_API_KEY .env && echo "OK: LOFTY_API_KEY in .env"
```

If either fails, go finish Tier 2 first.

### 2. Create the KV namespace

From `lofty-cowork-helper/workers/`:

```
npx wrangler kv namespace create LEADS_INDEX -c wrangler.leads-index.toml
```

Copy the returned `id` into the `[[kv_namespaces]]` block of `wrangler.leads-index.toml`, replacing `REPLACE_WITH_YOUR_LEADS_INDEX_KV_ID`.

### 3. Push the three secrets

```
# Reuse the same Lofty API key Tier 2 and Tier 3 use.
echo "$LOFTY_API_KEY" | npx wrangler secret put LOFTY_API_KEY -c wrangler.leads-index.toml

# Generate a random WEBHOOK_SECRET. This becomes the path segment on
# /webhook/<secret>; it filters out random POSTs from anyone who finds
# your Worker URL.
WEBHOOK_SECRET=$(openssl rand -hex 32)
echo "$WEBHOOK_SECRET" | npx wrangler secret put WEBHOOK_SECRET -c wrangler.leads-index.toml

# Generate a random EXPORT_API_KEY. This is the Bearer token your Python
# client uses to call /export, /lead/<id>, /bulk-import.
EXPORT_API_KEY=$(openssl rand -hex 32)
echo "$EXPORT_API_KEY" | npx wrangler secret put EXPORT_API_KEY -c wrangler.leads-index.toml
```

Save `WEBHOOK_SECRET` and `EXPORT_API_KEY` somewhere you can retrieve them. You will need both in step 7 (webhook wiring) and step 8 (`.env` write).

Wrangler will prompt you to create the Worker on the first `secret put` if it does not exist. Confirm.

### 4. Deploy

```
npx wrangler deploy -c wrangler.leads-index.toml
```

The Worker comes up at `https://leads-index.<your-subdomain>.workers.dev`.

### 5. Health check

```
curl https://leads-index.<your-subdomain>.workers.dev/
```

Expected:

```json
{
  "status": "ok",
  "service": "leads-index",
  "host": "leads-index.<your-subdomain>.workers.dev"
}
```

If curl returns exit code 35, the SSL certificate is still propagating. Wait 5-15 minutes and retry.

Verify Bearer auth on `/export`:

```
curl -H "Authorization: Bearer $EXPORT_API_KEY" \
  https://leads-index.<your-subdomain>.workers.dev/export | head -20
```

Expected: a JSON document with `count: 0, leads: []` (the KV index is empty until step 6).

### 6. Bootstrap the index

Push your current local index up to the Worker so `find_client` has something to read on day one:

```
python3 scripts/refresh_leads_index.py --push-to-worker
```

The flag tells `refresh_leads_index.py` to POST the resulting payload to `<LEADS_INDEX_WORKER_URL>/bulk-import` with the Bearer token. You should see something like:

```
imported: 612, skipped_stage: 38
```

`skipped_stage` is the count of leads excluded by the safety-rule defaults (DNC / Archived / Agents-Vendors). Those leads stay in Lofty; they just do not consume your KV storage.

### 7. Wire Lofty webhook list 2

```
python3 scripts/lofty_api.py webhook-create 2 \
  https://leads-index.<your-subdomain>.workers.dev/webhook/$WEBHOOK_SECRET
```

This registers your Worker URL with Lofty's webhook list 2. From this point on, every lead create / update / delete fires a POST into the Worker.

Confirm the registration:

```
python3 scripts/lofty_api.py webhooks
```

Look for a list-2 entry pointing at your Worker URL.

### 8. Wire `.env`

Append to `.env` at the repo root:

```
LOFTY_LEADS_INDEX_SOURCE=worker
LEADS_INDEX_WORKER_URL=https://leads-index.<your-subdomain>.workers.dev
LEADS_INDEX_EXPORT_API_KEY=<the EXPORT_API_KEY you generated in step 3>
```

`lofty_api.py`'s `find_client` and `get_recent_visits_from_index` read these vars. If `LOFTY_LEADS_INDEX_SOURCE` is anything other than `worker`, the Python client falls back to the local file (the v1.4.1 behavior).

### 9. Done

Tier 4 is live. Edit any lead in Lofty (change a tag, update a phone), then within 1-5 minutes:

```
curl https://leads-index.<your-subdomain>.workers.dev/stats
```

`eventCount` should have ticked up. If `skippedNoChange` ticked up instead, the diff check decided your edit did not touch a find_client-relevant field; that is correct behavior.

## Verify and troubleshoot (Tier 4)

### Common errors (Tier 4 specific)

- **`unauthorized` on `/export` or `/bulk-import`.** Your Bearer header is missing, malformed, or does not match the `EXPORT_API_KEY` you pushed in step 3. The header must be exactly `Authorization: Bearer <value>`. The Worker also rejects the `token <value>` scheme; only `Bearer` works on this Worker (Lofty's own API uses `token`, but this Worker is independent).
- **`forbidden` on `/webhook/<secret>`.** The secret in the URL path does not match the `WEBHOOK_SECRET` you pushed. If you rotated the secret, also update the webhook registration in Lofty (delete the old list-2 entry and re-register with the new URL).
- **`eventCount` is not ticking up after lead edits.** Check the Worker tail log: `npx wrangler tail leads-index -c wrangler.leads-index.toml`. The most common cause is the webhook is not registered in Lofty (re-run step 7) or the registered URL has a typo in the secret path (recreate with the right value).
- **KV is at 1,000 writes/day and starting to throttle.** Look at `/stats` for the ratio of `eventCount` to `skippedNoChange`. If the ratio is high (most events being skipped), your webhook stream is noisy. If `skippedNoChange` is low, real edits are happening and you may need to either edit `DIFF_FIELDS` in `leads_index_worker.js` to filter more aggressively, or accept that your workload exceeds the free tier and upgrade to Workers Paid.
- **`find_client` still reading from the local file even after `LOFTY_LEADS_INDEX_SOURCE=worker` is set.** Reload your shell or your editor so the new env var is picked up. Confirm with `python3 -c "import os; print(os.environ.get('LOFTY_LEADS_INDEX_SOURCE'))"`.
- **Stage-excluded lead is still showing up in `find_client`.** The stage exclusion runs at write time on the Worker. If a lead was excluded at bootstrap time it is not in KV; if its stage later changed to an excluded stage, the next webhook event drops it. If it is still appearing, run `python3 scripts/refresh_leads_index.py --push-to-worker` to force a fresh bootstrap.

### Roll back

Same shape as the Tier 2 and Tier 3 roll-backs. From `workers/`:

```
npx wrangler delete -c wrangler.leads-index.toml --name leads-index
```

Then remove the KV namespace from the dashboard (Workers & Pages → KV → LEADS_INDEX → Delete). The `LOFTY_API_KEY` secret can stay; the Tier 2 and Tier 3 Workers still use it.

Set `LOFTY_LEADS_INDEX_SOURCE=file` (or unset it) in your `.env` so `lofty_api.py` reverts to the local file fallback.

Finally, unwire the Lofty webhook so events do not pile up against a deleted Worker:

```
python3 scripts/lofty_api.py webhooks
python3 scripts/lofty_api.py webhook-delete <webhook-id>
```

---

## What comes next

Tier 2 unlocks:

- `api.get_buyer_preferences(lead_id)` from Python returns the aggregated profile.
- A "buyer profile" Cowork artifact you can ask Claude to render for any lead.
- Pre-filled Google Calendar events for follow-up showings, prefilled with the buyer's top 3 must-haves and dealbreakers.

Tier 3 unlocks:

- `prepare_showing(lead_id=...)` from Python schedules the post-showing SMS at exact precision.
- `api.list_pending_showings(lead_id)` and `api.cancel_showing(lead_id, full_address)` for queue management.
- The full per-showing audit trail in `SHOWING_SMS_QUEUE` KV with 30-day retention.

Tier 4 unlocks:

- `find_client` and `get_recent_visits_from_index` read from a live, webhook-fed KV mirror instead of the local file fallback.
- 1-5 minute write latency on lead changes in Lofty, with no polling.
- Skip metrics on `/stats` so you can see how noisy your webhook stream is and whether the content-diff check is doing its job.

The short-links Worker is the remaining opt-in Worker on the roadmap. It is candidate-for-cut; whether it ships in a future v1.9.x is a decision deferred until after Tier 4 sees real-user usage.
