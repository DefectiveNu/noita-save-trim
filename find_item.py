import os
import re

from constants import WORLD_PATH
from entity_file import EntityFile
from noita_bin_file import NoitaBinFile
from tools.coords import num_to_coords

#PATH = "./save00/ent/"
PATH = "/minecraft/noita/poly/"


def main():
    ent_files = [f for f in os.listdir(PATH) if f.startswith("entities_")]
    file_count = match_count = 0
    for filename in ent_files:
        file_count += 1
        file = NoitaBinFile(f"{PATH}{filename}")
        #file = NoitaBinFile(f"./save00/ent_ngplus/{filename}")
        file.read_file()
        #match = re.findall(b"brimstone", file.contents)
        #match = re.findall(b"thunderstone", file.contents)
        #matches = re.finditer(b"moon", file.contents)
        matches = re.finditer(b"POLYMORPH_FIELD", file.contents)
        for match in matches:
            match_count += 1
            coords = num_to_coords(file.short_filename.split("_")[1].split(".")[0])
            print(file.short_filename, 'match', coords, file.contents[match.start()-10:match.start()+1000])
            ef = EntityFile(f"{PATH}{filename}")
            for entity in ef.entities:
                for component in entity.component_items:
                    if "POLYMORPH_FIELD" in str(component):
                        print(entity)
                        print(component)
    print(f"{file_count} files, {match_count} matches")
    return


if __name__ == '__main__':
    main()
