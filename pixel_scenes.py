from noita_bin_file import NoitaBinFile, bytes_to_int, bytes_to_float
from typing import List


class PixelScene:
    x: float
    y: float
    mat: bytes
    visual: bytes
    bg: bytes
    gap_1: bytes
    unk1: bytes
    gap_2: bytes
    extra: str
    extra_parsed: List

    def __init__(self, file: NoitaBinFile):
        #print(file)
        self.x = file.read_int()
        self.y = file.read_int()
        self.mat = file.read_string()
        self.visual = file.read_string()
        self.bg = file.read_string()
        self.gap_1 = file.skip(6).hex(' ')
        self.unk1 = file.read_string()  # entity?
        self.gap_2 = file.skip(5).hex(' ')
        self.extra = ''
        self.extra_parsed = []
        try:
            n_extra = file.read_byte()
            if n_extra:
                extra = file.skip(n_extra * 8)
                for x in range(n_extra):
                    offset = x * 8
                    int1 = bytes_to_int(extra[offset:offset+4])
                    int2 = bytes_to_int(extra[offset+4:offset+8])
                    float1 = bytes_to_float(extra[offset:offset+4])
                    float2 = bytes_to_float(extra[offset+4:offset+8])
                    #int64 = bytes_to_int(extra[offset:offset+8])
                    #float64 = bytes_to_float(extra[offset:offset+8])
                    self.extra_parsed.append(((int1, int2), (float1, float2)))
                self.extra = extra.hex(' ')

        except IndexError:
            print(f"Index error at {file.read_pos} {self}")
        #if self.unk1:
        #    print("unk1", self)

    def __str__(self):
        return f"PixelScene({self.x}, {self.y}) mat {self.mat[:500]} visual {self.visual} bg {self.bg} {self.unk1}"

    def __repr__(self):
        return str(self)