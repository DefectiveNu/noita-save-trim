import os
from typing import List

from constants import WORLD_PATH, KEEP_ALL_WORLDS_DIST, AGGRO_CLEAN_DIST, ALWAYS_KEEP, ALWAYS_PRUNE, DEBUG
from entity_file import raws_and_strings
from tools.conversions import serialize_int, serialize_float, serialize_str, retry_as_float, hex_readable
from tools.coords import chunk_to_num, get_world_from_x
from noita_bin_file import NoitaBinFile
from tools.util import try_strings

path = "./save00/small_sim/"


class WorldSimPart:
    def __init__(self, file: NoitaBinFile):
        self.index = file.read_int()
        self.unk = file.skip(64)


class WorldSimFile(NoitaBinFile):

    def __init__(self, filename):
        super().__init__(filename)
        self.read_file()
        #self.int_list = raws_and_strings(self, len(self.contents), "component")
        self.int_list= []
        while self.read_pos < len(self.contents):
            try:
                self.int_list.append(self.read_int())
            except:
                return
        return
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
    filelist = [filepath for filepath in os.listdir(path) if filepath.endswith(".bin")]
    for i, filename in enumerate(filelist):
        f = WorldSimFile(path+filename)
        print(f"{f.short_filename:10}: {len(f.int_list)} {f.int_list}")
        #print(f"{f.short_filename:10}: {hex_readable(f.contents)}")
    #print(hex_readable(f.contents))
