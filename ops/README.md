# Ops utilities

Small helper scripts used to operate the CTF infrastructure.

## `k8s_node_summary.py`

One-line-per-node summary of GKE cluster resource usage: CPU / memory usage,
Pod counts, and declared requests / limits.

### Requirements

- `gcloud`
- `kubectl`
- Access to the target GKE cluster

### Usage

Set the target cluster via environment variables:

```bash
export GCP_PROJECT=hydrogene7
export GKE_CLUSTER=r3ctf-cluster
export GKE_LOCATION=asia-east2-b

python3 ops/k8s_node_summary.py
```

To also list pods in problematic states (`Pending`, `Failed`, `CrashLoopBackOff`,
`Error`):

```bash
python3 ops/k8s_node_summary.py --check-problems
```

By default the script uses the cluster's internal control-plane endpoint, which
works from a VM inside the same VPC (e.g. the ops host). To use the public
endpoint instead:

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

### Notes

- No credentials or keys are embedded in the script. It relies on `gcloud`
  authentication from the environment.
- The script does not write anything to the cluster; it is read-only.

## `gke_monitor.sh`

Wrapper that runs `k8s_node_summary.py` on the ops host every 5 minutes (via
`cron`), prints a one-line-per-node summary, and sends a Lark alert when it
detects:

- Nodes with CPU% or MEM% >= 80%
- Pods in `Pending`, `Failed`, `CrashLoopBackOff`, or `Error` states
- Node count changes
- Total Pod or challenge Pod count changes >= 50 within 5 minutes

The migration check for the old `n2std32-pool` node pool has been removed since
that pool no longer exists.

State is kept in `/tmp/.last_gke_summary.json` so the project directory is not
polluted.

### Usage

```bash
bash ops/gke_monitor.sh
```

Configure the target user for Lark notifications by editing `LARK_USER_ID`
inside the script.
