#!/usr/bin/env bash
# 用 wk.json 里对应端口的参数，单独拉起一台 someday 实例。
# 用法: ./run_one.sh <ssh_port>   例: ./run_one.sh 28403
set -euo pipefail
PORT=${1:?用法: run_one.sh <ssh_port>}
DIR=$(cd "$(dirname "$0")" && pwd)
cd "$DIR"
readarray -t A < <(python3 - "$PORT" <<'PY'
import json, sys
port = int(sys.argv[1])
d = json.load(open('wk.json'))
e = next(x for x in d if x['ssh_port'] == port)
print(e['flag'])
print(e['admin_password'])
print(e['ssh_port'])
print(e['timeout'])
PY
)
exec python3 -u run.py \
  --ssh-port "${A[2]}" \
  --admin-password "${A[1]}" \
  --flag "${A[0]}" \
  --timeout "${A[3]}"
