import datetime
import os
import struct
import threading
import time

# BSON (das Datenformat von MongoDB) lesen und schreiben - ohne pymongo.
# Wird vom eigenen MongoDB-Server (mongo_server.py) und vom Client (mongo_client.py) benutzt.


class ObjectId:
    _counter = int.from_bytes(os.urandom(3), "big")
    _random = os.urandom(5)
    _lock = threading.Lock()

    def __init__(self, raw=None):
        if raw is None:
            with ObjectId._lock:
                ObjectId._counter = (ObjectId._counter + 1) % 0xFFFFFF
                counter = ObjectId._counter
            raw = struct.pack(">I", int(time.time())) + ObjectId._random + counter.to_bytes(3, "big")
        elif isinstance(raw, str):
            raw = bytes.fromhex(raw)
        self.raw = raw

    def __eq__(self, other):
        return isinstance(other, ObjectId) and other.raw == self.raw

    def __hash__(self):
        return hash(self.raw)

    def __repr__(self):
        return f"ObjectId('{self.raw.hex()}')"


class Timestamp:
    def __init__(self, time_part, increment):
        self.time, self.inc = time_part, increment


class Binary(bytes):
    """Binaerdaten mit Subtyp (normale bytes werden als Subtyp 0 geschrieben)."""

    def __new__(cls, data, subtype=0):
        obj = super().__new__(cls, data)
        obj.subtype = subtype
        return obj


_EPOCH = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)


def _cstring(text):
    return text.encode("utf-8") + b"\x00"


def _element(key, value):
    name = _cstring(key)
    if isinstance(value, bool):
        return b"\x08" + name + (b"\x01" if value else b"\x00")
    if isinstance(value, float):
        return b"\x01" + name + struct.pack("<d", value)
    if isinstance(value, int):
        if -2 ** 31 <= value < 2 ** 31:
            return b"\x10" + name + struct.pack("<i", value)
        return b"\x12" + name + struct.pack("<q", value)
    if isinstance(value, str):
        raw = value.encode("utf-8") + b"\x00"
        return b"\x02" + name + struct.pack("<i", len(raw)) + raw
    if isinstance(value, dict):
        return b"\x03" + name + encode(value)
    if isinstance(value, (list, tuple)):
        return b"\x04" + name + encode({str(i): v for i, v in enumerate(value)})
    if isinstance(value, (bytes, bytearray)):
        subtype = getattr(value, "subtype", 0)
        return b"\x05" + name + struct.pack("<i", len(value)) + bytes([subtype]) + bytes(value)
    if isinstance(value, ObjectId):
        return b"\x07" + name + value.raw
    if isinstance(value, datetime.datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=datetime.timezone.utc)
        millis = int((value - _EPOCH).total_seconds() * 1000)
        return b"\x09" + name + struct.pack("<q", millis)
    if value is None:
        return b"\x0a" + name
    if isinstance(value, Timestamp):
        return b"\x11" + name + struct.pack("<II", value.inc, value.time)
    raise TypeError(f"BSON kennt den Typ {type(value).__name__} nicht ({key})")


def encode(document):
    body = b"".join(_element(key, value) for key, value in document.items())
    return struct.pack("<i", len(body) + 5) + body + b"\x00"


def _read_cstring(data, pos):
    end = data.index(b"\x00", pos)
    return data[pos:end].decode("utf-8"), end + 1


def decode(data, pos=0):
    """Liest ein BSON-Dokument ab pos. Gibt (dict, position_danach) zurueck."""
    size = struct.unpack_from("<i", data, pos)[0]
    end = pos + size - 1
    pos += 4
    document = {}
    while pos < end:
        kind = data[pos]
        key, pos = _read_cstring(data, pos + 1)
        if kind == 0x01:
            value = struct.unpack_from("<d", data, pos)[0]
            pos += 8
        elif kind in (0x02, 0x0D, 0x0E):                  # String, JavaScript, Symbol
            length = struct.unpack_from("<i", data, pos)[0]
            value = data[pos + 4:pos + 3 + length].decode("utf-8")
            pos += 4 + length
        elif kind in (0x03, 0x04):
            value, pos = decode(data, pos)
            if kind == 0x04:
                value = list(value.values())
        elif kind == 0x05:
            length = struct.unpack_from("<i", data, pos)[0]
            value = Binary(data[pos + 5:pos + 5 + length], data[pos + 4])
            pos += 5 + length
        elif kind == 0x07:
            value = ObjectId(bytes(data[pos:pos + 12]))
            pos += 12
        elif kind == 0x08:
            value = data[pos] == 1
            pos += 1
        elif kind == 0x09:
            millis = struct.unpack_from("<q", data, pos)[0]
            value = _EPOCH + datetime.timedelta(milliseconds=millis)
            pos += 8
        elif kind in (0x06, 0x0A, 0x7F, 0xFF):             # undefined, null, MaxKey, MinKey
            value = None
        elif kind == 0x10:
            value = struct.unpack_from("<i", data, pos)[0]
            pos += 4
        elif kind == 0x11:
            inc, time_part = struct.unpack_from("<II", data, pos)
            value = Timestamp(time_part, inc)
            pos += 8
        elif kind == 0x12:
            value = struct.unpack_from("<q", data, pos)[0]
            pos += 8
        elif kind == 0x13:                                   # Decimal128 - roh behalten
            value = Binary(data[pos:pos + 16], 0x13)
            pos += 16
        else:
            raise ValueError(f"unbekannter BSON-Typ 0x{kind:02x} bei {key}")
        document[key] = value
    return document, end + 1
