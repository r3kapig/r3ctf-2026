import logging

from kubernetes_asyncio import client


def generate_cluster(namespace: str, name: str):
    return {
        "apiVersion": "cluster.x-k8s.io/v1beta1",
        "kind": "Cluster",
        "metadata": {
            "name": name,
            "namespace": namespace,
            "labels": {
                "cni": "calico",
                "challenge": "challenge",
            },
        },
        "spec": {
            "clusterNetwork": {
                # kubeadm preflight refuses a Pod subnet smaller than /24, so
                # the cluster-wide range stays at /22. The Ghost-in-the-Chain
                # collision domain comes from Calico's per-node block size 28
                # (see resources/patch-calico.py) plus the ResourceQuota
                # capping the namespace at 10 pods — every pod ends up
                # competing for the same /28 (14 IPs) on the single worker.
                "pods": {
                    "cidrBlocks": ["10.244.0.0/22"],
                },
                "serviceDomain": "cluster.local",
                "services": {
                    "cidrBlocks": ["10.96.0.0/24"],
                },
            },
            "topology": {
                "class": "kond",
                "controlPlane": {
                    "metadata": {},
                    "replicas": 1,
                },
                "variables": [],
                # v1.28.0 ships runc 1.1.7 and is vulnerable to
                # CVE-2024-21626. v1.28.15 uses the patched kind node image
                # pinned in resources/cluster.yaml.
                "version": "v1.28.15",
                "workers": {
                    "machineDeployments": [
                        {
                            "class": "default-worker",
                            "name": "md-0",
                            "replicas": 1,
                        },
                    ],
                },
            },
        },
    }


class ClusterAPI:
    logger = logging.getLogger("clusterapi")

    def __init__(self, api: client.ApiClient):
        self.api = client.CustomObjectsApi(api)

    async def get_list(self, namespace: str):
        return await self.api.list_namespaced_custom_object("cluster.x-k8s.io", "v1beta1", namespace, "clusters")

    async def get(self, namespace: str, name: str):
        return await self.api.get_namespaced_custom_object("cluster.x-k8s.io", "v1beta1", namespace, "clusters", name)

    async def create(self, namespace: str, name: str):
        cluster = generate_cluster(namespace, name)
        self.logger.info(f"Creating cluster {name}")
        return await self.api.create_namespaced_custom_object(
            "cluster.x-k8s.io", "v1beta1", namespace, "clusters", cluster
        )

    async def delete(self, namespace: str, name: str):
        self.logger.info(f"Deleting cluster {name}")
        return await self.api.delete_namespaced_custom_object(
            "cluster.x-k8s.io", "v1beta1", namespace, "clusters", name
        )
