#!/usr/bin/env python3
"""Patch the upstream calico.yaml in place so the default IP pool is small
enough for the Ghost-in-the-Chain CTF challenge.

Upstream's calico-node DaemonSet ships with `CALICO_IPV4POOL_CIDR` commented
out (it defaults to 192.168.0.0/16 inside the binary). We need:

  1. CALICO_IPV4POOL_CIDR        = 10.244.1.0/28  (force a /28 pool)
  2. CALICO_IPV4POOL_BLOCK_SIZE  = 28             (default 26 wouldn't fit)
  3. CALICO_IPV4POOL_IPIP        = Never          (avoid burning an IP on the
                                                   tunnel device — every IP
                                                   counts in a /28)

We do this with line-by-line textual edits so the build does not depend on
PyYAML (kept stdlib-only). The script aborts loudly if the upstream layout
ever changes, so the image build will fail fast rather than silently leave
Calico misconfigured.
"""
import sys

if len(sys.argv) != 2:
    print("usage: patch-calico.py <calico.yaml>", file=sys.stderr)
    sys.exit(1)

path = sys.argv[1]
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

# 1. The CIDR env block is commented out; replace the two-line comment with
#    a real env var entry. Match the exact upstream wording so we fail loudly
#    if the manifest layout shifts.
needle = (
    "            # - name: CALICO_IPV4POOL_CIDR\n"
    "            #   value: \"192.168.0.0/16\"\n"
)
replacement = (
    # Pool matches the CAPI cluster's pod CIDR. Block size 28 means Calico
    # subdivides the /22 pool into /28 blocks (14 usable IPs each) and
    # assigns one to each node. With only one schedulable worker per cluster,
    # this gives the cluster a single /28 block to fight over — which is
    # exactly the collision domain the race condition challenge needs.
    "            - name: CALICO_IPV4POOL_CIDR\n"
    "              value: \"10.244.0.0/22\"\n"
    "            - name: CALICO_IPV4POOL_BLOCK_SIZE\n"
    "              value: \"28\"\n"
)
if needle not in src:
    print("patch-calico.py: CALICO_IPV4POOL_CIDR comment block not found", file=sys.stderr)
    sys.exit(2)
src = src.replace(needle, replacement, 1)

# 2. Disable IPIP so Calico does not consume a Pod IP for the tunnel
#    endpoint. With a /28 cluster pool every address is precious; we'd
#    rather have plain routed pods on a single worker.
ipip_needle = (
    "            - name: CALICO_IPV4POOL_IPIP\n"
    "              value: \"Always\"\n"
)
ipip_replace = (
    "            - name: CALICO_IPV4POOL_IPIP\n"
    "              value: \"Never\"\n"
)
if ipip_needle not in src:
    print("patch-calico.py: CALICO_IPV4POOL_IPIP=Always not found", file=sys.stderr)
    sys.exit(3)
src = src.replace(ipip_needle, ipip_replace, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(src)

print("patched calico.yaml: pool=10.244.0.0/22 block_size=28 ipip=Never")
