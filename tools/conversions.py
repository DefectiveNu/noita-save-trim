import struct
import sys
from typing import Literal


def serialize_int(i: int, size=4, byteorder: Literal['little', 'big'] = 'big', signed=True):
    return int.to_bytes(i, size, byteorder, signed=signed)


def serialize_float(f: float, byteorder='big'):
    if byteorder == "big":
        return struct.pack("f", f)[::-1]
    return struct.pack("f", f)


def serialize_str(b: bytes):
    length = serialize_int(len(b))
    return length + b


def bytes_to_int(b, byteorder: Literal['little', 'big'] = 'big', signed=True):
    return int.from_bytes(b, byteorder, signed=signed)


def bytes_to_float(b, byteorder='big'):
    step = 1
    if byteorder == "big":
        step = -1
    return struct.unpack("f", b[::step])[0]


def hex_to_int(h: str):
    return bytes_to_int(bytes.fromhex(h))


def hex_to_float(h: str):
    return bytes_to_float(bytes.fromhex(h))


def retry_as_float(i: int):
    return bytes_to_float(serialize_int(i))


def readable_bytes(b: bytes):
    ret = ""
    b = b.decode(errors="replace")
    for i in range(len(b)):
        if not b[i].isprintable():
            ret += "�"
        else:
            ret += b[i]
    return ret


def hex_readable(b: bytes):
    ret = []
    for i in range(len(b)):
        if 0x20 <= b[i] <= 0x7E:  # printable ascii
            ret.append(f" {chr(b[i])}")
        else:
            ret.append(b[i:i+1].hex())
    return " ".join(ret)


class ReadableBytes:
    b: bytes
    def __init__(self, b: bytes):
        self.b = b
    def __str__(self):
        return readable_bytes(self.b)
class ReadableHex:
    b: bytes
    def __init__(self, b: bytes):
        self.b = b
    def __str__(self):
        return hex_readable(self.b)
class BytesToPixels:
    b: bytes
    def __init__(self, b: bytes, dimx, dimy):
        self.b = b
        self.dimx = dimx
        self.dimy = dimy
    def __str__(self):
        return bytes_to_pixels(self.b, self.dimx, self.dimy)


def next_string(b: bytes):
    # note: this misses strings that extend past the end of supplied bytes
    for i in range(len(b)):
        str_len = int.from_bytes(b[i:i + 4], 'big')
        if 1 < str_len < len(b):
            end_pos = i + 4 + str_len
            str_contents = b[i + 4:end_pos].decode(errors="replace")
            if str_contents.isprintable() and "�" not in str_contents:
                #print(f"next str after {i} (len {str_len}) {str_contents}")
                return i, str_contents


def bytes_to_pixels(pxs: bytes, dimx, dimy):
    out = []
    for y in range(dimy):
        for x in range(dimx):
            a = pxs[4*x+4*dimx*y]/255
            # 0.2126×R+0.7152G+0.0722B
            b = pxs[4*x+4*dimx*y+1]/255
            g = pxs[4*x+4*dimx*y+2]/255
            r = pxs[4*x+4*dimx*y+3]/255
            intensity = (0.2126*r + 0.7152*g + 0.0722*b) * a
            if intensity < 0.001:
                out.append("  ")
            elif intensity < 0.3:
                out.append("\u2591\u2591")
            elif intensity < 0.5:
                out.append("\u2592\u2592")
            elif intensity < 0.7:
                out.append("\u2593\u2593")
            else:
                out.append("\u2588\u2588")  # full block
        out.append("\n")
    return "".join(out)


def is_valid_string(b: bytes):
    str_contents = b.decode(errors="replace")
    return str_contents.isprintable() and "�" not in str_contents