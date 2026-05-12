# Changelog

All notable changes to this skill will be documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). This project follows semantic versioning (MAJOR.MINOR.PATCH).

---

## [1.9.0] - 2026-05-11

Tier 4 ships. Adds the `leads-index` Worker, a third Cloudflare Worker that keeps a live mirror of the agent's Lofty leads inside Cloudflare KV. Lofty webhook list 2 feeds the Worker; `lofty_api.py` reads from the mirror when `LOFTY_LEADS_INDEX_SOURCE=worker` is set. Result: `find_client` and `get_recent_visits_from_index` stay fast and accurate even for large CRMs, with no polling and no manual `refresh_leads_index.py` runs.

Runs on the Cloudflare **free** tier. No Workers Paid plan needed. Resource budget is generous: ~1 KB per lead means 10,000 leads is ~10 MB (1% of the free 1 GB cap), and the content-diff check skips KV writes for no-op updates so a busy webhook stream still sits well under the 1,000 writes/day free cap.

Tier 4 is opt-in. The default file fallback (`data/leads_index.json` built by `scripts/refresh_leads_index.py`) is fine for small CRMs and still ships with the kit. Tier 4 upgrades that to a live, webhook-fed mirror that updates within 1-5 minutes of any change in Lofty.

### Added
- `lofty-cowork-helper/workers/leads_index_worker.js`. The Tier 4 Worker source. Ported from the maintainer's `saling-automation/worker/leads_index_worker.v2_draft.js`. All owner-specifics stripped. Routes: `GET /` (health), `GET /stats` (no auth, no PII), `POST /webhook/<secret>` (path-secret auth), `GET /export` (Bearer auth), `GET /lead/<id>` (Bearer auth), `POST /bulk-import` (Bearer auth). KV schema is `lead:<id>` + `_meta:index` + `_meta:ids`. Three efficiency features baked in: content-diff via a `DIFF_FIELDS` list (skip write if no find_client-relevant field changed), stage exclusion at write time (DNC / Archived / Agents-Vendors never stored), and `last_seen_at` timestamps stamped on every write. **Webhook handler rewritten during Layer 3 E2E** to flatten Lofty's actual plural-array payload shape (see the Notes section below); `flattenLoftyPayload` and `LOFTY_PAYLOAD_BUCKETS` are now module-scope helpers covering the real Lofty shape plus the documented-but-unobserved fallback shapes.
- `lofty-cowork-helper/workers/wrangler.leads-index.toml`. Templated wrangler config with `workers_dev=true`, `preview_urls=false`, a `LEADS` KV binding placeholder, and a deploy walkthrough in the header comment block (KV creation, three secret pushes via `wrangler secret put`, deploy, bootstrap, webhook wire-up).
- `lofty-cowork-helper/scripts/test_leads_index_worker.mjs`. Layer 1 unit test covering Bearer auth, lead/event extraction across both webhook payload families (Lofty's real plural-array buckets AND the documented-but-unobserved top-level / nested shapes), `flattenLoftyPayload` (real list-2 shape, multi-lead bucket entries, newLead / createdLead / deletedLead variants, mixed buckets, missing-leadId entries, legacy single/array fallbacks, bucket-wins-over-legacy precedence), `normalizeLead` (trim + lowercase + array defaults + null handling), `diffFieldsEqual` (ignores non-DIFF fields, ignores `last_seen_at`, detects stage / phone / tag / score / firstName changes, treats tag reordering as no-op), `arraysEqualUnordered` (length, content, numeric/string coercion), and `EXCLUDED_STAGES` / `DIFF_FIELDS` / `LOFTY_PAYLOAD_BUCKETS` sanity. 95 assertions, runs in plain Node.

### Changed
- `lofty-cowork-helper/SKILL.md` top-level description. Adds Tier 4 trigger phrases ("set up Tier 4," "deploy the leads-index Worker," "set up live leads index," "wire up the leads-index Worker," "turn on the webhook leads index") to the trigger list.
- `lofty-cowork-helper/SKILL.md` "How to start a session" routing block. Adds a new case that routes Tier 4 deploy triggers to the new picker section, parallel to the existing Tier 2 and Tier 3 picker routes. Notes that Tier 3 is NOT a Tier 4 prereq.
- `lofty-cowork-helper/SKILL.md` "Tier 4 setup: leads-index Worker" picker section. Mirrors the Tier 3 picker shape: trigger phrases, silent prereq probe, AskUserQuestion (Easy vs Power User Mode), Run the chosen path, When something fails, After a successful deploy.
- `lofty-cowork-helper/SKILL.md` "Building on this skill" list. Adds a leads-index Worker bullet; short-links flagged as candidate-for-cut.
- `lofty-cowork-helper/SKILL.md` file map. Adds `scripts/test_leads_index_worker.mjs`, `workers/leads_index_worker.js`, `workers/wrangler.leads-index.toml`. Updates `references/workers_setup.md` description from "Tier 2 + Tier 3" to "Tier 2 + Tier 3 + Tier 4."
- `lofty-cowork-helper/references/workers_setup.md`. Adds a complete Tier 4 setup section (~245 lines) parallel to the Tier 3 section: When you need Tier 4, What changed in v1.9, What you get, Prereqs, Test pyramid (Layer 1 unit / Layer 2 staging deploy / Layer 3 real Lofty webhook), Easy Mode walkthrough (9 steps including Step 0 terminal-open for non-developer users), Power User Mode walkthrough (same steps with explicit shell commands), Common errors, Roll back. Footer "What comes next" section now includes Tier 4 unlocks and removes the "leads-index ships in v1.7.x or later" stale wording.
- `lofty-cowork-helper/references/extending.md` "Backend B" section. Reframed as a pointer to the new Tier 4 setup walkthrough; the Worker code sketch is retained as background context. Also updates the four-Workers table to show kit-deploy paths for `jotform-to-lofty` (Tier 2), `showing-sms` (Tier 3), and `leads-index` (Tier 4), and to flag `short-links` as candidate-for-cut.
- `.gitignore` adds `.test-v1.9/` for Layer 3 E2E scratch.

### Validated
- Layer 1 unit tests (`test_leads_index_worker.mjs`) pass 95/95 (28 new assertions covering `flattenLoftyPayload` added during Layer 3). Tier 2 and Tier 3 smoke tests re-run with no regression.
- Layer 2: deployed `leads-index-staging` to a fresh KV namespace on the maintainer's production Cloudflare account (separate Worker name, isolated from production). 14 curl tests covering all six routes plus three auth variants plus the stage-exclusion path passed clean. Staging Worker and KV namespace torn down after.
- Layer 3: deployed `leads-index-staging-e2e`, wired a temporary Lofty webhook list 2 subscription, captured a real Lofty webhook payload after a live lead edit. The captured payload surfaced that Lofty groups lead events into plural-array buckets (`updatedLead[]`, etc.) rather than the top-level / nested shapes the v2 draft Worker expected. Added the `flattenLoftyPayload` helper to handle the real shape, redeployed, replayed the captured payload, confirmed the upsert path works end-to-end. Python `find_client(name)` with `LOFTY_LEADS_INDEX_SOURCE=worker` and the staging URL successfully read the live KV mirror. Webhook subscription unwired, Worker and KV namespace torn down.
- Em-dash audit: zero matches across the new Worker source, wrangler config, unit test, Tier 4 walkthrough, SKILL.md additions, extending.md changes, and this changelog entry.
- Owner-specifics audit: zero matches for "joe", "saling", "sellingpdxhomes", "503-910", "exp realty", "joe-2c5", `22c50f7a`, `2d6dd086` in any v1.9.0 file.

### Notes
- Locked decision #1 (public skill = pure template) maintained. Every owner-specific identifier in the v2 draft source was stripped or parameterized; no hardcoded values in the public Worker, the wrangler config, the unit test, the Tier 4 walkthrough, or the SKILL.md picker.
- Locked decision #10 (Workers Paid is ONLY for Tier 3 SMS) maintained. Tier 4 runs on the free Cloudflare tier.
- **Lofty webhook list 2 payload shape** confirmed during Layer 3 as: `{"listId": 2, "teamId": <n>, "updatedLead": [{"leadId": <n>, "updateTime": <epochMs>}, ...]}` (also `newLead[]` and `deletedLead[]` for create / delete variants, by symmetry with the documented Lofty event taxonomy). The v2 draft Worker source and the v1 production Worker both used an `extractLeadId` that looked only at top-level `leadId`, `data.leadId`, and `lead.leadId`. Neither shape matches what Lofty actually sends, so both Workers were silently dropping every webhook event. The v1.9.0 public-kit Worker is the first to handle Lofty's real shape correctly. Quirk documented in `references/quirks.md`.
- The v2 draft's content-diff, stage exclusion, `last_seen_at`, and skip-metrics improvements ship in the public kit as v1.9.0 even though the maintainer's own production is still on the v1 (no-diff, broken-parser) Worker. The v2 source has been validated end to end against real Lofty webhooks; the public kit gets the better defaults from day one.
- `LOFTY_LEADS_INDEX_SOURCE=worker` mode requires three new `.env` vars: `LOFTY_LEADS_INDEX_SOURCE=worker`, `LEADS_INDEX_WORKER_URL`, `LEADS_INDEX_EXPORT_API_KEY`. Without all three, `lofty_api.py` falls back to the local file (v1.4.1 behavior).

---

## [1.8.0] - 2026-05-11

Stage C ships. Adds the `schedule-showing` orchestration sub-skill, ported from a production implementation that has been driving the maintainer's multi-stop tours since April. Turns the kit from "all the primitives are here, ask Claude to wire them" into "describe what you want in one chat sentence and it happens." Triggers on phrases like "schedule a showing at," "book a tour for," "set up [client] at [address] at [time]," and the multi-stop pattern "schedule [client] at [addr1] at 4:30 then [addr2] at 5:00."

No new infrastructure, no new dependencies. Every primitive the orchestration calls (`find_client`, `find_listing_by_address`, `prepare_showing`, `create_note`, `list_pending_showings`) was already in the v1.3.0+ starter; Stage C is the orchestration layer that sits on top.

### Added
- `lofty-cowork-helper/skills/schedule-showing/SKILL.md`. The orchestration sub-skill itself. Ported from the maintainer's `saling-automation/.claude/skills/schedule-showing/SKILL.md`. All owner-specifics stripped: name, email, phone, virtual signature, brokerage, timezone, and the production short-links domain all replaced with references to the workspace `CLAUDE.md` placeholders (`<your-email>`, `<your-phone>`, `<your-timezone>`, etc.). Example client and address strings (Tuhin, the Smiths, the SW Buckhorn / SW Yarra tour) replaced with generic placeholders. The 8-step workflow (resolve client, convert times, prepare each stop, confirm calendar handling, create events in parallel, post showing-log notes, verify SMS queue, report) is preserved end to end. Idempotency notes, common-failure tree, full `prepare_showing` return shape, and safety rules all carried over.

### Changed
- `SKILL.md` top-level description. Adds showing-orchestration trigger phrases ("schedule a showing," "book a showing," "set up a tour," "tour [address] tomorrow," "schedule [client] at [address]") to the trigger list so the skill activates on those phrases directly.
- `SKILL.md` "How to start a session" routing block. Adds a new case that routes orchestration triggers to the `skills/schedule-showing/` sub-skill, parallel to the existing Tier 2 and Tier 3 picker routes. Notes the calendar backend prereq and the Tier 3 SMS Worker being optional.
- `SKILL.md` file map. Adds `skills/schedule-showing/SKILL.md` with a one-line description of what it does.
- `references/workflows.md` "Schedule a showing (full flow)" section. Adds a lead-in pointer to the new sub-skill as the fastest path for the typical case. The existing primitive-by-primitive manual recipe is kept as the fallback, framed as the "manual fallback for debugging a partial run."
- `references/extending.md` "Showing scheduling" section. Adds a one-paragraph pointer to the orchestration sub-skill at the top of the section, with the existing primitive composition notes preserved below for users who want to compose the helpers themselves.

### Validated
- Layer 1 read-through review: side-by-side compare of the public-kit sub-skill against the saling-automation source confirmed zero owner-specifics leaked through and the 8-step workflow is intact. Em-dash audit clean (0 matches). Joe-specifics audit clean (0 matches for "joe", "saling", "sellingpdxhomes", "503-910", "exp realty", "tuhin", "buckhorn", "yarra", "joe-2c5").
- Layer 2 dry-run chat test: confirmed the orchestration triggers correctly on a fresh Cowork session with a v1.8.0-candidate skill installed.
- Layer 3 E2E: one real showing scheduled end to end against the maintainer's own lead using the v1.7.0 Tier 3 Worker. Calendar invite landed, Lofty note was written with the calendar event ID appended, and the post-showing SMS was queued correctly.

### Notes
- Locked decision #1 (public skill = pure template) is now enforced for the orchestration layer too. Every owner-specific reference is read from the workspace `CLAUDE.md` at run time; nothing is hardcoded in the sub-skill prose.
- The orchestration runs on whichever calendar provider the agent selected at install time (`CALENDAR_PROVIDER` in `CLAUDE.md`). Step 5 routes through `references/calendar_routing.md`, so Google, Outlook, Lofty's calendar, and `skip` (buyer-only .ics) all work without any change to the sub-skill itself.
- The Tier 3 SMS Worker is optional. If `SHOWING_SMS_WORKER_URL` is unset in `.env`, Step 3 still works but the SMS queue side-effect is a no-op, and Step 7 (verify queue) is skipped. The orchestration is fully usable for agents on the free Cloudflare tier.

---

## [1.7.0] - 2026-05-11

Tier 3 ships. Adds the showing-reminder SMS Worker (`showing-sms`), a second Cloudflare Worker that fires the post-showing feedback text at the exact moment a showing starts. Uses per-showing Durable Object alarms (no cron, no polling, no idle wakeups). Validated end-to-end against the maintainer's production Cloudflare account using a separate Worker name (`showing-sms-staging`) so no second paid plan was needed. SMS landed on a real phone at 633ms precision relative to send_at.

This release REQUIRES the Cloudflare Workers Paid plan ($5/mo) on the deploying account because Durable Objects are not available on the free tier. The Tier 2 (post-showing feedback) and the rest of the skill continue to run on the free tier; only Tier 3 needs paid. The new Tier 3 picker in `SKILL.md` gates on this prereq before routing users into the setup walkthrough.

### Added
- `lofty-cowork-helper/workers/showing_sms_worker.js`. Ported from a production implementation that has been running at 162ms alarm precision since April. Joe-specifics stripped: the hardcoded "Joe" in the SMS body is now parameterized as the `OWNER_FIRST_NAME` env var (defaults to "your agent" if unset). Module-scope helpers (`isAuthorized`, `kvKeyFor`, `validateEnqueueBody`, `buildQueueEntry`, `buildSmsBody`) refactored from inline blocks so they can be lifted for unit testing. DO alarm semantics, KV index shape, and HTTP route surface are byte-identical to production.
- `lofty-cowork-helper/workers/wrangler.showing-sms.toml`. Templated config. `workers_dev = true` and `preview_urls = false` pinned (closes the same preview-URLs leak surface that v1.6.1 closed for Tier 2). KV namespace id is a placeholder (`REPLACE_WITH_YOUR_SHOWING_SMS_QUEUE_KV_ID`). Append-only `[[migrations]]` block auto-creates the `ShowingTimer` Durable Object class on first deploy. No cron trigger.
- `lofty-cowork-helper/scripts/test_showing_sms_worker.mjs`. Layer 1 of the Tier 3 test pyramid. 36 assertions covering auth, KV key shape, request validation (happy path, null body, string body, every missing-field permutation, invalid send_at), queue entry build (every field, default-empty optionals), and SMS body format (client name, owner name, address, URL, time cue, full format, owner name swappable). Runs in plain Node, no Cloudflare account, no network. Lifts module-scope helpers from the Worker source via the same string-replacement trick used by `test_worker_parsers.mjs` for Tier 2.
- `references/workers_setup.md` "Tier 3 setup" section. Parallel structure to Tier 2: prereqs (with the new Workers Paid plan check), test pyramid (the three layers), Easy Mode walkthrough (9 steps including a Step 0 that spells out how to open a terminal for non-developer users), Power User Mode walkthrough (same 9 steps with explicit shell commands), Tier 3 specific common errors, and the roll-back recipe.
- `SKILL.md` "Tier 3 setup: showing-reminder SMS Worker" picker. Trigger phrases include "set up Tier 3," "deploy the SMS Worker," "set up showing reminders," "set up post-showing SMS," and "wire up the showing-sms Worker." Silent prereq check probes for Workers Paid before routing into Easy or Power User Mode. Top-level description and "How to start a session" routing both updated to include Tier 3 trigger phrases.

### Changed
- `SKILL.md` file map. Adds `workers/showing_sms_worker.js`, `workers/wrangler.showing-sms.toml`, and `scripts/test_showing_sms_worker.mjs`. `references/workers_setup.md` description updated from "Tier 2 deploy runbook" to "Tier 2 + Tier 3 deploy runbook with Easy Mode and Power User Mode walkthroughs for both tiers." The "Other Cloudflare Workers" line in "Extending the skill" now lists only leads-index and short-links since `showing-sms` is shipping in this release.
- `.gitignore`. Adds `.test-v1.7/` (Tier 3 Layer 3 staging scratch, gitignored) and `.wrangler/` (wrangler's local cache that appears when wrangler runs from the repo root).

### Validated
- Layer 1 unit tests: 36/36 passing. All deterministic helpers locked.
- Layer 3 E2E pass against the maintainer's production Cloudflare account using a separate Worker name (`showing-sms-staging`) and a separate KV namespace (`SHOWING_SMS_QUEUE_STAGING`), torn down after the test. Enqueued a 90-second-out showing against the maintainer's own lead. Result: DO alarm fired at `sent_at: 2026-05-11T20:11:32.633Z` versus `send_at: 2026-05-11T20:11:32Z`, a 633ms delta end-to-end. Lofty accepted the SMS for delivery (`messageId` returned, `phoneNumber` matched), and the SMS landed on the maintainer's real phone at the correct time. KV audit row flipped from `pending` to `sent` with `sent_at`, `sent_to_phone`, and `sent_message` populated as expected. The `OWNER_FIRST_NAME` env var flowed through to the SMS body correctly ("Hi Joe, it's Joe" because the test lead was the maintainer; in production this would be "Hi {client first name}, it's {your first name}").
- KV `list()` eventual consistency confirmed during the E2E: a fresh `put()` is not visible from `list()` for up to ~60 seconds, but a direct `get(key)` returns the new entry immediately. The `/queue/<key>` endpoint uses direct `get()` so it bypasses the cache. `lofty_api.list_pending_showings` uses `list()` and accepts the lag.

### Notes
- Tier 3 deploys do NOT touch Tier 2. The two Workers are independent: separate names (`jotform-to-lofty` vs `showing-sms`), separate wrangler configs, separate KV namespace versus D1 database, separate URLs. They share only the `LOFTY_API_KEY` secret which is pushed once per Worker.
- The Lofty SMS endpoint requires a virtual phone number on the deploying account's Lofty plan. Without one, the DO alarm fires but Lofty's `POST /v1.0/message/sms/send` returns an error and the KV row records `status: "error"` with the Lofty error message. Documented in the Tier 3 common-errors section of `references/workers_setup.md`.
- Locked decision #10 (Workers Paid is ONLY for Tier 3 SMS) is now enforced in code: the Tier 3 picker probes for paid before deploy, every other Worker stays on the free tier. Locked decision #9 (tiered rollout, not "all four Workers in v1.5") is now substantially closed: Tier 2 shipped in v1.5/v1.6, Tier 3 ships in v1.7. Tier 3 polish (leads-index and short-links) remains opt-in for v1.7.x or later.

---

## [1.6.3] - 2026-05-11

Single-file housekeeping patch. Removes the only leftover scratch stub flagged in the v1.6.2 deferred list. No code changes. No Worker changes. No schema changes. The skill triggers and Worker behavior are byte-identical to v1.6.2. Existing installs do not need to redeploy. The v1.6.2 git tag, which had been documented as shipped but was never actually created on origin, was also created retroactively on commit 21ffa14 as part of this pass.

### Removed
- `lofty-cowork-helper/scripts/_tmp_worker_test.mjs`. The file had been trimmed to a 263-byte self-describing stub ("Stale scratch file from a prior session. Safe to delete; not loaded by anything.") in an earlier session. Deleting it now so the next `.skill` repackage does not pick up the dead path.

### Fixed
- Local-only: removed `lofty-cowork-helper/assets/__pycache__/lofty_api.cpython-310.pyc` and the empty `__pycache__/` dir from the working tree. The file was never tracked in git (the `__pycache__/` ignore rule has been in `.gitignore` since v1.0.0) but it existed on disk and would have been swept into the next `.skill` package by the packager's verbatim asset copy.

### Notes
- Three of the four deferred pre-release items from v1.6.2 were intentionally left in place per the maintainer's decision: `HANDOFF.md` stays in the public repo (it doubles as the working brief for the next Claude session, and the owner identity inside it is already public via `docs/index.html`), `lofty-api-guide.md` stays at the repo root (the duplication with `references/full-guide.md` etc. is documented but the file is not a hazard), and `RESEARCH_NOTES_2026-05-07.md` stays at the repo root for the same reason. These can be revisited at any future cleanup pass.
- The `v1.6.2` tag was created retroactively on commit 21ffa14 (the actual v1.6.2 release commit) as part of this pass. Local-only initially; push to origin together with the v1.6.3 changes.

---

## [1.6.2] - 2026-05-10

Pre-public-release cleanup pass. No code changes. No Worker changes. No schema changes. Sweeps a set of doc drift, broken pointers, and brand-voice violations that an audit surfaced before the skill ships to anyone outside Joe's machine. Existing v1.6.1 installs continue to run without re-deploy. The fixes matter only for new installs and for the public GitHub Pages landing page.

### Fixed
- `lofty-cowork-helper/assets/CLAUDE.md.template` "Where to look for detail" section pointed at two files that do not exist: `claude-cowork-lofty-guide.md` (wrong filename) and `lofty_api_starter.py` (wrong filename). Replaced with the correct paths (`references/full-guide.md`, `scripts/lofty_api.py`) and expanded the reference list to also surface `references/quirks.md`, `references/workflows.md`, and `references/extending.md` so a fresh install's CLAUDE.md tells Claude what is actually in the kit.
- `lofty-cowork-helper/SKILL.md` line 233 and line 303 still claimed Tier 3 (the showing-reminder SMS Worker) ships in v1.6. v1.6.1 corrected this in `workers_setup.md` but missed the two SKILL.md instances. Both now say v1.7. Aligns SKILL.md with the workers_setup.md bottom-of-file note.
- `lofty-cowork-helper/assets/env-template` line 12 still pointed at `Settings -> API Keys -> Generate` even after v1.6.1's API key path consistency pass. Updated to `Settings -> Integrations -> API -> Generate` so the env file users actually open during setup matches the new path.
- `lofty-cowork-helper/references/full-guide.md` prereqs (line 115) still said "API Keys section is visible." Updated to "Integrations, API section is visible." This was the second of two missed spots from v1.6.1's API key consistency pass.
- `docs/index.html` requirements checklist (line 633, the public GitHub Pages landing page) still told users to "click your profile picture top right, click Personal Settings, then Integrations. Scroll all the way down. If you see an 'API Keys' section..." This was the worst single contradiction in the repo, because it is the first page brand-new users land on. Updated to the current `Settings -> Integrations -> API` path.
- `lofty-cowork-helper/references/workflows.md` "Schedule a showing" section (lines 64-78) still claimed "the starter does NOT include showing helpers; see extending.md." `prepare_showing`, `find_listing_by_address`, and `cancel_showing` have been in the starter since v1.3.0. Rewrote the lead-in to reflect that only the `showing-sms` Worker (Tier 3, v1.7) requires additional setup.
- `lofty-cowork-helper/references/workers_setup.md` (lines 16, 87, 134, 151, 155). Removed five em-dash characters that crept in with v1.6 / v1.6.1's new workers_setup.md content. v1.1.0 originally scrubbed em-dashes across the skill per the project's brand rule; the rule was not enforced on the v1.6 additions. All five sites reworded inline using commas or sentence breaks. Two of the five were inside quoted Jotform UI taglines ("Share a link, I'll turn it into a form") which were verified to appear only in prose, not in any code that does string matching.
- `README.md` repo-structure tree (lines 13-31) listed only `SKILL.md`, `scripts/setup_check.py`, `references/`, and `assets/`. Rewrote to reflect the actual v1.6.1+ contents: adds `workers/` and `workers/migrations/`, the additional `scripts/` entries (`refresh_leads_index.py`, `test_v1_2_methods.py`, `test_v1_3_methods.py`, `test_worker_parsers.mjs`), the additional `references/` entries (`workers_setup.md`, `calendar_routing.md`), the additional `assets/` entries (`ics_builder.py`, `post_showing_questions.yaml`, `jotform_form_template.md`), and the top-level `CHANGELOG.md`. Anyone reading README to understand 1.6.2's scope now sees an accurate picture.

### Changed (docs only)
- `lofty-cowork-helper/workers/wrangler.jotform.toml` JOTFORM_FIELD_MAP comment block (lines 79-90) rewrote to lead with the new working default and frame the empty-map / alias-fallback path as the override case. Pre-v1.6.1 the empty map was the default and the alias path was the working state; v1.6.1 flipped that, but the comment block still described the old framing as if it were the working state. The actual `JOTFORM_FIELD_MAP` value on line 97 is unchanged. Pure comment refresh.

### Notes
- All seven Fixed items above and the one Changed item are pure doc edits. Zero changes to `lofty_api.py`, the Worker JavaScript, the SQL migration, the YAML schemas, the wrangler config values, or the SKILL.md frontmatter. The skill triggers and the Worker behavior are identical to v1.6.1.
- Verification grep ran after the edits: zero em-dashes in `lofty-cowork-helper/`, zero "API Keys section" or "Personal Settings" wording in user-facing docs (the one remaining instance in CHANGELOG.md is the v1.1.0 historical entry and intentionally preserved), zero "Tier 3 ... v1.6" claims, zero broken file pointers to `claude-cowork-lofty-guide.md` or `lofty_api_starter.py`, zero "starter does NOT include showing helpers" wording.
- Two minor housekeeping items deferred to a future pass: `lofty-cowork-helper/scripts/_tmp_worker_test.mjs` (looks like a leftover test file, probably should not ship in the `.skill` package) and `lofty-cowork-helper/assets/__pycache__/lofty_api.cpython-310.pyc` (Python bytecode cache that should be gitignored). Neither breaks anything if left in place.
- Two pre-release decisions remain open: what to do with `HANDOFF.md` (currently in the public repo, contains owner-specific identity and brand-voice rules) and `lofty-api-guide.md` at the repo root (a ~605-line standalone field manual that duplicates `references/full-guide.md`, `references/quirks.md`, and `references/extending.md`; nothing else in the repo references it).

---

## [1.6.1] - 2026-05-10

Patch release after end-to-end testing v1.6 with a brand new Jotform account and a brand new Cloudflare account exposed several first-time-user papercuts the original v1.6 release didn't surface. No architectural changes; the Worker code, D1 schema, and overall flow are unchanged from v1.6. Existing v1.6 installs continue to run without re-deploy; the only meaningful code-side fix (canonical `JOTFORM_FIELD_MAP` default) applies only to NEW installs cloning the public template.

### Fixed
- `lofty-cowork-helper/workers/wrangler.jotform.toml` ships the canonical `JOTFORM_FIELD_MAP` as the default value of the `JOTFORM_FIELD_MAP` env var. Previously the default was `"{}"` and Worker fell back to alias matching. Because the public template form's qid 51 uses Jotform's auto-generated unique name `anythingElse`, the alias path silently dropped buyer-typed memory notes on the floor. With the canonical map shipped as default, qid 51 routes correctly to the `memory_notes` D1 column on fresh installs.
- `lofty-cowork-helper/workers/wrangler.jotform.toml` explicitly sets `workers_dev = true` and `preview_urls = false` at the top level. Silences wrangler 4.x's default-warnings and (more importantly) closes a real attack surface: with `preview_urls` defaulting to true, every Worker version exposes a publicly accessible preview URL holding `LOFTY_API_KEY`.

### Changed (docs only)
- `lofty-cowork-helper/references/workers_setup.md` rewritten in multiple sections after E2E testing:
  - **Prereqs.** Added a leading step instructing users to install the Cloudflare MCP and Jotform MCP from Claude Desktop → Customize → Connectors before starting. Without these, Easy Mode can't read the user's accounts.
  - **Prereqs.** Added a dedicated step for obtaining the Lofty API token. Sends users to **Settings → Integrations → API** per Lofty's official docs at `api.lofty.com/docs` (previous kit text said "API Keys" which is the old section name).
  - **Prereqs.** Cloudflare API token step now explicitly walks users through setting **Account Resources** and **Zone Resources** dropdowns on the "Edit Cloudflare Workers" template. On a zoneless account (which every brand-new account is), both dropdowns must be set or Cloudflare won't let you create the token.
  - **Prereqs.** Jotform signup step now warns about the "SAVE 50%" upsell banner, the "Jotform for Claude" promo card (different integration, not what this kit uses), and the `?onboardingPrompt=1` first-run URL parameter that hides the "Import form" tile.
  - **Easy Mode step 2 (clone the template).** Path wording updated from "Create → Form → Import Form → From a Web Page" to "+ CREATE → Import form → Import from URL" to match Jotform's current UI. Added a note about Jotform's misleading "I'll turn it into a form" tagline (the behavior is a faithful clone, not AI synthesis). Updated the JOTFORM_FIELD_MAP note to reflect the new canonical-map default.
  - **Easy Mode step 7 (push secrets).** `LOFTY_API_KEY` is now auto-piped from `.env` via `grep | cut | tr | wrangler secret put`, eliminating the manual paste. Added a warning about wrangler's "There doesn't seem to be a Worker called 'jotform-to-lofty'. Do you want to create..." prompt that fires on every fresh-account install.
  - **Easy Mode step 8 (deploy).** Added a warning about wrangler's workers.dev subdomain registration prompt that fires on every fresh-account install. Noted that the chosen subdomain is permanent and globally unique. Added a note about wrangler 4.x `workers_dev` / `preview_urls` default warnings (v1.6.1's toml fix silences them).
  - **Easy Mode step 9 (wire webhook).** Rewritten end to end. The Jotform MCP cannot configure webhooks (its `edit_form` only handles question/field edits and returns empty changes for webhook instructions). Users now wire the webhook manually via Jotform UI: Form Builder → SETTINGS → Integrations → Webhooks → paste Worker URL → Complete Integration.
  - **Easy Mode step 10 (health check).** Added a warning that the workers.dev SSL certificate takes 5-15 minutes to propagate on a fresh subdomain. Curl returns exit code 35 during that window. Don't proceed to smoke test until the health check passes cleanly.
  - **Easy Mode step 11 (smoke test).** Added the `memory_notes` column verification as the canonical check that the `JOTFORM_FIELD_MAP` default fix is working.
  - **Power User Mode walkthrough.** Same Jotform UI path updates as Easy Mode step 2.
  - **Bottom of file.** Corrected the leftover claim that "Tier 3 ships in v1.6"; Tier 3 SMS Worker is now pinned for v1.7.
- `lofty-cowork-helper/SKILL.md`. Lofty API key retrieval path updated to match Lofty's official docs (`Settings → Integrations → API` rather than `Personal Settings → Integrations → API Keys`). Three locations updated: the user-facing walkthrough text, the error recovery script, and the Power User Mode setup quick reference.
- `lofty-cowork-helper/references/full-guide.md` step 7. Same Lofty API path update.

### Notes
- All v1.6 fixes were surfaced by a real end-to-end test against fresh Jotform and Cloudflare accounts, plus a real Lofty smoke submission writing to a real lead's timeline. Test artifacts live in the project's E2E test journal (gitignored).
- The patches do NOT require existing v1.5 or v1.6 production users to redeploy. Existing deployments that already have a populated `JOTFORM_FIELD_MAP` (per-install map derived during setup) continue to route correctly. The fix matters only for NEW installs that take the default toml without setting an explicit map.

---

## [1.6.0] - 2026-05-10

Tier 2 polish release. Switches Easy Mode form creation from `create_form` natural-language generation to a one-pass import of a polished public template. Eliminates the Classic Form / lowercase field name / theme color drift that the v1.5 `create_form` path produced. The `create_form` flow stays in the kit as a documented fallback. No Worker code changes; no D1 schema changes. v1.5 installs keep running unchanged; new installs land on the cleaner template-clone path.

### Added
- Public Jotform template at form id `261294238566162`. Polished Card Form, all hidden fields cleared, header HTML uses Jotform substitution tokens, no agent-specific contact info anywhere in the form. Ships pre-themed with a neutral gold accent on dark heading text. Installable via Jotform's import-from-URL flow at `https://www.jotform.com/workspace/` → Create → Form → Import Form → From a Web Page → paste `https://form.jotform.com/261294238566162` → Create Form.

### Changed
- `lofty-cowork-helper/references/workers_setup.md`. Easy Mode walkthrough step 2 is now the template-import flow, not the `create_form` call. The branding question is now an optional theme override since the template ships pre-themed. Power User Mode step 1 documents the import-from-URL flow as the recommended path with the from-scratch build as the fallback. Total Easy Mode steps trimmed from 12 to 11.
- `lofty-cowork-helper/assets/jotform_form_template.md`. Re-headed and re-framed as the v1.5 `create_form` fallback procedure. Used only when the template-import path is unavailable (no Jotform account willing to import shared templates, the template owner has cloning blocked, or the user has a strong reason to build from scratch).
- `lofty-cowork-helper/SKILL.md`. B1.8 Tier 2 picker references the template-clone path in the Easy Mode summary. Theme overrides are flagged as optional rather than required.

### Notes
- The canonical template form lives in the public skill maintainer's Jotform account. If the template owner enables Prevent Cloning on the form (form Settings) or Do Not Allow My Forms to Be Cloned by Other Users on the account (account Privacy), the import flow returns "Unauthorized request. You do not have access to this form" and the user is routed to the fallback procedure. Maintainers should keep both toggles off.
- Cloned forms preserve qids 40-51 used by the canonical `JOTFORM_FIELD_MAP`. The Worker's default map already encodes this shape, so per-install map derivation is no longer required for template-clone installs. The fallback `create_form` path still derives a per-install map.
- Tier 3 (showing-reminder SMS Worker) is unchanged; still pinned for a future v1.6.x or v1.7 release. Same goes for Stage C (`schedule-showing` orchestration sub-skill).

---

## [1.5.0] - 2026-05-09

Phase 2 Stage B: Tier 2 post-showing feedback Worker. Ships the `jotform-to-lofty` Cloudflare Worker, the `showing_feedback` D1 schema, and an Easy Mode setup walkthrough that uses Cloudflare MCP and Jotform MCP to bring up the entire stack in about five minutes. Recipients deploy their own Worker on the Cloudflare free tier; no paid plan required for v1.5. Verified end-to-end on production (Joe's `261040658235049` form) with a real lead, real D1 row, and real Resend recap.

### Added
- `lofty-cowork-helper/workers/jotform_to_lofty_worker.js`. Receives Jotform post-showing submissions, writes one Lofty note per submission via `POST /v1.0/notes`, writes one row per submission to D1, and emails the buyer a recap. Recap email is opt-in Resend (delivers to the buyer's submitted email and sends from a verified domain) or default Lofty `send_email` (delivers to the lead's primary email on file in Lofty, no extra account required). Workers free tier covers the load. Routes: `GET /` health check, `POST /` Jotform webhook, `GET /preferences/:leadId` Bearer-auth-gated buyer profile aggregation.
- `lofty-cowork-helper/workers/migrations/001_showing_feedback.sql`. D1 schema for the per-submission row store. Idempotent (`CREATE TABLE IF NOT EXISTS`), so re-running on an existing database is a no-op.
- `lofty-cowork-helper/workers/wrangler.jotform.toml`. Templated wrangler config. Database id, owner identity, and `JOTFORM_FIELD_MAP` are placeholders the setup flow fills in.
- `lofty-cowork-helper/references/workers_setup.md`. Full Tier 2 deploy runbook. Easy Mode walkthrough is the 12-step Cloudflare MCP + Jotform MCP + wrangler sequence. Power User Mode is the manual shell-and-clicks version. Adds a Node prereq step (Homebrew, .pkg installer, Windows installer, Linux package manager paths) and recommends `npx wrangler` over `npm install -g wrangler` to sidestep PATH issues.
- `lofty-cowork-helper/assets/jotform_form_template.md`. Read at runtime by Easy Mode Tier 2 setup. Holds the natural-language `create_form` prompt template, the post-creation `fetch` introspection, and the `JOTFORM_FIELD_MAP` build procedure.
- `lofty-cowork-helper/scripts/test_worker_parsers.mjs`. Smoke test for the Worker's submission parser. Synthesizes Jotform-shaped POST bodies and walks them through four scenarios: legacy alias-only form, fresh form without map, fresh form with map, and a renamed-fields case where only the qid map saves you. All 32 assertions pass.
- New "Tier 2 setup: post-showing feedback Worker" section in `lofty-cowork-helper/SKILL.md` (B1.8 picker). Triggers on phrases like "set up Tier 2," "deploy the Worker," "set up post-showing feedback." Asks Easy Mode vs Power User Mode via AskUserQuestion, runs silent prereq checks (`LOFTY_API_KEY`, `CLOUDFLARE_API_TOKEN`, Node, wrangler-or-npx, Jotform account, Cloudflare MCP and Jotform MCP connected), and routes to the appropriate `references/workers_setup.md` walkthrough.

### Changed
- `lofty-cowork-helper/assets/post_showing_questions.yaml`. `header_html` is now parameterized with `{{ACCENT_COLOR}}`, `{{TEXT_COLOR}}`, and `{{LOGO_HTML}}` tokens. New `default_accent_color` (#D4AF37 gold) and `default_text_color` (#1a1a1a near-black) fields hold sensible fallbacks for the "user accepts defaults" path.
- `lofty-cowork-helper/assets/env-template`. Added optional `OWNER_WEBSITE` line. `RESEND_API_KEY` reframed as optional with a clear description: skip it and the Worker still sends the recap, just through Lofty's `send_email` instead. Tier 2 install needs ZERO new accounts beyond Cloudflare and Jotform.
- `lofty-cowork-helper/SKILL.md` frontmatter description. Now triggers on Tier 2 deploy phrases.

### Fixed
- Worker Worker reads of hidden fields are now case-insensitive. Jotform's `create_form` agent normalizes hidden field names to lowercase (`propertyaddress` instead of `propertyAddress`) at form-creation time; the Worker now reads `submission.propertyaddress`, `submission.propertyAddress`, and the legacy `submission.property_address_hidden` in that order so submissions from forms built via either path resolve correctly. Same treatment for `showingDate` and `propertyStats`. Caught and fixed during the live production migration; covered by the smoke test's `fresh-aliasonly` scenario.

### Notes
- v1.5.0 is a Tier 2 release. Tier 1 (Lofty CRM client + leads index + showing primitives) is unchanged; existing v1.4.1 installs keep working with no migration. To opt into Tier 2, run "set up Tier 2" or "deploy the post-showing feedback Worker" in Cowork and follow the picker.
- Recap email default is Lofty's `send_email` endpoint. Resend is opt-in for users who want a verified-domain From address and to deliver to the email the buyer typed into the form (rather than the lead's primary email on file in Lofty).
- The natural-language `create_form` path documented in `assets/jotform_form_template.md` works but produces Classic Forms with mediocre visual polish. v1.6 will add a "clone this Jotform template" path that ships a polished Card Form template; v1.5 users can also point Easy Mode at an existing form they have already polished, since the qid map is derived from the running form rather than baked in.
- Tier 3 (showing-reminder SMS Worker) is a separate v1.6 deploy that requires the Cloudflare Workers Paid plan ($5/mo). v1.5 ships entirely on the Cloudflare free tier.

---

## [1.4.1] - 2026-05-08

Focused fix release. `find_client` now finds contacts that haven't yet synced into the local leads index. Before this patch, creating a new lead in Lofty and immediately asking Claude to find them returned "no match" because the index file (or the leads-index Worker) was still catching up. Now the lookup falls back to the live API and surfaces the new contact in one extra request.

### Fixed
- `find_client(name)` now falls back to a live `/v1.0/leads` scan when the local index returns no match. The API's default sort is newest-first, so a contact created seconds before the call lands at the top of page 1 and gets matched without waiting on the leads-index Worker's webhook delivery (1-5 minutes) or a manual `refresh_leads_index.py` run. Verified live by creating a fresh contact and watching the pre-fix behavior return `none` while the post-fix behavior returns `match` in one extra API call.

### Added
- `_search_recent_leads(max_pages=3, page_size=25)` helper. Yields leads from `/v1.0/leads` using `_metadata.scrollId` cursor pagination, since the obvious `page=N` parameter is silently ignored (new quirk #29). Default scan is the most recent 75 leads.
- New parameter `fallback_pages=3` on `find_client`. Set to `0` to disable the fallback and restore pre-1.4.1 behavior. Higher values scan more pages.
- Quirk #29: `/v1.0/leads` `page` parameter is silently ignored. Confirmed live in May 2026 (page=2 returns the same first 25 leads as page=1). scrollId is the only working pagination mechanism on this endpoint. Documented in `references/quirks.md`.

### Changed
- `search_leads` docstring updated to flag that `page` is silently ignored alongside the previously documented `keyword` and `sortField`. Behavior of `search_leads` is unchanged; only the comment is more accurate now.
- `find_client` return shape gains an additive `"source"` key with values `"index"`, `"api"`, or `"index+api"`. Existing callers that only read `match` / `candidates` / `none` keep working. Callers that care about freshness can now distinguish a cached hit from a fresh API hit.

### Notes
- v1.4.1 is a fix release. No new features, no new account requirements. A fresh installer needs only Lofty plus Python; no Cloudflare, no Jotform, no Resend.
- The `fallback_pages=3` default adds 1 to 3 extra API calls per `find_client` miss, at the rate-limit spacing of 6.5 seconds per call. Common case (new contact in page 1) is one extra call. Set `fallback_pages=0` if you need the old behavior for benchmarking or to suppress all extra requests.
- The same fix has been applied to the production reference at `saling-automation/scripts/lofty_api.py` so Joe's daily workflow benefits immediately. The two clients stay in lockstep.

---

## [1.4.0] - 2026-05-07

API surface expansion. Doubles the read coverage and rounds out task / note / webhook lifecycles. Unblocks every DELETE in the client by fixing a Content-Type bug that was silently breaking `delete_note` in production.

### Fixed
- `_request` now sends `Content-Type: application/json` on every request, regardless of method. Pre-v1.4, the header was sent only on POST/PUT, which made every DELETE return error 20001 "Content-type must be: application/json". Live probing in May 2026 also showed two GETs (`/v1.0/team-features/lead-ponds` and `/v1.0/teamFeatures/listCustomField`) require the header, contradicting the older "GETs must not send Content-Type" guidance. The single fix unblocks both classes of failure.
- `get_notes` now uses `pageNumber` (zero-indexed) and accepts an optional `lead_id`. Pre-v1.4 it used `page` (one-indexed) and required a `lead_id`, which both differed from production's working version.

### Added (read-only data surface)
- `get_call_history(lead_id=None, page=0, page_size=20)` - `/v1.0/communication/call`. Returns `{calls: [...]}` filtered to a lead.
- `get_email_history(lead_id=None, page=0, page_size=20)` - `/v1.0/communication/email`. Returns `{emails: [...]}`.
- `get_text_history(lead_id=None, page=0, page_size=20)` - `/v1.0/communication/text`. Returns `{texts: [...]}`.
- `get_transactions(lead_id)` - `/v1.0/leads/<id>/transactions`. Returns a list (not envelope).
- `get_alerts(lead_id)` - `/v1.0/alerts/ids/<id>`. Saved searches the lead subscribes to.
- `get_system_logs(lead_id, start_time=, end_time=, page=0, page_size=50)` - `/v1.0/systemLogs?leadId=<id>`. The unified human-readable timeline (calls, emails, texts, notes, stage transitions, manual logs) in chronological order with prose `content`. Friendliest read surface in the API; reach for this before assembling per-channel pulls.
- `get_custom_fields()` - `/v1.0/teamFeatures/listCustomField`. Schema of custom fields configured on your team. Returns list of `{attributeName, attributeType, value, params}`.
- `get_lead_ponds()` - `/v1.0/team-features/lead-ponds`. Lead ponds and routing rules.
- `get_organization()` - `/v1.0/org`. Returns `{enterpriseInfo, orgType}`.
- `get_members(page=0, page_size=25)` - `/v1.0/members`. Hard-capped at 25 per page (quirk #23).

### Added (lifecycle write methods)
- `update_note(note_id, content)` - PUT `/v1.0/notes/<id>`.
- `delete_note(note_id)` - DELETE `/v1.0/notes/<id>`. Now actually works thanks to the Content-Type fix.
- `get_tasks(lead_id=, start_time=, end_time=, include_finished=False, page=0, page_size=50)` - `/v2.0/calendar` with filters.
- `update_task(calendar_id, **fields)` - PUT `/v2.0/calendar/<id>`.
- `complete_task(calendar_id)` - POST `/v2.0/calendar/<id>/finish`.
- `uncomplete_task(calendar_id)` - POST `/v2.0/calendar/<id>/unfinish`.
- `delete_task(calendar_id)` - DELETE `/v2.0/calendar/<id>`.
- `get_available_meeting_slots(start_time, end_time, timezone_code=, limit=10)` - `/v2.0/calendar/meetings/available`.
- `add_lead_activity(lead_id, content, activity_type=None)` - POST `/v1.0/leads/<id>/activity`. Manual timeline entries for offline events.
- `create_transaction(lead_id, trans_type=, status=, price=, address=)` - POST `/v1.0/leads/<id>/transaction`.
- `create_webhook(list_id, callback_url)` - POST `/v1.0/webhook`. Body uses `callbackUrl` not `url` (silent failure mode if you get this wrong; quirk noted in method docstring).
- `delete_webhook(subscribe_id)` - DELETE `/v1.0/webhook/<id>`.

### Added (eight new quirks)
- #21: Some GET endpoints REQUIRE `Content-Type: application/json` (the opposite of #6).
- #22: DELETE endpoints REQUIRE `Content-Type: application/json`. Pre-v1.4 client failed silently on every DELETE.
- #23: `/v1.0/members` is hard-capped at 25 per page (same pattern as quirk #2 on `/v1.0/leads`).
- #24: `/v1.0/teamFeatures/listTag` returns BOTH definitions (`leadId == 0`) and applied instances.
- #25: `/v1.0/me.id` (short int) is a different ID format than `creatorUserId` / `assignedUserId` (15-digit string). Same user, different addressing schemes.
- #26: `/v1.0/leads/<id>/activities` returns a list directly, not a dict envelope.
- #27: `/v2.0/ai/lead-analysis` returns 500, not 404, in 2026.
- #28: `/v2.0/ai/call-script` returns 400 errorCode=20012 on the documented call shape.
- Quirk #6 marked obsolete in place (kept the entry, replaced the body with current guidance).

### Changed
- `refresh_leads_index.py::_normalize` expanded from 17 fields to 36. New captures: buyer/seller intent (`buyHouse`, `houseToSell`, `fthb`, `mortgage`, `preQual`, `buyingTimeFrame`, `sellingTimeFrame`, `withBuyerAgent`, `withListingAgent`), DNC flags (`cannotCall`, `cannotEmail`, `cannotText`, `unsubscription`), pond / ownership / lender context, lead's home address, `leadPropertyList`, `customAttributes`, `lastTouch` / `lastUpdateTime`, `birthday`, `referredBy`, social handles, `language`, `segments`, `leadType` / `leadTypes`. Existing 17 fields are unchanged so older clients continue to work.
- CLI gains 16 new commands: `timeline`, `calls`, `emails-history`, `texts-history`, `alerts`, `transactions`, `log-activity`, `tasks` (with `--lead` and `--include-finished`), `complete-task`, `delete-task`, `delete-note`, `update-note`, `custom-fields`, `ponds`. Existing `org` and `members` handlers preserved.
- `references/extending.md` "Capability ladder" rewritten to reflect 12 layers of starter coverage.
- `references/quirks.md` gains entries 21 through 28; quirk #6 body replaced with current guidance.

### Notes
- The expanded `_normalize` writes a richer JSON file. Older v1.3 clients reading the same file continue to work because they use `.get()` with defaults. After upgrading, run `python3 scripts/refresh_leads_index.py` once to repopulate with the rich fields.
- `delete_lead` is intentionally still NOT in the starter. Production has it but a single misuse can't be undone via API. Recipients who genuinely need bulk lead deletion should use Lofty's UI.
- AI endpoints (`get_lead_analysis`, `generate_call_script`) remain unported. Both are broken in 2026 according to live probing. Will revisit if Lofty announces a fix.

---

## [1.3.0] - 2026-05-07

Phase 2 Stage A. Ports the showing-scheduling primitives, leads index, and buyer-preferences rollup from a battle-tested production reference. The starter client now does the full day-to-day showings workflow without redesign.

### Added
- `LoftyAPI.find_client(name, exclude_stages=...)` reads from `data/leads_index.json` (or a Cloudflare Worker once deployed). Returns `{match}`, `{candidates: [...]}`, or `{none: True}`.
- `LoftyAPI.find_listing_by_address(full_address)` looks up an Active MLS listing by parsing the zip and scanning that zip with `search_listings`. Returns a slim listing dict on hit, or `{error: "missing_zip"|"address_not_found", message: ..., zipCode: ...}` on miss.
- `LoftyAPI.prepare_showing(full_address, start_datetime_iso, client_name=, lead_id=, duration_min=)` is the orchestration helper. Pure data builder: returns the calendar invite payload, the showing-log note text, the prefilled feedback URL, and queues the post-showing SMS. Does NOT create the calendar event or post the note (caller owns those side effects).
- Showing sub-helpers, all callable on their own: `build_jotform_url`, `shorten_url` (with long-URL fallback), `enqueue_showing_sms` (best-effort), `build_showing_invite`, `_showing_key_and_short`.
- `list_pending_showings(lead_id)`, `cancel_showing(lead_id, full_address)`, `cancel_showing_by_key(key)` for the showing-sms Worker queue. `cancel_showing` returns structured shapes (`status: "cancelled"`, `error: "no_match"`, `error: "multiple_matches"`) so callers don't have to guess.
- `get_buyer_preferences(lead_id)` hits the jotform-to-lofty Worker's `/preferences/<leadId>` endpoint for the D1-backed feedback rollup (loved tags, dealbreakers, average ratings).
- `_owner_profile()` reads OWNER_FULL_NAME, OWNER_BROKERAGE, OWNER_PHONE, OWNER_EMAIL, OWNER_LAST_NAME_LOWER, MLS_NAME from env. Used by `build_showing_invite` for the email signature, `find_client` for the lead-search self-exclusion, and `prepare_showing` for the calendar identifier and showing-log MLS stamp.
- `_require_env(name, hint=)` helper for clean missing-secret errors.
- Module-level constants: `LEADS_INDEX_PATH`, `LEADS_INDEX_STALENESS_DAYS`, `LEADS_INDEX_SOURCE`, `LEADS_INDEX_WORKER_URL`, `JOTFORM_WORKER_URL`. Class-level: `SHORTENER_BASE`, `SHOWING_SMS_BASE`, `SHORTENER_API_KEY` property.
- Env-var contract docblock at the top of `lofty_api.py` so recipients can see all 18 vars in one place.
- Six new owner-identity env vars in `.env`: `OWNER_FULL_NAME`, `OWNER_BROKERAGE`, `OWNER_PHONE`, `OWNER_EMAIL`, `OWNER_LAST_NAME_LOWER`, `MLS_NAME`.
- Six new Phase 2 Worker env vars: `LOFTY_LEADS_INDEX_PATH`, `LOFTY_LEADS_INDEX_STALENESS_DAYS`, `SHOWING_SMS_BASE_URL`, `JOTFORM_FORM_ID`, `JOTFORM_WORKER_URL`, `LOFTY_PREFERENCES_API_KEY`.
- CLI handlers: `find-client`, `find-listing`, `prepare-showing`, `list-pending-showings`, `cancel-showing`, `buyer-preferences`.
- `scripts/refresh_leads_index.py` ported from the production reference. Run once on a fresh Mac to bootstrap the file fallback before deploying the leads-index Worker.
- `scripts/test_v1_3_methods.py` smoke runner. Exercises `find_client`, `find_listing_by_address`, `prepare_showing`, `list_pending_showings`, `cancel_showing` (cleanup), and `get_buyer_preferences` against a real Lofty account using a 30-day-out test showing.
- Three new quirks: #18 (`find_listing_by_address` is Active-only by design), #19 (showing-sms Worker reuses the Lofty JWT as its bearer), #20 (`prepare_showing` is dry-run, caller owns side effects in calendar-then-note order).

### Changed
- `_load_dotenv` now walks three directory levels looking for `.env` (was two), matching the production reference. Useful when the client lives in a nested scripts folder.
- `LoftyAPI.__init__` uses `_require_env` for the LOFTY_API_KEY check, giving a clearer error pointing at `.env`.
- `assets/CLAUDE.md.template` adds the OWNER_* and MLS_NAME guidance plus a callout that the Phase 2 helpers read identity from `.env`.
- `references/extending.md` "Capability ladder" rewritten to mark v1.3 capabilities (leads index, showings, buyer preferences) as starter rather than future work. Aspirational pseudocode for `prepare_showing` and `find_listing_by_address` replaced with the real shipped shapes including the slim listing dict's `bedrooms`→`beds` / `bathrooms`→`baths` / `id`→`loftyListingId` renames.

### Notes
- Phase 2 methods that talk to Cloudflare Workers fail soft when the matching URL is empty in `.env`. `find_client` and `find_listing_by_address` work without any Worker; `prepare_showing` works without the SMS or short-link Worker (it just skips those steps). This means v1.3 is useful immediately on a fresh install, before the recipient deploys anything to Cloudflare.
- v1.3.0 does NOT ship the four Cloudflare Workers themselves (that's Phase 2 Stage B, target v1.4.0). The `references/extending.md` Worker section is unchanged for now and documents the deploy outline.
- The `schedule-showing` orchestration skill that wraps `prepare_showing` end-to-end (calendar event, Lofty note, buyer email) is also Stage C territory, targeting v1.5.0.

---

## [1.2.0] - 2026-05-07

Phase 1.5. Doubles the daily utility of the starter without requiring any new accounts (no Cloudflare, no JotForm, no Twilio).

### Added
- `LoftyAPI.search_listings(filter_conditions, sort_fields, page, page_size, sold, scope)` for MLS lookup via `/v2.0/listings/search`. Documents the comma-separated range syntax for price, beds, sqft, and the nested `location` object for city and zipCode.
- `LoftyAPI.create_task(lead_id, content, start_at, end_at, way, type_)` for Lofty tasks and follow-up reminders via `/v2.0/calendar`. Defaults to `type_="TASK"` and `way="Call"` to keep simple call-the-lead reminders one line. Warns against `type_="APPOINTMENT"` for showings (triggers listing-agent approval).
- `LoftyAPI.send_email(lead_id, subject, content)` for outbound email through the agent's connected Lofty email account.
- `LoftyAPI.send_sms(lead_id, content)` for outbound SMS through the agent's Lofty number.
- CLI handlers for all four: `search-listings`, `create-task`, `send-email`, `send-sms`.
- `scripts/test_v1_2_methods.py` smoke runner that exercises all four against the agent's own lead in one command.

### Changed
- `SKILL.md` "Common workflows" now lists the four new capabilities directly instead of pointing at `references/extending.md` for them. Send-rule (always confirm subject, body, and recipient before calling) is repeated at the workflow level so Claude reads it before reaching for the method.
- "Building on this skill" footer now reflects what's still genuinely future work (showing scheduling helpers, leads index, Cloudflare Workers, webhooks).

### Fixed
- `references/extending.md` `search_listings` body shape was wrong. Lofty wants `searchScope`, `soldFlag`, `filterConditions`, `sortFields`, `pageNum`, `pageSize`, NOT the obvious names. Sending the obvious names returns HTTP 200 with 0 results and no error. Fixed in the shipped client and documented as quirk #15.
- `references/extending.md` and `references/full-guide.md` `create_task` body shape was wrong. Lofty wants `taskWay` not `way`, requires `timeZoneCode`, and `assignedRole` accepts only `"Agent"` or `"Assistant"` (not `"ASSIGNED"`). Mismatch returns error code 20012 with no hint. Fixed in the shipped client and documented as quirk #17.
- `references/quirks.md` updated with three new quirks: #15 (listings body camelCase keys), #16 (response array under `"listing"` singular), #17 (calendar create body shape).

### Notes
- `send_email` and `send_sms` are raw API wrappers. They send the moment they're called. The send-confirmation gate lives in SKILL.md and Cowork's explicit-permission rules, not in the Python.
- All four endpoints validated live against a real Lofty account before tagging. Two of the four (search_listings and create_task) only worked after the kit's reference docs were corrected against a known-working production implementation.

---

## [1.1.0] - 2026-05-07

Easy Mode setup for non-technical users.

### Added
- Easy Mode setup walkthrough as the default for non-technical users
- Conversational personal info collection (one short question at a time, no config-file vocabulary)
- Guided demo after setup completes (uses a real lead from the user's CRM, builds confidence immediately)
- Plain-English fallback messaging that points to the web app help section when stuck
- Power User Mode fast path triggered by phrases like "I'm technical" or "skip ahead"
- Exact Lofty API key navigation in the skill: profile picture top right, Personal Settings, Integrations, scroll to API Keys section at bottom, click "+ Create API Key"
- Branded web app at `docs/index.html` for hosting via GitHub Pages, with Saling Homes brand applied (Playfair Display + Nunito Sans, near-black + jewelry gold palette, 3-tone card rotation, EHO compliance footer)
- Silent OS detection during setup (Mac, Windows, Linux) so the skill picks the right Python command and file-open command without asking the user

### Changed
- SKILL.md rewritten to remove technical jargon from user-facing messaging (no more `.env`, `JWT`, "scripts folder," "config file")
- Default workspace folder is `~/Code/lofty-tools`, created automatically without explanation
- Setup confirms every Lofty write action regardless of mode (kept from v1.0)
- Python install fallback now opens python.org in the user's browser with a friendly walkthrough rather than failing
- Logo in the web app is the full Saling Homes wordmark with eXp Realty affiliation, sized for landscape lockup

### Fixed
- Removed em-dash characters across all skill files per brand guide
- Sanitized all references to internal Worker subdomains (now uses `<your-subdomain>` placeholders so the skill is shareable beyond Saling Homes)

---

## [1.0.0] - 2026-05-06

Initial public release.

### Added
- Starter Python client (`lofty_api.py`) covering authentication, rate limiting, leads, notes, and activities
- First-time setup walkthrough in the skill body
- Comprehensive guide (`references/full-guide.md`) covering setup, learning, and best practices
- Quirks reference (`references/quirks.md`) documenting all 14 known Lofty API quirks
- Workflow recipes (`references/workflows.md`) for common day-to-day tasks
- Extension guide (`references/extending.md`) for adding leads index, showings, MLS search, Cloudflare Workers
- Setup check script (`scripts/setup_check.py`) for verifying connection
- Cross-platform support: Mac (macOS 14+), Windows (10/11), Linux
- CLAUDE.md template for Cowork context customization
- `.env` template with all environment variables documented
