#!/usr/bin/env python3
"""speedrun checker.

All teams share one container, so the flag is derived per-team:

  1. player enters their team token
  2. we query the platform team API to resolve the token -> team_id
  3. player enters a speedrun code (must be a real code from codes.json)
  4. we generate the team's dynamic flag via the UUID-stego flag-gen
     (same template + key the platform checker uses) and return it

Codes are reusable (the per-team flag already prevents sharing), so they are
validated but never consumed.
"""

import json
import os
import signal
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, "/app")
from uuid_stego import encode_uuid  # noqa: E402

CODES_FILE = Path(os.environ.get("CODES_FILE", "/shared/codes.json"))
TEAM_API_URL = os.environ.get(
    "TEAM_API_URL", "https://ctf2026.r3kapig.com/api/game/1/team/query"
)
FLAG_TEMPLATE = os.environ.get("FLAG_TEMPLATE", "")
FLAG_KEY = os.environ.get("FLAG_KEY", "")
FLAG_PREFIX = os.environ.get("FLAG_PREFIX", "r3ctf")
INVALID_MESSAGE = os.environ.get("INVALID_MESSAGE", "INVALID CODE")
API_TIMEOUT = float(os.environ.get("API_TIMEOUT", "8"))


def load_codes() -> set[str]:
    raw = json.loads(CODES_FILE.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("codes file must be a JSON array of strings")
    return {str(c) for c in raw}


def query_team_id(token: str) -> int:
    url = TEAM_API_URL + "?" + urllib.parse.urlencode({"token": token})
    req = urllib.request.Request(
        url, headers={"User-Agent": "speedrun-checker/1.0"}
    )
    with urllib.request.urlopen(req, timeout=API_TIMEOUT) as resp:
        if resp.status != 200:
            raise ValueError(f"team API HTTP {resp.status}")
        data = json.loads(resp.read().decode("utf-8"))
    tid = data.get("id")
    if not isinstance(tid, int):
        raise ValueError("team API returned no id")
    return tid


def make_flag(team_id: int) -> str:
    content = encode_uuid(FLAG_TEMPLATE, FLAG_KEY, team_id, True)
    return f"{FLAG_PREFIX}{{{content}}}"


def read_line(prompt: str) -> str:
    print(prompt, flush=True)
    line = sys.stdin.readline()
    return line.strip() if line else ""


def main() -> int:
    signal.alarm(120)

    if not FLAG_TEMPLATE or not FLAG_KEY:
        print("CHECKER ERROR: flag template/key not configured", flush=True)
        return 1

    try:
        codes = load_codes()
    except Exception as exc:  # noqa: BLE001
        print(f"CHECKER ERROR: {exc}", flush=True)
        return 1

    # 1. team token -> team_id
    token = read_line("Enter your team token:")
    if not token:
        print("INVALID TOKEN", flush=True)
        return 0
    try:
        team_id = query_team_id(token)
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError, TimeoutError) as exc:
        print(f"INVALID TOKEN ({exc})", flush=True)
        return 0

    # 2. speedrun code
    code = read_line("Enter code:")
    if not code or code not in codes:
        print(INVALID_MESSAGE, flush=True)
        return 0

    # 3. dynamic flag for this team
    print(make_flag(team_id), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
