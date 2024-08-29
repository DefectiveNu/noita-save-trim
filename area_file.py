import math
import os
import sys
from json import JSONEncoder
from pprint import pprint
from time import sleep
from typing import List, Type

from constants import WORLD_PATH, KEEP_ALL_WORLDS_DIST, AGGRO_CLEAN_DIST, ALWAYS_KEEP, ALWAYS_PRUNE, DEBUG
from tools.conversions import hex_readable, next_string, is_valid_string, ReadableHex, ReadableBytes, BytesToPixels, \
    bytes_to_int, bytes_to_float, readable_bytes, retry_as_float
from tools.coords import chunk_to_num, get_world_from_x, num_to_coords, coords_to_num, get_chunk
from noita_bin_file import NoitaBinFile
import logging
import coloredlogs
from entity_file import raws_and_strings


coloredlogs.install(level='WARNING', fmt='%(levelname)s %(message)s', isatty=True, level_styles={
    'debug': {'color': 'blue'},
    'info': {'color': 'green'},
    'warning': {'color': 'yellow'},
    'error': {'color': 'red'},
})
#coloredlogs.install(fmt='%(asctime)s,%(msecs)03d %(hostname)s %(name)s[%(process)d] %(levelname)s %(message)s')
log = logging.getLogger("area_file")


class AreaObj:
    def __init__(self, file, coord_list, unk2, unk3):
        self.file = file
        self.coord_list = coord_list
        self.unk2 = unk2
        self.unk3 = unk3
        global file_num_coords
        if file not in file_num_coords:
            file_num_coords[file] = {}

        file_num_coords[file][len(coord_list)] = file_num_coords[file].get(len(coord_list), 0) + 1

    def __str__(self):
        return f"{self.file.decode():80} {len(self.coord_list):2} {self.unk2} {retry_as_float(self.unk2)} {self.unk3}"

    def __repr__(self):
        return self.__str__()


class AreaFile(NoitaBinFile):
    def __init__(self, filename):
        super().__init__(filename)
        log.debug(self.short_filename)
        self.read_file()
        self.sign = self.read_int()  # 0 or -1
        assert self.sign in [0, -1]
        self.num = self.read_int()  # area_{num}.bin  includes sign
        assert self.num == int(self.short_filename.split("area_")[1].split(".bin")[0])
        self.version = self.read_int()
        assert self.version == 1
        self.count = self.read_int()  # number of x,y,idx entries
        # max(idx) appears to be the number of file,unk,unk entries after this, with idx=0 mapping to ???
        # areas with count=1 never have items with idx=0 (always 1, and 1 file entry) ???
        # idx usually is sorted (asc) but sometimes, idx=0 appears in the middle ???
        # longshot: idx=0 is "params for all (subsequent)"
        self.buffer = self.read_int()
        assert self.buffer == 0
        self.items = []
        if self.count != 20:
            return
        tmp_coords = {}
        tmp_coords_global = []
        for i in range(self.count):
            x = self.read_float()
            y = self.read_float()
            idx = self.read_int()
            if idx == 0:
                tmp_coords_global.append((x, y))
            assert coords_to_num(x, y) == self.num
            if idx not in tmp_coords:
                tmp_coords[idx] = tmp_coords_global.copy()
            tmp_coords[idx].append((x, y))
        self._pos_after_r1 = self.read_pos
        count_files = max(tmp_coords.keys())
        self.items.append(AreaObj(b'', tmp_coords.get(0, []), 0, 0))
        for i in range(count_files):
            file = self.read_string()
            unk2 = self.read_int()
            unk3 = self.read_int()
            self.items.append(AreaObj(file, tmp_coords[i+1], unk2, unk3))

            '''if not self.read_pos <= len(self.contents):
                print(self)
                return'''
        assert self.read_pos == len(self.contents)
        #print(self)
        #self.auto = raws_and_strings(self, 10_000, "component")

    def __str__(self):
        raw_items = []
        rpos = 20
        while rpos < self._pos_after_r1:
            f1 = bytes_to_float(self.contents[rpos:rpos+4])
            f2 = bytes_to_float(self.contents[rpos+4:rpos+8])
            idx = bytes_to_int(self.contents[rpos+8:rpos+12])
            raw_items.append(f"{hex_readable(self.contents[rpos:rpos+12])}  {f1} {f2} {idx or '!!!!!'}")
            rpos += 12
        ri = '\n'.join(raw_items)
        return f"{self.num} count:{self.count}  {self.items}\n{ri}\n{readable_bytes(self.contents[self._pos_after_r1:])}"

    def read_string_maybe(self):
        start_pos = self.read_pos
        try:
            tmp = self.read_string()
            if not is_valid_string(tmp):
                raise ValueError(f"bad string {tmp}")
            tmp = tmp.decode()
        except:
            self.read_pos = start_pos
            #tmp = self.read_float()
            tmp = None
        return tmp


def hex_readable_auto(lst: list):
    out = ""
    log.debug(lst)
    for item in lst:
        log.debug(item)
        if is_valid_string(item):
            i = item.decode() + "           "
            out += f"[{i[:11]}]"
        else:
            #out += item.hex(' ')
            out += hex_readable(item)
    return out

def num_strings(lst: list):
    out = 0
    for item in lst:
        if is_valid_string(item):
            out += 1
        else:
            pass
    return out


file_num_coords = {}
def main():
    path = "./save00/ent_36/"
    log.setLevel("WARNING")
    filelist = [filepath for filepath in os.listdir(path) if filepath.startswith("area_")]
    for i in range(len(filelist)):
        af = AreaFile(path+filelist[i])
        for item in af.items:
            print(f"{af.num:10}  {item}")
    pprint(file_num_coords)
    print(len(file_num_coords[b'']))
    max_different_param_count = 0
    param_count_stats = {}
    for k in file_num_coords:
        param_count_entries = len(file_num_coords[k])
        param_count_stats[param_count_entries] = param_count_stats.get(param_count_entries, 0) + 1
    for k in sorted(param_count_stats.keys()):
        print(k, "." * param_count_stats[k])
    return
    for i in range(len(filelist)):
        af = AreaFile(path+filelist[i])
        hra = hex_readable_auto(af.auto)
        if len(af.contents) > 20 and af.count > 0:
            print(f"{af.short_filename:20} count:{af.count:3} ns:{num_strings(af.auto):4}  {af.items}")
            #print(f"raw  {af.short_filename:20} {hex_readable(af.contents[20:])}")
            #print(f"auto {af.short_filename:20} {num_strings(af.auto):5}  {hex_readable(af.header)} {af.count: 3d} {hex_readable(af.buffer)} {hra}")
            '''x = bytes_to_float(af.contents[20:24])
            y = bytes_to_float(af.contents[24:28])
            print(f"i1 {af.short_filename:20} {num} {bytes_to_float(af.contents[20:24]): 15.2f} {bytes_to_float(af.contents[24:28]): 15.2f}")'''
            #print(f"i1 {af.short_filename:20} {af.x:10.0f},{af.y:10.0f} count:{af.count:3} ns:{num_strings(af.auto):5} unk1:{af.unk1:2} {str(af.str1):80} {af.x1:20.2f} {af.y1:20.2f} {hex_readable_auto(af.auto)}")
            #print(f"auto {af.short_filename:20} {num_strings(af.auto):5} {af.count: 3d} {hra}")
        #print(f"auto {len(hra)/(af.count or 1)}  {af.short_filename:20} {hex_readable(af.header)} {af.count: 3d} {hex_readable(af.buffer)} {hra}")
        #print(f"auto {af.short_filename:20} {num_strings(af.auto):5} {hex_readable(af.header)} {af.count: 3d} {hex_readable(af.buffer)} {hra}")
    sys.exit()
    start = 0
    log.setLevel("WARNING")


if __name__ == '__main__':
    main()
    sys.exit()
    import cProfile
    p = cProfile.run('main()', 'entity_profile_info')
    print('done')
    #main()