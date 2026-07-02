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
        die(f"LP geometry magic mismatch: {magic:#010x} (expected {LP_GEOMETRY_MAGIC:#010x})")
    metadata_max_size = struct.unpack_from("<I", geom, 40)[0]
    metadata_slot_count = struct.unpack_from("<I", geom, 44)[0]

    metadata_hdr_offset = super_byte_offset + LP_RESERVED_BYTES + 2 * 4096
    f.seek(metadata_hdr_offset)
    hdr = f.read(128)
    magic = struct.unpack_from("<I", hdr, 0)[0]
    if magic != LP_METADATA_MAGIC:
        die(f"LP metadata magic mismatch: {magic:#010x} (expected {LP_METADATA_MAGIC:#010x})")

    part_offset = struct.unpack_from("<I", hdr, 80)[0]
    part_num = struct.unpack_from("<I", hdr, 84)[0]
    part_entry_size = struct.unpack_from("<I", hdr, 88)[0]

    ext_offset = struct.unpack_from("<I", hdr, 92)[0]
    ext_num = struct.unpack_from("<I", hdr, 96)[0]
    ext_entry_size = struct.unpack_from("<I", hdr, 100)[0]

    bd_offset = struct.unpack_from("<I", hdr, 116)[0]
    bd_num = struct.unpack_from("<I", hdr, 120)[0]
    bd_entry_size = struct.unpack_from("<I", hdr, 124)[0]

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
        target_source = struct.unpack_from("<I", e, 20)[0]
        raw_extents.append((num_sectors, target_type, target_data, target_source))

    results = []
    for name, first_extent, num_extents in raw_parts:
        extents_list = []
        for ei in range(num_extents):
            num_sectors, ttype, target_data, target_source = raw_extents[first_extent + ei]
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
                    die(
                        f"'system' partition at {abs_byte:#x} does not have ext4 magic "
                        f"(got {magic.hex()}, expected 53ef)"
                    )
        die("'system' partition not found in LP metadata")

def bake_flag(image_path, flag_value):

    print(f"[bake_flag] Image: {image_path}")
    print(f"[bake_flag] Flag:  [REDACTED ({len(flag_value)} bytes)]")

    with open(image_path, "rb") as f:
        gpt_parts = parse_gpt(f)

    if "super" not in gpt_parts:
        die("'super' partition not found in GPT")
    super_start_lba, super_end_lba = gpt_parts["super"]
    super_byte_offset = super_start_lba * 512
    super_size = (super_end_lba - super_start_lba + 1) * 512
    print(f"[bake_flag] GPT: super at byte offset {super_byte_offset:#x}, size {super_size:#x} ({super_size/1024/1024:.1f} MiB)")

    sys_abs_offset, sys_size = find_system_ext4(image_path, super_byte_offset)
    print(f"[bake_flag] LP:   system ext4 at byte offset {sys_abs_offset:#x}, size {sys_size:#x} ({sys_size/1024/1024:.1f} MiB)")

    with open(image_path, "rb") as f:
        f.seek(sys_abs_offset + EXT4_SB_OFFSET)
        sb = f.read(264)
    free_blocks = struct.unpack_from("<I", sb, 12)[0]
    log2_bs = struct.unpack_from("<I", sb, 24)[0]
    block_size = 1024 << log2_bs
    free_mb = free_blocks * block_size / 1024 / 1024
    print(f"[bake_flag] ext4: block_size={block_size} free_blocks={free_blocks} ({free_mb:.1f} MiB free)")
    if free_blocks < 8:
        die("ext4 filesystem has fewer than 8 free blocks; insufficient space for /flag.txt")

    tmpdir = tempfile.mkdtemp(prefix="whisper_bake_")
    tmp_ext4 = os.path.join(tmpdir, "system.ext4")
    tmp_flag = os.path.join(tmpdir, "flag.txt")
    tmp_cmds = os.path.join(tmpdir, "dbfs_cmds.txt")

    try:

        block_sz = 4096
        skip_blocks = sys_abs_offset // block_sz
        count_blocks = sys_size // block_sz
        if sys_abs_offset % block_sz != 0 or sys_size % block_sz != 0:

            block_sz = 1
            skip_blocks = sys_abs_offset
            count_blocks = sys_size

        print(f"[bake_flag] Carving system ext4 to {tmp_ext4} ...")
        run([
            "dd",
            f"if={image_path}",
            f"of={tmp_ext4}",
            f"bs={block_sz}",
            f"skip={skip_blocks}",
            f"count={count_blocks}",
            "status=none",
        ])

        with open(tmp_flag, "w", newline="") as fh:
            fh.write(flag_value)

        check_result = run(
            ["debugfs", "-R", "stat /flag.txt", tmp_ext4],
            check=False,
            capture=True,
        )
        if "File not found" not in check_result.stderr:

            print("[bake_flag] Removing existing /flag.txt from ext4...")
            run(["debugfs", "-w", "-R", "rm /flag.txt", tmp_ext4])

        cmds = f"""write {tmp_flag} /flag.txt
sif /flag.txt mode 0100600
sif /flag.txt uid 0
sif /flag.txt gid 0
"""
        with open(tmp_cmds, "w") as fh:
            fh.write(cmds)

        print("[bake_flag] Injecting /flag.txt via debugfs ...")
        run(["debugfs", "-w", "-f", tmp_cmds, tmp_ext4])

        stat_result = run(
            ["debugfs", "-R", "stat /flag.txt", tmp_ext4],
            capture=True,
        )
        stat_output = stat_result.stderr + stat_result.stdout
        if "Mode:  0600" not in stat_output or "User:     0" not in stat_output:
            die(f"Post-write stat check failed:\n{stat_output}")

        cat_result = run(
            ["debugfs", "-R", "cat /flag.txt", tmp_ext4],
            capture=True,
        )
        actual = (cat_result.stderr.replace("debugfs 1.46.5 (30-Dec-2021)", "").replace("debugfs: cat /flag.txt", "").strip())

        actual_out = cat_result.stdout.strip()
        if actual_out != flag_value.strip():
            die(f"Flag content mismatch after write.\n  Expected: {flag_value!r}\n  Got:      {actual_out!r}")

        preview = repr(actual_out[:30])
        print(f"[bake_flag] Verified: mode=0600 uid=0 gid=0 content={preview}...")
        print("[bake_flag] Stat output:")
        for line in stat_output.splitlines():
            if any(k in line for k in ("Inode:", "Type:", "Mode:", "User:", "Group:", "Size:", "Links:")):
                print(f"  {line.strip()}")

        print(f"[bake_flag] Writing modified ext4 back to image at offset {sys_abs_offset:#x} ...")
        run([
            "dd",
            f"if={tmp_ext4}",
            f"of={image_path}",
            f"bs={block_sz}",
            f"seek={skip_blocks}",
            f"count={count_blocks}",
            "conv=notrunc",
            "status=none",
        ])
        print("[bake_flag] Write-back complete.")

    finally:

        for f in [tmp_ext4, tmp_flag, tmp_cmds]:
            try:
                os.remove(f)
            except OSError:
                pass
        try:
            os.rmdir(tmpdir)
        except OSError:
            pass

    print("[bake_flag] Final verification (reading back from image)...")
    with tempfile.NamedTemporaryFile(suffix=".ext4", delete=False) as tf:
        verify_tmp = tf.name
    try:
        run([
            "dd",
            f"if={image_path}",
            f"of={verify_tmp}",
            f"bs={block_sz}",
            f"skip={skip_blocks}",
            f"count={count_blocks}",
            "status=none",
        ])
        verify_stat = run(
            ["debugfs", "-R", "stat /flag.txt", verify_tmp],
            capture=True,
        )
        verify_cat = run(
            ["debugfs", "-R", "cat /flag.txt", verify_tmp],
            capture=True,
        )
        final_content = verify_cat.stdout.strip()
        if final_content != flag_value.strip():
            die(f"Final read-back mismatch.\n  Expected: {flag_value!r}\n  Got:      {final_content!r}")
        print("[bake_flag] PROOF:")
        for line in (verify_stat.stderr + verify_stat.stdout).splitlines():
            if any(k in line for k in ("Inode:", "Type:", "Mode:", "User:", "Group:", "Size:")):
                print(f"  stat: {line.strip()}")
        print(f"  cat /flag.txt => {final_content!r}")
        print("[bake_flag] SUCCESS: /flag.txt baked, mode 0600, uid=0, gid=0.")
    finally:
        try:
            os.remove(verify_tmp)
        except OSError:
            pass

def main():
    parser = argparse.ArgumentParser(description="Offline /flag.txt injection into Android AVD system.img")
    parser.add_argument("--image", required=True, help="Path to a WRITABLE COPY of system.img")
    parser.add_argument("--flag", required=True, help="Flag value to bake in (e.g. R3CTF{...})")
    args = parser.parse_args()

    if not os.path.isfile(args.image):
        die(f"Image not found: {args.image}")
    if not os.access(args.image, os.W_OK):
        die(f"Image is not writable: {args.image}")
    if not args.flag:
        die("Flag value must not be empty")

    result = subprocess.run(["which", "debugfs"], capture_output=True)
    if result.returncode != 0:
        die("debugfs not found. Install e2fsprogs: sudo apt-get install e2fsprogs")

    bake_flag(args.image, args.flag)

if __name__ == "__main__":
    main()
