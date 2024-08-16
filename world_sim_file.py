from typing import List

from constants import WORLD_PATH, KEEP_ALL_WORLDS_DIST, AGGRO_CLEAN_DIST, ALWAYS_KEEP, ALWAYS_PRUNE, DEBUG
from tools.conversions import serialize_int, serialize_float, serialize_str, retry_as_float
from tools.coords import chunk_to_num, get_world_from_x
from noita_bin_file import NoitaBinFile
from tools.util import try_strings


class WorldSimPart:
    def __init__(self, file: NoitaBinFile):
        self.index = file.read_int()
        self.unk = file.skip(64)


class WorldSimFile(NoitaBinFile):

    def __init__(self, filename=WORLD_PATH + "world_sim.bin"):
        super().__init__(filename)
        self.read_file()
        print(len(self.contents))
        for i in range(30):
            out = "\n"
            out += f"i {i}\n"
            out += self.contents[self.read_pos:self.read_pos+50].hex(' ') + "\n"
            tmp = self.read_int()
            out += f"{tmp}\n"
            remaining = len(self.contents) - self.read_pos
            candidate_obj_size = remaining/tmp
            out += f"count? {candidate_obj_size} {remaining}\n"
            if candidate_obj_size > 1:
                remainder = (remaining % int(candidate_obj_size))
                out += f"remainder {remainder}\n"
                if remainder > 0:
                    out += self.contents[0-remainder:].hex(' ') + "\n"
                if 0 < remainder < 20:
                    print(out)
        #try_strings(self)
        return
        self.unk_1 = self.read_int()
        self.count = self.read_int()
        self.items = []
        for i in range(self.count):
            self.items.append(WorldTreePart(self))
        assert self.read_pos == len(self.contents)


if __name__ == '__main__':
    f = WorldSimFile()
