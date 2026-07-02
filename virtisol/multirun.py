#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
RUN_SCRIPT = SCRIPT_DIR / "run.py"


class MultiRunError(RuntimeError):
    pass


def usage() -> str:
    return "./multirun.py <config.json>"


def load_entries(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise MultiRunError(f"Config file does not exist: {path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise MultiRunError(f"Config file is not valid JSON: {exc}") from exc

    if not isinstance(data, list):
        raise MultiRunError("Config file must contain a JSON array.")

    entries: list[dict[str, Any]] = []
    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise MultiRunError(f"Entry {index} must be a JSON object.")
        entries.append(item)
    return entries


def get_required_string(entry: dict[str, Any], index: int, *keys: str) -> str:
    for key in keys:
        value = entry.get(key)
        if isinstance(value, str) and value:
            return value
    joined = ", ".join(keys)
    raise MultiRunError(f"Entry {index} is missing a required string field: {joined}")


def get_required_value(entry: dict[str, Any], index: int, key: str) -> Any:
    if key not in entry:
        raise MultiRunError(f"Entry {index} is missing a required field: {key}")
    return entry[key]


def start_processes(entries: list[dict[str, Any]]) -> list[subprocess.Popen[str]]:
    processes: list[subprocess.Popen[str]] = []
    for index, entry in enumerate(entries, start=1):
        flag = get_required_string(entry, index, "flag")
        admin_password = get_required_string(entry, index, "admin_password")
        user_password = get_required_string(entry, index, "user_password")
        ssh_port = str(get_required_value(entry, index, "ssh_port"))
        timeout = str(get_required_value(entry, index, "timeout"))

        process = subprocess.Popen(
            [
                sys.executable,
                "-u",
                str(RUN_SCRIPT),
                "--ssh-port",
                ssh_port,
                "--admin-password",
                admin_password,
                "--user-password",
                user_password,
                "--flag",
                flag,
                "--timeout",
                timeout,
            ],
            cwd=str(SCRIPT_DIR),
        )
        processes.append(process)
    return processes


def wait_for_processes(processes: list[subprocess.Popen[str]]) -> int:
    return_codes = [process.wait() for process in processes]
    return 0 if all(code == 0 for code in return_codes) else 1


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        raise MultiRunError(f"Usage: {usage()}")

    entries = load_entries(Path(argv[0]).resolve())
    processes = start_processes(entries)
    return wait_for_processes(processes)


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except MultiRunError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise SystemExit(1)
