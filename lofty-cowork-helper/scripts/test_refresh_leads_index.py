#!/usr/bin/env python3
"""Unit tests for scripts/refresh_leads_index.py.

Stubs out network calls by monkeypatching `_fetch_one_page` and the
LoftyAPI constructor, so the tests are pure logic. Run:

    PYTHONPATH=lofty-cowork-helper/assets \\
        python3 lofty-cowork-helper/scripts/test_refresh_leads_index.py

Exit 0 on all-pass, non-zero on any failure.
"""

import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent / "assets"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ASSETS))

# Set a dummy LOFTY_API_KEY so LoftyAPI() instantiation doesn't fail.
os.environ.setdefault("LOFTY_API_KEY", "test-key-for-unit-tests")

import refresh_leads_index as rli  # noqa: E402

PASS = 0
FAIL = 0
SECTION = ""


def section(name):
    global SECTION
    SECTION = name
    print(f"\n--- {name} ----------")


def assert_eq(label, got, expected):
    global PASS, FAIL
    ok = got == expected
    if ok:
        PASS += 1
        print(f"PASS {SECTION}.{label}")
    else:
        FAIL += 1
        print(f"FAIL {SECTION}.{label}  got={got!r}  expected={expected!r}")


def assert_true(label, cond, msg=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS {SECTION}.{label}")
    else:
        FAIL += 1
        print(f"FAIL {SECTION}.{label}  {msg}")


# -------------------------------------------------------------------
# Fake API: returns canned pages from a script. No rate limit. No HTTP.
# -------------------------------------------------------------------

class FakeAPI:
    """Replaces LoftyAPI for tests.

    `pages` is a list of (page_leads, meta) tuples returned in order by
    successive _fetch_one_page calls. `calls` records the scroll_ids
    received so tests can assert pagination behavior.
    """

    def __init__(self, pages):
        self.pages = list(pages)
        self.calls = []

    def consume(self, scroll_id):
        self.calls.append(scroll_id)
        if not self.pages:
            raise RuntimeError("FakeAPI: no more pages programmed")
        return self.pages.pop(0)


def install_fake(fake):
    """Monkeypatch rli._fetch_one_page to drive off FakeAPI."""
    def patched(api, scroll_id=None, page_size=25):  # noqa: ARG001
        return fake.consume(scroll_id)
    rli._fetch_one_page = patched


def make_lead(lead_id, first="First", last=f"Last"):
    return {
        "leadId": lead_id,
        "firstName": first,
        "lastName": last,
        "emails": [],
        "phones": [],
    }


def fresh_tmp():
    """Return a clean tempdir path; caller is responsible for cleanup."""
    d = Path(tempfile.mkdtemp(prefix="refresh-test-"))
    return d


# -------------------------------------------------------------------
# Tests: incremental mode
# -------------------------------------------------------------------

def test_incremental_no_baseline_escalates():
    section("incremental.no-baseline")
    tmp = fresh_tmp()
    try:
        output = tmp / "leads_index.json"
        # No baseline file. Should exit 2 with no API call.
        fake = FakeAPI(pages=[])
        install_fake(fake)
        rc = rli._run_incremental(api=None, output=output, verbose=False)
        assert_eq("exit_code", rc, rli.EXIT_ESCALATE)
        assert_eq("no_api_call", len(fake.calls), 0)
        # File should NOT have been created.
        assert_eq("no_file_written", output.exists(), False)
        # Log line written with reason.
        log = (tmp / ".refresh-log.jsonl").read_text().strip()
        entry = json.loads(log)
        assert_eq("log_reason", entry["reason"], "no_baseline_file")
        assert_eq("log_mode", entry["mode"], "incremental")
    finally:
        shutil.rmtree(tmp)


def test_incremental_parity_ok():
    section("incremental.parity-ok")
    tmp = fresh_tmp()
    try:
        output = tmp / "leads_index.json"
        # Baseline: 3 leads (ids 1, 2, 3).
        baseline = {
            "refreshed_at": "2026-05-12T00:00:00-07:00",
            "refreshed_at_epoch_ms": int(time.time() * 1000) - 86_400_000,
            "count": 3,
            "source": "test",
            "leads": [rli._normalize(make_lead(i)) for i in (1, 2, 3)],
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(baseline))
        # Page 1 echoes the same 3 leads (no new ones), reports total=3.
        page = [make_lead(1), make_lead(2), make_lead(3)]
        fake = FakeAPI(pages=[(page, {"total": 3, "scrollId": "next"})])
        install_fake(fake)
        rc = rli._run_incremental(api=None, output=output, verbose=False)
        assert_eq("exit_code", rc, rli.EXIT_OK)
        merged = json.loads(output.read_text())
        assert_eq("count_unchanged", merged["count"], 3)
        log = (tmp / ".refresh-log.jsonl").read_text().strip()
        entry = json.loads(log)
        assert_eq("log_new_leads", entry["new_leads"], 0)
        assert_eq("log_updated", entry["updated_leads"], 3)
        assert_eq("log_lofty_total", entry["lofty_total"], 3)
    finally:
        shutil.rmtree(tmp)


def test_incremental_new_lead_merged():
    section("incremental.new-lead-merged")
    tmp = fresh_tmp()
    try:
        output = tmp / "leads_index.json"
        baseline = {
            "refreshed_at": "2026-05-12T00:00:00-07:00",
            "refreshed_at_epoch_ms": int(time.time() * 1000) - 86_400_000,
            "count": 3,
            "source": "test",
            "leads": [rli._normalize(make_lead(i)) for i in (1, 2, 3)],
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(baseline))
        # Page 1 has 4 leads (one new id=4), total=4.
        page = [make_lead(4, "New", "Person"), make_lead(1), make_lead(2), make_lead(3)]
        fake = FakeAPI(pages=[(page, {"total": 4, "scrollId": "next"})])
        install_fake(fake)
        rc = rli._run_incremental(api=None, output=output, verbose=False)
        assert_eq("exit_code", rc, rli.EXIT_OK)
        merged = json.loads(output.read_text())
        assert_eq("count_after", merged["count"], 4)
        ids = sorted(l["leadId"] for l in merged["leads"])
        assert_eq("ids_after", ids, [1, 2, 3, 4])
    finally:
        shutil.rmtree(tmp)


def test_incremental_escalates_when_total_too_high():
    # Lofty reports more leads than fit on page 1 after merging the
    # baseline. Means more new leads exist on later pages; only a full
    # scan can recover them. Should exit 2.
    section("incremental.escalate-when-total-higher")
    tmp = fresh_tmp()
    try:
        output = tmp / "leads_index.json"
        baseline = {
            "refreshed_at": "2026-05-12T00:00:00-07:00",
            "refreshed_at_epoch_ms": int(time.time() * 1000) - 86_400_000,
            "count": 3,
            "source": "test",
            "leads": [rli._normalize(make_lead(i)) for i in (1, 2, 3)],
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(baseline))
        # Page 1: one new lead (id=4), but Lofty says total=10.
        page = [make_lead(4), make_lead(1), make_lead(2)]
        fake = FakeAPI(pages=[(page, {"total": 10})])
        install_fake(fake)
        rc = rli._run_incremental(api=None, output=output, verbose=False)
        assert_eq("exit_code", rc, rli.EXIT_ESCALATE)
        # The merged file should still have been written (best effort).
        merged = json.loads(output.read_text())
        assert_eq("merged_count", merged["count"], 4)
    finally:
        shutil.rmtree(tmp)


def test_incremental_escalates_when_deletions_detected():
    # Lofty reports fewer leads than the merged local count, which can
    # only happen via upstream deletions.
    section("incremental.escalate-when-total-lower")
    tmp = fresh_tmp()
    try:
        output = tmp / "leads_index.json"
        baseline = {
            "refreshed_at": "2026-05-12T00:00:00-07:00",
            "refreshed_at_epoch_ms": int(time.time() * 1000) - 86_400_000,
            "count": 5,
            "source": "test",
            "leads": [rli._normalize(make_lead(i)) for i in (1, 2, 3, 4, 5)],
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(baseline))
        # Page 1 returns three IDs (1, 2, 3); Lofty reports total=3.
        # That means leads 4 and 5 were deleted upstream.
        page = [make_lead(1), make_lead(2), make_lead(3)]
        fake = FakeAPI(pages=[(page, {"total": 3})])
        install_fake(fake)
        rc = rli._run_incremental(api=None, output=output, verbose=False)
        assert_eq("exit_code", rc, rli.EXIT_ESCALATE)
    finally:
        shutil.rmtree(tmp)


def test_incremental_handles_api_error():
    section("incremental.api-error")
    tmp = fresh_tmp()
    try:
        output = tmp / "leads_index.json"
        baseline = {
            "refreshed_at": "2026-05-12T00:00:00-07:00",
            "refreshed_at_epoch_ms": int(time.time() * 1000) - 3600_000,
            "count": 1,
            "source": "test",
            "leads": [rli._normalize(make_lead(1))],
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(baseline))

        def boom(api, scroll_id=None, page_size=25):  # noqa: ARG001
            raise RuntimeError("simulated outage")
        rli._fetch_one_page = boom

        rc = rli._run_incremental(api=None, output=output, verbose=False)
        assert_eq("exit_code", rc, rli.EXIT_FAIL)
    finally:
        shutil.rmtree(tmp)


# -------------------------------------------------------------------
# Tests: --full --resumable mode
# -------------------------------------------------------------------

def test_resumable_single_invocation_completes():
    section("resumable.single-invocation")
    tmp = fresh_tmp()
    try:
        output = tmp / "leads_index.json"
        # Three pages, decreasing scrollIds. Final page returns no scrollId.
        pages = [
            ([make_lead(1), make_lead(2)], {"total": 5, "scrollId": "s1"}),
            ([make_lead(3), make_lead(4)], {"total": 5, "scrollId": "s2"}),
            ([make_lead(5)], {"total": 5}),  # no scrollId => done
        ]
        fake = FakeAPI(pages=pages)
        install_fake(fake)
        # Huge budget so we run to completion in one call.
        rc = rli._run_full_resumable(
            api=None, output=output, verbose=False, budget_sec=600
        )
        assert_eq("exit_code", rc, rli.EXIT_OK)
        result = json.loads(output.read_text())
        assert_eq("count", result["count"], 5)
        ids = sorted(l["leadId"] for l in result["leads"])
        assert_eq("ids", ids, [1, 2, 3, 4, 5])
        # State file should be cleaned up.
        state_path = tmp / ".refresh-state.json"
        assert_eq("state_cleared", state_path.exists(), False)
        # First call had scroll_id=None; later calls used scrollIds.
        assert_eq("call_count", len(fake.calls), 3)
        assert_eq("first_call_scroll", fake.calls[0], None)
        assert_eq("second_call_scroll", fake.calls[1], "s1")
        assert_eq("third_call_scroll", fake.calls[2], "s2")
    finally:
        shutil.rmtree(tmp)


def test_resumable_continues_across_invocations():
    section("resumable.multi-invocation")
    tmp = fresh_tmp()
    try:
        output = tmp / "leads_index.json"
        pages = [
            ([make_lead(1)], {"total": 3, "scrollId": "s1"}),
            ([make_lead(2)], {"total": 3, "scrollId": "s2"}),
            ([make_lead(3)], {"total": 3}),
        ]
        fake = FakeAPI(pages=pages)
        install_fake(fake)
        # Budget of 0 forces an exit after every single page.
        rc1 = rli._run_full_resumable(
            api=None, output=output, verbose=False, budget_sec=0
        )
        assert_eq("rc1_continue", rc1, rli.EXIT_CONTINUE)
        # leads_index.json should NOT exist yet; state should.
        assert_eq("no_index_yet", output.exists(), False)
        state_path = tmp / ".refresh-state.json"
        assert_eq("state_exists", state_path.exists(), True)
        state = json.loads(state_path.read_text())
        assert_eq("state_pages_done_1", state["pages_done"], 1)
        assert_eq("state_normalized_count_1", len(state["normalized"]), 1)
        assert_eq("state_scroll_id_1", state["scroll_id"], "s1")

        rc2 = rli._run_full_resumable(
            api=None, output=output, verbose=False, budget_sec=0
        )
        assert_eq("rc2_continue", rc2, rli.EXIT_CONTINUE)
        state2 = json.loads(state_path.read_text())
        assert_eq("state_pages_done_2", state2["pages_done"], 2)
        assert_eq("state_normalized_count_2", len(state2["normalized"]), 2)

        rc3 = rli._run_full_resumable(
            api=None, output=output, verbose=False, budget_sec=0
        )
        assert_eq("rc3_ok", rc3, rli.EXIT_OK)
        result = json.loads(output.read_text())
        ids = sorted(l["leadId"] for l in result["leads"])
        assert_eq("final_ids", ids, [1, 2, 3])
        assert_eq("state_cleared", state_path.exists(), False)
    finally:
        shutil.rmtree(tmp)


def test_resumable_stale_state_is_discarded():
    section("resumable.stale-state-discarded")
    tmp = fresh_tmp()
    try:
        output = tmp / "leads_index.json"
        state_path = tmp / ".refresh-state.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        # Hand-write a state file with an ancient timestamp.
        old_ms = int(time.time() * 1000) - 10 * 24 * 60 * 60 * 1000
        state_path.write_text(json.dumps({
            "started_at": "2026-04-01T00:00:00-07:00",
            "started_at_epoch_ms": old_ms,
            "scroll_id": "from-the-old-days",
            "pages_done": 17,
            "normalized": [rli._normalize(make_lead(999))],
            "leadIds_seen": [999],
            "expected_total": 100,
        }))
        # New pages from a fresh scan.
        pages = [
            ([make_lead(1)], {"total": 1}),
        ]
        fake = FakeAPI(pages=pages)
        install_fake(fake)
        rc = rli._run_full_resumable(
            api=None, output=output, verbose=False, budget_sec=600
        )
        assert_eq("exit_code", rc, rli.EXIT_OK)
        result = json.loads(output.read_text())
        ids = sorted(l["leadId"] for l in result["leads"])
        # The stale state's lead (999) must NOT appear.
        assert_eq("ids_fresh_only", ids, [1])
        # First (and only) API call should have used scroll_id=None,
        # not the stale "from-the-old-days" token.
        assert_eq("first_call_scroll", fake.calls[0], None)
    finally:
        shutil.rmtree(tmp)


def test_resumable_dedupes_across_chunks():
    # If Lofty returns the same lead in two pages (rare, but possible
    # if scrollId pagination overlaps), the resumable scan should
    # de-duplicate by leadId.
    section("resumable.dedupes-across-chunks")
    tmp = fresh_tmp()
    try:
        output = tmp / "leads_index.json"
        pages = [
            ([make_lead(1), make_lead(2)], {"total": 3, "scrollId": "s1"}),
            ([make_lead(2), make_lead(3)], {"total": 3}),  # 2 repeats
        ]
        fake = FakeAPI(pages=pages)
        install_fake(fake)
        rc = rli._run_full_resumable(
            api=None, output=output, verbose=False, budget_sec=600
        )
        assert_eq("exit_code", rc, rli.EXIT_OK)
        result = json.loads(output.read_text())
        ids = sorted(l["leadId"] for l in result["leads"])
        assert_eq("dedupes", ids, [1, 2, 3])
    finally:
        shutil.rmtree(tmp)


def test_resumable_save_state_on_fetch_error():
    section("resumable.error-mid-scan-saves-state")
    tmp = fresh_tmp()
    try:
        output = tmp / "leads_index.json"
        # First page succeeds, second page throws.
        calls = {"n": 0}

        def patched(api, scroll_id=None, page_size=25):  # noqa: ARG001
            calls["n"] += 1
            if calls["n"] == 1:
                return ([make_lead(1)], {"total": 5, "scrollId": "s1"})
            raise RuntimeError("simulated network blip")

        rli._fetch_one_page = patched

        rc = rli._run_full_resumable(
            api=None, output=output, verbose=False, budget_sec=600
        )
        assert_eq("exit_code", rc, rli.EXIT_FAIL)
        # Index file should NOT be partial.
        assert_eq("no_index", output.exists(), False)
        # State should have been saved for next attempt.
        state_path = tmp / ".refresh-state.json"
        assert_eq("state_saved", state_path.exists(), True)
        state = json.loads(state_path.read_text())
        assert_eq("state_pages_done", state["pages_done"], 1)
        assert_eq("state_scroll", state["scroll_id"], "s1")
        assert_eq("state_norm_count", len(state["normalized"]), 1)
    finally:
        shutil.rmtree(tmp)


# -------------------------------------------------------------------
# Tests: helpers
# -------------------------------------------------------------------

def test_normalize_preserves_segments_today():
    # _normalize should already pass segments through. Sanity-check
    # this so the v1.10 "expose segments via the index" feature has
    # a regression net.
    section("normalize.segments")
    raw = {
        "leadId": 42,
        "firstName": "Test",
        "lastName": "Person",
        "segments": ["Buyer", "Sphere"],
    }
    n = rli._normalize(raw)
    assert_eq("segments_present", n["segments"], ["Buyer", "Sphere"])


def test_log_appends_jsonl():
    section("log.appends")
    tmp = fresh_tmp()
    try:
        output = tmp / "leads_index.json"
        rli._append_log(output, {"ts": "now", "mode": "test", "result": "ok"})
        rli._append_log(output, {"ts": "later", "mode": "test", "result": "ok"})
        lines = (tmp / ".refresh-log.jsonl").read_text().strip().split("\n")
        assert_eq("two_lines", len(lines), 2)
        assert_eq("line1_mode", json.loads(lines[0])["mode"], "test")
        assert_eq("line2_ts", json.loads(lines[1])["ts"], "later")
    finally:
        shutil.rmtree(tmp)


# -------------------------------------------------------------------
# Runner
# -------------------------------------------------------------------

def main():
    test_incremental_no_baseline_escalates()
    test_incremental_parity_ok()
    test_incremental_new_lead_merged()
    test_incremental_escalates_when_total_too_high()
    test_incremental_escalates_when_deletions_detected()
    test_incremental_handles_api_error()

    test_resumable_single_invocation_completes()
    test_resumable_continues_across_invocations()
    test_resumable_stale_state_is_discarded()
    test_resumable_dedupes_across_chunks()
    test_resumable_save_state_on_fetch_error()

    test_normalize_preserves_segments_today()
    test_log_appends_jsonl()

    print()
    print(f"{PASS} passed, {FAIL} failed.")
    if FAIL:
        print("Some refresh_leads_index tests FAILED.")
        return 1
    print("All refresh_leads_index tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
