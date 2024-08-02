from pprint import pprint

from pixel_scenes import PixelSceneFile
from stream_info import StreamInfoFile
from tools.coords import get_world_from_x


def stats1():
    precrash_si = StreamInfoFile("./save00/precrash/.stream_info")
    precrash_wps = PixelSceneFile("./save00/precrash/world_pixel_scenes.bin")
    precrash_si_bgs = [(i.path, int(i.x), int(i.y)) for i in precrash_si.items]
    precrash_si_bgs_pathonly = set(i.path for i in precrash_si.items)
    precrash_wps_bgs_pathonly = set(i.bg for i in precrash_wps.scenes_1 + precrash_wps.scenes_2)
    precrash_wps_bgs = [(i.bg, i.x, i.y) for i in (precrash_wps.scenes_1 + precrash_wps.scenes_2) if i.bg]
    print(len(precrash_wps_bgs))
    print(len(precrash_si_bgs))
    print(precrash_wps_bgs[0])
    print(precrash_si_bgs[0])
    precrash_si_bgs_set = set(precrash_si_bgs)
    precrash_wps_bgs_set = set(precrash_wps_bgs)
    print(len(precrash_wps_bgs_set))
    print(len(precrash_si_bgs_set))
    intersect = precrash_si_bgs_set.intersection(precrash_wps_bgs_set)
    print(len(intersect))
    non_si_bgs = precrash_wps_bgs_set - precrash_si_bgs_set
    non_si_bgs_stats = {}
    for bg in non_si_bgs:
        bgp = bg[0]
        if bgp not in non_si_bgs_stats:
            non_si_bgs_stats[bgp] = 0
        non_si_bgs_stats[bgp] += 1
    pprint(non_si_bgs_stats)

    non_si_bgs_pathonly = precrash_wps_bgs_pathonly - precrash_si_bgs_pathonly
    pprint(non_si_bgs_pathonly)


def stats2():
    precrash_si = StreamInfoFile("./save00/precrash/.stream_info")
    precrash_wps = PixelSceneFile("./save00/precrash/world_pixel_scenes.bin")
    current_si = StreamInfoFile("./save00/current/.stream_info")
    current_wps = PixelSceneFile("./save00/current/world_pixel_scenes.bin")
    precrash_si_bgs = [(i.path, int(i.x), int(i.y)) for i in precrash_si.items]
    precrash_wps_bgs = [(i.bg, i.x, i.y) for i in (precrash_wps.scenes_1 + precrash_wps.scenes_2) if i.bg]
    current_si_bgs = [(i.path, int(i.x), int(i.y)) for i in current_si.items]
    current_wps_bgs = [(i.bg, i.x, i.y) for i in (current_wps.scenes_1 + current_wps.scenes_2) if i.bg]
    already_found = set()
    worlds = list(range(-100, 100))
    worlds.sort(key=lambda i: abs(i))  # 0, -1, 1...
    for world_target in worlds:
        print(f"for world {world_target} new items")
        precrash_si_bgs_stats = {}
        for bg in precrash_si_bgs:
            if get_world_from_x(bg[1]) != world_target:
                continue
            bgp = bg[0]
            if bgp not in precrash_si_bgs_stats:
                precrash_si_bgs_stats[bgp] = 0
            precrash_si_bgs_stats[bgp] += 1
        precrash_wps_bgs_stats = {}
        for bg in precrash_wps_bgs:
            if get_world_from_x(bg[1]) != world_target:
                continue
            bgp = bg[0]
            if bgp not in precrash_wps_bgs_stats:
                precrash_wps_bgs_stats[bgp] = 0
            precrash_wps_bgs_stats[bgp] += 1
        current_si_bgs_stats = {}
        for bg in current_si_bgs:
            if get_world_from_x(bg[1]) != world_target:
                continue
            bgp = bg[0]
            if bgp not in current_si_bgs_stats:
                current_si_bgs_stats[bgp] = 0
            current_si_bgs_stats[bgp] += 1
        current_wps_bgs_stats = {}
        for bg in current_wps_bgs:
            if get_world_from_x(bg[1]) != world_target:
                continue
            bgp = bg[0]
            if bgp not in current_wps_bgs_stats:
                current_wps_bgs_stats[bgp] = 0
            current_wps_bgs_stats[bgp] += 1
        keys = set(list(precrash_si_bgs_stats.keys()) + list(precrash_wps_bgs_stats.keys()) + list(current_si_bgs_stats.keys()) + list(current_wps_bgs_stats.keys()))
        dups = 0
        for k in sorted(keys):
            pc_wps = precrash_wps_bgs_stats.get(k, 0)
            pc_si = precrash_si_bgs_stats.get(k, 0)
            cur_wps = current_wps_bgs_stats.get(k, 0)
            cur_si = current_si_bgs_stats.get(k, 0)
            if (
                    (pc_wps == pc_si) and  # previously matched
                    (cur_wps > cur_si) and  # pixel scenes has at least some items si does not
                    (  # si is supposed to have this because:
                            pc_si > 0 or  # si had it before
                            cur_si > 0  # current has some but not all
                    ) and
                    k not in already_found
            ):
                print(f"{pc_wps: 5d}, {pc_si: 5d}; {cur_wps: 5d}, {cur_si: 5d} {k}")
                already_found.add(k)
            elif k in already_found:
                dups += 1
        print(f"+{dups} already found (of {len(already_found)})")
    i = 0
    for si_bg in precrash_si.items:
        i += 1
        #if not i % 1000:
        #    print(f"at {i}/{len(precrash_si.items)}  {si_bg}")
        if (
            (
                si_bg.a == 50.0 or
                (si_bg.a == 50.0 and b"vault/catwalk" in si_bg.path) or  # 00 00 00 00 00 32  00 00 00 00 00
                (si_bg.a == 50.0 and b"snowcastle/pod" in si_bg.path) or  # 00 00 00 00 00 32  00 00 00 00 00
                (si_bg.a == 50.0 and b"temple/altar" in si_bg.path) or  # 01 00 00 00 00 32  00 00 00 00 00
                (si_bg.a == 50.0 and b"rainforest/plantlife" in si_bg.path) or  # 00 00 00 00 00 32  00 00 00 00 00
                (si_bg.a == 60.0 and b"snowcastle/paneling" in si_bg.path) or  # 01 00 00 00 00 3c  00 00 00 00 00
                (si_bg.a == 35.0 and b"vault/lab_puzzle" in si_bg.path)  # 01 00 00 00 00 23  00 00 00 00 00
            )
            and si_bg.b == 0  # seems to be default
        ):
            continue
            # outliers:
            # data/biome_impl/snowcastle/paneling_07.png (-214255, 5107): 01 00 00 00 00 3c  00 00 00 00 00 [] :: 98.88999938964844 0
            # data/biome_impl/vault/catwalk_01_background.png (105475, 8987): 00 00 00 00 00 32  00 00 00 00 00 [] :: 60.0 0
        for wps_bg in (precrash_wps.scenes_1 + precrash_wps.scenes_2):
            if wps_bg.bg == si_bg.path and int(si_bg.x) == wps_bg.x and int(si_bg.y) == wps_bg.y:
                print(f"{wps_bg.bg.decode()} ({wps_bg.x}, {wps_bg.y}): {wps_bg.gap_1.hex(' ')}  {wps_bg.gap_2.hex(' ')} {wps_bg.extra_parsed} :: {si_bg.a} {si_bg.b}")


def main():
    stats2()


if __name__ == '__main__':
    main()
