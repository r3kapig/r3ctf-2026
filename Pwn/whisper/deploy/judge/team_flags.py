"""Per-team flags pushed by the per-team auth pod (Model B).

The auth pod is the SOLE source of each team's flag: it pushes the flag to the
judge via POST /admin/flags before the team can lease a victim. The judge no
longer generates flags itself — a lease for a team with no pushed flag is refused.
The victim's /flag.txt therefore matches the flag the scoring platform expects.
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
