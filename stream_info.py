from typing import List

from constants import WORLD_PATH, KEEP_ALL_WORLDS_DIST, AGGRO_CLEAN_DIST, ALWAYS_KEEP, ALWAYS_PRUNE, DEBUG
from tools.conversions import serialize_int, serialize_float, serialize_str
from tools.coords import chunk_to_num, get_world_from_x
from noita_bin_file import NoitaBinFile


class StreamInfoItem:
    a: float
    b: int
    count: int  # "root" item has count, all others are 0
    x: float
    y: float
    path: bytes

    def __init__(
        self,
        file: NoitaBinFile = None,
        a: float = None,
        b: int = None,
        x: float = None,
        y: float = None,
        path: bytes = None
    ):
        if file is not None:
            self.a = file.read_float()
            self.b = file.read_int()
            self.count = file.read_int()
            self.x = file.read_float()
            self.y = file.read_float()
            self.path = file.read_string()
        else:
            self.a = float(a)
            self.b = int(b)
            self.count = 0
            self.x = float(x)
            self.y = float(y)
            if isinstance(path, str):
                path = path.encode()
            self.path = path

    def __str__(self):
        return f"StreamInfoItem({self.x}, {self.y}) {self.path[:500].decode(errors='ignore')}"

    #def __repr__(self):
    #    return f"StreamInfoItem({self.x}, {self.y}) count {self.count} path {self.path[:500]} {self.a} {self.b} {hex(id(self))}"

    def __bytes__(self):
        ret = serialize_float(self.a)
        ret += serialize_int(self.b)
        ret += serialize_int(self.count)
        ret += serialize_float(self.x)
        ret += serialize_float(self.y)
        ret += serialize_str(self.path)
        return ret

    def __eq__(self, other):
        return (
                self.a == other.a and
                self.b == other.b and
                # self.count == other.count and  # should be a header but who's counting (boo)
                self.x == other.x and
                self.y == other.y and
                self.path == other.path
        )

    def debug(self):
        print(f"a:{self.a} b:{self.b} count:{self.count} ({self.x},{self.y}) {self.path}")
        #print(f"StreamInfoItem(None, {self.a}, {self.b}, {self.x}, {self.y}, {self.path}),")


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

    def __eq__(self, other):
        return (
            self.chunk_x == other[0] and
            self.chunk_y == other[1]
        )

    def __str__(self):
        return f"ChunkStatus({self.chunk_x}, {self.chunk_y}) {self.chunk_status}"

    def debug(self):
        print(f"({self.chunk_x},{self.chunk_y}) {self.chunk_status}")


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

    def trim(self):
        if not trim_filter(self.items[0]):
            self.items = [self.items[0]] + [item for item in self.items if not trim_filter(item)]
        else:
            self.items = [item for item in self.items if not trim_filter(item)]

    def save(self, suffix=""):
        self.read_pos = 0
        self.items[0].count = len(self.items)
        for item in self.items[1:]:
            item.count = 0
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
        self.save_compressed(suffix=suffix)

    def debug(self):
        print("version", self.version)
        print("seed", self.seed)
        print("frames_played", self.frames_played)
        print("header_unk_1", self.header_unk_1)
        for item in self.items:
            item.debug()
        print("unk_1", self.unk_1)
        print("unk_2", self.unk_2)
        print("unk_3", self.unk_3)
        print("count_chunk_status", self.count_chunk_status)
        print("schema", self.schema)
        print("gap_1", self.gap_1)
        print("gap_1", self.gap_1.hex(' '))
        for csi in self.chunk_status_items:
            csi.debug()


def trim_filter(item: StreamInfoItem) -> bool:
    world = get_world_from_x(item.x)
    if abs(world) <= KEEP_ALL_WORLDS_DIST:
        return False
    if abs(world) <= AGGRO_CLEAN_DIST:
        delete_mode = "safe"
    else:
        delete_mode = "agro"
    if delete_mode == "agro":
        for inc_item in ALWAYS_KEEP:
            if inc_item in item.path:
                return False
        if DEBUG: print(f"prune {world} {item} by agro")
        return True
    if delete_mode == "safe":
        for prune_item in ALWAYS_PRUNE:
            if prune_item in item.path:
                if DEBUG: print(f"prune {world} {item} by {prune_item}")
                return True
        return False
