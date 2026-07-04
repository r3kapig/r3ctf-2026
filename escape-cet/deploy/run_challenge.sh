#!/usr/bin/env bash
set -euo pipefail

uid=$(id -u)
lock=/tmp/tcet_launch.lock

kill_matching_processes() {
    local sig=$1
    local self=$$
    local pid cmd puid

    for stat in /proc/[0-9]*/stat; do
        pid=${stat#/proc/}
        pid=${pid%/stat}
        [[ "$pid" == "$self" ]] && continue
        [[ -r "/proc/$pid/status" && -r "/proc/$pid/cmdline" ]] || continue

        puid=$(awk '/^Uid:/ {print $2; exit}' "/proc/$pid/status" 2>/dev/null || true)
        [[ "$puid" == "$uid" ]] || continue

        cmd=$({ tr '\0' ' ' < "/proc/$pid/cmdline"; } 2>/dev/null || true)
        case "$cmd" in
            *"/home/ctf/challenge/tcet"*|*"/home/ctf/environment/"*"sde"*"tcet"*|*"/home/ctf/environment/"*"pin"*"tcet"*)
                kill "-$sig" "$pid" 2>/dev/null || true
                ;;
        esac
    done
}

cleanup_old_instances() {
    kill_matching_processes KILL
}

(
    flock -x 9
    cleanup_old_instances
) 9>"$lock"

cd /home/ctf
export SDE=/home/ctf/environment/sde-external-10.8.0-2026-03-15-lin/sde64
exec "$SDE" -tgl -cet 1 -cet-endbr-exe 1 -cet_output_file /dev/stderr -- /home/ctf/challenge/tcet \
    2> >(
        while IFS= read -r line; do
            case "$line" in
                "Using old Linux kernel interface") ;;
                *"sde"*|*"SDE"*) ;;
                *"IMG:"*) ;;
                *"[PIND]:"*) ;;
                *"eof"*) ;;
                *) printf '%s\n' "$line" >&2 ;;
            esac
        done
    )
