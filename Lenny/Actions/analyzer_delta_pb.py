READ_CONTINUOUSLY = (
    "/api.unsafe.analyzer_delta.AnalyzerDeltaEndpoint/read_continuously"
)


def _varint(value: int) -> bytes:
    result = bytearray()

    while value > 0x7F:
        result.append((value & 0x7F) | 0x80)
        value >>= 7

    result.append(value)
    return bytes(result)


def _length_delimited(field_number: int, payload: bytes) -> bytes:
    tag = (field_number << 3) | 2
    return _varint(tag) + _varint(len(payload)) + payload


def encode_newton_depth(hexdata: str) -> bytes:
    inner = _length_delimited(1, hexdata.encode("utf-8"))
    return _length_delimited(1, inner)


def encode_tachyon_data(hexdata: str) -> bytes:
    inner = _length_delimited(1, hexdata.encode("utf-8"))
    return _length_delimited(2, inner)