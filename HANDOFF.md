# Session Handoff: Phase 2

This file gets a new Claude Cowork session up to speed on the **Phase 2** build of the Lofty + Cowork skill project. Read this first, then explore the current files before doing anything.

---

## NEXT SESSION QUICK START

> Joe opened a new prompt and typed "Read Handoff.md and continue conversation." Follow this section to pick up exactly where we left off. Do NOT recap the prior session's work back to Joe; he was there. Get to the point.

**Where we left off (May 10, 2026):** v1.6.0 is shipped (tag `v1.6.0` on origin/main as of May 10). The release lands the template-clone path for Easy Mode Tier 2 setup. Joe published the polished public template at form id `261294238566162`, the docs walk users through Jotform's import-from-URL wizard (Workspace → Create → Form → Import Form → From a Web Page → paste `https://form.jotform.com/261294238566162` → Create Form), and the v1.5 `create_form` natural-language flow is now the documented fallback for users who cannot import shared templates. No Worker code changes; Tier 2 architecture and D1 schema are unchanged from v1.5.

The remaining v1.6 ladder item, the Tier 3 SMS Worker port, did not ship in this release. It is now pinned for v1.6.1 or v1.7 depending on whether Joe wants to bundle other Tier 3 work.

**Do these checks silently first (do NOT narrate them to Joe):**

1. Verify `~/Code/saling-automation/` is mounted via `mcp__cowork__request_cowork_directory`. If not, request it.
2. Run `git log --oneline -5` on `~/Code/lofty-cowork-skill`. Confirm `v1.6.0` tag is on the latest commit and the working tree is clean.
3. Run `node lofty-cowork-helper/scripts/test_worker_parsers.mjs`. Should print "All parser smoke tests passed."
4. Read the "v1.7 ladder" section below so you know what comes next.

**Then, as your FIRST user-facing message, ask Joe what to work on next:**

> v1.6 is shipped (tagged 2026-05-10, template-clone path live in Easy Mode). Three viable next directions: v1.6.1 / v1.7 Tier 3 SMS Worker port, Stage C (schedule-showing orchestration sub-skill), or a real end-to-end test of the v1.6 Easy Mode flow with a fresh Jotform account. Tier 3 SMS is the biggest user-visible payoff; Stage C streamlines your daily workflow; the e2e test catches any clone-flow papercuts before another agent hits them. Which way?

Use AskUserQuestion with options like "Push into Tier 3 SMS Worker (v1.7)," "Push into Stage C (schedule-showing sub-skill)," "End-to-end test v1.6 Easy Mode with a fresh account," or "Other."

---

## v1.6 SHIPPED (2026-05-10)

Tag `v1.6.0` on origin/main. What landed:

- Public Jotform template at form id `261294238566162` in Joe's Jotform account. Polished Card Form, all hidden fields cleared of defaults, header HTML uses Jotform substitution tokens, no agent-specific contact info anywhere. Imported into other accounts via Jotform's Workspace → Create → Form → Import Form → From a Web Page flow, pasting `https://form.jotform.com/261294238566162` as the source URL. "Prevent Cloning" is OFF on the form per maintainer responsibility.
- `lofty-cowork-helper/references/workers_setup.md`. Easy Mode walkthrough step 2 is now the template-import flow; the branding question is an optional theme override; total Easy Mode steps trimmed from 12 to 11. Power User Mode step 1 documents the import-from-URL flow as recommended with the from-scratch build as fallback.
- `lofty-cowork-helper/assets/jotform_form_template.md` re-headed and re-framed as the v1.5 fallback procedure.
- `lofty-cowork-helper/SKILL.md` B1.8 picker updated to reference template-clone in the Easy Mode summary; theme overrides flagged optional.
- `README.md` adds a Tier 2 template form section under Maintaining the skill, listing maintainer responsibilities (keep form Active, Prevent Cloning OFF, account Privacy clone setting OFF, qid layout stable, no agent-specifics).
- `CHANGELOG.md` entry for v1.6.0.

**Maintainer state on Joe's Jotform account:**
- Public template form: `261294238566162` (Card Form, scrubbed)
- Joe's production form (untouched by this release): `261040658235049`

The Tier 3 SMS Worker port from `saling-automation/worker/showing_sms_worker.js` did NOT ship in v1.6. It is the highest-priority remaining item for the next ladder.

---

## v1.5 SHIPPED (2026-05-09)

Tag `v1.5.0` on commit `b8374e3` on origin/main. What landed:

- `lofty-cowork-helper/workers/jotform_to_lofty_worker.js` ported from `saling-automation`. Joe-specifics replaced with env-driven `OWNER_*` vars. `JOTFORM_FIELD_MAP` env var routes submissions by Jotform qid when populated, falls back to alias matching. Resend is opt-in; if `RESEND_API_KEY` is unset the recap email goes through Lofty's `POST /v1.0/message/email/send` endpoint instead. May 9 bugfix: case-insensitive lookup for hidden field names (`propertyaddress`, `showingdate`, `propertystats`) since Jotform's create_form agent normalizes names to lowercase.
- `lofty-cowork-helper/workers/migrations/001_showing_feedback.sql` ported verbatim.
- `lofty-cowork-helper/workers/wrangler.jotform.toml` templated.
- `lofty-cowork-helper/references/workers_setup.md` is the v1.5 deploy runbook. Easy Mode + Power User Mode walkthroughs. May 9 update: Node prereq guidance (Homebrew / .pkg / Windows / Linux) and `npx wrangler` recommendation.
- `lofty-cowork-helper/assets/jotform_form_template.md` for the create_form path.
- `lofty-cowork-helper/assets/post_showing_questions.yaml` parameterized with `{{ACCENT_COLOR}}`, `{{TEXT_COLOR}}`, `{{LOGO_HTML}}` tokens.
- `lofty-cowork-helper/assets/env-template` updated. Optional `OWNER_WEBSITE`. Resend reframed as optional.
- `lofty-cowork-helper/scripts/test_worker_parsers.mjs` smoke test. 32 assertions, all green.
- B1.8 Tier 2 picker section in `lofty-cowork-helper/SKILL.md`. Triggers on "set up Tier 2," "deploy the Worker," etc. Routes Easy Mode vs Power User Mode, runs silent prereq checks (LOFTY_API_KEY, CLOUDFLARE_API_TOKEN, Node, wrangler-or-npx, Jotform account, Cloudflare MCP, Jotform MCP).

**Production state on Joe's Mac:**
- Form ID: `261040658235049` (existing polished Card Form, with `memory_notes` added as qid 51 on May 9)
- Worker: deployed at `https://jotform-to-lofty.joe-2c5.workers.dev`, version `00913c11-9b54-4b87-97b6-479da1bced7a` or later
- D1: `2d6dd086-c086-457c-a03e-11500da56f08`, two rows from May 9 smoke tests
- `JOTFORM_FIELD_MAP`: `{"40":"first_reaction","41":"daily_life_fit","42":"neighborhood_rating","43":"condition_rating","44":"value_rating","45":"short_list","46":"standout_text","49":"loved_tags","50":"dealbreaker_tags","51":"memory_notes"}`
- Obsolete new form `261280371447052` created during the session is dormant (webhook removed); Joe can delete it whenever.

---

## v1.7 ladder

Three viable next directions. They are independently scoped; pick whichever has the highest leverage for the moment.

1. **Tier 3 SMS Worker (highest user-visible payoff).** Port `saling-automation/worker/showing_sms_worker.js` (Durable Object alarms, no cron, 162ms alarm precision validated in production) into `lofty-cowork-helper/workers/showing_sms_worker.js`. Strip Joe-specifics. Templated `wrangler.toml` template under `workers/wrangler.showing-sms.toml`. Requires Cloudflare Workers Paid plan ($5/mo) for Durable Objects, so the picker in `SKILL.md` should add a Workers Paid prereq check before routing to Easy Mode. Update `references/workers_setup.md` with a "Tier 3 setup" section parallel to Tier 2.

2. **Stage C: schedule-showing orchestration sub-skill.** Port `.claude/skills/schedule-showing/SKILL.md` from `saling-automation` into `lofty-cowork-helper/`. Strip Joe-specifics. Drives multi-stop showing scheduling end-to-end (resolve client, parse times, prepare_showing per stop, calendar invite, note, SMS verification). Reduces a 10-minute multi-step workflow to a single chat sentence. Adds a Phase 2 onboarding step to the public skill's Easy Mode setup.

3. **End-to-end smoke of v1.6 Easy Mode with a fresh Jotform account.** Real-world test of the import-from-URL flow with a brand new Jotform account that has never seen the template. Confirms (a) the import wizard accepts `https://form.jotform.com/261294238566162` without an Unauthorized error, (b) the cloned form preserves the qid 40-51 layout the canonical `JOTFORM_FIELD_MAP` assumes, (c) the optional theme override edit_form call still works, (d) the rest of Easy Mode runs unchanged through to a green smoke test. Cheapest direction; surfaces any v1.6 papercuts before strangers hit them.

Recommend (3) first since it locks in the v1.6 release, then (1) since Tier 3 is the biggest functional jump remaining.

---

## Status snapshot (May 10, 2026)

- **v1.6.0 SHIPPED.** Tag on origin/main. Template-clone path live. CHANGELOG updated. Public template form `261294238566162` is published in Joe's Jotform account with Prevent Cloning OFF.
- Phase 2 Stage A is COMPLETE through v1.4.1. Showing primitives, leads index, post-showing question pack, full read coverage of the API surface, Content-Type bug fix, find_client fallback for unsynced contacts.
- Phase 2 Stage B v1.5 is COMPLETE. Tier 2 jotform-to-lofty Worker + D1 + Easy Mode picker shipped. Joe's production is on it.
- Phase 2 Stage B v1.6 is COMPLETE for the template-clone path. Tier 3 SMS Worker portion did NOT ship in v1.6; it remains the headline item for the next ladder.
- Phase 2 Stage B v1.7 is NOT STARTED. Tier 3 SMS Worker (top priority) plus Tier 3 polish (leads-index Worker free tier, optional once v1.4.1 fallback is in place; short-links Worker free tier, may be cut entirely per locked decision #11).
- Phase 2 Stage C (`schedule-showing` orchestration sub-skill, Phase 2 onboarding in Easy Mode) NOT STARTED.

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
9. **Tiered rollout, not "all four Workers in v1.5".** v1.5 = Tier 2 (jotform-to-lofty Worker + D1). v1.6 = template-clone path for Tier 2 Easy Mode (shipped 2026-05-10). v1.7 = Tier 3 SMS Worker. v1.7.x or later = Tier 3 polish.
10. **Workers Paid plan is ONLY for Tier 3 SMS.** $5/mo Cloudflare Workers Paid is required for Durable Objects in the showing-sms Worker. Every other Worker runs on the free tier.
11. **Short-links Worker is a candidate for cut.** Will revisit at v1.7 design.
12. **Branding step before form creation (NEW, May 8 second session).** When Easy Mode builds the Jotform form via MCP, it MUST first ask the user for brand colors (text + accent) and an optional logo (file path or URL). Render the YAML's `header_html` with those colors substituted in, prepend an `<img>` tag if a logo URL was provided, and follow up with `edit_form` to push matching theme colors. Joe's production form is black + gold with the Saling Homes logo; that branding is what makes the form feel like part of the agent's business rather than generic. Documented in `assets/jotform_form_template.md` and step 2 of `references/workers_setup.md` Easy Mode walkthrough.
13. **Form-import path = Path B, one codebase (NEW, May 8 second session).** The new field-ID-based Worker code in the public skill is the same code that will run in Joe's production after the production migration. Joe's existing Jotform form will be rebuilt to match the field-ID scheme. Historical D1 data is preserved (keys off `lead_id`).

---

## Stage status

### Stage A: COMPLETE through v1.4.1.
### Stage B v1.6: COMPLETE (shipped 2026-05-10 as v1.6.0) for the template-clone path. Tier 3 SMS Worker NOT included; remains pinned for v1.7.

Template-clone path landed. Public template form 261294238566162 in Joe's Jotform account, scrubbed, Prevent Cloning OFF. Easy Mode and Power User Mode walkthroughs in `references/workers_setup.md` updated. `assets/jotform_form_template.md` re-headed as the v1.5 fallback. `SKILL.md` B1.8 picker updated. `README.md` adds maintainer responsibilities for the template form.

### Stage B v1.5: COMPLETE (shipped 2026-05-09 as v1.5.0).

B1.1-B1.4 (read all the production source files) DONE.
B1.5 (port Worker, strip Joe-specifics, write templated wrangler config) DONE.
B1.6 (write workers_setup.md with Easy + Power User paths) DONE. Node prereq added in May 9 patch.
B1.7 (five Tier 2 optimizations) DONE.
B1.8 (Tier 2 picker in SKILL.md) DONE 2026-05-09.
Production migration DONE 2026-05-09. Joe's production is on the v1.5 Worker pointed at his existing form 261040658235049 (with memory_notes added as qid 51).
v1.5 release tag DONE 2026-05-09 (tag `v1.5.0` on commit `b8374e3` on origin/main).

### Stage B v1.7: NOT STARTED.

Top priority: Tier 3 SMS Worker (`showing-sms` with Durable Object alarms). Requires Cloudflare Workers Paid plan ($5/mo). Port `saling-automation/worker/showing_sms_worker.js` and `worker/wrangler.toml`, strip Joe-specifics, parameterize, add a "Tier 3 setup" section parallel to Tier 2 in `references/workers_setup.md`, add a Workers Paid prereq check to the Tier 3 picker in `SKILL.md`.

Tier 3 polish (lower priority): leads-index Worker (free tier, optional once v1.4.1 fallback is in place) and short-links Worker (free tier, may be cut entirely per locked decision #11).

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
