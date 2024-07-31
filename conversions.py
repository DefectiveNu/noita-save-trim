import struct


def serialize_int(i: int, size=4, byteorder='big', signed=True):
    return int.to_bytes(i, size, byteorder, signed=signed)


def serialize_float(f: float, byteorder='big'):
    if byteorder == "big":
        return struct.pack("f", f)[::-1]
    return struct.pack("f", f)


def serialize_str(b: bytes):
    length = serialize_int(len(b))
    return length + b


def bytes_to_int(b, byteorder='big', signed=True):
    return int.from_bytes(b, byteorder, signed=signed)


def bytes_to_float(b, byteorder='big'):
    step = 1
    if byteorder == "big":
        step = -1
    return struct.unpack("f", b[::step])[0]