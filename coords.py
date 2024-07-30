from constants import WORLD_CHUNK_WIDTH


def get_world_from_x(x):
    return get_world(x/512, 0)


def get_world(chunk_x, chunk_y):
    if chunk_x is None:
        return None
    chunk_x = int(chunk_x)
    dist_x = abs(chunk_x)
    if dist_x < WORLD_CHUNK_WIDTH/2:
        return 0
    else:
        dist_x -= WORLD_CHUNK_WIDTH/2
        world_dist = int(dist_x / WORLD_CHUNK_WIDTH) + 1
        if chunk_x < 0:
            return world_dist * -1
        return world_dist


def get_chunk(filename):
    chunk_x = chunk_y = None
    try:
        if filename.endswith(".bin"):
            num = int(filename.split("_")[1].split(".bin")[0])
            chunk_x, chunk_y = num_to_chunk(num)
        elif filename.endswith(".png_petri"):
            coords = filename.split("world_")[1].split(".png_petri")[0]
            coord_x, coord_y = coords.split("_")
            chunk_x = int(coord_x) / 512
            chunk_y = int(coord_y) / 512
    except:
        print("no coords for file", filename)
    return int(chunk_x or 0), int(chunk_y or 0)


def num_to_coords(num):
    chunk_x, chunk_y = num_to_chunk(num)
    return chunk_x * 512, chunk_y * 512


def num_to_chunk(num):
    num = int(num)
    chunk_y = round(num / 2000)
    chunk_x = num - (chunk_y * 2000)
    return int(chunk_x), int(chunk_y)
