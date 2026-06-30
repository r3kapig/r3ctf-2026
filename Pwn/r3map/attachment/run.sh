#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="."

KERNEL_IMAGE="$ROOT_DIR/bzImage"
INITRAMFS="$ROOT_DIR/initramfs.cpio.gz"
FLAG_SHARE_DIR="$ROOT_DIR/runtime/flagfs"
FLAG_FILE="$ROOT_DIR/flag.txt"
FLAG_VALUE="${FLAG:-}"
APPEND="console=ttyS0 init=/init quiet loglevel=3 oops=panic panic_on_warn=1 panic=1 pti=on kaslr"

require_file() {
	local path="$1"

	if [[ ! -f "$path" ]]; then
		echo "[-] missing file: $path" >&2
		exit 1
	fi
}

require_file "$KERNEL_IMAGE"
require_file "$INITRAMFS"

if [[ -z "$FLAG_VALUE" && ! -f "$FLAG_FILE" && ! -f "$FLAG_SHARE_DIR/flag" ]]; then
	echo "[-] missing flag source: set FLAG or create $FLAG_FILE" >&2
	exit 1
fi

if [[ ! -c /dev/kvm ]]; then
	echo "[-] /dev/kvm is required" >&2
	exit 1
fi

mkdir -p "$FLAG_SHARE_DIR"
if [[ -n "$FLAG_VALUE" ]]; then
	rm -f "$FLAG_SHARE_DIR/flag"
	printf '%s\n' "$FLAG_VALUE" >"$FLAG_SHARE_DIR/flag"
	chmod 0400 "$FLAG_SHARE_DIR/flag"
elif [[ -f "$FLAG_FILE" ]]; then
	rm -f "$FLAG_SHARE_DIR/flag"
	install -m 0400 "$FLAG_FILE" "$FLAG_SHARE_DIR/flag"
fi

QEMU_ARGS=(
	-m 2048
	-smp 4
	-kernel "$KERNEL_IMAGE"
	-initrd "$INITRAMFS"
	-virtfs "local,path=$FLAG_SHARE_DIR,mount_tag=r3flag,security_model=none,readonly=on"
	-nographic
	-append "$APPEND"
	-monitor none
	-nic user,model=e1000
	-enable-kvm
	-cpu host,+smep,+smap
	-no-reboot
)

exec qemu-system-x86_64 "${QEMU_ARGS[@]}"
