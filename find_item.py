import os
import re

from constants import WORLD_PATH
from entity_file import EntityFile
from noita_bin_file import NoitaBinFile
from tools.coords import num_to_coords

PATH = f"{os.environ['LOCALAPPDATA']}/../LocalLow/38/Nolla_Games_Noita/save00/world/"

import logging
logging.getLogger("entity_file").setLevel("INFO")

#TARGET = b"dark_alchemist"  # heart mimic
#TARGET = b"shaman_wind"  # spell refresh mimic
TARGET = (b"seed_f")
EXCLUDE = b'$item_book_moon'

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
        matches = re.finditer(TARGET, file.contents)
        for match in matches:
            match_count += 1
            coords = num_to_coords(file.short_filename.split("_")[1].split(".")[0])
            print(file.short_filename, 'match', coords, file.contents[match.start()-10:match.start()+1000])
            ef = EntityFile(f"{PATH}{filename}")
            for i, entity in enumerate(ef.entities):
                if 'items/pickup/sun/newsun.xml' in str(entity):
                    pass
                    #continue
                if TARGET.decode() in str(entity):
                    print("================= ent ======================")
                    print("entity:", entity)
                for component in entity.component_items:
                    if TARGET.decode() in str(component):# and EXCLUDE.decode() not in str(component):
                        print("================= component ======================")
                        print("transform:", entity.transform)
                        print("entity:", entity)
                        #print(component)
                        tmp_idx = i
                        while entity.transform.x == 0:
                            tmp_idx -= 1
                            entity = ef.entities[tmp_idx]
                        print("transform 2:", entity.transform, entity.component_items[0])
    print(f"{file_count} files, {match_count} matches")
    return


if __name__ == '__main__':
    main()
