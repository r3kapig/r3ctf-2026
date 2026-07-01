"""Per-team flags pushed by an external party (Model B: per-team auth pod).

In Model B the platform (or a per-team auth pod) generates each team's flag and
pushes it to the judge via POST /admin/flags. When set, the pushed flag takes
precedence over the judge's own flag_stego.make_flag() for that team, so the
victim's /flag.txt matches the flag the scoring platform expects.
"""
import threading

_lock = threading.RLock()
_flags: dict[int, str] = {}


def set_team_flag(team_id: int, flag: str) -> None:
    with _lock:
        _flags[int(team_id)] = str(flag)


def get_team_flag(team_id: int) -> str | None:
    with _lock:
        return _flags.get(int(team_id))


def all_team_flags() -> dict[int, str]:
    with _lock:
        return dict(_flags)
