#!/usr/bin/env python3
"""
Setup check for the Lofty + Claude Cowork skill.

Run this from the user's workspace folder:
    python3 .claude/skills/lofty-cowork-helper/scripts/setup_check.py

It verifies:
  1. Python version is 3.11 or newer
  2. .env exists in the workspace root
  3. LOFTY_API_KEY is set
  4. The Lofty API responds to a basic call

Outputs a clear pass/fail line for each check, and a final summary.
Exits 0 on full pass, 1 on any failure.
"""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


def check(label, ok, detail=""):
    status = "PASS" if ok else "FAIL"
    line = f"[{status}] {label}"
    if detail:
        line += f" -- {detail}"
    print(line)
    return ok


def find_env_file(start_path):
    """Walk up from start_path looking for .env. Returns the path or None."""
    current = Path(start_path).resolve()
    for _ in range(5):  # don't walk forever
        candidate = current / ".env"
        if candidate.is_file():
            return candidate
        if current.parent == current:
            break
        current = current.parent
    return None


def parse_env(env_path):
    """Read a .env file into a dict. Ignores comments and blanks."""
    out = {}
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        out[key.strip()] = val.strip().strip('"').strip("'")
    return out


def call_lofty_me(api_key):
    """Make one call to /v1.0/me. Returns (ok, detail)."""
    url = "https://api.lofty.com/v1.0/me"
    req = urllib.request.Request(url, headers={"Authorization": f"token {api_key}"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            name = data.get("firstName", "") + " " + data.get("lastName", "")
            user_id = data.get("userId") or data.get("id")
            return True, f"connected as {name.strip()} (userId {user_id})"
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8")[:200]
        except Exception:
            pass
        return False, f"HTTP {e.code} {e.reason}: {body}"
    except urllib.error.URLError as e:
        return False, f"network error: {e.reason}"
    except Exception as e:
        return False, f"unexpected error: {e}"


def main():
    print("Lofty + Cowork setup check")
    print("=" * 40)

    all_ok = True

    # 1. Python version
    py_ok = sys.version_info >= (3, 11)
    all_ok &= check(
        "Python 3.11 or newer",
        py_ok,
        f"running {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    )

    # 2. .env file
    env_path = find_env_file(os.getcwd())
    env_ok = env_path is not None
    all_ok &= check(
        ".env file present",
        env_ok,
        f"found at {env_path}" if env_ok else "not found in this folder or any parent",
    )

    # 3. LOFTY_API_KEY set
    api_key = None
    if env_ok:
        env = parse_env(env_path)
        api_key = env.get("LOFTY_API_KEY") or os.environ.get("LOFTY_API_KEY")
    else:
        api_key = os.environ.get("LOFTY_API_KEY")

    key_ok = bool(api_key) and api_key != "your-lofty-jwt-here"
    all_ok &= check(
        "LOFTY_API_KEY set to a real value",
        key_ok,
        "still set to placeholder; paste your actual JWT" if api_key == "your-lofty-jwt-here"
        else ("present" if key_ok else "missing"),
    )

    # 4. Lofty responds
    if key_ok:
        ok, detail = call_lofty_me(api_key)
        all_ok &= check("Lofty API responds to /v1.0/me", ok, detail)
    else:
        check("Lofty API responds to /v1.0/me", False, "skipped: no API key to test with")
        all_ok = False

    # Summary
    print("=" * 40)
    if all_ok:
        print("All checks passed. Setup is complete.")
        sys.exit(0)
    else:
        print("Some checks failed. See lines above.")
        print("Common fixes:")
        print("  - Make sure .env sits in your workspace root, not in scripts/")
        print("  - Verify LOFTY_API_KEY is your real Lofty JWT (starts with eyJ)")
        print("  - For HTTP 401 / Bad credentials: rotate the key in Lofty Settings")
        print("  - For error 200058: confirm you did not edit lofty_api.py auth header")
        sys.exit(1)


if __name__ == "__main__":
    main()
