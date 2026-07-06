#!/bin/bash
set -e

NEW_POOL="n2std32-nested"

gcloud container clusters get-credentials r3ctf-cluster --project=hydrogene7 --location=asia-east2-b --internal-ip >/dev/null 2>&1

echo "=== Step 2: wait for new nodes Ready ==="
kubectl wait --for=condition=Ready node -l "cloud.google.com/gke-nodepool=$NEW_POOL" --timeout=300s

echo ""
echo "=== Step 3: taint old pool nodes (n2std32-pool and n2std32-dense) ==="
for pool in n2std32-pool n2std32-dense; do
  if kubectl get nodes -l "cloud.google.com/gke-nodepool=$pool" >/dev/null 2>&1; then
    echo "Tainting $pool ..."
    kubectl taint nodes -l "cloud.google.com/gke-nodepool=$pool" retiring=true:NoSchedule --overwrite
  fi
done

echo ""
echo "=== Step 4: allow old pools to scale to 0 ==="
for pool in n2std32-pool n2std32-dense; do
  if gcloud container node-pools describe "$pool" --cluster=r3ctf-cluster --location=asia-east2-b --project=hydrogene7 >/dev/null 2>&1; then
    echo "Updating $pool autoscaling ..."
    gcloud container node-pools update "$pool" \
      --cluster=r3ctf-cluster \
      --location=asia-east2-b \
      --project=hydrogene7 \
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
