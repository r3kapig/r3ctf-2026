#!/usr/bin/env python3
"""Print a one-line-per-node summary of GKE cluster resource usage.

Requires kubectl + gcloud on PATH and permission to access the cluster.
Configure the target cluster via environment variables:

    export GCP_PROJECT=my-project
    export GKE_CLUSTER=my-cluster
    export GKE_LOCATION=asia-east2-b

By default this uses the cluster's internal control-plane endpoint, which works
from a VM inside the same VPC (e.g. the ops host). To use the public endpoint
instead:

    export GKE_USE_INTERNAL_IP=false
"""

import argparse
import json
import os
import re
import subprocess
import sys
from collections import defaultdict


def get_env(name, default=None):
    return os.environ.get(name, default)


def require_env(name):
    val = os.environ.get(name)
    if not val:
        print(f"Error: environment variable {name} is not set.", file=sys.stderr)
        sys.exit(1)
    return val


def run(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Command failed: {cmd}\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    return result.stdout


def parse_cpu(s):
    if s is None:
        return 0
    s = str(s)
    if s.endswith("m"):
        return int(s[:-1])
    return int(float(s) * 1000)


def parse_mem(s):
    if s is None:
        return 0
    s = str(s)
    units = {
        "Ki": 1024,
        "Mi": 1024 ** 2,
        "Gi": 1024 ** 3,
        "Ti": 1024 ** 4,
        "K": 1000,
        "M": 1000 ** 2,
        "G": 1000 ** 3,
        "T": 1000 ** 4,
    }
    m = re.match(r"([\d.]+)([A-Za-z]+)", s)
    if m:
        return int(float(m.group(1)) * units.get(m.group(2), 1))
    return int(s)


def fmt_mem(b):
    if b >= 1024 ** 3:
        return f"{b / 1024 ** 3:.1f}Gi"
    if b >= 1024 ** 2:
        return f"{b / 1024 ** 2:.0f}Mi"
    return f"{b}"


def setup_kubeconfig(project, cluster, location):
    internal_flag = "--internal-ip"
    if get_env("GKE_USE_INTERNAL_IP", "true").lower() in ("false", "0", "no"):
        internal_flag = ""
    cmd = (
        f"gcloud container clusters get-credentials {cluster} "
        f"--project={project} --location={location} {internal_flag}"
    )
    run(cmd)


PROBLEMATIC_STATUSES = {"Pending", "Failed", "CrashLoopBackOff", "Error"}


def check_problem_pods(pods_json):
    problems = []
    for pod in pods_json.get("items", []):
        status = pod.get("status", {})
        phase = status.get("phase", "")
        ns = pod.get("metadata", {}).get("namespace", "")
        name = pod.get("metadata", {}).get("name", "")
        if phase == "Pending":
            problems.append((ns, name, phase))
            continue
        for cs in status.get("containerStatuses", []):
            st = cs.get("state", {})
            if "waiting" in st:
                reason = st["waiting"].get("reason", "")
                if reason in PROBLEMATIC_STATUSES:
                    problems.append((ns, name, reason))
            if "terminated" in st:
                reason = st["terminated"].get("reason", "")
                if reason in PROBLEMATIC_STATUSES:
                    problems.append((ns, name, reason))
    return problems


def main():
    parser = argparse.ArgumentParser(description="GKE cluster node summary")
    parser.add_argument(
        "--check-problems",
        action="store_true",
        help="Also list pods that are Pending/Failed/CrashLoopBackOff/Error",
    )
    args = parser.parse_args()

    project = require_env("GCP_PROJECT")
    cluster = require_env("GKE_CLUSTER")
    location = require_env("GKE_LOCATION")
    challenge_ns = get_env("CHALLENGE_NAMESPACE", "ret2shell-challenge")

    setup_kubeconfig(project, cluster, location)

    nodes_json = json.loads(run("kubectl get nodes -o json"))
    pods_json = json.loads(run("kubectl get pods --all-namespaces -o json"))
    metrics_raw = run("kubectl top nodes --no-headers").strip()

    node_metrics = {}
    for line in metrics_raw.splitlines():
        parts = line.split()
        if len(parts) >= 5:
            node_metrics[parts[0]] = (parts[1], parts[2], parts[3], parts[4])

    node_alloc = {}
    node_pool = {}
    for n in nodes_json.get("items", []):
        name = n["metadata"]["name"]
        alloc = n.get("status", {}).get("allocatable", {})
        node_alloc[name] = (parse_cpu(alloc.get("cpu", "0")), parse_mem(alloc.get("memory", "0")))
        node_pool[name] = n.get("metadata", {}).get("labels", {}).get("cloud.google.com/gke-nodepool", "unknown")

    counts = defaultdict(
        lambda: {
            "total": 0,
            "challenge": 0,
            "cpu_req": 0,
            "cpu_lim": 0,
            "mem_req": 0,
            "mem_lim": 0,
        }
    )
    for pod in pods_json.get("items", []):
        node = pod.get("spec", {}).get("nodeName", "")
        ns = pod.get("metadata", {}).get("namespace", "")
        if not node:
            continue
        counts[node]["total"] += 1
        if ns == challenge_ns:
            counts[node]["challenge"] += 1
        for c in pod.get("spec", {}).get("containers", []):
            res = c.get("resources", {})
            req = res.get("requests", {})
            lim = res.get("limits", {})
            counts[node]["cpu_req"] += parse_cpu(req.get("cpu"))
            counts[node]["cpu_lim"] += parse_cpu(lim.get("cpu"))
            counts[node]["mem_req"] += parse_mem(req.get("memory"))
            counts[node]["mem_lim"] += parse_mem(lim.get("memory"))

    header = (
        f"{'NODE':<60} {'POOL':<18} {'CPU_USE':<10} {'CPU%':<6} {'MEM_USE':<10} {'MEM%':<6} "
        f"{'PODS':<6} {'CHAL':<6} {'CPU_REQ':<15} {'CPU_LIM':<10} "
        f"{'MEM_REQ':<15} {'MEM_LIM':<10}"
    )
    print(header)

    for name in sorted(node_alloc.keys()):
        alloc_cpu, alloc_mem = node_alloc[name]
        pool = node_pool.get(name, "unknown")
        m = node_metrics.get(name, ("-", "-", "-", "-"))
        c = counts.get(
            name,
            {
                "total": 0,
                "challenge": 0,
                "cpu_req": 0,
                "cpu_lim": 0,
                "mem_req": 0,
                "mem_lim": 0,
            },
        )
        cpu_req_pct = c["cpu_req"] / alloc_cpu * 100 if alloc_cpu else 0
        mem_req_pct = c["mem_req"] / alloc_mem * 100 if alloc_mem else 0
        print(
            f"{name:<60} {pool:<18} {m[0]:<10} {m[1]:<6} {m[2]:<10} {m[3]:<6} "
            f"{c['total']:<6} {c['challenge']:<6} "
            f"{int(c['cpu_req'])}m ({cpu_req_pct:.0f}%)".ljust(15)
            + f"{int(c['cpu_lim'])}m".ljust(10)
            + f"{fmt_mem(c['mem_req'])} ({mem_req_pct:.0f}%)".ljust(15)
            + f"{fmt_mem(c['mem_lim'])}".ljust(10)
        )

    if args.check_problems:
        problems = check_problem_pods(pods_json)
        if problems:
            print(f"PROBLEMS: {len(problems)}")
            for ns, name, reason in problems:
                print(f"  {ns}/{name}: {reason}")
        else:
            print("PROBLEMS: 0")


if __name__ == "__main__":
    main()
