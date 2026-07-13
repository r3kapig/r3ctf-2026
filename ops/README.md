# Ops utilities

Helper scripts for operating the GKE cluster.

## Prerequisites

- `gcloud`
- `kubectl`
- Access to the target GKE cluster

No credentials or keys are embedded in any script; they rely on `gcloud`
authentication from the environment.

## `k8s_node_summary.py`

One-line-per-node summary of cluster resource usage: CPU/memory usage, Pod
counts, and declared requests/limits. Read-only — never writes to the cluster.

### Usage

```bash
export GCP_PROJECT=hydrogene7
export GKE_CLUSTER=r3ctf-cluster
export GKE_LOCATION=asia-east2-b

python3 ops/k8s_node_summary.py
```

Also list pods in problematic states (`Pending`, `Failed`, `CrashLoopBackOff`,
`Error`):

```bash
python3 ops/k8s_node_summary.py --check-problems
```

By default the script uses the cluster's internal control-plane endpoint
(works from a VM inside the same VPC, e.g. the ops host). For the public
endpoint:

```bash
export GKE_USE_INTERNAL_IP=false
python3 ops/k8s_node_summary.py
```

### Output columns

| Column | Meaning |
|--------|---------|
| `NODE` | Node name |
| `POOL` | GKE node pool name |
| `CPU_USE` / `CPU%` | Currently measured CPU usage |
| `MEM_USE` / `MEM%` | Currently measured memory usage |
| `PODS` | Total number of Pods on the node |
| `CHAL` | Number of challenge Pods on the node (namespace `ret2shell-challenge` by default) |
| `CPU_REQ` | Sum of Pod CPU requests and percentage of node allocatable CPU |
| `CPU_LIM` | Sum of Pod CPU limits |
| `MEM_REQ` | Sum of Pod memory requests and percentage of node allocatable memory |
| `MEM_LIM` | Sum of Pod memory limits |

## `gke_monitor.sh`

Runs `k8s_node_summary.py` on the ops host every 5 minutes (via `cron`),
prints the one-line-per-node summary, and sends a Lark alert when it detects:

- Nodes with CPU% or MEM% >= 80%
- Pods in `Pending`, `Failed`, `CrashLoopBackOff`, or `Error` states
- Node count changes
- Total Pod or challenge Pod count changes >= 50 within 5 minutes

State is kept in `/tmp/.last_gke_summary.json`.

### Usage

```bash
bash ops/gke_monitor.sh
```

Configure the Lark notification target by editing `LARK_USER_ID` inside the
script.

## Node pool migration scripts

One-shot scripts used to migrate workloads to the `n2std32-nested` pool
(nested virtualization, 256 max pods per node). Same `GCP_PROJECT` /
`GKE_CLUSTER` / `GKE_LOCATION` environment variables as above.

- `create_nested_pool.sh` — create the `n2std32-nested` pool
  (`n2-standard-32`, autoscaling), then taint old pools.
- `continue_nested_setup.sh` — wait for new nodes Ready, taint old pools
  (`n2std32-pool`, `n2std32-dense`) with `retiring=true:NoSchedule`, and allow
  old pools to scale to 0.
- `drain_old_nodes.sh` — cordon and drain the old `n2std32-pool` nodes.
