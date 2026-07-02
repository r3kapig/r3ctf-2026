#!/bin/sh

set -e

cleanup() {
    echo "[+] Deleting kind cluster"
    kind delete cluster --name clusterapi-on-demand
}

# A previous container can be removed before its EXIT trap reaches Docker,
# leaving the Kind node behind. Starting again would otherwise fail with
# "node(s) already exist" and leave the compose service stopped.
if kind get clusters 2>/dev/null | grep -qx "clusterapi-on-demand"; then
    echo "[+] Removing stale kind cluster"
    kind delete cluster --name clusterapi-on-demand
fi

echo "[+] Creating kind cluster"
kind create cluster --config kind-cluster.yaml --name clusterapi-on-demand
trap cleanup TERM INT EXIT

# kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
# patched for ssl passthrough
echo "[+] Applying nginx deployment"
kubectl apply -f ingress-nginx.yaml

echo "[+] Loading controller image"
if ! docker image inspect kube-controller:latest >/dev/null 2>&1; then
    echo "[-] Missing kube-controller:latest image"
    echo "[-] Build it before starting compose:"
    echo "    docker build -t kube-controller:latest controller"
    exit 1
fi
kind load docker-image kube-controller:latest --name clusterapi-on-demand

kubectl create configmap app-domain --from-literal=domain="$APP_DOMAIN"
# Surface compose-level controller knobs (challenge customisation) as a
# ConfigMap consumed by resources/controller.yaml.
kubectl create configmap controller-config \
    --from-literal=skip-token-verify="${SKIP_TOKEN_VERIFY:-false}" \
    --from-literal=public-host="${PUBLIC_HOST:-127.0.0.1}"
kubectl create secret tls domain-cert --key tls.key --cert tls.crt

while [ "$(kubectl -n ingress-nginx get pods -l 'app.kubernetes.io/component=controller' -o 'jsonpath={..status.conditions[?(@.type=="Ready")].status}')" != "True" ]; do
    echo "[.] Waiting for ingress nginx";
    sleep 1;
done

echo "[+] Install Monitoring"
# headlamp.yaml contains an Ingress, which triggers the nginx admission webhook
# (validate.nginx.ingress.kubernetes.io). A Ready ingress-nginx controller Pod
# does NOT guarantee the admission Service (:443) already has endpoints / its CA
# bundle is injected, so applying immediately can fail with "connection refused"
# — and `set -e` + the EXIT trap would then tear the whole cluster down. Retry
# until the webhook is actually serving instead of dying on that race.
for attempt in $(seq 1 30); do
    if kubectl apply -f headlamp.yaml; then
        echo "[+] headlamp.yaml applied (attempt ${attempt})"
        break
    fi
    echo "[.] headlamp.yaml apply failed (attempt ${attempt}), ingress webhook not ready yet; retrying in 3s";
    sleep 3;
done
# metrics-server is fetched from GitHub (flaky through a proxy) and is only used
# by the dashboard, not the challenge — retry a few times but never let a
# transient fetch error abort the whole setup via `set -e`.
for attempt in $(seq 1 5); do
    if kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml; then
        break
    fi
    echo "[.] metrics-server apply failed (attempt ${attempt}); retrying in 3s";
    sleep 3;
done
sleep 3;
kubectl patch -n kube-system deployment metrics-server --type=json -p '[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]' || true
echo "\n\n[+] Get yourself a Headlamp Access token!!!\n"
echo "docker-compose exec kubernetes kubectl create token headlamp\n\n"

echo "[+] Applying controller deployment"
kubectl apply -f controller.yaml

echo "[+] Creating Cluster API resources"
export CLUSTERCTL_DISABLE_VERSIONCHECK=true
export CLUSTER_TOPOLOGY=true
export EXP_CLUSTER_RESOURCE_SET=true
clusterctl init --config clusterctl.yaml --infrastructure docker
echo "[+] Creating calico configmap"
kubectl create configmap calico-addon --from-file=calico.yaml
echo "[+] Creating challenge configmaps"
kubectl create configmap challenge --from-file=challenge.yaml
kubectl create configmap user --from-file=user.yaml

while [ "$(kubectl -n capi-system get pods -o 'jsonpath={..status.conditions[?(@.type=="Ready")].status}')" != "True" ]; do
    echo "[.] Waiting for Core Cluster API";
    sleep 1;
done

while [ "$(kubectl -n capd-system get pods -o 'jsonpath={..status.conditions[?(@.type=="Ready")].status}')" != "True" ]; do
    echo "[.] Waiting for Cluster API Provider Docker";
    sleep 1;
done

while [ "$(kubectl -n capi-kubeadm-bootstrap-system get pods -o 'jsonpath={..status.conditions[?(@.type=="Ready")].status}')" != "True" ]; do
    echo "[.] Waiting for Webhook services";
    sleep 1;
done

# A Ready CAPD controller Pod does NOT guarantee its admission webhook is
# already serving: the webhook server (:9443) and the cert-manager-injected
# CA bundle can lag a few seconds behind pod-Ready. Applying cluster.yaml in
# that gap fails with "capd-webhook-service ... connect: connection refused".
# Wait until the webhook Service actually has a ready endpoint.
echo "[.] Waiting for CAPD webhook endpoints"
while [ -z "$(kubectl -n capd-system get endpoints capd-webhook-service -o 'jsonpath={.subsets[*].addresses[*].ip}' 2>/dev/null)" ]; do
    echo "[.] Waiting for capd-webhook-service endpoints";
    sleep 2;
done

# Even with an endpoint present, the TLS handshake / CA injection may need a
# couple more seconds. Retry the apply instead of letting `set -e` + the EXIT
# trap tear the whole management cluster down on a transient webhook error.
echo "[+] Applying cluster definition"
for attempt in $(seq 1 30); do
    if kubectl apply -f cluster.yaml; then
        echo "[+] cluster.yaml applied (attempt ${attempt})"
        break
    fi
    echo "[.] cluster.yaml apply failed (attempt ${attempt}), webhook not ready yet; retrying in 5s";
    sleep 5;
done

echo "[+] Cluster API is ready"

while true; do
    sleep 5;
done
