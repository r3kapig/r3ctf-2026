# Kubernetes on Demand (KOND)

## Setup
* Needs docker
* Build the controller container `docker build -t kube-controller controller`
* Create network with name `kind`: `docker network create kind`
* Run with docker compose: `docker compose up --build`

* Mount`challenge.yaml` and `user.yaml` in `docker-compose.yaml`
* `user.yaml` must create service account with name `ctf-player`, token is automatically created and send to the player

* *INFO*: On some systems the inotify limits are to small, adjust with:
    ```
    sysctl fs.inotify.max_user_instances=8192
    sysctl fs.inotify.max_user_watches=1048576
    ```

## Player access

`PUBLIC_HOST` in `.env` must be an address assigned to the Docker host and
reachable from the player machine. Check it with `hostname -I`; a typo here
produces a kubeconfig whose API server always times out.

The generated certificate is self-signed. When using the returned token
directly instead of the generated kubeconfig, include the HTTPS scheme, skip
certificate verification, and select the challenge namespace:

```
kubectl \
  --server=https://192.168.31.253:<generated-port> \
  --token='<generated-token>' \
  --insecure-skip-tls-verify \
  get pods -n ctf-ghost
```

The `ctf-player` account cannot list pods in the `default` namespace. A plain
`get pods` therefore returns `Forbidden`; this is expected RBAC behavior.

## Domain setup
For testing the domain `domain.local` will be used for cluster access.
A self signed certificate is provided and will be added to the kubeconfig.
To use this setup the DNS server needs to resolve this domain to localhost.
```
sudo dnsmasq -d -A /domain.local/10.1.8.3 -2 lo
```

For public access a private key and fullchain certificate (wildcard) for the domain are required.
These must be mounted in the `docker-compose.yaml`.

## Resources
* [Kind](https://kind.sigs.k8s.io/docs/user/quick-start#installation)
* [ClusterAPI](https://cluster-api.sigs.k8s.io/introduction)
* [ClusterAPI Resource Specs](https://doc.crds.dev/github.com/kubernetes-sigs/cluster-api@v1.4.5)

## Load Debugging
Patches to increase rate limits and concurrency:
```
kubectl patch deployment -n capi-system capi-controller-manager --type "json" -p'[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kube-api-qps=50"},{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kube-api-burst=100"},{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--cluster-concurrency=50"}]'

kubectl patch deployment -n capd-system capd-controller-manager --type "json" -p'[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kube-api-qps=50"},{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kube-api-burst=100"},{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--concurrency=50"}]'

kubectl patch deployment -n capi-kubeadm-bootstrap-system capi-kubeadm-bootstrap-controller-manager --type "json" -p'[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kube-api-qps=50"},{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kube-api-burst=100"},{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--cluster-concurrency=50"}]'

kubectl patch deployment -n capi-kubeadm-control-plane-system capi-kubeadm-control-plane-controller-manager --type "json" -p'[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kube-api-qps=50"},{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kube-api-burst=100"},{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubeadmcontrolplane-concurrency=50"}]'
```

Other options for capi-controller-manager
```
--cluster-concurrency int                       Number of clusters to process simultaneously (default 10)
      --clusterclass-concurrency int                  Number of ClusterClasses to process simultaneously (default 10)
      --clusterresourceset-concurrency int            Number of cluster resource sets to process simultaneously (default 10)
      --clustertopology-concurrency int               Number of clusters to process simultaneously (default 10)
--machine-concurrency int                       Number of machines to process simultaneously (default 10)
      --machinedeployment-concurrency int             Number of machine deployments to process simultaneously (default 10)
      --machinehealthcheck-concurrency int            Number of machine health checks to process simultaneously (default 10)
      --machinepool-concurrency int                   Number of machine pools to process simultaneously (default 10)
      --machineset-concurrency int                    Number of machine sets to process simultaneously (default 10)
```
