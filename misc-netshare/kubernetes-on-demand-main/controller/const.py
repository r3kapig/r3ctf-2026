import os
from base64 import b64encode

DOMAIN = os.getenv("APP_DOMAIN", "domain.local")
def name_to_host(name: str):
    return f"{name}.{DOMAIN}"

try:
    CERTIFICATE = b64encode(open("resources/tls.crt").read().encode()).decode()
except FileNotFoundError:
    CERTIFICATE = None

NAMESPACE_CLUSTERS = "default"
NAMESPACE_SERVICES = "default"
NAMESPACE_ENDPOINTS = "default"
NAMESPACE_INGRESS ="default"
