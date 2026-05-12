#!/usr/bin/env python3
"""
Lofty CRM API: Starter Python Client
=====================================
A minimal, self-contained Lofty client. Drop into your project's scripts/
folder, set LOFTY_API_KEY in your .env file, and you're connected.

Usage from Python:
    from lofty_api import LoftyAPI
    api = LoftyAPI()
    me = api.get_me()
    lead = api.get_lead(12345)
    api.create_note(lead_id=12345, content="Followed up today")

Usage from the command line:
    python3 lofty_api.py test
    python3 lofty_api.py lead 12345
    python3 lofty_api.py activities 12345
    python3 lofty_api.py notes 12345

This client handles the four most important quirks:
    1. Auth header is "token", not "Bearer".
    2. Content-Type is sent only on POST/PUT, never on GET.
    3. Notes are POSTed to /v1.0/notes with leadId in the body.
    4. Rate limit: 10 req/min, enforced as 6.5s spacing.

Added in v1.2.0:
    - search_listings (MLS search via /v2.0/listings/search)
    - create_task (/v2.0/calendar)
    - send_email (/v1.0/message/email/send)
    - send_sms (/v1.0/message/sms/send)

Added in v1.3.0 (Phase 2):
    - find_client / leads-index reader (Worker first, file fallback)
    - find_listing_by_address (zip-scoped Active-only search)
    - prepare_showing (full multi-step showing prep)
    - shorten_url, build_jotform_url, build_showing_invite,
      enqueue_showing_sms (showing primitives)
    - list_pending_showings, cancel_showing, cancel_showing_by_key
    - get_buyer_preferences (D1-backed feedback rollup)

Phase 2 methods that talk to Cloudflare Workers fail soft when the
matching Worker URL is empty in .env. That way the v1.3 client is
still useful for find_client and find_listing_by_address even before
the recipient deploys their Workers.

Add other methods as you need them. The full guide has working examples.
"""

import json
import os
import sys
import time
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path


# -----------------------------------------------------------------
# .env loader (no external dependency, no pip install required)
# -----------------------------------------------------------------
# Looks for .env in the same directory as this file or one level up.
# Loads any KEY=value pair into os.environ if not already set.
# A missing .env is not an error at import time. We only fail when
# a caller actually tries to use a missing secret.
def _load_dotenv():
    here = Path(__file__).resolve().parent
    for candidate in [here / ".env", here.parent / ".env", here.parent.parent / ".env"]:
        if candidate.is_file():
            try:
                for line in candidate.read_text().splitlines():
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, _, val = line.partition("=")
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    if key and key not in os.environ:
                        os.environ[key] = val
            except Exception:
                pass
            return


_load_dotenv()


def _require_env(name, hint=""):
    """Return an env var or raise a clear error pointing at .env."""
    val = os.environ.get(name)
    if not val:
        msg = (
            f"Missing required environment variable: {name}\n"
            f"Add it to your .env file at the project root."
        )
        if hint:
            msg += f"\nHint: {hint}"
        raise RuntimeError(msg)
    return val


# -----------------------------------------------------------------
# Config
# -----------------------------------------------------------------
# Environment variable contract:
#
#   Required at startup:
#     LOFTY_API_KEY                   Your Lofty personal access token (JWT).
#
#   Optional core overrides:
#     LOFTY_BASE_URL                  Default: https://api.lofty.com
#     LOFTY_RATE_LIMIT_DELAY          Default: 6.5 (seconds between calls)
#
#   Owner identity (used by build_showing_invite and find_client):
#     OWNER_FULL_NAME                 e.g. "Jane Smith"
#     OWNER_BROKERAGE                 e.g. "Acme Realty"
#     OWNER_PHONE                     e.g. "503-555-1212"
#     OWNER_EMAIL                     e.g. "jane@acme.com" (also used as
#                                     the calendar identifier in
#                                     prepare_showing return)
#     OWNER_LAST_NAME_LOWER           Lowercased last name. find_client
#                                     uses this to exclude the user's own
#                                     record from name searches.
#     MLS_NAME                        e.g. "RMLS", "BrightMLS". Stamped
#                                     into the showing-log note.
#
#   Leads index (Phase 2 file or Worker fallback):
#     LOFTY_LEADS_INDEX_SOURCE        "file" (default) or "worker"
#     LOFTY_LEADS_INDEX_PATH          Default: <repo>/data/leads_index.json
#     LOFTY_LEADS_INDEX_STALENESS_DAYS  Default: 14 (warn-only)
#     LEADS_INDEX_WORKER_URL          Required when source=worker
#     LEADS_INDEX_EXPORT_API_KEY      Required when source=worker
#
#   Showing automation (only required when the matching Worker is used):
#     SHOWING_SMS_BASE_URL            Required for enqueue / cancel / list
#     SHORTENER_BASE_URL              Optional. shorten_url falls back
#                                     to the long URL on miss.
#     SHORTENER_API_KEY               Required when SHORTENER_BASE_URL set
#     JOTFORM_FORM_ID                 Required for build_jotform_url
#     JOTFORM_WORKER_URL              Required for get_buyer_preferences
#     LOFTY_PREFERENCES_API_KEY       Required for get_buyer_preferences
#
# The _require_env helper raises a clear, single-line error when a method
# needs a value that has not been set, so missing config never silently
# corrupts a workflow.
# -----------------------------------------------------------------
BASE_URL = os.environ.get("LOFTY_BASE_URL", "https://api.lofty.com")
RATE_LIMIT_DELAY = float(os.environ.get("LOFTY_RATE_LIMIT_DELAY", "6.5"))


# Local leads-index file. find_client reads this when LOFTY_LEADS_INDEX_SOURCE
# is not "worker". refresh_leads_index.py writes here. Both scripts read this
# same constant so they cannot drift. The file is git-ignored because it
# contains client PII.
LEADS_INDEX_PATH = Path(
    os.environ.get(
        "LOFTY_LEADS_INDEX_PATH",
        str(Path(__file__).resolve().parent.parent / "data" / "leads_index.json"),
    )
)

# Warn (don't block) if the local index is older than this many days.
# v1.10 dropped the default from 14 to 2 because the daily Cowork
# scheduled task is supposed to keep the index fresh; any gap longer
# than 2 days means a scheduled-task failure that's worth flagging.
LEADS_INDEX_STALENESS_DAYS = float(
    os.environ.get("LOFTY_LEADS_INDEX_STALENESS_DAYS", "2")
)

# Where _load_leads_index reads from.
#   "worker"  - fetch from the leads-index Cloudflare Worker /export
#               endpoint. Falls back to the local file on any Worker error.
#   anything else (default) - read from the local leads_index.json file
#               built by scripts/refresh_leads_index.py.
LEADS_INDEX_SOURCE = os.environ.get("LOFTY_LEADS_INDEX_SOURCE", "file").strip().lower()

# Worker URLs are not defaulted to a specific subdomain. Each recipient
# fills in their own deployed Worker URL via .env. Methods that need
# one but find it missing raise a clear error via _require_env.
LEADS_INDEX_WORKER_URL = os.environ.get("LEADS_INDEX_WORKER_URL", "")
JOTFORM_WORKER_URL = os.environ.get("JOTFORM_WORKER_URL", "")


# -----------------------------------------------------------------
# Client
# -----------------------------------------------------------------
class LoftyAPI:
    """Minimal wrapper around the Lofty REST API."""

    def __init__(self, api_key=None, base_url=None):
        self.api_key = api_key or _require_env(
            "LOFTY_API_KEY",
            hint="Your Lofty personal access token (long string starting with eyJ).",
        )
        self.base_url = base_url or BASE_URL
        self._last_call = 0.0
        # Memoized leads index. Loaded on first find_client / prepare_showing
        # call, reused for the rest of this LoftyAPI instance's life.
        self._leads_index = None
        # Set by _load_leads_index_from_file when the index is older
        # than LEADS_INDEX_STALENESS_DAYS. find_client surfaces this
        # to the caller as a structured `stale_warning` key so Claude
        # can offer to refresh without the user touching a terminal.
        self._index_stale_info = None

    # Phase 2 Worker base URLs are class-level so subclasses can override
    # for testing. Each is read from os.environ at class load time.
    SHORTENER_BASE = os.environ.get("SHORTENER_BASE_URL", "")
    SHOWING_SMS_BASE = os.environ.get("SHOWING_SMS_BASE_URL", "")

    @property
    def SHORTENER_API_KEY(self):
        return _require_env(
            "SHORTENER_API_KEY",
            hint="Bearer token for your short-links Cloudflare Worker.",
        )

    # ------------------------- internals ------------------------

    def _rate_limit(self):
        """Enforce the 10 req/min Lofty rate limit."""
        elapsed = time.time() - self._last_call
        if elapsed < RATE_LIMIT_DELAY:
            time.sleep(RATE_LIMIT_DELAY - elapsed)
        self._last_call = time.time()

    def _request(self, method, path, body=None, query_params=None):
        """Send an HTTP request to Lofty.

        Auth header uses "token", not "Bearer" (Lofty quirk #1).

        Content-Type is sent on EVERY request, regardless of method. Two
        endpoints (`/v1.0/team-features/lead-ponds`,
        `/v1.0/teamFeatures/listCustomField`) reject GET without the header,
        and ALL DELETE endpoints reject without it. Sending it on every
        method is verified safe across the methods this client uses
        (verified live in May 2026; supersedes the earlier "GET must not
        send Content-Type" guidance).
        """
        self._rate_limit()

        url = f"{self.base_url}{path}"
        if query_params:
            filtered = {k: str(v) for k, v in query_params.items()
                        if v is not None and v != ""}
            if filtered:
                url += "?" + urllib.parse.urlencode(filtered)

        headers = {
            "Authorization": f"token {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        data = json.dumps(body).encode("utf-8") if body else None

        req = urllib.request.Request(url, data=data, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    return raw
        except urllib.error.HTTPError as e:
            error_body = ""
            try:
                error_body = e.read().decode("utf-8") if e.fp else ""
            except Exception:
                pass
            return {
                "error": True,
                "status": e.code,
                "statusText": e.reason,
                "body": error_body,
            }
        except urllib.error.URLError as e:
            return {"error": True, "message": str(e.reason)}

    # ------------------------- account --------------------------

    def get_me(self):
        """Return your Lofty user record. Use this to verify the key works."""
        return self._request("GET", "/v1.0/me")

    def get_organization(self):
        """Return your Lofty organization record."""
        return self._request("GET", "/v1.0/org")

    def get_members(self, page=1, page_size=50):
        """List your team members."""
        return self._request("GET", "/v1.0/members",
                             query_params={"page": page, "pageSize": page_size})

    # ------------------------- leads (read) ---------------------

    def search_leads(self, page=1, page_size=25):
        """List leads, paginated.

        WARNING: Lofty silently ignores `keyword`, `page`, `sortField`,
        and `startTime` on this endpoint (Lofty quirks #2 and #29). The
        `page` parameter is accepted but ignored: page=2 returns the
        same 25 leads as page=1. To paginate, use scrollId from the
        response's _metadata. Default sort is newest first
        (createTime DESC), which is exactly what find_client's
        new-contact fallback relies on.
        """
        return self._request("GET", "/v1.0/leads",
                             query_params={"page": page, "pageSize": page_size})

    def _search_recent_leads(self, max_pages=3, page_size=25):
        """Yield leads from /v1.0/leads in default order (createTime DESC),
        using scrollId pagination to walk multiple pages.

        Why this exists: /v1.0/leads silently ignores keyword, page,
        sortField, and sortDirection (quirks #2 and #29). scrollId is
        the only working pagination mechanism. Default sort is newest
        first, which is exactly what the new-contact fallback in
        find_client needs.

        Args:
            max_pages: How many pages to walk before stopping.
            page_size: Page size hint. Hard-capped at 25 by the API.

        Yields:
            Raw lead dicts from the API response.
        """
        scroll_id = None
        for _ in range(max_pages):
            params = {"pageSize": page_size}
            if scroll_id:
                params["scrollId"] = scroll_id
            resp = self._request("GET", "/v1.0/leads", query_params=params)
            leads = resp.get("leads", []) if isinstance(resp, dict) else []
            if not leads:
                break
            for l in leads:
                yield l
            scroll_id = (resp.get("_metadata") or {}).get("scrollId")
            if not scroll_id:
                break

    def get_lead(self, lead_id):
        """Get full details for a single lead. Auto-unwraps the {"lead": {...}} envelope."""
        result = self._request("GET", f"/v1.0/leads/{lead_id}")
        if isinstance(result, dict) and "lead" in result:
            return result["lead"]
        return result

    def get_lead_activities(self, lead_id, limit=20):
        """Get a lead's activity feed (browses, searches, favorites, requests).

        IMPORTANT: must use v1.0. The v2.0 endpoint returns empty (Lofty quirk #3).
        """
        return self._request("GET", f"/v1.0/leads/{lead_id}/activities",
                             query_params={"limit": limit})

    def get_lead_segments(self, lead_id):
        """Return the list of segments (Lofty calls them "groups" in the
        web UI) currently attached to a lead.

        Read-only: Lofty's public API does NOT expose segment writes.
        Segment management routes through the signed-request internal
        API at crm.lofty.com/api/, which kit code does not call. To
        add or remove a segment, use the Lofty web UI.

        Returns a list of segment dicts (or strings, depending on
        Lofty's response shape; we pass through whatever comes back).
        Empty list if the lead has no segments.
        """
        lead = self.get_lead(lead_id)
        if isinstance(lead, dict) and lead.get("error"):
            return lead
        if not isinstance(lead, dict):
            return []
        return lead.get("segments") or []

    # ------------------------- leads (write) --------------------

    def create_lead(self, first_name, last_name, email=None, phone=None,
                    source=None, tags=None):
        """Create a new lead."""
        body = {
            "firstName": first_name,
            "lastName": last_name,
        }
        if email:
            body["emails"] = [email]
        if phone:
            body["phones"] = [phone]
        if source:
            body["source"] = source
        if tags:
            body["tags"] = tags
        return self._request("POST", "/v1.0/leads", body=body)

    def update_lead(self, lead_id, **fields):
        """Update fields on a lead.

        WARNING about the `tags` field: `update_lead(lead_id, tags=[...])`
        REPLACES the entire tag list. A naive "append a tag" pattern
        silently deletes every other tag the lead had. Also, list items
        are tag NAMES (strings), not tagIds; passing integers auto-
        creates new tags whose names are those integers, which pollutes
        your team tag library. For safe tag operations, use the
        wrappers below: add_tag, remove_tag, set_tags.
        """
        return self._request("PUT", f"/v1.0/leads/{lead_id}", body=fields)

    # ------------------------- tag-write helpers ----------------

    def _read_tag_names(self, lead_id):
        """Read the current list of tag names on a lead.

        Lofty's read responses store tags either as a list of strings
        or as a list of {tagName, tagId, ...} dicts depending on the
        endpoint and account. This helper normalizes both shapes to a
        list of unique name strings.
        """
        lead = self.get_lead(lead_id)
        if isinstance(lead, dict) and lead.get("error"):
            raise RuntimeError(
                f"get_lead({lead_id}) failed: {lead}"
            )
        raw = (lead.get("tags") if isinstance(lead, dict) else None) or []
        names = []
        seen = set()
        for t in raw:
            n = None
            if isinstance(t, dict):
                n = t.get("tagName") or t.get("name")
            elif isinstance(t, str):
                n = t
            if n and n not in seen:
                seen.add(n)
                names.append(n)
        return names

    def _log_tag_event(self, action, lead_id, before, after, tag=None):
        """Push a tag-change event into the unified kit history.

        Best-effort: a failed log write never raises. The history file
        is data/.kit-history.jsonl (managed by scripts/kit_history.py).
        Inspect it when a Lofty automation seems to have done something
        unexpected with tags.
        """
        try:
            from kit_history import log_event
            log_event(
                "tag_change",
                action=action,
                lead_id=lead_id,
                tag=tag,
                before=before,
                after=after,
            )
        except Exception:
            pass

    def add_tag(self, lead_id, tag_name):
        """Add a single tag to a lead without destroying existing tags.

        Reads the current tag names, appends the new one if it isn't
        already there, and writes the merged list back. Logs before
        and after to data/.kit-history.jsonl so the change is
        recoverable.

        Returns {"changed": bool, "tags": [...names], "result": <api>}.
        """
        if not isinstance(tag_name, str) or not tag_name.strip():
            raise ValueError("tag_name must be a non-empty string")
        before = self._read_tag_names(lead_id)
        if tag_name in before:
            self._log_tag_event(
                "add_noop", lead_id, before, before, tag=tag_name
            )
            return {"changed": False, "tags": before}
        after = before + [tag_name]
        result = self.update_lead(lead_id, tags=after)
        self._log_tag_event("add", lead_id, before, after, tag=tag_name)
        return {"changed": True, "tags": after, "result": result}

    def remove_tag(self, lead_id, tag_name):
        """Remove a single tag from a lead, leaving the others alone.

        Reads current names, filters, writes the result back. No-op
        (still logged) when the tag isn't there. Returns the same
        shape as add_tag.
        """
        if not isinstance(tag_name, str) or not tag_name.strip():
            raise ValueError("tag_name must be a non-empty string")
        before = self._read_tag_names(lead_id)
        if tag_name not in before:
            self._log_tag_event(
                "remove_noop", lead_id, before, before, tag=tag_name
            )
            return {"changed": False, "tags": before}
        after = [t for t in before if t != tag_name]
        result = self.update_lead(lead_id, tags=after)
        self._log_tag_event("remove", lead_id, before, after, tag=tag_name)
        return {"changed": True, "tags": after, "result": result}

    def set_tags(self, lead_id, tag_names):
        """Explicit replace: set the lead's tags to exactly this list.

        Use this only when the destructive semantic is what you want
        (e.g., "clear tags then apply the canonical set"). For the
        common case of adding or removing one tag, use add_tag /
        remove_tag instead.
        """
        if not isinstance(tag_names, list):
            raise TypeError("tag_names must be a list of strings")
        for t in tag_names:
            if not isinstance(t, str):
                raise TypeError(
                    "tag_names entries must be strings (NAMES, not "
                    "tagIds; passing integers auto-creates garbage tags)"
                )
        before = self._read_tag_names(lead_id)
        after = list(tag_names)
        result = self.update_lead(lead_id, tags=after)
        self._log_tag_event("set", lead_id, before, after)
        return {
            "changed": sorted(before) != sorted(after),
            "tags": after,
            "result": result,
        }

    # ------------------------- notes ----------------------------

    def create_note(self, lead_id, content):
        """Create a note on a lead.

        IMPORTANT: POST to /v1.0/notes with leadId in the body. The intuitive
        path /v1.0/leads/<id>/notes returns 404 (Lofty quirk #4). leadId must
        be a number, not a string.
        """
        return self._request("POST", "/v1.0/notes",
                             body={"leadId": int(lead_id), "content": content})

    def get_notes(self, lead_id=None, page=0, page_size=20):
        """List notes, optionally filtered by lead.

        Pagination param is `pageNumber` (not `page`); zero-indexed.
        Returns {"notes": [...]} envelope.
        """
        return self._request("GET", "/v1.0/notes",
                             query_params={"leadId": lead_id,
                                           "pageNumber": page,
                                           "pageSize": page_size})

    def update_note(self, note_id, content):
        """Update an existing note. PUT /v1.0/notes/<id> with {content}."""
        return self._request("PUT", f"/v1.0/notes/{note_id}",
                             body={"content": content})

    def delete_note(self, note_id):
        """Delete a note.

        Requires the Content-Type header on DELETE; the v1.4 _request always
        sends it. Earlier versions of this client (pre-v1.4) silently failed
        because they only sent Content-Type on POST/PUT.
        """
        return self._request("DELETE", f"/v1.0/notes/{note_id}")

    # ------------------------- listings (MLS) -------------------

    def search_listings(self, filter_conditions=None, sort_fields=None,
                        page=1, page_size=25, sold=False, scope="all"):
        """Search the MLS using Lofty's listings index.

        POST to /v2.0/listings/search. The /v1.0/listing endpoint exists but
        does not work with personal API key auth (Lofty quirk #10), so this
        is the right path for MLS lookup.

        Filter syntax:
          - Range fields use comma-separated min,max: "price": "400000,650000",
            "beds": "3,", "sqft": ",2500".
          - Multi-value fields use lists: "propertyType": ["Single Family", "Condo"].
          - Location uses a nested object:
            {"location": {"city": ["Portland"], "zipCode": ["97225"]}}.

        Sort options: "PRICE_DESC", "PRICE_ASC", "MLS_LIST_DATE_L_DESC".

        Scope: "all" (full MLS), "my" (your listings), "office" (your office).

        Lofty body keys are NOT the obvious names (quirk #11). Keep the camelCase
        body keys exactly as written: searchScope, soldFlag, filterConditions,
        sortFields, pageNum, pageSize. Sending "scope", "sold", "filter", "sort",
        or "page" returns 0 results with no error.
        """
        return self._request("POST", "/v2.0/listings/search", body={
            "searchScope": scope,
            "soldFlag": sold,
            "filterConditions": filter_conditions or {},
            "sortFields": sort_fields or ["MLS_LIST_DATE_L_DESC"],
            "pageNum": page,
            "pageSize": page_size,
        })

    # ------------------------- tasks / calendar -----------------

    def get_tasks(self, lead_id=None, start_time=None, end_time=None,
                  include_finished=False, page=0, page_size=50,
                  timezone_code="America/Los_Angeles"):
        """List tasks and appointments with optional filters.

        All filters are optional. Without them, returns the user's full
        task list. start_time / end_time use ISO 8601 with offset.
        """
        return self._request("GET", "/v2.0/calendar", query_params={
            "leadId": lead_id,
            "startTime": start_time,
            "endTime": end_time,
            "timeZoneCode": timezone_code,
            "includeFinished": str(include_finished).lower(),
            "page": page,
            "pageSize": page_size,
        })

    def update_task(self, calendar_id, **fields):
        """Update a task or appointment. Pass any of:
        content, startAt, endAt, timeZoneCode, address, leadId.
        """
        return self._request("PUT", f"/v2.0/calendar/{calendar_id}",
                             body=fields)

    def complete_task(self, calendar_id):
        """Mark a task or appointment as completed.

        POST to /v2.0/calendar/<id>/finish (no body). Use uncomplete_task
        to reopen.
        """
        return self._request("POST", f"/v2.0/calendar/{calendar_id}/finish")

    def uncomplete_task(self, calendar_id):
        """Reopen a completed task. POST /v2.0/calendar/<id>/unfinish."""
        return self._request("POST", f"/v2.0/calendar/{calendar_id}/unfinish")

    def delete_task(self, calendar_id):
        """Delete a task or appointment."""
        return self._request("DELETE", f"/v2.0/calendar/{calendar_id}")

    def get_available_meeting_slots(self, start_time, end_time,
                                    timezone_code="America/Los_Angeles",
                                    limit=10):
        """Find open meeting time slots within a date range.

        Times are ISO 8601 with offset. start_time must be in the future,
        within 90 days. Returns up to `limit` candidate slots.
        """
        return self._request("GET", "/v2.0/calendar/meetings/available",
                             query_params={
                                 "startTime": start_time,
                                 "endTime": end_time,
                                 "timeZoneCode": timezone_code,
                                 "limit": limit,
                             })

    def create_task(self, lead_id, content, start_at, end_at,
                    task_way="Call", task_type="TASK",
                    assigned_role=None, address=None,
                    timezone_code="America/Los_Angeles"):
        """Create a task or appointment on a lead.

        POST to /v2.0/calendar. task_type accepts "TASK" or "APPOINTMENT".

        IMPORTANT: do NOT use task_type="APPOINTMENT" for showings. That
        triggers listing-agent approval in Lofty. For showings, use the
        prepare_showing helper pattern (Google Calendar event + Lofty
        showing-log note) once added. See references/extending.md.

        Args:
            lead_id: Associated Lofty lead ID.
            content: Description text shown on the task in Lofty.
            start_at: ISO 8601 with offset, e.g. "2026-05-08T14:00:00-07:00".
            end_at:   ISO 8601 with offset.
            task_way: For TASK type: "Call", "Email", "Text", "Meeting", "Other".
            task_type: "TASK" or "APPOINTMENT".
            assigned_role: Optional. "Agent" or "Assistant".
            address: Optional. Used for APPOINTMENT type.
            timezone_code: Defaults to America/Los_Angeles. Required by Lofty.

        Body key quirks (Lofty quirk #12):
          - Lofty wants "taskWay", not "way"
          - "timeZoneCode" is required
          - "assignedRole" values are "Agent" or "Assistant", not "ASSIGNED"
        """
        body = {
            "type": task_type,
            "content": content,
            "leadId": int(lead_id),
            "startAt": start_at,
            "endAt": end_at,
            "timeZoneCode": timezone_code,
        }
        if task_way:
            body["taskWay"] = task_way
        if assigned_role:
            body["assignedRole"] = assigned_role
        if address:
            body["address"] = address
        return self._request("POST", "/v2.0/calendar", body=body)

    # ------------------------- messaging ------------------------

    def send_email(self, lead_id, subject, content):
        """Send an email to a lead through Lofty.

        POST to /v1.0/message/email/send. Sends from the agent's connected
        email account. Returns success even when delivery fails downstream,
        so trust the user's confirmation, not the response code.

        Skill rule (enforced in SKILL.md): ALWAYS confirm subject and content
        with the user before calling this. The Python wrapper does not gate
        the send.
        """
        return self._request("POST", "/v1.0/message/email/send",
                             body={"leadId": int(lead_id),
                                   "subject": subject,
                                   "content": content})

    def send_sms(self, lead_id, content):
        """Send an SMS to a lead through Lofty.

        POST to /v1.0/message/sms/send. Uses the agent's Lofty phone number.

        Skill rule (enforced in SKILL.md): ALWAYS confirm content with the
        user before calling this. The Python wrapper does not gate the send.
        """
        return self._request("POST", "/v1.0/message/sms/send",
                             body={"leadId": int(lead_id), "content": content})

    # ------------------------- communication history ------------

    def get_call_history(self, lead_id=None, page=0, page_size=20):
        """List call records, optionally filtered by lead.

        Returns {"calls": [...]}. Each call has: agentId, direction, id,
        leadId, callTime, callOutcome, callType, durationSec, etc.
        Webhook list 6 fires only on MANUAL or LOGGED calls, not on
        automated dialer activity.
        """
        return self._request("GET", "/v1.0/communication/call",
                             query_params={"leadId": lead_id,
                                           "pageNumber": page,
                                           "pageSize": page_size})

    def get_email_history(self, lead_id=None, page=0, page_size=20):
        """List email history, optionally filtered by lead.

        Returns {"emails": [...]}. Each row has: agentId, direction,
        emailEventTime, emailSubject, emailType, eventType, fromPond, id,
        leadId.
        """
        return self._request("GET", "/v1.0/communication/email",
                             query_params={"leadId": lead_id,
                                           "pageNumber": page,
                                           "pageSize": page_size})

    def get_text_history(self, lead_id=None, page=0, page_size=20):
        """List SMS history, optionally filtered by lead.

        Returns {"texts": [...]}. Each row has: agentId, direction, id,
        leadId, textContent, textOutcome, textTime, textType.
        """
        return self._request("GET", "/v1.0/communication/text",
                             query_params={"leadId": lead_id,
                                           "pageNumber": page,
                                           "pageSize": page_size})

    # ------------------------- timeline & alerts ----------------

    def get_system_logs(self, lead_id, start_time=None, end_time=None,
                        page=0, page_size=50):
        """The unified human-readable timeline for a single lead.

        Returns {"hasMore": int, "timeLines": [...]}. Each entry has:
        agentId, content (human prose), createTime, fromFirstName /
        fromLastName / fromId / fromType, id, leadId, refId, sticky,
        timelineTime, timelineType, toFirstName / toLastName.

        This is the friendliest read surface in the API: calls, emails,
        texts, notes, stage transitions, manual logs - all in chronological
        order with prose `content` ready to summarize. Reach for this
        before assembling per-channel pulls.

        start_time / end_time are ISO 8601 strings (optional).
        """
        return self._request("GET", "/v1.0/systemLogs",
                             query_params={"leadId": lead_id,
                                           "startTime": start_time,
                                           "endTime": end_time,
                                           "pageNumber": page,
                                           "pageSize": page_size})

    def get_alerts(self, lead_id):
        """Get listing alerts configured for a lead.

        Returns {"data": [...], "status": {"code", "msg", "trace"}}.
        Use this to see saved searches the lead has subscribed to,
        without configuring them via the UI.
        """
        return self._request("GET", f"/v1.0/alerts/ids/{lead_id}")

    def add_lead_activity(self, lead_id, content, activity_type=None):
        """Log a manual activity entry on a lead's timeline.

        POST /v1.0/leads/<id>/activity with {content, type?}. Useful for
        recording offline events ("Met at open house", "Buyer agreement
        signed") so the timeline reflects more than just digital touches.

        activity_type is optional and free-form. Common values: "note",
        "meeting", "showing", "call_attempt".
        """
        body = {"content": content}
        if activity_type:
            body["type"] = activity_type
        return self._request("POST", f"/v1.0/leads/{lead_id}/activity",
                             body=body)

    # ------------------------- transactions ---------------------

    def get_transactions(self, lead_id):
        """Get all transactions for a lead.

        Returns a list (not a dict envelope). Each transaction has type,
        status, price, address, and lifecycle timestamps.
        """
        return self._request("GET", f"/v1.0/leads/{lead_id}/transactions")

    def create_transaction(self, lead_id, trans_type=None, status=None,
                           price=None, address=None):
        """Create a new transaction record on a lead.

        trans_type: "BUYER", "SELLER", "RENTAL" (your team config).
        status: typical values are "ACTIVE", "PENDING", "CLOSED".
        Confirm naming with your team's transaction settings before calling.
        """
        body = {}
        if trans_type:
            body["type"] = trans_type
        if status:
            body["status"] = status
        if price:
            body["price"] = price
        if address:
            body["address"] = address
        return self._request("POST", f"/v1.0/leads/{lead_id}/transaction",
                             body=body)

    # ------------------------- team & metadata ------------------

    def get_me(self):
        """Get your own Lofty user profile.

        Note: the `id` field returned here is a SHORT integer (e.g.
        113209), distinct from the 15-digit `creatorUserId` /
        `assignedUserId` form that appears on every other record. Both
        identify the same user; treat them as different addressing
        schemes. See quirks.md for details.
        """
        return self._request("GET", "/v1.0/me")

    def get_organization(self):
        """Get your Lofty organization details.

        Returns {enterpriseInfo, orgType}. enterpriseInfo includes
        groupId, groupName, profileId, profileName, visibleOrgInfoList.
        """
        return self._request("GET", "/v1.0/org")

    def get_members(self, page=0, page_size=25):
        """List team members.

        Returns {"_metadata": {...}, "members": [...]}.
        Page size is hard-capped at 25 by Lofty (same silent-ignore
        pattern as /v1.0/leads). Use scrollId from _metadata for the
        next page if you have a large team.
        """
        return self._request("GET", "/v1.0/members",
                             query_params={"pageNumber": page,
                                           "pageSize": page_size})

    def get_tags(self):
        """List all tags on your team.

        Returns a list, NOT a dict envelope. Each entry has leadId, tagId,
        tagName, createTime, updateTime, creatorUserId, visibleType.

        Important: this endpoint returns BOTH tag definitions
        (`leadId == 0`) AND applied instances (`leadId > 0`). Filter as
        needed:
            defs = [t for t in api.get_tags() if t['leadId'] == 0]
            on_lead = [t for t in api.get_tags() if t['leadId'] == 12345]
        """
        return self._request("GET", "/v1.0/teamFeatures/listTag")

    def get_custom_fields(self):
        """List the custom fields configured on your team.

        Returns a list of {attributeName, attributeType, value, params}.
        attributeType is "date", "text", "number", or "dropdown".
        Use this to introspect the schema before reading or writing
        custom field values on a lead via update_lead.
        """
        return self._request("GET", "/v1.0/teamFeatures/listCustomField")

    def get_lead_ponds(self):
        """List lead ponds (shared lead pools) configured on your team.

        Returns a list (possibly empty). Each pond has id, name, members,
        and routing rules.
        """
        return self._request("GET", "/v1.0/team-features/lead-ponds")

    def get_webhooks(self):
        """List active webhook subscriptions.

        Returns a list. Each subscription has callbackUrl, limit, listId,
        subscribeId, teamId, vendorId.
        """
        return self._request("GET", "/v1.0/webhooks")

    def create_webhook(self, list_id, callback_url):
        """Create a webhook subscription.

        Lofty quirk: the body field is `callbackUrl`, NOT `url`. Sending
        `url` returns error 20049 "Please enter url in right format" -
        a misleading message that points at the value, not the key.

        Multiple subscriptions on the same listId are allowed (verified
        live). Useful for running your own Worker alongside an existing
        third-party subscription on the same list.

        Event lists (12 total): 1=Agent, 2=Lead Info, 3=Lead Activity,
        4=Listing Alert, 5=Transaction, 6=Call, 7=Email, 8=Text, 9=Note,
        10=Task, 11=Appointment, 12=Pipeline Change.
        """
        return self._request("POST", "/v1.0/webhook",
                             body={"listId": list_id,
                                   "callbackUrl": callback_url})

    def delete_webhook(self, subscribe_id):
        """Delete a webhook subscription.

        DELETE requires Content-Type, which v1.4's _request always sends.
        Returns the Worker response, or {"deleted": True, "subscribeId": ...}
        on empty 200.
        """
        return self._request("DELETE", f"/v1.0/webhook/{subscribe_id}")

    # ------------------------- owner profile --------------------

    def _owner_profile(self):
        """Read the agent's identity from environment variables.

        Used by build_showing_invite for the email signature, by find_client
        for the lead-search self-exclusion, and by prepare_showing for the
        calendar identifier and showing-log MLS stamp.

        Returns a dict with these keys (each may be empty if unset):
            full_name, brokerage, phone, email, last_name_lower, mls_name

        Empty values are tolerated. The skill prompts the recipient to fill
        these during Easy Mode setup.
        """
        return {
            "full_name": os.environ.get("OWNER_FULL_NAME", "").strip(),
            "brokerage": os.environ.get("OWNER_BROKERAGE", "").strip(),
            "phone": os.environ.get("OWNER_PHONE", "").strip(),
            "email": os.environ.get("OWNER_EMAIL", "").strip(),
            "last_name_lower": os.environ.get("OWNER_LAST_NAME_LOWER", "").strip().lower(),
            "mls_name": os.environ.get("MLS_NAME", "").strip(),
        }

    # ------------------------- leads index ----------------------

    def _load_leads_index(self):
        """Load and cache the leads index, in-process.

        Source is controlled by LOFTY_LEADS_INDEX_SOURCE:
          "worker" - fetch from the leads-index Cloudflare Worker /export.
                     Falls back to the local file on any Worker error so
                     the pipeline keeps working during outages.
          anything else (default) - read from local leads_index.json.

        Returns the full index dict: {refreshed_at, count, leads: [...]}.
        Memoized for the life of this LoftyAPI instance.

        Raises RuntimeError with a clear setup message if neither source
        produces usable data.
        """
        if self._leads_index is not None:
            return self._leads_index

        if LEADS_INDEX_SOURCE == "worker":
            try:
                data = self._load_leads_index_from_worker()
                self._leads_index = data
                return data
            except Exception as e:
                # Don't blow up the workflow just because the Worker is
                # momentarily unreachable. Try the local file next.
                print(
                    f"[warn] leads-index Worker unreachable ({e}); "
                    f"falling back to local file.",
                    flush=True,
                )

        data = self._load_leads_index_from_file()
        self._leads_index = data
        return data

    def _load_leads_index_from_worker(self):
        """Fetch the leads index from the Cloudflare Worker /export endpoint.

        Requires LEADS_INDEX_EXPORT_API_KEY (Bearer auth on the Worker).
        Returns the same shape as the local file. Raises on network
        failure, non-200, or invalid JSON; the dispatcher catches and
        falls back to the local file.
        """
        if not LEADS_INDEX_WORKER_URL:
            raise RuntimeError(
                "LEADS_INDEX_WORKER_URL is not set. Add it to .env, or "
                "switch LOFTY_LEADS_INDEX_SOURCE back to 'file'."
            )
        export_key = _require_env(
            "LEADS_INDEX_EXPORT_API_KEY",
            hint="Bearer token for the leads-index Worker /export endpoint.",
        )
        url = f"{LEADS_INDEX_WORKER_URL}/export"
        req = urllib.request.Request(
            url,
            method="GET",
            headers={
                "Authorization": "Bearer " + export_key,
                "User-Agent": "lofty-api-python/1.0",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode("utf-8"))
        if "leads" not in data:
            raise RuntimeError(
                f"Worker /export response missing 'leads' key. "
                f"Top-level keys returned: {list(data.keys())}"
            )
        return data

    def _load_leads_index_from_file(self):
        """Read the leads index from the local JSON file.

        Hard-errors with setup instructions if the file is missing.
        Prints a (non-blocking) staleness warning if the file is older
        than LEADS_INDEX_STALENESS_DAYS.
        """
        path = LEADS_INDEX_PATH
        if not path.is_file():
            raise RuntimeError(
                "Local leads index not found.\n\n"
                f"  Expected: {path}\n\n"
                "find_client needs this file to match clients beyond the\n"
                "25 most recently created leads. Lofty's /v1.0/leads endpoint\n"
                "silently ignores the keyword parameter, so older clients\n"
                "would otherwise return 'none' even when they exist.\n\n"
                "Two ways to fix:\n"
                "  1. Set LOFTY_LEADS_INDEX_SOURCE=worker in .env to read\n"
                "     from your leads-index Cloudflare Worker (preferred -\n"
                "     stays fresh via webhooks, no manual refresh needed).\n"
                "  2. Or build the local file once with:\n"
                "         python3 scripts/refresh_leads_index.py\n"
                "     Takes about 3 minutes for 650 leads. Becomes the\n"
                "     fallback used when the Worker is down."
            )

        try:
            data = json.loads(path.read_text())
        except Exception as e:
            raise RuntimeError(
                f"leads_index.json exists but could not be parsed: {e}\n"
                f"Path: {path}\n"
                "Try deleting it and re-running scripts/refresh_leads_index.py."
            )

        refreshed_ms = data.get("refreshed_at_epoch_ms", 0)
        if refreshed_ms:
            age_days = (time.time() * 1000 - refreshed_ms) / (1000 * 60 * 60 * 24)
            if age_days > LEADS_INDEX_STALENESS_DAYS:
                age_int = int(age_days)
                message = (
                    f"Your leads index hasn't refreshed in {age_int} "
                    f"day{'s' if age_int != 1 else ''}. The daily "
                    f"scheduled task may have failed. I can run a "
                    f"refresh now, or you can ask me to check kit health."
                )
                # Record on the instance so find_client surfaces it
                # as a structured `stale_warning` value (Claude reads
                # the action key to decide what to offer the user).
                self._index_stale_info = {
                    "age_days": age_int,
                    "message": message,
                    "action": "ask_to_refresh",
                }
                print(f"[warn] {message}", flush=True)

        return data

    def find_client(self, name, exclude_stages=None, fallback_pages=3):
        """Search leads by name. Reads the local index first, then falls
        back to scanning the most recently created leads via the API.

        The fallback handles the new-contact case: when you create a
        lead in Lofty and immediately ask Claude to find them, the
        index has not synced yet (the leads-index Worker has a 1-5
        minute webhook delivery SLA, and the file fallback is only as
        fresh as the last refresh_leads_index.py run). The API's
        default sort is newest first (quirk #29), so a newly created
        contact is always at the top of page 1.

        Returns one of:
            {"match": <slim_lead>, "source": "index" | "api"}
            {"candidates": [<slim>, ...], "source": "index" | "api"}
            {"none": True, "source": "index+api", "scanned": int}

        The "source" key is additive. Existing callers that read
        result["match"] / result["candidates"] / result["none"] keep
        working unchanged.

        Args:
            name: Substring to match on first/last/full name
                  (case-insensitive).
            exclude_stages: Stages to skip. Defaults to
                            ["DNC", "Archived", "Agents / Vendors"].
            fallback_pages: How many pages of /v1.0/leads (sorted by
                            newest first) to scan when the index
                            misses. 0 disables the fallback (matches
                            pre-v1.4.1 behavior). Default 3 covers the
                            most recent ~75 leads, which is enough for
                            "I just created this contact" without
                            spending too long at the rate limit.

        OWNER_LAST_NAME_LOWER (from .env) is excluded if set, so the
        agent's own record never bubbles up in name searches.

        Requires the leads index. Raises RuntimeError with setup
        instructions if the index can't be loaded.
        """
        if exclude_stages is None:
            exclude_stages = ["DNC", "Archived", "Agents / Vendors"]

        name_lower = name.strip().lower()
        if not name_lower:
            return self._attach_stale_warning(
                {"none": True, "source": "index", "scanned": 0}
            )

        owner_last = self._owner_profile()["last_name_lower"]
        index = self._load_leads_index()
        leads = index.get("leads", [])

        matches = []
        seen_ids = set()
        for l in leads:
            if l.get("stage") in exclude_stages:
                continue
            if owner_last and l.get("lastNameLower") == owner_last:
                continue
            first_l = l.get("firstNameLower", "")
            last_l = l.get("lastNameLower", "")
            full_l = l.get("fullNameLower", "")
            if (name_lower in full_l
                    or (first_l and name_lower in first_l)
                    or (last_l and name_lower in last_l)):
                matches.append({
                    "leadId": l.get("leadId"),
                    "firstName": l.get("firstName"),
                    "lastName": l.get("lastName"),
                    "email": (l.get("emails") or [""])[0],
                    "phone": (l.get("phones") or [""])[0],
                    "stage": l.get("stage", ""),
                    "score": l.get("score"),
                    "tags": l.get("tags") or [],
                    "segments": l.get("segments") or [],
                })
                if l.get("leadId") is not None:
                    seen_ids.add(l.get("leadId"))

        if len(matches) == 1:
            return self._attach_stale_warning(
                {"match": matches[0], "source": "index"}
            )
        if len(matches) > 1:
            return self._attach_stale_warning(
                {"candidates": matches, "source": "index"}
            )

        # Index missed. If the caller disabled the fallback, return now.
        if fallback_pages <= 0:
            return self._attach_stale_warning(
                {"none": True, "source": "index", "scanned": 0}
            )

        # Walk the most recently created leads via the API. New contacts
        # land at the top of page 1 because of the default sort.
        api_matches = []
        scanned = 0
        for raw in self._search_recent_leads(max_pages=fallback_pages):
            scanned += 1
            if raw.get("stage") in exclude_stages:
                continue
            first_lower = (raw.get("firstName") or "").strip().lower()
            last_lower = (raw.get("lastName") or "").strip().lower()
            full_lower = (first_lower + " " + last_lower).strip()
            if owner_last and last_lower == owner_last:
                continue
            if (name_lower in full_lower
                    or (first_lower and name_lower in first_lower)
                    or (last_lower and name_lower in last_lower)):
                lead_id = raw.get("leadId")
                if lead_id in seen_ids:
                    continue
                api_matches.append({
                    "leadId": lead_id,
                    "firstName": raw.get("firstName"),
                    "lastName": raw.get("lastName"),
                    "email": (raw.get("emails") or [""])[0],
                    "phone": (raw.get("phones") or [""])[0],
                    "stage": raw.get("stage", ""),
                    "score": raw.get("score"),
                    "tags": raw.get("tags") or [],
                    "segments": raw.get("segments") or [],
                })

        if len(api_matches) == 1:
            return self._attach_stale_warning(
                {"match": api_matches[0], "source": "api"}
            )
        if len(api_matches) > 1:
            return self._attach_stale_warning(
                {"candidates": api_matches, "source": "api"}
            )
        return self._attach_stale_warning(
            {"none": True, "source": "index+api", "scanned": scanned}
        )

    def _attach_stale_warning(self, result):
        """Optionally decorate find_client returns with a stale-index hint.

        Backward compatible: callers that don't read `stale_warning`
        keep working unchanged. Callers (or Claude) that read it can
        offer the user a refresh without the user touching a terminal.
        """
        if self._index_stale_info:
            result["stale_warning"] = self._index_stale_info
        return result

    def _client_dict_from_index(self, lead_id):
        """Return the slim client dict for a single lead_id.

        Same shape find_client returns under "match" / "candidates", read
        straight from the local leads index. Lets prepare_showing accept
        a lead_id when callers need to disambiguate two leads that share
        a name or phone. Returns None if the lead_id isn't in the index.
        """
        try:
            target_id = int(lead_id)
        except (TypeError, ValueError):
            return None

        index = self._load_leads_index()
        for l in index.get("leads", []):
            if l.get("leadId") == target_id:
                return {
                    "leadId": l.get("leadId"),
                    "firstName": l.get("firstName"),
                    "lastName": l.get("lastName"),
                    "email": (l.get("emails") or [""])[0],
                    "phone": (l.get("phones") or [""])[0],
                    "stage": l.get("stage", ""),
                    "score": l.get("score"),
                }
        return None

    # ------------------------- listing lookup -------------------

    def find_listing_by_address(self, full_address):
        """Find an Active MLS listing by full address (Lofty format).

        Input: 'STREET, CITY, STATE ZIP' e.g. '11513 SW BAMBI LN, Portland, OR 97223'

        Searches Active listings only in the parsed zip. Pending and Sold
        used to be checked as fallbacks; that masked typos because a wrong
        city or zip would silently return None. Showings are scheduled
        against Active listings, so Active-only is the right scope.

        Returns one of:
            slim listing dict (success): keys include address, streetAddress,
              city, state, zipCode, price, beds, baths, sqft, propertyType,
              mlsListingId, loftyListingId, listingStatus, siteDetailLink,
              mlsOrgId.
            {"error": "missing_zip", "message": "..."}: address has no zip.
            {"error": "address_not_found", "message": "...", "zipCode": "..."}:
              zip parsed fine but no Active listing in that zip matched the
              street segment.

        Callers MUST check for an "error" key on the result.
        """
        import re
        # Last 5-digit number is the zip. Accept optional -4-digit extension.
        zip_matches = re.findall(r"\b(\d{5})(?:-\d{4})?\b", full_address)
        if not zip_matches:
            return {
                "error": "missing_zip",
                "message": (
                    f"Could not parse a zip code from '{full_address}'. "
                    f"Use Lofty address format: 'STREET, CITY, STATE ZIP', "
                    f"e.g. '11513 SW BAMBI LN, Portland, OR 97223'."
                ),
            }
        zipcode = zip_matches[-1]
        street_part = full_address.split(",")[0].strip().upper()

        def check(l):
            addr_upper = (l.get("streetAddress") or "").upper()
            if street_part in addr_upper or addr_upper in street_part:
                return {
                    "address": l.get("address"),
                    "streetAddress": l.get("streetAddress"),
                    "city": l.get("city"),
                    "state": l.get("state"),
                    "zipCode": l.get("zipCode"),
                    "price": l.get("price"),
                    "beds": l.get("bedrooms"),
                    "baths": l.get("bathrooms"),
                    "sqft": l.get("sqft"),
                    "propertyType": l.get("propertyType"),
                    "mlsListingId": l.get("mlsListingId"),
                    "loftyListingId": l.get("id"),
                    "listingStatus": l.get("listingStatus"),
                    "siteDetailLink": l.get("siteDetailLink"),
                    "mlsOrgId": l.get("mlsOrgId"),
                }
            return None

        # Active-only, paginate up to 10 pages within the zip.
        try:
            res = self.search_listings(
                filter_conditions={
                    "location": {"zipCode": [zipcode]},
                    "listingStatus": ["Active"],
                },
                page_size=100,
            )
        except Exception as e:
            return {
                "error": "address_not_found",
                "zipCode": zipcode,
                "message": (
                    f"MLS search failed for zip {zipcode}: {e}. "
                    f"Confirm the address with the user and retry."
                ),
            }

        listings = res.get("listing", []) if isinstance(res, dict) else []
        meta = res.get("metadata", {}) if isinstance(res, dict) else {}

        for l in listings:
            found = check(l)
            if found:
                return found

        total_pages = meta.get("totalPage", 1) if isinstance(meta, dict) else 1
        for page in range(2, min(total_pages, 10) + 1):
            try:
                res = self.search_listings(
                    filter_conditions={
                        "location": {"zipCode": [zipcode]},
                        "listingStatus": ["Active"],
                    },
                    page_size=100, page=page,
                )
            except Exception:
                break
            for l in res.get("listing", []) if isinstance(res, dict) else []:
                found = check(l)
                if found:
                    return found

        return {
            "error": "address_not_found",
            "zipCode": zipcode,
            "message": (
                f"No active MLS listing found for '{full_address}' in zip "
                f"{zipcode}. Verify the address with the user. Common "
                f"causes: wrong city, wrong zip, typo in street name, or "
                f"the listing is no longer active. This function does not "
                f"search Pending or Sold."
            ),
        }

    # ------------------------- showing primitives ---------------

    def shorten_url(self, long_url, prefix="b"):
        """Create a short link for any long URL.

        Returns the short URL on success, or None if the shortener is
        unreachable / misconfigured. Callers should fall back to the
        long URL so the showing workflow never hard-fails on this.
        """
        if not self.SHORTENER_BASE:
            # Recipient hasn't deployed the shortener Worker yet.
            return None
        try:
            req = urllib.request.Request(
                self.SHORTENER_BASE + "/create",
                method="POST",
                data=json.dumps({"url": long_url, "prefix": prefix}).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + self.SHORTENER_API_KEY,
                    # Cloudflare WAF sometimes blocks default Python urllib UA.
                    "User-Agent": "lofty-api-python/1.0",
                    "Accept": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=5) as r:
                body = json.loads(r.read().decode("utf-8"))
                return body.get("short_url")
        except (urllib.error.URLError, urllib.error.HTTPError,
                TimeoutError, ValueError) as e:
            print(f"[shorten_url] fallback to long URL (shortener error: {e})")
            return None

    def build_jotform_url(self, lead_id, property_address, showing_date,
                          property_stats, client_name, buyer_email=None,
                          shorten=True):
        """Build the prefilled post-showing feedback Jotform URL.

        Reads JOTFORM_FORM_ID from .env. The hidden fields are populated
        from your forked copy of assets/post_showing_questions.yaml.

        buyer_email, if provided, is passed through as a hidden field so
        the jotform-to-lofty Worker can email the buyer a feedback recap
        after they submit.

        shorten: if True (default), the long Jotform URL is run through
        your short-links Worker. If shortening fails for any reason,
        returns the long URL so the workflow doesn't break.
        """
        form_id = _require_env(
            "JOTFORM_FORM_ID",
            hint="The Jotform form ID for your post-showing feedback form.",
        )
        base = f"https://form.jotform.com/{form_id}"
        params = {
            "lead_id": str(lead_id),
            "propertyAddress": property_address,
            "showingDate": showing_date,
            "propertyStats": property_stats,
            "client_name": client_name,
        }
        if buyer_email:
            params["buyer_email"] = buyer_email
        long_url = base + "?" + urllib.parse.urlencode(params)
        if shorten:
            short = self.shorten_url(long_url, prefix="b")
            if short:
                return short
        return long_url

    def enqueue_showing_sms(self, lead_id, send_at_iso, short_url,
                            property_short_address, phone=None,
                            buyer_first_name=None, showing_key=None):
        """Register a post-showing feedback SMS to fire at showing start.

        Writes an entry to the showing-sms Worker. The Worker uses Durable
        Object alarms to fire the SMS at exactly send_at.

        showing_key (recommended): stable identifier so rescheduling the
        same showing upserts instead of creating a duplicate. Format:
        f"{lead_id}:{property_address_slug}".

        Worker auth: Bearer LOFTY_API_KEY. The Lofty JWT is repurposed as
        the shared secret on the showing-sms Worker (see Worker source).
        Recipients deploying their own Worker should configure it to
        accept their LOFTY_API_KEY as the bearer.

        Returns the Worker response dict, or None on failure. A failure
        here should NOT block the rest of prepare_showing - the worst
        case is the buyer misses the auto-text and the agent texts
        them manually.
        """
        if not self.SHOWING_SMS_BASE:
            # Recipient hasn't deployed the showing-sms Worker yet.
            return None
        try:
            payload = {
                "lead_id": int(lead_id),
                "send_at": send_at_iso,
                "short_url": short_url,
                "property_short_address": property_short_address,
            }
            if phone:
                payload["phone"] = phone
            if buyer_first_name:
                payload["buyer_first_name"] = buyer_first_name
            if showing_key:
                payload["showing_key"] = showing_key

            req = urllib.request.Request(
                self.SHOWING_SMS_BASE + "/enqueue",
                method="POST",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + self.api_key,
                    "User-Agent": "lofty-api-python/1.0",
                    "Accept": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=5) as r:
                return json.loads(r.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError,
                TimeoutError, ValueError) as e:
            print(f"[enqueue_showing_sms] failed (text will not auto-send): {e}")
            return None

    def build_showing_invite(self, client_first_name, listing, showing_start_dt,
                             showing_end_dt, jotform_url):
        """Build the calendar invite subject + HTML and text descriptions.

        The signature block is read from the OWNER_* env vars. Empty owner
        fields are skipped so the invite still looks tidy on a fresh
        install before the user has filled in their identity.
        """
        owner = self._owner_profile()
        full_address = listing.get("address") or (
            f"{listing.get('streetAddress','')}, {listing.get('city','')}, "
            f"{listing.get('state','')} {listing.get('zipCode','')}"
        )
        price = listing.get("price") or 0
        price_str = f"${price:,}" if isinstance(price, (int, float)) and price > 0 else "Price on request"
        beds = listing.get("beds") or ""
        baths = listing.get("baths") or ""
        sqft = listing.get("sqft") or ""
        sqft_str = f"{sqft:,}" if isinstance(sqft, (int, float)) and sqft > 0 else str(sqft)
        listing_url = listing.get("siteDetailLink") or ""

        day_str = showing_start_dt.strftime("%A, %B %-d")
        time_str = f"{showing_start_dt.strftime('%-I:%M %p')} to {showing_end_dt.strftime('%-I:%M %p')}"

        subject = f"Home Showing: {full_address}"

        # Build sig lines from whatever owner fields are populated.
        sig_lines_html = []
        sig_lines_text = []
        for field in ("full_name", "brokerage", "phone", "email"):
            val = owner.get(field, "").strip()
            if val:
                sig_lines_html.append(val)
                sig_lines_text.append(val)
        sig_html = "<br>".join(sig_lines_html)
        sig_text = "\n".join(sig_lines_text)

        description_html = (
            f"Dear {client_first_name},<br><br>"
            f"This is to confirm our scheduled showing at {full_address} "
            f"on {day_str} from {time_str}.<br><br>"
            f"<b>Property Details</b><br>"
            f"{beds} bedrooms, {baths} bathrooms | {sqft_str} sqft | {price_str}<br>"
            f'Listing: <a href="{listing_url}">{listing_url}</a><br><br>'
            f"Following the showing, I would appreciate your feedback on the property: "
            f'<b><a href="{jotform_url}">Leave Feedback on This Home</a></b><br><br>'
            f"Your input is valuable as we continue to identify the right home for your needs. "
            f"Please contact me directly if any changes to this appointment are necessary.<br><br>"
            f"Best regards,<br><br>"
            f"{sig_html}"
        )

        description_text = (
            f"Dear {client_first_name},\n\n"
            f"This is to confirm our scheduled showing at {full_address} "
            f"on {day_str} from {time_str}.\n\n"
            f"Property Details\n"
            f"{beds} bedrooms, {baths} bathrooms | {sqft_str} sqft | {price_str}\n"
            f"Listing: {listing_url}\n\n"
            f"Following the showing, I would appreciate your feedback on the property:\n"
            f"Leave Feedback on This Home: {jotform_url}\n\n"
            f"Your input is valuable as we continue to identify the right home for your needs. "
            f"Please contact me directly if any changes to this appointment are necessary.\n\n"
            f"Best regards,\n\n"
            f"{sig_text}"
        )

        return {
            "subject": subject,
            "description_html": description_html,
            "description_text": description_text,
            "location": full_address,
        }

    def _showing_key_and_short(self, lead_id, listing, full_address):
        """Build the stable showing_key and short address used for the SMS queue.

        Single source of truth for the slug logic. Both prepare_showing
        (enqueue) and cancel_showing (delete) call this so they cannot drift.
        """
        listing = listing or {}
        property_short = (
            listing.get("streetAddress")
            or listing.get("address", full_address).split(",")[0]
        )
        showing_key = f"{lead_id}:" + "".join(
            c if c.isalnum() else "-" for c in property_short.lower()
        ).strip("-")
        return showing_key, property_short

    def prepare_showing(self, full_address, start_datetime_iso, client_name=None,
                        duration_min=30, lead_id=None):
        """Prepare all data needed to schedule a showing.

        DRY-RUN helper. Returns the payloads needed to create the calendar
        event (done outside this file via your calendar provider) and the
        Lofty showing-log note. Does NOT send emails or create events
        itself. The calling skill is responsible for actually creating
        the calendar event, posting the Lofty note, and emailing the buyer.

        This separation is intentional. An earlier version of this function
        wrote a note that pre-claimed "Calendar invite sent to: <email>";
        when the calendar step failed downstream, the note lied. The
        caller now writes the note ONLY after the calendar event succeeds.

        Pass either client_name (resolved via find_client) or lead_id
        (resolved against the local leads index). Use lead_id when two
        leads share a name or phone, so the caller can pin the exact
        record instead of getting a Multiple-clients error.

        Returns dict with keys: listing, client, jotform_url,
        calendar_invite, showing_note_content, sms_queue, sms_showing_key.
        Or {'error': ..., ...} on failure.
        """
        from datetime import datetime as _dt, timedelta as _td

        if lead_id is None and not client_name:
            return {"error": "prepare_showing requires either client_name or lead_id."}

        listing = self.find_listing_by_address(full_address)
        if not listing or listing.get("error"):
            return {
                "error": (listing or {}).get(
                    "message",
                    f"Could not find MLS listing for '{full_address}'. "
                    f"Confirm the address with the user and retry.",
                )
            }

        if lead_id is not None:
            client = self._client_dict_from_index(lead_id)
            if client is None:
                return {"error": f"No lead with id {lead_id} in the local leads index. "
                                 f"Run scripts/refresh_leads_index.py if this lead is new."}
        else:
            client_result = self.find_client(client_name)
            if client_result.get("none"):
                return {"error": f"No Lofty lead found for '{client_name}'."}
            if client_result.get("candidates"):
                return {
                    "error": "Multiple clients match. Pass lead_id= to pin one:",
                    "candidates": client_result["candidates"],
                }
            client = client_result["match"]

        try:
            start_dt = _dt.fromisoformat(start_datetime_iso)
        except ValueError:
            return {"error": f"Invalid start_datetime_iso: {start_datetime_iso}. "
                             f"Use e.g. '2026-04-19T14:00:00-07:00'."}
        end_dt = start_dt + _td(minutes=duration_min)

        showing_date_display = start_dt.strftime("%B %-d, %Y")
        price = listing.get("price") or 0
        price_str = f"${price:,}" if price else "N/A"
        property_stats = (f"{listing.get('beds','')} bed / {listing.get('baths','')} "
                          f"bath | {listing.get('sqft','')} sqft | {price_str}")

        try:
            jotform_url = self.build_jotform_url(
                lead_id=client["leadId"],
                property_address=listing.get("address", full_address),
                showing_date=showing_date_display,
                property_stats=property_stats,
                client_name=f"{client['firstName']} {client['lastName']}".strip(),
                buyer_email=client.get("email") or None,
            )
        except RuntimeError as e:
            # JOTFORM_FORM_ID not set. Soft-fail: build the rest of the
            # payload anyway so the agent can still create the calendar
            # event manually and copy-paste the note.
            print(f"[prepare_showing] Jotform URL skipped: {e}")
            jotform_url = ""

        showing_key, property_short = self._showing_key_and_short(
            client["leadId"], listing, full_address
        )
        sms_queue_result = self.enqueue_showing_sms(
            lead_id=client["leadId"],
            send_at_iso=start_dt.isoformat(),
            short_url=jotform_url,
            property_short_address=property_short,
            phone=client.get("phone"),
            buyer_first_name=client.get("firstName"),
            showing_key=showing_key,
        )

        invite_first_name = (
            client.get("firstName")
            or (client_name.split()[0] if client_name else "")
        )
        invite = self.build_showing_invite(
            client_first_name=invite_first_name,
            listing=listing,
            showing_start_dt=start_dt,
            showing_end_dt=end_dt,
            jotform_url=jotform_url,
        )

        owner = self._owner_profile()
        mls_label = f" ({owner['mls_name']})" if owner.get("mls_name") else ""
        note_content = (
            f"=== SHOWING LOG ===\n"
            f"Property: {listing.get('address', full_address)}\n"
            f"MLS: {listing.get('mlsListingId','')}{mls_label}\n"
            f"Client: {client['firstName']} {client['lastName']}\n"
            f"Showing date/time: {start_dt.strftime('%B %-d, %Y at %-I:%M %p')} - "
            f"{end_dt.strftime('%-I:%M %p')}\n"
            f"Listing: {listing.get('siteDetailLink','')}"
        )

        return {
            "listing": listing,
            "client": client,
            "jotform_url": jotform_url,
            "calendar_invite": {
                **invite,
                "start_iso": start_dt.isoformat(),
                "end_iso": end_dt.isoformat(),
                "attendee_email": client.get("email"),
                "calendar": owner.get("email") or None,
            },
            "showing_note_content": note_content,
            "sms_queue": sms_queue_result,
            "sms_showing_key": showing_key,
        }

    # ------------------------- showing cancellation -------------

    def list_pending_showings(self, lead_id):
        """Return all pending post-showing SMS entries for a lead.

        Reads from the showing-sms Worker via GET /queue?lead_id=<id>.
        The Worker is the source of truth for what's queued, so this
        avoids re-hitting the MLS just to figure out what's scheduled.

        Returns a list of slim dicts (possibly empty), each shaped like:
            {
              "showing_key": "<lead>:<slug>",
              "lead_id": <int>,
              "send_at": "<iso>",
              "phone": "...",
              "buyer_first_name": "...",
              "short_url": "...",
              "property_short_address": "...",
              "status": "pending",
              "created_at": "<iso>",
            }

        Raises RuntimeError if the Worker is unreachable or returns
        non-200. Empty list is a legitimate state (no showings queued),
        not an error.
        """
        if not self.SHOWING_SMS_BASE:
            raise RuntimeError(
                "SHOWING_SMS_BASE_URL is not set. Add it to .env to use "
                "list_pending_showings, or skip this function until the "
                "showing-sms Worker is deployed."
            )
        url = f"{self.SHOWING_SMS_BASE}/queue?lead_id={int(lead_id)}"
        req = urllib.request.Request(
            url,
            method="GET",
            headers={
                "Authorization": "Bearer " + self.api_key,
                "User-Agent": "lofty-api-python/1.0",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                body = json.loads(r.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError,
                TimeoutError, ValueError) as e:
            raise RuntimeError(
                f"Failed to list pending showings at {url}: {e}. "
                f"The showing-sms Worker may be down or unreachable."
            )
        # Defensive double-filter: older Worker versions don't honor the
        # ?lead_id= query param. This keeps the Python contract stable.
        lead_id_int = int(lead_id)
        out = []
        for e in body.get("entries", []):
            v = e.get("value")
            if not v:
                continue
            if int(v.get("lead_id", -1)) != lead_id_int:
                continue
            if v.get("status") != "pending":
                continue
            out.append(v)
        return out

    def cancel_showing_by_key(self, showing_key):
        """DELETE a queued post-showing SMS by its showing_key.

        Use when you already have the key (from list_pending_showings or
        a prior prepare_showing return). Most callers should use
        cancel_showing instead, which finds the right key for you.

        Returns the Worker's JSON response. Raises RuntimeError on Worker
        failure. A silent failure here means the buyer still gets texted
        about a tour that didn't happen, so we surface the error loudly.
        """
        if not self.SHOWING_SMS_BASE:
            raise RuntimeError(
                "SHOWING_SMS_BASE_URL is not set. Cannot cancel a queued "
                "showing without it."
            )
        url = f"{self.SHOWING_SMS_BASE}/queue/{showing_key}"
        req = urllib.request.Request(
            url,
            method="DELETE",
            headers={
                "Authorization": "Bearer " + self.api_key,
                "User-Agent": "lofty-api-python/1.0",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return json.loads(r.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError,
                TimeoutError, ValueError) as e:
            raise RuntimeError(
                f"Failed to cancel showing SMS at {url}: {e}. "
                f"The buyer may still receive the feedback text at the "
                f"original showing time. Retry, or manually delete via: "
                f"curl -X DELETE -H 'Authorization: Bearer $LOFTY_API_KEY' {url}"
            )

    def cancel_showing(self, lead_id, full_address):
        """Cancel a queued post-showing SMS for a lead + address.

        Worker is the source of truth: this calls list_pending_showings to
        see what is actually queued, matches against the supplied address,
        and DELETEs the matching entry. No MLS round-trip, no slug guessing.

        Address matching is loose on purpose: case-insensitive substring
        in either direction. "11513 SW Bambi Ln" matches the queue's
        "11513 SW BAMBI LN" property_short_address.

        Returns one of:
            {"status": "cancelled", "showing_key": "...",
             "worker_response": {...}, "cancelled_entry": {...}}
            {"error": "no_match", "message": "...", "pending": [...]}
            {"error": "multiple_matches", "candidates": [...], "message": "..."}

        Raises RuntimeError ONLY for actual Worker failures. "No match"
        is not a failure - it's a legitimate state the caller can act on.
        """
        pending = self.list_pending_showings(lead_id)

        if not pending:
            return {
                "error": "no_match",
                "message": (
                    f"No pending showings queued for lead {lead_id}. "
                    f"Nothing to cancel."
                ),
                "pending": [],
            }

        addr_lower = (full_address or "").lower().strip()
        addr_first = addr_lower.split(",")[0].strip()

        def matches(entry):
            ps = (entry.get("property_short_address") or "").lower().strip()
            if not ps or not addr_lower:
                return False
            return (
                ps in addr_lower
                or addr_lower in ps
                or ps in addr_first
                or addr_first in ps
            )

        candidates = [e for e in pending if matches(e)]

        if len(candidates) == 0:
            return {
                "error": "no_match",
                "message": (
                    f"No queued showing for lead {lead_id} matched "
                    f"'{full_address}'. The lead has {len(pending)} other "
                    f"pending showing(s) - see 'pending' to pick one and "
                    f"call cancel_showing_by_key(showing_key) directly."
                ),
                "pending": pending,
            }

        if len(candidates) > 1:
            return {
                "error": "multiple_matches",
                "message": (
                    f"{len(candidates)} pending showings for lead {lead_id} "
                    f"matched '{full_address}'. Pick one and call "
                    f"cancel_showing_by_key(showing_key) directly."
                ),
                "candidates": candidates,
            }

        entry = candidates[0]
        worker_response = self.cancel_showing_by_key(entry["showing_key"])
        return {
            "status": "cancelled",
            "showing_key": entry["showing_key"],
            "cancelled_entry": entry,
            "worker_response": worker_response,
        }

    # ------------------------- buyer preferences ----------------

    def get_buyer_preferences(self, lead_id):
        """Fetch a buyer's aggregated showing-feedback profile.

        Hits the jotform-to-lofty Worker's /preferences/:leadId endpoint,
        which queries the showing_feedback D1 database and rolls up the
        loved tags, dealbreaker tags, and average ratings across every
        submission for the given lead.

        Returns a dict shaped like:
            {
              "status": "ok",
              "lead_id": <int>,
              "total_showings": <int>,
              "loved": [{"tag": "yard", "count": 3}, ...],
              "dealbreakers": [{"tag": "street noise", "count": 2}, ...],
              "average_ratings": {
                 "first_reaction": 4.0,
                 "daily_life_fit": 3.5,
                 ...
              }
            }

        When the buyer has no submissions yet, returns the same shape
        with total_showings=0 and empty lists.

        Requires LOFTY_PREFERENCES_API_KEY (Bearer auth on the Worker).
        Raises RuntimeError on network failure, 401, or non-JSON.
        """
        if not JOTFORM_WORKER_URL:
            raise RuntimeError(
                "JOTFORM_WORKER_URL is not set. Add it to .env to use "
                "get_buyer_preferences."
            )
        prefs_key = _require_env(
            "LOFTY_PREFERENCES_API_KEY",
            hint="Bearer token for the jotform-to-lofty Worker /preferences endpoint.",
        )
        url = f"{JOTFORM_WORKER_URL}/preferences/{int(lead_id)}"
        req = urllib.request.Request(
            url,
            method="GET",
            headers={
                "Authorization": "Bearer " + prefs_key,
                "User-Agent": "lofty-api-python/1.0",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8") if e.fp else ""
            except Exception:
                pass
            raise RuntimeError(
                f"Worker /preferences/{lead_id} returned {e.code}: {body or e.reason}. "
                f"Check LOFTY_PREFERENCES_API_KEY matches the Worker secret."
            )
        except (urllib.error.URLError, TimeoutError, ValueError) as e:
            raise RuntimeError(
                f"Failed to reach {url}: {e}. "
                f"The jotform-to-lofty Worker may be down or unreachable."
            )


# -----------------------------------------------------------------
# Command-line entry point
# -----------------------------------------------------------------
def _print_json(obj):
    print(json.dumps(obj, indent=2, default=str))


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 lofty_api.py <command> [args]")
        print("Commands:")
        print("  test                                  verify connection")
        print("  org                                   show organization")
        print("  members                               list team members")
        print("  lead <id>                             show one lead")
        print("  activities <id>                       show lead activity feed")
        print("  notes <id>                            list notes on a lead")
        print("  tags                                  list configured tags")
        print("  webhooks                              list webhook subscriptions")
        print("  search-listings <city> <zip>          MLS search by city + zip (active only)")
        print("  create-task <leadId> <content> <startISO> <endISO> [way]")
        print("  send-email <leadId> <subject> <content>")
        print("  send-sms <leadId> <content>")
        print("  find-client <name>                    Look up a lead by name (uses leads index)")
        print("  find-listing <full address>           Look up an Active MLS listing by address")
        print("  prepare-showing <addr> <startISO> <client name> [duration_min]")
        print("  list-pending-showings <leadId>        List queued post-showing SMS entries")
        print("  cancel-showing <leadId> <full address>")
        print("  buyer-preferences <leadId>            Aggregated showing-feedback rollup")
        print()
        print("  Activity & timeline:")
        print("  timeline <leadId>                     Unified human-readable timeline")
        print("  calls <leadId>                        Call history for a lead")
        print("  emails-history <leadId>               Email history for a lead")
        print("  texts-history <leadId>                SMS history for a lead")
        print("  alerts <leadId>                       Listing alerts on a lead")
        print("  transactions <leadId>                 Transactions for a lead")
        print("  log-activity <leadId> <content>       Add manual activity log entry")
        print()
        print("  Tasks:")
        print("  tasks [--lead <id>] [--include-finished]")
        print("  complete-task <calendarId>            Mark a task complete")
        print("  delete-task <calendarId>              Delete a task / appointment")
        print()
        print("  Notes:")
        print("  delete-note <noteId>                  Delete a note")
        print("  update-note <noteId> <content>        Edit an existing note")
        print()
        print("  Team & metadata:")
        print("  org                                   Organization details")
        print("  members                               List team members")
        print("  custom-fields                         Schema of configured custom fields")
        print("  ponds                                 List lead ponds")
        sys.exit(1)

    api = LoftyAPI()
    cmd = sys.argv[1]

    if cmd == "test":
        result = api.get_me()
        if isinstance(result, dict) and result.get("error"):
            print("FAILED: {}".format(result))
            sys.exit(1)
        print("Connection works. Your Lofty record:")
        _print_json(result)

    elif cmd == "org":
        _print_json(api.get_organization())

    elif cmd == "members":
        _print_json(api.get_members())

    elif cmd == "lead":
        if len(sys.argv) < 3:
            print("Usage: python3 lofty_api.py lead <id>")
            sys.exit(1)
        _print_json(api.get_lead(sys.argv[2]))

    elif cmd == "activities":
        if len(sys.argv) < 3:
            print("Usage: python3 lofty_api.py activities <id>")
            sys.exit(1)
        _print_json(api.get_lead_activities(sys.argv[2]))

    elif cmd == "notes":
        if len(sys.argv) < 3:
            print("Usage: python3 lofty_api.py notes <id>")
            sys.exit(1)
        _print_json(api.get_notes(sys.argv[2]))

    elif cmd == "tags":
        _print_json(api.get_tags())

    elif cmd == "webhooks":
        _print_json(api.get_webhooks())

    elif cmd == "search-listings":
        if len(sys.argv) < 4:
            print("Usage: python3 lofty_api.py search-listings <city> <zip>")
            sys.exit(1)
        city, zip_code = sys.argv[2], sys.argv[3]
        filters = {
            "location": {"city": [city], "zipCode": [zip_code]},
            "listingStatus": ["Active"],
        }
        _print_json(api.search_listings(filter_conditions=filters,
                                        sort_fields=["MLS_LIST_DATE_L_DESC"],
                                        page_size=10))

    elif cmd == "create-task":
        if len(sys.argv) < 6:
            print("Usage: python3 lofty_api.py create-task <leadId> <content> "
                  "<startISO> <endISO> [way]")
            print("Example: ... 12345 'Follow up' "
                  "'2026-05-08T14:00:00-07:00' '2026-05-08T14:30:00-07:00' Call")
            sys.exit(1)
        lead_id, content, start_at, end_at = sys.argv[2:6]
        task_way = sys.argv[6] if len(sys.argv) > 6 else "Call"
        _print_json(api.create_task(lead_id, content, start_at, end_at,
                                    task_way=task_way))

    elif cmd == "send-email":
        if len(sys.argv) < 5:
            print("Usage: python3 lofty_api.py send-email <leadId> <subject> <content>")
            sys.exit(1)
        lead_id, subject, content = sys.argv[2], sys.argv[3], sys.argv[4]
        _print_json(api.send_email(lead_id, subject, content))

    elif cmd == "send-sms":
        if len(sys.argv) < 4:
            print("Usage: python3 lofty_api.py send-sms <leadId> <content>")
            sys.exit(1)
        lead_id, content = sys.argv[2], sys.argv[3]
        _print_json(api.send_sms(lead_id, content))

    elif cmd == "find-client":
        if len(sys.argv) < 3:
            print("Usage: python3 lofty_api.py find-client <name>")
            sys.exit(1)
        _print_json(api.find_client(sys.argv[2]))

    elif cmd == "find-listing":
        if len(sys.argv) < 3:
            print("Usage: python3 lofty_api.py find-listing 'STREET, CITY, STATE ZIP'")
            sys.exit(1)
        _print_json(api.find_listing_by_address(sys.argv[2]))

    elif cmd == "prepare-showing":
        if len(sys.argv) < 5:
            print("Usage: python3 lofty_api.py prepare-showing "
                  "'STREET, CITY, STATE ZIP' '2026-05-15T14:00:00-07:00' "
                  "'Jane Smith' [duration_min]")
            sys.exit(1)
        addr = sys.argv[2]
        start_iso = sys.argv[3]
        client_name = sys.argv[4]
        duration = int(sys.argv[5]) if len(sys.argv) > 5 else 30
        _print_json(api.prepare_showing(addr, start_iso,
                                        client_name=client_name,
                                        duration_min=duration))

    elif cmd == "list-pending-showings":
        if len(sys.argv) < 3:
            print("Usage: python3 lofty_api.py list-pending-showings <leadId>")
            sys.exit(1)
        _print_json(api.list_pending_showings(sys.argv[2]))

    elif cmd == "cancel-showing":
        if len(sys.argv) < 4:
            print("Usage: python3 lofty_api.py cancel-showing <leadId> "
                  "'STREET, CITY, STATE ZIP'")
            sys.exit(1)
        lead_id, addr = sys.argv[2], sys.argv[3]
        _print_json(api.cancel_showing(lead_id, addr))

    elif cmd == "buyer-preferences":
        if len(sys.argv) < 3:
            print("Usage: python3 lofty_api.py buyer-preferences <leadId>")
            sys.exit(1)
        _print_json(api.get_buyer_preferences(sys.argv[2]))

    elif cmd == "timeline":
        if len(sys.argv) < 3:
            print("Usage: python3 lofty_api.py timeline <leadId>")
            sys.exit(1)
        _print_json(api.get_system_logs(sys.argv[2]))

    elif cmd == "calls":
        if len(sys.argv) < 3:
            print("Usage: python3 lofty_api.py calls <leadId>")
            sys.exit(1)
        _print_json(api.get_call_history(lead_id=sys.argv[2]))

    elif cmd == "emails-history":
        if len(sys.argv) < 3:
            print("Usage: python3 lofty_api.py emails-history <leadId>")
            sys.exit(1)
        _print_json(api.get_email_history(lead_id=sys.argv[2]))

    elif cmd == "texts-history":
        if len(sys.argv) < 3:
            print("Usage: python3 lofty_api.py texts-history <leadId>")
            sys.exit(1)
        _print_json(api.get_text_history(lead_id=sys.argv[2]))

    elif cmd == "alerts":
        if len(sys.argv) < 3:
            print("Usage: python3 lofty_api.py alerts <leadId>")
            sys.exit(1)
        _print_json(api.get_alerts(sys.argv[2]))

    elif cmd == "transactions":
        if len(sys.argv) < 3:
            print("Usage: python3 lofty_api.py transactions <leadId>")
            sys.exit(1)
        _print_json(api.get_transactions(sys.argv[2]))

    elif cmd == "log-activity":
        if len(sys.argv) < 4:
            print("Usage: python3 lofty_api.py log-activity <leadId> <content>")
            sys.exit(1)
        _print_json(api.add_lead_activity(sys.argv[2], sys.argv[3]))

    elif cmd == "tasks":
        # Optional --lead <id> --include-finished
        lead_id = None
        include_finished = False
        i = 2
        while i < len(sys.argv):
            if sys.argv[i] == "--lead" and i + 1 < len(sys.argv):
                lead_id = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--include-finished":
                include_finished = True
                i += 1
            else:
                i += 1
        _print_json(api.get_tasks(lead_id=lead_id, include_finished=include_finished))

    elif cmd == "complete-task":
        if len(sys.argv) < 3:
            print("Usage: python3 lofty_api.py complete-task <calendarId>")
            sys.exit(1)
        _print_json(api.complete_task(sys.argv[2]))

    elif cmd == "delete-task":
        if len(sys.argv) < 3:
            print("Usage: python3 lofty_api.py delete-task <calendarId>")
            sys.exit(1)
        _print_json(api.delete_task(sys.argv[2]))

    elif cmd == "delete-note":
        if len(sys.argv) < 3:
            print("Usage: python3 lofty_api.py delete-note <noteId>")
            sys.exit(1)
        _print_json(api.delete_note(sys.argv[2]))

    elif cmd == "update-note":
        if len(sys.argv) < 4:
            print("Usage: python3 lofty_api.py update-note <noteId> <content>")
            sys.exit(1)
        _print_json(api.update_note(sys.argv[2], sys.argv[3]))

    elif cmd == "custom-fields":
        _print_json(api.get_custom_fields())

    elif cmd == "ponds":
        _print_json(api.get_lead_ponds())

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
