# Session Handoff: Phase 2

This file gets a new Claude Cowork session up to speed on the **Phase 2** build of the Lofty + Cowork skill project. Read this first, then explore the current files before doing anything.

---

## NEXT SESSION QUICK START

> Joe opened a new prompt and typed "Read Handoff.md and continue conversation." Follow this section to pick up exactly where we left off. Do NOT recap the prior session's work back to Joe; he was there. Get to the point.

**Where we left off (May 8, 2026, second session of the day):** v1.5 is mid-build. v1.4.1 is still the latest tagged release on GitHub. The May 8 second session resolved one open decision and landed five concrete artifacts on disk in the public skill. Joe will commit and push everything in this snapshot before the next session opens, so origin/main will have the new files when you arrive.

**What got built in the second May 8 session (already on disk, not yet shipped to GitHub at the time of this handoff write):**

- `lofty-cowork-helper/workers/jotform_to_lofty_worker.js` ported from `saling-automation`. Joe-specifics replaced with env-driven `OWNER_*` vars. New `JOTFORM_FIELD_MAP` env var routes submissions by Jotform qid when populated, falls back to alias matching for backward compat with Joe's pre-migration form. Resend is now opt-in; if `RESEND_API_KEY` is unset the recap email goes through Lofty's `POST /v1.0/message/email/send` endpoint instead.
- `lofty-cowork-helper/workers/migrations/001_showing_feedback.sql` ported verbatim, only the path comment in the header changed.
- `lofty-cowork-helper/workers/wrangler.jotform.toml` templated. Database id, owner identity, and `JOTFORM_FIELD_MAP` are placeholders. Resend reframed as opt-in with the Lofty fallback as default.
- `lofty-cowork-helper/references/workers_setup.md` is the v1.5 deploy runbook. Leads with an Easy Mode vs Power User Mode picker. Easy Mode walkthrough is the 12-step Cloudflare MCP + Jotform MCP + wrangler sequence. Power User Mode is the manual shell-and-clicks version. All five Tier 2 optimizations (form built programmatically with brand inputs, Resend optional, Cloudflare MCP for D1, auto-generated `PREFERENCES_API_KEY`, auto-wired Jotform webhook) are documented in the Easy Mode steps.
- `lofty-cowork-helper/assets/jotform_form_template.md` is a new asset Easy Mode reads at runtime. Contains the natural-language `create_form` prompt template, post-creation `fetch` introspection, and the `JOTFORM_FIELD_MAP` build procedure. Captures brand inputs (accent color, text color, optional logo URL) before form creation per the locked branding step.
- `lofty-cowork-helper/assets/post_showing_questions.yaml` updated. `header_html` now uses `{{ACCENT_COLOR}}`, `{{TEXT_COLOR}}`, and `{{LOGO_HTML}}` tokens; `default_accent_color` and `default_text_color` fields hold sensible fallbacks (gold + dark heading text) for the "user accepts defaults" path.
- `lofty-cowork-helper/assets/env-template` updated. Added optional `OWNER_WEBSITE` line and reframed `RESEND_API_KEY` as optional with a clear description of what falls back to what.
- `lofty-cowork-helper/scripts/test_worker_parsers.mjs` is a new smoke test. Synthesizes Jotform-shaped POST bodies and walks them through the Worker's parser refactor. Covers four scenarios: legacy form (alias-only), fresh form without map, fresh form with map, and a renamed-fields case where only the qid map saves you. All 32 assertions pass.

**Path B was chosen for the form-import question** (one codebase across the public skill and Joe's production). The Worker on disk in the public skill is the same code that will replace `saling-automation/worker/jotform_to_lofty_worker.js` once the production migration runs. The production migration is still pending; Joe's Worker has not been touched yet.

**Do these checks silently first (do NOT narrate them to Joe):**

1. Verify `~/Code/saling-automation/` is mounted via `mcp__cowork__request_cowork_directory`. If not, request it.
2. Run `git log --oneline -5` on `~/Code/lofty-cowork-skill`. There should be a recent commit landing the v1.5 mid-build files (`lofty-cowork-helper/workers/`, `lofty-cowork-helper/references/workers_setup.md`, `lofty-cowork-helper/assets/jotform_form_template.md`, `lofty-cowork-helper/scripts/test_worker_parsers.mjs`, plus updates to `lofty-cowork-helper/assets/post_showing_questions.yaml` and `lofty-cowork-helper/assets/env-template`). Confirm the working tree is clean.
3. Skim these files end-to-end so you know what's there:
   - `lofty-cowork-helper/references/workers_setup.md`
   - `lofty-cowork-helper/assets/jotform_form_template.md`
   - `lofty-cowork-helper/workers/jotform_to_lofty_worker.js` (most of the actual code logic for v1.5)
   - `lofty-cowork-helper/scripts/test_worker_parsers.mjs` and confirm it still passes by running `node lofty-cowork-helper/scripts/test_worker_parsers.mjs`
4. Read the "v1.5 ladder remaining" section of THIS file so you know what comes next.

**Then, as your FIRST user-facing message, ask Joe this:**

> Picking up at v1.5. Three things left before v1.5 ships: B1.8 (the "set up Tier 2" picker in SKILL.md that routes Easy Mode vs Power User Mode), the production migration (rebuild your Jotform form, swap your saling-automation Worker to the new code, validate one end-to-end submission), and the v1.5 release commit + tag. Recommend tackling in that order since the picker is needed before the production migration can run end-to-end. Want to push into B1.8 next?

Use the AskUserQuestion tool for this so Joe gets a clean choice picker with options like "Yes, push into B1.8," "Run the production migration first," "Pause and review," or "Other."

---

## v1.5 ladder remaining

Concrete tasks the next session needs to finish before v1.5 ships:

1. **B1.8: Tier 2 picker in SKILL.md.** Add a section to `lofty-cowork-helper/SKILL.md` that triggers on "set up Tier 2," "set up post-showing feedback," "deploy the Worker," etc. Asks Joe (or any user running the skill) "Easy Mode (Claude does it for you) or Power User (you run the commands)?" and routes to the appropriate path documented in `references/workers_setup.md`. Easy Mode flow follows steps 1-12 of the Easy Mode walkthrough verbatim; Power User Mode flow points the user at the manual section and answers questions inline.

2. **Production migration.** Joe's path B commit. Sequence:
   - Use Jotform MCP `create_form` to rebuild Joe's production post-showing form following `assets/jotform_form_template.md` (with Joe's actual brand inputs: black + gold, Saling Homes logo URL).
   - Run `fetch(form_id)` and build `JOTFORM_FIELD_MAP` for the new form.
   - Copy the public skill's Worker code into `saling-automation/worker/jotform_to_lofty_worker.js`. Add Joe's specifics back (his existing Resend domain, his email signature, etc.) via the env-driven OWNER_* vars in `saling-automation/worker/wrangler.jotform.toml`. Joe's production keeps Resend (he's already paying), so don't disable it.
   - Push `JOTFORM_FIELD_MAP` to Joe's production wrangler config.
   - Update Joe's `.env` with the new `JOTFORM_FORM_ID`.
   - Deploy the new Worker to Joe's production.
   - Wire Jotform webhook from the new form to Joe's production Worker URL.
   - Submit one test entry. Confirm the Lofty note lands, the D1 row count goes up by one, and the recap email arrives via Resend at the email Joe submitted.
   - If everything looks right, archive Joe's old Jotform form (don't delete; keep for rollback).
   - **Historical D1 data stays put.** All existing rows key off `lead_id`, not field IDs. The `loved_tags` / `dealbreaker_tags` columns continue to hold the JSON arrays they always have. Future rows from the new form get the same treatment.

3. **v1.5 release.** Update `CHANGELOG.md` with a v1.5.0 entry covering everything in the "What got built" section above. Repackage `lofty-cowork-helper.skill` from the kit-creator skill at `/sessions/<your-session>/mnt/.claude/skills/skill-creator`. Commit the CHANGELOG + repackaged .skill, tag `v1.5.0`, push to origin with `--tags`.

That's it for v1.5. Stage C (the orchestration sub-skill) and v1.6/v1.7 (Tier 3) come later.

---

## Status snapshot (May 8, 2026, second session)

- v1.4.1 is the latest tagged release on GitHub. Public skill commit `f027a87` was on origin/main at the start of the second session. HANDOFF.md and v1.5 mid-build files were uncommitted at the time of writing this handoff; Joe will commit them shortly after.
- Phase 2 Stage A is COMPLETE through v1.4.1. Showing primitives, leads index, post-showing question pack, full read coverage of the API surface, Content-Type bug fix, find_client fallback for unsynced contacts.
- Phase 2 Stage B v1.5 (Tier 2: jotform-to-lofty Worker + D1 + optimized setup) is mid-build. All file artifacts are on disk in the public skill. The B1.8 picker, the production migration, and the release-tag pass are pending.
- Phase 2 Stage B v1.6 (Tier 3 SMS Worker) and v1.7 (Tier 3 polish: leads-index, possibly short-links) are not started. They sit behind v1.5 by design (see locked decision #9 below).
- Phase 2 Stage C (`schedule-showing` orchestration sub-skill, Phase 2 onboarding in Easy Mode) not started.

If you're a new Claude session: do NOT redesign Phase 2 from first principles. The reference implementation is `~/Code/saling-automation/`. Phase 2 of the public skill is a port + strip + parameterize, not a fresh design. The TIERING decision (#9 below) controls WHICH pieces port and in what order; it does not change the underlying architecture.

---

## What this project is

A Claude Cowork skill that connects Claude Desktop to the Lofty CRM for real estate agents and VAs. Open source under MIT. Owned by Joe Saling at Saling Homes at eXp Realty in Portland, Oregon.

GitHub repo: `github.com/Joe-exprlty/lofty-cowork-skill`. Public web page (Easy Mode walkthrough) at `joe-exprlty.github.io/lofty-cowork-skill`.

---

## The PRODUCTION REFERENCE: `saling-automation`

Joe runs a private repo at `/Users/joesaling/Code/saling-automation/` containing the COMPLETE, BATTLE-TESTED implementation of everything Phase 2 needs. The folder is mounted; if it isn't in your session, request it via `mcp__cowork__request_cowork_directory`.

Phase 2 of the public skill is the work of porting that production code into the public kit, with all Joe-specifics replaced by template placeholders. Joe explicitly told me: "You can use as much of my stuff as you need. I do not want my profile or any of my project in this skill though. I want it to be pure template."

What lives in `saling-automation` that's the source of truth:

- `scripts/lofty_api.py` (~900+ lines): showing primitives, find_client, find_listing_by_address, build_jotform_url, shorten_url, enqueue_showing_sms, list_pending_showings, cancel_showing, get_buyer_preferences, leads-index reader.
- `worker/jotform_to_lofty_worker.js`: receives JotForm submissions, writes to Lofty + Resend recap email + D1 `showing_feedback` row. Currently still alias-based; will be replaced by the new field-ID-based code from the public skill at production migration time.
- `worker/showing_sms_worker.js`: per-showing Durable Object alarms (no cron). 162ms precision validated in production. Requires Workers Paid plan ($5/mo).
- `worker/short_links_worker.js`: branded short-link redirector backed by KV.
- `worker/leads_index_worker.js`: webhook-list-2 fed leads index. KV-backed.
- `worker/migrations/001_showing_feedback.sql`: D1 schema. Already generic; ports verbatim. The public skill copy is byte-identical.
- `worker/wrangler.toml` and `worker/wrangler.jotform.toml`: deploy configs.
- `.claude/skills/schedule-showing/SKILL.md`: orchestration skill that drives multi-stop showing scheduling end-to-end. Port verbatim, strip Joe-specifics. Pinned for v1.7 or later.
- `.claude/CLAUDE.md`: lean knowledge base structure.
- `docs/architecture.md`, `docs/api-reference.md`, `docs/lofty-quirks.md`, `docs/local-leads-index.md`, `docs/phase2-feedback-db-deploy.md`.

What you must NOT carry into the public skill:

- `joe-2c5.workers.dev` subdomain (replace with `<your-subdomain>` or env-driven).
- `sellingpdxhomes.com`, `sellingpdxhomes`, `Joe Saling`, `Joe`, `joe@sellingpdxhomes.com`, `503-910-7364`. Anywhere they appear.
- `Saling Homes`, `eXp Realty` brand strings.
- Any API key value: `LOFTY_API_KEY`, `RESEND_API_KEY`, `PREFERENCES_API_KEY`, `LEADS_INDEX_EXPORT_API_KEY`. Configs use placeholders.
- `data/leads_index.json` (git-ignored anyway).
- Joe's Cloudflare account ID `22c50f7ac3f85d789dfec570642ae9af`.
- Joe's production D1 database id `2d6dd086-c086-457c-a03e-11500da56f08`.

The QUESTION CONTENT in the post-showing form (the actual prompt wording, the curated `loved_tags` and `dealbreaker_tags` starter lists, the rationale for why "Flood zone" is intentionally excluded from dealbreakers) IS portable; Joe explicitly opted into sharing those because they're general post-showing wisdom. They live in `lofty-cowork-helper/assets/post_showing_questions.yaml` already.

---

## Phase 2 LOCKED DECISIONS

Decided across the May 7 and two May 8 design sessions. Do not revisit without strong reason.

1. **Public skill = pure template.** No Joe-specifics anywhere in the kit. Recipients fork, fill in their own values, ship.
2. **Phase 2 design = port from `saling-automation`, not redesign.** Strip Joe-specifics, parameterize, add the public-skill Easy Mode walkthrough on top.
3. **MCPs are the easy path for everyone.** Cloudflare MCP for D1 / KV / Worker inspection. Jotform MCP for form creation, submissions, webhook wire-up. Wrangler is reserved for Worker code deploys and `wrangler secret put`.
4. **Recap email: Resend optional, Lofty fallback as the DEFAULT.** Lofty's `POST /v1.0/message/email/send` is the recap path on a fresh install. Resend is opt-in for users who want better deliverability and want the recap to come from their own domain. Tier 2 install needs ZERO new accounts beyond Cloudflare and Jotform. **Implemented in code as of May 8 second session.**
5. **Leads index: file fallback first, Worker optional.** v1.4.1's live-API fallback in `find_client` makes the leads-index Worker much less load-bearing. The file fallback is the default; the Worker is a Tier 3 polish item.
6. **Calendar provider: Google Calendar at v1.** Four-provider router parked as a "future feature for clients who want options."
7. **Hosting model: self-hosted at v1.** Each agent deploys their own Workers + D1.
8. **Twilio is OUT for v1.** Lofty's SMS is reliable enough for the showing reminders.
9. **Tiered rollout, not "all four Workers in v1.5".** v1.5 = Tier 2 (jotform-to-lofty Worker + D1). v1.6 = Tier 3 SMS Worker. v1.7 = Tier 3 polish.
10. **Workers Paid plan is ONLY for Tier 3 SMS.** $5/mo Cloudflare Workers Paid is required for Durable Objects in the showing-sms Worker. Every other Worker runs on the free tier.
11. **Short-links Worker is a candidate for cut.** Will revisit at v1.7 design.
12. **Branding step before form creation (NEW, May 8 second session).** When Easy Mode builds the Jotform form via MCP, it MUST first ask the user for brand colors (text + accent) and an optional logo (file path or URL). Render the YAML's `header_html` with those colors substituted in, prepend an `<img>` tag if a logo URL was provided, and follow up with `edit_form` to push matching theme colors. Joe's production form is black + gold with the Saling Homes logo; that branding is what makes the form feel like part of the agent's business rather than generic. Documented in `assets/jotform_form_template.md` and step 2 of `references/workers_setup.md` Easy Mode walkthrough.
13. **Form-import path = Path B, one codebase (NEW, May 8 second session).** The new field-ID-based Worker code in the public skill is the same code that will run in Joe's production after the production migration. Joe's existing Jotform form will be rebuilt to match the field-ID scheme. Historical D1 data is preserved (keys off `lead_id`).

---

## Stage status

### Stage A: COMPLETE through v1.4.1.
### Stage B v1.5: in progress.

B1.1-B1.4 (read all the production source files) DONE.
B1.5 (port Worker, strip Joe-specifics, write templated wrangler config) DONE.
B1.6 (write workers_setup.md with Easy + Power User paths) DONE.
B1.7 (five Tier 2 optimizations) DONE in code + runbook. The five optimizations:
  1. Build the Jotform form programmatically. DONE; see `assets/jotform_form_template.md` for the runtime procedure and `assets/post_showing_questions.yaml` for the parameterized header_html.
  2. Drop Resend as a setup requirement; Lofty fallback. DONE in Worker code.
  3. Cloudflare MCP for D1, wrangler only for Worker code. DONE in runbook.
  4. Auto-generate `PREFERENCES_API_KEY`. DONE in runbook (silent generation step).
  5. Auto-wire Jotform webhook. DONE in runbook (`edit_form` natural-language call).

B1.8 (Tier 2 picker in SKILL.md) PENDING. Next task.
Production migration PENDING. Runs after B1.8.
v1.5 release tag PENDING. Runs after production migration.

### Stage B v1.6: NOT STARTED.

The Tier 3 SMS Worker (showing-sms with Durable Object alarms). Requires Workers Paid plan. Stripped equivalents of `saling-automation/worker/showing_sms_worker.js` and `wrangler.toml`.

**v1.6 also adds: template-form-clone path for the post-showing form (NEW, May 9 session).** The v1.5 `create_form` natural-language approach in `assets/jotform_form_template.md` ships in v1.5 and works, but produces Classic Forms with mediocre visual polish. The Jotform create_form agent (a) defaults to Classic Form layout instead of Card Form, (b) auto-renames hidden fields to lowercase even when the prompt asks for camelCase, (c) does not reliably apply theme colors, fonts, or button styling, and (d) sometimes drops questions on initial create_form so a follow-up edit_form pass is required. v1.6 should switch Easy Mode to a "clone this Jotform template" flow: Joe publishes a polished Card Form template (Saling-specifics scrubbed) under his Jotform account, the kit's Easy Mode walkthrough points users at a `https://www.jotform.com/use-template/<template_id>` URL, the user clicks once to clone it into their account, the kit reads the cloned form's id and derives `JOTFORM_FIELD_MAP` from it (qids are stable across clones). Eliminates the create_form fragility, locks in the Card layout, and gives every install Joe's polished baseline on day 1. The v1.5 create_form path becomes a documented fallback for users without a Jotform account willing to clone shared templates. Implementation tasks: scrub Saling-specifics from form 261040658235049, mark it as a Jotform Public Template, document the clone flow in `references/workers_setup.md`, simplify the branding step to "optional theme override" since the template ships pre-themed, update the v1.5 `assets/jotform_form_template.md` to be the fallback procedure not the primary one. Reference the May 8-9 production migration history for why this matters.

### Stage B v1.7: NOT STARTED.

Tier 3 polish: leads-index Worker (free tier, optional once v1.4.1 fallback is in place) and short-links Worker (free tier, may be cut entirely per locked decision #11).

### Stage C: NOT STARTED. Target v1.7 or later.

Port `.claude/skills/schedule-showing/SKILL.md` from `saling-automation`. Add Phase 2 onboarding step to the public skill's Easy Mode setup.

---

## Where everything lives (current state)

- **Skill source:** `/Users/joesaling/Code/lofty-cowork-skill/lofty-cowork-helper/`
- **New v1.5 files** (added in May 8 second session, all under `lofty-cowork-helper/`):
  - `workers/jotform_to_lofty_worker.js`
  - `workers/migrations/001_showing_feedback.sql`
  - `workers/wrangler.jotform.toml`
  - `references/workers_setup.md`
  - `assets/jotform_form_template.md`
  - `scripts/test_worker_parsers.mjs`
- **Updated v1.5 files:**
  - `assets/post_showing_questions.yaml` (header_html parameterized with brand tokens)
  - `assets/env-template` (added OWNER_WEBSITE; reframed RESEND_API_KEY as optional)
- **Packaged skill file:** `/Users/joesaling/Code/lofty-cowork-skill/lofty-cowork-helper.skill` (v1.4.1, ~90 KB, gitignored). Will be repackaged at v1.5 release.
- **Production reference:** `/Users/joesaling/Code/saling-automation/` (mounted; grant via `mcp__cowork__request_cowork_directory` if missing).
- **Public web page source:** `docs/index.html`
- **Recipient-facing docs:** `INSTALL.md`, `README.md`, `LICENSE`, `CHANGELOG.md`
- **Distributor docs:** `PACKAGING.md`
- **References:** `lofty-cowork-helper/references/{full-guide,quirks,workflows,extending,calendar_routing,workers_setup}.md`
- **Assets:** `lofty-cowork-helper/assets/{lofty_api.py,env-template,CLAUDE.md.template,ics_builder.py,post_showing_questions.yaml,jotform_form_template.md}`
- **Scripts:** `lofty-cowork-helper/scripts/{setup_check.py,refresh_leads_index.py,test_v1_2_methods.py,test_v1_3_methods.py,test_worker_parsers.mjs}`
- **Repackage command:** `cd /sessions/<your-session>/mnt/.claude/skills/skill-creator && python3 -m scripts.package_skill /sessions/<your-session>/mnt/lofty-cowork-skill/lofty-cowork-helper /sessions/<your-session>/mnt/lofty-cowork-skill`

`calendar_routing.md` and `ics_builder.py` exist but are demoted per locked decision #6.

---

## Outstanding decisions

1. **`v1.4.1` git tag.** Commit `f027a87` was on origin/main but no tag was created at v1.4.1 ship time. If Joe wants release-tag parity with v1.4.0, tag it before v1.5. Otherwise skip.
2. **Cut the short-links Worker from the public skill?** Locked decision #11 flagged this for investigation at v1.7. Joe to confirm at that time.
3. **Slide deck for Joe's realtor talk.** Joe was building a 12-slide deck in Claude Design at `claude.ai/design`, project name "Lofty + Claude for Realtors - 25 min Talk." Verify state separately from engineering work.
4. **Lofty API key rotation.** Hold until Phase 2 is fully deployed so it's a single rotation pass.

The form-import migration path question is RESOLVED (Path B, one codebase). The branding-before-form-creation question is RESOLVED (locked decision #12).

---

## MCP connectors confirmed available

- **Jotform MCP:** `mcp__fb185796-3f32-4d0b-960a-fb8d0869ca9c__*` (9 tools). Notable: `search`, `create_form`, `edit_form`, `display_form`, `assign_form`, `fetch`, `list_submissions`, `create_submission`, `analyze_submissions`. **Important:** `create_form` and `edit_form` take a single natural-language `description` parameter; structured field IDs are not directly settable. Easy Mode strategy: pass detailed natural-language prompt, then call `fetch(form_id)` to introspect the actual qids the Jotform agent assigned, then build `JOTFORM_FIELD_MAP` from the fetch result. Documented in `assets/jotform_form_template.md`.
- **Cloudflare MCP:** `mcp__c55037a8-92bb-4dab-ab11-9e055ea57019__*`. Notable: `accounts_list`, `set_active_account`, `d1_database_create/query/get/delete`, `d1_databases_list`, `kv_namespace_*`, `workers_list/get_worker/get_worker_code` (READ-ONLY for Workers; deploy still needs wrangler), `r2_bucket_*`, `search_cloudflare_documentation`.
- **Google Calendar MCP, Gmail, Asana, Canva, Google Drive, Microsoft Learn:** also installed.

Loading deferred tool schemas in a new session: `ToolSearch` with `select:<tool_name>[,<tool_name>...]` for direct picks, or keyword search like `query: "cloudflare"` to bulk-load.

---

## Brand and voice rules

- **No em-dash characters anywhere.** Use commas, periods, or hyphens. Apply to ALL new content.
- **Forbidden words (Saling Homes brand only):** cozy, vibrant, amazing, incredible, mouthwatering, family-friendly, good schools, safe neighborhood.
- **Voice signature (Saling Homes brand only):** "Listening, educating, advocating."
- **Colors / fonts / logo / phone / email:** ONLY in `docs/index.html` (the GitHub Pages site, Saling Homes-branded by design).

---

## Data handling disclosure

Public-facing template wording for the kit's homepage, README, and INSTALL:

> When you ask Claude to look up, update, or summarize leads, the lead content Claude reads (names, contact info, notes, activity) is processed through Anthropic's models the same way any Claude conversation is processed. Your Lofty API key stays on your computer and is never sent to Anthropic.
>
> Before using this tool with real client data, confirm it fits your brokerage's data handling rules, your MLS rules, and what your clients reasonably expect. This skill is provided as is. Verify behavior in your own Lofty account before relying on it for client-facing work. Not affiliated with or endorsed by Lofty Inc. or Anthropic.

Phase 2 disclosure expansions per tier:

- v1.5 ship: lead data passes through Cloudflare (Worker + D1), Jotform (form submissions), and optionally Resend (only if the user enables it). Add these as named third parties.
- v1.6 ship: SMS feedback texts route through Lofty's SMS endpoint (already covered) but the Worker schedule queue runs on Cloudflare. No new third parties beyond v1.5.
- v1.7 ship: leads-index Worker reads webhook events from Lofty and stores them in Cloudflare KV. Same providers. If short-links Worker ships, the redirector domain becomes a new visible touchpoint for buyers.

---

## Joe's contact

Joe Saling, Saling Homes at eXp Realty, 503-910-7364, joe@sellingpdxhomes.com, www.sellingpdxhomes.com.

These details belong in HANDOFF.md and `docs/index.html` ONLY. Not in the public template.

---

## Recommended order for the next session

1. Read this HANDOFF.md (you're doing it now).
2. Verify the production reference is mounted and the public skill working tree is clean (silent checks per the QUICK START).
3. Run the parser smoke test to confirm the Worker still works: `node lofty-cowork-helper/scripts/test_worker_parsers.mjs`. Should print "All parser smoke tests passed."
4. Ask Joe whether to push into B1.8, run the production migration first, or pause (use AskUserQuestion).
5. After Joe answers, proceed accordingly. Likely path: B1.8 → production migration → v1.5 release.
6. When porting code into Joe's production: every Worker URL, every account ID, every secret value still applies. Use the Cloudflare MCP for read-only inspection during development; reserve `wrangler` for actual deploys and `wrangler secret put`.

Do NOT delete this HANDOFF.md until Phase 2 is finished and shipped. Joe wants it kept as the working brief.
