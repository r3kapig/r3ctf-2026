"""Per-team flags pushed by the per-team auth pod.

The auth pod is the SOLE source of each team's flag: it pushes the flag to the
judge via POST /admin/flags before the team can lease a victim. The judge no
longer generates flags itself — a lease for a team with no pushed flag is refused.

Flags are stored in a JSON file (TEAM_FLAGS_FILE, default /data/team_flags.json),
which is the source of truth: every read and write goes to the file. Writes are
atomic (write .tmp then os.replace); a reader always sees a consistent snapshot.
"""
import json
import logging
import os
import threading

logger = logging.getLogger("team_flags")

_lock = threading.Lock()

FLAGS_FILE = os.environ.get("TEAM_FLAGS_FILE", "/data/team_flags.json")


def _load_flags() -> dict[int, str]:
    try:
        with open(FLAGS_FILE) as fh:
            return {int(k): str(v) for k, v in json.load(fh).items()}
    except FileNotFoundError:
        return {}


def _save_flags(flags: dict[int, str]) -> None:
    os.makedirs(os.path.dirname(FLAGS_FILE) or ".", exist_ok=True)
    tmp = FLAGS_FILE + ".tmp"
    with open(tmp, "w") as fh:
        json.dump({str(k): v for k, v in flags.items()}, fh)
    os.replace(tmp, FLAGS_FILE)


def set_team_flag(team_id: int, flag: str) -> None:
    with _lock:
        flags = _load_flags()
        flags[int(team_id)] = str(flag)
        _save_flags(flags)


def get_team_flag(team_id: int) -> str | None:
    return _load_flags().get(int(team_id))


def all_team_flags() -> dict[int, str]:
    return _load_flags()
