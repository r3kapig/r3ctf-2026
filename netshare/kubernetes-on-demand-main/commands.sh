kind create cluster --config kind-cluster.yaml
# kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
# patched for ssl passthrough
kubectl apply -f ingress-nginx.yaml

export CLUSTER_TOPOLOGY=true
export EXP_CLUSTER_RESOURCE_SET=true
clusterctl init --infrastructure docker
kubectl create configmap calico-addon --from-file=calico.yaml

kubectl apply -f capi-quickstart.yaml

watch clusterctl describe cluster capi-quickstart
