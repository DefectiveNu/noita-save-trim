import sys
import re
from typing import List

from constants import WORLD_PATH, KEEP_ALL_WORLDS_DIST, AGGRO_CLEAN_DIST, ALWAYS_KEEP, ALWAYS_PRUNE, DEBUG
from tools.conversions import serialize_int, serialize_float, serialize_str, retry_as_float, bytes_to_int
from tools.coords import chunk_to_num, get_world_from_x, num_to_coords
from noita_bin_file import NoitaBinFile
from tools.util import try_strings


class Transform:
    def __init__(self, file: NoitaBinFile):
        self.x = file.read_float()
        self.y = file.read_float()
        self.scale_x = file.read_float()
        self.scale_y = file.read_float()
        self.rotation = file.read_float()

    def __str__(self):
        return f"{self.x, self.y} {self.scale_x, self.scale_y} {self.rotation}"


class Entity:
    def __init__(self, file: NoitaBinFile):
        self.name = file.read_string()
        self.b1 = file.read_byte()
        ##print('name', self.name, self.b1)
        if bytes_to_int(file.peek(4)) > 500:
            print("!! big string! try rewind 1")
            file.read_pos -= 1
        self.ent_file = file.read_string()
        ##print('ent file', self.ent_file)
        self.tags = file.read_string()
        ##print('tags', self.tags)
        self.transform = Transform(file)
        ##print("transform", self.transform)
        self.components = file.read_int()
        ##print("components", self.components)
        # seek next entity
        save_pos = file.read_pos
        ready_next = False
        matches = re.finditer(b'data/entities/.*?..xml', file.contents[file.read_pos:])
        for match in matches:
            target_pos = save_pos + match.start()
            ##print(match.start(), match.end())
            file.read_pos = target_pos - 8  # 4 for ent file length, 5 for name length + null
            ##print("start looking", file.peek(20))
            #while bytes_to_int(file.peek(4)) + 5 + file.read_pos != target_pos and \
            while file.read_pos > target_pos - 100:
                #print("bad name", bytes_to_int(file.peek(4)), file.peek(10))
                if bytes_to_int(file.peek(4)) + 8 + file.read_pos != target_pos:
                    file.read_pos -= 1
                else:
                    ready_next = True
                    break
            if ready_next:
                ##print(f"found next ent at {file.read_pos} match at {target_pos}")
                break
            else:
                print("bad match", file.contents[target_pos-10:10+target_pos + (match.end()-match.start())])
        raw_byte_count = file.read_pos - save_pos
        file.read_pos = save_pos
        if ready_next:
            self.raw = file.skip(raw_byte_count)
        else:
            self.raw = file.skip(len(file.contents)-file.read_pos)

    def __str__(self):
        out = f"{self.__class__} "
        #raws = []
        for k in self.__dict__:
            if k.startswith("raw"):
                #raws.append(f"{k}:{self.__dict__[k].hex(' ', -4)}")
                out += f"{k}:[len {len(self.__dict__[k])}] "
            elif isinstance(self.__dict__[k], list):
                out += f"{k}:[{len(self.__dict__[k])} items] "
            else:
                out += f"{k}:{self.__dict__[k]} "
        #out += " ".join(raws)
        return out


class EntityFile(NoitaBinFile):

    def __init__(self, filename="./save00/ent/entities_39998.bin"):
        super().__init__(filename)
        print()
        print(self.short_filename)
        num = int(self.short_filename.split("entities_")[1].split(".bin")[0])
        coord_x, coord_y = num_to_coords(num)
        print("for coords", coord_x, coord_y)
        self.read_file()
        #try_strings(self, filter = b"data/entities")
        #return
        self.c1 = self.read_int()  # 2
        assert self.c1 == 2
        self.schema = self.read_string()  # c8ecfb341d22516067569b04563bff9c
        assert self.schema == b'c8ecfb341d22516067569b04563bff9c'
        #Entity

        #return
        self.count = self.read_int()
        print('count', self.count)
        if self.count == 0: return
        self.entities = []
        #for i in range(self.count):
        i=0
        while self.read_pos != len(self.contents):
            print(f"=== entity {i} ===")
            i+=1
            ent = Entity(self)
            print(ent)
            if coord_x - 512 <= ent.transform.x <= coord_x:
                print("entity out of bounds! x", coord_x - ent.transform.x)
                raise ValueError
            if coord_y - 512 <= ent.transform.y <= coord_y:
                print("entity out of bounds! y", coord_y - ent.transform.y)
                raise ValueError
            self.entities.append(ent)
        if self.read_pos != len(self.contents):
            print(self.read_pos, len(self.contents), "to go:", len(self.contents) - self.read_pos)
            raise ValueError
        #print(tmp)
        print("dumb ent count", len(self.entities))
        print("file ent count", self.count)
        print("sum component count", sum([ent.components for ent in self.entities]))
        return

        print(len(self.contents))
        for i in range(1):
            out = "\n"
            out += f"i {i}\n"
            out += self.contents[self.read_pos:self.read_pos+50].hex(' ') + "\n"
            out += f"{self.contents[self.read_pos:self.read_pos+50]}" + "\n"
            tmp = self.read_int()
            out += f"{tmp}\n"
            remaining = len(self.contents) - self.read_pos
            candidate_obj_size = remaining/(tmp or 0.00000001)
            out += f"count? {candidate_obj_size} {remaining}\n"
            if candidate_obj_size > 1:
                remainder = (remaining % int(candidate_obj_size))
                out += f"remainder {remainder}\n"
                if 200 > remainder > 0:
                    out += self.contents[0-remainder:].hex(' ') + "\n"
                #if 0 < remainder < 200:
            print(out)
        #try_strings(self)
        return
        self.unk_1 = self.read_int()
        self.count = self.read_int()
        self.items = []
        for i in range(self.count):
            self.items.append(WorldTreePart(self))
        assert self.read_pos == len(self.contents)


def make_component(file: NoitaBinFile):
    component_type = file.read_string()
    return getattr(sys.modules[__name__], component_type.decode())(file)



if __name__ == '__main__':
    #f = EntityFile('./save00/ent/entities_39998.bin')
    #f = EntityFile('./save00/ent/entities_-28006.bin')
    #f = EntityFile('./save00/ent/entities_-28007.bin')
    f = EntityFile('./save00/ent/entities_-26006.bin')
    #f = EntityFile('./save00/ent/entities_3999.bin')
    f = EntityFile('./save00/ent/entities_63858.bin')
    f = EntityFile('./save00/ent/entities_64068.bin')
    f = EntityFile('./save00/ent/entities_16440.bin')
    f = EntityFile('./save00/ent/entities_43532.bin')
