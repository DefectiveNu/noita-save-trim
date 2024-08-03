import json
import math
from pprint import pprint
from typing import List

from constants import WORLD_PATH
from tools.conversions import serialize_float, bytes_to_int
from tools.coords import get_world_from_x
from tools.flatten import flatten
from pixel_scenes import PixelScene
from stream_info import StreamInfoItem, StreamInfoFile
from tools.util import pixel_scene_key, stream_info_key


# bunch of random stuff I used to get an idea what was stored and how
# (not complete...)


def pixel_scene_stats(items: List[PixelScene]):
    item_stats = {}
    path_stats = {
        "mat": {},
        "vis": {},
        "bg": {},
        "ent": {},
    }
    for item in items:
        mat_tree = item.mat.decode().split("/")
        prev = None
        base = path_stats["mat"]
        for mat in mat_tree:
            if mat not in base:
                base[mat] = {}
            prev = base
            base = base[mat]
        if base == {}:
            prev[mat] = 0
        prev[mat] += 1
        del mat, mat_tree

        vis_tree = item.visual.decode().split("/")
        prev = None
        base = path_stats["vis"]
        for vis in vis_tree:
            if vis not in base:
                base[vis] = {}
            prev = base
            base = base[vis]
        if base == {}:
            prev[vis] = 0
        prev[vis] += 1
        del vis, vis_tree

        ent_tree = item.unk1.decode().split("/")
        prev = None
        base = path_stats["ent"]
        for ent in ent_tree:
            if ent not in base:
                base[ent] = {}
            prev = base
            base = base[ent]
        if base == {}:
            prev[ent] = 0
        prev[ent] += 1
        del ent, ent_tree

        bg_tree = item.bg.decode().split("/")
        prev = None
        base = path_stats["bg"]
        for bg in bg_tree:
            if bg not in base:
                base[bg] = {}
            prev = base
            base = base[bg]
        if base == {}:
            prev[bg] = 0
        prev[bg] += 1
        del bg, bg_tree

        key = pixel_scene_key(item)
        if key not in item_stats:
            item_stats[key] = 0
        item_stats[key] += 1
    for k, v in sorted(item_stats.items(), key=lambda i: item_stats[i[0]]):
        print(f"{v: 6d} \"{k}\",")
    #pprint(path_stats)
    with open(WORLD_PATH + "path.json", "w") as f:
        f.write(json.dumps(path_stats, indent=2))


def pixel_scene_tree(items):
    item_tree = {}
    extra_stats = {}
    for item in items:
        if item.extra not in extra_stats:
            extra_stats[item.extra] = {"parsed:": item.extra_parsed, "count": 0}
        extra_stats[item.extra]["count"] += 1
        mat = "mat-" + item.mat.decode() or "empty string"
        if mat not in item_tree:
            item_tree[mat] = {}

        vis = "vis-" + item.visual.decode() or "empty string"
        if vis not in item_tree[mat]:
            item_tree[mat][vis] = {}

        bg = "bg-" + item.bg.decode() or "empty string"
        if bg not in item_tree[mat][vis]:
            item_tree[mat][vis][bg] = {}

        misc = f"{item.gap_1 or 'gap_1'}_{item.gap_2 or 'gap_2'}_{item.unk1 or 'unk1'}_{item.extra or 'extra'}"
        if misc not in item_tree[mat][vis][bg]:
            item_tree[mat][vis][bg][misc] = 0

        #item_tree[mat][vis][bg][misc][f"{item.x}, {item.y}"] = item_tree[mat][vis][bg][misc].get(f"{item.x}, {item.y}", 0) + 1
        item_tree[mat][vis][bg][misc] += 1
        #print(mat, vis, bg, misc)

    # collapse tree
    item_tree_2 = {}

    with open(WORLD_PATH + "item_tree4.json", "w") as f:
        f.write(json.dumps(item_tree, indent=2))
    print("=============")
    print("=============")
    item_tree = flatten(item_tree)
    #item_tree = flatten(item_tree)
    #item_tree = flatten(item_tree)
    #item_tree = flatten(item_tree)
    with open(WORLD_PATH + "item_tree5.json", "w") as f:
        f.write(json.dumps(item_tree, indent=2))


def stream_info_non_default(items: List[StreamInfoItem]):
    outliers = set()
    for item in items:
        if (
            item.a != 50.0 and
            not (
                (item.a == 60.0 and b"snowcastle/paneling" in item.path) or
                (item.a == 60.0 and b"excavationsite/beam" in item.path) or
                (item.a == 40.0 and b"crypt/pillars" in item.path) or
                (item.a == 40.0 and b"vault/pillar" in item.path) or
                (item.a == 40.0 and b"crypt/slab" in item.path) or
                (item.a == 35.0 and b"vault/lab_puzzle" in item.path)
            ) or
            item.b != 0
        ):
            k = (item.a, item.b, item.path)
            if k not in outliers:
                item.debug()
                #print(serialize_float(item.a).hex(' '))
                outliers.add(k)


def stream_info_stats(si_file: StreamInfoFile, world_target=0, wps_items: List[PixelScene]=[]):
    items = si_file.items
    print(f"stats world {world_target}")
    item_stats = {}
    i = 0
    min_x = 1_000_000_000
    max_x = -1_000_000_000
    min_y = 1_000_000_000
    max_y = -1_000_000_000
    #items[0].debug()
    for item in items:
        i += 1
        if b"pyramid" not in item.path:
            continue
        if get_world_from_x(item.x) != world_target:
            continue
        #print(i)
        '''if item.a not in [
            101.0,
            99.9000015258789,
            50.0,
            40.0
        ]:'''
        #item.debug()
        key = stream_info_key(item)
        if key not in item_stats:
            item_stats[key] = 0
        item_stats[key] += 1
        min_x = min(min_x, item.x)
        max_x = max(max_x, item.x)
        min_y = min(min_y, item.y)
        max_y = max(max_y, item.y)
    print(f"min {min_x, min_y}  max {max_x, max_y}")
    for i in [str(item) for item in items if min_x <= item.x <= max_x and min_y <= item.y <= max_y]:
        print(i)
    for i in [str(item) for item in wps_items if min_x <= item.x <= max_x and min_y <= item.y <= max_y]:
        print(i)
    '''for cx in range(math.floor(min_x/512), math.ceil(max_x/512)):
        for cy in range(math.floor(min_y/512), math.ceil(max_y/512)):
            print(cx,cy, (cx,cy) in si_file.chunk_status_items)'''
    return
    for k, v in sorted(item_stats.items(), key=lambda i: item_stats[i[0]]):
        print(f"{v: 6d} \"{k}\",")
    for k in sorted(item_stats.keys()):
        print(k)
