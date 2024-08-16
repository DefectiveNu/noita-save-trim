from noita_bin_file import NoitaInt
from pixel_scenes import PixelSceneFile
from stream_info import StreamInfoFile
from tools.stats import items_by_world


def trim_pixel_scenes():
    psf = PixelSceneFile()
    sif = StreamInfoFile()
    for w in range(-28, 42):
        items_by_world(sif, psf, w)
    return

    f = PixelSceneFile()
    print(f"pre-prune  g1: {f.count_1: 5d}   g2: {f.count_2: 7d}")
    f.trim()
    print(f"post-prune g1: {f.count_1: 5d}   g2: {f.count_2: 7d}")
    f.save()


def main():
    #t1 = NoitaInt(1)
    #print(t1)
    #print(t1.serialize())
    t2 = NoitaInt.from_bytes(b'\x00\x00\x00\x01')
    print('t2', t2, [{k: v for k, v in t2.__dict__.items()}])
    print(t2.serialize())
    t2.value = 2
    print('t2', t2, [{k: v for k, v in t2.__dict__.items()}])
    print(t2.serialize())
    print("=====")
    print(NoitaInt.from_file(None))
    return
    trim_pixel_scenes()
    return


if __name__ == '__main__':
    main()
