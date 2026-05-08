#!/usr/bin/env python3
"""
Refresh the local leads index.
==============================

Scans every lead in Lofty via scrollId pagination and writes a clean
local cache to data/leads_index.json. find_client reads from this
file to match clients by name without hitting the API on every call.

Why this exists:
    The Lofty /v1.0/leads endpoint silently ignores the `keyword`
    parameter. Without an index, find_client only sees the 25 most
    recently created leads, and any older client returns "none."
    This script fixes that by building a full local index.

Usage:
    python3 scripts/refresh_leads_index.py
    python3 scripts/refresh_leads_index.py --output path/to/file.json

Runtime:
    Lofty enforces 10 requests per minute. The Python client sleeps
    6.5 seconds between calls. Expect ~3 minutes for 650 leads, longer
    for larger CRMs. Each page returns 25 leads (API hard cap).

This script is safe to re-run. It writes the file atomically.

Cowork bash tool note: this run takes longer than the 45-second
hard timeout. Run it from your real terminal, not Claude's bash.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Make LoftyAPI importable when running from anywhere.
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from lofty_api import LoftyAPI, LEADS_INDEX_PATH  # noqa: E402


# Default location. Both scripts read this same constant so they can't
# drift. Override with --output or LOFTY_LEADS_INDEX_PATH (see lofty_api.py).
DEFAULT_OUTPUT = LEADS_INDEX_PATH


def _normalize(lead):
    """Flatten a Lofty lead dict into the shape find_client and Cowork need.

    Stores lowercase names so lookups don't have to re-lowercase on every
    call. Keeps emails and phones as arrays (they can have multiples).

    Captures buyer/seller intent, DNC flags, and ownership context so
    Claude can answer questions like "is this a first-time buyer?" or
    "did they unsubscribe from email?" without a per-lead get_lead
    round-trip.
    """
    first = (lead.get("firstName") or "").strip()
    last = (lead.get("lastName") or "").strip()
    return {
        # Identity
        "leadId": lead.get("leadId"),
        "firstName": first,
        "lastName": last,
        "firstNameLower": first.lower(),
        "lastNameLower": last.lower(),
        "fullNameLower": f"{first} {last}".strip().lower(),
        "emails": lead.get("emails") or [],
        "phones": lead.get("phones") or [],
        # Pipeline
        "stage": lead.get("stage", ""),
        "stageId": lead.get("stageId"),
        "score": lead.get("score", 0),
        "tags": lead.get("tags") or [],
        "segments": lead.get("segments") or [],
        "leadType": lead.get("leadType", ""),
        "leadTypes": lead.get("leadTypes") or [],
        # Source & ownership
        "leadSource": lead.get("leadSource", ""),
        "source": lead.get("source", ""),
        "referredBy": lead.get("referredBy", ""),
        "assignedUser": lead.get("assignedUser", ""),
        "assignedUserId": lead.get("assignedUserId"),
        "leadUserId": lead.get("leadUserId"),
        "lenderUserId": lead.get("lenderUserId"),
        "pondId": lead.get("pondId"),
        "pondName": lead.get("pondName", ""),
        # Buyer / seller intent (the most useful new fields)
        "buyHouse": lead.get("buyHouse"),
        "buyingTimeFrame": lead.get("buyingTimeFrame", ""),
        "houseToSell": lead.get("houseToSell"),
        "sellingTimeFrame": lead.get("sellingTimeFrame", ""),
        "withBuyerAgent": lead.get("withBuyerAgent"),
        "withListingAgent": lead.get("withListingAgent"),
        "fthb": lead.get("fthb"),  # first-time home buyer flag
        "mortgage": lead.get("mortgage", ""),
        "preQual": lead.get("preQual", ""),
        # Contact preferences (DNC-style)
        "cannotCall": lead.get("cannotCall"),
        "cannotEmail": lead.get("cannotEmail"),
        "cannotText": lead.get("cannotText"),
        "unsubscription": lead.get("unsubscription"),
        # Visibility
        "hiddenFlag": lead.get("hiddenFlag"),
        "privateFlag": lead.get("privateFlag"),
        # Address (the lead's home address; not their target search area)
        "streetAddress": lead.get("streetAddress", ""),
        "city": lead.get("city", ""),
        "state": lead.get("state", ""),
        "zipCode": lead.get("zipCode", ""),
        # Time
        "createTime": lead.get("createTime", ""),
        "lastVisit": lead.get("lastVisit", ""),
        "lastTouch": lead.get("lastTouch", ""),
        "lastUpdateTime": lead.get("lastUpdateTime", ""),
        "assignTime": lead.get("assignTime", ""),
        "birthday": lead.get("birthday", ""),
        # Other
        "language": lead.get("language", ""),
        "facebook": lead.get("facebook", ""),
        "twitter": lead.get("twitter", ""),
        "opportunity": lead.get("opportunity", ""),
        # Child collections (kept as-is; can be nested)
        "leadFamilyMemberList": lead.get("leadFamilyMemberList") or [],
        "leadInquiry": lead.get("leadInquiry") or [],
        "leadPropertyList": lead.get("leadPropertyList") or [],
        "customAttributes": lead.get("customAttributes") or {},
    }


def _format_elapsed(seconds):
    m, s = divmod(int(seconds), 60)
    return f"{m}m {s:02d}s" if m else f"{s}s"


def _fetch_all_leads(api, verbose=True):
    """Paginate every lead via scrollId and return a flat list.

    Progress is printed after each page when verbose=True. Handles the
    case where scrollId is None on the last page.
    """
    leads = []
    scroll_id = None
    page_num = 0
    total_expected = None
    start = time.time()

    while True:
        page_num += 1

        if scroll_id:
            data = api._request("GET", "/v1.0/leads",
                                query_params={"scrollId": scroll_id})
        else:
            # First call. Don't pass sortField since it's silently
            # ignored anyway. Default pageSize of 25 is the hard cap.
            data = api._request("GET", "/v1.0/leads", query_params={
                "pageSize": 25,
                "page": 1,
            })

        if isinstance(data, dict) and data.get("error"):
            print(f"\n[ERROR] API returned an error on page {page_num}: {data}",
                  file=sys.stderr)
            raise RuntimeError("Aborting. No partial file will be written.")

        page_leads = data.get("leads", []) if isinstance(data, dict) else []
        meta = data.get("_metadata", {}) if isinstance(data, dict) else {}

        if total_expected is None:
            total_expected = meta.get("total")

        leads.extend(page_leads)

        if verbose:
            elapsed = time.time() - start
            if total_expected and total_expected > 0:
                pct = min(100, int(len(leads) * 100 / total_expected))
                remaining_leads = max(0, total_expected - len(leads))
                remaining_pages = max(0, (remaining_leads + 24) // 25)
                # Each remaining page takes ~6.5 seconds (rate limit).
                eta_sec = remaining_pages * 6.5
                print(
                    f"  page {page_num:>2d} | {len(leads):>4d}/{total_expected} leads "
                    f"({pct}%) | elapsed {_format_elapsed(elapsed)} | "
                    f"~{_format_elapsed(eta_sec)} left",
                    flush=True,
                )
            else:
                print(
                    f"  page {page_num:>2d} | {len(leads):>4d} leads so far | "
                    f"elapsed {_format_elapsed(elapsed)}",
                    flush=True,
                )

        scroll_id = meta.get("scrollId")

        # Stop conditions: no more leads on the page, or no next scrollId.
        if not page_leads or not scroll_id:
            break

    return leads


def _write_atomic(path, payload):
    """Write JSON atomically so a crash mid-write can't leave a half file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
    os.replace(tmp, path)


def main():
    parser = argparse.ArgumentParser(
        description="Rebuild data/leads_index.json from Lofty."
    )
    parser.add_argument(
        "--output", "-o",
        default=str(DEFAULT_OUTPUT),
        help=f"Output path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress per-page progress output.",
    )
    args = parser.parse_args()

    output = Path(args.output)
    verbose = not args.quiet

    if verbose:
        print("Refreshing local leads index")
        print("=" * 45)
        print(f"Target file: {output}")
        print("Scanning all pages from Lofty. This takes ~3 min for 650 leads.")
        print("Rate limit is 10 requests/min. Please be patient.\n")

    api = LoftyAPI()
    start = time.time()

    raw_leads = _fetch_all_leads(api, verbose=verbose)
    normalized = [_normalize(l) for l in raw_leads]

    now = datetime.now(timezone.utc).astimezone()
    payload = {
        "refreshed_at": now.isoformat(),
        "refreshed_at_epoch_ms": int(now.timestamp() * 1000),
        "count": len(normalized),
        "source": "lofty /v1.0/leads (scrollId pagination)",
        "leads": normalized,
    }

    _write_atomic(output, payload)

    elapsed = time.time() - start
    if verbose:
        print()
        print("=" * 45)
        print(f"Done. {len(normalized)} leads indexed in {_format_elapsed(elapsed)}.")
        print(f"Written to: {output}")
        print()
        print("find_client will now read from this file.")
        print("Re-run this script whenever you want fresh data, or set")
        print("LOFTY_LEADS_INDEX_SOURCE=worker in .env once you've deployed")
        print("the leads-index Cloudflare Worker.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted. No file was written.", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"\n[FATAL] {e}", file=sys.stderr)
        sys.exit(1)
