from pixel_scenes import PixelSceneFile
from stream_info import StreamInfoFile
from tools.stats import stream_info_stats


def trim_pixel_scenes():
    f = PixelSceneFile()
    print(f"pre-prune  g1: {f.count_1: 5d}   g2: {f.count_2: 7d}")
    f.trim()
    print(f"post-prune g1: {f.count_1: 5d}   g2: {f.count_2: 7d}")
    f.save()


def main():
    #f = StreamInfoFile()
    #stream_info_stats(f.items)
    #f.save()
    trim_pixel_scenes()
    return
    #print("=-=-=-=-=-=-=-=")
    #pixel_scene_stats(preprune_items)


if __name__ == '__main__':
    main()
