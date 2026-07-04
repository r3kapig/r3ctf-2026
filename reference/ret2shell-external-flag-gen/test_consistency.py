#!/usr/bin/env python3
"""
Consistency test: Python uuid_stego vs Rust ret2script UUIDStego.
Tests XXTEA, encode/decode round-trip, cross-decode, and determinism.
"""

import subprocess
import sys
import uuid as _uuid_mod
from uuid_stego import encode_uuid, decode_uuid, xxtea_encrypt
import struct

RUST_BIN = ["cargo", "run", "--"]
TEST_CASES = [
    ("bangdreamitsmygo", "some_key", 1919810),
    ("hello_world", "secret123", 42),
    ("test_template", "key_abc", 0),
    ("test_template", "key_abc", -1),
    ("a" * 32, "short", 2**63 - 1),
    ("flag_template_2024", "f80f9a197163", 114514),
]

passed = 0
failed = 0


def run_rust(args: list[str]) -> str:
    p = subprocess.run(RUST_BIN + args, capture_output=True, text=True, cwd="/home/reverier/Code/DevOps/r3ctf2026-flaggenerator")
    if p.returncode != 0:
        raise RuntimeError(f"Rust error: {p.stderr.strip()}")
    return p.stdout.strip()


def run_py_encode(template: str, key: str, tid: int) -> str:
    raw = encode_uuid(template, key, tid, True)
    return raw


def run_py_decode(template: str, key: str, flag: str) -> int:
    return decode_uuid(template, key, flag)


def check(name: str, condition: bool, detail: str = ""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}  {detail}")


print("=" * 60)
print("UUID Stego Consistency Test")
print("=" * 60)

for template, key, team_id in TEST_CASES:
    print(f"\n--- Case: template={template!r}, key={key!r}, id={team_id} ---")

    # 1. XXTEA consistency
    py_xxtea = xxtea_encrypt(struct.pack("<q", team_id), key)[:8].hex()
    rust_xxtea = run_rust(["xxtea", key, str(team_id)])
    check("XXTEA match", py_xxtea == rust_xxtea, f"py={py_xxtea} rust={rust_xxtea}")

    # 2. Python self round-trip
    py_flag = run_py_encode(template, key, team_id)
    py_decoded = run_py_decode(template, key, py_flag)
    check("Python round-trip", py_decoded == team_id, f"got {py_decoded}")

    # 3. Rust self round-trip
    rust_flag_full = run_rust(["encode", template, key, str(team_id)])
    rust_flag = rust_flag_full.replace("flag{", "").replace("}", "")
    rust_decoded = run_rust(["decode", template, key, rust_flag])
    check("Rust round-trip", rust_decoded == str(team_id), f"got {rust_decoded}")

    # 4. Python→Rust cross-decode
    rust_cross = run_rust(["decode", template, key, py_flag])
    check("Python→Rust decode", rust_cross == str(team_id), f"got {rust_cross}")

    # 5. Rust→Python cross-decode
    py_cross = run_py_decode(template, key, rust_flag)
    check("Rust→Python decode", py_cross == team_id, f"got {py_cross}")

    # 6. Python determinism (encode twice, same result)
    py_flag2 = run_py_encode(template, key, team_id)
    check("Python determinism", py_flag == py_flag2)

    # 7. UUID format validity
    try:
        _uuid_mod.UUID(py_flag)
        check("Python flag is valid UUID", True)
    except ValueError as e:
        check("Python flag is valid UUID", False, str(e))

    try:
        _uuid_mod.UUID(rust_flag)
        check("Rust flag is valid UUID", True)
    except ValueError as e:
        check("Rust flag is valid UUID", False, str(e))

print("\n" + "=" * 60)
print(f"Results: {passed} passed, {failed} failed out of {passed + failed}")
if failed:
    sys.exit(1)
else:
    print("All tests passed!")
