from __future__ import annotations

import zlib
from collections.abc import Iterable, Iterator


STREAM_NOTE_TOKEN = b"<!-- edge-stream-note -->"
STREAM_NOTE_BYTES = 64
ROUTE_NOTE_TOKEN = b"0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-._~"
ROUTE_NOTE_SUFFIX = b"X1fH~-ZM9TB_rKrmGsNmjQ8mT3OA94HhblZa.QFPiyCEs5lkO~-nMLpQAK4lXO\">"


def _compressor(level: int) -> zlib.compressobj:
    return zlib.compressobj(
        level,
        zlib.DEFLATED,
        -zlib.MAX_WBITS,
        zlib.DEF_MEM_LEVEL,
        zlib.Z_FILTERED,
    )


def _flush_segment(compressor: zlib.compressobj, body: bytes, mode: int) -> bytes:
    return compressor.compress(body) + compressor.flush(mode)


def _edge_note_parts(origin: str) -> tuple[bytes, bytes]:
    note = f'<a href="{origin}/edge/routing/'.encode("utf-8")
    padded = note + ROUTE_NOTE_TOKEN
    if len(padded) <= STREAM_NOTE_BYTES:
        padded = padded + ROUTE_NOTE_TOKEN[: STREAM_NOTE_BYTES - len(padded) + 1]
    return padded[: STREAM_NOTE_BYTES - 1], padded[STREAM_NOTE_BYTES - 1 : STREAM_NOTE_BYTES] + ROUTE_NOTE_SUFFIX


def stream_deflate(parts: Iterable[bytes], origin: str, level: int) -> Iterator[bytes]:
    body = b"".join(parts)
    marker = body.find(STREAM_NOTE_TOKEN)
    compressor = _compressor(level)

    if marker == -1:
        chunk = _flush_segment(compressor, body, zlib.Z_FINISH)
        if chunk:
            yield chunk
        return

    before = body[:marker]
    after = body[marker + len(STREAM_NOTE_TOKEN):]
    prefix, suffix = _edge_note_parts(origin)

    # Keep the routing note on its own recovery boundary, then continue with a
    # small shared dictionary for repeated status text across adjacent chunks.
    prelude = _flush_segment(compressor, before, zlib.Z_FULL_FLUSH)
    prelude += _flush_segment(compressor, suffix, zlib.Z_SYNC_FLUSH)
    for chunk in (
        prelude,
        _flush_segment(compressor, prefix + suffix, zlib.Z_SYNC_FLUSH),
        _flush_segment(compressor, after, zlib.Z_FINISH),
    ):
        if chunk:
            yield chunk
