import re
from typing import Literal

import fastlz
import struct
import os

from tools.conversions import serialize_str, serialize_int, serialize_float, readable_bytes, hex_readable, \
    ReadableBytes, ReadableHex
from tools.coords import num_to_coords


class NoitaFileSection:
    def __init__(self, value):
        self.value = value

    def serialize(self):
        return self.value

    @property
    def raw_len(self):
        return len(self.value)

    def readable_short(self):
        return readable_bytes(self.value)

    def readable_long(self):
        return hex_readable(self.value)

    def to_dict(self, **kwargs):
        return self.value


class NoitaRaw(NoitaFileSection, bytes):
    @classmethod
    def from_file(cls, file: "NoitaBinFile", read_len):
        ret = NoitaRaw(file.contents[file.read_pos:file.read_pos + read_len])
        file.read_pos += read_len
        return ret

    def to_dict(self, raw_as="both", hex_group=1, **kwargs):
        if raw_as == "hex":
            return self.hex(' ', hex_group)
        if raw_as == "hex_readable":
            return hex_readable(self)
        if raw_as == "bytes":
            return hex_readable(self)
        if raw_as == "both":
            return {"hex": self.hex(' ', -4), "bytes": readable_bytes(self)}
        if raw_as == "length":
            return len(self)

class NoitaString(NoitaFileSection, bytes):
    def __init__(self, value):
        super().__init__(value)

    def serialize(self):
        return serialize_str(self.value)

    @property
    def raw_len(self):
        return len(self.value) + 4

    def readable_short(self):
        return self.value.decode()

    def readable_long(self):
        return self.value.decode()

    def to_dict(self, **kwargs):
        return self.value.decode()


class NoitaInt(NoitaFileSection, int):
    raw_len = 4

    def __init__(self, value):
        super().__init__(value)

    def serialize(self):
        return serialize_int(self.value)

    @classmethod
    def from_bytes(cls, b, byteorder: Literal["little", "big"] = "big", signed=True):
        return cls(int.from_bytes(b, byteorder, signed=signed))

    @classmethod
    def from_file(cls, file: "NoitaBinFile"):
        ret = cls.from_bytes(file.contents[file.read_pos:file.read_pos + 4], 'big', signed=True)
        file.read_pos += 4
        return ret

    def readable_short(self):
        return str(self.value)

    def readable_long(self):
        return str(self.value)


class NoitaByte(NoitaInt):
    raw_len = 1

    def __init__(self, value):
        super().__init__(value)

    def serialize(self):
        #TODO
        raise NotImplemented()

    @classmethod
    def from_bytes(cls, *args, **kwargs):
        raise ValueError("tried from_bytes on single byte!")

    @classmethod
    def from_file(cls, file: "NoitaBinFile"):
        ret = file.contents[file.read_pos]
        file.read_pos += 1
        return ret

    def readable_short(self):
        return str(self.value)

    def readable_long(self):
        return str(self.value)


class NoitaBool(NoitaFileSection):
    raw_len = 1

    def __init__(self, value):
        super().__init__(value)

    def serialize(self):
        #TODO
        raise NotImplemented()

    @classmethod
    def from_bytes(cls, *args, **kwargs):
        raise ValueError("tried from_bytes on single byte!")

    @classmethod
    def from_file(cls, file: "NoitaBinFile"):
        ret = file.contents[file.read_pos]
        file.read_pos += 1
        return ret

    def readable_short(self):
        return bool(self.value)

    def readable_long(self):
        return bool(self.value)


class NoitaFloat(NoitaFileSection, float):
    raw_len = 4

    def __init__(self, value):
        super().__init__(value)

    def serialize(self):
        return serialize_float(self.value)

    @classmethod
    def from_bytes(cls, b, byteorder: Literal["little", "big"] = "big"):
        step = 1
        if byteorder == "big":
            step = -1
        return struct.unpack("f", b[::step])[0]

    @classmethod
    def from_file(cls, file: "NoitaBinFile"):
        ret = cls.from_bytes(file.contents[file.read_pos:file.read_pos + 4], 'big')
        file.read_pos += 4
        return ret

    def readable_short(self):
        return f"{self.value:.1f}"

    def readable_long(self):
        return f"{self.value:.5e}"


class NoitaBinFile:
    short_filename: str
    filename: str
    compressed_size: int
    decompressed_size: int
    contents: bytes
    read_pos: int

    def __init__(self, filename):
        self.short_filename = os.path.basename(filename)
        self.filename = filename
        self.read_pos = 0
        self.contents = b''

    def read_file(self, file_input_bytes=b''):
        if file_input_bytes == b'':
            with open(self.filename, "rb") as f:
                file_input_bytes = f.read()
        self.compressed_size = int.from_bytes(file_input_bytes[0:4], 'little')
        #print("compressed size:", self.compressed_size, len(file_input_bytes))
        self.decompressed_size = int.from_bytes(file_input_bytes[4:8], 'little')
        #print("decompressed size:", self.decompressed_size)
        if self.compressed_size == self.decompressed_size:
            self.contents = file_input_bytes[8:]
        else:
            self.contents = fastlz.decompress(file_input_bytes[4:])

    def coords(self):
        try:
            num = int(self.short_filename.split("_")[1].split(".bin")[0])
            coord_x, coord_y = num_to_coords(num)
        except:
            #print(f"file {self.short_filename} is not for a chunk!")
            raise ValueError(f"file {self.short_filename} is not for a chunk!")
        return coord_x, coord_y

    def peek(self, peek_len, peek_start_offset=0):
        return self.contents[self.read_pos+peek_start_offset:self.read_pos+peek_len]

    def read_string(self, no_seek=False, sanity_check_len=500, quiet=False) -> bytes:
        str_len = int.from_bytes(self.contents[self.read_pos:self.read_pos + 4], 'big')
        if str_len > sanity_check_len:
            #if not quiet:
            #    print(f"tried to read a string with len {str_len}")
            #    print(self.peek(50))
            raise ValueError(f"tried to read a string with len {str_len}", ReadableBytes(self.peek(50)), ReadableHex(self.peek(100,-90)))
        end_pos = self.read_pos + 4 + str_len
        str_contents = self.contents[self.read_pos + 4:end_pos]
        if not no_seek:
            self.read_pos = end_pos
        return NoitaString(str_contents)

    def read_nt_string(self, no_seek=False, sanity_check_len=500) -> bytes:
        end_pos = self.read_pos
        for i in range(sanity_check_len):
            if self.contents[self.read_pos+i] == 0:
                end_pos = i
                break
        str_contents = self.contents[self.read_pos:end_pos-1]
        if not no_seek:
            self.read_pos = end_pos
        return str_contents

    def read_until(self, term) -> bytes:
        m = next(re.finditer(term, self.contents[self.read_pos:]))
        print(f"read until {m.end()}")
        return self.skip(m.end())

    def read_int(self, no_seek=False) -> int:
        ret = int.from_bytes(self.contents[self.read_pos:self.read_pos + 4], 'big', signed=True)
        if not no_seek:
            self.read_pos += 4
        return NoitaInt(ret)

    def read_float(self, no_seek=False) -> float:
        ret = struct.unpack("f", self.contents[self.read_pos:self.read_pos + 4][::-1])[0]
        if not no_seek:
            self.read_pos += 4
        return NoitaFloat(ret)

    def read_byte(self, no_seek=False) -> int:
        ret = self.contents[self.read_pos]
        if not no_seek:
            self.read_pos += 1
        return NoitaByte(ret)

    def skip(self, amt, show=False):
        if show:
            skip_contents = self.contents[self.read_pos:self.read_pos+amt]
            print(f"{self.read_pos} skip {amt} {len(skip_contents)} {skip_contents} {skip_contents.hex(' ')}")
        ret = self.contents[self.read_pos:self.read_pos+amt]
        self.read_pos += amt
        return NoitaRaw(ret)

    def __str__(self):
        if hasattr(self, "decompressed_size"):
            return f"NoitaBinFile {self.short_filename} size {len(self.contents)} at {self.read_pos} {100*self.read_pos/self.decompressed_size:3.2f}%"

    def save_decompressed(self):
        size_bytes = int.to_bytes(self.decompressed_size or len(self.contents), 4, 'little')
        with open(self.filename + ".decompressed", "wb") as f:
            f.write(size_bytes + size_bytes + self.contents)

    def save_compressed(self, suffix=""):
        #size_bytes = int.to_bytes(self.decompressed_size or len(self.contents), 4, 'little')
        compressed_contents = fastlz.compress(self.contents)
        compressed_size = int.to_bytes(len(compressed_contents)-4, 4, 'little')
        with open(self.filename + suffix, "wb") as f:
            f.write(compressed_size + compressed_contents)
        return
