from __future__ import annotations

import os
import time
from dataclasses import dataclass

from flask import Flask, Response, jsonify, render_template, request, url_for

from .deflate_stream import stream_deflate


STARTED_AT = int(time.time())


@dataclass(frozen=True)
class ServiceCheck:
    name: str
    owner: str
    state: str
    latency_ms: int
    detail: str


CHECKS = (
    ServiceCheck("receiving-api", "platform", "nominal", 18, "localhost upstream routing"),
    ServiceCheck("label-print", "operations", "nominal", 24, "print queue drain within target"),
    ServiceCheck("cold-chain", "facilities", "watch", 41, "sensor bridge in scheduled maintenance"),
    ServiceCheck("fulfillment-feed", "integrations", "nominal", 33, "last vendor poll completed"),
)

MAINTENANCE = (
    {"window": "2026-06-08 02:00 UTC", "scope": "Inventory sync connector", "impact": "read-only"},
    {"window": "2026-06-12 05:30 UTC", "scope": "Thermal label profile refresh", "impact": "none"},
)


def bool_from_env(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def compression_level() -> int:
    raw = os.environ.get("WAREHOUSEHUB_STREAM_COMPRESSION_LEVEL", "6")
    try:
        return max(1, min(int(raw), 9))
    except ValueError:
        return 6


def public_origin() -> str:
    return request.url_root.rstrip("/")


def stream_chunk_size() -> int:
    raw = os.environ.get("WAREHOUSEHUB_STREAM_CHUNK_BYTES", "768")
    try:
        return max(256, min(int(raw), 8192))
    except ValueError:
        return 768


def html_chunks(html: str) -> list[bytes]:
    body_bytes = html.encode("utf-8")
    size = stream_chunk_size()
    return [body_bytes[offset : offset + size] for offset in range(0, len(body_bytes), size)]


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("WAREHOUSEHUB_SECRET", "warehousehub-local-secret"),
        STREAM_COMPRESSED_HOME=bool_from_env("WAREHOUSEHUB_STREAM_COMPRESSED_HOME", True),
    )

    @app.context_processor
    def template_links():
        return {
            "absolute_for": lambda endpoint, **values: url_for(endpoint, _external=True, **values),
            "origin": public_origin,
        }

    @app.get("/healthz")
    def healthz():
        return jsonify(
            {
                "service": "WarehouseHub",
                "status": "ok",
                "uptime_seconds": int(time.time()) - STARTED_AT,
            }
        )

    @app.get("/")
    def overview():
        rendered = render_template(
            "index.html",
            checks=CHECKS,
            maintenance=MAINTENANCE,
            canonical_url=url_for("overview", _external=True),
        )
        if not app.config["STREAM_COMPRESSED_HOME"]:
            return rendered

        response = Response(
            stream_deflate(html_chunks(rendered), public_origin(), compression_level()),
            mimetype="text/html",
            direct_passthrough=True,
        )
        response.headers["Content-Encoding"] = "deflate"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Vary"] = "Accept-Encoding"
        response.headers["X-WarehouseHub-View"] = "overview"
        return response

    @app.get("/status")
    def status():
        return render_template(
            "status.html",
            checks=CHECKS,
            maintenance=MAINTENANCE,
            canonical_url=url_for("status", _external=True),
        )

    @app.get("/api/status")
    def api_status():
        return jsonify(
            {
                "service": "WarehouseHub",
                "checks": [check.__dict__ for check in CHECKS],
                "maintenance": list(MAINTENANCE),
            }
        )

    @app.get("/robots.txt")
    def robots():
        return Response("User-agent: *\nDisallow:\n", mimetype="text/plain")

    return app


app = create_app()
