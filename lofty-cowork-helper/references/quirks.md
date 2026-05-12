# Lofty API Quirks (Full List)

Load this when a Lofty API call behaves unexpectedly. The five most common are also in `SKILL.md`; the rest are listed here.

These behaviors were observed during testing on one team's Lofty account in mid-2026. Lofty can change them on any deploy. If you hit something not on this list, treat it as new and verify in the user's environment.

---

## The five most common

1. **Auth header is `token`, not `Bearer`.** For personal access tokens (the JWTs starting with `eyJ`), the right header is `Authorization: token <key>`. Using `Bearer` returns error code 200058: "User in token does not exist." The starter Python client handles this; if a user calls the API with `curl` or another HTTP client, they need to know.

2. **`/v1.0/leads` silently ignores `sortField`, `keyword`, `startTime`, and oversized `pageSize`.** The endpoint accepts those parameters and returns 200, but the response is always sorted by `leadId` DESC and any keyword filter is dropped. Page size is hard-capped at 25 (the response metadata echoes `limit: 25` regardless of what you asked for). This is the single biggest behavioral surprise in the API. The workaround is a leads index: a separate cache populated either by webhook list 2 (a Cloudflare Worker, fresh within 5 minutes) or by a periodic full-rescan script (~3 minutes for 650 leads). See `full-guide.md` section 15.

3. **Activities must use v1.0.** `/v1.0/leads/<id>/activities` works. `/v2.0/activities` and `/v2.0/leads/<id>/activities` return empty results no matter what.

4. **Notes endpoint:** `POST /v1.0/notes` with body `{"leadId": <number>, "content": "..."}`. No `title` field. `leadId` must be a number, not a string. The intuitive path `/v1.0/leads/<id>/notes` returns 404.

5. **Rate limit is 10 requests per minute.** The starter client enforces 6.5s spacing automatically. Direct API callers need to throttle themselves.

---

## The rest

6. **OBSOLETE in v1.4.0. Always send `Content-Type: application/json`.** Earlier client versions only sent the header on POST/PUT. Live testing in May 2026 showed two endpoints (`/v1.0/team-features/lead-ponds`, `/v1.0/teamFeatures/listCustomField`) reject GET WITHOUT it (415 "Content-Type 'null' is not supported") and ALL DELETE endpoints reject without it (400 errorCode=20001). Sending it on every method is verified safe across all read endpoints the client uses. The v1.4 `_request` always sends the header. See quirks #21 and #22.

7. **Lead data shape:** `phones` and `emails` are plain string arrays, not objects. Code that expects `lead.emails[0].address` will fail; the right path is just `lead.emails[0]`.

8. **`get_lead` response is wrapped** in `{"lead": {...}}`. The starter client unwraps; if a user writes their own client, they need to.

9. **Pagination uses `scrollId` inside `_metadata`** for pages 2+ on lead search. Page size hard-capped at 25.

10. **`/v1.0/listing` does not work with personal API key auth.** Use `/v2.0/listings/search` with `scope="my"` instead.

11. **All times are ISO 8601 with offset.** Pacific looks like `2026-04-15T14:00:00-07:00`. Naive timestamps without an offset get rejected or interpreted in unexpected timezones.

12. **No bulk activity feed exists.** `/v1.0/activities`, `/v2.0/activities`, `/v1.0/events`, `/v1.0/notifications`, `/v1.0/timeline`, and `/v1.0/leadActivities` all return 404. `/v1.0/systemLogs` requires a `leadId`. For cross-lead activity, subscribe to webhook list 3 and call back to enrich each event.

13. **Webhook list 3 payloads are pings.** The body is just `{leadId, updateTime}` with no activity type or detail. Consumers must call `/v1.0/leads/{id}/activities` to enrich. Delivery SLA: typically under 1 minute, sometimes up to 5.

14. **Cowork's bash tool has a 45-second hard timeout.** At 6.5s spacing, that caps a single bash call at about 6 API requests. Long scans (the 650-lead index refresh runs ~3 minutes) must be run from the user's real terminal or chunked.

15. **`/v2.0/listings/search` body keys are NOT the obvious names.** Verified live in May 2026. Send `searchScope` (not `scope`), `soldFlag` (not `sold`), `filterConditions` (not `filter`), `sortFields` (not `sort`), `pageNum` (not `page`), and `pageSize`. Sending the obvious names returns HTTP 200 with 0 results and no error, so the bug is silent. The starter client's `search_listings` uses the right keys; if a caller writes their own request body, get this exactly right.

16. **`/v2.0/listings/search` results live under `listing` (singular), not `listings`.** The response shape is `{"listing": [...], "metadata": {"total": N}}`. Code that reads `response["listings"]` returns nothing.

17. **`/v2.0/calendar` create body uses `taskWay`, not `way`, and requires `timeZoneCode`.** The valid `assignedRole` values are `"Agent"` and `"Assistant"`, not `"ASSIGNED"`. Mismatched names return error code 20012, "Invalid parameter" with no hint about which key is wrong. The starter client's `create_task` handles this; raw callers need to match exactly.

18. **`find_listing_by_address` is Active-only by design.** Earlier versions fell through to Pending and Sold when an Active match wasn't found, which masked typos: a wrong city or wrong zip would silently return None instead of telling the user the address is bad. The shipped helper now returns `{"error": "address_not_found", "zipCode": "<parsed>", "message": "..."}` so the caller can ask the user to verify. If the listing genuinely is Pending or Sold, query that scope yourself with `search_listings(filter_conditions={"location": {"zipCode": [zip]}, "listingStatus": ["Pending"]})`.

19. **The showing-sms Worker reuses your Lofty JWT as its bearer token.** `enqueue_showing_sms`, `list_pending_showings`, and `cancel_showing_by_key` all send `Authorization: Bearer $LOFTY_API_KEY` to the Worker. The Worker is configured to accept the Lofty JWT as its shared secret. This avoids managing yet another API key, but it does mean rotating your Lofty key requires updating the Worker's environment too. The other Workers (`short-links`, `jotform-to-lofty`) use their own bearer tokens (`SHORTENER_API_KEY`, `LOFTY_PREFERENCES_API_KEY`).

20. **`prepare_showing` is a dry-run helper, not a side-effect machine.** It returns payloads and queues the post-showing SMS, but it does NOT create the calendar event, post the Lofty note, or email the buyer. The calling code is responsible for those, in order: create calendar event, then post the Lofty note (so the note can truthfully say "Calendar invite sent to: <email>"), then optionally email the buyer with the .ics. An earlier version posted the note first; when the calendar step failed downstream, the note lied about a meeting that never got scheduled. Don't reorder these.

21. **Some GET endpoints REQUIRE `Content-Type: application/json`** (the OPPOSITE of the older quirk #6 guidance). `/v1.0/team-features/lead-ponds` and `/v1.0/teamFeatures/listCustomField` return 415 "Content-Type 'null' is not supported" when the header is absent, and 200 with data when it's present. The v1.4 `_request` plumbing always sends it. If you write a raw caller, do the same.

22. **DELETE endpoints REQUIRE `Content-Type: application/json`.** `DELETE /v1.0/notes/<id>` and `DELETE /v1.0/webhook/<id>` both return 400 errorCode=20001 "Content-type must be: application/json" without the header. Pre-v1.4 client versions silently failed on every DELETE call because they only sent the header on POST/PUT. Combined with quirk #21, the only safe rule is to always send Content-Type, on every method.

23. **`/v1.0/members` is hard-capped at 25 per page**, the same silent-ignore pattern as `/v1.0/leads` (quirk #2). Asking for `pageSize=5` or `pageSize=500` both return 25. Pagination via `_metadata.scrollId` works the same way as on `/v1.0/leads`.

24. **`/v1.0/teamFeatures/listTag` returns BOTH definitions and applied instances.** A single response contains entries with `leadId == 0` (tag definitions, never applied) AND entries with `leadId > 0` (a specific tag applied to a specific lead). The endpoint name suggests "tags configured on the team" but the payload mixes both. Filter `[t for t in tags if t['leadId'] == 0]` for definitions only.

25. **`/v1.0/me` returns a different ID format than the rest of the API.** `GET /v1.0/me` returns `{"id": 113209, ...}` (a short integer). But `creatorUserId`, `assignedUserId`, `leadUserId`, `lenderUserId` on every other record are 15-digit strings (e.g. `844510972070138`). Both refer to the same user; they're different addressing schemes. Code that joins `/v1.0/me.id` against any of those other fields will match nothing. Use the 15-digit form (which appears in HANDOFF.md and on every record this user touches) when joining; use the short `id` only inside `/v1.0/me`.

26. **`/v1.0/leads/<id>/activities` returns a LIST directly, not a dict envelope.** Most endpoints wrap responses in `{"key": [...]}`. Activities does not. Code that does `response.get("activities", [])` returns `[]` and silently drops the data. The starter's `get_lead_activities` already accommodates both shapes.

27. **`/v2.0/ai/lead-analysis` returns 500 errorCode=20005, not 404.** Pre-v1.4 docs said this AI endpoint was "not enabled / no replacement." In 2026 the endpoint accepts the call and crashes server-side. Treat as broken, not as cleanly absent.

28. **`/v2.0/ai/call-script` returns 400 errorCode=20012 "Invalid parameter".** The documented call shape `{"leadId": <id>}` is rejected. Body or path may have changed in 2026. Treat as broken pending further probing.

29. **`/v1.0/leads` `page` parameter is silently ignored.** Confirmed live in May 2026. Calling `page=2` returns the same first 25 leads as `page=1`. The only working pagination is `scrollId` from the response's `_metadata`: pass that value back as a query param to get the next 25. Default sort appears to be newest-first (createTime DESC), which is what the v1.4.1 `find_client` fallback relies on. Quirk #2 covered keyword/sortField/startTime; #29 adds `page` to that list. The starter's `_search_recent_leads` helper handles scrollId pagination correctly.

30. **`-1` is the "unset" sentinel for numeric fields on Lofty objects**, not null. Affects `leadSource` on manually created leads, `leadInquiry.priceMin/Max` and `bedroomsMin/Max`, and `leadPropertyList[].price`, `lotSize`, `floors`, `parkingSpace`. Code that filters with `if v is not None` will keep "unset" values; the right filter is `if v > 0`. Confirmed live May 2026.

31. **`_metadata.total` is exposed on `/v1.0/leads`.** The wrapper is `{collection, limit, offset, total, scrollId}`, not just `scrollId`. `total` is the full count of leads matching the query, so a caller can get a count without paginating all the way through. Useful when you only need "how many leads do I have in stage X?" Confirmed live May 2026.

32. **Activity `created` is epoch milliseconds, not an ISO string.** Activity rows from `/v1.0/leads/{id}/activities` have an integer `created` field in epoch ms. Convert with `datetime.fromtimestamp(v / 1000)`. Lead-level timestamps (`createTime`, `lastTouch`, `lastUpdateTime`, etc.) are strings in `YYYY-MM-DDThh:mm:ssGMT` format, not ISO 8601 with offset. Lofty mixes the two formats; pick the right parser per field.

33. **`customRoleList[]` field is `role`, not `roleName`.** Every lead read returns the full role catalog (Buyer Agent, Showing Assistant, ISA, Transaction Coordinator, etc.) with `assigneeId=0` and `assignee=null` when nothing is assigned. To find actual role assignments, filter `[r for r in lead["customRoleList"] if r["assigneeId"] > 0]`. Confirmed live May 2026.

34. **`/v1.0/calls` returns 404 without `leadId`.** Despite the OpenAPI docs description suggesting agent-wide call listing is supported, the endpoint requires a `?leadId=<id>` query param. With it, returns `{_metadata, calls}` using the same `scrollId` pagination as `/v1.0/leads`. Confirmed live May 2026.

35. **`/v1.0/vendor/list` returns a bare list with no `_metadata`.** All vendors come back in one response. No pagination params observed. Different envelope shape from every other list endpoint in the API. Confirmed live May 2026.

36. **`/v1.0/getPublishedListings` requires content negotiation.** Returns 406 "Not Acceptable" on a plain GET. The endpoint is an XML/RETS feed, so callers need to send `Accept: application/xml`. The starter client does not currently use this endpoint, but raw callers will hit the 406 without the right header.

---

## Webhook event types

There are 12 webhook event types total:

| ID | Name | Notes |
|---|---|---|
| 1 | Agent | Agent profile changes |
| 2 | Lead Info | Lead create / update / delete (basis for the leads index) |
| 3 | Lead Activity | Browse / search / favorite / request (ping payloads only; enrich with `/leads/<id>/activities`) |
| 4 | Listing Alert | New listings matching a saved search |
| 5 | Transaction | Transaction state changes |
| 6 | Call | Call recorded (manual + logged only, NOT auto) |
| 7 | Email | Email sent (manual + logged only, NOT auto) |
| 8 | Text | SMS sent (manual + logged only, NOT auto) |
| 9 | Note | Note created |
| 10 | Task | Task created or updated |
| 11 | Appointment | Appointment created or updated |
| 12 | Pipeline Change | Lead stage transition |

Call, Email, and Text webhooks fire only on MANUAL or LOGGED events. Automated sends from sequences do not fire these.

---

## Endpoints that don't work (don't try)

| What you might try | What works instead |
|---|---|
| `Authorization: Bearer <jwt>` | `Authorization: token <jwt>` |
| `/v1.0/leads/<id>/notes` | `POST /v1.0/notes` with `leadId` in body |
| `/v2.0/activities`, `/v2.0/leads/<id>/activities` | `/v1.0/leads/<id>/activities` |
| `/v1.0/listing` (own listings) | `/v2.0/listings/search` with `scope="my"` |
| `/v2.0/ai/lead-analysis` | Not enabled. No replacement. |
| `/v2.0/ai/call-script` | Not enabled. No replacement. |
| `/v1.0/activities` (cross-lead) | No bulk feed. Use webhook list 3 + per-lead enrichment. |

---

## When in doubt

Read the response body. The Lofty API is usually pretty good about saying what is wrong. The starter client returns `{"error": True, "status": <code>, "body": "..."}` on HTTP errors. The `body` field is the API's actual error message.
