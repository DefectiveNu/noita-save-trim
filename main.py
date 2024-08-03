from pixel_scenes import PixelSceneFile


def trim_pixel_scenes():
    f = PixelSceneFile()
    print(f"pre-prune  g1: {f.count_1: 5d}   g2: {f.count_2: 7d}")
    f.trim()
    print(f"post-prune g1: {f.count_1: 5d}   g2: {f.count_2: 7d}")
    f.save()


def main():
    trim_pixel_scenes()
    return


if __name__ == '__main__':
    main()
