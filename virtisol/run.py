#!/usr/bin/env python3
from __future__ import annotations

import argparse
import platform
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


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
BASE_IMAGE = SCRIPT_DIR / "babycom.qcow2"
SERVICE_SOURCE_DIR = REPO_ROOT / "archive" / "bin"
SERVICE_ARTIFACT_NAMES = ("vaultsvc.exe", "vaultsvc_ps.dll", "vaultsvc.tlb")
SERVICE_NAME = "VaultSvc"
SERVICE_CLSID = "{1B2C3D4E-5F67-8901-A234-56789BCDEF01}"
LOG_DIR = Path(tempfile.gettempdir()) / "logs"
BOOTSTRAP_ADMIN_USER = "Administrator"
BOOTSTRAP_ADMIN_PASSWORD = "!R3k4CtF_4DM1n!"
HACKER_USER = "hacker"
FLAG_DISK_SIZE = 1024
FLAG_MAX_BYTES = 127
PASSWORD_MAX_BYTES = 127
BOOT_TIMEOUT = 240.0
MEMORY_MB = 512
CPU_COUNT = 1
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
    parser.add_argument("--user-password", required=True)
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

    for name in ("admin_password", "user_password"):
        value = getattr(args, name)
        if not value:
            raise RuntimeError(f"{name} must not be empty.")
        if len(value.encode("utf-8")) > PASSWORD_MAX_BYTES:
            raise RuntimeError(f"{name} must stay under {PASSWORD_MAX_BYTES} UTF-8 bytes.")

    validate_windows_password(args.admin_password, BOOTSTRAP_ADMIN_USER, "admin_password")
    validate_windows_password(args.user_password, HACKER_USER, "user_password")

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
            (Path("/usr/share/OVMF/OVMF_CODE.fd"), Path("/usr/share/OVMF/OVMF_VARS.fd")),
            (Path("/usr/share/OVMF/OVMF_CODE_4M.fd"), Path("/usr/share/OVMF/OVMF_VARS_4M.fd")),
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


def challenge_artifacts() -> dict[str, Path]:
    artifacts: dict[str, Path] = {}
    for name in SERVICE_ARTIFACT_NAMES:
        path = (SERVICE_SOURCE_DIR / name).resolve()
        if not path.is_file():
            raise RuntimeError(f"required challenge artifact does not exist: {path}")
        artifacts[name] = path
    return artifacts


def ensure_remote_dir(sftp, remote_dir: str) -> None:
    try:
        sftp.stat(remote_dir)
    except OSError:
        sftp.mkdir(remote_dir)


def build_provision_script(
    admin_password_ps: str, user_password_ps: str, remote_stage_dir: str
) -> str:
    source_dir_ps = remote_stage_dir.replace("'", "''")
    clsid_ps = SERVICE_CLSID.replace("'", "''")
    service_name_ps = SERVICE_NAME.replace("'", "''")
    return (
        "$ErrorActionPreference = 'Stop'\n"
        f"$adminPassword = '{admin_password_ps}'\n"
        f"$userPassword = '{user_password_ps}'\n"
        f"$sourceDir = '{source_dir_ps}'\n"
        "$serviceRoot = 'C:\\CTF\\VaultSvc'\n"
        "$binDir = Join-Path $serviceRoot 'bin'\n"
        "$ctfRoot = 'C:\\CTF'\n"
        "$vaultDir = 'C:\\ProgramData\\Vault'\n"
        "$versionPath = Join-Path $vaultDir 'Version.txt'\n"
        "$sentinelRoot = 'C:\\ProgramData\\SentinelVault'\n"
        "$stagingDir = Join-Path $sentinelRoot 'staging'\n"
        f"$serviceClsid = '{clsid_ps}'\n"
        f"$serviceName = '{service_name_ps}'\n"
        "function Set-GuestPassword([string]$UserName, [string]$Password) {\n"
        "  if (Get-Command -Name Set-LocalUser -ErrorAction SilentlyContinue) {\n"
        "    $securePassword = ConvertTo-SecureString $Password -AsPlainText -Force\n"
        "    Set-LocalUser -Name $UserName -Password $securePassword\n"
        "  } else {\n"
        "    & net.exe user $UserName $Password | Out-Null\n"
        "    if ($LASTEXITCODE -ne 0) {\n"
        '      throw \"net user failed for $UserName with exit code $LASTEXITCODE\"\n'
        "    }\n"
        "  }\n"
        "}\n"
        "function Grant-Acl([string]$Path, [string[]]$Rules) {\n"
        "  & icacls.exe $Path /inheritance:r /grant:r @Rules | Out-Null\n"
        "  if ($LASTEXITCODE -ne 0) {\n"
        '    throw \"icacls failed for $Path with exit code $LASTEXITCODE\"\n'
        "  }\n"
        "}\n"
        "function Remove-RegistryTree([string]$Path) {\n"
        "  if (Test-Path -LiteralPath $Path) {\n"
        "    Remove-Item -LiteralPath $Path -Recurse -Force\n"
        "  }\n"
        "}\n"
        "function Set-ComPermission([string]$RegistryPath, [string]$ValueName, [string]$Sddl) {\n"
        "  $descriptor = New-Object System.Security.AccessControl.RawSecurityDescriptor $Sddl\n"
        "  $bytes = New-Object byte[] $descriptor.BinaryLength\n"
        "  $descriptor.GetBinaryForm($bytes, 0)\n"
        "  New-ItemProperty -Path $RegistryPath -Name $ValueName -Value $bytes -PropertyType Binary -Force | Out-Null\n"
        "}\n"
        "function Wait-ForServiceDeletion([string]$Name, [int]$TimeoutSeconds) {\n"
        "  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)\n"
        "  while ((Get-Date) -lt $deadline) {\n"
        "    if (-not (Get-Service -Name $Name -ErrorAction SilentlyContinue)) {\n"
        "      return\n"
        "    }\n"
        "    Start-Sleep -Seconds 1\n"
        "  }\n"
        '  throw \"service $Name was not deleted in time\"\n'
        "}\n"
        "function Wait-ForServiceState([string]$Name, [string]$DesiredStatus, [int]$TimeoutSeconds) {\n"
        "  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)\n"
        "  while ((Get-Date) -lt $deadline) {\n"
        "    $service = Get-Service -Name $Name -ErrorAction SilentlyContinue\n"
        "    if ($null -ne $service -and $service.Status.ToString() -eq $DesiredStatus) {\n"
        "      return\n"
        "    }\n"
        "    Start-Sleep -Seconds 1\n"
        "  }\n"
        '  throw \"service $Name did not reach state $DesiredStatus in time\"\n'
        "}\n"
        "function Reset-VaultService() {\n"
        "  $service = Get-Service -Name $serviceName -ErrorAction SilentlyContinue\n"
        "  if ($null -ne $service) {\n"
        "    if ($service.Status -ne 'Stopped') {\n"
        "      Stop-Service -Name $serviceName -Force -ErrorAction SilentlyContinue\n"
        "      Start-Sleep -Seconds 1\n"
        "    }\n"
        "    Get-Process -Name vaultsvc -ErrorAction SilentlyContinue | Stop-Process -Force\n"
        "    & sc.exe delete $serviceName | Out-Null\n"
        "    Wait-ForServiceDeletion -Name $serviceName -TimeoutSeconds 30\n"
        "  } else {\n"
        "    Get-Process -Name vaultsvc -ErrorAction SilentlyContinue | Stop-Process -Force\n"
        "  }\n"
        "}\n"
        "try {\n"
        f"  Set-GuestPassword -UserName '{BOOTSTRAP_ADMIN_USER}' -Password $adminPassword\n"
        f"  Set-GuestPassword -UserName '{HACKER_USER}' -Password $userPassword\n"
        "  Reset-VaultService\n"
        "  Remove-RegistryTree -Path (\"HKLM:\\SOFTWARE\\Classes\\CLSID\\\" + $serviceClsid)\n"
        "  Remove-RegistryTree -Path (\"HKLM:\\SOFTWARE\\Classes\\AppID\\\" + $serviceClsid)\n"
        "  Remove-Item -LiteralPath 'C:\\flag.txt' -Force -ErrorAction SilentlyContinue\n"
        "  Remove-Item -LiteralPath $serviceRoot -Recurse -Force -ErrorAction SilentlyContinue\n"
        "  if (Test-Path -LiteralPath $ctfRoot) {\n"
        "    Get-ChildItem -LiteralPath $ctfRoot -Force -ErrorAction SilentlyContinue |\n"
        "      Where-Object { $_.Name -ne 'VaultSvc' } |\n"
        "      Remove-Item -Recurse -Force -ErrorAction SilentlyContinue\n"
        "  }\n"
        "  New-Item -ItemType Directory -Path $ctfRoot, $serviceRoot, $binDir, $vaultDir, $sentinelRoot, $stagingDir -Force | Out-Null\n"
        "  Copy-Item -LiteralPath (Join-Path $sourceDir 'vaultsvc.exe') -Destination (Join-Path $binDir 'vaultsvc.exe') -Force\n"
        "  Copy-Item -LiteralPath (Join-Path $sourceDir 'vaultsvc_ps.dll') -Destination (Join-Path $binDir 'vaultsvc_ps.dll') -Force\n"
        "  Copy-Item -LiteralPath (Join-Path $sourceDir 'vaultsvc.tlb') -Destination (Join-Path $binDir 'vaultsvc.tlb') -Force\n"
        "  Get-ChildItem -LiteralPath $stagingDir -Force -ErrorAction SilentlyContinue |\n"
        "    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue\n"
        "  [System.IO.File]::WriteAllText($versionPath, \"1.0.0`r`n\", [System.Text.Encoding]::ASCII)\n"
        "  Grant-Acl -Path $ctfRoot -Rules @('SYSTEM:(OI)(CI)(F)', 'Administrators:(OI)(CI)(F)', 'Users:(OI)(CI)(RX)')\n"
        "  Grant-Acl -Path $serviceRoot -Rules @('SYSTEM:(OI)(CI)(F)', 'Administrators:(OI)(CI)(F)', 'Users:(OI)(CI)(RX)')\n"
        "  Grant-Acl -Path $binDir -Rules @('SYSTEM:(OI)(CI)(F)', 'Administrators:(OI)(CI)(F)', 'Users:(OI)(CI)(RX)')\n"
        "  Grant-Acl -Path $vaultDir -Rules @('SYSTEM:(OI)(CI)(F)', 'Administrators:(OI)(CI)(F)')\n"
        "  Grant-Acl -Path $versionPath -Rules @('SYSTEM:(F)', 'Administrators:(F)')\n"
        "  Grant-Acl -Path $sentinelRoot -Rules @('SYSTEM:(OI)(CI)(F)', 'Administrators:(OI)(CI)(F)')\n"
        "  Grant-Acl -Path $stagingDir -Rules @('SYSTEM:(OI)(CI)(F)', 'Administrators:(OI)(CI)(F)')\n"
        "  & regsvr32.exe /s (Join-Path $binDir 'vaultsvc_ps.dll')\n"
        "  if ($LASTEXITCODE -ne 0) {\n"
        '    throw \"regsvr32 failed with exit code $LASTEXITCODE\"\n'
        "  }\n"
        "  New-Service -Name $serviceName -BinaryPathName (Join-Path $binDir 'vaultsvc.exe') -DisplayName $serviceName -StartupType Automatic | Out-Null\n"
        "  $clsidKey = 'HKLM:\\SOFTWARE\\Classes\\CLSID\\' + $serviceClsid\n"
        "  $localServerKey = Join-Path $clsidKey 'LocalServer32'\n"
        "  $appIdKey = 'HKLM:\\SOFTWARE\\Classes\\AppID\\' + $serviceClsid\n"
        "  New-Item -Path $clsidKey -Force | Out-Null\n"
        "  Set-Item -Path $clsidKey -Value 'VaultService'\n"
        "  New-ItemProperty -Path $clsidKey -Name 'AppID' -Value $serviceClsid -PropertyType String -Force | Out-Null\n"
        "  New-Item -Path $localServerKey -Force | Out-Null\n"
        "  Set-Item -Path $localServerKey -Value (Join-Path $binDir 'vaultsvc.exe')\n"
        "  New-Item -Path $appIdKey -Force | Out-Null\n"
        "  New-ItemProperty -Path $appIdKey -Name 'LocalService' -Value $serviceName -PropertyType String -Force | Out-Null\n"
        "  Set-ComPermission -RegistryPath $appIdKey -ValueName 'AccessPermission' -Sddl 'O:BAG:BAD:(A;;0x3;;;SY)(A;;0x3;;;BA)(A;;0x3;;;AU)'\n"
        "  Set-ComPermission -RegistryPath $appIdKey -ValueName 'LaunchPermission' -Sddl 'O:BAG:BAD:(A;;0xb;;;SY)(A;;0xb;;;BA)(A;;0xb;;;AU)'\n"
        "  Start-Service -Name $serviceName\n"
        "  Wait-ForServiceState -Name $serviceName -DesiredStatus 'Running' -TimeoutSeconds 30\n"
        "  Write-Output 'PROVISIONED'\n"
        "} finally {\n"
        "  Remove-Item -LiteralPath $sourceDir -Recurse -Force -ErrorAction SilentlyContinue\n"
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

    service_artifacts = challenge_artifacts()
    qemu, ovmf_code, ovmf_vars_template = qemu_paths()
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    workdir = Path(tempfile.mkdtemp(prefix="babycom-"))
    log_path = LOG_DIR / f"{args.ssh_port}.log"
    public_port_guard = reserve_port(PUBLIC_HOST, args.ssh_port)
    bootstrap_guard = reserve_port(LOOPBACK_HOST, 0)
    bootstrap_port = int(bootstrap_guard.getsockname()[1])
    bootstrap_guard.close()
    qemu_process = None
    proxy_process = None

    try:
        admin_password_ps = args.admin_password.replace("'", "''")
        user_password_ps = args.user_password.replace("'", "''")
        remote_stage_dir = f"C:/Windows/Temp/babycom-vaultsvc-{args.ssh_port}"
        remote_script = f"{remote_stage_dir}/provision.ps1"
        (workdir / "ovmf-vars.fd").write_bytes(ovmf_vars_template.read_bytes())
        flag_disk = bytearray(FLAG_DISK_SIZE)
        flag_bytes = args.flag.encode("utf-8")
        flag_disk[: len(flag_bytes)] = flag_bytes
        flag_disk[len(flag_bytes)] = 0
        (workdir / "flag-drive.raw").write_bytes(flag_disk)
        (workdir / "proxy.py").write_text(PROXY_PY, encoding="utf-8")
        (workdir / "provision.ps1").write_text(
            build_provision_script(admin_password_ps, user_password_ps, remote_stage_dir),
            encoding="utf-8",
        )

        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if platform.system() == "Windows" else 0
        with log_path.open("wb") as log_file:
            qemu_process = subprocess.Popen(
                [
                    str(qemu),
                    "-machine",
                    f"pc,accel={accel()}",
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

        wait_for_ssh_banner(bootstrap_port, BOOT_TIMEOUT)
        admin = ssh_connect(bootstrap_port, BOOTSTRAP_ADMIN_USER, BOOTSTRAP_ADMIN_PASSWORD, BOOT_TIMEOUT)
        try:
            sftp = admin.open_sftp()
            try:
                ensure_remote_dir(sftp, remote_stage_dir)
                sftp.put(str(workdir / "provision.ps1"), remote_script)
                for name, local_path in service_artifacts.items():
                    sftp.put(str(local_path), f"{remote_stage_dir}/{name}")
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

        print(f"Timeout: {args.timeout} seconds")
        print(f"pid={qemu_process.pid} port={args.ssh_port}")
        print(f"ssh=ssh -p {args.ssh_port} {HACKER_USER}@127.0.0.1")
        print(f"password={args.user_password}")
        print(f"admin_password={args.admin_password}")
        print(f"flag={args.flag}")
        print(f"log={log_path}")
        time.sleep(args.timeout)
        return 0
    finally:
        public_port_guard.close()
        stop_process(proxy_process)
        stop_process(qemu_process)
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise SystemExit(1)
