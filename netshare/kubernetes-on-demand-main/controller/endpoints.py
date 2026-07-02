from kubernetes_asyncio import client

def generate_endpoints(namespace: str, name: str, ip: str):
    return client.V1Endpoints(
        api_version="v1",
        kind="Endpoints",
        metadata=client.V1ObjectMeta(
            name=name,
            namespace=namespace,
        ),
        subsets=[
            client.V1EndpointSubset(
                addresses=[client.V1EndpointAddress(ip=ip)],
                ports=[client.CoreV1EndpointPort(name="https", port=6443, protocol="TCP")],
            ),
        ],
    )


async def create_endpoints(api: client.ApiClient, name: str, namespace: str, ip: str):
    core_api = client.CoreV1Api(api)
    body = generate_endpoints(namespace, name, ip)
    await core_api.create_namespaced_endpoints(namespace, body)


