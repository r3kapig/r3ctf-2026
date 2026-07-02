import asyncio
import logging

from const import name_to_host, DOMAIN, NAMESPACE_INGRESS
from dataclasses import dataclass
from kubernetes_asyncio import client, config, watch


def generate_ingress(namespace: str, name: str, rules: list):
    return client.V1Ingress(
        api_version="networking.k8s.io/v1",
        kind="Ingress",
        metadata=client.V1ObjectMeta(
            name=name,
            namespace=namespace,
            annotations={"nginx.ingress.kubernetes.io/backend-protocol": "HTTPS"},
        ),
        spec=client.V1IngressSpec(
            tls=[
                client.V1IngressTLS(
                    hosts=[DOMAIN],
                    secret_name="domain-cert",
                )
            ],
            rules=rules,
            default_backend=client.V1IngressBackend(
                service=client.V1IngressServiceBackend(
                    name="default-backend",
                    port=client.V1ServiceBackendPort(number=443),
                )
            ),
        ),
    )


@dataclass
class IngressEvent:
    action: str
    name: str


class Ingress:
    api: client.NetworkingV1Api
    names: list[str]
    queue = asyncio.Queue()
    logger = logging.getLogger("ingress")

    def __init__(self, api: client.ApiClient):
        self.api = client.NetworkingV1Api(api)
        self.names = []

    def generate_rules(self):
        return [
            client.V1IngressRule(
                host=name_to_host(name),
                http=client.V1HTTPIngressRuleValue(
                    paths=[
                        client.V1HTTPIngressPath(
                            path="/",
                            path_type="Prefix",
                            backend=client.V1IngressBackend(
                                service=client.V1IngressServiceBackend(
                                    name=name,
                                    port=client.V1ServiceBackendPort(
                                        number=443,
                                    ),
                                )
                            ),
                        )
                    ]
                ),
            )
            for name in self.names
        ]

    async def ensure(self):
        try:
            await self.api.read_namespaced_ingress("kube-api-entry", NAMESPACE_INGRESS)
            self.logger.info("Ingress already exists")
            return
        except client.ApiException as e:
            if e.status != 404:
                # other error
                raise e
            # ingress doesn't exists

        self.logger.info("Ingress not found, creating")

        body = generate_ingress(NAMESPACE_INGRESS, "kube-api-entry", [])

        await self.api.create_namespaced_ingress(NAMESPACE_INGRESS, body)

    async def remove(self):
        self.logger.info("Destroying ingress")
        await self.api.delete_namespaced_ingress("kube-api-entry", NAMESPACE_INGRESS)

    async def configure(self):
        rules = self.generate_rules()
        body = generate_ingress(NAMESPACE_INGRESS, "kube-api-entry", rules)
        await self.api.patch_namespaced_ingress("kube-api-entry", NAMESPACE_INGRESS, body)

    async def worker(self):
        while True:
            event: IngressEvent = await self.queue.get()
            match event.action:
                case "create":
                    self.logger.info(f"Adding name {event.name}")
                    self.names.append(event.name)
                case "delete":
                    self.logger.info(f"Removing name {event.name}")
                    try:
                        self.names.remove(event.name)
                    except ValueError:
                        # ignore if not exists
                        pass

            await self.configure()

            self.queue.task_done()

    @classmethod
    async def add_name(cls, name: str):
        await cls.queue.put(IngressEvent("create", name))

    @classmethod
    async def remove_name(cls, name: str):
        await cls.queue.put(IngressEvent("delete", name))
