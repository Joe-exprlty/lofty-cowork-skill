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
- Step 9 (webhook wiring) is rewritten — the Jotform MCP cannot wire webhooks, so users wire them via Jotform's UI (Settings → Integrations → Webhooks).
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
   - Click the green **Import** button. The page tagline says "Share a link — I'll turn it into a form," which sounds like AI synthesis but is actually a faithful clone of the public template (preserving qid layout, hidden fields, Card Form layout, and styling).
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
    - Every column on the new D1 row is populated, especially `memory_notes` (the qid 51 routing test — this is the v1.6.1 fix's smoke check).

    If any field landed in the wrong D1 column, run `fetch(<form_id>)` to introspect the cloned form's qids, build a corrected `JOTFORM_FIELD_MAP`, push as a Worker variable with `wrangler secret put JOTFORM_FIELD_MAP -c workers/wrangler.jotform.toml`, and redeploy.

If any step fails, Claude reports the exact error and offers to roll back (drop the D1 database, undo the Jotform changes) or to switch to Power User Mode partway.

---

## Power User Mode walkthrough

Run from the kit root unless noted. All commands are copy-paste safe.

### 1. Build the Jotform form

**Recommended: import the public template into your Jotform account.**

1. Sign into Jotform.
2. Go to `https://www.jotform.com/workspace/`. If your URL has `?onboardingPrompt=1` from a fresh signup, strip it first — the onboarding modal hides the "Import form" tile.
3. Click **+ CREATE** (top-left). The "Describe your form" modal opens.
4. Under the AI prompt input, in the "Other ways to create" tiles, click **Import form**, then **Import from URL**.
5. Paste `https://form.jotform.com/261294238566162` into the URL input field. (The kit's canonical template id is documented in the README.)
6. Click the green **Import** button. Jotform's tagline says "Share a link — I'll turn it into a form," but the actual behavior is a faithful clone of the public template (preserving qid layout, hidden fields, Card Form layout, and styling).
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

## What comes next

Tier 2 unlocks:

- `api.get_buyer_preferences(lead_id)` from Python returns the aggregated profile.
- A "buyer profile" Cowork artifact you can ask Claude to render for any lead.
- Pre-filled Google Calendar events for follow-up showings, prefilled with the buyer's top 3 must-haves and dealbreakers.

Tier 3 (the showing-reminder SMS Worker) ships in v1.7 and requires the Cloudflare Workers Paid plan ($5/mo). Tier 3 polish (the leads-index and short-links Workers) is opt-in and ships in v1.7.x or later.
