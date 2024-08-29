import logging
import os
import sys
from datetime import datetime
from time import sleep

from autosaves import AutosaveFile
from tools.coords import get_world_from_x

path = f"{os.environ['LOCALAPPDATA']}/../LocalLow/Nolla_Games_Noita/save00/world/"
logging.getLogger("entity_file").setLevel("WARNING")

#AUTOSAVE_INTERVAL = 180 # seconds
# game does not save more frequently than this, but may wait longer


def main():
    last_mtime = datetime.fromtimestamp(int(os.stat(path+".autosave_player").st_mtime))
    print(last_mtime)
    player_autosave = AutosaveFile(path+".autosave_player")
    print(player_autosave.e1.transform, get_world_from_x(player_autosave.e1.transform.x))
    autosave_interval = 0
    #sys.exit()
    while True:
        mtime = datetime.fromtimestamp(int(os.stat(path+".autosave_player").st_mtime))
        if mtime > last_mtime:
            autosave_interval = (mtime - last_mtime).total_seconds()
            last_mtime = mtime
            player_autosave = AutosaveFile(path+".autosave_player")
            print(f"[{last_mtime}] {(datetime.now() - mtime).total_seconds(): 7.2f} ago  world dist: {get_world_from_x(player_autosave.e1.transform.x)}  interval {autosave_interval}   {player_autosave.e1.transform}")
        else:
            print(f"[{last_mtime}] {(datetime.now() - mtime).total_seconds(): 7.2f} old", end="\r")
        #sleep_time = AUTOSAVE_INTERVAL - (datetime.now() - mtime).total_seconds()
        #if sleep_time < 0.1:
        #    sleep_time = 0.1
        sleep_time = 1.0
        sleep(sleep_time)


if __name__ == '__main__':
    main()
