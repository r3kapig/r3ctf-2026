#!/usr/bin/env bash
# 用 vs.json 里对应端口的参数，单独拉起一台 babycom 实例。
# 用法: ./run_one.sh <ssh_port>   例: ./run_one.sh 28303
set -euo pipefail
PORT=${1:?用法: run_one.sh <ssh_port>}
DIR=$(cd "$(dirname "$0")" && pwd)
cd "$DIR"
readarray -t A < <(python3 - "$PORT" <<'PY'
import json, sys
port = int(sys.argv[1])
d = json.load(open('vs.json'))
e = next(x for x in d if x['ssh_port'] == port)
print(e['flag'])
print(e['admin_password'])
print(e['ssh_port'])
print(e['user_password'])
print(e['timeout'])
PY
)
exec python3 -u run.py \
  --ssh-port "${A[2]}" \
  --admin-password "${A[1]}" \
  --user-password "${A[3]}" \
  --flag "${A[0]}" \
  --timeout "${A[4]}"
