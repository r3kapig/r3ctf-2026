#!/bin/bash
# GKE cluster monitor wrapper.
# Runs k8s_node_summary.py on the ops host, checks for anomalies/changes,
# prints a one-line-per-node table, and sends a Lark notification if needed.
#
# No credentials/keys are embedded here; they come from environment/auth.

set -e

WORK_DIR=$(cd "$(dirname "$0")/.." && pwd)
STATE_FILE="/tmp/.last_gke_summary.json"
SCRIPT="$WORK_DIR/ops/k8s_node_summary.py"
REMOTE_HOST="r3kapig@ops.ctf2026.r3kapig.com"
REMOTE_SCRIPT="/tmp/k8s_node_summary.py"
LARK_USER_ID="ou_c7da9e42f0ec468c47aae13d636fe7bb"

# --- 1. sync and run the summary script on ops host (single ssh session) ---
# Use ssh here-document instead of scp; scp occasionally gets rejected by the ops host.
# Add a short delay between the two ssh connections to avoid hitting rate limits.
ssh -o BatchMode=yes "$REMOTE_HOST" "cat > $REMOTE_SCRIPT" < "$SCRIPT" >/dev/null 2>&1
sleep 3
RAW_OUTPUT=$(ssh -o BatchMode=yes "$REMOTE_HOST" \
  'sudo -i bash -c "export GCP_PROJECT=hydrogene7; export GKE_CLUSTER=r3ctf-cluster; export GKE_LOCATION=asia-east2-b; python3 /tmp/k8s_node_summary.py --check-problems"')

# --- 2. split python output into table and problems ---
OUTPUT=$(echo "$RAW_OUTPUT" | awk '/^PROBLEMS:/ {exit} {print}')
PROBLEMS=$(echo "$RAW_OUTPUT" | awk '/^PROBLEMS: [1-9]/ {flag=1} flag {sub(/^PROBLEMS: /,""); if (NF) print}')

# --- 3. parse summary ---
# Output columns: NODE POOL CPU_USE CPU% MEM_USE MEM% PODS CHAL ...
NODE_COUNT=$(echo "$OUTPUT" | tail -n +2 | grep -c '^gke-' || true)
TOTAL_PODS=$(echo "$OUTPUT" | tail -n +2 | awk '{sum+=$7} END {print sum+0}')
CHAL_PODS=$(echo "$OUTPUT" | tail -n +2 | awk '{sum+=$8} END {print sum+0}')
HIGH_USAGE_NODES=$(echo "$OUTPUT" | tail -n +2 | awk '{if ($4+0>=80 || $6+0>=80) print $1}' | paste -sd ', ' -)

POD_CHANGE_THRESHOLD=50

# --- 4. load previous state ---
PREV_NODE_COUNT=""
PREV_TOTAL_PODS=""
PREV_CHAL_PODS=""
if [ -f "$STATE_FILE" ]; then
  PREV_NODE_COUNT=$(python3 -c "import json,sys; d=json.load(open('$STATE_FILE')); print(d.get('node_count',''))")
  PREV_TOTAL_PODS=$(python3 -c "import json,sys; d=json.load(open('$STATE_FILE')); print(d.get('total_pods',''))")
  PREV_CHAL_PODS=$(python3 -c "import json,sys; d=json.load(open('$STATE_FILE')); print(d.get('challenge_pods',''))")
fi

# --- 5. decide whether to alert ---
ALERT=false
REASONS=""

if [ -n "$HIGH_USAGE_NODES" ]; then
  ALERT=true
  REASONS+="节点CPU/内存使用率超80%: $HIGH_USAGE_NODES; "
fi

if [ -n "$PROBLEMS" ]; then
  ALERT=true
  REASONS+="存在异常Pod; "
fi

if [ -n "$PREV_NODE_COUNT" ] && [ "$NODE_COUNT" != "$PREV_NODE_COUNT" ]; then
  ALERT=true
  REASONS+="节点数变化: $PREV_NODE_COUNT -> $NODE_COUNT; "
fi

if [ -n "$PREV_TOTAL_PODS" ]; then
  TOTAL_DIFF=$((TOTAL_PODS - PREV_TOTAL_PODS))
  TOTAL_DIFF_ABS=${TOTAL_DIFF#-}
  if [ "$TOTAL_DIFF_ABS" -ge "$POD_CHANGE_THRESHOLD" ]; then
    ALERT=true
    REASONS+="总 Pod 数 5 分钟内变化超过 $POD_CHANGE_THRESHOLD: $PREV_TOTAL_PODS -> $TOTAL_PODS (差值 $TOTAL_DIFF); "
  fi
fi

if [ -n "$PREV_CHAL_PODS" ]; then
  CHAL_DIFF=$((CHAL_PODS - PREV_CHAL_PODS))
  CHAL_DIFF_ABS=${CHAL_DIFF#-}
  if [ "$CHAL_DIFF_ABS" -ge "$POD_CHANGE_THRESHOLD" ]; then
    ALERT=true
    REASONS+="challenge pods 5 分钟内变化超过 $POD_CHANGE_THRESHOLD: $PREV_CHAL_PODS -> $CHAL_PODS (差值 $CHAL_DIFF); "
  fi
fi

# --- 6. save current state ---
python3 -c "
import json, datetime
with open('$STATE_FILE', 'w') as f:
    json.dump({
        'timestamp': datetime.datetime.now().isoformat(),
        'node_count': $NODE_COUNT,
        'total_pods': $TOTAL_PODS,
        'challenge_pods': $CHAL_PODS
    }, f)
"

# --- 7. output ---
echo "$OUTPUT"

if [ "$ALERT" = true ]; then
  echo "⚠️ 异常/变更: $REASONS"

  # Build a concise summary message for Lark
  SUMMARY="GKE 监控告警"
  if [ -n "$HIGH_USAGE_NODES" ]; then
    SUMMARY+="，节点 $HIGH_USAGE_NODES 资源使用率超 80%"
  fi
  if [ -n "$PROBLEMS" ]; then
    SUMMARY+="，存在异常 Pod"
  fi
  if [ -n "$PREV_NODE_COUNT" ] && [ "$NODE_COUNT" != "$PREV_NODE_COUNT" ]; then
    SUMMARY+="，节点数从 $PREV_NODE_COUNT 变为 $NODE_COUNT"
  fi
  if [ -n "$PREV_TOTAL_PODS" ]; then
    TOTAL_DIFF=$((TOTAL_PODS - PREV_TOTAL_PODS))
    TOTAL_DIFF_ABS=${TOTAL_DIFF#-}
    if [ "$TOTAL_DIFF_ABS" -ge "$POD_CHANGE_THRESHOLD" ]; then
      SUMMARY+="，总 Pod 数从 $PREV_TOTAL_PODS 变为 $TOTAL_PODS（$TOTAL_DIFF）"
    fi
  fi
  if [ -n "$PREV_CHAL_PODS" ]; then
    CHAL_DIFF=$((CHAL_PODS - PREV_CHAL_PODS))
    CHAL_DIFF_ABS=${CHAL_DIFF#-}
    if [ "$CHAL_DIFF_ABS" -ge "$POD_CHANGE_THRESHOLD" ]; then
      SUMMARY+="，challenge pods 从 $PREV_CHAL_PODS 变为 $CHAL_PODS（$CHAL_DIFF）"
    fi
  fi
  SUMMARY+="，当前 $NODE_COUNT 个节点、$TOTAL_PODS 个 Pod、$CHAL_PODS 个 challenge pods。"

  MSG=$(printf "%s\n详情：%s" "$SUMMARY" "$REASONS")
  lark-cli im +messages-send --user-id "$LARK_USER_ID" --text "$MSG" --as bot >/dev/null 2>&1 || true
  echo "已发送飞书通知"
else
  echo "状态正常"
fi
