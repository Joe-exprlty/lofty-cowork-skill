# Session Handoff: Phase 2

This file gets a new Claude Cowork session up to speed on the **Phase 2** build of the Lofty + Cowork skill project. Read this first, then explore the current files before doing anything.

---

## NEXT SESSION QUICK START

> Joe opened a new prompt and typed "Read Handoff.md and continue conversation." Follow this section to pick up exactly where we left off. Do NOT recap the prior session's work back to Joe; he was there. Get to the point.

**Where we left off (May 11, 2026 evening, second session):** v1.8.0 Stage C is fully SHIPPED to origin. The `schedule-showing` orchestration sub-skill is ported from `saling-automation` into `lofty-cowork-helper/skills/schedule-showing/SKILL.md`. All Joe-specifics stripped and replaced with workspace `CLAUDE.md` placeholders. SKILL.md trigger phrases, "How to start a session" routing, and file map all updated. `workflows.md` and `extending.md` get lead-in pointers to the sub-skill, with the existing primitive recipes preserved as manual fallbacks. The v1.7.0 and v1.8.0 commits and tags are all on origin.

Before v1.8.0 (still relevant context): v1.7.0 shipped the same day (Tier 3 SMS Worker with per-showing Durable Object alarms, 633ms E2E precision). v1.6.3 shipped earlier that day (housekeeping patch closing the v1.6.2 deferred list). Everything through v1.8.0 is on origin.

v1.6.3 (housekeeping patch, deleted the leftover `_tmp_worker_test.mjs` stub) and the v1.6.2 tag were both shipped earlier on 2026-05-11 and pushed to origin. Three deferred items from the v1.6.2 list remain intentionally in place per Joe's call: `HANDOFF.md`, `lofty-api-guide.md`, and `RESEARCH_NOTES_2026-05-07.md`.

Before v1.6.3 (still relevant context): v1.6.2 was a pure pre-public-release doc cleanup pass on top of v1.6.1. Pure doc drift fixes: broken file pointers in `CLAUDE.md.template`, "Tier 3 v1.6" stragglers in `SKILL.md` corrected to v1.7, Lofty API key path made consistent across `env-template`, `full-guide.md`, and the public `docs/index.html` GitHub Pages page, stale "starter does NOT include showing helpers" wording in `workflows.md`, five em-dashes scrubbed out of `workers_setup.md` per the brand rule, `README.md` repo-structure tree rewritten to reflect actual v1.6.1+ contents, and the `wrangler.jotform.toml` JOTFORM_FIELD_MAP comment block reframed to lead with the new working default. Existing v1.6.1 installs continue running without redeploy.

Before v1.6.2 (still relevant context): v1.6.1 fixed first-time-user papercuts surfaced by an end-to-end test of v1.6 Easy Mode against brand new Jotform and Cloudflare accounts. One real code fix (canonical `JOTFORM_FIELD_MAP` default in `wrangler.jotform.toml` so fresh template clones route qid 51 correctly; previously it was `"{}"` and `memory_notes` data dropped silently) plus `workers_dev`/`preview_urls` explicit toml settings plus a substantial doc rewrite covering MCP install prereq, Lofty API token retrieval, Cloudflare token Account/Zone Resources dropdowns, Jotform UI path updates, wrangler interactive prompts, workers.dev SSL cert propagation delay, and the Jotform UI webhook wiring fix.

Tier 3 SMS Worker (v1.7) and Stage C orchestration sub-skill (v1.8) are both DONE. The remaining ladder to v2.0.0 is Tier 3 polish: v1.9.0 (leads-index Worker, free tier, opt-in) and v1.9.1 (short-links Worker decision per locked decision #11).

**MCP STATE WARNING:** As of v1.6.1 ship time, Joe's Cloudflare MCP and Jotform MCP are connected to test accounts (`jsaling31@gmail.com`) rather than his production accounts. He opted to swap them back "later, when I get around to it." Before any MCP call against Cloudflare or Jotform, verify which account is connected. The memory file at `project_mcps_on_test_accounts.md` has the full state. Test-account artifacts left in place: Cloudflare Worker `jotform-to-lofty.jsaling31-test.workers.dev`, Jotform form `261294822008152`, and the `.test-v1.6/` scratch folder in the kit (gitignored).

**Do these checks silently first (do NOT narrate them to Joe):**

1. Verify `~/Code/saling-automation/` is mounted via `mcp__cowork__request_cowork_directory`. If not, request it.
2. Run `git log --oneline -5` on `~/Code/lofty-cowork-skill`. Confirm the most recent commit is the v1.8.0 ship commit (`8699ad8 v1.8.0: Stage C ships`) and the working tree is clean. Confirm `git ls-remote --tags origin` shows `v1.7.0` AND `v1.8.0`. If either tag is missing, ask Joe to push tags before doing anything else.
3. Run both `node lofty-cowork-helper/scripts/test_worker_parsers.mjs` and `node lofty-cowork-helper/scripts/test_showing_sms_worker.mjs`. Both should pass. This reassures you that nothing has rotted since v1.8.0 shipped.
4. Check MCP state: call `mcp__c55037a8-92bb-4dab-ab11-9e055ea57019__accounts_list`. If the result names `Jsaling31@gmail.com's Account`, the MCPs are still on the test accounts (per the MCP STATE WARNING above). Surface this to Joe in your first message if true. Worth noting: v1.9.0 deploy work touches Cloudflare directly, so the test-account-vs-production question matters more this session than it did for Stage C.
5. Read the "v1.9.0 plan: leads-index Worker" section below so you know what comes next.

**Then, as your FIRST user-facing message, do NOT ask Joe what to work on. The next step is already decided: v1.9.0, the leads-index Worker (free Cloudflare tier, opt-in). Lead with:**

> v1.8.0 Stage C is shipped. Next up is v1.9.0: the leads-index Worker port from saling-automation. Free Cloudflare tier, no Workers Paid needed. Ready to start the port?

Then proceed directly into the port work. The full plan is in the "v1.9.0 plan: leads-index Worker" section below.

If the MCP state check shows test accounts still connected, lead with: "Quick heads up before we start: your Cloudflare MCP is still on the test account from the v1.6.1 E2E session. v1.9.0 deploy work hits Cloudflare directly, so this matters more this session. Want to swap back to production first, or stay on test for the port + dry runs and swap before Layer 3 E2E?"

---

## v1.8.0 SHIPPED (2026-05-11 evening, second session)

Tag `v1.8.0` on local main, NOT YET PUSHED to origin as of this session. Stage C ships: the `schedule-showing` orchestration sub-skill. What landed:

- **`lofty-cowork-helper/skills/schedule-showing/SKILL.md`** ported from `~/Code/saling-automation/.claude/skills/schedule-showing/SKILL.md`. Every Joe-specific identifier stripped:
  - Name "Joe" (8+ uses) replaced with "the agent" or "the user" depending on context.
  - Brokerage "Saling Homes" removed from the description; replaced with "an existing Lofty client."
  - Email `joe@sellingpdxhomes.com` (the inline calendarId) replaced with a pointer to read the agent's email from the workspace `CLAUDE.md`.
  - Phone `503-910-7364` and the virtual signature removed.
  - Timezone hardcode `America/Los_Angeles` and offsets `-07:00`/`-08:00` reframed as examples; the workflow now reads the timezone from the workspace `CLAUDE.md` at run time.
  - Short-links domain `short-links.joe-2c5.workers.dev` replaced with a generic `<short-links-domain-or-direct-jotform-url>` placeholder in the reference return shape.
  - Example client and address strings (Tuhin Dey, the Smiths, the SW Buckhorn / SW Yarra tour) replaced with generic placeholders (Jane Smith, 1234 NW Main, 1500 NW Oak).
  - The 8-step workflow (resolve client, convert times, prepare each stop, confirm calendar handling, create events in parallel, post showing-log notes, verify SMS queue, report) is preserved end to end. Idempotency notes, common-failure tree, full `prepare_showing` return shape, and safety rules all carried over verbatim with placeholder substitutions only.
- **`lofty-cowork-helper/SKILL.md`** top-level description. Adds showing-orchestration trigger phrases to the trigger list (`"schedule a showing," "book a showing," "set up a tour," "tour [address] tomorrow," "schedule [client] at [address]"`).
- **`lofty-cowork-helper/SKILL.md`** "How to start a session" routing block. Adds a new case that routes orchestration triggers to the `skills/schedule-showing/` sub-skill, parallel to the existing Tier 2 and Tier 3 picker routes.
- **`lofty-cowork-helper/SKILL.md`** file map. Adds `skills/schedule-showing/SKILL.md` with a one-line description.
- **`lofty-cowork-helper/references/workflows.md`** "Schedule a showing (full flow)" section. Adds a lead-in pointer to the new sub-skill as the fastest path for the typical case; existing primitive recipe preserved below as the "manual fallback for debugging a partial run."
- **`lofty-cowork-helper/references/extending.md`** "Showing scheduling" section. Adds a one-paragraph pointer to the orchestration sub-skill at the top; existing primitive composition notes preserved below.
- **`CHANGELOG.md`** v1.8.0 entry.

**Verification ran after the port.** Zero em-dashes in the new sub-skill (0 matches). Zero Joe-specifics (0 matches for `joe`, `saling`, `sellingpdxhomes`, `503-910`, `exp realty`, `tuhin`, `buckhorn`, `yarra`, `joe-2c5`). The sub-skill is 198 lines (vs 190 in the source) because of the added Tier 3-optional notes and the calendar-provider routing reference.

**Layer 1 read-through review:** completed during the port. Side-by-side compare of the public-kit sub-skill against the saling-automation source confirmed the conversational flow is intact and no owner-specifics leaked through.

**Layer 2 dry-run chat test:** not yet run as of this session. Open for the next session if Joe wants stronger pre-push validation.

**Layer 3 E2E:** not yet run as of this session. Plan from the v1.7.0 ladder applies: one real showing scheduled end to end against Joe's own lead, using the v1.7.0 Tier 3 Worker.

**Push status:** v1.8.0 commit (`8699ad8`) and tag are on origin. v1.7.0 tag is also on origin. All shipped releases through v1.8.0 are pushed.

**Smoke tests:** Both `node lofty-cowork-helper/scripts/test_worker_parsers.mjs` and `node lofty-cowork-helper/scripts/test_showing_sms_worker.mjs` pass at v1.8.0 HEAD (no code paths touched by this release; the smoke tests are a defensive check).

---

## v1.7.0 SHIPPED (2026-05-11)

Tag `v1.7.0` on local main, NOT YET PUSHED to origin as of this session. Tier 3 ships. What landed:

- **`lofty-cowork-helper/workers/showing_sms_worker.js`** ported from the saling-automation production code. Joe-specifics stripped: hardcoded "Joe" in the SMS body now parameterized as `OWNER_FIRST_NAME` env var. Module-scope helpers refactored from inline blocks for test-lifting. DO alarm semantics, KV index shape, HTTP route surface byte-identical to production.
- **`lofty-cowork-helper/workers/wrangler.showing-sms.toml`** templated config. `workers_dev=true`, `preview_urls=false`. KV id placeholder. Append-only `[[migrations]]` block auto-creates the `ShowingTimer` Durable Object class on first deploy.
- **`lofty-cowork-helper/scripts/test_showing_sms_worker.mjs`** Layer 1 unit tests. 36 assertions covering auth, KV key shape, request validation, queue entry build, SMS body format. All passing.
- **`references/workers_setup.md`** Tier 3 setup section. ~180 lines parallel to Tier 2's structure. Includes a Step 0 in Easy Mode walkthrough that spells out how to open a terminal for non-developer users (Spotlight on macOS, Start menu on Windows).
- **`SKILL.md`** Tier 3 picker. Trigger phrases include "set up Tier 3," "deploy the SMS Worker," etc. Workers Paid prereq probe before routing to Easy or Power User Mode.
- **`CHANGELOG.md`** v1.7.0 entry.
- **`.gitignore`** adds `.test-v1.7/` and `.wrangler/`.

**Layer 3 E2E results (the v1.7.0 release gate):**

Deployed `showing-sms-staging` to Joe's production Cloudflare account as a separate Worker name. Created `SHOWING_SMS_QUEUE_STAGING` KV namespace. Pushed `LOFTY_API_KEY` secret. Enqueued a 90-second-out showing against Joe's own lead (`1142635515796067`).

Result: DO alarm fired at `sent_at: 2026-05-11T20:11:32.633Z` versus `send_at: 2026-05-11T20:11:32Z`. **633ms end-to-end precision.** Lofty accepted the SMS for delivery (`messageId: 223094189` for `phoneNumber: 5039107364`). SMS landed on Joe's real phone at 13:11 Pacific. KV audit row flipped from `pending` to `sent` with `sent_at`, `sent_to_phone`, and `sent_message` populated. `OWNER_FIRST_NAME="Joe"` flowed through the alarm() handler correctly.

Both staging artifacts (Worker `showing-sms-staging`, KV namespace `eb1f068d14af4e8789c498cbfddd3b3c`) torn down via `npx wrangler delete` and `npx wrangler kv namespace delete`. Joe's production `showing-sms` Worker untouched throughout.

**Saved feedback memory (2026-05-11):** Easy Mode walkthroughs for the lofty-cowork-skill must include explicit terminal-open instructions before any CLI step. Real estate agents often have never opened a terminal. Tier 3 walkthrough already has the Step 0. Tier 2 walkthrough does NOT yet; revisit at a future cleanup pass.

**Push status:** v1.7.0 commit (`e8b05dd`) and tag are on origin as of the v1.8.0 ship session.

**Smoke tests:** Both `node lofty-cowork-helper/scripts/test_worker_parsers.mjs` and `node lofty-cowork-helper/scripts/test_showing_sms_worker.mjs` pass at v1.7.0 HEAD.

---

## v1.6.3 SHIPPED (2026-05-11)

Tag `v1.6.3` on local main, NOT YET PUSHED to origin as of this session. Single-file housekeeping patch closing out the v1.6.2 deferred list. What landed:

- **Removed:** `lofty-cowork-helper/scripts/_tmp_worker_test.mjs`. The file had been trimmed to a 263-byte self-describing stub ("Stale scratch file from a prior session. Safe to delete; not loaded by anything.") in an earlier session. Deleting it now so the next `.skill` repackage does not pick up the dead path.
- **Local-only cleanup:** `lofty-cowork-helper/assets/__pycache__/lofty_api.cpython-310.pyc` and the empty `__pycache__/` dir removed from the working tree. The file was never tracked in git (`__pycache__/` has been in `.gitignore` since v1.0.0) but it existed on disk and would have been swept into the next `.skill` package.
- **Retroactive tagging:** The `v1.6.2` git tag was created on commit 21ffa14 (the actual v1.6.2 release commit). HANDOFF.md had claimed the tag was made at v1.6.2 ship time; it wasn't. Local-only at the moment, will go to origin together with v1.6.3.
- `CHANGELOG.md`: v1.6.3 entry added.

**Three v1.6.2 deferred items intentionally kept in place per Joe's call:**
- `HANDOFF.md` stays in the public repo. It doubles as the working brief for the next Claude session; the owner identity inside it is already public via `docs/index.html`.
- `lofty-api-guide.md` stays at the repo root. Duplication with `references/full-guide.md` etc. is documented but the file is not a hazard.
- `RESEARCH_NOTES_2026-05-07.md` stays at the repo root for the same reason.

**Push status:** v1.6.2 and v1.6.3 commits and tags are on origin as of post-v1.6.3 push.

**Smoke test:** `node lofty-cowork-helper/scripts/test_worker_parsers.mjs` still prints "All parser smoke tests passed." after the deletion. The Worker is byte-identical to v1.6.2.

---

## v1.6.2 SHIPPED (2026-05-10 evening)

Tag `v1.6.2` on origin/main. Pure pre-public-release doc cleanup pass. No code changes. No Worker changes. No schema changes. The skill triggers and the Worker behavior are byte-identical to v1.6.1. What landed:

- **`lofty-cowork-helper/assets/CLAUDE.md.template`:** "Where to look for detail" section pointed at `claude-cowork-lofty-guide.md` (no such file) and `lofty_api_starter.py` (real file is `lofty_api.py`). Both pointers fixed. List expanded to also surface `references/quirks.md`, `references/workflows.md`, and `references/extending.md` so fresh installs' CLAUDE.md tells Claude what is actually in the kit.
- **`lofty-cowork-helper/SKILL.md` lines 233 and 303:** still claimed Tier 3 ships in v1.6 after v1.6.1's pass missed these two instances. Both now say v1.7. Aligns SKILL.md with the workers_setup.md bottom-of-file note.
- **`lofty-cowork-helper/assets/env-template` line 12:** still pointed at "Settings -> API Keys" after v1.6.1's API key path consistency pass. Updated to "Settings -> Integrations -> API."
- **`lofty-cowork-helper/references/full-guide.md` line 115 (prereqs):** same fix.
- **`docs/index.html` line 633 (public GitHub Pages landing page):** still told users to "click your profile picture top right, click Personal Settings, then Integrations. Scroll all the way down. If you see an 'API Keys' section..." This was the worst single contradiction in the repo because it is the first page brand-new users land on. Updated to the current path.
- **`lofty-cowork-helper/references/workflows.md` lines 64-78:** still said "the starter does NOT include showing helpers; see extending.md." Showing helpers have been in the starter since v1.3.0. Rewrote the lead-in to reflect that only the showing-sms Worker (Tier 3, v1.7) requires additional setup.
- **`lofty-cowork-helper/references/workers_setup.md` (lines 16, 87, 134, 151, 155):** removed five em-dash characters that crept in with v1.6 / v1.6.1's new content. v1.1.0 originally scrubbed em-dashes across the skill per the brand rule; the rule was not enforced on the v1.6 additions. Verified that none of the removed em-dashes were in file paths, variable names, env vars, config keys, JSON keys, URLs, or any code that does string matching. Two of the five were inside quoted Jotform UI taglines ("Share a link, I'll turn it into a form") which appear only in prose.
- **`README.md` lines 13-31:** repo-structure tree listed only `SKILL.md`, `scripts/setup_check.py`, `references/`, and `assets/`. Rewrote to reflect the actual v1.6.1+ contents: adds `workers/` and `workers/migrations/`, the additional `scripts/` entries, the additional `references/` entries (`workers_setup.md`, `calendar_routing.md`), the additional `assets/` entries (`ics_builder.py`, `post_showing_questions.yaml`, `jotform_form_template.md`), and the top-level `CHANGELOG.md`.
- **`lofty-cowork-helper/workers/wrangler.jotform.toml` lines 79-90:** JOTFORM_FIELD_MAP comment block still described the pre-v1.6.1 "empty default, alias fallback" framing as the working state. Rewrote to lead with the new working default and frame the empty-map / alias-fallback path as the override case. Actual `JOTFORM_FIELD_MAP` value on line 97 is unchanged. Pure comment refresh.
- **`CHANGELOG.md`:** v1.6.2 entry added.

**Verification grep ran after the edits.** Zero em-dashes in `lofty-cowork-helper/`. Zero "API Keys section" or "Personal Settings" wording in user-facing docs (the one remaining instance in `CHANGELOG.md` is the v1.1.0 historical entry and intentionally preserved). Zero "Tier 3 ... v1.6" claims. Zero broken file pointers. Zero "starter does NOT include showing helpers" wording.

**Deferred from this pass (open for the next session):**
- `HANDOFF.md` placement decision: this file contains owner-specific identity (Joe's name, email, phone, Cloudflare account ID) and brand-voice rules. Two options: move to a `.private/` folder before packaging, or add to `.gitignore` so it stays on Joe's machine. Joe opted to keep it for now since it is also the working brief for the next Claude session.
- `lofty-api-guide.md` at the repo root: a ~605-line standalone field manual that duplicates `references/full-guide.md`, `references/quirks.md`, and `references/extending.md`. Grep returns zero internal references. Likely a leftover from an earlier release. Move to `_archive/` or delete.
- `lofty-cowork-helper/scripts/_tmp_worker_test.mjs`: looks like a leftover scratch file from worker parser testing. Probably should not ship in the `.skill` package. Delete or move.
- `lofty-cowork-helper/assets/__pycache__/lofty_api.cpython-310.pyc`: Python bytecode cache. Add to `.gitignore` if not already there.

---

## v1.6.1 SHIPPED (2026-05-10 evening)

Tag `v1.6.1` on origin/main. Patch release surfaced by an end-to-end test of v1.6 Easy Mode against brand new Jotform and Cloudflare accounts. What landed:

- **Code fix:** `lofty-cowork-helper/workers/wrangler.jotform.toml` ships the canonical `JOTFORM_FIELD_MAP` as the default value of the `JOTFORM_FIELD_MAP` env var (was `"{}"`). Critical because the public template (form `261294238566162`) uses Jotform's auto-generated unique name `anythingElse` for qid 51, and the alias-fallback path in the Worker doesn't match it, so qid 51 buyer-typed memory notes would land in the wrong place on a fresh clone. With the canonical map shipped as default, qid 51 routes correctly to the `memory_notes` D1 column without any per-install configuration.
- **Code/security fix:** `lofty-cowork-helper/workers/wrangler.jotform.toml` explicitly sets `workers_dev = true` and `preview_urls = false` at the top level. Silences wrangler 4.x default warnings and closes a real attack surface (preview URLs default-on would expose a publicly accessible Worker version holding `LOFTY_API_KEY`).
- **Doc rewrite:** `lofty-cowork-helper/references/workers_setup.md`. New prereqs covering MCP install (Cloudflare + Jotform from Customize → Connectors), Lofty API token retrieval (path corrected to `Settings → Integrations → API` per `api.lofty.com/docs`), Cloudflare token Account/Zone Resources dropdowns required on zoneless accounts, and Jotform signup gotchas (`?onboardingPrompt=1` URL param, "SAVE 50%" upsell banner, "Jotform for Claude" promo card). Easy Mode steps 2, 7, 8, 9, 10, 11 all rewritten. Power User Mode Jotform path updated. Bottom-of-file Tier 3 version corrected from v1.6 to v1.7.
- **Doc rewrite:** Easy Mode step 9 webhook wiring rewritten end to end. The Jotform MCP cannot configure webhooks (its `edit_form` only handles question/field-level edits). Users now wire webhooks manually via Jotform UI: Form Builder → SETTINGS → Integrations → Webhooks → paste Worker URL → Complete Integration.
- **Doc fix:** Lofty API token path corrected in three locations in `SKILL.md` and one in `references/full-guide.md` to match `api.lofty.com/docs`.
- **Easy Mode step 7 optimization:** `LOFTY_API_KEY` is now auto-piped from `.env` via `grep | cut | tr | wrangler secret put`, eliminating manual paste.
- `CHANGELOG.md` v1.6.1 entry.

**Verified end-to-end:** Tested against brand new Jotform account, brand new Cloudflare account, real Lofty (Jack Ryan, `lead_id 1146742878287627`). D1 row landed with all columns populated correctly including `memory_notes`. Lofty note delivered with full formatting. Recap email delivered to jsaling31@hotmail.com via Lofty `send_email` fallback path.

**Test artifacts NOT torn down per Joe's choice:**
- Cloudflare test account `b04007e6828b36bea0360850eca935ce`: Worker `jotform-to-lofty.jsaling31-test.workers.dev` still deployed (D1 deleted; subdomain `jsaling31-test` is permanent on the account).
- Jotform test account: form `261294822008152` still in place.
- Local: `/Users/joesaling/Code/lofty-cowork-skill/.test-v1.6/` (gitignored).
- Cloudflare MCP and Jotform MCP still connected to the test accounts. Joe to swap back at his convenience.

**Cloudflare API token leak:** during the test, the Cloudflare API token Joe generated for the test account was inadvertently pasted into chat. Joe was advised to revoke from the Cloudflare dashboard when finished with the test account. Treat that token as compromised.

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

## Roadmap from v1.7.0 to v2.0.0

The order below is dependency-respecting and leverage-maximizing. Reasoning, not just version numbers, is what matters; the version labels are placeholders. Tier 3 SMS Worker (the previous v1.7 ladder headline) is DONE; it shipped as v1.7.0 on 2026-05-11.

### v1.8.0: Stage C, the `schedule-showing` orchestration sub-skill (DONE)

Shipped 2026-05-11 evening (second session), now on origin. Turned the kit from "all the primitives are here, ask Claude to wire them" into "describe what you want in one chat sentence and it happens." Full notes in the "v1.8.0 SHIPPED" section above.

### v1.9.0: `leads-index` Worker (free tier, opt-in) (NEXT)

Adds `get_all_leads_by_visit` (deprecated forwarder) and `get_recent_visits_from_index` to the public kit's `lofty_api.py`. Note: both methods already exist in the public kit's `lofty_api.py` as of v1.3.0+; what's missing is the Worker that backs them when `LOFTY_LEADS_INDEX_SOURCE=worker` is set. Source: `~/Code/saling-automation/worker/leads_index_worker.js` (production) and `worker/leads_index_worker.v2_draft.js` (newer draft, evaluate which to port).

Free Cloudflare tier covers it (no Workers Paid needed; that's Tier 3 only per locked decision #10). Depends on: nothing functional. The file-fallback in `find_client` continues to work for installs that skip this Worker. This is polish for agents with large CRMs (>10k leads).

Full working brief in the "v1.9.0 plan: leads-index Worker" section below.

Optional skip path: jump straight to a v2.0.0 packaging audit. If Stage C real-user usage suggests file-fallback name lookup is fine for small/medium CRMs, the leads-index Worker can stay parked indefinitely without blocking the public release. Confirm with Joe before starting v1.9.0.

### v1.9.x: Standalone niche methods in `lofty_api.py` (bundle if any are touched during v1.9.0 port)

Nine `lofty_api.py` methods present in production but missing from the public kit:
- Utility helpers: `epoch_ms_to_dt`, `parse_time`
- Niche capability: `assign_lead`, `delete_lead`, `generate_call_script`, `get_lead_analysis`, `summarize_activities`
- Already in the kit, but `LOFTY_LEADS_INDEX_SOURCE=worker` mode untested without the Worker: `get_all_leads_by_visit`, `get_recent_visits_from_index`

If v1.9.0 needs any of these during the port, bundle directly rather than holding for a separate patch.

### v1.9.1 or later: Decide on `short-links` Worker

Locked decision #11 flagged this as a candidate to cut. Three options at this checkpoint: port it, formally remove it from the roadmap, or keep it parked. Defer the decision until after Stage C and leads-index ship.

### v2.0.0: First major public release

Feature parity with Joe's production reached. Announce on the GitHub Pages page, package the `.skill`, get the 25-minute realtor talk on the calendar, point Joe's network at it. The "v1.x → v2.0.0" jump signals "the kit is what Joe runs daily, you can run it too."

---

## v1.9.0 plan: `leads-index` Worker (free Cloudflare tier, opt-in)

This is the working brief for the next session. Read this section + the "Recommended order" at the bottom, then start the port.

### What the leads-index Worker does

It keeps a live mirror of the agent's Lofty leads inside Cloudflare KV, updated via Lofty webhook list 2 (Lead Info: create/update/delete). The Python client reads from KV instead of polling Lofty's broken `/v1.0/leads` endpoint (which silently ignores `keyword` and `sortField` query parameters, confirmed by direct probe 2026-04-21). Result: `find_client` and `get_recent_visits_from_index` stay fast and accurate even for agents with 10k+ leads, with no polling and no quota burn.

The Python side is already wired. `lofty_api.py` has `get_recent_visits_from_index` (the primary method) and `get_all_leads_by_visit` (deprecated forwarder). Both already respect the `LOFTY_LEADS_INDEX_SOURCE` env var: `worker` reads from the Cloudflare Worker's `/export` endpoint; anything else (default) reads from the local `data/leads_index.json` file built by `scripts/refresh_leads_index.py`. So when the Worker is deployed and `LOFTY_LEADS_INDEX_SOURCE=worker` is set, the Python automatically switches.

### Source files in saling-automation

- `~/Code/saling-automation/worker/leads_index_worker.js` (production, 16,683 bytes, last touched 2026-04-22). The version that runs in production today. Webhook receiver + KV write path + `/export`, `/lead/<id>`, `/bulk-import`, `/stats`, `/` health-check routes. Auth: bearer token on read/write endpoints; secret in path for the webhook receiver.
- `~/Code/saling-automation/worker/leads_index_worker.v2_draft.js` (newer draft, 16,267 bytes, last touched 2026-04-24). Evaluate during the port whether the v2 draft is the better starting point or whether production is the right canonical source.
- `~/Code/saling-automation/worker/wrangler.toml` (or whichever wrangler config currently deploys leads-index in production). Templatize KV namespace id, account id, and any other deploy-specific values.
- `~/Code/saling-automation/scripts/refresh_leads_index.py`. Already exists in the public kit at `lofty-cowork-helper/scripts/refresh_leads_index.py`; confirm it's still byte-compatible with the v1.9.0 Worker's `/bulk-import` shape.
- `~/Code/saling-automation/scripts/lofty_api.py` `_load_leads_index`, `_load_leads_index_from_worker`, `_load_leads_index_from_file` methods. Confirm parity with the public kit's `lofty_api.py`.

### Port checklist (parallel to Tier 2 / Tier 3 port pattern)

1. **Decide which source variant to port.** Read both `leads_index_worker.js` and `leads_index_worker.v2_draft.js` end to end. Confirm with Joe at port start which one to use as the canonical source for the public kit. Defaults to production unless v2 has a clear UX or correctness improvement.
2. **Read the chosen source end to end.** Catalogue every Joe-specific identifier: account ID `22c50f7ac3f85d789dfec570642ae9af`, KV namespace id, the `leads-index.joe-2c5.workers.dev` subdomain, any hardcoded `OWNER_*` strings, the production webhook secret, the production `EXPORT_API_KEY` value.
3. **Create `lofty-cowork-helper/workers/leads_index_worker.js`** in the public kit. Strip Joe-specifics. Parameterize webhook secret and `EXPORT_API_KEY` to env vars (set by `wrangler secret put`). Use the same Module-scope helper extraction pattern that v1.7 used so the lifted helpers can be unit-tested.
4. **Create `lofty-cowork-helper/workers/wrangler.leads-index.toml`** templated config. `workers_dev = true`, `preview_urls = false` (same security posture as Tier 2 and Tier 3). KV namespace id is a placeholder (`REPLACE_WITH_YOUR_LEADS_INDEX_KV_ID`). No Durable Object class needed (this is a free-tier Worker). Webhook secret and `EXPORT_API_KEY` are `wrangler secret put` values, NOT in the toml.
5. **Create `lofty-cowork-helper/scripts/test_leads_index_worker.mjs`** Layer 1 unit tests. Parallel to the Tier 2 (`test_worker_parsers.mjs`) and Tier 3 (`test_showing_sms_worker.mjs`) test files. Cover: webhook receiver (auth via path-embedded secret, payload normalization, KV write), `/export` (bearer auth, full-index serialization, ids-meta freshness), `/lead/<id>` (bearer auth, single-record read, 404 path), `/bulk-import` (bearer auth, replace semantics, ids-meta rebuild), `/stats` (no auth, counters), `/` health-check. Run in plain Node, no Cloudflare account, no network.
6. **Add a Tier 4 setup section in `references/workers_setup.md`** parallel to Tier 2 and Tier 3 structure: prereqs, test pyramid, Easy Mode walkthrough (10 steps or so, includes the Step 0 terminal-open guidance per v1.7 feedback memory), Power User Mode walkthrough (same steps with explicit shell commands), common errors, roll-back recipe. Webhook wire-up step needs Lofty UI guidance: Settings → API → Webhooks → list 2 → POST to `<your-worker>/webhook/<secret>`. The bootstrap step needs to run `python3 scripts/refresh_leads_index.py` to do the initial bulk-import from the file fallback.
7. **Add a Tier 4 picker to `lofty-cowork-helper/SKILL.md`** parallel to Tier 2 and Tier 3 pickers. Triggers on "set up Tier 4," "deploy the leads-index Worker," "set up live leads index," "wire up the leads-index Worker." Prereq probe (Tier 1 done, Cloudflare MCP optional, Lofty plan has webhook access). Routes to Easy Mode or Power User Mode.
8. **Update top-level `SKILL.md` description** with Tier 4 trigger phrases. Same pattern v1.7 used.
9. **Update `references/extending.md`** Cloudflare Workers section to reflect leads-index as a v1.9.0 shipping item rather than "still optional."
10. **`.gitignore`** add `.test-v1.9/` for Layer 3 E2E scratch.
11. **`CHANGELOG.md`** v1.9.0 entry.
12. **`HANDOFF.md`** updates (v1.9.0 SHIPPED section, status snapshot, stage status).

### Test approach for v1.9.0

The Worker has more deterministic logic than the orchestration sub-skill but less than the SMS Worker (no Durable Objects, no alarm semantics). Test pyramid:

- **Layer 1: unit tests.** `test_leads_index_worker.mjs`. Lift module-scope helpers from the Worker source via the same string-replacement trick `test_worker_parsers.mjs` and `test_showing_sms_worker.mjs` already use. Cover the seven routes plus auth + normalization + KV index meta updates.
- **Layer 2: deploy + smoke test in isolation.** Deploy to `leads-index-staging` on Joe's production Cloudflare account (separate Worker name, separate `LEADS_INDEX_STAGING` KV namespace). Hit each HTTP route with `curl`. Confirm webhook receiver, `/export`, `/lead/<id>`, `/bulk-import`, `/stats`, `/` all behave as expected. Tear down after.
- **Layer 3: E2E with real Lofty webhook.** Wire Lofty webhook list 2 at Joe's actual account to a `leads-index-staging-e2e` Worker. Update a lead in Lofty (change stage, update phone). Watch the webhook fire and the KV row update. Confirm `api.find_client` with `LOFTY_LEADS_INDEX_SOURCE=worker` sees the change end to end. Tear down after.

### Recommended order for the v1.9.0 session

1. Read this section.
2. Verify `~/Code/saling-automation/` is mounted (the source of truth).
3. Read both `leads_index_worker.js` and `leads_index_worker.v2_draft.js`. Confirm with Joe which one to use as canonical.
4. Port + strip + parameterize the Worker, the wrangler config, and the unit tests.
5. Add Tier 4 setup section to `references/workers_setup.md`.
6. Add Tier 4 picker to `SKILL.md` and update the top-level description.
7. Update `references/extending.md`, `CHANGELOG.md`, `HANDOFF.md`.
8. Layer 1 unit tests must pass before any deploy.
9. Layer 2 isolated staging deploy + smoke test.
10. Layer 3 E2E against Joe's actual Lofty webhook list 2 (this is where the test-vs-production MCP decision matters).
11. Tear down staging artifacts.
12. Commit, tag v1.9.0, Joe pushes.

### Open questions to resolve at port start

1. **Which source variant?** Production (`leads_index_worker.js`) vs draft (`leads_index_worker.v2_draft.js`). Read both before deciding.
2. **Webhook secret rotation strategy.** Production uses a fixed secret in the path. For the public kit, decide whether the Easy Mode walkthrough generates a fresh secret at install time and stores it, or whether the user supplies their own.
3. **Test-vs-production MCP.** Layer 2 staging can run on the test account (`Jsaling31@gmail.com`). Layer 3 needs Joe's production Lofty account because webhook list 2 fires against the real lead database. Plan the swap to production accounts before Layer 3, then back to test if Joe prefers.
4. **MLS code interaction.** None expected; the Worker doesn't care about MLS codes. Flag if anything surfaces during the read-through.

---

---

## Status snapshot (May 11, 2026 evening, post-v1.8.0 ship)

- **v1.8.0 SHIPPED to origin.** Commit `8699ad8` and tag on origin/main. Stage C ships: the `schedule-showing` orchestration sub-skill at `lofty-cowork-helper/skills/schedule-showing/SKILL.md`. Joe-specifics stripped, all references parameterized via the workspace `CLAUDE.md`. SKILL.md trigger phrases, routing block, and file map updated. `workflows.md` and `extending.md` get lead-in pointers; existing primitive recipes preserved as manual fallbacks. Closes the 25-point UX gap between the public kit and Joe's daily workflow. No new infrastructure, no new dependencies.
- **v1.7.0 SHIPPED to origin.** Commit `e8b05dd` and tag on origin/main. Tier 3 SMS Worker (`showing-sms`) with per-showing Durable Object alarms. Layer 3 E2E pass clean (633ms end-to-end precision, real SMS delivered to maintainer's phone). Adds ~620 lines across Worker, wrangler config, unit tests, Tier 3 walkthrough, and SKILL.md picker. Requires Cloudflare Workers Paid plan for installs.
- **v1.6.3 SHIPPED.** Tag pushed to origin. Single-file housekeeping patch removing the leftover `_tmp_worker_test.mjs` stub. Retroactively created the `v1.6.2` tag in the same session.
- **v1.6.2 SHIPPED.** Tag pushed to origin. Pre-public-release doc cleanup pass. Pure doc edits, zero code or schema changes. Broken file pointers in `CLAUDE.md.template` fixed, "Tier 3 v1.6" stragglers in `SKILL.md` corrected to v1.7, Lofty API key path made consistent across `env-template`, `full-guide.md`, and the public `docs/index.html` page, stale "starter does NOT include showing helpers" wording in `workflows.md` rewritten, five em-dashes scrubbed from `workers_setup.md`, `README.md` repo-structure tree rewritten to reflect actual v1.6.1+ contents, `wrangler.jotform.toml` JOTFORM_FIELD_MAP comment reframed.
- **v1.6.1 SHIPPED.** Tag on origin/main. Patch release fixing the first-time-user papercuts that v1.6 Easy Mode E2E testing surfaced. Canonical `JOTFORM_FIELD_MAP` default in toml; `workers_dev`/`preview_urls` pinned; doc rewrites covering MCP install, Lofty API token path, Cloudflare token dropdown gotchas, Jotform UI path updates, wrangler interactive prompts, SSL cert delay, and webhook UI path. Verified end-to-end against brand new accounts.
- **v1.6.0 SHIPPED.** Template-clone path live. Public template form `261294238566162` published in Joe's Jotform account with Prevent Cloning OFF.
- Phase 2 Stage A is COMPLETE through v1.4.1. Showing primitives, leads index, post-showing question pack, full read coverage of the API surface, Content-Type bug fix, find_client fallback for unsynced contacts.
- Phase 2 Stage B v1.5 is COMPLETE. Tier 2 jotform-to-lofty Worker + D1 + Easy Mode picker shipped. Joe's production is on it.
- Phase 2 Stage B v1.6 / v1.6.1 is COMPLETE. Template-clone path live AND verified end-to-end against fresh accounts. Tier 3 SMS Worker portion did NOT ship; it remains the headline item for the next ladder.
- Phase 2 Stage B v1.7 is COMPLETE through v1.7.0. Tier 3 SMS Worker shipped 2026-05-11. Tier 3 polish (leads-index Worker, short-links Worker) is the v1.9.x ladder.
- Phase 2 Stage C is COMPLETE through v1.8.0. `schedule-showing` orchestration sub-skill shipped 2026-05-11 evening.
- Phase 2 onboarding step for the orchestration sub-skill in Easy Mode is NOT STARTED (still NOT-STARTED for v2.0.0 packaging).

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

### Stage C v1.8.0: COMPLETE (shipped 2026-05-11 evening, pushed to origin). Schedule-showing orchestration sub-skill ported from saling-automation. Joe-specifics stripped, parameterized via workspace `CLAUDE.md`. SKILL.md trigger phrases, routing block, file map updated. `workflows.md` and `extending.md` get lead-in pointers; primitive recipes preserved as manual fallbacks. The 25-point UX gap between the public kit and Joe's daily workflow is closed. No new infrastructure, no new dependencies.

### Stage B v1.7.0: COMPLETE (shipped 2026-05-11, pushed to origin). Tier 3 SMS Worker (`showing-sms`) with per-showing Durable Object alarms. Layer 3 E2E pass clean (633ms precision, real SMS delivered). The headline functional jump for the public kit is now closed; Tier 3 polish (leads-index in v1.9.0, short-links decision in v1.9.1) is opt-in.

### Stage B v1.6.3: COMPLETE (shipped 2026-05-11 as v1.6.3, pushed to origin). Housekeeping patch closing out the v1.6.2 deferred list. `_tmp_worker_test.mjs` deleted. `__pycache__/.pyc` removed from disk. `v1.6.2` tag retroactively created on commit 21ffa14. Three deferred items (HANDOFF.md, lofty-api-guide.md, RESEARCH_NOTES_2026-05-07.md) intentionally kept in place per Joe's call.

### Stage B v1.6.2: COMPLETE (shipped 2026-05-10 evening as v1.6.2). Pre-public-release doc cleanup pass. Pure doc edits, zero code or schema changes.

### Stage B v1.6.1: COMPLETE (shipped 2026-05-10 evening as v1.6.1). Template-clone path live AND verified end-to-end against fresh accounts. Tier 3 SMS Worker NOT included; remains pinned for v1.7.

v1.6.1 patches the first-time-user papercuts that surfaced during the E2E test. `JOTFORM_FIELD_MAP` default now canonical in `wrangler.jotform.toml`. `workers_dev` / `preview_urls` pinned. Doc rewrites cover MCP install prereq, Lofty API token path (`Settings → Integrations → API` per Lofty docs), Cloudflare token dropdowns on zoneless accounts, Jotform UI path update (`+ CREATE → Import form → Import from URL`), wrangler interactive prompts (create-Worker, register-subdomain), workers.dev SSL cert propagation delay, and Jotform UI webhook wiring (Jotform MCP `edit_form` cannot configure webhooks).

### Stage B v1.6: COMPLETE (shipped 2026-05-10 as v1.6.0) for the template-clone path.

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
- **Production reference:** `/Users/joesaling/Code/saling-automation/` (mounted; grant via `mcp__cowork__request_cowork_directory` if missing).
- **Public web page source:** `docs/index.html`
- **Recipient-facing docs:** `INSTALL.md`, `README.md`, `LICENSE`, `CHANGELOG.md`
- **Distributor docs:** `PACKAGING.md`
- **References:** `lofty-cowork-helper/references/{full-guide,quirks,workflows,extending,calendar_routing,workers_setup}.md`
- **Assets:** `lofty-cowork-helper/assets/{lofty_api.py,env-template,CLAUDE.md.template,ics_builder.py,post_showing_questions.yaml,jotform_form_template.md}`
- **Scripts:** `lofty-cowork-helper/scripts/{setup_check.py,refresh_leads_index.py,test_v1_2_methods.py,test_v1_3_methods.py,test_worker_parsers.mjs,test_showing_sms_worker.mjs}`
- **Workers:** `lofty-cowork-helper/workers/{jotform_to_lofty_worker.js,showing_sms_worker.js,wrangler.jotform.toml,wrangler.showing-sms.toml,migrations/001_showing_feedback.sql}`
- **Sub-skills:** `lofty-cowork-helper/skills/schedule-showing/SKILL.md` (v1.8.0, orchestration sub-skill)
- **v1.9.0 will add:** `lofty-cowork-helper/workers/leads_index_worker.js`, `lofty-cowork-helper/workers/wrangler.leads-index.toml`, `lofty-cowork-helper/scripts/test_leads_index_worker.mjs`, plus a Tier 4 section in `references/workers_setup.md` and a Tier 4 picker in `SKILL.md`.
- **Packaged skill file:** `/Users/joesaling/Code/lofty-cowork-skill/lofty-cowork-helper.skill` (gitignored). Repackaged at each release.
- **Repackage command:** `cd /sessions/<your-session>/mnt/.claude/skills/skill-creator && python3 -m scripts.package_skill /sessions/<your-session>/mnt/lofty-cowork-skill/lofty-cowork-helper /sessions/<your-session>/mnt/lofty-cowork-skill`

`calendar_routing.md` and `ics_builder.py` exist but are demoted per locked decision #6.

---

## Outstanding decisions

1. **`HANDOFF.md` placement (DEFERRED).** This file is in the public repo. It contains owner identity (Joe's name, email, phone, Cloudflare account ID `22c50f7ac3f85d789dfec570642ae9af`, production D1 id `2d6dd086-c086-457c-a03e-11500da56f08`, production Worker subdomain `joe-2c5`), brand voice rules, and explicit instructions for the next Claude session. Per locked decision #1 the public skill is supposed to be a pure template, so HANDOFF.md technically violates that. Joe opted to keep it as-is for now (working brief for the next session). Revisit any time.
2. **`lofty-api-guide.md` at the repo root (DEFERRED).** A ~605-line standalone field manual that heavily duplicates `references/full-guide.md`, `references/quirks.md`, and `references/extending.md`. Grep returns zero internal references. Joe opted to leave it in place. Revisit any time.
3. **`RESEARCH_NOTES_2026-05-07.md` at the repo root (DEFERRED).** May 7 deep-probe working brief, ~14KB. Same family as `lofty-api-guide.md`. Joe opted to leave it in place. Revisit any time.
4. **`v1.4.1` git tag.** Commit `f027a87` was on origin/main but no tag was created at v1.4.1 ship time. If Joe wants release-tag parity with v1.4.0, tag it. Otherwise skip.
5. **Cut the short-links Worker from the public skill?** Locked decision #11 flagged this for investigation. Pinned to the v1.9.1 ladder; resolve after v1.9.0 ships.
6. **Slide deck for Joe's realtor talk.** Joe was building a 12-slide deck in Claude Design at `claude.ai/design`, project name "Lofty + Claude for Realtors - 25 min Talk." Verify state separately from engineering work.
7. **Lofty API key rotation.** Hold until Phase 2 is fully deployed so it's a single rotation pass.
8. **Duplicate uppercase-V tags on origin.** `git fetch` after the v1.8.0 push surfaced `V1.6.2` and `V1.6.3` (capital V) as separate tags alongside the lowercase ones. Likely a GitHub Desktop artifact. One-line patch sometime to delete the uppercase variants.

**RESOLVED in v1.6.3:** `_tmp_worker_test.mjs` deleted. `__pycache__/.pyc` deleted from disk. v1.6.2 tag created retroactively (now pushed to origin as of the v1.8.0 ship session).

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
- v1.7 ship: SMS feedback texts route through Lofty's SMS endpoint (already covered) but the showing-sms Worker schedule queue runs on Cloudflare KV + Durable Objects. No new third parties.
- v1.9 ship: leads-index Worker reads webhook events from Lofty and stores them in Cloudflare KV. Same providers; the lead-data flow direction is new (Lofty pushes to Cloudflare KV on update). If short-links Worker ships at v1.9.1, the redirector domain becomes a new visible touchpoint for buyers.

---

## Joe's contact

Joe Saling, Saling Homes at eXp Realty, 503-910-7364, joe@sellingpdxhomes.com, www.sellingpdxhomes.com.

These details belong in HANDOFF.md and `docs/index.html` ONLY. Not in the public template.

---

## Recommended order for the next session

1. Read this HANDOFF.md (you're doing it now).
2. Verify the production reference is mounted and the public skill working tree is clean (silent checks per the QUICK START). Latest tag should be `v1.8.0`.
3. Run both smoke tests to confirm nothing has rotted: `node lofty-cowork-helper/scripts/test_worker_parsers.mjs` and `node lofty-cowork-helper/scripts/test_showing_sms_worker.mjs`. Both should pass cleanly.
4. The next step is v1.9.0 (leads-index Worker). Lead with the QUICK START's first user-facing message and proceed directly to the v1.9.0 plan section below.
5. Optional skip path: if Joe wants v2.0.0 sooner, park v1.9.0 and start a packaging audit instead. Confirm with Joe before deviating from the v1.9.0 plan.
6. When porting code: use the Cloudflare MCP for read-only inspection during development; reserve `wrangler` for actual deploys and `wrangler secret put`. Note the MCP state warning at the top of QUICK START; the test-vs-production swap matters more for v1.9.0 than it did for v1.8.0 because Layer 3 E2E hits Lofty webhook list 2 at the real account.

Do NOT delete this HANDOFF.md until Phase 2 is finished and shipped. Joe wants it kept as the working brief. The decision about how to keep HANDOFF.md OUT of the public package is Outstanding decision #1.
