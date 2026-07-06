#!/bin/bash
# Create a new GKE node pool with nested virtualization + 256 max pods,
# then taint old pools so workloads migrate to the new pool.

set -e

: "${GCP_PROJECT:?set GCP_PROJECT}"
: "${GKE_CLUSTER:?set GKE_CLUSTER}"
: "${GKE_LOCATION:?set GKE_LOCATION}"

NEW_POOL="n2std32-nested"
MACHINE_TYPE="n2-standard-32"

gcloud container clusters get-credentials "$GKE_CLUSTER" \
  --project="$GCP_PROJECT" \
  --location="$GKE_LOCATION" \
  --internal-ip >/dev/null 2>&1

echo "=== Step 1: create $NEW_POOL with nested virtualization and 256 max pods ==="
gcloud container node-pools create "$NEW_POOL" \
  --cluster="$GKE_CLUSTER" \
  --location="$GKE_LOCATION" \
  --project="$GCP_PROJECT" \
  --machine-type="$MACHINE_TYPE" \
  --disk-size=100 \
  --disk-type=pd-balanced \
  --max-pods-per-node=256 \
  --enable-nested-virtualization \
  --num-nodes=1 \
  --enable-autoscaling \
  --min-nodes=1 \
  --max-nodes=6 \
  --quiet

echo ""
echo "=== Step 2: wait for new nodes Ready ==="
kubectl wait --for=condition=Ready node \
  -l "cloud.google.com/gke-nodepool=$NEW_POOL" \
  --timeout=300s

echo ""
echo "=== Step 3: taint old pool nodes (n2std32-pool and n2std32-dense) ==="
for pool in n2std32-pool n2std32-dense; do
  if kubectl get nodes -l "cloud.google.com/gke-nodepool=$pool" >/dev/null 2>&1; then
    echo "Tainting $pool ..."
    kubectl taint nodes -l "cloud.google.com/gke-nodepool=$pool" \
      retiring=true:NoSchedule --overwrite
  fi
done

echo ""
echo "=== Step 4: allow old pools to scale to 0 ==="
for pool in n2std32-pool n2std32-dense; do
  if gcloud container node-pools describe "$pool" --cluster="$GKE_CLUSTER" --location="$GKE_LOCATION" --project="$GCP_PROJECT" >/dev/null 2>&1; then
    echo "Updating $pool autoscaling ..."
    gcloud container node-pools update "$pool" \
      --cluster="$GKE_CLUSTER" \
      --location="$GKE_LOCATION" \
      --project="$GCP_PROJECT" \
      --enable-autoscaling \
      --min-nodes=0 \
      --max-nodes=6 \
      --quiet
  fi
done

echo ""
echo "=== Step 5: remove scale-down-disabled from old nodes ==="
for node in $(kubectl get nodes -l 'retiring=true' -o jsonpath='{.items[*].metadata.name}' 2>/dev/null || true); do
  if [ -n "$node" ]; then
    kubectl annotate node "$node" cluster-autoscaler.kubernetes.io/scale-down-disabled- --overwrite 2>/dev/null || true
  fi
done

echo ""
echo "=== Step 6: protect one new node from scale-down ==="
NEW_NODE=$(kubectl get nodes -l "cloud.google.com/gke-nodepool=$NEW_POOL" -o jsonpath='{.items[0].metadata.name}')
kubectl annotate node "$NEW_NODE" cluster-autoscaler.kubernetes.io/scale-down-disabled=true --overwrite

echo ""
echo "=== Done. Current nodes ==="
kubectl get nodes -o wide
