#!/usr/bin/env python3
"""
v1.2.0 smoke tests for the four new lofty_api.py methods.

Run from your lofty-tools workspace folder:

    cd ~/Code/lofty-tools
    cp ~/Code/lofty-cowork-skill/lofty-cowork-helper/assets/lofty_api.py scripts/lofty_api.py
    python3 ~/Code/lofty-cowork-skill/lofty-cowork-helper/scripts/test_v1_2_methods.py <yourLeadId>

What it does:
    1. search_listings: NW Portland active listings, top 3
    2. create_task: TASK-type follow-up due tomorrow (creates a real task on
       your own lead so you can see it in Lofty)
    3. send_email: a tiny test email to your own lead (you'll receive it)
    4. send_sms: a tiny test SMS to your own lead (you'll receive it)

Each call prints its result. If any of them returns {"error": True, ...},
that's the one we need to fix before shipping v1.2.0.
"""

import os
import sys
from datetime import datetime, timedelta, timezone

# Make sure the v1.2.0 lofty_api.py is on the path. Prefer the workspace copy
# the user already has at ~/Code/lofty-tools/scripts/, fall back to the kit
# source.
HOME = os.path.expanduser("~")
for candidate in [
    os.path.join(HOME, "Code", "lofty-tools", "scripts"),
    os.path.join(HOME, "Code", "lofty-cowork-skill", "lofty-cowork-helper", "assets"),
]:
    if os.path.isfile(os.path.join(candidate, "lofty_api.py")):
        sys.path.insert(0, candidate)
        break

from lofty_api import LoftyAPI


def section(title):
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 test_v1_2_methods.py <yourLeadId>")
        print("Find yourLeadId in Lofty by searching your own name.")
        sys.exit(1)

    lead_id = int(sys.argv[1])
    api = LoftyAPI()

    def _summarize_listings(resp, label):
        if isinstance(resp, dict) and resp.get("error"):
            print(f"FAILED ({label}):", resp)
            return
        if isinstance(resp, dict):
            print(f"Response keys: {list(resp.keys())}")
        # Lofty puts results under "listing" (singular), not "listings"
        items = (resp.get("listing")
                 or resp.get("listings")
                 or resp.get("items")
                 or [])
        meta = resp.get("metadata") or {}
        total = meta.get("total") or meta.get("totalCount") or "?"
        print(f"OK ({label}). Got {len(items)} on this page; total={total}")
        if items:
            first = items[0]
            print(f"  First item keys: {list(first.keys())[:12]}")
            for k in ("streetAddress", "city", "price", "beds", "baths",
                      "sqft", "listingStatus", "mlsListingId"):
                if k in first:
                    print(f"  {k}: {first[k]}")

    section("1a. search_listings (scope=all): NW Portland 97210 active")
    _summarize_listings(api.search_listings(
        filter_conditions={
            "location": {"city": ["Portland"], "zipCode": ["97210"]},
            "listingStatus": ["Active"],
        },
        sort_fields=["MLS_LIST_DATE_L_DESC"],
        page_size=3,
    ), "all NW Portland")

    section("1b. search_listings (scope=my): your own listings")
    _summarize_listings(api.search_listings(
        scope="my",
        page_size=3,
    ), "scope=my")

    section("2. create_task: follow-up tomorrow at 10am Pacific")
    tomorrow_10 = datetime.now(timezone.utc).replace(
        hour=17, minute=0, second=0, microsecond=0
    ) + timedelta(days=1)
    start_iso = tomorrow_10.isoformat()
    end_iso = (tomorrow_10 + timedelta(minutes=30)).isoformat()
    task = api.create_task(
        lead_id=lead_id,
        content="v1.2.0 smoke test task. Safe to delete.",
        start_at=start_iso,
        end_at=end_iso,
        task_way="Call",
    )
    if isinstance(task, dict) and task.get("error"):
        print("FAILED:", task)
    else:
        print("OK. Task response:")
        print(task)

    section("3. send_email: tiny test email to your own lead")
    email = api.send_email(
        lead_id=lead_id,
        subject="v1.2.0 smoke test (safe to ignore)",
        content=(
            "<p>This is an automated v1.2.0 smoke test of the Lofty + Cowork skill.</p>"
            "<p>If you got this, send_email works. Safe to delete.</p>"
        ),
    )
    if isinstance(email, dict) and email.get("error"):
        print("FAILED:", email)
    else:
        print("OK. Email response:")
        print(email)

    section("4. send_sms: tiny test SMS to your own lead")
    sms = api.send_sms(
        lead_id=lead_id,
        content="v1.2.0 smoke test of send_sms. Safe to ignore.",
    )
    if isinstance(sms, dict) and sms.get("error"):
        print("FAILED:", sms)
    else:
        print("OK. SMS response:")
        print(sms)

    section("Done")
    print("Paste the full output of this run back to Claude.")


if __name__ == "__main__":
    main()
