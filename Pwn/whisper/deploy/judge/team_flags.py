"""Per-team flags pushed by the per-team auth pod (Model B).

The auth pod is the SOLE source of each team's flag: it pushes the flag to the
judge via POST /admin/flags before the team can lease a victim. The judge no
longer generates flags itself — a lease for a team with no pushed flag is refused.
The victim's /flag.txt therefore matches the flag the scoring platform expects.

Flags are persisted to a JSON file (TEAM_FLAGS_FILE, default /data/team_flags.json)
so a judge restart does not lose them. The file is written atomically; if it cannot
be written the judge still works in-memory (and the auth pod re-pushes on lease).
"""
import json
import logging
import os
import threading

logger = logging.getLogger("team_flags")

_lock = threading.RLock()
_flags: dict[int, str] = {}

FLAGS_FILE = os.environ.get("TEAM_FLAGS_FILE", "/data/team_flags.json")


def _load() -> None:
    if not FLAGS_FILE:
        return
    try:
        with open(FLAGS_FILE) as fh:
            data = json.load(fh)
        with _lock:
            _flags.update({int(k): str(v) for k, v in data.items()})
        logger.info("loaded %d team flags from %s", len(_flags), FLAGS_FILE)
    except FileNotFoundError:
        pass
    except Exception as exc:
        logger.warning("failed to load %s: %s", FLAGS_FILE, exc)


def _save_locked() -> None:
    """Persist _flags to disk. Caller must hold _lock."""
    if not FLAGS_FILE:
        return
    try:
        os.makedirs(os.path.dirname(FLAGS_FILE) or ".", exist_ok=True)
        tmp = FLAGS_FILE + ".tmp"
        with open(tmp, "w") as fh:
            json.dump({str(k): v for k, v in _flags.items()}, fh)
        os.replace(tmp, FLAGS_FILE)
    except Exception as exc:
        logger.warning("failed to persist %s: %s", FLAGS_FILE, exc)


def set_team_flag(team_id: int, flag: str) -> None:
    with _lock:
        _flags[int(team_id)] = str(flag)
        _save_locked()


def get_team_flag(team_id: int) -> str | None:
    with _lock:
        return _flags.get(int(team_id))


def all_team_flags() -> dict[int, str]:
    with _lock:
        return dict(_flags)


_load()
