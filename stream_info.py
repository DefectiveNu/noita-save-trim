from constants import WORLD_PATH
from tools.coords import chunk_to_num
from noita_bin_file import NoitaBinFile


class StreamInfoItem:
    a: float
    b: int
    count: int
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


def parse_stream_info():
    file = NoitaBinFile(WORLD_PATH + ".stream_info")
    file.read_file()
    header_version = file.read_int()
    assert header_version == 24
    header_seed = file.read_int()
    print("header_seed", header_seed)
    header_frames_played = file.read_int()
    print("header_frames_played", header_frames_played)
    header_unk1 = file.read_int()
    print("header_unk1", header_unk1)
    #file.debug()
    items = [StreamInfoItem(file)]
    print(items)
    count = items[0].count
    print(file)
    for i in range(1, count):
        item = StreamInfoItem(file)
        items.append(item)
    unk_1 = file.read_int()
    unk_2 = file.read_int()
    unk_3 = file.read_int()
    unk_4 = file.read_int()
    unk_str = file.read_string()  # schema?
    print(file)
    print(unk_1)
    print(unk_2)
    print(unk_3)
    print(unk_4)  # number of items? 9 bytes per item
    print(unk_str)
    print(len(file.contents) - file.read_pos)
    int_freq = {}
    i=0
    #print(file.skip(49).hex(' '))
    print(file.read_byte())
    print(file.read_int())
    print(file.read_int())
    print(file.read_int())
    print(file.read_int())
    print(file.read_int())
    print(file.read_int())
    print(file.read_int())
    print(file.read_int())
    print(file.read_int())
    print(file.read_int())
    print(file.read_int())
    print(file.read_int())
    with open(WORLD_PATH + "files2.txt", "r") as f:
        file_list = [l.strip() for l in f.readlines()]
    while file.read_pos < len(file.contents):
        i += 1
        tmp1 = file.read_int()  # chunk x?
        tmp2 = file.read_int()  # chunk y?
        tmp3 = file.read_byte() # always 1, "generated"?
        num = chunk_to_num(tmp1, tmp2)
        has_area_file = f"area_{num}.bin" in file_list
        has_entity_file = f"entities_{num}.bin" in file_list
        has_world_file = f"world_{tmp1*512}_{tmp2*512}.png_petri" in file_list
        key = f"{has_area_file} {has_entity_file} {has_world_file}"
        if abs(tmp3) > 100_000 or i<10:
            print(tmp1, tmp2, tmp3, i, num)
            print(file.contents[file.read_pos:file.read_pos+9])
        int_freq[key] = int_freq.get(key, 0) + 1
        #pos = 5
        #tmp = file.skip(9).hex(' ')[pos*3:pos*3+2]
        #tmp = file.skip(9).hex(' ')
        #print(tmp)
        #int_freq[tmp] = int_freq.get(tmp,0) + 1
    for k, v in sorted(int_freq.items(), key=lambda i: int_freq[i[0]]):
        print(f"{v: 6d} \"{k}\",")
    print(len(file.contents)-file.read_pos)
    print(file)
    print(i)
    print(file.contents[file.read_pos:])
    #print(file.contents[file.read_pos:])
    return items