#!/usr/bin/env python3
from __future__ import annotations

import secrets
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
FLAG = "r3ctf{example_single_vm}"
SSH_PORT = "30022"
TIMEOUT = "600"


def random_password(prefix: str) -> str:
    return f"{prefix}!{secrets.token_hex(8)}9"


def main() -> int:
    admin_password = random_password("A")
    return subprocess.call(
        [
            sys.executable,
            str(SCRIPT_DIR / "run.py"),
            "--ssh-port",
            SSH_PORT,
            "--admin-password",
            admin_password,
            "--flag",
            FLAG,
            "--timeout",
            TIMEOUT,
        ],
        cwd=str(SCRIPT_DIR),
    )


if __name__ == "__main__":
    raise SystemExit(main())
