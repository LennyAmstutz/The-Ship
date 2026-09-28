# Protobuf-Nachrichten aus proto/api.proto, von Hand codiert (ohne protoc/grpcio).
#   message Void {}                       -> 0 Bytes
#   message SensorData { string hexdata = 1; }

READ_SENSOR_DATA = "/api.unsafe.sensor_void_energy.SensorVoidEnergyServer/read_sensor_data"


def _varint(value):
    out = bytearray()
    while value >= 0x80:
        out.append((value & 0x7F) | 0x80)
        value >>= 7
    out.append(value)
    return bytes(out)


def encode_sensor_data(hexdata):
    raw = hexdata.encode("utf-8")
    return b"\x0a" + _varint(len(raw)) + raw        # Feld 1, Typ 2 (Laenge + Bytes)
