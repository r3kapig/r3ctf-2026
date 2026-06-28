from kubernetes_asyncio import client

def generate_service(namespace: str, name: str):
    return client.V1APIService(
        api_version="v1",
        kind="Service",
        metadata=client.V1ObjectMeta(
            name=name,
            namespace=namespace,
        ),
        spec=client.V1ServiceSpec(
            ports=[
                client.V1ServicePort(
                    name="https",
                    port=443,
                    target_port=6443,
                )
            ]
        ),
    )


async def create_service(api: client.ApiClient, name: str, namespace: str):
    core_api = client.CoreV1Api(api)
    body = generate_service(namespace, name)
    await core_api.create_namespaced_service(namespace, body)


async def delete_service(api: client.ApiClient, name: str, namespace: str):
    core_api = client.CoreV1Api(api)
    await core_api.delete_namespaced_service(name, namespace)


