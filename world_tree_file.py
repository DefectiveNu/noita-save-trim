import sys
from typing import List

from constants import WORLD_PATH, KEEP_ALL_WORLDS_DIST, AGGRO_CLEAN_DIST, ALWAYS_KEEP, ALWAYS_PRUNE, DEBUG
from tools.conversions import serialize_int, serialize_float, serialize_str, retry_as_float
from tools.coords import chunk_to_num, get_world_from_x
from noita_bin_file import NoitaBinFile
from tools.util import try_strings


class WorldTreePart:
    def __init__(self, file: NoitaBinFile):
        self.index = file.read_int()
        self.unk = file.skip(64)


class WorldTreeFile(NoitaBinFile):

    def __init__(self, filename=WORLD_PATH + "world_tree.bin"):
        super().__init__(filename)
        self.read_file()
        self.unk_1 = self.read_int()
        self.count = self.read_int()
        self.items = []
        for i in range(self.count):
            self.items.append(WorldTreePart(self))
        assert self.read_pos == len(self.contents)


if __name__ == '__main__':
    f = WorldTreeFile()
    print(f.count)
    for i in f.items:
        print(i.unk.hex(' '))
