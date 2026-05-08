# Session Handoff: Phase 2

This file gets a new Claude Cowork session up to speed on the **Phase 2** build of the Lofty + Cowork skill project. Read this first, then explore the current files before doing anything.

**Status as of May 8, 2026:**

- **v1.4.0 is built locally** (`lofty-cowork-helper.skill`, ~88 KB at the kit root). Phase 2 Stage A complete.
- v1.2.0, v1.3.0, and v1.4.0 are all in the working tree. CHANGELOG.md treats them as separate logical releases. NOT yet pushed to GitHub. Last tag on origin/main is `v1.1.0`. Recommended path is one combined commit + a single `v1.4.0` tag, since separating the working tree into three clean commits is impractical at this point.
- Phase 2 Stage A is COMPLETE: showing primitives ported, leads index, post-showing question pack, full read-coverage of the API surface, Content-Type bug fix that unblocks all DELETEs in the client.
- Phase 2 Stage B (the four Cloudflare Workers + D1 migration + setup runbook) NOT started.
- Phase 2 Stage C (`schedule-showing` orchestration sub-skill, Phase 2 onboarding in Easy Mode) NOT started.

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

## What v1.4.0 ships (current state, May 8, 2026 - SHIPPED LOCALLY, NOT YET PUSHED)

v1.4.0 is built, polished, and verified live. The kit is at the kit root as `lofty-cowork-helper.skill` (~88 KB). The CHANGELOG documents v1.2.0, v1.3.0, and v1.4.0 as separate logical releases.

What v1.4.0 ships (Phase 2 Stage A complete):

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

What v1.4.0 does NOT ship (Phase 2 Stages B and C):

- The four Cloudflare Workers themselves (Stage B, target v1.5.0): `leads-index`, `short-links`, `jotform-to-lofty`, `showing-sms`
- D1 migration SQL
- Workers setup runbook with Cloudflare MCP shortcuts
- The `schedule-showing` orchestration sub-skill (Stage C, target v1.6.0)
- Phase 2 onboarding step in Easy Mode setup (Stage C)

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

Each stage is shippable on its own. Stage A done at v1.3.0; v1.4.0 added the API surface expansion on top. Stage B targets v1.5.0; Stage C targets v1.6.0; full Phase 2 ships at v1.6.0.

### Stage A status: COMPLETE (v1.3.0 + v1.4.0)

A1 ~~Revise `post_showing_questions.yaml` to match D1 schema.~~ DONE.
A2 ~~Read `saling-automation/scripts/lofty_api.py` end-to-end.~~ DONE.
A3 ~~Port `prepare_showing` and the rest of the showing primitives.~~ DONE.
A4 ~~Add CLI handlers and write smoke runner at `scripts/test_v1_3_methods.py`.~~ DONE.
A5 ~~Update CHANGELOG to v1.3.0, repackage .skill.~~ DONE.

Stage A bonus work in v1.4.0 (added based on deep API research probing Joe's real Lofty on May 7, 2026):
- Discovered and fixed the Content-Type bug affecting all DELETE methods. Production has the same bug; Joe should patch his too.
- Found 8 new quirks; documented as #21-#28 in `references/quirks.md`. Quirk #6 marked obsolete in place.
- Ported 22 additional production methods: communication history reads, transactions, alerts, system logs (the unified human-readable timeline), task lifecycle, note lifecycle, webhook lifecycle, schema introspection.
- Expanded `refresh_leads_index.py::_normalize` from 17 to 36 fields to capture buyer/seller intent, DNC flags, `leadPropertyList`, etc.
- Confirmed that Lofty's REST API is much narrower than the UI suggests: 12 targeted 404s on guesses (stages, sources, segments, saved searches, drip campaigns, sequences, email templates, native showings, feedbacks). This negative data justifies the Phase 2 Workers+JotForm+D1 architecture and is documented in `RESEARCH_NOTES_2026-05-07.md` at the kit root.
- The deep-research notes file is local-only (not tracked in the repo by default). Joe can decide whether to commit it.

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

Stage A is complete. The next session is picking up at Stage B (porting the four Cloudflare Workers).

1. Read this HANDOFF.md (you're doing it now).
2. Verify `~/Code/saling-automation/` is mounted via `mcp__cowork__request_cowork_directory`. If not, request it. The production reference is required for the Worker port.
3. Read `CHANGELOG.md` and confirm v1.4.0 is the latest entry.
4. Confirm whether Joe has pushed v1.4.0 to GitHub yet:
   - Run `git log --oneline -5` and `git tag --list` against the kit repo.
   - If `v1.4.0` is NOT in the tag list, the working tree is still pre-release. Don't start Stage B until Joe ships v1.4.0; mixing pre-release working-tree changes with new Stage B work creates a tangled commit history.
   - If `v1.4.0` IS tagged, you're clear to start Stage B from a clean main.
5. Read `RESEARCH_NOTES_2026-05-07.md` at the kit root for the API surface map and the architectural justification of the Phase 2 Workers.
6. Read the four Worker source files in `saling-automation/worker/` end-to-end before designing anything: `leads_index_worker.js`, `short_links_worker.js`, `jotform_to_lofty_worker.js`, `showing_sms_worker.js`. Plus `worker/migrations/001_showing_feedback.sql` and the two wrangler configs (`wrangler.toml`, `wrangler.jotform.toml`).
7. Ask Joe one question: "Ready to push into Stage B1 (read all four Workers and plan the port)?" Wait for his answer before doing more.
8. When Stage B porting begins (B2 onwards): every Worker URL, every account ID, every secret name becomes a placeholder or pulled from env. The Cloudflare account ID `22c50f7ac3f85d789dfec570642ae9af` and the `joe-2c5.workers.dev` subdomain MUST NOT appear in the public kit. Use the Cloudflare MCP for read-only inspection during development; reserve `wrangler` for actual deploys.

Do NOT delete this HANDOFF.md until Phase 2 is finished and shipped. Joe wants it kept as the working brief.
