import os
import re
from pprint import pprint

from noita_bin_file import NoitaBinFile
from stream_info import StreamInfoFile, StreamInfoItem
from pixel_scenes import PixelSceneFile
from tools.coords import num_to_coords
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


def main():
    si_file = StreamInfoFile()
    wps_file = PixelSceneFile()
    wps_bg_items = [item for item in wps_file.scenes_1 + wps_file.scenes_2 if any(x in item.bg for x in MERGE_ITEMS)]
    pprint(wps_bg_items)
    print(len(wps_bg_items))
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
        else:
            skipped_items += 1
            #print("skipped item", si_item)
    print(f"merged {merged_items}  skipped {skipped_items}")
    si_file.save("_reconstruct")


if __name__ == '__main__':
    main()
