# Lofty API Deep-Probe Research, May 7, 2026

One-shot research document. Not shipped in the `.skill` bundle — this is a working brief for Joe to decide what to act on.

Test target: lead `1142635515796067` (Joe Saling, joe@sellingpdxhomes.com). All probes scoped to this lead. One reversible round-trip write (create_note + delete_note); cleaned up at end of run.

---

## Top finding: a production bug in `delete_note` and friends

`api.delete_note(note_id)` returns:

```
{"error": True, "status": 400, "body": "{\"code\":20001,\"message\":\"Content-type must be: application/json\"}"}
```

Root cause: `_request` only sets `Content-Type: application/json` when method is POST or PUT. DELETE never gets it. Lofty's notes endpoint rejects DELETE without it.

This bug applies to every DELETE method in the production client: `delete_note`, `delete_lead`, `delete_task`, `delete_webhook`, and any future DELETE caller.

Fix: change one line in `_request`. Always send Content-Type on writes (POST, PUT, DELETE). Even simpler: always send it. I tested five GET endpoints (`/v1.0/me`, `/v1.0/leads/<id>`, `/v1.0/leads/<id>/activities`, `/v1.0/notes?leadId=<id>`, `/v1.0/leads?pageSize=5`) with Content-Type on GET and all five worked. Quirk #6 (the documented "GETs must not send Content-Type") looks obsolete in 2026.

Suggested replacement plumbing:

```python
def _request(self, method, path, body=None, query_params=None):
    self._rate_limit()
    url = f"{self.base_url}{path}"
    if query_params:
        filtered = {k: str(v) for k, v in query_params.items() if v is not None and v != ""}
        if filtered:
            url += "?" + urllib.parse.urlencode(filtered)

    headers = {
        "Authorization": f"token {self.api_key}",
        "Content-Type": "application/json",   # always set; required by some GETs and all DELETEs
        "Accept": "application/json",
    }
    data = json.dumps(body).encode("utf-8") if body else None
    # ... rest unchanged
```

Apply this in both production AND the public port, then add `delete_note`, `delete_task`, `delete_webhook` to the ported method list.

---

## New quirks to add to `references/quirks.md`

Numbered to extend the existing list (last entry was #20).

### 21. Some GET endpoints REQUIRE Content-Type, contradicting quirk #6

`/v1.0/team-features/lead-ponds` and `/v1.0/teamFeatures/listCustomField` return `415 "Content-Type 'null' is not supported"` when called without the header. Same call with `Content-Type: application/json` returns 200.

Workaround: always send Content-Type on every request (verified safe across `/v1.0/me`, `/v1.0/leads`, `/v1.0/leads/<id>`, `/v1.0/leads/<id>/activities`, `/v1.0/notes`). This single change supersedes quirks #6 and #22 below.

### 22. DELETE endpoints REQUIRE Content-Type

`DELETE /v1.0/notes/<id>` returns `400 errorCode=20001 "Content-type must be: application/json"` without the header. Production's `_request` is missing this. See top finding above.

### 23. `/v1.0/members` is hard-capped at 25 per page (same as `/v1.0/leads`)

Asking for `pageSize=5` returns 25 items. Same silent ignore pattern as quirk #2. Confirmed live. The `_metadata.scrollId` works for pagination — just like leads.

### 24. `/v1.0/teamFeatures/listTag` returns BOTH definitions and instances

The endpoint name suggests "list of tags configured on the team," but it returns:
- `leadId: 0` rows (tag definitions, never applied)
- `leadId: <int>` rows (a tag applied to a specific lead)

Same payload contains both. To get just definitions: filter `leadId == 0`. To get instances on a lead: filter by that `leadId`.

This means a single response can be huge for a busy team. Joe's team has 390 rows across 652 leads.

### 25. `/v1.0/me` returns a different ID format than the rest of the API

`GET /v1.0/me` returns `{"id": 113209, ...}`. But Joe's `creatorUserId` on tags he created is `844510972070138`, and that's also what HANDOFF.md records as Joe's "Lofty User ID." Both refer to the same user; they're different ID schemes.

Side effect: a script that does `me = api.get_me(); my_id = me["id"]; tags_i_created = [t for t in tags if t["creatorUserId"] == my_id]` will match nothing. Use the 15-digit form from HANDOFF/lead records, not the short `id` from `/v1.0/me`, when joining against `creatorUserId`, `leadUserId`, `assignedUserId`, `lenderUserId`, etc.

### 26. `/v1.0/leads/<id>/activities` returns a LIST directly, not a dict envelope

Most endpoints wrap responses in `{"key": [...]}`. Activities does not. `response[0]` is the first activity. Code that does `response.get("activities", [])` returns `[]` and silently skips the data.

Activity item shape: `{type, text, link, picture, listing, pageName, scheduledDate, created}`. The `listing` field is the full inline listing dict, which is helpful for "show me homes Joe browsed last week" without an extra MLS round-trip.

### 27. `get_lead_analysis` returns 500, not the documented 404

Production marks `/v2.0/ai/lead-analysis` as "Not enabled. No replacement." In 2026 it returns:

```
{"status": 500, "body": "{\"message\":\"BaseApplicationException:errorCode=20005,errorMsg=There is an internal error happened\"}"}
```

The endpoint exists, accepts the call, then crashes server-side. Don't rely on it; treat as broken, not as a clean 404.

### 28. `generate_call_script` returns 400 errorCode=20012, not 404

Same pattern. Production's documented signature `generate_call_script(lead_id, purpose=None)` returns Invalid Parameter. Endpoint exists but the documented call shape doesn't satisfy it. Either the body is required, or the path differs in 2026. Worth one more probe pass before declaring permanently broken.

---

## Methods that work but aren't yet ported to the public skill

All confirmed live against Joe's account. Worth adding to `assets/lofty_api.py` in v1.4:

| Method | Endpoint | Returns |
|---|---|---|
| `get_call_history(lead_id=)` | `/v1.0/leads/<id>/calls` | `{calls: [...]}` (Joe: 0) |
| `get_email_history(lead_id=)` | `/v1.0/leads/<id>/emails` | `{emails: [...]}` (Joe: 10, fields: agentId, direction, emailEventTime, emailSubject, emailType, eventType, fromPond, id, leadId) |
| `get_text_history(lead_id=)` | `/v1.0/leads/<id>/texts` | `{texts: [...]}` (Joe: 6, fields: agentId, direction, id, leadId, textContent, textOutcome, textTime, textType) |
| `get_transactions(lead_id)` | `/v1.0/leads/<id>/transactions` | `list[]` (Joe: 0) |
| `get_alerts(lead_id)` | `/v1.0/leads/<id>/alerts` | `{data: [...], status: {code, msg, trace}}` (Joe: 1) |
| `get_system_logs(lead_id, page_size=)` | `/v1.0/systemLogs?leadId=<id>` | `{hasMore: int, timeLines: [...]}` — the **unified human timeline** for a lead |
| `get_custom_fields()` | `/v1.0/teamFeatures/listCustomField` | `list[]` of `{attributeName, attributeType, value, params}` (Joe: 37 fields configured) |
| `get_lead_ponds()` | `/v1.0/team-features/lead-ponds` | `list[]` of pond definitions (Joe: 0) |
| `get_organization()` | `/v1.0/org` | `{enterpriseInfo, orgType}` |
| `get_members(page_size=25)` | `/v1.0/members` | `{_metadata, members: [...25...]}` |
| `delete_note(note_id)` | `DELETE /v1.0/notes/<id>` | empty body on success — REQUIRES Content-Type fix |
| `delete_task(calendar_id)` | `DELETE /v2.0/calendar/<id>` | (assumed) — REQUIRES Content-Type fix |

`get_system_logs` is the standout. It returns the unified timeline (calls, emails, texts, notes, stage transitions, manual logs, etc.) in chronological order with human-readable `content` strings. That's a much friendlier surface than the per-channel pulls when Claude is asked "what's been happening with Jane Smith lately?"

---

## Lead-record fields the slim dict throws away

`get_lead(<id>)` returns 51 top-level fields. The leads-index normalizer (`refresh_leads_index.py::_normalize`) captures 17. Worth-reading fields the slim dict drops:

**Buyer/seller intent**
`buyHouse`, `buyingTimeFrame`, `houseToSell`, `sellingTimeFrame`, `withBuyerAgent`, `withListingAgent`, `fthb` (first-time-home-buyer flag), `mortgage`, `preQual`

**Contact preferences (DNC-style flags)**
`cannotCall`, `cannotEmail`, `cannotText`, `phoneStatuses` (granular per-phone status), `unsubscription`

**Address fields on the lead itself**
`streetAddress`, `city`, `state`, `zipCode` (the lead's home address, not their target search area)

**Visibility / ownership**
`hiddenFlag`, `privateFlag`, `assignedUser`, `assignedUserId`, `leadUserId`, `lenderUserId`, `pondId`, `pondName`, `ownershipId`, `ownershipScope`

**Time / activity**
`createTime`, `lastTouch`, `lastUpdateTime`, `lastVisit`, `assignTime`

**Rich child collections**
`leadFamilyMemberList`, `leadInquiry`, `leadPropertyList` (the list of properties tied to this lead — saved searches, favorites, viewed)

**Other**
`birthday`, `referredBy`, `language`, `facebook`, `twitter`, `customAttributes`, `customRoleList`, `groups`, `segments`, `opportunity`

If the leads-index normalizer captured even a subset of these (intent + DNC + last-touch + leadPropertyList), `find_client` could power richer answers without an extra `get_lead` round-trip per match. Worth a v1.4 expansion.

---

## What's NOT in the API surface (confirmed via probe)

Twelve targeted 404s confirm these UI features have no REST exposure:

```
/v1.0/leadStages          → 404
/v1.0/lead-stages         → 404
/v1.0/teamFeatures/listLeadStage   → 404
/v1.0/leadSources         → 404
/v1.0/teamFeatures/listLeadSource  → 404
/v1.0/segments            → 404
/v1.0/teamFeatures/listSegment     → 404
/v1.0/teamFeatures        → 404
/v1.0/team-features       → 404
/v1.0/savedSearches       → 404
/v1.0/listingAlerts       → 404
/v1.0/listings            → 404 (use /v2.0/listings/search instead)
/v1.0/showings            → 404
/v1.0/feedbacks           → 404
/v1.0/email-templates     → 404
/v1.0/sequences           → 404
/v1.0/snippets            → 404
/v2.0/leads               → 404
```

Confirmed why Phase 2 needs the Cloudflare Workers + Jotform + D1 architecture. Lofty exposes the lead-centric core well, but it doesn't expose:
- pipeline configuration (stages, sources, segments live INSIDE lead records, not as queryable lists)
- saved searches / listing alerts (managed via webhook list 4 if at all)
- automation surface (drip campaigns, sequences, templates, snippets)
- a native showings or feedbacks endpoint (we have to roll our own)

This is a clean justification for the Phase 2 architecture. Worth working into the main README so recipients understand WHY the Workers are necessary, not just HOW to deploy them.

---

## Two anomalies worth surfacing

### Duplicate Joe Saling records

Your leads index has two Joe Saling entries:

```
leadId=1142635515796067 | joe@sellingpdxhomes.com  | stage=Hot
leadId=1141206465681198 | joe@salinghomes.com      | stage=Hot
```

Older email on the second record. Worth a one-time consolidation pass: pick the keeper, transfer any tags / notes / activity from the duplicate, then delete the duplicate. Useful as a "cleanup my CRM" workflow recipe for the public skill.

### Three different "user ID" representations for one user

You appear in the API under three numeric IDs:

| Field | Value | Where it shows up |
|---|---|---|
| `id` (from `/v1.0/me`) | `113209` | Only in `/v1.0/me` |
| `creatorUserId`, `assignedUserId`, etc. | `844510972070138` | On every record this user touches |
| `memberUserId` (from `/v1.0/me`) | `113209` (same) | `/v1.0/me`, members list |

This is documented as quirk #25 above. The HANDOFF.md "Lofty User ID: 844510972070138" line is the right one to use as the practical agent identifier; Lofty's response from `/v1.0/me` doesn't expose that form.

---

## Recommended next moves, in priority order

1. **Fix `_request` Content-Type handling.** One-line change. Unblocks all DELETE methods. Apply to both production lofty_api.py AND public assets/lofty_api.py. Low risk: GETs continue to work with the header, POST/PUT unchanged.

2. **Port the 12 new methods listed above to v1.4.** Most are 5-line wrappers around `_request`. The whole batch is probably 80 lines of code. The standout (`get_system_logs`) genuinely changes what Claude can answer without extra API calls.

3. **Expand the leads-index normalizer.** Add the buyer/seller intent fields, DNC flags, and `leadPropertyList`. `find_client` becomes substantially more useful when the slim dict already contains "is this a first-time home buyer," "do they have a house to sell," "did they unsubscribe from email."

4. **Replace quirks.md entries #6 and #22.** Quirk #6 ("GETs must not send Content-Type") is obsolete. Quirk #22 (current bug placeholder for DELETE) gets resolved by the one-line fix above. Replace with the new #21–#28 entries from this document.

5. **Address the duplicate Joe Saling record in your CRM.** Manual cleanup, not skill code. But while it's there, `find_client("Joe")` returns two candidates and your search self-exclusion only fires for `lastNameLower == "saling"` — which excludes both. Net effect: you can't find yourself. Probably fine.

6. **Update the public README with the API-surface map** ("here's what works, here's why Phase 2 needs Workers"). Helps non-technical adopters understand the architecture without having to discover it themselves.

---

## Files NOT modified during this run

I only wrote one new file (this document). I did NOT yet:

- Update `references/quirks.md` (the new entries are staged here, awaiting your approval)
- Modify `_request` in either lofty_api.py
- Add the 12 unported methods
- Touch `refresh_leads_index.py`'s `_normalize`

That's intentional. These are real changes with downstream effects (e.g., a Content-Type change touches every API call you make). Let me know which of the six recommended moves to act on and I'll proceed.

Test note created during the run was deleted as cleanup. Lead `1142635515796067` is in its original state with 0 notes and the same 3 tags it had at the start.
