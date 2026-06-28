import asyncio
import logging
import base64
import os
import socket
import yaml
import datetime
import dateutil.parser

# When SKIP_TOKEN_VERIFY=true the controller does not require a GZCTF-signed
# team token. This is intended for local validation of the Ghost-in-the-Chain
# challenge bundle — never enable it in a contest deployment.
SKIP_TOKEN_VERIFY = os.getenv("SKIP_TOKEN_VERIFY", "false").lower() == "true"

from cluster import ClusterAPI
from const import name_to_host, CERTIFICATE, DOMAIN, NAMESPACE_CLUSTERS, NAMESPACE_ENDPOINTS, NAMESPACE_INGRESS, NAMESPACE_SERVICES
from endpoints import create_endpoints
from ingress import Ingress
from kubernetes_asyncio import client, config, watch
from kubeconfig import create_kube_token_and_server, create_service_assertion, flag_generate
from pprint import pprint
from service import create_service, delete_service
from uuid import uuid4
from nacl.signing import VerifyKey

DEBUG = False
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MAIN")
num = 0


async def setup_cluster(cluster_api: ClusterAPI, conn_id: str, writer):
    global num
    await cluster_api.create(NAMESPACE_CLUSTERS, conn_id)

    # Written as a YAML comment (leading '#') so the whole nc stream stays a
    # valid kubeconfig the player can save directly; the dots appended below
    # land inside this same comment line.
    writer.write(b"Waiting for control plane")
    logger.info("Creating Cluster:" + str(num))
    num += 1
    while True:
        writer.write(b".")
        await writer.drain()
        api_response = await cluster_api.get(NAMESPACE_CLUSTERS, conn_id)
        if "status" in api_response and api_response["status"].get("controlPlaneReady"):
            break
        await asyncio.sleep(1)
    writer.write(b"\n")
    return api_response.get("spec", {}).get("controlPlaneEndpoint")


async def get_kubeconfig(api: client.ApiClient, conn_id: str, conn_logger: logging.Logger):
    core_api = client.CoreV1Api(api)
    secret = await core_api.read_namespaced_secret(f"{conn_id}-kubeconfig", NAMESPACE_CLUSTERS)
    kubeconfig = base64.b64decode(secret.data["value"]).decode()
    # load yaml
    kubeconfig = yaml.safe_load(kubeconfig)
    return kubeconfig


async def inject_service_assertion(workload_api: client.ApiClient, team_token: str, conn_logger: logging.Logger):

    core_api = client.CoreV1Api(workload_api)
    ns = "platform-operations"
    flag = flag_generate(team_token)
    assertion = create_service_assertion(flag)
    patch = {"stringData": {"client-assertion": assertion}}

    # The Secret is delivered via ClusterResourceSet and may not exist yet;
    # retry on 404 until the challenge bundle has been applied.
    for _ in range(120):
        try:
            await core_api.patch_namespaced_secret("profile-client-credentials", ns, patch)
            break
        except client.ApiException as e:
            if e.status == 404:
                await asyncio.sleep(1)
                continue
            conn_logger.error("Failed to patch service assertion Secret", exc_info=True)
            return
    else:
        conn_logger.error("Timed out waiting for profile-client-credentials Secret")
        return

    # Restart the refresh worker so the new pod picks up the patched assertion.
    # Best-effort: if no pod exists yet the eventually-created one already
    # reads the patched Secret.
    try:
        await core_api.delete_collection_namespaced_pod(
            ns, label_selector="app.kubernetes.io/name=profile-cache-refresh"
        )
    except client.ApiException as e:
        if e.status != 404:
            conn_logger.warning("Failed to restart profile-cache-refresh", exc_info=True)


async def get_service_account_token(api: client.ApiClient, conn_id: str, team_token: str,  conn_logger: logging.Logger):
    kubeconfig = await get_kubeconfig(api, conn_id, conn_logger)
    api = await config.new_client_from_config_dict(kubeconfig)
    core_api = client.CoreV1Api(api)
    for _ in range(120):
        try:
            await core_api.read_namespaced_service_account("runtime-operator", "default")
            break
        except client.ApiException as e:
            if e.status != 404:
                raise e
            await asyncio.sleep(1)
    else:
        conn_logger.error(
            "Timed out waiting for runtime-operator ServiceAccount; the challenge "
            "bundle (user.yaml) likely failed to apply to the workload cluster"
        )
        raise client.ApiException(
            status=504, reason="Timed out waiting for runtime-operator ServiceAccount"
        )

    token_secret_name = "runtime-operator-token"
    token_secret = client.V1Secret(
        metadata=client.V1ObjectMeta(
            name=token_secret_name,
            namespace="default",
            annotations={"kubernetes.io/service-account.name": "runtime-operator"},
        ),
        type="kubernetes.io/service-account-token",
    )
    try:
        await core_api.create_namespaced_secret("default", token_secret)
    except client.ApiException as e:
        if e.status != 409:  # already created on a previous / reconnected attempt
            raise e

    token = None
    for _ in range(120):
        secret = await core_api.read_namespaced_secret(token_secret_name, "default")
        if secret.data and secret.data.get("token"):
            token = base64.b64decode(secret.data["token"]).decode()
            break
        await asyncio.sleep(1)
    if token is None:
        conn_logger.error("Timed out waiting for runtime-operator token Secret to be populated")
        raise client.ApiException(
            status=504, reason="Timed out waiting for runtime-operator token"
        )
    # Install the team-specific service assertion before returning kubeconfig.
    await inject_service_assertion(api, team_token, conn_logger)

    await api.close()

    if DOMAIN == "domain.local":
        cert = CERTIFICATE  # TODO load certificate
    else:
        cert = None
    return create_kube_token_and_server(token, conn_id)


async def resource_setup(api: client.ApiClient, conn_id: str, conn_logger: logging.Logger, reader, writer):
    global num

    # no more than 5000 clusters
    if num > 5000:
        writer.write(b"# Too many connections, please try again later\n")
        return

    cluster_api = ClusterAPI(api)

    # get the team token and generate the flag

    writer.write(b"Please input the team token: ")
    # Without an explicit drain the prompt stays buffered: a client that waits
    # for the prompt before sending its token sees a blank, unresponsive
    # connection while the controller blocks on reader.read() below.
    await writer.drain()
    data = await reader.read(100)


    try:
        team_token = data.decode().strip()
        if not team_token:
            raise ValueError("empty token")
        if not SKIP_TOKEN_VERIFY:
            verify_key = VerifyKey(base64.b64decode("MLFvjNFeBwDsXOND5LpJG5mzvYvvNOPy0URpRunjNTw="))
            verify_data = f"GZCTF_TEAM_{team_token.split(':')[0]}".encode()
            verify_key.verify(verify_data, base64.b64decode(team_token.split(":")[1]))
    except asyncio.CancelledError:
        raise
    except Exception:
        writer.write(b"# Invalid token\n")
        return

    writer.write(rb"""
     _____      _    __
  _ _|___ /  ___| |_ / _|
 | '__||_ \ / __| __| |_
 | |  ___) | (__| |_|  _|
 |_| |____/ \___|\__|_|

""")
    writer.write(b"Challenge: Net Share\n")
    writer.write(b"Creating Cluster\n")
    try:
        control_plane = await setup_cluster(cluster_api, conn_id, writer)
        await Ingress.add_name(conn_id)
        try:
            await create_service(api, conn_id, NAMESPACE_SERVICES)
            try:
                await create_endpoints(api, conn_id, NAMESPACE_ENDPOINTS, control_plane["host"])
                try:
                    kubeconfig = await get_service_account_token(api, conn_id, team_token, conn_logger)
                except (KeyError, client.ApiException):
                    conn_logger.error("Error getting kubeconfig", exc_info=True)
                    writer.write(b"Error getting Kubernetes information\n")
                else:
                    # kubeconfig is already a complete apiVersion:v1/kind:Config
                    # document (see kubeconfig.create_kube_token_and_server). The
                    # surrounding lines are YAML comments, so the whole stream is
                    # a valid kubeconfig: just `nc <host> 8888 > kubeconfig.yaml`
                    # and `kubectl --kubeconfig kubeconfig.yaml get ns`.
                    writer.write(b"Your kubeconfig is below. Save this whole output to a file:\n")
                    writer.write(kubeconfig.encode())
                    writer.write(b"Keep this connection open: the kubeconfig stays valid until you disconnect. Closing the connection deletes your cluster.\n")
                    await writer.drain()
                    data = await reader.read(100)
            finally:
                try:
                    await delete_service(api, conn_id, NAMESPACE_SERVICES)
                    # endpoints is deleted automatically with the service
                except client.ApiException as e:
                    if e.status != 404:
                        # other error
                        raise e
        finally:
            await Ingress.remove_name(conn_id)
    finally:
        num -= 1
        try:
            await cluster_api.delete(NAMESPACE_CLUSTERS, conn_id)
        except client.ApiException as e:
            if e.status != 404:
                # other error
                raise e


def enable_keepalive(sock: socket.socket):
    """Enable TCP keepalive to detect dead connections through NAT/firewall.

    Without keepalive, if the client disconnects but the FIN is lost (e.g. NAT
    conntrack expired after long idle), reader.read() hangs forever and the k8s
    cluster is never cleaned up.
    """
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    # Start probing after 60s idle
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 60)
    # Probe every 10s
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)
    # Give up after 6 failed probes (~2 min to detect dead connection)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 6)


async def handle_connection(reader, writer):
    addr = writer.get_extra_info("peername")
    conn_id = "flux-cluster-" + uuid4().hex
    conn_logger = logging.getLogger(conn_id)
    conn_logger.info(f"New connection from {addr!r}, id: {conn_id}")

    # Enable TCP keepalive so dead connections are detected even if
    # NAT/firewall drops the conntrack entry during long idle periods
    sock = writer.get_extra_info("socket")
    if sock is not None:
        try:
            enable_keepalive(sock)
        except OSError:
            conn_logger.warning("Failed to set TCP keepalive", exc_info=True)



    try:
        async with client.ApiClient() as api:
            try:
                await resource_setup(api, conn_id, conn_logger, reader, writer)
            except client.ApiException as e:
                logger.error("Exception when calling kube api", exc_info=True)
            except ConnectionError:
                logger.error("Client closed connection:", exc_info=True)
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.warning("Unhandled exception", exc_info=True)
        try:
            writer.write(b"Unhandled exception during operation, please try again.")
            await writer.drain()
        except (ConnectionError, OSError):
            # Might fail if connection is closed, ignore
            pass
    finally:
        try:
            logger.info("Closing connection")
            writer.close()
            await writer.wait_closed()
        except:
            # Might fail if connection is closed, ignore
            pass


async def housekeeping():
    async with client.ApiClient() as api:
        ingress = Ingress(api)
        try:
            await ingress.ensure()
            asyncio.create_task(ingress.worker())
            logger.info("Setup done, running main loop")
            while True:
                await asyncio.sleep(10)
                #await cleanup_old_clusters(api)
        except asyncio.CancelledError:
            logger.info("housekeeping cancelled, running cleanup")
            await cleanup(api, ingress)


async def cleanup_old_clusters(api: client.ApiClient):
    cluster_api = ClusterAPI(api)
    cluster_list = await cluster_api.get_list(NAMESPACE_CLUSTERS)
    current_time = datetime.datetime.now(datetime.timezone.utc)

    for k,v in list(cluster_list.items()):
        if (current_time - dateutil.parser.isoparse(i.metadata.creation_timestamp)) > datetime.timedelta(minutes=60):
            try:
                await cluster_api.delete(NAMESPACE_CLUSTERS, i.metadata.name)
            except client.ApiException as e:
                if e.status != 404:
                    # other error
                    raise e


async def cleanup(api: client.ApiClient, ingress: Ingress):
    # destroy ingress
    await ingress.remove()


async def setup_config():
    if DEBUG:
        client_config = client.Configuration()
        client_config.debug = True
        await config.load_kube_config(client_configuration=client_config)
        client.Configuration.set_default(client_config)
    else:
        try:
            await config.load_kube_config()
        except config.config_exception.ConfigException:
            config.incluster_config.load_incluster_config()


async def main():
    await setup_config()

    server = await asyncio.start_server(handle_connection, "0.0.0.0", 8888)

    addrs = ", ".join(str(sock.getsockname()) for sock in server.sockets)
    print(f"Serving on {addrs}")

    async with server:
        await housekeeping()


loop = asyncio.get_event_loop()
try:
    # Here `amain(loop)` is the core coroutine that may spawn any
    # number of tasks
    exit(loop.run_until_complete(main()))
except KeyboardInterrupt:
    # Optionally show a message if the shutdown may take a while
    print("Attempting graceful shutdown, press Ctrl+C again to exit…", flush=True)

    # Do not show `asyncio.CancelledError` exceptions during shutdown
    # (a lot of these may be generated, skip this if you prefer to see them)
    # def shutdown_exception_handler(loop, context):
    #    if "exception" not in context \
    #    or not isinstance(context["exception"], asyncio.CancelledError):
    #        loop.default_exception_handler(context)
    # loop.set_exception_handler(shutdown_exception_handler)

    # Cancel all current tasks
    tasks = asyncio.gather(*asyncio.all_tasks(loop=loop), return_exceptions=True)
    tasks.add_done_callback(lambda t: loop.stop())
    tasks.cancel()

    # Keep the event loop running until it is either destroyed or all tasks have really terminated
    while not tasks.done() and not loop.is_closed():
        loop.run_forever()
    print(repr(tasks.exception()))
finally:
    loop.run_until_complete(loop.shutdown_asyncgens())
    loop.close()
