#!/usr/bin/env python3
from __future__ import annotations

import json
import secrets
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent


def random_password(prefix: str) -> str:
    return f"{prefix}!{secrets.token_hex(8)}9"


def main() -> int:
    entries = [
        {
            "flag": "r3ctf{example_multi_vm_1}",
            "admin_password": random_password("A1"),
            "user_password": random_password("U1"),
            "ssh_port": 30022,
            "timeout": 600,
        },
        {
            "flag": "r3ctf{example_multi_vm_2}",
            "admin_password": random_password("A2"),
            "user_password": random_password("U2"),
            "ssh_port": 30023,
            "timeout": 600,
        },
    ]
    with tempfile.TemporaryDirectory(prefix="babycom-example-") as temp_dir:
        config_path = Path(temp_dir) / "multirun.json"
        config_path.write_text(json.dumps(entries, indent=2), encoding="utf-8")
        return subprocess.call(
            [
                sys.executable,
                str(SCRIPT_DIR / "multirun.py"),
                str(config_path),
            ],
            cwd=str(SCRIPT_DIR),
        )


if __name__ == "__main__":
    raise SystemExit(main())
