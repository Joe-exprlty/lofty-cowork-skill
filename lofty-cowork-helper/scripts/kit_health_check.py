#!/usr/bin/env python3
"""
Kit health check.
=================

Quick status check for the Lofty kit. Claude runs this when the user
asks "is everything working?"

Default output is short and human-readable, 3 to 5 lines. Pass --json
for a structured report Claude can parse.

Exit codes:
    0  everything OK
    1  something needs attention
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def _check_lofty_api():
    if not os.environ.get("LOFTY_API_KEY"):
        return "fail", "Lofty API key is not set"
    try:
        from lofty_api import LoftyAPI
        result = LoftyAPI().get_me()
    except Exception as e:
        return "fail", f"Lofty connection error: {e}"
    if isinstance(result, dict) and result.get("error"):
        return "fail", "Lofty API rejected your key (try regenerating it)"
    return "ok", "Lofty connected"


def _check_leads_index():
    try:
        from lofty_api import LEADS_INDEX_PATH
    except Exception:
        return "fail", "Could not load index path", None, None
    path = LEADS_INDEX_PATH
    if not path.is_file():
        return ("fail",
                "Leads index missing. Ask me to refresh it.",
                None, None)
    try:
        data = json.loads(path.read_text())
    except Exception:
        return "fail", "Leads index is corrupted. Ask me to rebuild it.", None, None
    count = data.get("count") or 0
    refreshed_ms = data.get("refreshed_at_epoch_ms") or 0
    if not refreshed_ms:
        return "warn", f"{count} leads in index; age unknown", count, None
    age_h = (time.time() * 1000 - refreshed_ms) / (1000 * 60 * 60)
    age_str = _human_age(age_h)
    if age_h > 8 * 24:
        return ("fail",
                f"Leads index is {age_str} old. Ask me to refresh it.",
                count, age_h)
    if age_h > 2 * 24:
        return ("warn",
                f"{count} leads; index is {age_str} old (refresh recommended)",
                count, age_h)
    return "ok", f"{count} leads, refreshed {age_str} ago", count, age_h


def _check_auto_refresh():
    """Did the auto-refresh run recently? Read the log, check last entry."""
    try:
        from lofty_api import LEADS_INDEX_PATH
    except Exception:
        return "warn", "Auto-refresh status unknown"
    log_path = LEADS_INDEX_PATH.parent / ".refresh-log.jsonl"
    if not log_path.is_file():
        return "warn", "Auto-refresh has not run yet"
    try:
        lines = [l for l in log_path.read_text().splitlines() if l.strip()]
        last = json.loads(lines[-1]) if lines else None
    except Exception:
        return "warn", "Auto-refresh status unknown"
    if not last:
        return "warn", "Auto-refresh has not run yet"
    # Use the leads_index file's mtime as the freshness signal; the log
    # itself is just a "did it run" check.
    return "ok", "Auto-refresh is running"


def _human_age(hours):
    if hours < 1:
        return f"{int(hours * 60)}m"
    if hours < 24:
        return f"{int(hours)}h"
    return f"{int(hours / 24)}d"


def _build_report():
    api_status, api_msg = _check_lofty_api()
    idx_status, idx_msg, idx_count, idx_age_h = _check_leads_index()
    ref_status, ref_msg = _check_auto_refresh()

    statuses = [api_status, idx_status, ref_status]
    if "fail" in statuses:
        overall = "fail"
    elif "warn" in statuses:
        overall = "warn"
    else:
        overall = "ok"

    return {
        "ok": overall == "ok",
        "summary": {
            "ok": "Everything's working",
            "warn": "Needs attention",
            "fail": "Something's broken",
        }[overall],
        "lofty_api": api_msg,
        "leads_index": idx_msg,
        "auto_refresh": ref_msg,
    }


def _pretty(report):
    icon = "OK" if report["ok"] else "!!"
    lines = [f"[{icon}] {report['summary']}"]
    lines.append(f"     Lofty API:     {report['lofty_api']}")
    lines.append(f"     Leads index:   {report['leads_index']}")
    lines.append(f"     Auto-refresh:  {report['auto_refresh']}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Kit health check.")
    parser.add_argument(
        "--json", action="store_true",
        help="Print a JSON report instead of a human summary.",
    )
    args = parser.parse_args()

    try:
        report = _build_report()
    except Exception as e:
        report = {"ok": False, "summary": "Health check itself failed",
                  "error": str(e)}

    # Push a full record into the kit history so we have a trail when
    # something slips past the lean summary. The user never sees this.
    try:
        from kit_history import log_event
        log_event("health_check", **report)
    except Exception:
        # History logging is best-effort; never let it break the check.
        pass

    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(_pretty(report))

    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
