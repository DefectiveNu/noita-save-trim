import json
from typing import List

from constants import WORLD_PATH
from flatten import flatten
from pixel_scenes import PixelScene
from util import pixel_scene_key, stream_info_key


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


def stream_info_stats(items):
    item_stats = {}
    for item in items:
        key = stream_info_key(item)
        if key not in item_stats:
            item_stats[key] = 0
        item_stats[key] += 1
    for k, v in sorted(item_stats.items(), key=lambda i: item_stats[i[0]]):
        print(f"{v: 6d} \"{k}\",")