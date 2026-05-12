# Lofty Cowork Skill: Roadmap

This file is the working brief for what comes after v1.9.0. It's specific, scoped, and dated. Each version below has a goal, a what-ships list, a done-criteria checklist, and a time estimate. Two pinned guarantees: (a) every version has a clear stopping point, (b) anything deferred lives in the "v2.1 and later" section so it doesn't bloat the next release.

For new Claude sessions: this file is the source of truth for "what's next." If it conflicts with HANDOFF.md, this file wins. Update HANDOFF.md when a version ships, but check here first for the plan.

---

## Status snapshot (as of v1.9.0 ship, 2026-05-12 evening)

Shipped:

- **Tier 1 (v1.0 through v1.4.1):** Python client with full read+write coverage of Lofty's working API surface. Local-file leads index. Showing primitives. find_client live-scan fallback.
- **Tier 2 (v1.5 through v1.6.3):** `jotform-to-lofty` Worker with D1 backend for post-showing feedback. Template-clone path for the Jotform form. Easy Mode + Power User Mode walkthroughs.
- **Tier 3 (v1.7.0):** `showing-sms` Worker with per-showing Durable Object alarms. Requires Workers Paid ($5/mo).
- **Stage C (v1.8.0):** `schedule-showing` orchestration sub-skill that drives multi-stop tour scheduling in one chat sentence.
- **Tier 4 (v1.9.0):** `leads-index` Worker, webhook-fed live KV mirror. Free Cloudflare tier. `flattenLoftyPayload` handles Lofty's plural-array webhook payload shape (discovered during Layer 3 E2E).

Production-side cleanup also landed in this session (not part of the public kit but worth noting): Joe's production `saling-automation/worker/leads_index_worker.js` is now on v2 logic with the parser fix. It was silently dropping every webhook event since April 22.

What remains before v2.0.0:

- **v1.10.0:** Refresh architecture for non-tech users. The Tier 1 leads index needs to stay current without an agent ever opening a terminal. Daily incremental + weekly full reconciliation, both driven by Cowork scheduled tasks. This is the work that makes the kit genuinely shareable to non-tech agents.
- **v2.0.0:** Public release packaging. Bloat audit on SKILL.md, landing-page rewrite, Easy Mode polish, kit health check.

---

## v1.10.0: hands-off leads index for non-tech users

### Goal

After v1.10.0 ships, a non-tech real estate agent can install the kit, never open a terminal, and have their leads index stay current within 24 hours of any change in Lofty (new leads, deletions, updates) without thinking about it.

### Why this is the right next release

The kit's value to non-tech agents is the conversational layer (Tier 1 + the `schedule-showing` sub-skill). The leads index is invisible infrastructure they shouldn't have to think about. Today, agents have to manually run `refresh_leads_index.py` every couple of weeks, which non-tech users will never do. v1.10.0 closes that gap with scheduled tasks.

This unblocks v2.0.0 packaging because we can honestly tell non-tech agents "the index stays current automatically." Without this, the public README has to qualify Tier 1 with "you'll need to remember to refresh occasionally," which undermines the pitch.

### What ships

Code:

- **`scripts/refresh_leads_index.py` gets two new modes.**
  - `--incremental` mode. Reads the local file's known leadId set. Fetches page 1 of `/v1.0/leads`. Adds any new leadIds to the file. Reads `_metadata.total`. If Lofty's total has dropped below `local_count + new_count`, returns an exit code that signals "escalate to full scan." Fits inside Cowork's 45-second bash timeout. Wall time: 1-15 seconds depending on how many new leads to ingest.
  - `--full --resumable` mode. Replacement for the current full-scan mode. Checkpoints progress to `data/.refresh-state.json` after every page so the script can be killed and resumed. Each invocation processes as many pages as fit in 30 seconds (the bash timeout has a 15-second safety margin). Claude (the agent) loops invocations until done. The script writes the final file atomically (`.tmp` + rename, same as today) so a crash mid-write can't corrupt anything. Wall time: 3 minutes for 650 leads, ~20 minutes for 5000.
  - The existing default mode (no flag) stays for backward compat: full scan in one process, blocks the caller until done. Used by power users via terminal.

- **Cowork scheduled-tasks integration in `SKILL.md` Easy Mode.** At install time, Easy Mode calls `mcp__scheduled-tasks__create_scheduled_task` twice:
  - Daily incremental at 2am local: `python3 scripts/refresh_leads_index.py --incremental`
  - Weekly full at Sunday 2am local: `python3 scripts/refresh_leads_index.py --full --resumable`
  Both tasks log to `data/.refresh-log.jsonl` so the agent can see refresh history.

- **`scripts/kit_health_check.py` (new file).** A small script Claude can run on demand when the user asks "is everything working?" Checks:
  - `data/leads_index.json` exists and is younger than 8 days (would suggest weekly hasn't run)
  - `data/.refresh-log.jsonl` shows successful runs in the last 7 days
  - `LOFTY_API_KEY` is set and the test endpoint responds
  - Scheduled tasks are registered

  Returns a structured JSON report Claude can summarize.

- **Read-only segments support.** Lofty exposes a `segments` field on every lead read but does NOT support writing segments via the public API (segment writes are gated behind signed requests on the internal `crm.lofty.com/api/` host; see "Recent finds" below). The kit currently drops the `segments` field when normalizing leads. v1.10 surfaces it:
  - Add `segments` to `normalize_lead()` output so `find_client` returns it.
  - Add `get_lead_segments(lead_id)` convenience helper that reads the lead and returns the segments list.
  - Document the read-only constraint in `references/quirks.md` so kit users don't try to write.

- **Tag-write helpers with the right semantics.** The naive pattern `update_lead(lead_id, tags=[...])` has two traps confirmed live on 2026-05-12: (a) it REPLACES the entire tag list, so naive "add" would silently delete existing tags, and (b) it expects tag NAMES (strings), not tagIds. Passing integers auto-creates new tags with those integers as their names. v1.10 adds three safe wrappers:
  - `add_tag(lead_id, tag_name)`: reads current tag names, appends new one, calls `update_lead(tags=[...names])`.
  - `remove_tag(lead_id, tag_name)`: reads current, filters, calls update.
  - `set_tags(lead_id, tag_names)`: explicit replace, named to make the destructive semantic obvious.

  Each wrapper logs the before-state to `data/.tag-log.jsonl` so a buggy automation can be reconstructed.

- **Stale-warning rewrite in `lofty_api.py` `find_client`.** Currently warns at 14 days. Change to 2 days. Wording shifts from "run refresh_leads_index.py" (instructional, terminal-flavored) to "your leads index hasn't refreshed in N days. The daily scheduled task may have failed. I can run a refresh now, or you can check kit health." Offers Claude a clear path to recover without the user touching the terminal.

Docs:

- **`references/workflows.md`:** new section "How the leads index stays current" describing the daily + weekly + live-scan architecture. Three paragraphs, no jargon.
- **`references/extending.md`:** Backend A section rewritten to reflect the new scheduled-task model. Make clear that file-backend with scheduled tasks is the default for non-tech users; Tier 4 webhooks are for power users with very large CRMs or sub-day staleness requirements.
- **`SKILL.md`:** add the kit-health-check trigger phrases ("is my Lofty integration working", "check kit health", "is the leads index current"). Add the new Easy Mode setup steps (schedule task creation, initial bootstrap).
- **`CHANGELOG.md`:** v1.10.0 entry.
- **`HANDOFF.md`:** v1.10.0 SHIPPED section, status snapshot update.

### Engineering tasks (ordered)

1. **Refactor `refresh_leads_index.py` to support `--incremental` mode.** Lift the per-page processing into a function. Read existing local file's leadId set. Fetch page 1. Diff. Write. Read `_metadata.total`. Return exit code 0 (success), 1 (failure), 2 (escalate-to-full-scan). ~1 hour.

2. **Add `--full --resumable` mode.** Checkpoint state to `data/.refresh-state.json` after each page (current scrollId, leadIds-seen-so-far, expected_total, started_at). On invoke, read state if present and resume from there. After 30 seconds wall time, save state and exit with code 3 (continue-me). On final page completion, atomic-write the file and clear the state. ~1.5 hours.

3. **Write `scripts/kit_health_check.py`.** ~1 hour.

4. **Update `lofty_api.py` `find_client` stale warning.** Adjust threshold to 2 days, rewrite message. Add a structured return-value hint that Claude can act on. ~30 min.

5. **Add read-only segments support.** Include `segments` in `normalize_lead()`. Add `get_lead_segments(lead_id)` helper. Document the read-only constraint in `references/quirks.md`. ~30 min.

6. **Add tag-write helpers: `add_tag`, `remove_tag`, `set_tags`.** Read-merge-write pattern with the right semantics (names not IDs, explicit replace). Tag log to `data/.tag-log.jsonl`. ~45 min.

7. **Wire Cowork scheduled tasks into Easy Mode.** Update `SKILL.md` Easy Mode setup section to call `mcp__scheduled-tasks__create_scheduled_task` for daily and weekly runs. Add kit-health-check trigger phrases and tag-write trigger phrases. ~45 min.

8. **Update docs.** `references/workflows.md`, `references/extending.md`, `references/quirks.md` (add the tag-write traps and the segment read-only quirk), `CHANGELOG.md`, `HANDOFF.md`. ~1.5 hours.

9. **Test end-to-end on a fresh-feeling install.** Use the `.test-v1.10/` scratch folder (gitignored, add to `.gitignore`). Walk through Easy Mode as if a new user. Verify the daily incremental runs in <15 seconds. Verify the weekly full reconciliation completes across multiple bash calls. Verify a Lofty-side delete is reflected in the local file after the next weekly run. Verify `add_tag` adds without destroying existing tags. ~1.5 hours.

10. **Commit, tag v1.10.0, push.**

### Done criteria

- [ ] `refresh_leads_index.py --incremental` runs in under 30 seconds for a typical day's lead delta.
- [ ] `refresh_leads_index.py --full --resumable` completes across multiple Cowork bash invocations without manual intervention.
- [ ] After the weekly run completes, a lead deleted in Lofty during the week is gone from the local file.
- [ ] Easy Mode install on a fresh setup creates two scheduled tasks (daily + weekly) and registers them with Cowork.
- [ ] `kit_health_check.py` returns a structured report Claude can summarize in plain English.
- [ ] `find_client` stale warning fires at 2 days, not 14.
- [ ] `find_client` and `get_lead` return the `segments` field.
- [ ] `add_tag(lead_id, tag_name)` adds without destroying existing tags. Verified live against a test lead.
- [ ] `remove_tag(lead_id, tag_name)` removes only the named tag.
- [ ] `references/quirks.md` documents the tag-write traps (replace-semantics, names-not-IDs) and the segment read-only constraint.
- [ ] The 95-assertion Tier 4 unit test still passes (no regression from v1.9.0).
- [ ] Em-dash audit clean. Joe-specifics audit clean.
- [ ] HANDOFF.md updated.

### Time estimate

~8 hours of focused engineering, one or two sessions. (Up from ~6 hours after adding segments-read and tag-write helpers.)

### Dependencies

- Cowork scheduled-tasks tool must be available (`mcp__scheduled-tasks__create_scheduled_task`). Confirmed available in current Cowork builds.
- No new external services. No new accounts. No new costs.

### Risks

- **Scheduled tasks require Claude Desktop to be running.** If the user closes Claude for a week, the daily task doesn't run. v1.10 documents this; v2.1+ could explore `launchd`-based persistence.
- **Lofty rate-limit changes.** If Lofty drops below 10 req/min on a free tier (or raises), the weekly full-scan timing changes. Worth re-testing after Lofty plan changes.
- **`_metadata.total` could be unreliable.** Confirmed it works May 12, but if it ever returns stale or wrong values, the delete-detection breaks. Mitigation: weekly full scan is the authoritative reconciliation regardless.

---

## v2.0.0: first major public release

### Goal

A polished, non-tech-shareable kit with a credible landing page, lean SKILL.md, clean Easy Mode UX, and the kit-health-check feature visible. After v2.0.0 ships, the GitHub Pages site is the public face of the kit and the .skill file is download-ready for real estate agents at any skill level.

### Why v2.0.0 instead of v1.10.1

Versions through v1.9.x have been internal-feeling releases. v1.10.0 closes the last functional gap. v2.0.0 is the moment we say "this is the kit, install it." The version jump signals product readiness, not feature count.

### What ships

Bloat audit and packaging:

- **SKILL.md slimmed to <5,000 tokens.** Currently ~9,000 tokens. The cut comes from:
  - Moving Tier 2, 3, 4 pickers to separate files in `pickers/` directory. SKILL.md keeps the routing logic (one-line per tier) but the detailed picker workflows load on tier-trigger only.
  - Stripping historical version notes (v1.6.1 changed X, v1.7.0 changed Y) which belong in CHANGELOG, not SKILL.md.
  - Condensing the file map into a single paragraph instead of a per-file list.
  - Tightening trigger phrases. The current list has 20+ phrases; many are redundant ("set up Lofty" and "connect my CRM" trigger the same flow). Cut to ~12 high-signal phrases.

- **Explicit reference-loading guidance in SKILL.md.** Add a "Reference loading" section that tells Claude:
  - Only read `workers_setup.md` if the user is setting up a Worker tier.
  - Only read `schema.md` if the user is asking about response shapes.
  - Only read `extending.md` if the user is asking how to customize.
  This prevents Claude from over-loading references "just to be safe."

- **Minimal-mode trigger.** A new phrase like "use minimal Lofty mode" tells Claude to NOT auto-load references unless explicitly requested. For agents who also use Claude for other things and want to keep context lean.

Public face:

- **`docs/index.html` rewritten.** Currently leads with deployment complexity. Rewrite leads with "Schedule a multi-stop showing in one sentence" and the conversational pitch. Workers tier becomes a footnote ("Power user? Tier 2 adds X. Tier 3 adds Y. Tier 4 adds Z.") Use the schedule-showing sub-skill as the headline feature, not the Workers.

- **`README.md` rewritten.** Same shape as the landing page: leads with conversational use, tiers become opt-in upgrades. Update repo-structure tree to reflect v1.10+ contents.

- **`INSTALL.md` rewritten.** Two install paths: (a) "Just the conversational kit" (5 minutes, no terminal, no Cloudflare). (b) "Conversational kit plus power-user tiers" (links to per-tier walkthroughs). The first path should be the obvious default.

Easy Mode UX:

- **Per-team stage probing.** At install time, Easy Mode probes the user's Lofty account for the actual list of stages and asks "Which of these should we exclude from leads-index lookups? Default: anything named DNC, Archived, or Agents / Vendors. Edit if your brokerage uses different names." Writes the result to a config the kit reads.

- **Initial bootstrap UX.** Easy Mode tells the user "Your leads index will take about 3 minutes to populate on first run. I can do it now (you wait) or schedule it for tonight (you wait until tomorrow for find_client to be fully populated)." Default to "do it now" but let users pick. After the bootstrap completes, Claude says "Done. You have 655 leads in your index. Try asking me to find one."

- **Multi-device note.** README and INSTALL flag that file-backed leads index is per-device. Two-device users either need to copy `data/leads_index.json` between machines or deploy Tier 4 for centralized state.

Outstanding decisions to resolve:

- **HANDOFF.md placement** (Outstanding decision #1 in current HANDOFF). Move to `.private/` or add to `.gitignore`. v2.0.0 is the right time to resolve this since the file currently contains owner identity that shouldn't ship with the public kit.

- **`lofty-api-guide.md` cleanup** (Outstanding decision #2). Either consolidate into `references/full-guide.md` or delete. Pick one.

- **`RESEARCH_NOTES_2026-05-07.md` cleanup** (Outstanding decision #3). Same as above.

- **Short-links Worker decision** (locked decision #11). Formally remove from roadmap or commit to v2.x build. Recommendation: formally remove. The Worker is candidate-for-cut, no agent is asking for it, and the YAML in the assets folder is enough for someone who wants to roll their own.

### Engineering tasks (ordered)

1. **Bloat audit pass on SKILL.md.** Move tier pickers to `pickers/` directory. Strip version notes. Tighten trigger phrases. Add reference-loading guidance. Target <5,000 tokens. ~2 hours.

2. **Per-team stage probing in Easy Mode.** Add a step that calls `lofty_api.get_lead_ponds()` or `lofty_api.get_custom_fields()` to surface the team's actual stage names, then asks the user to pick excludes. ~1 hour.

3. **Initial-bootstrap UX flow in Easy Mode.** Update the install steps so the bootstrap is a clear user-facing choice with progress feedback. ~45 min.

4. **`docs/index.html` rewrite.** Reframe around conversational use. The Workers become a footnote. ~2 hours.

5. **`README.md` and `INSTALL.md` rewrite.** Two-path install structure. ~1.5 hours.

6. **Resolve outstanding decisions 1, 2, 3.** Move/delete/clean as decided. ~30 min.

7. **Decide short-links Worker fate.** Update roadmap and assets accordingly. ~15 min.

8. **Repackage the .skill file.** Verify it loads cleanly in a fresh Cowork install. ~30 min.

9. **Test on a fresh-feeling install end-to-end.** Walk through the new conversational pitch, install the kit, do a multi-stop showing schedule, ask Claude to find a lead. Verify it all feels coherent. ~1 hour.

10. **Announce on GitHub Pages.** Pin the v2.0.0 release. Update social channels.

11. **Commit, tag v2.0.0, push.**

### Done criteria

- [ ] SKILL.md is under 5,000 tokens.
- [ ] Tier pickers live in separate files and load only when their tier triggers fire.
- [ ] `docs/index.html` leads with the conversational pitch, not deployment.
- [ ] `README.md` two-path install is unambiguous about which path is for whom.
- [ ] Per-team stage probing in Easy Mode works against the user's actual Lofty data.
- [ ] First-time install, including bootstrap, completes in under 10 minutes wall time without ever opening a terminal.
- [ ] Outstanding decisions 1, 2, 3 are resolved one way or another (not left open).
- [ ] Short-links Worker formally removed from the roadmap OR scheduled for a specific v2.x.
- [ ] HANDOFF.md updated.

### Time estimate

~10 hours of focused engineering, two or three sessions.

### Dependencies

- v1.10.0 must ship first. v2.0.0 leans on the scheduled-task architecture for its "non-tech-shareable" claim.

### Risks

- **Landing-page rewrite is creative work, not engineering.** It might iterate. Budget extra time for design feedback.
- **The bloat audit might find that splitting pickers into separate files BREAKS Cowork's skill activation.** Test the picker-split early. If it doesn't work, fall back to slimming SKILL.md in place.
- **Per-team stage probing requires reliable read endpoints.** `get_custom_fields()` and `get_lead_ponds()` are confirmed working, but stage-name probing needs more verification.

---

## v2.1 and later: deferred items

These are real items, not just brainstorming. Each will be promoted to its own version when the team is ready. Listed in rough priority order.

1. **Persistent scheduling via `launchd`.** Cowork scheduled tasks only run when Claude Desktop is running. For users who close Claude for days at a time, daily refresh stops. `launchd` (macOS) and Windows Task Scheduler would persist regardless. Trade-off: requires terminal access at install time, which contradicts the v1.10 non-tech goal. Likely a power-user opt-in.

2. **Multi-agent team scoping.** Team agents (ISA, TC, buyer's agent) may want `find_client` to scope to their own assigned leads. Lofty exposes `assignedUserId` on the lead object but `/v1.0/leads` doesn't support server-side filtering (see new quirk added in v1.10). Would require client-side filtering at index-build time and a `MY_USER_ID` config.

3. **Multi-device sync for the file backend.** Two-device users (Mac + iMac) currently each have their own copy of `data/leads_index.json` and run their own refresh. They drift. Options: (a) sync via iCloud Drive, (b) deploy Tier 4 (centralized), (c) sync via a small Worker that exposes file get/put. v2.0 documents the limit; v2.1+ might pick a path.

4. **Kit auto-update mechanism.** When v2.0.0 ships and v2.0.1 follows, how do existing users get the new version? Current path is manual reinstall. Cowork plugins might support auto-update; worth investigating.

5. **The new write endpoints from `lofty-api-opportunities.md`.** Five high-value endpoints documented yesterday:
   - `set_lead_inquiry(lead_id, criteria)`: POST `/v1.0/leads/{leadId}/inquiry`
   - `add_lead_property(lead_id, listing_id_or_address, label)`: POST `/v1.0/leads/{leadId}/property`
   - `log_communication(lead_id, channel, direction, content, when)`: POST `/v1.0/agent/communication`
   - `send_opportunity(lead_id, notification_type, description, link)`: POST `/v1.0/agent/send-notification`
   - `find_vendor(name)`: GET `/v1.0/vendor/list` with client-side filter

   Each is a small `lofty_api.py` addition. Probably ship together as v2.1.0.

6. **Cross-CRM support.** The same Cowork + skill pattern works for Follow Up Boss, kvCORE, Real Geeks, Sierra Interactive. Long-term fork target. Not v2.x.

7. **Showings analytics.** The Tier 2 D1 database accumulates buyer-feedback over time. Could expose aggregate views: "what dealbreakers come up most often?", "what neighborhoods get the highest scores?" Power-user feature.

8. **Lead merge / dedupe helpers.** Lofty supports merging leads in the UI but no API. A `find_duplicate_leads(threshold=0.8)` helper that returns lead pairs with similar names+emails+phones would be useful. Read-only flagging, not auto-merge.

9. **Onboarding flow polish.** A "first-week checklist" Cowork artifact that walks new users through trying find_client, scheduling a showing, asking for buyer preferences. Reduces the "I installed it, now what?" gap.

---

## What's explicitly NOT on the roadmap

If you find yourself wanting to add these, push back. They're out for specific reasons.

- **AI endpoints on Lofty** (`/v2.0/ai/lead-analysis`, `/v2.0/ai/call-script`). Broken in Lofty's API as of 2026. Skip.
- **Brokermint integration**. Joe's brokerage doesn't use Brokermint. No demand.
- **Lead Routing endpoints** (`/v1.0/routing/*`). Multi-agent team feature. Out of scope for solo realtors.
- **Smart Plans**. No API exposure from Lofty. Workaround documented in `references/extending.md`.
- **Bulk mass-email / mass-text**. No API. Loop client-side or use Smart Plans via UI.
- **A second CRM in the same kit**. Different scope; would be a fork, not an extension.
- **Custom field SETUP automation**. Read works (`get_custom_fields`); write (`/v1.0/teamFeatures/custom-field`) is low-frequency. Not worth the surface area.
- **A native macOS app wrapper**. Cowork already runs in the user's Claude Desktop. Building a separate app would duplicate effort.

---

## Strategic positioning (for the v2.0 landing-page rewrite)

The pitch for v2.0 should NOT be "deploy four Cloudflare Workers." It should be "have a conversation about your real estate business."

Sample headline candidates for the landing page:

- "Schedule a multi-stop tour by typing one sentence."
- "Find any client by name. Log any note. Without leaving the conversation."
- "Your CRM, now conversational."

The tier ladder should appear AFTER the conversational pitch:

> If you want more, the kit also includes optional upgrades for power users. Tier 2 captures structured post-showing feedback from buyers. Tier 3 sends pre-showing SMS reminders. Tier 4 keeps your leads index sync'd in real time. All optional. Most agents stop at the conversational layer and that's fine.

The maintainer's brand (Saling Homes at eXp Realty, Portland Oregon) belongs on the landing page in a "who built this" footer, not in the kit itself per locked decision #1.

---

## How to use this roadmap

For Claude sessions:

- If the user says "let's work on the next release" or "what's next," start with v1.10.0 unless this file marks it shipped.
- Don't add features that aren't on this roadmap without asking first. Scope creep is the most common way these projects drift.
- Update this file when a version ships. Move the version block from the active section into a "Shipped" section.
- If a deferred item gets promoted (a v2.1+ task becomes the next release), move it up and write a full task block for it.

For Joe:

- Use this file to push back when Claude proposes work that's not here.
- Edit it directly if priorities change. Claude will respect what's in the file.
- The estimates are deliberately conservative. Real time tends to be 1.2 to 1.5x the estimate.

---

## Recent finds worth carrying forward

These are findings from the v1.9.0 session that the next release should keep in mind:

1. **Lofty webhook list 2 payload shape uses plural-array buckets** (`updatedLead[]`, `newLead[]`, `deletedLead[]`). Documented as quirk #37. Anything that handles a webhook from Lofty must call `flattenLoftyPayload` from `workers/leads_index_worker.js`.

2. **Lofty's `/v1.0/leads` ignores `assigneeId`, `stageId`, `tagId` silently** (in addition to `keyword`, `sortField`, `startTime`, `page`). All filtering on leads must be client-side. This is the strongest version of quirk #2 to date and should be added to quirks.md in v1.10.

3. **Production Workers can silently fail for weeks if the parser doesn't match Lofty's actual payload shape.** The fix is debug-capture via a temporary debug Worker that writes raw payloads to KV. Pattern documented in this session's HANDOFF v1.9.0 SHIPPED section.

4. **The "Easy Mode" walkthrough genuinely IS for the tech-savvy helper, not the agent.** Reframe accordingly in v2.0 landing-page and docs. Solo non-tech agents stop at Tier 1.

5. **Cowork scheduled tasks are a real lever** for hands-off automation. Used heavily in v1.10. The kit should not be afraid to lean on Cowork infrastructure where it exists.

6. **`update_lead(tags=[...])` has two traps confirmed live on 2026-05-12.** First, it REPLACES the entire tags list, so naive "append a tag" patterns silently delete existing tags. Second, the items in the list are treated as tag NAMES (strings), not tagIds. Passing integer tagIds auto-CREATES new tags with those integers as their tag names, polluting the team tag library. Three garbage tags ("6536952", "903557", "954693") landed in Joe's team library during this test session and have to be cleaned up via the Lofty web UI because the public API does NOT expose tag deletion at any common path (probed: `/v1.0/tags/{id}`, `/v1.0/tag/{id}`, `/v1.0/team-features/tag/{id}`, `/v1.0/agent/{agentId}/tag/{id}` all 404 with Content-Type set). The v1.10 tag-write helpers MUST send names, MUST read-merge before write, and MUST log to `data/.tag-log.jsonl`.

7. **Segments are read-only from the public API, confirmed via Claude in Chrome.** Lofty's web UI calls segments "groups" internally and routes them through `POST /api/user/group/page` on `crm.lofty.com/api/`, not `api.lofty.com/v1.0/`. The internal API requires signed requests (`platform`, `timestamp`, and a per-request `signature` header generated by Lofty's web JS). Reverse-engineering the signature is out of scope and probably violates Lofty's ToS. The lead object DOES include a `segments` field on every read, so the kit can surface segments read-only in v1.10. Write access to segments requires either Lofty exposing the public API or a browser-automation tier (Claude in Chrome driving the UI), the latter is fragile and not in the public-kit scope.

8. **Lofty also silently ignores `assigneeId`, `stageId`, and likely `tagId` as query filters on `/v1.0/leads`.** Confirmed live on 2026-05-12. The endpoint returns the unfiltered first page regardless. Add to quirks.md in v1.10 as an expansion of quirk #2. All filtering must be client-side.

---
