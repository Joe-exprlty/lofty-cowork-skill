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

6. **GET requests must NOT send `Content-Type`.** Some endpoints return 415 Unsupported Media Type if you do. The starter client only sends `Content-Type` on POST and PUT.

7. **Lead data shape:** `phones` and `emails` are plain string arrays, not objects. Code that expects `lead.emails[0].address` will fail; the right path is just `lead.emails[0]`.

8. **`get_lead` response is wrapped** in `{"lead": {...}}`. The starter client unwraps; if a user writes their own client, they need to.

9. **Pagination uses `scrollId` inside `_metadata`** for pages 2+ on lead search. Page size hard-capped at 25.

10. **`/v1.0/listing` does not work with personal API key auth.** Use `/v2.0/listings/search` with `scope="my"` instead.

11. **All times are ISO 8601 with offset.** Pacific looks like `2026-04-15T14:00:00-07:00`. Naive timestamps without an offset get rejected or interpreted in unexpected timezones.

12. **No bulk activity feed exists.** `/v1.0/activities`, `/v2.0/activities`, `/v1.0/events`, `/v1.0/notifications`, `/v1.0/timeline`, and `/v1.0/leadActivities` all return 404. `/v1.0/systemLogs` requires a `leadId`. For cross-lead activity, subscribe to webhook list 3 and call back to enrich each event.

13. **Webhook list 3 payloads are pings.** The body is just `{leadId, updateTime}` with no activity type or detail. Consumers must call `/v1.0/leads/{id}/activities` to enrich. Delivery SLA: typically under 1 minute, sometimes up to 5.

14. **Cowork's bash tool has a 45-second hard timeout.** At 6.5s spacing, that caps a single bash call at about 6 API requests. Long scans (the 650-lead index refresh runs ~3 minutes) must be run from the user's real terminal or chunked.

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
