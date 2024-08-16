import json
import os
import sys
from json import JSONEncoder
from pprint import pprint
from typing import List, Type

from constants import WORLD_PATH, KEEP_ALL_WORLDS_DIST, AGGRO_CLEAN_DIST, ALWAYS_KEEP, ALWAYS_PRUNE, DEBUG
from tools.conversions import serialize_int, serialize_float, serialize_str, retry_as_float, readable_bytes, \
    hex_readable, next_string, bytes_to_int, bytes_to_pixels, is_valid_string
from tools.coords import chunk_to_num, get_world_from_x, num_to_coords, coords_to_num, get_chunk
from noita_bin_file import NoitaBinFile
from tools.util import try_strings
import logging
import coloredlogs


coloredlogs.install(level='DEBUG', fmt='%(levelname)s %(message)s', isatty=True, level_styles={
    'debug': {'color': 'blue'},
    'info': {'color': 'green'},
    'warning': {'color': 'yellow'},
    'error': {'color': 'red'},
})
#coloredlogs.install(fmt='%(asctime)s,%(msecs)03d %(hostname)s %(name)s[%(process)d] %(levelname)s %(message)s')
log = logging.getLogger("entity_file")


next_item = ""
global component_adjustment_dict
component_adjustment_dict = {}


def _default(self, obj):
    return getattr(obj.__class__, "to_json", _default.default)(obj)


_default.default = JSONEncoder().default
JSONEncoder.default = _default


class Transform:
    def __init__(self, file: NoitaBinFile, quiet=False):
        self.x = file.read_float()
        self.y = file.read_float()
        self.scale_x = file.read_float()
        self.scale_y = file.read_float()
        self.rotation = file.read_float()
        coord_x, coord_y = file.coords()
        file_cx, file_cy = get_chunk(file.short_filename)
        #if self.x != 0.0 and not coord_x <= self.x <= coord_x + 512 and not quiet:
        if file_cx != int(self.x / 512):
            log.debug('x out of range')
            log.debug(self)
            log.debug(f"filename {file.short_filename} computed at: {coord_x, coord_y}  coords: {self.x, self.y} (num {coords_to_num(self.x, self.y)})  diff {self.x - coord_x} {self.y - coord_y}")
            #sys.exit(0)
            #raise ValueError("entity out of bounds! x", self.x, coord_x, coord_x - self.x)
        #if self.y != 0.0 and not coord_y <= self.y <= coord_y + 512 and not quiet:
        if file_cy != int(self.y / 512):
            log.debug('y out of range')
            log.debug(self)
            log.debug(f"filename {file.short_filename} computed at: {coord_x, coord_y}  coords: {self.x, self.y} (num {coords_to_num(self.x, self.y)})  diff {self.x - coord_x} {self.y - coord_y}")
            #sys.exit(0)
            #raise ValueError("entity out of bounds! y", self.y, coord_y,  coord_y - self.y)

    def __str__(self):
        return f"{self.x, self.y} {self.scale_x, self.scale_y} {self.rotation}"


class BaseComponent:
    def __init__(self, file: NoitaBinFile):
        self._start_pos = file.read_pos
        self.b1 = file.read_byte()
        #assert self.b1 == 1
        self.b2 = file.read_byte()  # no children?
        #assert self.b2 == 1
        self.base_unk1 = file.read_string()  # enabled_in_world?
        ##log.debug(f"base: {self.b1} {self.b2} {self.base_unk1} {self.__class__}")
        #log.debug("base end peek " + hex_readable(file.peek(200)))

    def len_bytes(self):
        ttl_len = 0
        min_len = 0
        for k in self.__dict__:
            if k.startswith("_"):
                pass
            elif k in ["b1", "b2"]:
                ttl_len += 1
                min_len += 1
            elif k.startswith("auto"):
                for item in self.__dict__[k]:
                    if is_valid_string(item):
                        ttl_len += len(item) + 4
                        min_len += 4
                    else:
                        ttl_len += len(item)
                        min_len += len(item)
            elif isinstance(k, int):
                ttl_len += 4
                min_len += 4
            elif isinstance(self.__dict__[k], bytes) and "raw" in k:
                ttl_len += len(self.__dict__[k])
                min_len += len(self.__dict__[k])
            elif isinstance(self.__dict__[k], bytes):
                ttl_len += len(self.__dict__[k]) + 4  # string with length
                min_len += 4
            else:
                raise ValueError(f"unknown length for {k}")
        #log.info(f"min len for {self.__class__.__name__} {min_len} {self.printable_autos()}")
        return ttl_len

    def printable_autos(self):
        auto = getattr(self, 'auto', None)
        if not auto:
            return None
        out = []
        for item in auto:
            if is_valid_string(item):
                out.append(item.decode())
            else:
                out.append(hex_readable(item))
        return out

    def printable_autos_short(self):
        auto = getattr(self, 'auto', None)
        if not auto:
            return None
        out = []
        for item in auto:
            if is_valid_string(item):
                out.append(item.decode())
            else:
                out.append(len(item))
        return out

    def raws(self):
        out = {}
        for k in self.__dict__:
            if k.startswith("raw"):
                out[k] = self.__dict__[k]
            if k.startswith("auto"):
                for index, item in enumerate(self.__dict__[k]):
                    if not is_valid_string(item):
                        out[k+str(index)] = item
        return out

    def __str__(self):
        out = f"{self.__class__} "
        for k in self.__dict__:
            if k.startswith("raw"):
                out += f"{k}:[len {len(self.__dict__[k])}] "
            elif isinstance(self.__dict__[k], list):
                out += f"{k}:[{len(self.__dict__[k])} items] "
            else:
                out += f"{k}:{self.__dict__[k]} "
        return out + str(id(self))

    def __repr__(self):
        out = self.__class__.__name__ + '\n'
        raws = self.raws()
        for raw in raws:
            out += f"    {raw}: {hex_readable(raws[raw])}\n"
        return out

    '''def __str__(self):
        out = f"{self.__class__} "
        raws = []
        for k in self.__dict__:
            if k.startswith("raw"):
                raws.append(f"{k}:{self.__dict__[k].hex(' ', -4)}")
            else:
                out += f"{k}:{self.__dict__[k]} "
        out += " ".join(raws)
        return out'''


class HitboxComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw = file.skip(31)


class AbilityComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw = file.skip(4)
        self.xml1 = file.read_string()
        self.image = file.read_string()  # data/items_gfx/wands/wand_0761.png
        self.raw2 = file.skip(59)
        self.itemxml = file.read_string()  # data/entities/base_item.xml
        self.raw3 = file.skip(22)
        self.name = file.read_string()  # Rapid bolt wand
        self.raw4 = file.skip(31)
        self.uifx = file.read_string()  # data/ui_gfx/gun_actions/unidentified.png
        self.raw5 = file.skip(228)
        self.durability = file.read_string()  # _get_gun_slot_durability_default
        self.raw6 = file.skip(21)


class ItemActionComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.unk2 = file.read_string()  # ex: CIRCLE_SHAPE "action_id"?


class ItemComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        #print("start", hex_readable(file.peek(1000)))
        self.name = file.read_string()
        self.raw1 = file.skip(32)
        #print("raw1", hex_readable(self.raw1))
        self.custom = file.read_string()  # data/items_gfx/wands/custom/plant_02.png
        self.s2 = file.read_string()
        self.raw3 = file.skip(7)
        self.s3 = file.read_string()
        #print("s2", hex_readable(file.peek(1000)))
        self.raw3 = file.skip(36)


class SimplePhysicsComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(1)


class SpriteComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        log.debug(f"SpriteComponent start peek {readable_bytes(file.peek(1000))} {self}")
        self.sprite = file.read_string()
        self.raw = file.skip(35)
        self.anchor = file.read_string()  # float_right
        self.raw2 = file.skip(4)
        self.text = file.read_string()
        self.raw3 = file.skip(17)
        '''#with open("SpriteComponent2.txt", "a") as f:
        #    f.write(f"{file.read_pos: 10d} {self.b1} {self.b2} {hex_readable(self.raw)} || {hex_readable(self.raw2)} || {hex_readable(self.raw3)} {self.sprite} {self.anchor} {self.text}\n")
        if self.sprite in [
            b"data/debug/empty.png",
            b"data/ui_gfx/sale_indicator.png"
        ]:  # I don't like this...
            self.raw3 = file.skip(4)'''


class SpriteOffsetAnimatorComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw = file.skip(28)


class VelocityComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        #with open("VelocityComponent_stats.txt", "a") as f:
        #    f.write(hex_readable(file.peek(100)) + "\n")
        #print("VelocityComponent", hex_readable(file.peek(100)))
        self.raw = file.skip(41)
        '''
            b"\x00\x00\x00\x00",
            b"C\xf1\xcd\x15",
            b'C\xb9v\xe9',
            b'C\xddXo',
            b'@\xd3`d',
            b'\xba\xb6\xd1\xdb',
            b'C\xf244',
            b'>0\xdf\x9a',
            b'D4&\x92',
            b'C\xb7\xa9`',
            b'C\xdf\xd3:',
            b'\xb8u\x8c^',
            b'>\xf8\xeeL',
            b'@\x11\x9e\xc1',
            b'C\xfcv\x8c',
            b'C\x9c*Y',
            b'D*?\\',
            b'C\xc0\xf7W',
            b'C\xf0\xfbH',
            b'C\xf1e\x1a'
        00000000000000000000000000000000
        10000110111100011100110110101000
        10000110101110011110110011101001
        10000110110111011011000011011110
        10000000110100111100000011001000
        10111010101101101101000111011011
        10000110111100101101000011010000
        11111000110000001101111110011010
        10001000110100001001100010010010
        10000110101101111010100111000000
        10000110110111111101001111101000
        10111000111010101000110010111100
        11111000111110001110111010011000
        10000000100010001001111011000001
        10000110111111001110110010001100
        10000110100111001010100010110010
        10001000101010001111110010111000
        10000110110000001111011110101110
        10000110111100001111101110010000
        10000110111100011100101011010000
        11010000111100001000100110111111 x
               x?       ?       ?
        12345678123456781234567812345678
        00000000100000001000000010000000
        '''
        '''
        #if self.raw.endswith(b"4\xf0\x89\xbf"):
        #print(self.raw[-4:])
        #if self.raw[-4:] != b"\x00\x00\x00\x00":
            #log.warning(" ".join([f"{bin(b)[2:]:08}" for b in self.raw[-4:]]))
            #log.warning(hex_readable(self.raw + b"::" + file.peek(1000)))
        if False and self.raw[-4:] != b"\x00\x00\x00\x00" and (bytes_to_int(self.raw[-4:]) & 0b00000000100000001000000010000000 != 0b00000000100000001000000010000000):
            print("".join([f"{bin(b)[2:]:08}" for b in self.raw[-4:]]))
            print("VelocityComponent raw", hex_readable(self.raw))
            print("VelocityComponen2", hex_readable(file.peek(100)))
            self.subitems = file.read_int()
            for i in range(self.subitems):
                setattr(self, f"subitem{i}str", file.read_string())
                setattr(self, f"subitem{i}raw", file.skip(33))
        #print("VelocityComponent raw", hex_readable(self.raw))
        #print("VelocityComponen2", hex_readable(file.peek(100)))
        #if " i  n  v  e  n  t  o  r  y  _  q  u  i  c  k" in hex_readable(file.peek(100)):
        #    sys.exit(1)'''


class ElectricityComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw = file.skip(31)


class ElectricChargeComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw = file.skip(24)


class PixelSpriteComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.img1 = file.read_string()
        self.raw = file.skip(8)
        self.material = file.read_string()  # ?
        self.raw2 = file.skip(4)
        self.sprite = file.read_string()
        self.raw3 = file.skip(33)
        self.material2 = file.read_string()  # ?
        self.raw4 = file.skip(1)  # continue?
        #with open("PixelSpriteComponent.txt", "a") as f:
        #    f.write(f"{file.read_pos: 10d} {hex_readable(self.raw)} {hex_readable(self.raw2)} {hex_readable(self.raw3)} {hex_readable(self.raw4)} {hex_readable(file.peek(2408))}\n")
        if self.raw4 == b'\x01':  # attached RGBA bitmap (reversed? at least, first byte seems to be opacity)
            #log.debug("!!!! continue?", self, "\n", bytes_to_int(file.peek(4))," ", bytes_to_int(file.peek(8)[-4:]), "\n", (file.peek(16464)).hex(' ', -4))
            self.bitmap_x = file.read_int()
            self.bitmap_y = file.read_int()
            self.bitmap_raw = file.skip(4 * self.bitmap_x * self.bitmap_y)
            log.debug(self.bitmap_x, self.bitmap_y)
            log.debug(bytes_to_pixels(self.bitmap_raw, self.bitmap_x, self.bitmap_y))
        #    self.raw5 = file.skip(2408)
        #log.debug("PixelSpriteComponent end peek", readable_bytes(file.peek(2586)))
        #log.debug(self)


class AudioComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        #print("AudioComponent start", hex_readable(file.peek(100)))
        self.bankfile = file.read_string()
        self.trigger = file.read_string()
        self.type = file.read_string()
        self.raw = file.skip(4)


class AudioLoopComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.bankfile = file.read_string()
        self.trigger = file.read_string()
        self.raw = file.skip(11)


class HotspotComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        #print("start", hex_readable(file.peek(1000)))
        self.raw = file.skip(9)
        self.s1 = file.read_string()


class ItemAlchemyComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw = file.skip(24)


class ExplodeOnDamageComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(21)
        self.xml1 = file.read_string()
        self.raw2 = file.skip(24)
        self.xml2 = file.read_string()
        self.raw3 = file.skip(41)
        self.dmgtype = file.read_string()
        self.raw4 = file.skip(8)
        self.dmgtype2 = file.read_string()
        self.raw5 = file.skip(95)
        self.src = file.read_string()
        self.raw6 = file.skip(17)


class PhysicsBody2Component(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw = file.skip(64)


class InheritTransformComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw = file.skip(2)
        self.unkstr = file.read_string()
        self.raw2 = file.skip(26)
        #with open("ITCLog.txt", "a") as f:
        #    f.write(f"ITC at {file.read_pos: 10d} {file.peek(100)}\n")
        if self.raw == b"\x00\x01":  # extend
            self.raw_extended = file.skip(4)


class LightComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw = file.skip(33)


class ParticleEmitterComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.particle = file.read_string()
        self.raw1 = file.skip(179)
        self.image = file.read_string()
        self.raw2 = file.skip(20)


class SpriteAnimatorComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.sprite = file.read_string()
        self.raw = file.skip(1)


class TorchComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw = file.skip(17)


class LuaComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.script1 = file.read_string()
        self.auto = raws_and_strings(file, 131)
        tmp = self.printable_autos_short()
        if isinstance(tmp[0], str):
            print(tmp)
        #self.auto = raws_and_strings(file, 141)
        log.info(self.auto)
        '''self.file1 = file.read_string()
        log.debug("LuaComponent next1 string", next_string(file.peek(1000)), self)
        self.raw1 = file.skip(26)
        self.file2 = file.read_string()
        log.debug("LuaComponent next2 string", next_string(file.peek(1000)), self)
        self.raw2 = file.skip(8)
        self.file3 = file.read_string()
        log.debug("LuaComponent next3 string", next_string(file.peek(1000)), self)
        #with open("LuaComponentLog.txt", "a") as f:
        #    f.write(f"{file.read_pos: 10d} {file.peek(200)}\n")
        self.raw3 = file.skip(4)
        self.file4 = file.read_string()
        log.debug("LuaComponent next4 string", next_string(file.peek(1000)), self)
        self.raw4 = file.skip(4)
        self.file5 = file.read_string()
        log.debug("LuaComponent next5 string", next_string(file.peek(1000)), self)
        self.raw5 = file.skip(8)
        self.file6 = file.read_string()
        log.debug("LuaComponent next6 string", next_string(file.peek(1000)), self)
        self.raw6 = file.skip(4)
        self.file7 = file.read_string()
        self.file8 = file.read_string()
        log.debug("LuaComponent next7 string", next_string(file.peek(1000)), self)
        self.raw7 = file.skip(49)'''


class ManaReloaderComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)


class MaterialAreaCheckerComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.auto = raws_and_strings(file, 35)
        log.info(self.auto)
        #if self.raw.endswith(b'\x01'):
        #    self.raw_extended = file.skip(4)


class SpriteParticleEmitterComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.xmlfile = file.read_string()
        self.raw = file.skip(224)


class CellEaterComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw = file.skip(23)


class TeleportComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw = file.skip(10)
        self.file1 = file.read_string()
        self.file2 = file.read_string()
        self.raw2 = file.skip(1)


class UIInfoComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        #with open("UIInfoComponent.txt", "a") as f:
        #    f.write(f"{file.read_pos: 10d} {hex_readable(file.peek(100))}\n")
        self.s1 = file.read_string()
        '''if self.s1 in [
            b'$teleport_deeper',
            #b'$building_worm_deflector',
        ]:
            self.raw = file.skip(4)'''


class WormAttractorComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw = file.skip(8)


class ItemAIKnowledgeComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw = file.skip(16)


class PhysicsBodyComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw = file.skip(50)


class PhysicsImageShapeComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw = file.skip(20)
        self.shapefile = file.read_string()
        self.raw2 = file.skip(4)


class PhysicsJoint2MutatorComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw = file.skip(19)

class ItemCostComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw = file.skip(9)


class DamageModelComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        #log.debug(f"DamageModelComponent start string {next_string(file.peek(1000))}")
        self.raw = file.skip(139)
        #print("raw", hex_readable(self.raw))
        self.dmgmats = file.read_string()
        self.multis = file.read_string()
        self.raw2 = file.skip(3)
        self.mat = file.read_string()
        self.filenames = file.read_string()  # data/ragdolls/root_grower_leaf/filenames.txt
        self.mat2 = file.read_string()
        self.raw4 = file.skip(12)
        #print("raw4", hex_readable(self.raw4))
        self.mat3 = file.read_string()
        self.mat4 = file.read_string()
        self.raw5 = file.skip(9)
        #print("raw5", hex_readable(self.raw5))
        self.mat5 = file.read_string()
        self.xmlfiles = file.read_string()
        self.xml2 = file.read_string()
        self.raw6 = file.skip(49)
        #print("raw6", hex_readable(self.raw6))


class LifetimeComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw = file.skip(24)


class MaterialInventoryComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw = file.skip(3788)


class VariableStorageComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.varname = file.read_string()
        self.varname = file.read_string()
        #log.debug(f"VariableStorageComponent varname string {next_string(file.peek(1000))}, {self}")
        #log.debug(f"VariableStorageComponent varname peek {hex_readable(file.peek(1000))}")
        self.raw = file.skip(9)


class VerletPhysicsComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        #self.raw = file.skip(1396)  # TODO: overreads by 1 sometimes?? maybe check if null-term is actually 0
        self.raw = file.skip(1388)


class VerletWorldJointComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw = file.skip(12)


class MaterialSuckerComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw = file.skip(44)


class PhysicsBodyCollisionDamageComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw = file.skip(8)


class PhysicsThrowableComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw = file.skip(37)


class PotionComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw = file.skip(21)


class ProjectileComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.auto = raws_and_strings(file, 100000)
        return
        self.raw = file.skip(30)
        self.file1 = file.read_string()
        self.raw2 = file.skip(265)
        self.mat1 = file.read_string()
        self.raw3 = file.skip(8)
        self.part1 = file.read_string()
        self.raw4 = file.skip(11)
        self.part2 = file.read_string()
        self.raw5 = file.skip(57)
        self.file2 = file.read_string()
        self.raw6 = file.skip(69)
        self.dmgtype1 = file.read_string()
        self.raw7 = file.skip(8)
        self.dmgtype2 = file.read_string()
        self.raw8 = file.skip(152)
        self.properties = file.read_string()
        self.raw9 = file.skip(97)
        self.effect = file.read_string()
        self.raw10 = file.skip(7)


class CollisionTriggerComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw = file.skip(12)
        self.target = file.read_string()
        self.raw = file.skip(11)


class GenomeDataComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw = file.skip(18)


class IKLimbsAnimatorComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw = file.skip(34)


class ItemChestComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw = file.skip(29)


class LimbBossComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw = file.skip(4)


class PathFindingComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        #self.raw = file.skip(78)
        #self.raw = file.skip(150)
        #self.raw = file.read_until(b'\x80\x00\x00\x00\x00\x00\x00')  # TODO
                                     #"80  00  00  00  00  00  00"
        self.auto = raws_and_strings(file, 1000)
        log.info(self.auto)
        return


class PathFindingGridMarkerComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        #print(hex_readable(file.peek(100)))
        self.raw = file.skip(16)


class PhysicsAIComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw = file.skip(74)


class PhysicsShapeComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw = file.skip(45)


class IKLimbComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw = file.skip(36)


class IKLimbAttackerComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw = file.skip(13)
        self.s1 = file.read_string()  # mortal
        self.raw = file.skip(8)


class HomingComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.target = file.read_string()  # prey
        self.raw1 = file.skip(23)


class PositionSeedComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(8)


class ElectricityReceiverComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(24)


class LaserEmitterComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(54)


class EnergyShieldComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(28)


class LooseGroundComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(40)
        self.images = file.read_string()


class BookComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(8)


class AnimalAIComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(9)
        self.ai = file.read_string()
        self.raw2 = file.skip(110)
        self.xml1 = file.read_string()
        self.raw3 = file.skip(69)
        self.el1 = file.read_string()
        self.raw4 = file.skip(8)
        self.el2 = file.read_string()
        self.raw5 = file.skip(174)
        self.xml2 = file.read_string()
        self.raw5 = file.skip(103)


class CameraBoundComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(15)


class CharacterCollisionComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(8)


class CharacterDataComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(175)


class CharacterPlatformingComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(185)


class ControlsComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(12)


class GameStatsComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.stat1 = file.read_string()
        self.stat2 = file.read_string()
        self.raw1 = file.skip(10)


class SpriteStainsComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(17)


class StatusEffectDataComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(1032)


class GameEffectComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(94)


class DieIfSpeedBelowComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(8)


class MagicConvertMaterialComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(17)
        self.str1 = file.read_string()  # [liquid]
        self.raw2 = file.skip(28)
        self.str2 = file.read_string()  # b'water,water_swamp,water_salt,radioactive_liquid'
        self.str3 = file.read_string()  # b'steam,steam,steam,radioactive_gas'
        self.raw3 = file.skip(4)  # 00 00 00 09


class GunComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)


class Inventory2Component(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(16)  # 00 00 00 01 00 00 00 08 00 00 00 08 00 00 00 00


class ItemPickUpperComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(16)  # 01 00 01 00 0a d7 8b 01 00 00 00 00 00 00 00 00


class HitEffectComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(16)  # 00 00 00 00 00 00 00 00 00 00 00 03 00 00 00 00
        self.str1 = file.read_string()  # b'data/entities/misc/shieldshot_shield.xml'


class AreaDamageComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(36)  # c1 90 00 00 c1 90 00 00  A 90 00 00  A 90 00 00 00 00 00 00 00 00 00 01  > 0f  \  ) 00 00 00 04 00 00 00 00
        self.str1 = file.read_string()  # b'$damage_curse'
        self.str2 = file.read_string()  # b'human'


class ElectricitySourceComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(8)  # 00 00 00 18 00 00 00  @


class LoadEntitiesComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.str1 = file.read_string()  # b'data/entities/particles/particle_explosion/explosion_smoke_pillar_top_left_pink.xml'
        self.raw1 = file.skip(17)  # 00 00 00 01 00 00 00 01 00 00 00 00 0a 01 0d  k 1d


class IKLimbWalkerComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(53)  # A 80 00 00 00 00 00 0a  ?  L cc cd  ? 93  3  3  A  p 00 00 00 00 00 00 c9  E a8  q d8  F  "  j  3  E a8 19 bb  F  " 00  )  E a8  L 85  F  " 18  U 00 00 00 01


class PhysicsJoint2Component(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(51)  # 00 00  @  @ 00 00  A a0 00 00 00 00 00 00 00 00 00 00 01 00 00 00  d 00 00 01  , c1  h 00 00 c1 00 00 00 00 00 00 00 c1    00 00 00 00 00 00  @    00 00


class GasBubbleComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(8)  # c3  H 00 00  B b4 00 00


class UIIconComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.str1 = file.read_string()  # b'data/ui_gfx/status_indicators/neutralized.png'
        self.str2 = file.read_string()  # b'$effect_neutralized'
        self.str3 = file.read_string()  # b'$effectdesc_neutralized'
        self.raw1 = file.skip(3)  # 00 01 00


class TemplateComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(8)
        log.debug(self)
        log.debug("TemplateComponent next string %s", next_string(file.peek(1000)))
        log.debug("TemplateComponent peek %s", hex_readable(file.peek(200)))
        1/0


class Entity:
    def __init__(self, file: NoitaBinFile, peek=False):
        start_pos = file.read_pos
        #log.debug("entity start peek %s", readable_bytes(file.peek(200)))
        self.name = file.read_string(quiet=peek)
        assert is_valid_string(self.name)
        self.b1 = file.read_byte()
        #log.debug('name %s %s', self.name, self.b1)
        self.ent_file = file.read_string(quiet=peek)
        assert is_valid_string(self.ent_file)
        #log.debug("ent file %s", self.ent_file)
        assert self.name == b"inventory_quick" or (self.ent_file == b"??SAV/player.xml" or (self.ent_file.startswith(b'data/entities/') and self.ent_file.endswith(b'.xml')))
        self.tags = file.read_string(quiet=peek)
        assert is_valid_string(self.tags)
        #log.debug('tags %s', self.tags)
        self.transform = Transform(file)
        #log.debug("transform %s", self.transform)
        self.components = file.read_int()
        #log.debug("components %s", self.components)
        if peek:
            file.read_pos = start_pos
            return
        #log.debug("entity mid peek %s", readable_bytes(file.peek(200)))
        self.component_items = []
        self.adjustments = []
        for i in range(self.components):
            log.debug(self)
            log.debug(self.component_items)
            log.debug(f"at {file.read_pos} / {len(file.contents)}")
            log.debug(f"========================================================")
            log.info(f"======= component {i+1} / {self.components} ==============")
            log.debug(f"========================================================")
            if adj := next_component(file):
                #sys.exit(1)
                self.adjustments.append((i, adj))  # issue was in previous
                log.warning(f"add adjustment {(i, adj)} {file.read_pos-adj}-{file.read_pos} {file.contents[file.read_pos-adj:file.read_pos]}")
                self.component_items[i-1].raw_adjust = file.contents[file.read_pos-adj:file.read_pos]
                log.warning(self.component_items[i-1])
                sys.exit(2)
            component_class = get_component_class(file)
            global next_item
            next_item = "component" if i + 1 < self.components else "entity"
            if not isinstance(component_class, str):
                comp = component_class(file)
            else:
                comp = autogenerate_component(file, component_class)
                1/0
            #comp = make_component(file)
            log.debug("---------------------")
            log.debug(self)
            log.debug(self.component_items)
            self.component_items.append(comp)
            #log.debug(comp)
            #log.debug("at", file.read_pos, len(file.contents))
            #log.debug(file.peek(1000))
            '''while i+1 == self.components and comp.b2 == 0:
                log.debug("~~~~~~~~~~~~~~~~~~~~")
                log.debug("at", file.read_pos)
                log.debug("!!!!! comp b2 peek", file.peek(1000))
                comp = make_component(file)
                log.debug(comp)
                self.component_items_2.append(comp)
                #Entity(file)'''
        self.children = file.read_int()  # count of subitems
        self.child_items = []
        for i in range(self.children):
            log.debug("---==================================================---")
            log.info(f"---======= entity child {i+1} / {self.children} ===========---")
            log.debug("---==================================================---")
            self.child_items.append(Entity(file))
        return

    def __str__(self):
        #out = f"{self.__class__} "
        out = "Entity "
        for k in self.__dict__:
            if isinstance(self.__dict__[k], list):
                if k == "component_items":
                    out += f"{k}:{[f'{i: 3d} {ci.__class__.__name__}' for i, ci in enumerate(self.__dict__[k], start=1)]} "
                elif k == "adjustments":
                    out += f"{k}:{self.__dict__[k]} "
                else:
                    out += f"{k}:[{len(self.__dict__[k])} items] "
            else:
                out += f"{k}:{self.__dict__[k]} "
        return out


class EntityFile(NoitaBinFile):
    def __init__(self, filename="./save00/ent/entities_39998.bin"):
        super().__init__(filename)
        log.info(self.short_filename)
        num = int(self.short_filename.split("entities_")[1].split(".bin")[0])
        log.info(f"for coords {num_to_coords(num)}")
        self.read_file()
        #try_strings(self, filter = b"data/entities")
        #return
        self.c1 = self.read_int()  # 2
        assert self.c1 == 2
        self.schema = self.read_string()  # c8ecfb341d22516067569b04563bff9c
        assert self.schema == b'c8ecfb341d22516067569b04563bff9c'
        #Entity

        #return
        self.count = self.read_int()
        log.debug('count %s', self.count)
        if self.count == 0: return
        self.entities = []
        self.adjustments = []
        for i in range(self.count):
            j = 0
            log.info("adjustments: %s", self.adjustments)
            for e in self.entities:
                log.info(f"{j: 5d} {e}")
                j+=1
            j = 0
            for e in self.entities:
                j += 1
                if len(e.adjustments):
                    log.info(f"{j} {e.adjustments}")
            log.debug(f"========================================================")
            log.info(f"=========== entity {i+1} / {self.count} ===============")
            log.debug(f"========================================================")
            if adj := next_entity(self):
                log.debug(f"!!ent {i} adjust {adj}")
                self.adjustments.append((i, adj))  # issue was in previous ent
                self.entities[i-1].raw_adjust = self.contents[self.read_pos-adj:self.read_pos]
                log.warning(f"add adjustment {(adj)} {self.read_pos-adj}-{self.read_pos} {self.contents[self.read_pos-adj:self.read_pos]}")
                log.warning(self.entities[i-1].component_items[-1])
                sys.exit(2)
            #with open("entity-bound.txt", "a") as f:
            #    f.write(f"{self.read_pos: 10d} {hex_readable(self.contents[self.read_pos-4:self.read_pos])}\n")
            ent = Entity(self)
            log.debug(ent)
            self.entities.append(ent)
        i = 0
        while self.read_pos != len(self.contents):
            1/0
            if self.read_pos + 25 > len(self.contents):
                diff = len(self.contents) - self.read_pos
                self.read_pos -= diff
                self.adjustments.append((len(self.entities), diff))
                break
            if adj := next_entity(self):
                log.warning(f"!!ent extra {i+self.count} adjust {adj}")  # issue was in previous ent
                self.adjustments.append((i+self.count,adj))
                self.entities[self.count+i-1].raw_adjust = self.contents[self.read_pos-adj:self.read_pos]
                log.warning(f"add adjustment {(adj)} {self.read_pos-adj}-{self.read_pos} {self.contents[self.read_pos-adj:self.read_pos]}")
                log.warning(self.entities[i-1].component_items[-1])
                sys.exit(2)
            ent = Entity(self)
            log.info(ent)
            self.entities.append(ent)
            log.info(f"{self.short_filename} {self.read_pos} / {len(self.contents)} to go: {len(self.contents) - self.read_pos}")
            #log.debug(self.peek(100))
            #raise ValueError
            i += 1
        #log.debug(tmp)
        component_adjustments = []
        i=0
        card_action = 0
        for ent in self.entities:
            i+=1
            if b"card_action" in ent.tags:
                card_action += 1
            if len(ent.adjustments):
                component_adjustments.append((i, ent.adjustments))
            #log.debug(f"{i: 5d} {ent}")
        log.info(f"{self.short_filename} for coords {num_to_coords(num)}")
        log.info(f"file count: {self.count} actual {len(self.entities)}")
        log.info("adjustments: %s", self.adjustments)
        for adjustment in self.adjustments:
            adj_comp = self.entities[adjustment[0] - 1].component_items[-1]
            log.warning(f"{adjustment} {adj_comp.__class__.__name__}")
            log.warning(adj_comp)
            log.warning(adj_comp.len_bytes())
            end_pos = adj_comp._start_pos + adj_comp.len_bytes()
            adj_end_pos = end_pos + adjustment[1]
            log.warning(hex_readable(self.contents[adj_comp._start_pos:end_pos]))
            log.warning(hex_readable(self.contents[end_pos:adj_end_pos]))
        log.info("component_adjustments %s", component_adjustments)
        for adjustment in component_adjustments:
            for adj2 in adjustment[1]:
                component = self.entities[adjustment[0]-1].component_items[adj2[0]-1]
                raws = component.raws()
                #raws = {k: next_string(raws[k]) for k in raws}
                log.warning(f"{adjustment} {len(self.entities[adjustment[0] - 1].component_items)} {component.__class__.__name__} {raws}")
                global component_adjustment_dict
                if component.__class__.__name__ not in component_adjustment_dict:
                    component_adjustment_dict[component.__class__.__name__] = []
                component_adjustment_dict[component.__class__.__name__].append(adjustment)
                #log.debug(getattr(component, "raw_adjust"))
        log.debug("card_action: %s %s", card_action, self.count+card_action)
        i = 0
        cnt = 0
        ttl = 0
        for e in self.entities:
            i += 1
            if e.children:
                cnt += 1
                ttl += e.children
                #log.debug(f"footer {e.footer} for {i} {e.ent_file}")
        log.debug(f"{cnt} footers totaling {ttl} {ttl + self.count} {len(self.entities)}")
        return

        log.debug(len(self.contents))
        for i in range(1):
            out = "\n"
            out += f"i {i}\n"
            out += self.contents[self.read_pos:self.read_pos+50].hex(' ') + "\n"
            out += f"{self.contents[self.read_pos:self.read_pos+50]}" + "\n"
            tmp = self.read_int()
            out += f"{tmp}\n"
            remaining = len(self.contents) - self.read_pos
            candidate_obj_size = remaining/(tmp or 0.00000001)
            out += f"count? {candidate_obj_size} {remaining}\n"
            if candidate_obj_size > 1:
                remainder = (remaining % int(candidate_obj_size))
                out += f"remainder {remainder}\n"
                if 200 > remainder > 0:
                    out += self.contents[0-remainder:].hex(' ') + "\n"
                #if 0 < remainder < 200:
            log.debug(out)
        #try_strings(self)
        return


def next_entity(file: NoitaBinFile):
    start_pos = file.read_pos
    #log.debug("start looking at", start_pos)
    search_index = list(range(-20, 100))
    search_index.sort(key=lambda i: abs(i))
    search_index += list(range(-20, -100, -1))
    for i in search_index:
        file.read_pos = start_pos + i
        #log.debug("::::", i, file.read_pos, start_pos)
        #log.debug(file.peek(40))
        try:
            name = file.read_string(quiet=True)
            #log.debug("name", name)
            b1 = file.read_byte()
            #log.debug("b1", b1)
            ent_file = file.read_string(quiet=True)
            #log.debug("ent_file", ent_file)
            tags = file.read_string(quiet=True)
            #log.debug("tags", tags)
            transform = Transform(file, quiet=True)
            #log.debug("transform", transform)
            components = file.read_int()
            #log.debug("components", components)
            if (
                ent_file == b"??SAV/player.xml" or (
                    ent_file.startswith(b'data/entities/') and
                    ent_file.endswith(b'.xml')
                ) or
                name == b"inventory_quick"
            ):
                file.read_pos = start_pos + i
                #log.debug(file.read_pos, start_pos, i)
                if i:
                    log.warning(f"next_entity adjusting read position! {i}  {readable_bytes(file.contents[file.read_pos - i:file.read_pos])}")
                    #with open("entity-bound.txt", "a") as f:
                    #    f.write(f"{file.read_pos: 10d} {hex_readable(file.contents[file.read_pos-20:file.read_pos+20])} {file.short_filename} ent\n")
                return i
        except Exception as e:
            pass
            #log.debug(e)


def next_component(file: NoitaBinFile):
    start_pos = file.read_pos
    search_index = list(range(-20, 50))  # PixelSpriteComponent can be VERY big??
    search_index.sort(key=lambda i: abs(i))
    for i in search_index:
        file.read_pos = start_pos + i
        try:
            #log.debug(i, file.read_pos, start_pos, file.peek(20))
            component_type = file.read_string(quiet=True)
            b1 = file.read_byte()
            b2 = file.read_byte()
            base_unk1 = file.read_string(quiet=True)
            #log.debug(component_type, b1, b2, base_unk1)
            if (
                component_type.endswith(b'Component') and
                b1 in [0, 1] and
                b2 in [0, 1]
            ):
                file.read_pos = start_pos + i
                if i:
                    log.warning("next_component adjusting read position! %s %s", i, readable_bytes(file.contents[file.read_pos-i:file.read_pos]))
                    #with open("entity-bound.txt", "a") as f:
                    #    f.write(f"{file.read_pos: 10d} {hex_readable(file.contents[file.read_pos-20:file.read_pos+20])} {file.short_filename} comp\n")
                #log.debug(f"found next component after {i}")
                return i
        except Exception as e:
            pass
            #log.debug(e)


def raws_and_strings(file: NoitaBinFile, read_len):
    global next_item
    if next_item == "entity":
        log.info("looking for next entity in %s", hex_readable(file.peek(1000)))
    log.info(f"autoread: reading {read_len} next item {next_item}")
    out = []
    raw_read = 0
    min_len = 0
    while raw_read < read_len:
        next_str_pos = (next_string(file.peek(read_len-raw_read)) or (read_len, ''))[0]
        if next_str_pos < read_len-raw_read:
            if next_item == "component":
                if next_str_pos:
                    log.debug(f"autoread: skipping to string {next_str_pos}")
                    out.append(file.skip(next_str_pos))
                    min_len += next_str_pos
                    log.debug(f"autoread: got raw before str {out[-1]}")
                else:
                    log.debug(f"autoread: already at next string")
                out.append(file.read_string())
                log.debug(f"autoread: got string {out[-1]}")
                if out[-1].endswith(b'Component'):
                    compname = out.pop()
                    rewind = len(compname) + 4
                    log.info(f"autoread: rewinding {rewind} due to hitting next component! {compname}")
                    file.read_pos -= rewind
                    min_len -= rewind
                    log.info("min len %s", min_len)
                    return out
            elif next_item == "entity":
                log.debug(f"autoread: scanning for entity until string at {next_str_pos}")
                ent_scan_start_pos = file.read_pos
                for ent_scan_i in range(next_str_pos):
                    file.read_pos = ent_scan_start_pos + ent_scan_i
                    try:
                        peek_entity = Entity(file, peek=True)
                        log.info(f"autoread: got valid entity after {ent_scan_i}, peek: {peek_entity}")
                        raw_to_read = file.read_pos - ent_scan_start_pos - 4  # footer
                        file.read_pos = ent_scan_start_pos
                        out.append(file.skip(raw_to_read))
                        min_len += raw_to_read
                        log.info("min len %s", min_len)
                        return out
                    except:
                        pass
                log.debug(f"autoread: no entity in scan")
                file.read_pos = ent_scan_start_pos
                out.append(file.skip(next_str_pos))
                min_len += next_str_pos + 4
                log.debug(f"autoread: got raw before str {out[-1]}")
                out.append(file.read_string())
                log.debug(f"autoread: got string {out[-1]}")
            raw_read += next_str_pos + 4  # raws to get to string + empty string as raw: 0x00 * 4
        else:
            out.append(file.skip(read_len-raw_read))
            log.debug(f"autoread: got raw only {out[-1]} {read_len-raw_read}")
            min_len += read_len-raw_read
            raw_read += read_len-raw_read
    log.info(f"autoread: complete")
    log.info("min len %s", min_len)
    return out


def get_component_class(file: NoitaBinFile) -> Type[BaseComponent] | str:
    log.debug("get_component_class start peek %s", readable_bytes(file.peek(200)))
    component_type = file.read_string()
    return getattr(sys.modules[__name__], component_type.decode(), component_type.decode())


def make_component(file: NoitaBinFile):
    log.debug("make_component start peek %s", readable_bytes(file.peek(200)))
    component_type = file.read_string()
    component_class = getattr(sys.modules[__name__], component_type.decode(), None)
    if component_class is None:
        log.warning(f"component {component_type.decode()} does not exist, trying to generate")
        autogenerate_component(file)
        sys.exit()
    return getattr(sys.modules[__name__], component_type.decode())(file)


def autogenerate_component(file: NoitaBinFile, component_class):
    log.warning(f"autogenerating {component_class}")
    out = [f"class {component_class}(BaseComponent):\n    def __init__(self, file: NoitaBinFile):\n        super().__init__(file)"]
    comp = BaseComponent(file)
    i_raw = 1
    i_str = 1
    while True:
        start_pos = file.read_pos
        next_str_info = next_string(file.peek(len(file.contents) - file.read_pos))
        log.info(next_str_info)
        next_pos = next_str_info[0]
        if next_pos:
            tmp = file.skip(next_pos)
            log.info(f"skip {next_pos}  # {hex_readable(tmp)}")
            out.append(f"        self.raw{i_raw} = file.skip({next_pos})  # {hex_readable(tmp)}")
            i_raw += 1
        try:
            component_type = file.read_string(quiet=True)
            assert component_type.endswith(b'Component')
            b1 = file.read_byte()
            assert b1 in [0, 1]
            b2 = file.read_byte()
            assert b2 in [0, 1]
            base_unk1 = file.read_string(quiet=True)
            print("================= component finished =================")
            print("\n".join(out))
            file.read_pos = start_pos
            log.debug(readable_bytes(file.peek(100)))
            return comp
        except:
            file.read_pos = next_pos + start_pos
            tmp = file.read_string()
            log.info(f"read string  # {tmp}")
            out.append(f"        self.str{i_str} = file.read_string()  # {tmp}")
            i_str += 1


if __name__ == '__main__':
    '''ef = EntityFile("/minecraft/New folder/entities_41407.bin")
    print([str(e.ent_file) for e in ef.entities])
    for e in ef.entities:
        for c in e.component_items:
            c.len_bytes()'''

    #EntityFile("./save00/ent/entities_31999.bin")
    '''sys.exit()
    start = 845
    filelist = os.listdir("./save00/ent/")'''
    filelist = os.listdir("/minecraft/noita/New folder/")
    start = 0
    log.setLevel("WARNING")
    for i in range(start, len(filelist)):
        try:
            EntityFile("/minecraft/noita/New folder/" + filelist[i])
        except Exception as e:
            log.error(f"{i} {filelist[i]}")
            #global component_adjustment_dict
            pprint(component_adjustment_dict)
            raise
    #global component_adjustment_dict
    pprint(component_adjustment_dict)

    #EntityFile("./save00/ent/entities_-3911.bin")
    #EntityFile('./save00/ent/entities_39998.bin')
    #EntityFile('./save00/ent/entities_-28006.bin')
    #EntityFile('./save00/ent/entities_-28007.bin')
    #EntityFile('./save00/ent/entities_-26006.bin')
    #EntityFile('./save00/ent/entities_3999.bin')
    #EntityFile('./save00/ent/entities_63858.bin')
    #EntityFile('./save00/ent/entities_64068.bin')
    #EntityFile('./save00/ent/entities_16440.bin')
    #EntityFile('./save00/ent/entities_43532.bin')
