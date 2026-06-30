#!/usr/bin/env python3

import argparse
import os
import struct
import subprocess
import sys
import tempfile

LP_GEOMETRY_MAGIC = 0x616c4467
LP_METADATA_MAGIC = 0x414c5030
LP_RESERVED_BYTES = 4096
LP_GEOMETRY_OFFSET = LP_RESERVED_BYTES

EXT4_SB_OFFSET = 1024
EXT4_MAGIC_OFFSET = 56
EXT4_MAGIC = b'\x53\xef'

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))

DECOY_FILES = [
    (
        os.path.join(_THIS_DIR, "decoys/system/lib64/libwhisperfx.so"),
        "/system/lib64/libwhisperfx.so",
        0o0644,
    ),

    (
        os.path.join(_THIS_DIR, "decoys/system/lib64/libwhisperimg.so"),
        "/system/lib64/libwhisperimg.so",
        0o0644,
    ),
    (
        os.path.join(_THIS_DIR, "decoys/system/lib64/libwhispervoice.so"),
        "/system/lib64/libwhispervoice.so",
        0o0644,
    ),
    (
        os.path.join(_THIS_DIR, "decoys/system/lib64/libwhispersticker.so"),
        "/system/lib64/libwhispersticker.so",
        0o0644,
    ),
    (
        os.path.join(_THIS_DIR, "decoys/system/lib64/libwhisperpoll.so"),
        "/system/lib64/libwhisperpoll.so",
        0o0644,
    ),
    (
        os.path.join(_THIS_DIR, "decoys/system/bin/whisperctl"),
        "/system/bin/whisperctl",
        0o0755,
    ),

    (
        os.path.join(_THIS_DIR, "decoys/system/bin/whisper_backupd"),
        "/system/bin/whisper_backupd",
        0o0755,
    ),
    (
        os.path.join(_THIS_DIR, "decoys/system/bin/whisper_otad"),
        "/system/bin/whisper_otad",
        0o0755,
    ),
    (
        os.path.join(_THIS_DIR, "decoys/whisper_backupd.rc"),
        "/system/etc/init/whisper_backupd.rc",
        0o0644,
    ),
    (
        os.path.join(_THIS_DIR, "decoys/whisper_otad.rc"),
        "/system/etc/init/whisper_otad.rc",
        0o0644,
    ),
]

def die(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)

def run(cmd, check=True, capture=False):
    kwargs = {}
    if capture:
        kwargs["capture_output"] = True
        kwargs["text"] = True
    result = subprocess.run(cmd, **kwargs)
    if check and result.returncode != 0:
        die(f"Command failed ({result.returncode}): {' '.join(str(c) for c in cmd)}")
    return result

def dir_exists_in_ext4(tmp_ext4, device_path):

    result = run(
        ["debugfs", "-R", f"stat {device_path}", tmp_ext4],
        check=False,
        capture=True,
    )
    combined = result.stderr + result.stdout
    return "Type: directory" in combined

def file_exists_in_ext4(tmp_ext4, device_path):

    result = run(
        ["debugfs", "-R", f"stat {device_path}", tmp_ext4],
        check=False,
        capture=True,
    )
    combined = result.stderr + result.stdout
    return "Inode:" in combined and "File not found" not in combined

def remove_if_present(tmp_ext4, device_path):

    if not file_exists_in_ext4(tmp_ext4, device_path):
        return
    result = run(
        ["debugfs", "-w", "-R", f"rm {device_path}", tmp_ext4],
        check=False,
        capture=True,
    )
    if result.returncode != 0:
        combined = result.stderr + result.stdout
        print(f"[bake_decoys]   WARN: rm {device_path} failed: {combined.strip()}", file=sys.stderr)

def bake_decoys(tmp_ext4):

    print("[bake_decoys] Injecting auxiliary system binaries ...")

    for src, device_path, mode in DECOY_FILES:
        if not os.path.isfile(src):
            die(f"Source not found: {src}\n"
                "  Run 'make x86_64' in aosp/decoys/ first.")

    results = []

    tmpdir = tempfile.mkdtemp(prefix="whisper_decoys_")
    try:
        for src, device_path, mode in DECOY_FILES:
            parent = os.path.dirname(device_path)

            if not dir_exists_in_ext4(tmp_ext4, parent):
                print(f"[bake_decoys]   SKIP {device_path}: parent {parent} does not exist in ext4")
                results.append((device_path, "skipped - parent missing"))
                continue

            remove_if_present(tmp_ext4, device_path)

            mode_sif = f"0{0o100000 | mode:06o}"

            cmds = (
                f"write {src} {device_path}\n"
                f"sif {device_path} mode {mode_sif}\n"
                f"sif {device_path} uid 0\n"
                f"sif {device_path} gid 0\n"
            )
            tmp_cmds = os.path.join(tmpdir, "cmds.txt")
            with open(tmp_cmds, "w") as fh:
                fh.write(cmds)

            inject_result = run(
                ["debugfs", "-w", "-f", tmp_cmds, tmp_ext4],
                check=False,
                capture=True,
            )
            if inject_result.returncode != 0:
                combined = inject_result.stderr + inject_result.stdout
                print(f"[bake_decoys]   SKIP {device_path}: inject failed: {combined.strip()}", file=sys.stderr)
                results.append((device_path, "skipped - inject failed"))
                continue

            stat_result = run(
                ["debugfs", "-R", f"stat {device_path}", tmp_ext4],
                check=False,
                capture=True,
            )
            stat_out = stat_result.stderr + stat_result.stdout
            mode_str = f"{mode:04o}"
            if f"Mode:  {mode_str}" not in stat_out:
                print(f"[bake_decoys]   WARN: {device_path} stat check: {stat_out.strip()}")

            src_size = os.path.getsize(src)
            print(f"[bake_decoys]   OK   {device_path}  mode={mode_str} uid=0 gid=0 size={src_size}")
            results.append((device_path, "ok"))

    finally:
        for fname in os.listdir(tmpdir):
            try:
                os.remove(os.path.join(tmpdir, fname))
            except OSError:
                pass
        try:
            os.rmdir(tmpdir)
        except OSError:
            pass

    ok_count = sum(1 for _, s in results if s == "ok")
    skip_count = len(results) - ok_count
    print(f"[bake_decoys] Done: {ok_count} injected, {skip_count} skipped.")
    return results

def parse_gpt(f):
    f.seek(512)
    hdr = f.read(92)
    if hdr[:8] != b"EFI PART":
        die("Not a GPT disk (EFI PART signature not found at LBA 1)")
    part_start_lba = struct.unpack_from("<Q", hdr, 72)[0]
    num_parts = struct.unpack_from("<I", hdr, 80)[0]
    part_entry_size = struct.unpack_from("<I", hdr, 84)[0]

    f.seek(part_start_lba * 512)
    partitions = {}
    for _ in range(num_parts):
        entry = f.read(part_entry_size)
        if entry[:16] == b"\x00" * 16:
            continue
        start_lba = struct.unpack_from("<Q", entry, 32)[0]
        end_lba = struct.unpack_from("<Q", entry, 40)[0]
        name_bytes = entry[56:128]
        name = name_bytes.decode("utf-16-le").rstrip("\x00")
        partitions[name] = (start_lba, end_lba)
    return partitions

def parse_lp_metadata(f, super_byte_offset):
    f.seek(super_byte_offset + LP_GEOMETRY_OFFSET)
    geom = f.read(52)
    magic = struct.unpack_from("<I", geom, 0)[0]
    if magic != LP_GEOMETRY_MAGIC:
        die(f"LP geometry magic mismatch: {magic:#010x}")

    metadata_hdr_offset = super_byte_offset + LP_RESERVED_BYTES + 2 * 4096
    f.seek(metadata_hdr_offset)
    hdr = f.read(128)
    magic = struct.unpack_from("<I", hdr, 0)[0]
    if magic != LP_METADATA_MAGIC:
        die(f"LP metadata magic mismatch: {magic:#010x}")

    part_offset = struct.unpack_from("<I", hdr, 80)[0]
    part_num = struct.unpack_from("<I", hdr, 84)[0]
    part_entry_size = struct.unpack_from("<I", hdr, 88)[0]
    ext_offset = struct.unpack_from("<I", hdr, 92)[0]
    ext_num = struct.unpack_from("<I", hdr, 96)[0]
    ext_entry_size = struct.unpack_from("<I", hdr, 100)[0]

    tables_base = metadata_hdr_offset + 128

    f.seek(tables_base + part_offset)
    raw_parts = []
    for _ in range(part_num):
        p = f.read(part_entry_size)
        name = p[:36].rstrip(b"\x00").decode("utf-8", errors="replace")
        first_extent = struct.unpack_from("<I", p, 40)[0]
        num_extents = struct.unpack_from("<I", p, 44)[0]
        raw_parts.append((name, first_extent, num_extents))

    f.seek(tables_base + ext_offset)
    raw_extents = []
    for _ in range(ext_num):
        e = f.read(ext_entry_size)
        num_sectors = struct.unpack_from("<Q", e, 0)[0]
        target_type = struct.unpack_from("<I", e, 8)[0]
        target_data = struct.unpack_from("<Q", e, 12)[0]
        raw_extents.append((num_sectors, target_type, target_data))

    results = []
    for name, first_extent, num_extents in raw_parts:
        extents_list = []
        for ei in range(num_extents):
            num_sectors, ttype, target_data = raw_extents[first_extent + ei][:3]
            if ttype != 0:
                continue
            abs_byte = super_byte_offset + target_data * 512
            size_bytes = num_sectors * 512
            extents_list.append((abs_byte, size_bytes))
        if extents_list:
            results.append({"name": name, "extents": extents_list})
    return results

def find_system_ext4(image_path, super_byte_offset):
    with open(image_path, "rb") as f:
        lp_parts = parse_lp_metadata(f, super_byte_offset)
        for part in lp_parts:
            if part["name"] != "system":
                continue
            for abs_byte, size_bytes in part["extents"]:
                f.seek(abs_byte + EXT4_SB_OFFSET + EXT4_MAGIC_OFFSET)
                magic = f.read(2)
                if magic == EXT4_MAGIC:
                    return abs_byte, size_bytes
                else:
                    die(f"system partition at {abs_byte:#x} does not have ext4 magic")
    die("'system' partition not found in LP metadata")

def inject_decoys_into_image(image_path):

    print(f"[bake_decoys] Image: {image_path}")

    with open(image_path, "rb") as f:
        gpt_parts = parse_gpt(f)

    if "super" not in gpt_parts:
        die("'super' partition not found in GPT")
    super_start_lba, super_end_lba = gpt_parts["super"]
    super_byte_offset = super_start_lba * 512
    print(f"[bake_decoys] GPT: super at {super_byte_offset:#x}")

    sys_abs_offset, sys_size = find_system_ext4(image_path, super_byte_offset)
    print(f"[bake_decoys] LP:  system ext4 at {sys_abs_offset:#x}, size {sys_size/1024/1024:.1f} MiB")

    block_sz = 4096
    skip_blocks = sys_abs_offset // block_sz
    count_blocks = sys_size // block_sz
    if sys_abs_offset % block_sz != 0 or sys_size % block_sz != 0:
        block_sz = 1
        skip_blocks = sys_abs_offset
        count_blocks = sys_size

    tmpdir = tempfile.mkdtemp(prefix="whisper_decoy_bake_")
    tmp_ext4 = os.path.join(tmpdir, "system.ext4")
    try:
        print(f"[bake_decoys] Carving system ext4 to {tmp_ext4} ...")
        run([
            "dd", f"if={image_path}", f"of={tmp_ext4}",
            f"bs={block_sz}", f"skip={skip_blocks}", f"count={count_blocks}",
            "status=none",
        ])

        results = bake_decoys(tmp_ext4)

        print(f"[bake_decoys] Writing modified ext4 back to image at {sys_abs_offset:#x} ...")
        run([
            "dd", f"if={tmp_ext4}", f"of={image_path}",
            f"bs={block_sz}", f"seek={skip_blocks}", f"count={count_blocks}",
            "conv=notrunc", "status=none",
        ])
        print("[bake_decoys] Write-back complete.")

    finally:
        try:
            os.remove(tmp_ext4)
        except OSError:
            pass
        try:
            os.rmdir(tmpdir)
        except OSError:
            pass

    print("[bake_decoys] Final verification ...")
    with tempfile.NamedTemporaryFile(suffix=".ext4", delete=False) as tf:
        verify_tmp = tf.name
    try:
        run([
            "dd", f"if={image_path}", f"of={verify_tmp}",
            f"bs={block_sz}", f"skip={skip_blocks}", f"count={count_blocks}",
            "status=none",
        ])

        all_ok = True
        for src, device_path, mode in DECOY_FILES:
            stat_r = run(
                ["debugfs", "-R", f"stat {device_path}", verify_tmp],
                check=False, capture=True,
            )
            s = stat_r.stderr + stat_r.stdout
            if "Inode:" not in s or "File not found" in s:
                print(f"[bake_decoys]   FAIL readback: {device_path} not found")
                all_ok = False
            else:
                import re
                mode_match = re.search(r"Mode:\s+(\S+)", s)
                size_match = re.search(r"Size:\s+(\d+)", s)
                mode_found = mode_match.group(1) if mode_match else "?"
                size_found = size_match.group(1) if size_match else "?"
                expected_size = os.path.getsize(src)
                size_ok = (size_found == str(expected_size))
                print(f"[bake_decoys]   VERIFY {device_path}: mode={mode_found} size={size_found}"
                      f" (expected {expected_size}) {'OK' if size_ok else 'SIZE MISMATCH'}")
                if not size_ok:
                    all_ok = False

        flag_stat = run(
            ["debugfs", "-R", "stat /flag.txt", verify_tmp],
            check=False, capture=True,
        )
        fs = flag_stat.stderr + flag_stat.stdout
        if "Mode:  0600" in fs and "User:     0" in fs:
            print("[bake_decoys]   VERIFY /flag.txt: mode=0600 uid=0 gid=0  [UNCHANGED]")
        else:
            print(f"[bake_decoys]   WARN: /flag.txt stat unexpected:\n{fs}", file=sys.stderr)

        if all_ok:
            print("[bake_decoys] SUCCESS: all decoys present in image.")
        else:
            print("[bake_decoys] WARN: some decoys failed readback verification.")

    finally:
        try:
            os.remove(verify_tmp)
        except OSError:
            pass

    return results

def main():
    parser = argparse.ArgumentParser(
        description="Inject auxiliary system binaries into Android AVD system.img"
    )
    parser.add_argument("--image", required=True, help="Path to a WRITABLE COPY of system.img")
    args = parser.parse_args()

    if not os.path.isfile(args.image):
        die(f"Image not found: {args.image}")
    if not os.access(args.image, os.W_OK):
        die(f"Image is not writable: {args.image}")

    result = subprocess.run(["which", "debugfs"], capture_output=True)
    if result.returncode != 0:
        die("debugfs not found. Install e2fsprogs: sudo apt-get install e2fsprogs")

    inject_decoys_into_image(args.image)

if __name__ == "__main__":
    main()
