# Warning
This needs a lot more testing before it can be truly considered "safe".

I tried to be conservative, especially closer to the main world (see constants) but you should back up your save and double-check any important areas after running this

## Feature creep

### Repair backgrounds after a crash
`merge_stream_info.py`: takes a `.stream_info` file from before and after a crash recovery, the new file should restore some backgrounds that normally get lost.
Take your pre-crash file and name it `.stream_info_precrash` in your current save.  The merged file will be called `.stream_info_merged`

`reconstruct_stream_info.py`: reconstruct some entries (from `world_pixel_scenes.bin`) that should be in `.stream_info` but seem to get lost after a crash recovery
The modified file will be named `.stream_info_reconstruct`

### Other
`find_item.py`: locate a string in the entity files, and print (approximate, based on chunk) coords

## Other uses
This should also be adaptable to respawn essence eaters, music boxes, etc, might also need to delete area/entity/png_petri files for that chunk.
`tools/coords.py` has functions to convert the numbers in area/entity files to/from coords/chunks.