FROM debian:bookworm

RUN apt-get update && apt-get install -y curl
RUN curl -LO https://download.docker.com/linux/static/stable/x86_64/docker-27.5.1.tgz && \
    tar --extract --strip-components 1 --file docker-27.5.1.tgz --directory /usr/local/bin/ docker/docker && \
    rm docker-27.5.1.tgz && \
    curl -Lo /usr/local/bin/kind https://kind.sigs.k8s.io/dl/v0.25.0/kind-linux-amd64 && \
    curl -Lo /usr/local/bin/kubectl https://dl.k8s.io/release/v1.31.4/bin/linux/amd64/kubectl && \
    curl -Lo /usr/local/bin/clusterctl https://github.com/kubernetes-sigs/cluster-api/releases/download/v1.9.7/clusterctl-linux-amd64 && \
    chmod +x /usr/local/bin/docker /usr/local/bin/kind /usr/local/bin/kubectl /usr/local/bin/clusterctl && \
    mkdir /app

WORKDIR /app

# Github rate limits access to the repositories, create a local mirror
# path format must be: {basepath}/{provider-name}/{version}/{components.yaml}
ADD https://github.com/kubernetes-sigs/cluster-api/releases/download/v1.9.7/core-components.yaml /app/cluster-api/v1.9.7/core-cluster-api.yaml
ADD https://github.com/kubernetes-sigs/cluster-api/releases/download/v1.9.7/bootstrap-components.yaml /app/bootstrap-kubeadm/v1.9.7/bootstrap-kubeadm.yaml
ADD https://github.com/kubernetes-sigs/cluster-api/releases/download/v1.9.7/control-plane-components.yaml /app/control-plane-kubeadm/v1.9.7/control-plane-kubeadm.yaml
ADD https://github.com/kubernetes-sigs/cluster-api/releases/download/v1.9.7/infrastructure-components-development.yaml /app/infrastructure-docker/v1.9.7/infrastructure-docker.yaml

ADD https://github.com/kubernetes-sigs/cluster-api/releases/download/v1.9.7/metadata.yaml /app/cluster-api/v1.9.7/
ADD https://github.com/kubernetes-sigs/cluster-api/releases/download/v1.9.7/metadata.yaml /app/infrastructure-docker/v1.9.7/

ADD https://github.com/cert-manager/cert-manager/releases/download/v1.16.3/cert-manager.yaml /app/cert-manager/v1.16.3/cert-manager.yaml

# cni manifest
ADD https://raw.githubusercontent.com/projectcalico/calico/v3.26.1/manifests/calico.yaml /app/calico.yaml
# Shrink Calico IPAM to match the /28 Pod CIDR used by the Ghost-in-the-Chain
# challenge: change the default IP pool to 10.244.1.0/28 and inject a /28
# CALICO_IPV4POOL_BLOCK_SIZE env var so the entire cluster shares the same
# 14 usable Pod IPs (the race condition relies on this collision domain).
COPY resources/patch-calico.py /app/patch-calico.py
RUN apt-get install -y python3 && \
    python3 /app/patch-calico.py /app/calico.yaml

COPY resources/entrypoint.sh resources/clusterctl.yaml resources/kind-cluster.yaml resources/ingress-nginx.yaml resources/headlamp.yaml resources/cluster.yaml resources/controller.yaml /app/
COPY resources/example-challenge.yaml /app/challenge.yaml
COPY resources/example-user.yaml /app/user.yaml

CMD [ "/app/entrypoint.sh" ]
