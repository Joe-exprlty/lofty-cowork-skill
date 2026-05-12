#!/usr/bin/env python3
"""Unit tests for the v1.10 additions to lofty_api.py.

Covers:
  * find_client stale_warning surfacing (task #4)
  * get_lead_segments + segments in find_client matches (task #5)
  * add_tag / remove_tag / set_tags read-merge-write semantics and
    kit_history wiring (task #6)

Run:
    PYTHONPATH=lofty-cowork-helper/assets \\
        python3 lofty-cowork-helper/scripts/test_lofty_api_v1_10.py

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

os.environ.setdefault("LOFTY_API_KEY", "test-key-for-unit-tests")
# Point the kit history file into a tempdir so tests don't pollute
# the real data/ directory.
_HISTORY_TMP = Path(tempfile.mkdtemp(prefix="api-v1-10-test-"))
os.environ["LOFTY_LEADS_INDEX_PATH"] = str(_HISTORY_TMP / "leads_index.json")

from lofty_api import LoftyAPI  # noqa: E402

PASS = 0
FAIL = 0
SECTION = ""


def section(name):
    global SECTION
    SECTION = name
    print(f"\n--- {name} ----------")


def assert_eq(label, got, expected):
    global PASS, FAIL
    if got == expected:
        PASS += 1
        print(f"PASS {SECTION}.{label}")
    else:
        FAIL += 1
        print(f"FAIL {SECTION}.{label}  got={got!r}  expected={expected!r}")


def assert_true(label, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS {SECTION}.{label}")
    else:
        FAIL += 1
        print(f"FAIL {SECTION}.{label}")


# -------------------------------------------------------------------
# Test fixtures
# -------------------------------------------------------------------

def fresh_api():
    """A LoftyAPI instance with the network stubbed out."""
    api = LoftyAPI()
    api._calls = []  # record (method, path, body) for assertions

    def fake_request(method, path, body=None, query_params=None):
        api._calls.append({"method": method, "path": path,
                           "body": body, "query": query_params})
        # Test driver pre-loads canned responses on api._responses
        # (FIFO). Tests that don't need a response can leave it empty.
        if api._responses:
            return api._responses.pop(0)
        return {}

    api._responses = []
    api._request = fake_request
    return api


# -------------------------------------------------------------------
# find_client stale_warning (task #4)
# -------------------------------------------------------------------

def test_find_client_no_stale_warning_when_fresh():
    section("find_client.no-stale-when-fresh")
    api = fresh_api()
    api._leads_index = {
        "refreshed_at_epoch_ms": int(time.time() * 1000) - 60_000,
        "count": 1,
        "leads": [{
            "leadId": 100, "firstName": "Jane", "lastName": "Smith",
            "firstNameLower": "jane", "lastNameLower": "smith",
            "fullNameLower": "jane smith", "stage": "Active",
            "emails": ["jane@example.com"], "phones": ["555-1212"],
            "score": 80, "tags": ["Buyer"], "segments": ["Sphere"],
        }],
    }
    api._index_stale_info = None
    result = api.find_client("Jane")
    assert_true("has_match", "match" in result)
    assert_true("no_stale_key", "stale_warning" not in result)


def test_find_client_attaches_stale_warning():
    section("find_client.attaches-stale-warning")
    api = fresh_api()
    api._leads_index = {
        "refreshed_at_epoch_ms": int(time.time() * 1000) - 5 * 86_400_000,
        "count": 1,
        "leads": [{
            "leadId": 200, "firstName": "John", "lastName": "Doe",
            "firstNameLower": "john", "lastNameLower": "doe",
            "fullNameLower": "john doe", "stage": "Active",
            "emails": [], "phones": [], "score": 0,
            "tags": [], "segments": [],
        }],
    }
    api._index_stale_info = {
        "age_days": 5,
        "message": "Your leads index hasn't refreshed in 5 days.",
        "action": "ask_to_refresh",
    }
    result = api.find_client("John")
    assert_true("has_match", "match" in result)
    assert_true("has_stale_warning", "stale_warning" in result)
    assert_eq("stale_days", result["stale_warning"]["age_days"], 5)
    assert_eq("stale_action",
              result["stale_warning"]["action"], "ask_to_refresh")


def test_find_client_stale_warning_on_no_match():
    section("find_client.stale-warning-on-no-match")
    api = fresh_api()
    api._leads_index = {"refreshed_at_epoch_ms": 0, "count": 0, "leads": []}
    api._index_stale_info = {
        "age_days": 9, "message": "...", "action": "ask_to_refresh",
    }
    # Disable the API fallback so no live request happens.
    result = api.find_client("Nobody", fallback_pages=0)
    assert_true("is_none", result.get("none") is True)
    assert_true("has_stale_warning", "stale_warning" in result)


# -------------------------------------------------------------------
# segments (task #5)
# -------------------------------------------------------------------

def test_find_client_returns_segments_in_match():
    section("find_client.match-includes-segments")
    api = fresh_api()
    api._leads_index = {
        "refreshed_at_epoch_ms": int(time.time() * 1000),
        "count": 1,
        "leads": [{
            "leadId": 300, "firstName": "Test", "lastName": "Person",
            "firstNameLower": "test", "lastNameLower": "person",
            "fullNameLower": "test person", "stage": "Active",
            "emails": [], "phones": [], "score": 50,
            "tags": ["Hot"], "segments": ["Buyer", "Sphere"],
        }],
    }
    api._index_stale_info = None
    result = api.find_client("Test")
    assert_eq("segments_present",
              result["match"]["segments"], ["Buyer", "Sphere"])
    assert_eq("tags_present", result["match"]["tags"], ["Hot"])


def test_get_lead_segments_reads_through():
    section("get_lead_segments.reads-through-get_lead")
    api = fresh_api()
    api._responses = [{"segments": ["A", "B"], "leadId": 42}]
    out = api.get_lead_segments(42)
    assert_eq("returns_segments", out, ["A", "B"])
    assert_eq("called_get_lead",
              api._calls[0]["path"], "/v1.0/leads/42")


def test_get_lead_segments_returns_empty_for_no_segments():
    section("get_lead_segments.empty-when-missing")
    api = fresh_api()
    api._responses = [{"leadId": 7}]  # no segments key
    out = api.get_lead_segments(7)
    assert_eq("returns_empty", out, [])


def test_get_lead_segments_passes_through_api_errors():
    section("get_lead_segments.passes-through-errors")
    api = fresh_api()
    api._responses = [{"error": True, "status": 404, "statusText": "Not Found"}]
    out = api.get_lead_segments(99)
    assert_true("error_passed_through",
                isinstance(out, dict) and out.get("error") is True)


# -------------------------------------------------------------------
# Tag-write helpers (task #6)
# -------------------------------------------------------------------

def test_add_tag_appends_to_existing():
    section("add_tag.appends")
    api = fresh_api()
    # First call: get_lead. Second call: update_lead.
    api._responses = [
        {"leadId": 500, "tags": [{"tagName": "Buyer"}, {"tagName": "Hot"}]},
        {"leadId": 500},  # update_lead response
    ]
    out = api.add_tag(500, "Acreage")
    assert_eq("changed", out["changed"], True)
    assert_eq("after_tags", out["tags"], ["Buyer", "Hot", "Acreage"])
    # Verify the PUT body sent NAMES not IDs and preserved existing tags.
    update_call = api._calls[1]
    assert_eq("update_method", update_call["method"], "PUT")
    assert_eq("update_tags_body",
              update_call["body"]["tags"], ["Buyer", "Hot", "Acreage"])


def test_add_tag_handles_string_tag_shape():
    section("add_tag.string-tag-shape")
    api = fresh_api()
    api._responses = [
        {"leadId": 501, "tags": ["Buyer", "Hot"]},  # strings, not dicts
        {"leadId": 501},
    ]
    out = api.add_tag(501, "Acreage")
    assert_eq("after_tags", out["tags"], ["Buyer", "Hot", "Acreage"])


def test_add_tag_noop_when_already_present():
    section("add_tag.noop-when-present")
    api = fresh_api()
    api._responses = [
        {"leadId": 502, "tags": [{"tagName": "Buyer"}]},
    ]
    out = api.add_tag(502, "Buyer")
    assert_eq("changed", out["changed"], False)
    assert_eq("call_count_no_update", len(api._calls), 1)  # only get_lead


def test_remove_tag_keeps_other_tags():
    section("remove_tag.keeps-others")
    api = fresh_api()
    api._responses = [
        {"leadId": 600, "tags": [{"tagName": "Buyer"},
                                 {"tagName": "Acreage"},
                                 {"tagName": "Hot"}]},
        {"leadId": 600},
    ]
    out = api.remove_tag(600, "Acreage")
    assert_eq("changed", out["changed"], True)
    assert_eq("after_tags", out["tags"], ["Buyer", "Hot"])
    update_body = api._calls[1]["body"]
    assert_eq("body_no_acreage", update_body["tags"], ["Buyer", "Hot"])


def test_remove_tag_noop_when_absent():
    section("remove_tag.noop-when-absent")
    api = fresh_api()
    api._responses = [
        {"leadId": 601, "tags": [{"tagName": "Buyer"}]},
    ]
    out = api.remove_tag(601, "Acreage")
    assert_eq("changed", out["changed"], False)
    assert_eq("call_count_no_update", len(api._calls), 1)


def test_set_tags_explicit_replace():
    section("set_tags.replace")
    api = fresh_api()
    api._responses = [
        {"leadId": 700, "tags": [{"tagName": "Old1"}, {"tagName": "Old2"}]},
        {"leadId": 700},
    ]
    out = api.set_tags(700, ["NewA", "NewB"])
    assert_eq("changed", out["changed"], True)
    assert_eq("after_tags", out["tags"], ["NewA", "NewB"])
    body = api._calls[1]["body"]
    assert_eq("body_tags", body["tags"], ["NewA", "NewB"])


def test_set_tags_rejects_integers():
    # The number-as-tagId trap. set_tags must refuse integer entries
    # to prevent garbage-tag pollution of the team library.
    section("set_tags.rejects-integers")
    api = fresh_api()
    api._responses = [{"leadId": 701, "tags": []}]
    raised = False
    try:
        api.set_tags(701, [123, "real-tag-name"])
    except TypeError:
        raised = True
    assert_true("raised_typeerror", raised)


def test_add_tag_rejects_empty_string():
    section("add_tag.rejects-empty")
    api = fresh_api()
    raised = False
    try:
        api.add_tag(800, "")
    except ValueError:
        raised = True
    assert_true("raised_valueerror", raised)


def test_tag_helpers_log_to_kit_history():
    # Confirm the kit_history pipe is wired. The history file lives
    # next to LEADS_INDEX_PATH, which the harness redirected into a
    # tempdir.
    section("tag_helpers.log-to-kit-history")
    history_file = _HISTORY_TMP / ".kit-history.jsonl"
    # Clear any prior runs.
    if history_file.exists():
        history_file.unlink()
    api = fresh_api()
    api._responses = [
        {"leadId": 900, "tags": [{"tagName": "Buyer"}]},
        {"leadId": 900},
    ]
    api.add_tag(900, "Acreage")
    assert_true("history_file_created", history_file.exists())
    lines = history_file.read_text().splitlines()
    last = json.loads(lines[-1])
    assert_eq("event_type", last["event"], "tag_change")
    assert_eq("action", last["action"], "add")
    assert_eq("lead_id", last["lead_id"], 900)
    assert_eq("tag", last["tag"], "Acreage")
    assert_eq("before", last["before"], ["Buyer"])
    assert_eq("after", last["after"], ["Buyer", "Acreage"])


# -------------------------------------------------------------------
# Runner
# -------------------------------------------------------------------

def main():
    try:
        test_find_client_no_stale_warning_when_fresh()
        test_find_client_attaches_stale_warning()
        test_find_client_stale_warning_on_no_match()

        test_find_client_returns_segments_in_match()
        test_get_lead_segments_reads_through()
        test_get_lead_segments_returns_empty_for_no_segments()
        test_get_lead_segments_passes_through_api_errors()

        test_add_tag_appends_to_existing()
        test_add_tag_handles_string_tag_shape()
        test_add_tag_noop_when_already_present()
        test_remove_tag_keeps_other_tags()
        test_remove_tag_noop_when_absent()
        test_set_tags_explicit_replace()
        test_set_tags_rejects_integers()
        test_add_tag_rejects_empty_string()
        test_tag_helpers_log_to_kit_history()

        print()
        print(f"{PASS} passed, {FAIL} failed.")
        if FAIL:
            print("Some v1.10 lofty_api tests FAILED.")
            return 1
        print("All v1.10 lofty_api tests passed.")
        return 0
    finally:
        # Cleanup the tempdir we created for kit-history isolation.
        shutil.rmtree(_HISTORY_TMP, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
