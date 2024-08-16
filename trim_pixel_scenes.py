from pixel_scenes import PixelSceneFile

f = PixelSceneFile()
print(f"pre-prune  g1: {f.count_1: 5d}   g2: {f.count_2: 7d}")
f.trim()
print(f"post-prune g1: {f.count_1: 5d}   g2: {f.count_2: 7d}")
f.save()
