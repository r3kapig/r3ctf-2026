import docker
import base64
import hashlib
import hmac
import json
import os
import struct
import time
import uuid as _uuid

# Host (or IP) players use to reach the per-cluster haproxy container. The
# controller bakes this into the kubeconfig it returns. Configured via the
# PUBLIC_HOST env var on the kubernetes service in docker-compose.yml.
PUBLIC_HOST = os.getenv("PUBLIC_HOST", "127.0.0.1")

# Per-team dynamic flag parameters. The flag is derived from the GZCTF team
# token so every team gets a different flag (anti-sharing). For GZCTF to accept
# the submitted flag, FLAG_SALT and FLAG_CHAL_ID must match the values this
# challenge is configured with on the platform — override them via env when the
# net-share challenge's real salt / challenge-id differ from the defaults below.
FLAG_SALT = os.getenv("FLAG_SALT", "bd6b642f4db5d1718fa7b509f9058a2f57337a6e86c730362e5a6edafe915686")
FLAG_CHAL_ID = os.getenv("FLAG_CHAL_ID", "62")


# UUIDStego per-team flag, equivalent to ret2script audit.rs / uuid_stego.py.
# Embed team_id into a random-looking UUID: SHA1(template) supplies the carrier,
# XXTEA(key) encrypts team_id, the encrypted bytes are interleaved into the odd
# carrier bytes with XOR, then ChaCha20-Poly1305 with a key-derived nonce
# diffuses the result into the final UUID. The salt is fixed at zero, so output
# is deterministic. External platform decoders using the same key=FLAG_SALT and
# template=FLAG_CHAL_ID can strip the sk- prefix and decode the team_id for
# attribution and anti-sharing checks.
_XXTEA_DELTA = 0x9E3779B9


def _xxtea_to_u32(data: bytes) -> list:
    n = (len(data) + 3) >> 2
    v = [0] * n
    for i in range(len(data)):
        v[i >> 2] |= data[i] << ((i & 3) << 3)
    return v


def _xxtea_to_bytes(v: list) -> bytes:
    out = bytearray(len(v) << 2)
    for i in range(len(out)):
        out[i] = (v[i >> 2] >> ((i & 3) << 3)) & 0xFF
    return bytes(out)


def _xxtea_mx(s, y, z, p, e, k):
    return (
        (((z >> 5) ^ (y << 2)) + ((y >> 3) ^ (z << 4)))
        ^ ((s ^ y) + (k[(p & 3) ^ e] ^ z))
    ) & 0xFFFFFFFF


def _xxtea_encrypt(data: bytes, key: str) -> bytes:
    v = _xxtea_to_u32(data)
    k = _xxtea_to_u32(key.encode())
    while len(k) < 4:
        k.append(0)
    n = len(v) - 1
    z = v[n]
    s = 0
    q = 6 + 52 // len(v)
    for _ in range(q):
        s = (s + _XXTEA_DELTA) & 0xFFFFFFFF
        e = (s >> 2) & 3
        for p in range(n):
            y = v[p + 1]
            v[p] = (v[p] + _xxtea_mx(s, y, z, p, e, k)) & 0xFFFFFFFF
            z = v[p]
        y = v[0]
        v[n] = (v[n] + _xxtea_mx(s, y, z, n, e, k)) & 0xFFFFFFFF
        z = v[n]
    return _xxtea_to_bytes(v)


def _chacha_block(key: str, data: bytes) -> bytes:
    # Lazy import so kubeconfig.py still imports if the package is missing at
    # build time; controller/Dockerfile installs `cryptography`.
    from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

    h = hashlib.sha256(key.encode()).digest()
    return ChaCha20Poly1305(h[:32]).encrypt(h[-12:], data, None)


def _encode_uuid(template: str, key: str, team_id: int, with_hyphen: bool = True) -> str:
    hash_slice = bytearray(hashlib.sha1(template.encode()).digest()[2:18])
    enc = _xxtea_encrypt(struct.pack("<q", team_id), key)[:8].ljust(8, b"\x00")
    salt = b"\x00\x00\x00\x00"  # Fixed salt: same input, same output.
    for i in range(8):
        if i % 2 == 0:
            hash_slice[i * 2] ^= salt[i // 2]
        hash_slice[i * 2 + 1] ^= enc[i]
    uuid_bytes = _chacha_block(key, bytes(hash_slice))[:16]
    u = _uuid.UUID(bytes=uuid_bytes)
    return str(u) if with_hyphen else u.hex


def _team_id_from_token(team_token: str) -> int:
    """Derive the i64 team_id embedded in the flag.

    Real GZCTF tokens are `<id>:<sig>` -> use the numeric id (so decode yields
    the real team). SKIP_TOKEN_VERIFY test tokens (e.g. test-team-001) aren't
    numeric -> fall back to a stable signed-64-bit hash of the whole token.
    """
    head = team_token.split(":")[0]
    try:
        tid = int(head)
        if -(2 ** 63) <= tid < 2 ** 63:
            return tid
    except ValueError:
        pass
    return int.from_bytes(
        hashlib.sha256(team_token.encode()).digest()[:8], "little", signed=True
    )


def flag_generate(team_token: str) -> str:
    """Per-team flag via UUIDStego (key=FLAG_SALT, template=FLAG_CHAL_ID).

    Embeds the team_id into a UUID and prefixes it with `sk-`. Deterministic:
    same (team_token, salt, chal_id) -> same flag. The platform decodes the
    UUID (after stripping `sk-`) back to team_id; different team_token ->
    different flag.
    """
    team_id = _team_id_from_token(team_token)
    uuid_str = _encode_uuid(FLAG_CHAL_ID, FLAG_SALT, team_id, with_hyphen=True)
    return f"sk-{uuid_str}"


def create_service_assertion(flag: str) -> str:
    """Wrap the challenge proof in a business-style signed service assertion."""
    now = int(time.time())
    payload = {
        "iss": "profile-cache-refresh",
        "aud": "customer-profile-api",
        "scope": "profile.read",
        "tenant": "tenant-runtime",
        "iat": now,
        "exp": now + 86400,
        "service_proof": flag,
    }
    encoded_payload = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    ).decode().rstrip("=")
    signature = hmac.new(
        FLAG_SALT.encode(), encoded_payload.encode(), hashlib.sha256
    ).digest()
    encoded_signature = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    return f"svc.v1.{encoded_payload}.{encoded_signature}"


def create_kube_token_and_server(token: str, conn_id: str) -> str:
    client = docker.from_env()
    containers = client.containers.list()

    mapping_ports = ""

    for container in containers:
        details = container.attrs
        name = details["Name"][1:]
        path = details["Path"]
        ports = details["NetworkSettings"]["Ports"]

        if name.startswith(conn_id) and path == "haproxy":
            for mapping in ports.get("6443/tcp", []) or []:
                if mapping.get("HostIp") in ("0.0.0.0", "::", "127.0.0.1"):
                    mapping_ports = mapping["HostPort"]
                    break

    server = f"https://{PUBLIC_HOST}:{mapping_ports}"


    kubeconfig = f"""apiVersion: v1
kind: Config
clusters:
- name: tenant-platform
  cluster:
    server: {server}
    insecure-skip-tls-verify: true
contexts:
- name: runtime-operator
  context:
    cluster: tenant-platform
    user: runtime-operator
    namespace: tenant-runtime
current-context: runtime-operator
users:
- name: runtime-operator
  user:
    token: {token}
"""

    return kubeconfig
