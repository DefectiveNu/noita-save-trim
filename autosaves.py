import logging
import os
import sys
from typing import List

from constants import WORLD_PATH, KEEP_ALL_WORLDS_DIST, AGGRO_CLEAN_DIST, ALWAYS_KEEP, ALWAYS_PRUNE, DEBUG
from entity_file import raws_and_strings, Entity, find_next_entity
from pixel_scenes import PixelSceneFile
from tools.conversions import serialize_int, serialize_float, serialize_str, retry_as_float, hex_readable
from tools.coords import chunk_to_num, get_world_from_x
from noita_bin_file import NoitaBinFile
from tools.util import try_strings

path = f"{os.environ['LOCALAPPDATA']}/../LocalLow/Nolla_Games_Noita/save00/world/"
logging.getLogger("entity_file").setLevel("WARNING")


class AutosaveFile(NoitaBinFile):
    def __init__(self, filename):
        super().__init__(filename)
        self.read_file()
        #print(hex_readable(self.peek(100)))
        self.version = self.read_int()  # 1
        self.schema = self.read_string()  # c8ecfb341d22516067569b04563bff9c
        self.e1 = Entity(self, allow_weird=True)
        #print(e1)
        #print(self)
        #print(hex_readable(self.peek(100)))
        if not self.read_pos == len(self.contents):
            logging.error("didn't read whole file, read pos %s len %s diff %s", self.read_pos, len(self.contents), self.read_pos - len(self.contents))
        #find_next_entity(self, e1)
        return


def main():
    filelist = [filepath for filepath in os.listdir(path) if filepath.startswith(".autosave")]
    filelist = [".autosave_world_state"]
    for filename in filelist:
        if "pixel" in filename:
            f = PixelSceneFile(path + filename)
            continue
            #print(f)
            #sys.exit()
        else:
            f = AutosaveFile(path+filename)
            #sys.exit()
            #print(f)
        #print(f"{f.short_filename:10}: {len(f.int_list)} {f.int_list[:100]}")
        #print(f"{f.short_filename:22}: {hex_readable(f.contents[:1000])}")
    #print(hex_readable(f.contents))


if __name__ == '__main__':
    main()
