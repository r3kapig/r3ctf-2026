#!/usr/bin/env python3
from __future__ import annotations

import argparse
import platform
import random
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(line_buffering=True)


# Counts how many VM cycles this process has run. The first cycle sleeps a
# random duration in [0, timeout] so that, across many instances started at the
# same time, the first restart (and therefore every later restart) is spread
# uniformly over the interval instead of firing all at once.
_run_cycle = 0


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent

# --- challenge image -------------------------------------------------------
# Windows qcow2 with the challenge already baked in (patched/signed driver,
# testsigning on, Secure Boot off) and OpenSSH Server installed + running.
BASE_IMAGE = SCRIPT_DIR / "ctf.qcow2"

# Optional OVMF NVRAM seed containing the Windows UEFI boot entry. Empty/factory
# NVRAM can't locate the Windows bootloader and OVMF black-screen loops, so if
# this file exists it is used instead of the pristine firmware vars. Ship it
# next to run.py (e.g. a copy of the ovmf-vars.fd you boot the image with).
OVMF_VARS_SEED = SCRIPT_DIR / "ovmf-vars.fd"

# --- bootstrap admin (MUST already exist in BASE_IMAGE) --------------------
# run.py SSHes in as this account to provision, then rotates its password to
# the per-instance --admin-password. Set both to match your image exactly.
BOOTSTRAP_ADMIN_USER = "Admin"
BOOTSTRAP_ADMIN_PASSWORD = "!R3k4CtF_4DM1n!"

# --- player account --------------------------------------------------------
HACKER_USER = "hacker"
HACKER_PASSWORD = "hacker123@"   # fixed credential handed to players

LOG_DIR = Path(tempfile.gettempdir()) / "logs"
FLAG_DISK_SIZE = 1024
FLAG_MAX_BYTES = 127
PASSWORD_MAX_BYTES = 127
BOOT_TIMEOUT = 240.0
MEMORY_MB = 4096
CPU_COUNT = 2
PUBLIC_HOST = "0.0.0.0"
LOOPBACK_HOST = "127.0.0.1"

PROXY_PY = """\
import socket
import socketserver
import sys
import threading

LISTEN_HOST = sys.argv[1]
LISTEN_PORT = int(sys.argv[2])
TARGET_HOST = sys.argv[3]
TARGET_PORT = int(sys.argv[4])


def forward_stream(source, destination):
    try:
        while True:
            data = source.recv(65536)
            if not data:
                try:
                    destination.shutdown(socket.SHUT_WR)
                except OSError:
                    pass
                return
            destination.sendall(data)
    except OSError:
        try:
            destination.shutdown(socket.SHUT_WR)
        except OSError:
            pass


class ProxyHandler(socketserver.BaseRequestHandler):
    def handle(self):
        upstream = socket.create_connection((TARGET_HOST, TARGET_PORT))
        try:
            self.request.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            upstream.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            workers = [
                threading.Thread(target=forward_stream, args=(self.request, upstream), daemon=True),
                threading.Thread(target=forward_stream, args=(upstream, self.request), daemon=True),
            ]
            for worker in workers:
                worker.start()
            for worker in workers:
                worker.join()
        finally:
            upstream.close()
            self.request.close()


class ProxyServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


with ProxyServer((LISTEN_HOST, LISTEN_PORT), ProxyHandler) as server:
    server.serve_forever()
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ssh-port", required=True, type=int)
    parser.add_argument("--admin-password", required=True)
    # Player password is fixed (HACKER_PASSWORD); the flag is optional and only
    # here so multirun.py / run_example.py keep working if they still pass it.
    parser.add_argument("--user-password", default=HACKER_PASSWORD)
    parser.add_argument("--flag", required=True)
    parser.add_argument("--timeout", required=True, type=float)
    args = parser.parse_args()

    if args.ssh_port <= 0 or args.ssh_port > 65535:
        raise RuntimeError("ssh_port must be between 1 and 65535.")
    if args.timeout <= 0:
        raise RuntimeError("timeout must be greater than zero.")
    if not args.flag.startswith("r3ctf{") or not args.flag.endswith("}"):
        raise RuntimeError("flag must have the form r3ctf{...}.")
    if len(args.flag.encode("utf-8")) > FLAG_MAX_BYTES:
        raise RuntimeError(f"flag must stay under {FLAG_MAX_BYTES} UTF-8 bytes.")
    if args.admin_password == BOOTSTRAP_ADMIN_PASSWORD:
        raise RuntimeError("admin_password must not reuse the built-in bootstrap password.")
    if not args.admin_password:
        raise RuntimeError("admin_password must not be empty.")
    if len(args.admin_password.encode("utf-8")) > PASSWORD_MAX_BYTES:
        raise RuntimeError(f"admin_password must stay under {PASSWORD_MAX_BYTES} UTF-8 bytes.")

    validate_windows_password(args.admin_password, BOOTSTRAP_ADMIN_USER, "admin_password")

    return args


def validate_windows_password(password: str, username: str, field_name: str) -> None:
    if len(password) < 8:
        raise RuntimeError(f"{field_name} must be at least 8 characters.")

    category_count = sum(
        (
            any(char.islower() for char in password),
            any(char.isupper() for char in password),
            any(char.isdigit() for char in password),
            any(not char.isalnum() for char in password),
        )
    )
    if category_count < 3:
        raise RuntimeError(
            f"{field_name} must include at least three of: lowercase, uppercase, digit, symbol."
        )

    if username.lower() in password.lower():
        raise RuntimeError(f"{field_name} must not contain the account name.")


def find_file(candidates: list[str | Path]) -> Path:
    for candidate in candidates:
        path = Path(candidate)
        if path.is_file():
            return path.resolve()
    for candidate in candidates:
        resolved = shutil.which(Path(candidate).name)
        if resolved:
            return Path(resolved).resolve()
    raise RuntimeError("required file or executable not found: " + ", ".join(str(x) for x in candidates))


def qemu_paths() -> tuple[Path, Path, Path]:
    if platform.system() == "Windows":
        qemu = find_file(
            [r"C:\Program Files\qemu\qemu-system-x86_64.exe", "qemu-system-x86_64.exe"]
        )
        candidates = [
            (qemu.parent / "share" / "edk2-x86_64-code.fd", qemu.parent / "share" / "edk2-i386-vars.fd"),
            (qemu.parent / "share" / "edk2-x86_64-code.fd", qemu.parent / "share" / "edk2-x86_64-vars.fd"),
        ]
    else:
        qemu = find_file(
            ["/usr/bin/qemu-system-x86_64", "/usr/local/bin/qemu-system-x86_64", "qemu-system-x86_64"]
        )
        candidates = [
            (Path("/usr/share/OVMF/OVMF_CODE_4M.fd"), Path("/usr/share/OVMF/OVMF_VARS_4M.fd")),
            (Path("/usr/share/OVMF/OVMF_CODE.fd"), Path("/usr/share/OVMF/OVMF_VARS.fd")),
            (Path("/usr/share/edk2/ovmf/OVMF_CODE.fd"), Path("/usr/share/edk2/ovmf/OVMF_VARS.fd")),
            (Path("/usr/share/edk2-ovmf/x64/OVMF_CODE.fd"), Path("/usr/share/edk2-ovmf/x64/OVMF_VARS.fd")),
            (Path("/usr/share/qemu/OVMF_CODE.fd"), Path("/usr/share/qemu/OVMF_VARS.fd")),
        ]

    for code, vars_path in candidates:
        if code.is_file() and vars_path.is_file():
            return qemu, code.resolve(), vars_path.resolve()
    raise RuntimeError("could not find OVMF firmware files.")


def accel() -> str:
    if platform.system() == "Windows":
        return "whpx:tcg"
    if platform.system() == "Linux":
        return "kvm:tcg"
    return "tcg"


def reserve_port(host: str, port: int) -> socket.socket:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((host, port))
    except OSError as exc:
        sock.close()
        raise RuntimeError(f"TCP port {host}:{port} is not available.") from exc
    return sock


def wait_for_ssh_banner(port: int, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((LOOPBACK_HOST, port), timeout=3.0) as sock:
                sock.settimeout(3.0)
                if sock.recv(256).startswith(b"SSH-"):
                    return
        except OSError:
            pass
        time.sleep(2.0)
    raise RuntimeError(f"timed out waiting for SSH on {LOOPBACK_HOST}:{port}.")


def ssh_connect(port: int, username: str, password: str, timeout: float):
    import paramiko

    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(
                LOOPBACK_HOST,
                port=port,
                username=username,
                password=password,
                look_for_keys=False,
                allow_agent=False,
                timeout=5.0,
                auth_timeout=5.0,
                banner_timeout=5.0,
            )
            return client
        except paramiko.AuthenticationException as exc:
            client.close()
            raise RuntimeError(
                f"SSH authentication failed for {username}@{LOOPBACK_HOST}:{port}."
            ) from exc
        except (paramiko.SSHException, OSError, EOFError) as exc:
            client.close()
            last_error = exc
            time.sleep(2.0)
    if last_error is None:
        raise RuntimeError(f"timed out waiting for SSH login on {LOOPBACK_HOST}:{port}.")
    raise RuntimeError(f"timed out waiting for SSH login on {LOOPBACK_HOST}:{port}: {last_error}")


def run_remote(ssh_client, command: str) -> tuple[int, str, str]:
    stdin, stdout, stderr = ssh_client.exec_command(command, timeout=120.0)
    stdin.close()
    return (
        stdout.channel.recv_exit_status(),
        stdout.read().decode("utf-8", errors="replace"),
        stderr.read().decode("utf-8", errors="replace"),
    )


def ensure_remote_dir(sftp, remote_dir: str) -> None:
    try:
        sftp.stat(remote_dir)
    except OSError:
        sftp.mkdir(remote_dir)


def build_provision_script(admin_password_ps: str, hacker_password_ps: str) -> str:
    return (
        "$ErrorActionPreference = 'Stop'\n"
        f"$adminUser = '{BOOTSTRAP_ADMIN_USER}'\n"
        f"$adminPassword = '{admin_password_ps}'\n"
        f"$hackerUser = '{HACKER_USER}'\n"
        f"$hackerPassword = '{hacker_password_ps}'\n"
        "function Set-GuestPassword([string]$UserName, [string]$Password) {\n"
        "  if (Get-Command -Name Set-LocalUser -ErrorAction SilentlyContinue) {\n"
        "    $secure = ConvertTo-SecureString $Password -AsPlainText -Force\n"
        "    Set-LocalUser -Name $UserName -Password $secure\n"
        "  } else {\n"
        "    & net.exe user $UserName $Password | Out-Null\n"
        '    if ($LASTEXITCODE -ne 0) { throw "net user failed for $UserName ($LASTEXITCODE)" }\n'
        "  }\n"
        "}\n"
        "function Ensure-StandardUser([string]$Name, [string]$Password) {\n"
        "  $exists = Get-LocalUser -Name $Name -ErrorAction SilentlyContinue\n"
        "  if (-not $exists) {\n"
        "    if (Get-Command -Name New-LocalUser -ErrorAction SilentlyContinue) {\n"
        "      $secure = ConvertTo-SecureString $Password -AsPlainText -Force\n"
        "      New-LocalUser -Name $Name -Password $secure -PasswordNeverExpires -AccountNeverExpires | Out-Null\n"
        "    } else {\n"
        "      & net.exe user $Name $Password /add | Out-Null\n"
        '      if ($LASTEXITCODE -ne 0) { throw "net user /add failed for $Name ($LASTEXITCODE)" }\n'
        "    }\n"
        "  } else {\n"
        "    Set-GuestPassword -UserName $Name -Password $Password\n"
        "  }\n"
        "  # Standard user only: member of Users (S-1-5-32-545), never Administrators\n"
        "  # (S-1-5-32-544). Keeps the player off any UAC-bypass / admin shortcut.\n"
        "  try { Add-LocalGroupMember    -SID 'S-1-5-32-545' -Member $Name -ErrorAction SilentlyContinue } catch {}\n"
        "  try { Remove-LocalGroupMember -SID 'S-1-5-32-544' -Member $Name -ErrorAction SilentlyContinue } catch {}\n"
        "}\n"
        "try {\n"
        "  Set-GuestPassword  -UserName $adminUser -Password $adminPassword\n"
        "  Ensure-StandardUser -Name $hackerUser  -Password $hackerPassword\n"
        "  # Scratch dir the player can read/write.\n"
        "  $tmpDir = 'C:\\Users\\Public\\tmp'\n"
        "  New-Item -ItemType Directory -Path $tmpDir -Force | Out-Null\n"
        '  & icacls.exe $tmpDir /grant "${hackerUser}:(OI)(CI)F" | Out-Null\n'
        '  if ($LASTEXITCODE -ne 0) { throw "icacls failed for $tmpDir ($LASTEXITCODE)" }\n'
        "  Write-Output 'PROVISIONED'\n"
        "} finally {\n"
        "  Remove-Item -LiteralPath $PSCommandPath -Force -ErrorAction SilentlyContinue\n"
        "}\n"
    )


def expect_auth_failure(port: int, username: str, password: str, timeout: float) -> None:
    try:
        client = ssh_connect(port, username, password, timeout)
    except RuntimeError as exc:
        if "SSH authentication failed" in str(exc):
            return
        raise
    else:
        client.close()
        raise RuntimeError(f"unexpected SSH login success for {username}@{LOOPBACK_HOST}:{port}.")


def stop_process(process: subprocess.Popen[bytes] | subprocess.Popen[str] | None) -> None:
    if process is None or process.poll() is not None:
        return
    if platform.system() == "Windows":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


def main() -> int:
    args = parse_args()
    if not BASE_IMAGE.is_file():
        raise RuntimeError(f"base image does not exist: {BASE_IMAGE}")

    qemu, ovmf_code, ovmf_vars_template = qemu_paths()
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    workdir = Path(tempfile.mkdtemp(prefix="ctf-"))
    log_path = LOG_DIR / f"{args.ssh_port}.log"
    public_port_guard = reserve_port(PUBLIC_HOST, args.ssh_port)
    bootstrap_guard = reserve_port(LOOPBACK_HOST, 0)
    bootstrap_port = int(bootstrap_guard.getsockname()[1])
    bootstrap_guard.close()
    qemu_process = None
    proxy_process = None

    try:
        admin_password_ps = args.admin_password.replace("'", "''")
        hacker_password_ps = args.user_password.replace("'", "''")
        remote_stage_dir = f"C:/Windows/Temp/ctf-provision-{args.ssh_port}"
        remote_script = f"{remote_stage_dir}/provision.ps1"
        vars_seed = OVMF_VARS_SEED if OVMF_VARS_SEED.is_file() else ovmf_vars_template
        print(f"[*] OVMF NVRAM seed: {vars_seed}", flush=True)
        (workdir / "ovmf-vars.fd").write_bytes(vars_seed.read_bytes())
        flag_disk = bytearray(FLAG_DISK_SIZE)
        flag_bytes = args.flag.encode("utf-8")
        flag_disk[: len(flag_bytes)] = flag_bytes
        flag_disk[len(flag_bytes)] = 0
        (workdir / "flag-drive.raw").write_bytes(flag_disk)
        (workdir / "proxy.py").write_text(PROXY_PY, encoding="utf-8")
        (workdir / "provision.ps1").write_text(
            build_provision_script(admin_password_ps, hacker_password_ps),
            encoding="utf-8",
        )

        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if platform.system() == "Windows" else 0
        with log_path.open("wb") as log_file:
            qemu_process = subprocess.Popen(
                [
                    str(qemu),
                    "-machine",
                    f"pc,accel={accel()}",
                    "-cpu",
                    "max",
                    "-smp",
                    str(CPU_COUNT),
                    "-m",
                    str(MEMORY_MB),
                    "-vga",
                    "std",
                    "-rtc",
                    "base=utc",
                    "-drive",
                    f"if=pflash,format=raw,unit=0,readonly=on,file={ovmf_code}",
                    "-drive",
                    f"if=pflash,format=raw,unit=1,file={workdir / 'ovmf-vars.fd'}",
                    "-drive",
                    f"if=ide,index=0,media=disk,file={BASE_IMAGE},format=qcow2,cache=writeback,discard=unmap,snapshot=on",
                    "-drive",
                    f"if=ide,index=1,media=disk,file={workdir / 'flag-drive.raw'},format=raw,cache=writeback",
                    "-netdev",
                    f"user,id=net0,hostfwd=tcp:{LOOPBACK_HOST}:{bootstrap_port}-:22",
                    "-device",
                    "e1000,netdev=net0",
                    "-display",
                    "none",
                ],
                cwd=str(workdir),
                stdout=log_file,
                stderr=subprocess.STDOUT,
                creationflags=creationflags,
            )

        time.sleep(1.0)
        if qemu_process.poll() is not None:
            raise RuntimeError("QEMU exited immediately.")

        print(f"[*] qemu pid={qemu_process.pid}  ssh-port={args.ssh_port}  log={log_path}", flush=True)
        print(f"[*] booting guest headless; waiting up to {BOOT_TIMEOUT:.0f}s for sshd "
              f"(watch: tail -f {log_path})", flush=True)
        wait_for_ssh_banner(bootstrap_port, BOOT_TIMEOUT)
        print("[*] guest sshd is up; provisioning (set passwords, create hacker)...", flush=True)
        admin = ssh_connect(bootstrap_port, BOOTSTRAP_ADMIN_USER, BOOTSTRAP_ADMIN_PASSWORD, BOOT_TIMEOUT)
        try:
            sftp = admin.open_sftp()
            try:
                ensure_remote_dir(sftp, remote_stage_dir)
                sftp.put(str(workdir / "provision.ps1"), remote_script)
            finally:
                sftp.close()
            status, out, err = run_remote(
                admin,
                'powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File '
                + f'"{remote_script}"',
            )
        finally:
            admin.close()

        if status != 0 or "PROVISIONED" not in out:
            raise RuntimeError(f"guest provisioning failed.\nstdout:\n{out}\nstderr:\n{err}")

        ssh_connect(bootstrap_port, BOOTSTRAP_ADMIN_USER, args.admin_password, 30.0).close()
        ssh_connect(bootstrap_port, HACKER_USER, args.user_password, 30.0).close()

        public_port_guard.close()
        with log_path.open("ab") as log_file:
            proxy_process = subprocess.Popen(
                [
                    sys.executable,
                    "-u",
                    str(workdir / "proxy.py"),
                    PUBLIC_HOST,
                    str(args.ssh_port),
                    LOOPBACK_HOST,
                    str(bootstrap_port),
                ],
                cwd=str(workdir),
                stdout=log_file,
                stderr=subprocess.STDOUT,
                creationflags=creationflags,
            )

        time.sleep(1.0)
        if proxy_process.poll() is not None:
            raise RuntimeError("proxy exited immediately.")

        wait_for_ssh_banner(args.ssh_port, 30.0)
        ssh_connect(args.ssh_port, HACKER_USER, args.user_password, 30.0).close()
        ssh_connect(args.ssh_port, BOOTSTRAP_ADMIN_USER, args.admin_password, 30.0).close()
        expect_auth_failure(args.ssh_port, BOOTSTRAP_ADMIN_USER, BOOTSTRAP_ADMIN_PASSWORD, 15.0)

        print(f"Restart interval: {args.timeout} seconds (VM reboots fresh each cycle; accounts/flag unchanged)")
        print(f"pid={qemu_process.pid} port={args.ssh_port}")
        print(f"ssh=ssh -p {args.ssh_port} {HACKER_USER}@127.0.0.1")
        print(f"password={args.user_password}")
        print(f"admin_password={args.admin_password}")
        print(f"flag={args.flag}")
        print(f"log={log_path}")
        global _run_cycle
        if _run_cycle == 0:
            sleep_for = random.uniform(0, args.timeout)
            print(f"[stagger] first cycle = {sleep_for:.0f}s (random 0..{args.timeout:.0f}); steady = {args.timeout:.0f}s")
        else:
            sleep_for = args.timeout
        _run_cycle += 1
        time.sleep(sleep_for)
        return 0
    finally:
        public_port_guard.close()
        stop_process(proxy_process)
        stop_process(qemu_process)
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    import signal as _signal

    def _on_term(signum, frame):  # noqa: ANN001
        # Run main()'s finally (stop proxy/qemu, remove workdir) before exiting.
        raise SystemExit(0)

    _signal.signal(_signal.SIGTERM, _on_term)
    _signal.signal(_signal.SIGINT, _on_term)
    try:
        while True:
            rc = main()
            if rc != 0:
                raise SystemExit(rc)
            print("[restart] instance timed out; rebooting fresh VM...", flush=True)
    except SystemExit:
        raise
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise SystemExit(1)
