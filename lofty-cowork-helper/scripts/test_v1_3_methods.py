#!/usr/bin/env python3
"""
v1.3.0 smoke tests for the Phase 2 showing helpers.

Run from anywhere. Pre-load your .env via shell-source so the Python
client picks up your real keys without us hard-coding paths:

    set -a
    source <path-to-your-project>/.env
    set +a

    # If your .env doesn't yet have the new v1.3 vars, set them inline:
    export OWNER_FULL_NAME="Your Name"
    export OWNER_BROKERAGE="Your Brokerage"
    export OWNER_PHONE="<your-phone>"
    export OWNER_EMAIL="<your-email>"
    export OWNER_LAST_NAME_LOWER=<your last name lowercase>
    export MLS_NAME=<your MLS, e.g. RMLS>
    export JOTFORM_FORM_ID=<your-jotform-form-id>
    export SHOWING_SMS_BASE_URL=https://showing-sms.<your-subdomain>.workers.dev
    export JOTFORM_WORKER_URL=https://jotform-to-lofty.<your-subdomain>.workers.dev

    python3 <path-to-this-kit>/lofty-cowork-helper/scripts/test_v1_3_methods.py \\
        <yourLeadId> "STREET, CITY, STATE ZIP"

What it does:
    1. find_client by your own name (should be excluded if
       OWNER_LAST_NAME_LOWER matches; that's the right behavior).
       Then a known test name to confirm matching works.
    2. find_listing_by_address against the address you pass in
       (verifies it's Active in your MLS).
    3. prepare_showing for that address against your own lead, with a
       start time 30 days in the future so the auto-SMS won't actually
       fire during the test. Verifies the full payload assembly.
    4. list_pending_showings to confirm the SMS was queued.
    5. cancel_showing to delete the test entry and clean up.
    6. get_buyer_preferences to read the D1 rollup for your lead.

Each call prints its result. If any returns {"error": ...}, that's the
one to fix. Cleanup in step 5 is critical so you don't end up with a
stray queued SMS hitting your phone in 30 days.
"""

import os
import sys
from datetime import datetime, timedelta, timezone

# Prefer the kit-source v1.3 lofty_api.py so we test the new code, not
# whatever older copy lives in a workspace folder.
HOME = os.path.expanduser("~")
for candidate in [
    os.path.join(HOME, "Code", "lofty-cowork-skill", "lofty-cowork-helper", "assets"),
    os.path.join(HOME, "Code", "lofty-tools", "scripts"),
]:
    if os.path.isfile(os.path.join(candidate, "lofty_api.py")):
        sys.path.insert(0, candidate)
        break

from lofty_api import LoftyAPI  # noqa: E402


def section(title):
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def is_error_dict(resp):
    return isinstance(resp, dict) and (resp.get("error") is True or
                                       isinstance(resp.get("error"), str))


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 test_v1_3_methods.py <yourLeadId> "
              "'STREET, CITY, STATE ZIP'")
        print()
        print("yourLeadId: search Lofty for your own name to find it.")
        print("Address: a real Active listing in your MLS, in Lofty format.")
        sys.exit(1)

    lead_id = int(sys.argv[1])
    full_address = sys.argv[2]

    api = LoftyAPI()

    # ─────────────────────────────────────────────────────────────
    section("1a. find_client('your last name'): self-exclusion check")
    # If OWNER_LAST_NAME_LOWER is set, your own record should NOT come
    # back in name searches. Pass YOUR last name and confirm "none".
    own_last = os.environ.get("OWNER_LAST_NAME_LOWER", "").strip()
    if not own_last:
        print("SKIP: OWNER_LAST_NAME_LOWER not set in env.")
    else:
        try:
            res = api.find_client(own_last)
            if res.get("none"):
                print(f"OK. Your last name '{own_last}' was excluded as expected.")
            else:
                print("WARN: own record was returned. OWNER_LAST_NAME_LOWER may "
                      "not match your actual lead's lastNameLower in the index.")
                print(res)
        except RuntimeError as e:
            print(f"FAILED: {e}")
            print("This usually means the leads index isn't built yet. Run:")
            print("  python3 scripts/refresh_leads_index.py")

    # ─────────────────────────────────────────────────────────────
    section("1b. find_client: lookup by known name (use your own first name)")
    own_first = os.environ.get("OWNER_FULL_NAME", "").split()[0] if \
        os.environ.get("OWNER_FULL_NAME") else ""
    if not own_first:
        print("SKIP: OWNER_FULL_NAME not set; can't construct a known-name probe.")
    else:
        try:
            # Even though your full name self-excludes, your first name
            # may match other leads in the index. Just verify the index
            # search is reachable and returns a sensible shape.
            res = api.find_client(own_first)
            if res.get("none"):
                print(f"OK. No leads other than yours matched '{own_first}'.")
            elif res.get("match"):
                print(f"OK. One lead matched '{own_first}': "
                      f"{res['match'].get('firstName')} {res['match'].get('lastName')}")
            elif res.get("candidates"):
                print(f"OK. {len(res['candidates'])} leads matched '{own_first}'. "
                      f"This is normal in a CRM with many first-name overlaps.")
        except RuntimeError as e:
            print(f"FAILED: {e}")

    # ─────────────────────────────────────────────────────────────
    section("2. find_listing_by_address: must return an Active listing")
    listing = api.find_listing_by_address(full_address)
    if listing.get("error"):
        print(f"FAILED: {listing}")
        print("Confirm the address is Active in your MLS and uses Lofty format.")
        sys.exit(2)
    print(f"OK. Listing found:")
    for k in ("address", "city", "zipCode", "price", "beds", "baths",
              "sqft", "listingStatus", "mlsListingId", "loftyListingId"):
        if k in listing:
            print(f"  {k}: {listing[k]}")

    # ─────────────────────────────────────────────────────────────
    section("3. prepare_showing: build payloads for a 30-day-out showing")
    start = datetime.now(timezone.utc).astimezone() + timedelta(days=30)
    start = start.replace(hour=14, minute=0, second=0, microsecond=0)
    start_iso = start.isoformat()

    prep = api.prepare_showing(
        full_address=full_address,
        start_datetime_iso=start_iso,
        lead_id=lead_id,
        duration_min=30,
    )
    if is_error_dict(prep):
        print(f"FAILED: {prep}")
        sys.exit(3)
    print("OK. Top-level keys:", list(prep.keys()))
    print("  showing_key:", prep.get("sms_showing_key"))
    print("  jotform_url:", (prep.get("jotform_url") or "")[:80] + "...")
    print("  calendar_invite.subject:", prep.get("calendar_invite", {}).get("subject"))
    print("  calendar_invite.location:", prep.get("calendar_invite", {}).get("location"))
    print("  showing_note_content (first 200 chars):")
    print("   ", (prep.get("showing_note_content") or "")[:200])
    queued = prep.get("sms_queue")
    if queued:
        print("  SMS queue response:", queued)
    else:
        print("  SMS queue: not enqueued (Worker URL likely empty in env)")

    showing_key = prep.get("sms_showing_key")

    # ─────────────────────────────────────────────────────────────
    section("4. list_pending_showings: confirm the test entry is queued")
    if not os.environ.get("SHOWING_SMS_BASE_URL"):
        print("SKIP: SHOWING_SMS_BASE_URL not set; cannot list queue.")
    else:
        try:
            pending = api.list_pending_showings(lead_id)
            print(f"OK. {len(pending)} pending showings for lead {lead_id}.")
            for p in pending[:5]:
                print(f"  - {p.get('showing_key')} | "
                      f"{p.get('property_short_address')} | "
                      f"send_at={p.get('send_at')}")
        except RuntimeError as e:
            print(f"FAILED: {e}")

    # ─────────────────────────────────────────────────────────────
    section("5. cancel_showing: delete the test entry (cleanup)")
    if not os.environ.get("SHOWING_SMS_BASE_URL"):
        print("SKIP: SHOWING_SMS_BASE_URL not set; cleanup unnecessary.")
    else:
        try:
            cancel = api.cancel_showing(lead_id, full_address)
            if cancel.get("status") == "cancelled":
                print(f"OK. Cancelled showing_key={cancel.get('showing_key')}")
            elif cancel.get("error") == "no_match":
                # Could happen if the Worker URL was empty during prep but
                # set during cancel, etc. Surface plainly.
                print(f"NOTE: no_match. Either prep didn't enqueue or the "
                      f"address didn't match. Pending: {len(cancel.get('pending', []))}")
            else:
                print(f"WARN: unexpected response: {cancel}")
        except RuntimeError as e:
            print(f"FAILED: {e}")
            print("IMPORTANT: a queued SMS may still fire in 30 days. "
                  "Run cancel_showing manually before then.")

    # ─────────────────────────────────────────────────────────────
    section("6. get_buyer_preferences: D1 rollup for your lead")
    if not os.environ.get("JOTFORM_WORKER_URL"):
        print("SKIP: JOTFORM_WORKER_URL not set; preferences endpoint unreachable.")
    else:
        try:
            prefs = api.get_buyer_preferences(lead_id)
            print(f"OK. status={prefs.get('status')} "
                  f"total_showings={prefs.get('total_showings', 0)}")
            if prefs.get("loved"):
                print(f"  top loved: {prefs['loved'][:5]}")
            if prefs.get("dealbreakers"):
                print(f"  top dealbreakers: {prefs['dealbreakers'][:5]}")
            if prefs.get("average_ratings"):
                print(f"  avg ratings: {prefs['average_ratings']}")
        except RuntimeError as e:
            print(f"FAILED: {e}")

    section("Done")
    print("If everything above said OK, v1.3.0 is good to ship.")
    print("Paste the full output back to Claude.")


if __name__ == "__main__":
    main()
