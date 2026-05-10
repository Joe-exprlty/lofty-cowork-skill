# Changelog

All notable changes to this skill will be documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). This project follows semantic versioning (MAJOR.MINOR.PATCH).

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
