# NetShare

- **Category:** Misc
- **Author:** christa
- **Difficulty:** Medium
- **Wave:** 2
- **Points:** 
- **Solves:** 

## Description

Daniel built GhostByte's authentication system himself, reviewed every line, and signed off without hesitation. As far as he was concerned, it was airtight — a problem already solved, and one he was completely certain he would never have to think about again.

NetShare is a Kubernetes CTF challenge about stale EndpointSlice data and Pod IP reuse. It is delivered on demand via the **ret.sh** platform: each team gets a bridge pod that talks over `nc` to a KOND controller, which spins up a dedicated CAPI workload cluster for the team, generates a per-team flag from the team id, and returns a kubeconfig for a low-privilege `runtime-operator` identity. Players use that kubeconfig in their own cluster to complete the exploitation.

- Connect: `nc vm.ctf2026.r3kapig.com 28888`
- Flag format: `sk-<uuid>` (no braces)

If you think your exploit should be working but you're not getting the flag, please open a ticket.

## Files

- `kubernetes-on-demand-main/` — KOND controller: started with `docker compose`, `nc` listener on :8888; each connection creates a CAPI workload cluster and automatically applies `challenge.yaml` / `user.yaml` (cluster templates in `resources/`).
- `ctf-challenge/challenge.yaml` — challenge body: namespace, victim service `profile-query`, the stale EndpointSlice controller, policies and platform workers.
- `ctf-challenge/user.yaml` — player low-privilege identity `runtime-operator` and its RBAC.
- `ret2shell-ext-controller-pod/` — ret.sh instance bridge pod image source: `app.py` (nc bridge serving the kubeconfig on :5000), `pod.yaml` (instance manifest), `checker.rx` (flag checker), `Dockerfile`. Image: `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/netshare:latest`.
- `infra.sh` — notes/echo script documenting the build + controller run commands.

## Deployment

On-demand ret.sh environment; there is no single long-lived instance. Flow:

```text
player clicks "create"
  → ret.sh starts a bridge pod (injects RET2SHELL_TEAM_ID + CONTROLLER_HOST + CONTROLLER_PORT)
  → bridge pod connects to the controller via nc and sends the team id
  → controller creates a dedicated workload cluster, generates the sk-<uuid> flag
     from the team id and injects it into the service assertion
  → controller returns the runtime-operator kubeconfig
  → bridge pod shows the kubeconfig on a :5000 web page
  → player uses that kubeconfig to exploit in their own cluster
stopping the instance → bridge pod exits → nc disconnects → controller destroys the cluster
```

Deployment steps:

1. Start the controller:

```sh
cd kubernetes-on-demand-main
PUBLIC_HOST=<controller host IP reachable by players> \
FLAG_SALT=<salt matching the platform> FLAG_CHAL_ID=<challenge id matching the platform> \
docker compose up -d
```

The controller listens for `nc` on :8888 and creates one workload cluster per connection.

2. Align flag parameters (controller and ret.sh `checker.rx` must match, or submissions fail):
   - controller `FLAG_SALT` == `checker.rx` `ENCRYPT_KEY`
   - controller `FLAG_CHAL_ID` == `checker.rx` `HASH_KEY`

3. Build and push the bridge pod image:

```sh
cd ret2shell-ext-controller-pod
docker build -t registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/netshare:latest .
docker push registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/netshare:latest
```

4. Configure the challenge on ret.sh:
   - `ret2shell-ext-controller-pod/checker.rx`: point `CONTROLLER_HOST` / `CONTROLLER_PORT` at the controller from step 1; align `ENCRYPT_KEY` / `HASH_KEY` per step 2; handle the `sk-` prefix parsing per platform convention (flag is `sk-<uuid>`, no braces)
   - `ret2shell-ext-controller-pod/pod.yaml`: set `image` to the image from step 3
   - set `checker.rx` as the flag checker and `pod.yaml` as the instance manifest

Environment requirements (the controller creates workload clusters from the templates in `kubernetes-on-demand-main/resources/`, which already provide the properties the vulnerability needs):

- Kubernetes v1.28 (created by CAPI, `ValidatingAdmissionPolicy` enabled by default).
- Calico CNI with small `blockSize: 28` allocation blocks, so a stale backend IP can be re-occupied by the target Pod.
- Nodes preloaded with the `python:3.11-alpine` image (the target Pod uses `imagePullPolicy: Never`).

Local quick check (bypassing ret.sh) — simulate the bridge pod with a single `nc`:

```sh
printf '62\n' | nc <controller host> 8888   # keep the connection open
```

The kubeconfig is between `-----BEGIN KUBECONFIG-----` and `-----END KUBECONFIG-----` in the output; save it and run `kubectl --kubeconfig <file> get ns`. Closing the connection destroys the corresponding cluster.

Verify available permissions after obtaining the kubeconfig:

```sh
export KUBECONFIG="$PWD/runtime-operator.kubeconfig"
kubectl get pods -n tenant-runtime
kubectl get pods,svc,endpoints,endpointslices -n customer-platform -o wide
```
