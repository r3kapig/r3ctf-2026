#!/bin/sh
# netshare is a k8s-on-demand system (controller + per-team bridge pod).
# 1. Build+push the bridge image (already pushed as .../netshare:latest):
#      cd ret2shell-ext-controller-pod
#      docker build -t registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/netshare:latest .
#      docker push registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/netshare:latest
# 2. Run the controller on the controller host:
#      cd kubernetes-on-demand-main
#      PUBLIC_HOST=<IP> FLAG_SALT=<salt> FLAG_CHAL_ID=<id> docker compose up -d
# 3. Point ret2shell-ext-controller-pod/pod.yaml image at the pushed bridge image.
set -e
echo "netshare: bridge image = registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/netshare:latest"
echo "netshare: run controller from kubernetes-on-demand-main/ (see README.md)."
