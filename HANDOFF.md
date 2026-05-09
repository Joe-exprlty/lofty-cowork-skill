# Session Handoff: Phase 2

This file gets a new Claude Cowork session up to speed on the **Phase 2** build of the Lofty + Cowork skill project. Read this first, then explore the current files before doing anything.

---

## NEXT SESSION QUICK START

> Joe opened a new prompt and typed "Read Handoff.md and continue conversation." Follow this section to pick up exactly where we left off. Do NOT recap the prior session's work back to Joe; he was there. Get to the point.

**Where we left off (May 8, 2026):** v1.4.1 shipped to GitHub (commit `f027a87` on origin/main). The find_client fallback is live in both the public skill and the production reference. We agreed Phase 2 Stage B is re-sliced into tiers: v1.5 = Tier 2 (the `jotform-to-lofty` Worker plus D1), v1.6 = Tier 3 SMS, v1.7 = Tier 3 polish. We also locked the five Tier 2 optimizations (see "Tier 2 (v1.5) plan" below). One decision is still open from the May 8 conversation: the form-import migration path. That is the gating question for v1.5.

**Do these checks silently first (do NOT narrate them to Joe):**

1. Verify `~/Code/saling-automation/` is mounted via `mcp__cowork__request_cowork_directory`. If not, request it.
2. Run `git log --oneline -3` on `~/Code/lofty-cowork-skill`. Confirm commit `f027a87 v1.4.1: find_client fallback for unsynced contacts` is at the top and the working tree is clean. If HANDOFF.md is uncommitted, that is fine and expected; Joe planned to land it with v1.5 prep.
3. Read these v1.5-relevant production files end-to-end (skim if you read them in a recent prior session, but do not skip):
   - `saling-automation/worker/jotform_to_lofty_worker.js`
   - `saling-automation/worker/migrations/001_showing_feedback.sql`
   - `saling-automation/worker/wrangler.jotform.toml`
   - `saling-automation/docs/phase2-feedback-db-deploy.md` if it exists (Joe-side runbook to port)
4. Skim the "Phase 2 LOCKED DECISIONS," "Tier 2 (v1.5) plan," and "Stage B status" sections of THIS file so you have the constraints fresh.

**Then, as your FIRST user-facing message, ask Joe this exact question** (no preamble beyond "Picking up where we left off." or similar one-liner; no recap of v1.4.1):

> Picking up at v1.5 / Tier 2. One open decision before I touch code: for the form-import optimization (the public skill's Easy Mode walkthrough creates a Jotform form programmatically from `assets/post_showing_questions.yaml`), the public Worker should key off Jotform field IDs instead of guessing aliases like your production Worker does today. That gives us two paths.
>
> **Path A: separate codebases.** Ship a new field-ID-based Worker for the public template only. Your production Worker stays alias-based and unchanged. The two implementations diverge.
>
> **Path B: one codebase.** Migrate your production Jotform form to match the new field-ID scheme, update your production Worker to match, and ship the same Worker code in the public skill. One implementation across both repos.
>
> Path A is faster to ship but creates two things to maintain. Path B is more disruptive in the short term but keeps your stack and the public skill in lockstep. Which one?

Use the AskUserQuestion tool for this so Joe gets a clean choice picker. Wait for his answer.

**After Joe answers**, proceed to v1.5 B1.5 (port the Worker, strip Joe-specifics, write the v1.5 setup runbook). The full B1.x task ladder is in the "Stage B status" section below. The five Tier 2 optimizations are locked and listed in the "Tier 2 (v1.5) plan" section. Setup-time goal: a fresh Tier 2 install runs in roughly five minutes.

---

**Status as of May 8, 2026:**

- **v1.4.1 is shipped to GitHub** (`lofty-cowork-helper.skill`, ~90 KB at the kit root, gitignored). Public skill commit `f027a87` is on origin/main. The matching production patch is on `saling-automation` origin/main (commit `9217d0c`). The `v1.4.1` git tag was NOT created on the public repo (commit landed via GitHub Desktop without the tag step). If Joe wants tagged-release parity with v1.4.0, tag commit `f027a87` as `v1.4.1` and push tags. Otherwise the working tree is clean.
- Phase 2 Stage A is COMPLETE through v1.4.1: showing primitives ported, leads index, post-showing question pack, full read-coverage of the API surface, Content-Type bug fix, and the v1.4.1 find_client fallback that closes the new-contact gap (live API scan via scrollId pagination when the local index misses).
- Phase 2 Stage B (the Cloudflare Workers) NOT started, AND has been re-sliced into tiers (see "Phase 2 LOCKED DECISIONS" and "Tier 2 (v1.5) plan" below). The handoff's original "all four Workers in v1.5" plan is OBSOLETE.
- Phase 2 Stage C (`schedule-showing` orchestration sub-skill, Phase 2 onboarding in Easy Mode) NOT started.

If you're a new Claude session: do NOT redesign Phase 2 from first principles. The reference implementation is `~/Code/saling-automation/`. Phase 2 of the public skill is a port + strip + parameterize, not a fresh design. The TIERING decision (below) shapes WHICH pieces port and in what order; it does not change the underlying architecture.

---

## What this project is

A Claude Cowork skill that connects Claude Desktop to the Lofty CRM for real estate agents and VAs. Open source under MIT. Owned by Joe Saling at Saling Homes at eXp Realty in Portland, Oregon.

GitHub repo: `github.com/Joe-exprlty/lofty-cowork-skill`. Public web page (Easy Mode walkthrough) at `joe-exprlty.github.io/lofty-cowork-skill`.

---

## The PRODUCTION REFERENCE: `saling-automation`

This is the most important section in this handoff. Read it carefully.

Joe runs a private repo at `/Users/joesaling/Code/saling-automation/` that contains the COMPLETE, BATTLE-TESTED implementation of everything Phase 2 needs to ship. The folder is mounted in this session. If it isn't mounted in your session, request it via `mcp__cowork__request_cowork_directory` with that path.

Phase 2 of the public skill is the work of porting that production code into the public kit, with all Joe-specifics replaced by template placeholders. Joe explicitly told me: "You can use as much of my stuff as you need. I do not want my profile or any of my project in this skill though. I want it to be pure template."

What lives in `saling-automation` that you should treat as the source of truth:

- `scripts/lofty_api.py` (~900+ lines): contains `prepare_showing`, `find_listing_by_address`, `find_client`, `build_jotform_url`, `shorten_url`, `enqueue_showing_sms`, `list_pending_showings`, `cancel_showing`, `get_buyer_preferences`, the leads-index reader. All the showing primitives.
- `worker/jotform_to_lofty_worker.js`: receives JotForm submissions, writes to Lofty + Resend recap email + D1 `showing_feedback` row. Exposes `/preferences/:leadId` (Bearer-auth) and `/` health.
- `worker/showing_sms_worker.js`: per-showing Durable Object alarms (no cron). 162ms precision validated in production. Requires Workers Paid plan ($5/mo).
- `worker/short_links_worker.js`: branded short-link redirector backed by KV.
- `worker/leads_index_worker.js`: webhook-list-2 fed leads index. KV-backed. Exposes `/export` (Bearer-auth) and `/stats`.
- `worker/migrations/001_showing_feedback.sql`: D1 schema. 6 numeric ratings (1-5), 2 free-text columns, 2 JSON-array tag columns, 1 reserved `claude_tags` column, plus metadata. Already generic.
- `worker/wrangler.toml` and `worker/wrangler.jotform.toml`: deploy configs with secrets and bindings.
- `.claude/skills/schedule-showing/SKILL.md`: orchestration skill that drives multi-stop showing scheduling end-to-end. Port this verbatim, strip Joe-specifics.
- `.claude/CLAUDE.md`: lean knowledge base structure to mirror in the public template.
- `docs/architecture.md`: what's running and where.
- `docs/api-reference.md`: full Python client method list.
- `docs/lofty-quirks.md`: full quirks list (the 14 most common, plus the three new body-shape quirks discovered in this session, which are already in the public skill's `references/quirks.md`).
- `docs/local-leads-index.md`: leads-index Worker vs file design.
- `docs/phase2-feedback-db-deploy.md`: the runbook for setting up D1 + the jotform-to-lofty Worker. Port this, parameterize, replace `wrangler` shell commands with Cloudflare MCP calls where the MCP supports it.

What you must NOT carry into the public skill:

- `joe-2c5.workers.dev` subdomain anywhere. Replace with `<your-subdomain>`.
- `sellingpdxhomes.com`, `sellingpdxhomes`, `Joe Saling`, `Joe`, `joe@sellingpdxhomes.com`, `503-910-7364`. Anywhere they appear in code, configs, or docs, replace with placeholders.
- `Saling Homes`, `eXp Realty` brand strings.
- `LOFTY_API_KEY` value, `RESEND_API_KEY` value, `PREFERENCES_API_KEY` value, `LEADS_INDEX_EXPORT_API_KEY` value. Obvious. Configs use `<set-via-wrangler-secret-put>` placeholders.
- The `data/leads_index.json` file itself (it's git-ignored anyway and contains real client PII).
- Joe's Cloudflare account ID (`22c50f7ac3f85d789dfec570642ae9af`).

The QUESTION CONTENT in the post-showing form (the actual prompt wording, the curated `loved_tags` and `dealbreaker_tags` starter lists, the rationale for why "Flood zone" is intentionally excluded from dealbreakers) IS portable. Joe explicitly opted into sharing those because they're general post-showing wisdom. They live in the public skill's `assets/post_showing_questions.yaml` already.

---

## What v1.4.x ships (current state, May 8, 2026 - SHIPPED TO GITHUB)

v1.4.1 is the latest tagged release path. The kit is at the kit root as `lofty-cowork-helper.skill` (~90 KB, gitignored). The CHANGELOG documents v1.2.0, v1.3.0, v1.4.0, and v1.4.1 as separate logical releases.

What v1.4.0 shipped (Phase 2 Stage A complete):

- Easy Mode + Power User Mode setup (Phase 1.5)
- Branded web page at `docs/index.html`
- 22 new methods plus the showing primitives (full read coverage of the Lofty REST surface)
- Content-Type fix in `_request` that unblocks every DELETE in the client (resolves a silent bug that affected production too)
- Leads index (file or Worker fallback) with rich normalizer (36 fields including buyer/seller intent, DNC flags, lead's `leadPropertyList`)
- Showing primitives: `prepare_showing`, `find_listing_by_address`, `cancel_showing`, `list_pending_showings`, `get_buyer_preferences`, plus sub-helpers
- Unified timeline read via `get_system_logs`, plus per-channel comm history (`get_call_history`, `get_email_history`, `get_text_history`)
- Schema introspection: `get_custom_fields`, `get_lead_ponds`, `get_organization`, `get_members`
- Task lifecycle: `get_tasks`, `update_task`, `complete_task`, `uncomplete_task`, `delete_task`, `get_available_meeting_slots`
- Note lifecycle: `update_note`, `delete_note`
- Webhook lifecycle: `create_webhook`, `delete_webhook`
- 28 documented quirks (the original 14 plus 14 added across v1.2-v1.4)
- All forbidden em-dash characters removed
- All known Joe-specifics scrubbed from files that ship in the bundle (verified May 8, 2026)

What v1.4.1 added on top of v1.4.0 (focused fix release):

- `find_client` fallback to a live `/v1.0/leads` scan when the local index returns no match. Closes the new-contact gap: a contact created in Lofty seconds before the call now lands in `find_client` results without waiting on the leads-index Worker's 1-5 minute webhook delivery SLA. Verified live against a fresh test contact (Robin Hood) on May 8, 2026.
- `_search_recent_leads(max_pages=3, page_size=25)` helper using scrollId-cursor pagination.
- New `fallback_pages` parameter on `find_client` (default 3, set to 0 to revert to v1.4.0 behavior).
- Additive `"source"` key on `find_client` return shape: `"index"`, `"api"`, or `"index+api"`. Backward compatible.
- Quirk #29: `/v1.0/leads` `page` parameter is silently ignored. scrollId is the only working pagination on that endpoint.
- Same patch mirrored into `saling-automation/scripts/lofty_api.py` so Joe's daily workflow benefits immediately.

What v1.4.x does NOT yet ship (Phase 2 Stages B and C, now re-sliced into tiers):

- Tier 2: the `jotform-to-lofty` Worker plus D1 migration plus optimized setup runbook (target v1.5.0).
- Tier 3 SMS: the `showing-sms` Worker with Durable Object alarms (target v1.6.0). Requires Cloudflare Workers Paid plan ($5/mo).
- Tier 3 polish: the `leads-index` Worker (free tier, optional once the v1.4.1 fallback is in place) and the `short-links` Worker (free tier, may be cut entirely from the public skill, see locked decision #11). Target v1.7.0.
- The `schedule-showing` orchestration sub-skill (Stage C, target v1.7.0 or later).
- Phase 2 onboarding step in Easy Mode setup (Stage C).

---

## Phase 2 LOCKED DECISIONS

Decided across the May 7 and May 8 design sessions, do not revisit without strong reason:

1. **Public skill = pure template.** No Joe-specifics anywhere in the kit. Recipients fork, fill in their own values, ship. This is non-negotiable.
2. **Phase 2 design = port from `saling-automation`, not redesign.** The production architecture works. Strip Joe-specifics, parameterize, add the public-skill's Easy Mode walkthrough on top. Tiering (decision #9) controls WHICH pieces port and in what order; it does not change the underlying architecture.
3. **MCPs are the easy path for everyone.** Cloudflare MCP for D1 / KV / Worker inspection. JotForm MCP for form creation, submissions, analysis. Reserve `wrangler` CLI for the parts the MCP can't do (Worker code deploys, secret push). MCP-first is for both setup walkthroughs AND for how WE build the public skill.
4. **Recap email: optional with Lofty fallback as the DEFAULT.** Lofty's `send_email` is the recap path on a fresh install. Resend is opt-in for users who want better deliverability. This means a Tier 2 install needs ZERO new accounts beyond Cloudflare and JotForm. Reverses the original plan, locked in the May 8 cost-tier conversation.
5. **Leads index: file fallback first, Worker optional.** v1.4.1's live-API fallback in `find_client` makes the leads-index Worker much less load-bearing. The file fallback is the default; the Worker is a Tier 3 polish item. This is a softening of the original locked decision and reflects the reality that v1.4.1 closes the new-contact gap without any Worker.
6. **Calendar provider: Google Calendar at v1.** The four-provider router (`references/calendar_routing.md`, `assets/ics_builder.py`) is parked as a "future feature for clients who want options." Production uses Google exclusively and that is what ships first. Keep the router files; demote them in SKILL.md to "if you want alternatives."
7. **Hosting model: self-hosted at v1.** Each agent deploys their own Workers + D1. Joe-hosted-shared is a possible future "premium tier" service for paying coaching clients but is NOT how the public open-source skill ships. Self-host is the simpler ownership story for v1.
8. **Twilio is OUT for v1.** Lofty's SMS is reliable enough for the showing reminders. Twilio adds another account, another set of secrets, another point of failure. Skip until someone needs it.
9. **Tiered rollout, not "all four Workers in v1.5".** Locked May 8. The public skill ships in three layers: Tier 1 (zero infra, already in v1.4.x), Tier 2 (one Worker plus D1 plus JotForm, target v1.5), Tier 3 (the SMS Worker plus optional polish Workers, target v1.6 and v1.7). Most adopters will land at Tier 2 and never spend a cent on infrastructure. The original "all four Workers in v1.5.0" plan from this handoff is OBSOLETE.
10. **Workers Paid plan is ONLY for Tier 3 SMS.** $5/mo Cloudflare Workers Paid is required for Durable Objects in the `showing-sms` Worker. Every other Worker (`jotform-to-lofty`, `leads-index`, `short-links`) runs on the Cloudflare free tier. v1.4.1 and v1.5 cost the recipient nothing.
11. **Short-links Worker is a candidate for cut.** Locked May 8 as "investigate cutting from public skill entirely." The branded short-link feature is a Joe-brand investment; the long Jotform prefill URL works fine in SMS in 2026. If the v1.7 design session confirms the cut, the public skill ships without `short_links_worker.js` and recipients send long URLs in their post-showing texts. Joe's private setup keeps `go.sellingpdxhomes.com` independently.

---

## Phase 2 stages (re-sliced into tiers, May 8, 2026)

Stage A: extend `lofty_api.py` with the showing primitives plus the v1.4.1 find_client fallback. (Largest pure-Python work.) **COMPLETE through v1.4.1.**

Stage B: bundle the Workers as a tiered, configurable, deployable kit. **Re-sliced** from "all four Workers in v1.5" to "one Worker per release":
- v1.5 = Tier 2 (`jotform-to-lofty` Worker + D1 + optimized setup).
- v1.6 = Tier 3 SMS (`showing-sms` Worker, requires $5/mo paid plan).
- v1.7 = Tier 3 polish (`leads-index` Worker, optionally `short-links` Worker if not cut per locked decision #11).

Stage C: orchestration. Port the `schedule-showing` skill and add Phase 2 onboarding to the Easy Mode setup. Target v1.7 or later (no longer pinned to a specific version, will fall in wherever it fits).

Each tier is shippable on its own and useful in isolation. Most adopters will install v1.5 and stop there.

### Stage A status: COMPLETE (v1.3.0 + v1.4.0 + v1.4.1)

A1 ~~Revise `post_showing_questions.yaml` to match D1 schema.~~ DONE.
A2 ~~Read `saling-automation/scripts/lofty_api.py` end-to-end.~~ DONE.
A3 ~~Port `prepare_showing` and the rest of the showing primitives.~~ DONE.
A4 ~~Add CLI handlers and write smoke runner at `scripts/test_v1_3_methods.py`.~~ DONE.
A5 ~~Update CHANGELOG to v1.3.0, repackage .skill.~~ DONE.

Stage A bonus work in v1.4.0 (May 7 deep API probe):
- Fixed Content-Type bug affecting all DELETE methods. Same patch applied to production.
- Found 8 new quirks; documented as #21-#28 in `references/quirks.md`. Quirk #6 marked obsolete.
- Ported 22 additional production methods: communication history reads, transactions, alerts, system logs (the unified human-readable timeline), task lifecycle, note lifecycle, webhook lifecycle, schema introspection.
- Expanded `refresh_leads_index.py::_normalize` from 17 to 36 fields.
- Confirmed Lofty's REST surface via 12 targeted 404s. Documented in `RESEARCH_NOTES_2026-05-07.md` at the kit root.

Stage A bonus work in v1.4.1 (May 8 fix release):
- `find_client` fallback to live API scan when local index misses. Closes the new-contact gap.
- `_search_recent_leads` helper using scrollId-cursor pagination.
- Quirk #29 added: `/v1.0/leads` `page` parameter is silently ignored.
- Same patch mirrored to production.

### Stage B status: NOT STARTED. Re-sliced into three releases.

#### v1.5 (Tier 2: `jotform-to-lofty` Worker + D1)

B1.1 Read `saling-automation/worker/jotform_to_lofty_worker.js` end-to-end. Confirm the field-alias mapping vs. the field-ID mapping (see "Tier 2 (v1.5) plan" below for why this matters).
B1.2 Read `saling-automation/worker/migrations/001_showing_feedback.sql` (already generic, ports verbatim).
B1.3 Read `saling-automation/worker/wrangler.jotform.toml` and identify all Joe-specific values to placeholderize.
B1.4 Read `saling-automation/docs/phase2-feedback-db-deploy.md` if it exists. This is the runbook to port and parameterize.
B1.5 Create `lofty-cowork-helper/workers/` directory. Copy the Worker JS, the SQL migration, and a templated wrangler config. Strip Joe-specifics. Replace hardcoded values with `<placeholder>` tokens or env-driven config.
B1.6 Write `lofty-cowork-helper/references/workers_setup.md` for the Tier 2 deploy. Cloudflare MCP for D1 creation and migration apply, wrangler for Worker code deploy and secret push. Five-minute target setup, validated by walking through it on a fresh test account.
B1.7 Implement the five Tier 2 optimizations (see "Tier 2 (v1.5) plan" below).
B1.8 Add a Tier 2 Easy Mode walkthrough subroutine to SKILL.md: "set up post-showing feedback."

#### v1.6 (Tier 3 SMS: `showing-sms` Worker)

B2.1 Read `saling-automation/worker/showing_sms_worker.js` and `wrangler.toml` (the DO migration).
B2.2 Port the Worker to `lofty-cowork-helper/workers/`. Strip the hardcoded SMS template ("it's Joe") into an env-driven `OWNER_SMS_NAME` field.
B2.3 Document the Workers Paid plan requirement prominently in the Tier 3 setup docs.
B2.4 Add a Tier 3 SMS Easy Mode walkthrough subroutine.

#### v1.7 (Tier 3 polish: `leads-index` Worker, possibly `short-links` Worker)

B3.1 Decide whether to ship the `short-links` Worker at all (locked decision #11). If yes, port it; if no, document the long-Jotform-URL approach in the Tier 2 setup.
B3.2 Port the `leads-index` Worker. Note: v1.4.1's find_client fallback makes this Worker a polish item rather than a requirement.
B3.3 Update SKILL.md to surface the Tier 3 polish add-ons as opt-in.

### Stage C status: NOT STARTED. Target v1.7 or later.

C1 Port `.claude/skills/schedule-showing/SKILL.md` from `saling-automation` into the public kit as a sub-skill (or merged into the main SKILL.md as a workflow recipe; decide based on how Cowork prefers to bundle skills).
C2 Add Phase 2 onboarding step to the public skill's Easy Mode setup: "Do you want the showing automation pieces?" If yes, walk through the relevant tier deploys.
C3 Cancellation flow, multi-stop tour flow, post-showing feedback flow workflow recipes.

---

## Tier 2 (v1.5) plan

Five optimizations, locked in the May 8 design conversation. The first three together reduce setup from ~30 minutes to ~5 minutes. Numbers four and five are polish.

1. **Build the Jotform form programmatically at setup.** The Easy Mode walkthrough calls Jotform MCP's `create_form` with the structure derived from `assets/post_showing_questions.yaml` (already in the public skill). The user gets a fresh form in their account with predictable field IDs. The Worker drops the alias-guessing code (currently 30+ lines of `RATING_FIELDS` / `TEXT_FIELDS` / `TAG_FIELDS` arrays) and keys off the known IDs instead. Setup goes from "build a form with these 14 fields and pray the aliases match" to "say yes when Claude asks if you want a feedback form." THIS IS THE BIGGEST WIN.

2. **Drop Resend as a setup requirement.** Lofty's `send_email` is the default recap path. Resend becomes opt-in via `RESEND_API_KEY` env var. Removes one entire account from the onboarding flow. Day-1 users get the recap email feature without a second sign-up. Already locked in decision #4.

3. **Cloudflare MCP for D1, wrangler only for Worker code.** Setup walkthrough calls `d1_database_create` and `d1_database_query` via MCP. The MCP returns the database ID, which Claude pipes into the wrangler config automatically. Migration SQL applied via MCP too. Wrangler is left only for `wrangler deploy` and `wrangler secret put`.

4. **Auto-generate `PREFERENCES_API_KEY`.** Setup script generates a random 32-char string, writes it to `.env` and pushes it to the Worker as a secret in the same step. User never sees it.

5. **Auto-wire the Jotform webhook.** After the Worker deploys and we know its URL, Jotform MCP sets the form's webhook URL automatically. No "now copy this URL into Jotform's Settings" paragraph.

### Open question for v1.5 to resolve before B1.7

The form-import optimization (#1) makes the public Worker key off Jotform field IDs instead of guessing aliases. That means the public Worker will NOT be drop-in compatible with Joe's existing production form. Two paths:

a) Ship a different field-ID-based Worker for the public template only. Leave Joe's production Worker (alias-based) alone. Two codebases diverge.

b) Update both Joe's production AND the public to a field-ID-based Worker at once. Migrate Joe's existing form to match the new ID scheme. Single codebase stays.

NOT decided in the May 8 conversation. Joe to pick at the start of v1.5.

### One simplification considered and rejected (May 8)

Moving the recap email send out of the Worker and into the Python client would remove the Resend dependency from the Worker entirely. Rejected because of timing: if a buyer submits feedback at 7pm and the agent is not running Cowork, the email does not go out until next morning. Bad buyer experience. Email stays in the Worker.

---

## Where everything lives (current state)

- **Skill source:** `/Users/joesaling/Code/lofty-cowork-skill/lofty-cowork-helper/`
- **Packaged skill file:** `/Users/joesaling/Code/lofty-cowork-skill/lofty-cowork-helper.skill` (v1.4.1, ~90 KB, gitignored)
- **Production reference:** `/Users/joesaling/Code/saling-automation/` (mounted; grant via `mcp__cowork__request_cowork_directory` if missing)
- **Public web page source:** `docs/index.html`
- **Recipient-facing docs:** `INSTALL.md`, `README.md`, `LICENSE`, `CHANGELOG.md`
- **Distributor docs:** `PACKAGING.md`
- **References:** `lofty-cowork-helper/references/{full-guide,quirks,workflows,extending,calendar_routing}.md`
- **Assets:** `lofty-cowork-helper/assets/{lofty_api.py,env-template,CLAUDE.md.template,ics_builder.py,post_showing_questions.yaml}`
- **Scripts:** `lofty-cowork-helper/scripts/{setup_check.py,refresh_leads_index.py,test_v1_2_methods.py,test_v1_3_methods.py}`
- **Logo:** `docs/SalingHomes_logo_wEXP_logo.png` (kept for the Saling Homes-branded GitHub Pages site; do NOT include in the .skill file or public template)
- **Repackage command:** `cd /sessions/<your-session>/mnt/.claude/skills/skill-creator && python3 -m scripts.package_skill /sessions/<your-session>/mnt/lofty-cowork-skill/lofty-cowork-helper /sessions/<your-session>/mnt/lofty-cowork-skill`

`calendar_routing.md` and `ics_builder.py` exist but are demoted to "future feature" per locked decision #6. Don't delete them; they'll come back when someone wants Outlook or Lofty-only flows.

---

## Outstanding decisions

1. **`v1.4.1` git tag.** The commit landed on origin/main as `f027a87` but no tag was created. If Joe wants release-tag parity with v1.4.0, tag it. Otherwise leave it as a tagless patch on main.
2. **Form-import migration path for v1.5.** See "Open question for v1.5 to resolve before B1.7" above. Two-codebase divergence vs. one-codebase migration. Joe to pick at the start of v1.5.
3. **Cut the short-links Worker from the public skill?** Locked decision #11 flagged this for investigation at v1.7. Joe to confirm at that time.
4. **Slide deck for Joe's realtor talk.** Joe was building a 12-slide deck in Claude Design at `claude.ai/design`, project name "Lofty + Claude for Realtors - 25 min Talk." Verify state. Separate from engineering work.
5. **Lofty API key rotation.** Joe mentioned he might want to rotate after Phase 2 ships, since this skill becomes semi-public. Hold the rotation until Phase 2 is fully deployed so it's a single rotation pass, not two.

---

## MCP connectors confirmed available

- **JotForm MCP:** `mcp__fb185796-3f32-4d0b-960a-fb8d0869ca9c__*` (9 tools). `search`, `create_form`, `edit_form`, `display_form`, `assign_form`, `fetch`, `list_submissions`, `create_submission`, `analyze_submissions`. Used in this session to find Joe's real form (ID `261267225671155`) and read its question structure.
- **Cloudflare MCP:** `mcp__c55037a8-92bb-4dab-ab11-9e055ea57019__*` (~25 tools). Notable scope: `accounts_list`, `set_active_account`, `d1_database_create/query/get/delete`, `kv_namespace_create/get/update/delete`, `workers_list/get_worker/get_worker_code` (READ-ONLY for Workers), `r2_bucket_create/get/delete`, `search_cloudflare_documentation`. Workers cannot be DEPLOYED via MCP; deploys still need wrangler.
- **Google Calendar MCP:** `mcp__a3caf83a-55c5-4144-a996-303f3d83e660__*`. `create_event`, `update_event`, `delete_event`, `list_calendars`, `list_events`, `respond_to_event`, `suggest_time`. Used in production for showing scheduling.
- **Asana, Canva, Gmail, Google Drive, Microsoft Learn:** also installed. Not directly relevant to Phase 2 build but available.
- **Microsoft 365 connector:** Anthropic-hosted, opt-in per agent. NOT installed for Joe (he doesn't have M365). Documented as the future Outlook calendar adapter for coaching clients on M365.

Loading deferred tool schemas in a new session: `ToolSearch` with `select:<tool_name>[,<tool_name>...]` for direct picks, or keyword search like `query: "cloudflare"` to bulk-load.

---

## Brand and voice rules (apply to ALL new content; PUBLIC skill must use placeholders, not Joe-specific values)

These are Joe's personal brand rules. They apply to public-facing content in the kit ONLY where the kit is referencing Saling Homes assets (the GitHub Pages site, README disclosure language Joe wrote). The public template files (SKILL.md, lofty_api.py, references, etc.) must NOT carry these specifics; they're for the recipient to fill in.

- **No em-dash characters anywhere.** Use commas, periods, or hyphens. Apply to ALL new content, public template included.
- **Forbidden words (Saling Homes brand only, not enforced in template files):** cozy, vibrant, amazing, incredible, mouthwatering, family-friendly, good schools, safe neighborhood.
- **Voice signature (Saling Homes brand only):** "Listening, educating, advocating."
- **Colors / fonts / logo / phone / email:** ONLY in `docs/index.html` (the GitHub Pages site for the kit's homepage, which is Saling Homes-branded by design as Joe's distribution channel). DO NOT carry into SKILL.md, references, assets, or the .skill bundle.

---

## Data handling disclosure (apply consistently to anything new)

This wording is currently used on the homepage, README, and INSTALL. Any new public-facing doc should mirror it:

> When you ask Claude to look up, update, or summarize leads, the lead content Claude reads (names, contact info, notes, activity) is processed through Anthropic's models the same way any Claude conversation is processed. Your Lofty API key stays on your computer and is never sent to Anthropic.
>
> Before using this tool with real client data, confirm it fits your brokerage's data handling rules, your MLS rules, and what your clients reasonably expect. This skill is provided as is. Verify behavior in your own Lofty account before relying on it for client-facing work. Not affiliated with or endorsed by Lofty Inc. or Anthropic.

Phase 2 disclosure expansion needed at each tier ship:

- v1.5 ship: lead data passes through Cloudflare (the Worker and D1) and JotForm (form submissions). Add these as named third parties, note recipient responsibility to verify their brokerage's rules cover them.
- v1.6 ship: SMS feedback texts route through Lofty's SMS endpoint (already covered) but the Worker handling the schedule queue runs on Cloudflare. No new third parties beyond v1.5; just expand the surface description.
- v1.7 ship: leads-index Worker reads webhook events from Lofty and stores them in Cloudflare KV. Same providers as before. If short-links Worker is shipped (decision #11 pending), the redirector domain becomes a new visible touchpoint for buyers.
- Optional Resend: only when the user opts in. Disclosure should treat it as opt-in, not default.

---

## Joe's contact

Joe Saling, Saling Homes at eXp Realty, 503-910-7364, joe@sellingpdxhomes.com, www.sellingpdxhomes.com.

These details belong in HANDOFF.md and `docs/index.html` ONLY. Not in the public template.

---

## What to do first when picking this up (recommended order, v1.5 pickup)

Stage A is COMPLETE through v1.4.1. The next session is picking up at v1.5 / Tier 2: porting the `jotform-to-lofty` Worker plus D1 plus the optimized setup, NOT all four Workers. The "all four Workers in v1.5" plan from earlier in this handoff is OBSOLETE; locked decision #9 supersedes it.

1. Read this HANDOFF.md (you're doing it now). Pay particular attention to the Phase 2 LOCKED DECISIONS section (especially #9 tiering, #4 Resend optional, #10 paid plan only for Tier 3 SMS, #11 short-links cut candidate) and the Tier 2 (v1.5) plan section.

2. Verify `~/Code/saling-automation/` is mounted via `mcp__cowork__request_cowork_directory`. If not, request it. The production reference is required for the Worker port.

3. Read `CHANGELOG.md` and confirm v1.4.1 is the latest entry. Run `git log --oneline -5` against the kit repo and confirm commit `f027a87` is on origin/main. If the v1.4.1 tag is missing, ask Joe whether he wants to add it before v1.5 starts (outstanding decision #1).

4. Read `RESEARCH_NOTES_2026-05-07.md` at the kit root if you have not already. The API surface map and the architectural justification for the Workers is still relevant.

5. Read the v1.5-relevant production files end-to-end (skip the SMS and leads-index Workers, those are v1.6 / v1.7 territory):
   - `saling-automation/worker/jotform_to_lofty_worker.js`
   - `saling-automation/worker/migrations/001_showing_feedback.sql`
   - `saling-automation/worker/wrangler.jotform.toml`
   - `saling-automation/docs/phase2-feedback-db-deploy.md` (the Joe-side runbook to port and parameterize)
   - `saling-automation/docs/architecture.md` (still useful context)

6. Resolve outstanding decision #2 with Joe BEFORE coding anything: "For the form-import optimization (Tier 2 plan #1), do you want to ship a separate field-ID-based Worker for the public template (your production form stays alias-based), or migrate both your production form and the public Worker to the new field-ID scheme at once?" Wait for his answer.

7. Ask Joe one more confirmation: "Ready to push into B1.5 (port the Worker, strip Joe-specifics, write the v1.5 setup runbook)?" Wait for his answer.

8. When porting begins: every Worker URL, every account ID, every secret name becomes a placeholder or pulled from env. The Cloudflare account ID `22c50f7ac3f85d789dfec570642ae9af`, the `joe-2c5.workers.dev` subdomain, the `sellingpdxhomes.com` domain, and Joe's email signature MUST NOT appear in the public kit. Use the Cloudflare MCP for read-only inspection during development; reserve `wrangler` for actual deploys.

9. Setup-time goal: a fresh Tier 2 install runs in roughly five minutes. If the runbook gets longer than that, look back at the five Tier 2 optimizations and check whether something is being underused.

Do NOT delete this HANDOFF.md until Phase 2 is finished and shipped. Joe wants it kept as the working brief.
