from noita_bin_file import NoitaBinFile
from pixel_scenes import PixelScene
from stream_info import StreamInfoItem


def stream_info_key(p: StreamInfoItem) -> str:
    key = ""
    if p.path:
        key += f"path:{p.path.decode()} "
    key = key.strip()
    return key


def pixel_scene_key(p: PixelScene) -> str:
    key = ""
    if p.mat:
        key += f"mat:{p.mat.decode()} "
    if p.visual:
        key += f"vis:{p.visual.decode()} "
    if p.bg:
        key += f"bg:{p.bg.decode()} "
    if p.unk1:
        key += f"ent:{p.unk1.decode()}"
    key = key.strip()
    return key


def try_strings(file: NoitaBinFile):
    while len(file.contents) > file.read_pos:
        try:
            str_contents = file.read_string(True).decode("ascii")
        except:
            str_contents = ''
        if str_contents.isprintable() and len(str_contents):
            print(str_contents, file.read_string())
        else:
            file.read_byte()
