from noita_bin_file import NoitaBinFile

from pixel_scenes import PixelScene
from stream_info import StreamInfoItem
from coords import get_world_from_x
from constants import ALWAYS_PRUNE, ALWAYS_KEEP, WORLD_PATH, KEEP_ALL_WORLDS_DIST, AGGRO_CLEAN_DIST


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
    #print("header_unk1", header_unk1)
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
    return items


def should_exclude(item: PixelScene) -> bool:
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
        return True
    if delete_mode == "safe":
        for prune_item in ALWAYS_PRUNE:
            if prune_item in item.mat:
                return True
        return False


def process_pixel_scenes():
    file = NoitaBinFile(WORLD_PATH + "world_pixel_scenes.bin")
    file.read_file()
    header_version = file.read_int()
    assert header_version == 3
    header_unk = file.read_int()
    #print("header_unk", header_unk)
    header_count = file.read_int()
    #print("header_count", header_count)

    items_all = []
    items = []
    partial_contents_g1 = []
    for i in range(header_count):
        start_pos = file.read_pos
        item = PixelScene(file)
        items_all.append(item)
        end_pos = file.read_pos
        if not should_exclude(item):
            items.append(item)
            partial_contents_g1.append(file.contents[start_pos:end_pos])
    break_index = file.read_pos
    count_2 = file.read_int()
    #print("count_2", count_2)
    partial_contents_g2 = []
    for i in range(count_2):
        start_pos = file.read_pos
        item = PixelScene(file)
        items_all.append(item)
        end_pos = file.read_pos
        if not should_exclude(item):
            items.append(item)
            partial_contents_g2.append(file.contents[start_pos:end_pos])
    reconstructed_contents = int.to_bytes(3, 4, 'big')  # header version
    reconstructed_contents += int.to_bytes(header_unk, 4, 'big')  # unk1
    reconstructed_contents += int.to_bytes(len(partial_contents_g1), 4, 'big')  # count 1
    reconstructed_contents += b''.join(partial_contents_g1)
    reconstructed_contents += int.to_bytes(len(partial_contents_g2), 4, 'big')  # count 2
    reconstructed_contents += b''.join(partial_contents_g2)
    reconstructed_contents += file.contents[file.read_pos:]
    file.contents = reconstructed_contents
    file.save_compressed()
    return items_all, items


def main():
    #parse_stream_info()
    preprune_items, prune_items = process_pixel_scenes()
    print(f"prune {len(preprune_items)} to {len(prune_items)}")
    #print("=-=-=-=-=-=-=-=")
    #pixel_scene_stats(prune_items)


if __name__ == '__main__':
    main()
