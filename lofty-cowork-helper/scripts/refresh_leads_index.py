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

Modes (v1.10):
    (default / --full)
        Full scan in one process. Blocks the caller until done.
        ~3 minutes for 650 leads, longer for larger CRMs. Use this
        from a real terminal.

    --incremental
        Fetch only page 1, merge any new leads into the existing
        file, and exit. Fits inside Cowork's 45-second bash timeout.
        Intended for the daily Cowork scheduled task. Exits 2 if
        the incremental probe cannot confirm parity with Lofty
        (suggests upstream deletions or more than 25 new leads),
        which Claude should treat as "run a full --resumable
        scan next."

    --full --resumable
        Chunked full scan suitable for Cowork's bash sandbox.
        Checkpoints state to data/.refresh-state.json after each
        page. Each invocation processes as many pages as fit in
        ~30 seconds. Exits 3 ("continue me") when more pages
        remain. Re-invoke until exit 0. The final leads_index.json
        write is atomic, so a crash mid-run cannot corrupt it.
        Intended for the weekly Cowork scheduled task, driven by
        Claude looping the script.

Usage:
    python3 scripts/refresh_leads_index.py
    python3 scripts/refresh_leads_index.py --output path/to/file.json
    python3 scripts/refresh_leads_index.py --incremental
    python3 scripts/refresh_leads_index.py --full --resumable

Exit codes:
    0   success (file is up to date, possibly unchanged)
    1   hard failure (network error, bad API response, etc.)
    2   incremental probe could not confirm parity; escalate to
        a --full --resumable run on the next opportunity.
    3   --full --resumable processed all the pages it could in
        this invocation; state was saved; re-invoke to continue.

Rate limit:
    Lofty enforces 10 requests per minute. The Python client sleeps
    6.5 seconds between calls. Each page returns 25 leads (API cap).
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

# Wall-time budget for --full --resumable. Cowork bash has a 45 second
# hard timeout; leave a 15 second safety margin for write and exit.
RESUMABLE_BUDGET_SEC = float(os.environ.get("LOFTY_REFRESH_BUDGET_SEC", "30"))

# A saved state older than this is treated as stale and discarded.
# Lofty's scrollId tokens are undocumented but get rejected after a
# while; we play it safe and restart from page 1 if too much time
# has passed since the last chunk.
RESUMABLE_STATE_MAX_AGE_SEC = float(
    os.environ.get("LOFTY_REFRESH_STATE_MAX_AGE_SEC", "3600")
)

# Exit codes. Keep these stable; the Cowork scheduled tasks (and Claude
# itself when looping --full --resumable) branch on them.
EXIT_OK = 0
EXIT_FAIL = 1
EXIT_ESCALATE = 2
EXIT_CONTINUE = 3


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


# -------------------------------------------------------------------
# Shared paging primitives (used by every mode)
# -------------------------------------------------------------------

def _fetch_one_page(api, scroll_id=None, page_size=25):
    """Fetch a single page from /v1.0/leads.

    Returns (page_leads, meta) where meta is the response's _metadata
    block (may include `scrollId` and `total`). Raises RuntimeError
    on an API-level error so callers can decide whether to abort or
    retry.
    """
    if scroll_id:
        data = api._request(
            "GET", "/v1.0/leads", query_params={"scrollId": scroll_id}
        )
    else:
        # First call. Don't pass sortField since it's silently
        # ignored anyway. Default pageSize of 25 is the hard cap.
        data = api._request(
            "GET", "/v1.0/leads",
            query_params={"pageSize": page_size, "page": 1},
        )

    if isinstance(data, dict) and data.get("error"):
        raise RuntimeError(f"API error from /v1.0/leads: {data}")

    page_leads = data.get("leads", []) if isinstance(data, dict) else []
    meta = data.get("_metadata", {}) if isinstance(data, dict) else {}
    return page_leads, meta


def _fetch_all_leads(api, verbose=True):
    """Paginate every lead via scrollId and return a flat list.

    Progress is printed after each page when verbose=True. Handles the
    case where scrollId is None on the last page. Used by the default
    (non-resumable) full scan.
    """
    leads = []
    scroll_id = None
    page_num = 0
    total_expected = None
    start = time.time()

    while True:
        page_num += 1
        page_leads, meta = _fetch_one_page(api, scroll_id=scroll_id)

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


def _build_payload(normalized, source_label):
    """Wrap normalized leads in the canonical leads_index.json envelope."""
    now = datetime.now(timezone.utc).astimezone()
    return {
        "refreshed_at": now.isoformat(),
        "refreshed_at_epoch_ms": int(now.timestamp() * 1000),
        "count": len(normalized),
        "source": source_label,
        "leads": normalized,
    }


# -------------------------------------------------------------------
# Run log (data/.refresh-log.jsonl) and state (data/.refresh-state.json)
# -------------------------------------------------------------------

def _refresh_log_path(output):
    return output.parent / ".refresh-log.jsonl"


def _refresh_state_path(output):
    return output.parent / ".refresh-state.json"


def _append_log(output, entry):
    """Append a single JSON line to data/.refresh-log.jsonl.

    Best-effort. We never let log-write failure abort a refresh run,
    because the run itself succeeded; losing a log line is much less
    bad than failing to update the index.
    """
    path = _refresh_log_path(output)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
    except Exception as e:
        print(f"[warn] failed to append refresh log entry: {e}", file=sys.stderr)


def _now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat()


def _load_state(output):
    """Load data/.refresh-state.json if present and fresh; else None."""
    path = _refresh_state_path(output)
    if not path.is_file():
        return None
    try:
        state = json.loads(path.read_text())
    except Exception as e:
        print(
            f"[warn] could not read {path} ({e}); discarding and starting fresh.",
            file=sys.stderr,
        )
        return None

    started_ms = state.get("started_at_epoch_ms") or 0
    age_sec = (time.time() * 1000 - started_ms) / 1000.0 if started_ms else 0.0
    if age_sec > RESUMABLE_STATE_MAX_AGE_SEC:
        print(
            f"[info] saved state is {int(age_sec)}s old "
            f"(> {int(RESUMABLE_STATE_MAX_AGE_SEC)}s). Discarding and "
            f"starting fresh.",
            flush=True,
        )
        return None
    return state


def _save_state(output, state):
    """Persist data/.refresh-state.json atomically."""
    path = _refresh_state_path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False, default=str))
    os.replace(tmp, path)


def _clear_state(output):
    path = _refresh_state_path(output)
    try:
        path.unlink()
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"[warn] could not delete {path}: {e}", file=sys.stderr)


# -------------------------------------------------------------------
# Mode 1: full scan, single process (default; pre-v1.10 behavior)
# -------------------------------------------------------------------

def _run_full_blocking(api, output, verbose=True):
    if verbose:
        print("Refreshing local leads index (full, single-process)")
        print("=" * 45)
        print(f"Target file: {output}")
        print("Scanning all pages from Lofty. ~3 min for 650 leads.")
        print("Rate limit is 10 requests/min. Please be patient.\n")

    start = time.time()
    raw_leads = _fetch_all_leads(api, verbose=verbose)
    normalized = [_normalize(l) for l in raw_leads]
    payload = _build_payload(
        normalized, "lofty /v1.0/leads (scrollId pagination)"
    )
    _write_atomic(output, payload)

    elapsed = time.time() - start
    if verbose:
        print()
        print("=" * 45)
        print(f"Done. {len(normalized)} leads indexed in {_format_elapsed(elapsed)}.")
        print(f"Written to: {output}")

    _append_log(output, {
        "ts": _now_iso(),
        "mode": "full",
        "result": "ok",
        "leads_count": len(normalized),
        "duration_sec": round(elapsed, 2),
        "exit_code": EXIT_OK,
    })
    return EXIT_OK


# -------------------------------------------------------------------
# Mode 2: incremental (daily Cowork scheduled task)
# -------------------------------------------------------------------

def _run_incremental(api, output, verbose=True):
    """Pull page 1 only, merge into the existing local file.

    Escalation rules (exit code 2):
      * No existing file (nothing to merge into).
      * meta.total > (existing_count + new_unseen_on_page_1).
        Means we missed new leads beyond page 1.
      * meta.total < existing_count + new_unseen_on_page_1.
        Means upstream deletions happened (the incremental cannot
        detect which leadIds were deleted; only a full scan can).

    Other outcomes -> exit 0.
    """
    start = time.time()

    if not output.is_file():
        if verbose:
            print(
                f"[info] {output} not found. Incremental mode cannot run "
                f"without a baseline. Escalating to a full scan.",
                flush=True,
            )
        _append_log(output, {
            "ts": _now_iso(),
            "mode": "incremental",
            "result": "escalate",
            "reason": "no_baseline_file",
            "duration_sec": round(time.time() - start, 2),
            "exit_code": EXIT_ESCALATE,
        })
        return EXIT_ESCALATE

    try:
        existing = json.loads(output.read_text())
    except Exception as e:
        print(
            f"[error] could not parse {output}: {e}. Escalating.",
            file=sys.stderr,
        )
        _append_log(output, {
            "ts": _now_iso(),
            "mode": "incremental",
            "result": "escalate",
            "reason": "baseline_unparseable",
            "duration_sec": round(time.time() - start, 2),
            "exit_code": EXIT_ESCALATE,
        })
        return EXIT_ESCALATE

    existing_leads = existing.get("leads") or []
    existing_by_id = {l.get("leadId"): l for l in existing_leads}
    existing_count = len(existing_by_id)

    if verbose:
        print(
            f"Incremental refresh. Baseline: {existing_count} leads in "
            f"{output.name}.",
            flush=True,
        )

    try:
        page_leads, meta = _fetch_one_page(api, scroll_id=None)
    except Exception as e:
        print(f"[error] {e}", file=sys.stderr)
        _append_log(output, {
            "ts": _now_iso(),
            "mode": "incremental",
            "result": "fail",
            "reason": str(e)[:200],
            "duration_sec": round(time.time() - start, 2),
            "exit_code": EXIT_FAIL,
        })
        return EXIT_FAIL

    meta_total = meta.get("total")
    new_unseen = 0
    updated = 0
    for raw in page_leads:
        lid = raw.get("leadId")
        if lid is None:
            continue
        n = _normalize(raw)
        if lid in existing_by_id:
            existing_by_id[lid] = n
            updated += 1
        else:
            existing_by_id[lid] = n
            new_unseen += 1

    merged = list(existing_by_id.values())
    payload = _build_payload(
        merged, "lofty /v1.0/leads (incremental merge of page 1)"
    )
    _write_atomic(output, payload)
    duration = time.time() - start

    if verbose:
        if meta_total is not None:
            print(
                f"Page 1 returned {len(page_leads)} leads "
                f"({new_unseen} new, {updated} updated). Lofty reports "
                f"total={meta_total}; local now has {len(merged)}.",
                flush=True,
            )
        else:
            print(
                f"Page 1 returned {len(page_leads)} leads "
                f"({new_unseen} new, {updated} updated). Local now has "
                f"{len(merged)}. Lofty did not return a total.",
                flush=True,
            )

    # Decide whether the incremental is enough or whether to escalate.
    escalate_reason = None
    if meta_total is None:
        # We can't confirm parity. Don't escalate every day; just warn.
        # The weekly full will catch up.
        pass
    elif meta_total > len(merged):
        escalate_reason = (
            f"lofty_total={meta_total} > local_after={len(merged)} "
            f"(more new leads than fit on page 1)"
        )
    elif meta_total < len(merged):
        escalate_reason = (
            f"lofty_total={meta_total} < local_after={len(merged)} "
            f"(upstream deletions detected)"
        )

    if escalate_reason:
        if verbose:
            print(
                f"[info] escalating to a full scan: {escalate_reason}",
                flush=True,
            )
        _append_log(output, {
            "ts": _now_iso(),
            "mode": "incremental",
            "result": "escalate",
            "reason": escalate_reason,
            "new_leads": new_unseen,
            "updated_leads": updated,
            "leads_count": len(merged),
            "lofty_total": meta_total,
            "duration_sec": round(duration, 2),
            "exit_code": EXIT_ESCALATE,
        })
        return EXIT_ESCALATE

    _append_log(output, {
        "ts": _now_iso(),
        "mode": "incremental",
        "result": "ok",
        "new_leads": new_unseen,
        "updated_leads": updated,
        "leads_count": len(merged),
        "lofty_total": meta_total,
        "duration_sec": round(duration, 2),
        "exit_code": EXIT_OK,
    })
    if verbose:
        print(f"Incremental complete in {_format_elapsed(duration)}.")
    return EXIT_OK


# -------------------------------------------------------------------
# Mode 3: --full --resumable (weekly Cowork scheduled task)
# -------------------------------------------------------------------

def _run_full_resumable(api, output, verbose=True, budget_sec=None):
    """Process as many pages as fit in budget_sec; checkpoint state.

    Re-invoke this until it exits 0. State lives at
    data/.refresh-state.json. The actual leads_index.json is only
    written when the scan completes; partial state stays in the
    checkpoint file so a crash mid-scan can't corrupt the index.
    """
    budget = budget_sec if budget_sec is not None else RESUMABLE_BUDGET_SEC
    start = time.time()

    state = _load_state(output)
    if state is None:
        state = {
            "started_at": _now_iso(),
            "started_at_epoch_ms": int(time.time() * 1000),
            "scroll_id": None,
            "pages_done": 0,
            "normalized": [],
            "expected_total": None,
            "leadIds_seen": [],
        }
        if verbose:
            print(
                f"Starting resumable full scan. Budget {int(budget)}s per "
                f"invocation. State will live at "
                f"{_refresh_state_path(output)}.",
                flush=True,
            )
    else:
        if verbose:
            print(
                f"Resuming from {state['pages_done']} pages, "
                f"{len(state['normalized'])} leads in state. Budget "
                f"{int(budget)}s.",
                flush=True,
            )

    seen_ids = set(state.get("leadIds_seen") or [])
    normalized = list(state.get("normalized") or [])
    scroll_id = state.get("scroll_id")
    pages_done = int(state.get("pages_done") or 0)
    expected_total = state.get("expected_total")

    # Process pages until we hit the budget OR Lofty stops giving us
    # scroll IDs. We always run at least one page per invocation so
    # the scan still makes progress even when the budget is tight
    # relative to the rate limit.
    pages_this_run = 0
    while True:
        try:
            page_leads, meta = _fetch_one_page(api, scroll_id=scroll_id)
        except Exception as e:
            print(f"[error] page fetch failed: {e}", file=sys.stderr)
            # Save what we have so the next invocation resumes here.
            state.update({
                "scroll_id": scroll_id,
                "pages_done": pages_done,
                "normalized": normalized,
                "leadIds_seen": list(seen_ids),
                "expected_total": expected_total,
            })
            _save_state(output, state)
            _append_log(output, {
                "ts": _now_iso(),
                "mode": "full-resumable",
                "result": "fail",
                "reason": str(e)[:200],
                "pages_done": pages_done,
                "leads_so_far": len(normalized),
                "duration_sec": round(time.time() - start, 2),
                "exit_code": EXIT_FAIL,
            })
            return EXIT_FAIL

        pages_done += 1
        pages_this_run += 1
        if expected_total is None:
            expected_total = meta.get("total")
        scroll_id = meta.get("scrollId")

        for raw in page_leads:
            lid = raw.get("leadId")
            if lid is None or lid in seen_ids:
                continue
            seen_ids.add(lid)
            normalized.append(_normalize(raw))

        if verbose:
            elapsed = time.time() - start
            if expected_total:
                pct = min(100, int(len(normalized) * 100 / expected_total))
                print(
                    f"  page {pages_done:>2d} | {len(normalized):>4d}/"
                    f"{expected_total} leads ({pct}%) | this-run "
                    f"{_format_elapsed(elapsed)}",
                    flush=True,
                )
            else:
                print(
                    f"  page {pages_done:>2d} | {len(normalized):>4d} leads "
                    f"so far | this-run {_format_elapsed(elapsed)}",
                    flush=True,
                )

        done = (not page_leads) or (not scroll_id)
        if done:
            break

        # Budget check: only AFTER at least one page has run, so we
        # always make progress. The 6.5s rate-limit delay happens
        # inside the next _fetch_one_page call, so a "running" budget
        # check before that is the right shutdown point.
        if (time.time() - start) >= budget:
            break

    duration = time.time() - start

    if (not page_leads) or (not scroll_id):
        # Done. Write the real index file, clear state.
        payload = _build_payload(
            normalized,
            "lofty /v1.0/leads (resumable full scan)",
        )
        _write_atomic(output, payload)
        _clear_state(output)

        if verbose:
            print()
            print("=" * 45)
            print(
                f"Full scan complete. {len(normalized)} leads indexed. "
                f"This invocation: {_format_elapsed(duration)} across "
                f"{pages_this_run} page(s).",
            )
            print(f"Written to: {output}")

        _append_log(output, {
            "ts": _now_iso(),
            "mode": "full-resumable",
            "result": "ok",
            "leads_count": len(normalized),
            "pages_done_total": pages_done,
            "pages_done_this_run": pages_this_run,
            "duration_sec": round(duration, 2),
            "exit_code": EXIT_OK,
        })
        return EXIT_OK

    # Out of budget but more pages remain. Save state, exit 3.
    state.update({
        "scroll_id": scroll_id,
        "pages_done": pages_done,
        "normalized": normalized,
        "leadIds_seen": list(seen_ids),
        "expected_total": expected_total,
    })
    _save_state(output, state)

    if verbose:
        print()
        print(
            f"Hit per-invocation budget after {pages_this_run} page(s) "
            f"({_format_elapsed(duration)}). State saved with "
            f"{len(normalized)} leads. Re-invoke this script to continue.",
            flush=True,
        )

    _append_log(output, {
        "ts": _now_iso(),
        "mode": "full-resumable",
        "result": "continue",
        "pages_done_total": pages_done,
        "pages_done_this_run": pages_this_run,
        "leads_so_far": len(normalized),
        "expected_total": expected_total,
        "duration_sec": round(duration, 2),
        "exit_code": EXIT_CONTINUE,
    })
    return EXIT_CONTINUE


# -------------------------------------------------------------------
# CLI
# -------------------------------------------------------------------

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

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--incremental",
        action="store_true",
        help=(
            "Fetch page 1 only and merge new leads into the existing file. "
            "Fits inside Cowork's 45s bash timeout. Exits 2 if Lofty's "
            "reported total disagrees with the merged local count."
        ),
    )
    mode.add_argument(
        "--full",
        action="store_true",
        help=(
            "Full scan (default behavior). Combine with --resumable to run "
            "across multiple Cowork bash invocations."
        ),
    )

    parser.add_argument(
        "--resumable",
        action="store_true",
        help=(
            "Only valid with --full. Checkpoints state per page; exits 3 "
            "when the per-invocation budget is reached. Re-invoke until "
            "exit 0."
        ),
    )
    parser.add_argument(
        "--budget-sec",
        type=float,
        default=None,
        help=(
            f"Wall-time budget per --full --resumable invocation. Default: "
            f"{int(RESUMABLE_BUDGET_SEC)}s. Tune down if you see Cowork "
            f"timeouts."
        ),
    )

    args = parser.parse_args()

    if args.resumable and not args.full:
        parser.error("--resumable is only valid with --full")

    output = Path(args.output)
    verbose = not args.quiet
    api = LoftyAPI()

    if args.incremental:
        return _run_incremental(api, output, verbose=verbose)

    if args.full and args.resumable:
        return _run_full_resumable(
            api, output, verbose=verbose, budget_sec=args.budget_sec
        )

    return _run_full_blocking(api, output, verbose=verbose)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted. No file was written.", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"\n[FATAL] {e}", file=sys.stderr)
        sys.exit(EXIT_FAIL)
