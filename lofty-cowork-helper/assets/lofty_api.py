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

What it doesn't do (yet):
    - Showing scheduling helpers (prepare_showing, find_listing_by_address)
    - The leads index workaround for /v1.0/leads sort/keyword bugs
    - MLS search (search_listings)
    - Tasks, email, SMS

Add those methods as you need them. The full guide has working examples.

Reference: see claude-cowork-lofty-guide.md sections 14 and 22.
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
    for candidate in [here / ".env", here.parent / ".env"]:
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


# -----------------------------------------------------------------
# Config
# -----------------------------------------------------------------
BASE_URL = os.environ.get("LOFTY_BASE_URL", "https://api.lofty.com")
RATE_LIMIT_DELAY = float(os.environ.get("LOFTY_RATE_LIMIT_DELAY", "6.5"))


# -----------------------------------------------------------------
# Client
# -----------------------------------------------------------------
class LoftyAPI:
    """Minimal wrapper around the Lofty REST API."""

    def __init__(self, api_key=None, base_url=None):
        self.api_key = api_key or os.environ.get("LOFTY_API_KEY")
        if not self.api_key:
            raise RuntimeError(
                "Missing LOFTY_API_KEY. Add it to .env at the project root.\n"
                "Get your key from Lofty Settings, API Keys (long string starting with eyJ)."
            )
        self.base_url = base_url or BASE_URL
        self._last_call = 0.0

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
        Content-Type is sent ONLY on POST/PUT (Lofty quirk #6).
        """
        self._rate_limit()

        url = f"{self.base_url}{path}"
        if query_params:
            filtered = {k: str(v) for k, v in query_params.items()
                        if v is not None and v != ""}
            if filtered:
                url += "?" + urllib.parse.urlencode(filtered)

        headers = {"Authorization": f"token {self.api_key}"}
        data = None
        if body and method in ("POST", "PUT"):
            headers["Content-Type"] = "application/json"
            data = json.dumps(body).encode("utf-8")

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

        WARNING: Lofty silently ignores `keyword`, `sortField`, and `startTime`
        on this endpoint (Lofty quirk #2). Sort always returns leadId DESC.
        For lead lookup by name, build a leads index instead. The full guide
        has the pattern (section 15).
        """
        return self._request("GET", "/v1.0/leads",
                             query_params={"page": page, "pageSize": page_size})

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
        """Update fields on a lead."""
        return self._request("PUT", f"/v1.0/leads/{lead_id}", body=fields)

    # ------------------------- notes ----------------------------

    def create_note(self, lead_id, content):
        """Create a note on a lead.

        IMPORTANT: POST to /v1.0/notes with leadId in the body. The intuitive
        path /v1.0/leads/<id>/notes returns 404 (Lofty quirk #4). leadId must
        be a number, not a string.
        """
        return self._request("POST", "/v1.0/notes",
                             body={"leadId": int(lead_id), "content": content})

    def get_notes(self, lead_id, page=1, page_size=25):
        """List notes for a lead."""
        return self._request("GET", "/v1.0/notes",
                             query_params={"leadId": lead_id,
                                           "page": page, "pageSize": page_size})

    # ------------------------- tags / metadata ------------------

    def get_tags(self):
        """List all tags configured on your team."""
        return self._request("GET", "/v1.0/teamFeatures/listTag")

    def get_webhooks(self):
        """List active webhook subscriptions."""
        return self._request("GET", "/v1.0/webhooks")


# -----------------------------------------------------------------
# Command-line entry point
# -----------------------------------------------------------------
def _print_json(obj):
    print(json.dumps(obj, indent=2, default=str))


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 lofty_api.py <command> [args]")
        print("Commands: test, org, members, lead <id>, activities <id>, notes <id>, tags, webhooks")
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

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
