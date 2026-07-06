#!/bin/bash
set -e

gcloud container clusters get-credentials r3ctf-cluster --project=hydrogene7 --location=asia-east2-b --internal-ip >/dev/null 2>&1

for node in gke-r3ctf-cluster-n2std32-pool-a8c9e03e-fnd9 gke-r3ctf-cluster-n2std32-pool-a8c9e03e-x7nh; do
  echo "Draining $node ..."
  kubectl cordon "$node"
  kubectl drain "$node" --ignore-daemonsets --delete-emptydir-data --force --timeout=180s
done

echo "Done"
kubectl get nodes -o wide
