import os

WORLD_PATH = f"{os.environ['LOCALAPPDATA']}/../LocalLow/Nolla_Games_Noita/save00/world/"

WORLD_CHUNK_WIDTH = 70  # ng=70 ng+,nightmare=64

KEEP_ALL_WORLDS_DIST = 2  # won't prune ANYTHING inside these worlds
# between these, "always prune" is active
AGGRO_CLEAN_DIST = 9  # prune everything not in "always keep" at this distance

ALWAYS_KEEP = [
    b"temple",  # holy mountain stuff
    b"snowcastle/side_cavern_right",  # hourglass
    b"snowcastle/side_cavern_left",
    b"snowcastle/forge",  # anvil
    b"snowcastle/hourglass_chamber",
    b"excavationsite/meditation_cube",
    b"excavationsite/cube_chamber",
    b"excavationsite/receptacle_steam",
    b"coalmine/receptacle_oil",
    b"coalmine/oiltank_puzzle",
    b"biome_impl/spliced",  # bunch of world 0 stuff
    b"snowcave/receptacle_water",
    b"snowcave/statue_hand",  # unsure
    b"snowcave/shop",
    b"snowcave/buried_eye",
    b"snowcave/secret_chamber",
    b"biome_impl/watercave_layout_",
    b"biome_impl/eyespot",
    b"biome_impl/orbroom",
    b"biome_impl/essenceroom",
    b"biome_impl/fishing_hut",  # lakehouse
    b"biome_impl/bunker",  # both lakehouse bunkers
    b"biome_impl/lavalake_pit",
    b"biome_impl/friendroom",
    b"biome_impl/robot_egg",
    b"biome_impl/lavalake_racing",
    b"biome_impl/wizardcave_entrance",
    b"biome_impl/boss_arena",
    b"biome_impl/mystery_teleport",  # tower entrance
    b"biome_impl/teleroom",  # fast travel room
    b"biome_impl/ocarina",
    b"biome_impl/null_room",  # perk nullifier
    b"biome_impl/greed_treasure",
    b"biome_impl/huussi",  # outhouse
    b"biome_impl/alchemist_secret",
    b"vault/lab_puzzle",
    b"vault/shop",
]

ALWAYS_PRUNE = [
    b"vault/pipe",
    b"vault/catwalk",
    b"rainforest/plantlife",
    b"crypt/stairs",
    b"snowcastle/pillar",
    b"snowcastle/paneling",
    b"snowcastle/chamfer",
    b"wandcave/floor_rubble",
    b"vault/pillar",
]

DEBUG = False
