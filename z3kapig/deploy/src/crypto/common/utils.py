from crypto.common.ec import Point, ECOperations



ec = ECOperations()


def serialize_point(point: Point) -> dict:
    if point is None:
        return None
    if point.is_infinity:
        return {"is_infinity": True, "x": "0x0", "y": "0x0"}
    return {"is_infinity": False, "x": hex(point.x), "y": hex(point.y)}


def deserialize_point(data: dict) -> Point:
    if data is None:
        return None
    if data.get("is_infinity", False):
        return Point.infinity(ec.curve)
    x = int(data["x"], 16)
    y = int(data["y"], 16)
    return Point(x, y, ec.curve)


def serialize_bytes_list(bytes_list) -> list[str]:
    if bytes_list is None:
        return None

    if not isinstance(bytes_list, list):
        return [bytes_list.hex()]
    return [b.hex() if isinstance(b, bytes) else b for b in bytes_list]


def deserialize_bytes_list(hex_list: list[str]) -> list[bytes]:
    if hex_list is None:
        return None
    return [bytes.fromhex(h) if isinstance(h, str) else h for h in hex_list]
