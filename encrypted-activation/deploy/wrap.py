#!/usr/bin/env python3
"""TCP wrapper for task.py (a stdin/stdout service).

Binds 0.0.0.0:PORT (default 1336) and, per connection, spawns task.py with its
stdin/stdout bridged to the client socket. Keeps task.py itself untouched.
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import threading

PORT = int(os.environ.get("PORT", "1336"))
TASK = "/app/task.py"


def handle(conn: socket.socket) -> None:
    proc = subprocess.Popen(
        [sys.executable, TASK],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd="/app",
        bufsize=0,
    )

    def client_to_task() -> None:
        try:
            while True:
                data = conn.recv(65536)
                if not data:
                    break
                proc.stdin.write(data)
        except OSError:
            pass
        finally:
            try:
                proc.stdin.close()
            except OSError:
                pass

    def task_to_client() -> None:
        try:
            while True:
                data = proc.stdout.read(65536)
                if not data:
                    break
                conn.sendall(data)
        except OSError:
            pass
        finally:
            try:
                conn.shutdown(socket.SHUT_WR)
            except OSError:
                pass

    t1 = threading.Thread(target=client_to_task, daemon=True)
    t2 = threading.Thread(target=task_to_client, daemon=True)
    t1.start()
    t2.start()
    proc.wait()
    try:
        conn.close()
    except OSError:
        pass


def main() -> int:
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", PORT))
    srv.listen(16)
    print(f"[*] listening on 0.0.0.0:{PORT}", flush=True)
    with srv:
        while True:
            conn, _addr = srv.accept()
            threading.Thread(target=handle, args=(conn,), daemon=True).start()


if __name__ == "__main__":
    raise SystemExit(main())
