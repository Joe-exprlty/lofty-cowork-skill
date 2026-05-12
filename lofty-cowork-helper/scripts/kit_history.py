"""
Kit history log.
================

Shared helper for appending structured events to data/.kit-history.jsonl.
The user-facing kit_health_check.py summary is intentionally short
(3-5 lines). When something slips past that summary, the history file
is what we read to figure out what happened.

Anything in the kit that does something interesting (health checks,
tag writes, future automated runs) should push a one-line event here.

Usage:
    from kit_history import log_event
    log_event("health_check", ok=True, details={...})

Best-effort: a failed log write never raises. Caller's work always
wins over our ability to record it.
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Auto-prune the history when it grows past this many bytes. Roughly
# one entry per kilobyte, so 1 MB is ~1,000 events: plenty of trail
# for debugging without letting the file grow forever.
_MAX_BYTES = int(os.environ.get("KIT_HISTORY_MAX_BYTES", 1_000_000))
# When pruning, keep this many of the most recent lines.
_KEEP_LINES = int(os.environ.get("KIT_HISTORY_KEEP_LINES", 500))


def _history_path():
    """Resolve the history file path off LEADS_INDEX_PATH's parent.

    Importing lofty_api lazily keeps this module callable from test
    harnesses that haven't set LOFTY_API_KEY.
    """
    try:
        from lofty_api import LEADS_INDEX_PATH
        return LEADS_INDEX_PATH.parent / ".kit-history.jsonl"
    except Exception:
        # Fallback: a path next to this script so we never crash the
        # caller, even in a half-configured environment.
        return Path(__file__).resolve().parent / ".kit-history.jsonl"


def _now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat()


def _maybe_prune(path):
    """If the file is over the byte cap, keep only the last _KEEP_LINES."""
    try:
        if path.stat().st_size <= _MAX_BYTES:
            return
        lines = path.read_text(encoding="utf-8").splitlines()
        keep = lines[-_KEEP_LINES:]
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text("\n".join(keep) + "\n", encoding="utf-8")
        os.replace(tmp, path)
    except Exception:
        # Pruning is best-effort. A stuck pruner shouldn't break the
        # next log_event call.
        pass


def log_event(event_type, **fields):
    """Append a single event to data/.kit-history.jsonl.

    `event_type` is a short string ("health_check", "tag_change",
    "refresh_escalate", etc.). Everything else is event-specific
    metadata. A timestamp is added automatically.

    Returns the dict that was (or would have been) written, so callers
    can also log it locally if they want. Never raises.
    """
    entry = {"ts": _now_iso(), "event": event_type}
    entry.update(fields)
    path = _history_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
        _maybe_prune(path)
    except Exception as e:
        # Best-effort: surface the failure to stderr but never raise.
        print(f"[warn] kit_history.log_event failed: {e}", file=sys.stderr)
    return entry


def read_recent(limit=20):
    """Return the most recent `limit` events as a list of dicts.

    Lets Claude inspect the history without shelling out to `tail`.
    Malformed lines are skipped silently.
    """
    path = _history_path()
    if not path.is_file():
        return []
    out = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return []
    for line in lines[-limit:]:
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out


if __name__ == "__main__":
    # Tiny CLI so Claude (or Joe) can read the history from a terminal.
    # Usage: python3 scripts/kit_history.py [N]
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    events = read_recent(limit=n)
    if not events:
        print("No kit history yet.")
        sys.exit(0)
    for e in events:
        ts = e.pop("ts", "")
        ev = e.pop("event", "")
        print(f"{ts}  {ev}  {json.dumps(e, default=str)}")
