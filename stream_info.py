from typing import List

from constants import WORLD_PATH
from tools.conversions import serialize_int, serialize_float, serialize_str
from tools.coords import chunk_to_num
from noita_bin_file import NoitaBinFile


class StreamInfoItem:
    a: float
    b: int
    count: int  # "root" item has count, all others are 0
    x: float
    y: float
    path: bytes

    def __init__(self, file: NoitaBinFile):
        self.a = file.read_float()
        self.b = file.read_int()
        self.count = file.read_int()
        self.x = file.read_float()
        self.y = file.read_float()
        self.path = file.read_string()

    def __str__(self):
        return f"StreamInfoItem({self.x}, {self.y}) count {self.count} path {self.path[:500]} {self.a} {self.b}"

    def __repr__(self):
        return str(self)

    def __bytes__(self):
        ret = serialize_float(self.a)
        ret += serialize_int(self.b)
        ret += serialize_int(self.count)
        ret += serialize_float(self.x)
        ret += serialize_float(self.y)
        ret += serialize_str(self.path)
        return ret


class ChunkStatus:
    chunk_x: int
    chunk_y: int
    chunk_status: int  # 1 byte, always 1

    def __init__(self, file: NoitaBinFile):
        self.chunk_x = file.read_int()
        self.chunk_y = file.read_int()
        self.chunk_status = file.read_byte()

    def __bytes__(self):
        ret = serialize_int(self.chunk_x)
        ret += serialize_int(self.chunk_y)
        ret += serialize_int(self.chunk_status, 1)
        return ret


class StreamInfoFile(NoitaBinFile):
    version: int
    seed: int
    frames_played: int
    header_unk_1: int
    items: List[StreamInfoItem]
    unk_1: int
    unk_2: int
    unk_3: int
    count_chunk_status: int
    schema: bytes
    gap_1: bytes
    chunk_status_items: List[ChunkStatus]

    def __init__(self, filename=WORLD_PATH + ".stream_info"):
        super().__init__(filename)
        self.read_file()
        self.version = self.read_int()
        assert self.version == 24
        self.seed = self.read_int()
        self.frames_played = self.read_int()
        self.header_unk_1 = self.read_int()
        self.items = [StreamInfoItem(self)]
        count = self.items[0].count
        for i in range(1, count):
            self.items.append(StreamInfoItem(self))
        self.unk_1 = self.read_int()
        self.unk_2 = self.read_int()
        self.unk_3 = self.read_int()
        self.count_chunk_status = self.read_int()  # number of items? 9 bytes per item
        self.schema = self.read_string()  # c8ecfb341d22516067569b04563bff9c
        self.gap_1 = self.skip(49)
        self.chunk_status_items = []
        for i in range(self.count_chunk_status):
            self.chunk_status_items.append(ChunkStatus(self))
        if self.contents[self.read_pos:]:  # check for unread contents
            raise Exception("file not fully processed")

    def save(self):
        self.read_pos = 0
        self.contents = serialize_int(self.version)
        self.contents += serialize_int(self.seed)
        self.contents += serialize_int(self.frames_played)
        self.contents += serialize_int(self.header_unk_1)
        self.contents += b''.join([bytes(sii) for sii in self.items])
        self.contents += serialize_int(self.unk_1)
        self.contents += serialize_int(self.unk_2)
        self.contents += serialize_int(self.unk_3)
        self.contents += serialize_int(self.count_chunk_status)
        self.contents += serialize_str(self.schema)
        self.contents += self.gap_1
        self.contents += b''.join([bytes(csi) for csi in self.chunk_status_items])
        self.save_compressed()
