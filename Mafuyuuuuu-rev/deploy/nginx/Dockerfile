FROM nginx:1.27-alpine

# Bake the in-pod config (upstreams on 127.0.0.1) so the image works in a pod
# out of the box, without relying on a ConfigMap override. Local docker compose
# overrides this with the service-name config (see docker-compose.yml).
COPY nginx.pod.conf /etc/nginx/nginx.conf
EXPOSE 8089
