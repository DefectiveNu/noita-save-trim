import argparse
import os
import re
from pprint import pprint

from constants import WORLD_PATH
from noita_bin_file import NoitaBinFile
from stream_info import StreamInfoFile, StreamInfoItem
from pixel_scenes import PixelSceneFile
from tools.coords import num_to_coords, get_world_from_x
from tools.stats import stream_info_stats

MERGE_ITEMS = [
    b'data/biome_impl/acidtank',
    b'data/biome_impl/bunker',
    b'data/biome_impl/dragoncave',
    b'data/biome_impl/essenceroom',
    b'data/biome_impl/excavationsite/cube_chamber',
    b'data/biome_impl/fishing_hut',
    b'data/biome_impl/greed_treasure',
    b'data/biome_impl/lavalake_racing',
    # b'data/biome_impl/liquidcave/background_panel',
    b'data/biome_impl/mountain/hall',
    b'data/biome_impl/mountain/left_entrance',
    b'data/biome_impl/mountain/left_stub',
    b'data/biome_impl/mountain/right',
    b'data/biome_impl/orbroom',
    # b'data/biome_impl/pillars/pillar',  # unsure if safe
    b'data/biome_impl/pyramid/entrance',
    b'data/biome_impl/pyramid/top',
    b'data/biome_impl/pyramid/',
    # b'data/biome_impl/rainforest/plantlife',
    # b'data/biome_impl/rainforest/hut',
    b'data/biome_impl/robot_egg',
    b'data/biome_impl/secret_lab',
    # b'data/biome_impl/snowcastle/bedroom',
    b'data/biome_impl/snowcastle/forge',
    # b'data/biome_impl/snowcastle/greenhouse',
    b'data/biome_impl/snowcastle/hourglass',
    # b'data/biome_impl/snowcastle/paneling',
    # b'data/biome_impl/snowcastle/pod',
    b'data/biome_impl/snowcastle/side_cavern',
    # b'data/biome_impl/snowcastle/bar',
    # b'data/biome_impl/snowcastle/drill',
    # b'data/biome_impl/snowcave/snowcastle',
    # b'data/biome_impl/snowcave/puzzle_capsule',
    # b'data/biome_impl/snowcave/tinyobservatory',
    # b'data/biome_impl/snowcave/verticalobservatory',
    # b'data/biome_impl/snowcave/horizontalobservatory',
    # b'data/biome_impl/snowcave/receptacle_water',
    # b'data/biome_impl/spliced/boss_arena/',
    b'data/biome_impl/spliced/lake_statue/',
    b'data/biome_impl/spliced/lavalake_pit_bottom/',
    b'data/biome_impl/spliced/tree/',
    b'data/biome_impl/spliced/watercave/',
    b'data/biome_impl/temple/altar',
    # b'data/biome_impl/vault/brain_room',
    # b'data/biome_impl/vault/catwalk',
    # b'data/biome_impl/vault/lab',
    # b'data/biome_impl/vault/lab_puzzle',
    # b'data/biome_impl/vault/electric_tunnel',
    b'data/biome_impl/wizardcave_entrance',
    # b'data/biome_impl/coalmine/oiltank_puzzle',
]

# boss (W0 only) is in WPS only, not SI
PYRAMID_STRUCTURE = [
    StreamInfoItem(None, 101.0,            0,  8128.0,   161.0, b'data/weather_gfx/limit_y/background_pyramid.png'),
    StreamInfoItem(None, 101.0,            0, 11200.0,   161.0, b'data/weather_gfx/limit_y/background_pyramid.png'),  # ambiguous, can't use to anchor
    StreamInfoItem(None, 99.9000015258789, 0,  8192.0,     0.0, b'data/biome_impl/pyramid/left_background.png'),
    StreamInfoItem(None, 50.0,             0,  8704.0,  -512.0, b'data/biome_impl/pyramid/entrance_background.png'),
    StreamInfoItem(None, 99.9000015258789, 0,  9216.0, -1024.0, b'data/biome_impl/pyramid/left_background.png'),
    StreamInfoItem(None, 99.9000015258789, 0, 10240.0, -1024.0, b'data/biome_impl/pyramid/right_background.png'),
    StreamInfoItem(None, 99.9000015258789, 0, 10752.0,  -512.0, b'data/biome_impl/pyramid/right_background.png'),
    StreamInfoItem(None, 99.9000015258789, 0, 11264.0,     0.0, b'data/biome_impl/pyramid/right_background.png'),
    StreamInfoItem(None, 50.0,             0,  9728.0, -1536.0, b'data/biome_impl/pyramid/top_background.png'),
    StreamInfoItem(None, 40.0,             0,  9216.0,  -512.0, b'data/weather_gfx/background_pyramid.png'),
    StreamInfoItem(None, 40.0,             0,  9216.0,  -256.0, b'data/weather_gfx/background_pyramid.png'),
]

PYRAMID_PATHS = [item.path for item in PYRAMID_STRUCTURE]


def rebuild_pyramid(si_file: StreamInfoFile):
    # could adapt to regen other worlds...
    # TODO: check chunk status before adding
    world_target = 0
    w0_items = [item for item in si_file.items if get_world_from_x(item.x) == world_target]
    structure_matched_item = item = None
    for item in w0_items:
        if item.path in PYRAMID_PATHS and b'limit_y' not in item.path:
            structure_matched_item = next(si for si in PYRAMID_STRUCTURE if si.path == item.path and si.y == item.y)
            print("match item", item)
            break
    if structure_matched_item is None or item is None:
        print(f"can't rebuild pyramid for world {world_target}: nothing to work with")
    else:
        offset_x = item.x - structure_matched_item.x
        print(f"rebuild world {world_target} pyramid, displaced by {offset_x}")
        for psi in PYRAMID_STRUCTURE:
            psi.x += offset_x
            if psi not in si_file.items:
                print("add item", psi)
                si_file.items.append(psi)
            else:
                print("skip item", psi)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rebuild-pyramid", action='store_true')
    do_rebuild_pyramid = parser.parse_args().rebuild_pyramid
    si_file = StreamInfoFile()
    wps_file = PixelSceneFile()
    wps_bg_items = [item for item in wps_file.scenes_1 + wps_file.scenes_2 if any(x in item.bg for x in MERGE_ITEMS)]
    #pprint(wps_bg_items)
    print("wps items", len(wps_bg_items))
    print("si items", len(si_file.items))
    merged_items = 0
    skipped_items = 0
    for wps_bg in wps_bg_items:
        a = 50.0
        b = 0
        if b"snowcastle/paneling" in wps_bg.bg:
            a = 60.0
        elif b"vault/lab_puzzle" in wps_bg.bg:
            a = 35.0
        si_item = StreamInfoItem(None, a, b, wps_bg.x, wps_bg.y, wps_bg.bg)
        # chunk = (round(si_item.x / 512), round(si_item.y / 512))
        if si_item not in si_file.items:
            merged_items += 1
            print("merging item", si_item)
            si_file.items.append(si_item)
        else:
            skipped_items += 1
            #print("skipped item", si_item)
    print(f"merged {merged_items}  skipped {skipped_items}")
    print("si items", len(si_file.items))
    if do_rebuild_pyramid:
        rebuild_pyramid(si_file)
        print("si items", len(si_file.items))

    si_file.save("_reconstruct")
    '''si2 = StreamInfoFile(WORLD_PATH + ".stream_info_reconstruct")
    print(si_file)
    print(si2)
    print(si2.short_filename)'''


if __name__ == '__main__':
    main()
