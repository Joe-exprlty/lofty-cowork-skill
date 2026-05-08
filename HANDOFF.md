# Session Handoff: Phase 2

This file gets a new Claude Cowork session up to speed on the **Phase 2** build of the Lofty + Cowork skill project. Read this first, then explore the current files before doing anything.

**Status as of May 7, 2026 (late evening):**

- v1.2.0 is built locally (`lofty-cowork-helper.skill`, ~50 KB at the kit root). Phase 1.5 done. Four new methods (`search_listings`, `create_task`, `send_email`, `send_sms`) verified live against Joe's real Lofty.
- Phase 2 design has been REVISED. Earlier in the same session I designed a calendar adapter pattern, an .ics builder, and a question pack from scratch. Then Joe granted access to his production `saling-automation` repo and most of those designs were either wrong-shape or overkill compared to what's already running in production.
- Stage A1 (revising `post_showing_questions.yaml` to match the real D1 schema) is done. Stages A2 through A5 are next.
- v1.2.0 has NOT been pushed to GitHub or tagged yet.

If you're a new Claude session: do NOT redesign Phase 2 from first principles. The reference implementation is `~/Code/saling-automation/`. Phase 2 of the public skill is a port + strip + parameterize, not a fresh design.

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

## Where Phase 1 ended (May 7, 2026, v1.2.0 - SHIPPED LOCALLY, NOT YET PUSHED)

v1.2.0 is built, polished, and ready. Working tree has uncommitted changes from the Phase 2 design exploration. Whether to commit those before tagging is a judgment call, see "Outstanding decisions" below.

What v1.2.0 ships (Phase 1.5):

- Easy Mode setup as the default (plain English, Claude does technical work)
- Power User Mode opt-in via "I'm technical" or "skip ahead"
- Branded web page at `docs/index.html`
- INSTALL.md is a 50-line stub pointing at the web page
- README.md has a data handling disclosure
- SKILL.md is tightened so Claude no longer reads the `.env` back to validate the key
- All forbidden em-dash characters removed
- Four new methods in `lofty_api.py`: `search_listings`, `create_task`, `send_email`, `send_sms`. All four verified live.
- Three new quirks documented (#15 listings body keys, #16 listing-singular response, #17 calendar create body keys).
- Body shapes in references/extending.md, full-guide.md, workflows.md corrected from the aspirational shapes (which would have failed the same way mine did) to the actual working shapes from `saling-automation`.

What v1.2.0 does NOT ship (Phase 2 territory):

- Showing scheduling end-to-end (`prepare_showing` and friends)
- Leads index (file or Worker)
- Post-showing feedback flow
- Pre-showing 2-hour confirmation SMS
- Branded short links
- Buyer preferences aggregation

---

## Phase 2 LOCKED DECISIONS

Decided in the May 7 design session, do not revisit without strong reason:

1. **Public skill = pure template.** No Joe-specifics anywhere in the kit. Recipients fork, fill in their own values, ship. This is non-negotiable.
2. **Phase 2 design = port from `saling-automation`, not redesign.** The production architecture works. Strip Joe-specifics, parameterize, add the public-skill's Easy Mode walkthrough on top.
3. **MCPs are the easy path for everyone.** Cloudflare MCP for D1 / KV / Worker inspection. JotForm MCP for form creation, submissions, analysis. Reserve `wrangler` CLI for the parts the MCP can't do (Worker code deploys, secret push). MCP-first is for both setup walkthroughs AND for how WE build the public skill.
4. **Recap email: optional with Lofty fallback at v1.** Recipient picks at setup. Resend if they want best-in-class deliverability. Lofty `send_email` if they want zero new accounts. Both paths get docs and tests.
5. **Leads index: Worker preferred, file fallback.** Same as Joe's proven design. Fresh Mac runs file-only until the Worker is deployed; after deploy, set `LOFTY_LEADS_INDEX_SOURCE=worker`.
6. **Calendar provider: Google Calendar at v1.** The four-provider router I designed (`references/calendar_routing.md`, `assets/ics_builder.py`) is parked as a "future feature for clients who want options." Production uses Google exclusively and that's what ships first. Keep the router files; demote them in SKILL.md to "if you want alternatives."
7. **Hosting model: self-hosted at v1.** Each agent deploys their own four Workers + D1. Joe-hosted-shared is a possible future "premium tier" service for paying coaching clients but is NOT how the public open-source skill ships. Self-host is the simpler ownership story for v1.
8. **Twilio is OUT for v1.** Lofty's SMS is reliable enough for the showing reminders. Twilio adds another account, another set of secrets, another point of failure. Skip until someone needs it.

---

## The three Phase 2 stages

Stage A: extend `lofty_api.py` with the showing primitives. (Largest pure-Python work.)
Stage B: bundle the four Workers as a configurable, deployable kit. (Worker source + wrangler configs + deploy runbook with Cloudflare MCP shortcuts.)
Stage C: orchestration. Port the `schedule-showing` skill and add Phase 2 onboarding to the Easy Mode setup.

Each stage is shippable on its own. Targeting v1.3.0 for Stage A complete, v1.4.0 for Stage B complete, v1.5.0 for full Phase 2.

### Stage A status

A1 ~~Revise `post_showing_questions.yaml` to match D1 schema.~~ DONE. The pack now has 6 rating_1_5 (first reaction, daily life fit, neighborhood, condition, value, shortlist), 2 long_text (standout, memory notes), 2 multi_select tag arrays (loved, dealbreakers), each `purpose` mapped 1:1 to a `showing_feedback` D1 column. Joe's "intentionally_excluded: Flood zone" wisdom annotation is preserved.

A2 Read `saling-automation/scripts/lofty_api.py` end-to-end. (~900 lines. Use offset/limit because Read has a token cap. Focus on `prepare_showing` and its sub-helpers, the leads-index reader, `find_listing_by_address`, `cancel_showing`. Skip stuff already ported in v1.2.0 like `create_task` and `send_email`.)

A3 Port `prepare_showing` and the rest of the showing primitives into the public `lofty-cowork-helper/assets/lofty_api.py`, with all Joe-specifics replaced by `<placeholder>` style values that the recipient sets in their `.env` (`SHORT_LINKS_WORKER_URL`, `SHOWING_SMS_WORKER_URL`, `JOTFORM_FORM_ID`, `LOFTY_PREFERENCES_API_KEY`, `LEADS_INDEX_WORKER_URL`, `LEADS_INDEX_EXPORT_API_KEY`, etc.). Write a parameter table at the top of the module so recipients know what to set.

A4 Add CLI handlers (`prepare-showing <args>`, `find-listing <full_address>`, `cancel-showing <leadId> <full_address>`, `list-pending-showings <leadId>`). Write a smoke runner at `scripts/test_v1_3_methods.py` that exercises against Joe's real Lofty using HIS `.env` from `~/Code/saling-automation/.env` via the `set -a; source ...; set +a` pattern from the v1.2.0 test runner.

A5 Update CHANGELOG to v1.3.0, repackage the .skill, update HANDOFF to mark Stage A done.

### Stage B status (not started)

B1 Read all four Worker source files in `saling-automation/worker/` to understand the moving parts.
B2 Create `lofty-cowork-helper/workers/` directory in the public kit. Copy the four Worker JS files plus their wrangler configs. Strip Joe-specifics. Replace any hardcoded URLs with environment-driven config.
B3 Copy `worker/migrations/001_showing_feedback.sql` (already generic).
B4 Write `lofty-cowork-helper/references/workers_setup.md` (port from Joe's `phase2-feedback-db-deploy.md`). Replace `wrangler` shell commands with Cloudflare MCP calls where the MCP supports it. Keep wrangler for: Worker code deploys, secret pushes, DO migrations.
B5 Add a Worker-deploy walkthrough subroutine to SKILL.md that can be called from Easy Mode.

### Stage C status (not started)

C1 Port `.claude/skills/schedule-showing/SKILL.md` from `saling-automation` into the public kit as a sub-skill (or merged into the main SKILL.md as a workflow recipe; decide based on how Cowork prefers to bundle skills).
C2 Add Phase 2 onboarding step to the public skill's Easy Mode setup: "Do you want the showing automation pieces?" If yes, walk through Cloudflare account check, JotForm account check, Resend optional, Worker deploys.
C3 Cancellation flow, multi-stop tour flow, post-showing feedback flow workflow recipes.

---

## Where everything lives (current state)

- **Skill source:** `/Users/joesaling/Code/lofty-cowork-skill/lofty-cowork-helper/`
- **Packaged skill file:** `/Users/joesaling/Code/lofty-cowork-skill/lofty-cowork-helper.skill` (v1.2.0, ~50 KB, gitignored)
- **Production reference:** `/Users/joesaling/Code/saling-automation/` (mounted; grant via `mcp__cowork__request_cowork_directory` if missing)
- **Public web page source:** `docs/index.html`
- **Recipient-facing docs:** `INSTALL.md`, `README.md`, `LICENSE`, `CHANGELOG.md`
- **Distributor docs:** `PACKAGING.md`
- **References:** `lofty-cowork-helper/references/{full-guide,quirks,workflows,extending,calendar_routing}.md`
- **Assets:** `lofty-cowork-helper/assets/{lofty_api.py,env-template,CLAUDE.md.template,ics_builder.py,post_showing_questions.yaml}`
- **Scripts:** `lofty-cowork-helper/scripts/{setup_check.py,test_v1_2_methods.py}`
- **Logo:** `docs/SalingHomes_logo_wEXP_logo.png` (kept for the Saling Homes-branded GitHub Pages site; do NOT include in the .skill file or public template)

`calendar_routing.md` and `ics_builder.py` exist but are demoted to "future feature" per locked decision #6. Don't delete them; they'll come back when someone wants Outlook or Lofty-only flows.

---

## Outstanding decisions

1. **v1.2.0 GitHub release.** Tag and release. Whether to commit the Phase 2 design files (calendar_routing.md, ics_builder.py, post_showing_questions.yaml) BEFORE the v1.2.0 tag or AFTER is the only judgment call. My recommendation: tag v1.2.0 from the state at the end of the v1.2.0 work (just the four new methods + body-shape fixes + quirks), then commit the Phase 2 work as the start of v1.3.0. Keeps the version history clean.
2. **Slide deck for Joe's realtor talk.** Joe was building a 12-slide deck in Claude Design at `claude.ai/design`, project name "Lofty + Claude for Realtors - 25 min Talk." Verify state. Separate from engineering work.
3. **Lofty API key rotation.** Joe mentioned he might want to rotate after Phase 2 ships, since this skill becomes semi-public. Hold the rotation until Phase 2 is fully deployed so it's a single rotation pass, not two.

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

Phase 2 disclosure expansion needed: when the recipient deploys the four Workers, lead data passes through Cloudflare (the Workers and D1) and JotForm (form submissions) and possibly Resend (email). Update the disclosure to enumerate these third parties and note the recipient's responsibility to verify their brokerage's data handling rules cover them.

---

## How to package the skill after editing SKILL.md

```bash
cd /sessions/<your-session-id>/mnt/.claude/skills/skill-creator
python3 -m scripts.package_skill /sessions/<your-session-id>/mnt/lofty-cowork-skill/lofty-cowork-helper /sessions/<your-session-id>/mnt/lofty-cowork-skill
```

Session ID is whatever your session has. Don't run this from inside the skill; run it from the skill-creator's location.

---

## Joe's contact

Joe Saling, Saling Homes at eXp Realty, 503-910-7364, joe@sellingpdxhomes.com, www.sellingpdxhomes.com.

These details belong in HANDOFF.md and `docs/index.html` ONLY. Not in the public template.

---

## What to do first when picking this up (recommended order)

1. Read this HANDOFF.md (you're doing it now).
2. Verify `~/Code/saling-automation/` is mounted via `mcp__cowork__request_cowork_directory`. If not, request it. This is the production reference; you cannot safely proceed without it.
3. Read `CHANGELOG.md` and confirm v1.2.0 is the latest entry.
4. Read `lofty-cowork-helper/SKILL.md`, focusing on the workflow section that mentions the new Phase 2 capabilities. Confirm the calendar router is demoted to "future" and that Google Calendar is the default.
5. Read `lofty-cowork-helper/assets/post_showing_questions.yaml` to confirm Stage A1 looks right.
6. Ask Joe one question: "Ready to push into Stage A2 (read your full lofty_api.py and start the port)?" Wait for his answer before doing more.
7. When Stage A2 begins: read `~/Code/saling-automation/scripts/lofty_api.py` strategically (it's ~900 lines, Read has a token cap, so use offset/limit). Focus on `prepare_showing`, `find_listing_by_address`, `find_client`, `build_jotform_url`, `shorten_url`, `enqueue_showing_sms`, `list_pending_showings`, `cancel_showing`, `get_buyer_preferences`, the leads-index reader. SKIP the methods already ported in v1.2.0 (`search_listings`, `create_task`, `send_email`, `send_sms`).
8. When porting in Stage A3: every URL, every brand string, every personal identifier becomes a placeholder. Read URLs from `.env`. Document the env-var contract at the top of `lofty_api.py`.

Do NOT delete this HANDOFF.md until Phase 2 is finished and shipped. Joe wants it kept as the working brief.
