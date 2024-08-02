import os
import re

from constants import WORLD_PATH
from noita_bin_file import NoitaBinFile
from tools.coords import num_to_coords


def main():
    ent_files = [f for f in os.listdir(WORLD_PATH) if f.startswith("entities_")]
    for filename in ent_files:
        file = NoitaBinFile(f"./save00/world/{filename}")
        file.read_file()
        match = re.findall(b"item_moon", file.contents)
        if match:
            coords = num_to_coords(file.short_filename.split("_")[1].split(".")[0])
            print(file.short_filename, match, coords, file.contents)
    return


if __name__ == '__main__':
    main()
