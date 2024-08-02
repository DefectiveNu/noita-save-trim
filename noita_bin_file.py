import fastlz
import struct
import os


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

    def read_file(self):
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

    def read_string(self, no_seek=False) -> bytes:
        str_len = int.from_bytes(self.contents[self.read_pos:self.read_pos + 4], 'big')
        end_pos = self.read_pos + 4 + str_len
        str_contents = self.contents[self.read_pos + 4:end_pos]
        if not no_seek:
            self.read_pos = end_pos
        return str_contents

    def read_int(self, no_seek=False) -> int:
        ret = int.from_bytes(self.contents[self.read_pos:self.read_pos + 4], 'big', signed=True)
        if not no_seek:
            self.read_pos += 4
        return ret

    def read_float(self, no_seek=False) -> float:
        ret = struct.unpack("f", self.contents[self.read_pos:self.read_pos + 4][::-1])[0]
        if not no_seek:
            self.read_pos += 4
        return ret

    def read_byte(self, no_seek=False) -> int:
        ret = self.contents[self.read_pos]
        if not no_seek:
            self.read_pos += 1
        return ret

    def skip(self, amt, show=False):
        if show:
            skip_contents = self.contents[self.read_pos:self.read_pos+amt]
            print(f"{self.read_pos} skip {amt} {len(skip_contents)} {skip_contents} {skip_contents.hex(' ')}")
        ret = self.contents[self.read_pos:self.read_pos+amt]
        self.read_pos += amt
        return ret

    def __str__(self):
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
