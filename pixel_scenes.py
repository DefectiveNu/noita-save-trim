from pprint import pprint

from constants import WORLD_PATH, KEEP_ALL_WORLDS_DIST, AGGRO_CLEAN_DIST, ALWAYS_KEEP, ALWAYS_PRUNE, DEBUG
from tools.coords import get_world_from_x
from noita_bin_file import NoitaBinFile
from typing import List

from tools.conversions import serialize_int, serialize_str, bytes_to_int, bytes_to_float


class PixelScene:
    x: int
    y: int
    mat: bytes
    visual: bytes
    bg: bytes
    gap_1: bytes
    unk1: bytes
    gap_2: bytes
    n_extra: int
    extra: bytes
    extra_parsed: List

    def __init__(self, file: NoitaBinFile):
        #print(file)
        self.x = file.read_int()
        self.y = file.read_int()
        self.mat = file.read_string()
        self.visual = file.read_string()
        self.bg = file.read_string()
        self.gap_1 = file.skip(6)
        self.unk1 = file.read_string()  # entity?
        self.gap_2 = file.skip(5)
        self.extra = b''
        self.extra_parsed = []
        try:
            self.n_extra = file.read_byte()
            if self.n_extra:
                self.extra = file.skip(self.n_extra * 8)
                for x in range(self.n_extra):
                    offset = x * 8
                    int1 = bytes_to_int(self.extra[offset:offset+4])
                    int2 = bytes_to_int(self.extra[offset+4:offset+8])
                    float1 = bytes_to_float(self.extra[offset:offset+4])
                    float2 = bytes_to_float(self.extra[offset+4:offset+8])
                    #int64 = bytes_to_int(extra[offset:offset+8])
                    #float64 = bytes_to_float(extra[offset:offset+8])
                    self.extra_parsed.append(((int1, int2), (float1, float2)))
                #self.extra = extra.hex(' ')

        except IndexError:
            print(f"Index error at {file.read_pos} {self}")
        #if self.unk1:
        #    print("unk1", self)

    def __str__(self):
        return f"PixelScene({self.x}, {self.y}) mat {self.mat[:500]} visual {self.visual} bg {self.bg} entity {self.unk1}"

    #def __repr__(self):
    #    return str(self)

    def __bytes__(self):
        ret = serialize_int(self.x)
        ret += serialize_int(self.y)
        ret += serialize_str(self.mat)
        ret += serialize_str(self.visual)
        ret += serialize_str(self.bg)
        ret += self.gap_1
        ret += serialize_str(self.unk1)
        ret += self.gap_2
        ret += serialize_int(self.n_extra, 1)
        ret += self.extra
        return ret


class PixelSceneFile(NoitaBinFile):
    header_version: int
    header_unk: int
    count_1: int
    scenes_1: List[PixelScene]
    count_2: int
    scenes_2: List[PixelScene]
    footer: int  # always 4 nulls? maybe "count_3"?

    def __init__(self, filename=WORLD_PATH + "world_pixel_scenes.bin"):
        super().__init__(filename)
        self.read_file()
        self.header_version = self.read_int()
        assert self.header_version == 3
        self.header_unk = self.read_int()
        self.count_1 = self.read_int()
        self.scenes_1 = []
        for i in range(self.count_1):
            self.scenes_1.append(PixelScene(self))
        self.count_2 = self.read_int()
        self.scenes_2 = []
        for i in range(self.count_2):
            self.scenes_2.append(PixelScene(self))
        self.footer = self.read_int()
        if self.contents[self.read_pos:]:  # check for unread contents
            raise Exception("file not fully processed")

    def get_world_width(self):
        landmarks = set()
        for item in self.scenes_1 + self.scenes_2:
            if item.bg == b'data/biome_impl/temple/altar_background.png':
                landmarks.add(item.x)
        landmark_x = sorted(landmarks)
        landmark_dist = set()
        last_pos = landmark_x[0]
        for lm in landmark_x[1:]:
            landmark_dist.add(lm - last_pos)
            last_pos = lm
        return int(min(landmark_dist) / 512)

    def trim(self):
        self.scenes_1 = [scene for scene in self.scenes_1 if not trim_filter(scene)]
        self.count_1 = len(self.scenes_1)
        self.scenes_2 = [scene for scene in self.scenes_2 if not trim_filter(scene)]
        self.count_2 = len(self.scenes_2)

    def save(self):
        self.read_pos = 0
        self.contents = serialize_int(self.header_version)
        self.contents += serialize_int(self.header_unk)
        self.contents += serialize_int(len(self.scenes_1))  # count 1
        self.contents += b''.join([bytes(scene) for scene in self.scenes_1])
        self.contents += serialize_int(len(self.scenes_2))  # count 2
        self.contents += b''.join([bytes(scene) for scene in self.scenes_2])
        self.contents += serialize_int(self.footer)
        self.save_compressed()


def trim_filter(item: PixelScene) -> bool:
    world = get_world_from_x(item.x)
    if abs(world) <= KEEP_ALL_WORLDS_DIST:
        return False
    if abs(world) <= AGGRO_CLEAN_DIST:
        delete_mode = "safe"
    else:
        delete_mode = "agro"
    all_scan = ["mat", "visual", "bg", "unk1"]
    if delete_mode == "agro":
        for inc_item in ALWAYS_KEEP:
            for prop in all_scan:
                if inc_item in getattr(item, prop):
                    return False
        if DEBUG: print(f"prune {world} {item} by agro")
        return True
    if delete_mode == "safe":
        for prune_item in ALWAYS_PRUNE:
            if prune_item in item.mat:
                if DEBUG: print(f"prune {world} {item} by {prune_item}")
                return True
        return False
