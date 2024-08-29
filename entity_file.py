import math
import os
import sys
import psutil
from json import JSONEncoder
from logging import lastResort
from pprint import pprint, pformat
from typing import List, Type

from constants import WORLD_PATH, KEEP_ALL_WORLDS_DIST, AGGRO_CLEAN_DIST, ALWAYS_KEEP, ALWAYS_PRUNE, DEBUG
from tools.conversions import hex_readable, next_string, is_valid_string, ReadableHex, ReadableBytes, BytesToPixels, \
    readable_bytes, bytes_to_int
from tools.coords import chunk_to_num, get_world_from_x, num_to_coords, coords_to_num, get_chunk
from noita_bin_file import NoitaBinFile, NoitaRaw, NoitaString, NoitaBool, NoitaInt
import logging
import verboselogs
from verboselogs import VerboseLogger as getLogger
import coloredlogs
from json import JSONEncoder
import json

DEBUG_FORCE_AUTOCOMPONENT = False


def to_dict(obj, raw_as="length", hex_group=1):
    #print(obj)
    if isinstance(obj, NoitaRaw):
        if raw_as == "hex":
            return obj.hex(' ', hex_group)
        if raw_as == "hex_readable":
            return hex_readable(obj)
        if raw_as == "bytes":
            return hex_readable(obj)
        if raw_as == "both":
            return {"hex": obj.hex(' ', -4), "bytes": readable_bytes(obj)}
        if raw_as == "length":
            return len(obj)
    if isinstance(obj, NoitaString):
        return obj.decode()
    if isinstance(obj, EntityFile):
        return {obj.short_filename: [to_dict(e) for e in obj.entities]}
    if isinstance(obj, list):
        return [to_dict(o) for o in obj]
    if isinstance(obj, Entity):
        return {k: to_dict(v) for k, v in obj.__dict__.items()}
    #if isinstance(obj, Transform):
    #    return obj.__dict__
    #if isinstance(obj, BaseComponent):
    #    return obj.__dict__
    if isinstance(obj, (int, float)):
        return obj
    return {k: to_dict(v) for k, v in obj.__dict__.items()}


verboselogs.install()
coloredlogs.install(level='SPAM', fmt='%(asctime)s %(levelname)s %(message)s', isatty=True, level_styles={
    'spam': {'color': 'blue', 'faint': True},
    'debug': {'color': 'blue'},
    'info': {'color': 'green'},
    'warning': {'color': 'yellow'},
    'error': {'color': 'red'},
})
#coloredlogs.install(fmt='%(asctime)s,%(msecs)03d %(hostname)s %(name)s[%(process)d] %(levelname)s %(message)s')
log = getLogger("entity_file")
next_item = ""


class Transform:
    @classmethod
    def from_file(cls, file: NoitaBinFile, quiet=False):
        x = file.read_float()
        y = file.read_float()
        scale_x = file.read_float()
        scale_y = file.read_float()
        rotation = file.read_float()
        try:
            coord_x, coord_y = file.coords()
            file_cx, file_cy = get_chunk(file.short_filename)
        except ValueError as e:
            log.debug(e)
            coord_x = coord_y = file_cx = file_cy = 0
        #if self.x != 0.0 and not coord_x <= self.x <= coord_x + 512 and not quiet:
        if file_cx != math.floor(x / 512) and not quiet:
            log.debug('x out of range')
            log.debug("filename %s computed at: %s, %s  coords: %s %s (num %s)  diff %s %s",
                      file.short_filename, coord_x, coord_y, x, y, coords_to_num(x, y), x - coord_x, y - coord_y)
            #sys.exit(0)
            #raise ValueError("entity out of bounds! x", self.x, coord_x, coord_x - self.x)
        #if self.y != 0.0 and not coord_y <= self.y <= coord_y + 512 and not quiet:
        if file_cy != math.floor(y / 512) and not quiet:
            log.debug('y out of range')
            log.debug("filename %s computed at: %s, %s  coords: %s %s (num %s)  diff %s %s",
                      file.short_filename, coord_x, coord_y, x, y, coords_to_num(x, y), x - coord_x, y - coord_y)
            #sys.exit(0)
            #raise ValueError("entity out of bounds! y", self.y, coord_y,  coord_y - self.y)
        return cls(x, y, scale_x, scale_y, rotation)

    def __init__(self, x=0.0, y=0.0, scale_x=1.0, scale_y=1.0, rotation=0.0):
        self.x = x
        self.y = y
        self.scale_x = scale_x
        self.scale_y = scale_y
        self.rotation = rotation

    def to_dict(self, sparse=True, **kwargs):
        ret = {'coords': (self.x, self.y)}
        if not sparse:
            if self.scale_x != 1.0 or self.scale_y != 1.0:
                ret['scale'] = (self.scale_x, self.scale_y)
            if self.rotation != 0.0:
                ret['rotation'] = self.rotation
        return ret

    def __str__(self):
        return f"{self.x, self.y} {self.scale_x, self.scale_y} {self.rotation}"

    def __eq__(self, other: "Transform"):
        return (
            self.x == other.x and
            self.y == other.y and
            self.scale_x == other.scale_x and
            self.scale_y == other.scale_y and
            self.rotation == other.rotation
        )


class BaseComponent:
    def __init__(self, file: NoitaBinFile):
        self._start_pos = file.read_pos
        self.b1 = file.read_byte()
        #assert self.b1 == 1
        self.b2 = file.read_byte()  # no children?
        #assert self.b2 == 1
        self.base_unk1 = file.read_string()  # enabled_in_world?
        log.spam("base: %s %s %s %s", self.b1, self.b2, self.base_unk1, self.__class__)
        log.spam("base end peek %s", ReadableHex(file.peek(200)))

    def to_dict(self, sparse=True, **kwargs):
        defaults = {
            'name': b'',
            'b1': 1,
            'b2': 1,
            'base_unk1': b'',
        }
        try:
            ret = {"component": self.__class__.__name__}
            if sparse:
                ret.update({k: (v.to_dict(sparse=sparse, **kwargs) if not isinstance(v, list) else [i.to_dict(sparse=sparse, **kwargs) for i in v]) for k, v in self.__dict__.items() if k not in ('_start_pos',) and not isinstance(v, NoitaRaw) and v != defaults.get(k, b'')})
            else:
                ret.update({k: (v.to_dict(sparse=sparse, **kwargs) if not isinstance(v, list) else [i.to_dict(sparse=sparse, **kwargs) for i in v]) for k, v in self.__dict__.items() if k not in ('_start_pos',)})
            return ret
        except:
            print()
            print("!!!!!!!!!!!!!!!!")
            print(self)
            raise

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
                out.append(ReadableHex(item))
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

    def __str__(self):
        return repr(self)

    def __repr__(self):
        out = f"<{self.__class__.__name__}\n"
        for k, v in self.__dict__.items():
            if k == '_start_pos' or (k in ('b1', 'b2') and v == 1):
                continue
            if isinstance(v, NoitaRaw):
                out += f"    {k}:{ReadableHex(v)}\n"
            elif isinstance(v, list):
                list_strs = []
                for item in v:
                    if isinstance(item, NoitaString):
                        list_strs.append(item.decode(errors="replace"))
                    else:
                        list_strs.append(hex_readable(item))
                list_strs = '\n        '.join(list_strs)
                out += f"    {k}:[{list_strs}]\n"
            else:
                out += f"    {k}:{v}\n"
        return out + f"id {hex(id(self))}>"


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
        self.name = file.read_string()
        self.raw1 = file.skip(32)
        self.custom = file.read_string()  # data/items_gfx/wands/custom/plant_02.png
        self.s2 = file.read_string()
        self.raw3 = file.skip(7)
        self.s3 = file.read_string()
        self.raw3 = file.skip(36)


class SimplePhysicsComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(1)


class SpriteComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        log.spam("SpriteComponent start peek %s %s", ReadableBytes(file.peek(1000)), self)
        self.sprite = file.read_string()
        self.raw = file.skip(35)
        self.anchor = file.read_string()  # float_right
        self.str1 = file.read_string()
        self.text = file.read_string()
        self.raw3 = file.skip(17)
        '''#with open("SpriteComponent2.txt", "a") as f:
        #    f.write(f"{file.read_pos: 10d} {self.b1} {self.b2} {ReadableHex(self.raw)} || {ReadableHex(self.raw2)} || {ReadableHex(self.raw3)} {self.sprite} {self.anchor} {self.text}\n")
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
            #log.warning(ReadableHex(self.raw + b"::" + file.peek(1000)))
        if False and self.raw[-4:] != b"\x00\x00\x00\x00" and (bytes_to_int(self.raw[-4:]) & 0b00000000100000001000000010000000 != 0b00000000100000001000000010000000):
            print("".join([f"{bin(b)[2:]:08}" for b in self.raw[-4:]]))
            print("VelocityComponent raw", ReadableHex(self.raw))
            print("VelocityComponen2", ReadableHex(file.peek(100)))
            self.subitems = file.read_int()
            for i in range(self.subitems):
                setattr(self, f"subitem{i}str", file.read_string())
                setattr(self, f"subitem{i}raw", file.skip(33))
        #print("VelocityComponent raw", ReadableHex(self.raw))
        #print("VelocityComponen2", ReadableHex(file.peek(100)))
        #if " i  n  v  e  n  t  o  r  y  _  q  u  i  c  k" in ReadableHex(file.peek(100)):
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
        #    f.write(f"{file.read_pos: 10d} {ReadableHex(self.raw)} {ReadableHex(self.raw2)} {ReadableHex(self.raw3)} {ReadableHex(self.raw4)} {ReadableHex(file.peek(2408))}\n")
        if self.raw4 == b'\x01':  # attached RGBA bitmap (reversed? at least, first byte seems to be opacity)
            #log.debug("!!!! continue?", self, "\n", bytes_to_int(file.peek(4))," ", bytes_to_int(file.peek(8)[-4:]), "\n", (file.peek(16464)).hex(' ', -4))
            self.bitmap_x = file.read_int()
            self.bitmap_y = file.read_int()
            self.bitmap_raw = file.skip(4 * self.bitmap_x * self.bitmap_y)
            log.debug("%s %s", self.bitmap_x, self.bitmap_y)
            log.debug(BytesToPixels(self.bitmap_raw, self.bitmap_x, self.bitmap_y))
        #    self.raw5 = file.skip(2408)
        #log.debug("PixelSpriteComponent end peek", ReadableBytes(file.peek(2586)))
        #log.debug(self)


class AudioComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
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
        log.spam(self)
        log.spam("InheritTransformComponent end peek %s", ReadableHex(file.peek(30)))
        #with open("ITCLog.txt", "a") as f:
        #    f.write(f"ITC at {file.read_pos: 10d} {file.peek(100)}\n")
        #if self.raw == b"\x00\x01":  # extend
        #    self.raw_extended = file.skip(4)


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
        self.raw1 = file.skip(26)  # params?
        self.script2 = file.read_string()
        self.script3 = file.read_string()
        self.script4 = file.read_string()  # not verified, but raw 0's
        self.script5 = file.read_string()
        self.script6 = file.read_string()
        self.script7 = file.read_string()
        self.script8 = file.read_string()  # not verified, but raw 0's
        self.script9 = file.read_string()
        self.script10 = file.read_string()  # not verified, but raw 0's
        self.script11 = file.read_string()  # not verified, but raw 0's
        self.script12 = file.read_string()
        self.script13 = file.read_string()
        self.script14 = file.read_string()
        self.script15 = file.read_string()
        self.script16 = file.read_string()  # not verified, but raw 0's
        self.script17 = file.read_string()  # not verified, but raw 0's
        self.script18 = file.read_string()  # not verified, but raw 0's
        self.script19 = file.read_string()  # not verified, but raw 0's
        self.script20 = file.read_string()  # not verified, but raw 0's
        self.script21 = file.read_string()  # not verified, but raw 0's
        self.script22 = file.read_string()  # not verified, but raw 0's
        self.script23 = file.read_string()
        self.script24 = file.read_string()  # not verified, but raw 0's
        self.script25 = file.read_string()
        self.raw25 = file.skip(9)



class ManaReloaderComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)

min_mac_raw = 999

class MaterialAreaCheckerComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(35)
        '''self.auto = raws_and_strings(file, 35)
        tmp = self.printable_autos_short()
        if tmp and isinstance(tmp[0], str):
            print(tmp)
        if tmp and isinstance(tmp[0], int):
            global min_mac_raw
            if min_mac_raw > tmp[0]:
                min_mac_raw = tmp[0]
                print(tmp)'''


class SpriteParticleEmitterComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.xmlfile = file.read_string()
        self.raw = file.skip(224)


class CellEaterComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        log.spam("CellEaterComponent start peek %s", ReadableHex(file.peek(200)))
        #self.raw = file.skip(23)
        #self.raw1 = file.skip(19)
        self.raw1 = file.skip(15)
        self.str1 = file.read_string()
        log.spam("CellEaterComponent raw1 peek %s %s", self, ReadableHex(file.peek(200)))
        self.count_unk = file.read_int()
        if self.count_unk > 1_000:
            raise ValueError(f"CellEaterComponent count too large: {self.count_unk}")
        self.unk = []
        for i in range(self.count_unk):
            self.unk.append(file.read_int())

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
        #    f.write(f"{file.read_pos: 10d} {ReadableHex(file.peek(100))}\n")
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
        self.raw = file.skip(139)
        #print("raw", ReadableHex(self.raw))
        self.dmgmats = file.read_string()
        self.multis = file.read_string()
        self.raw2 = file.skip(3)
        self.mat = file.read_string()
        self.filenames = file.read_string()  # data/ragdolls/root_grower_leaf/filenames.txt
        self.mat2 = file.read_string()
        self.raw4 = file.skip(12)
        #print("raw4", ReadableHex(self.raw4))
        self.mat3 = file.read_string()
        self.mat4 = file.read_string()
        self.raw5 = file.skip(9)
        #print("raw5", ReadableHex(self.raw5))
        self.mat5 = file.read_string()
        self.xmlfiles = file.read_string()
        self.xml2 = file.read_string()
        self.raw6 = file.skip(49)
        #print("raw6", ReadableHex(self.raw6))


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
        self.raw1 = file.skip(20)
        self.str1 = file.read_string()  # filter? b'[mimic_liquid]'
        self.raw2 = file.skip(20)


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

min_pc_raw = 999999
class ProjectileComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(14)  # 00 00 00 00 00 98 7f  J 00 00 00 00 01 00
        self.str1 = file.read_string()  # b'RESET'
        self.str2 = file.read_string()  # b'$action_reset'
        self.raw2 = file.skip(8)  # 00 00 00 00 00 00 00 00
        self.str3 = file.read_string()  # b'data/ui_gfx/gun_actions/unidentified.png'
        #self.raw3 = file.skip(200)
        self.raw3 = file.skip(155)
        self.str3b = file.read_string()
        self.raw3b = file.skip(41)
        #self.auto = raws_and_strings(file, 4000)
        #print(len(self.auto[0]))
        self.strtmp = file.read_string(sanity_check_len=9999999999)  # data/entities/particles/blood_sparks.xml,data/entities/particles/blood_sparks.xml,data/entities/particles/blood_sparks.xml,data/entities/particles/blood_sparks.xml,data/entities/particles/blood_sparks.xml,data/entities/particles/blood_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/gold_sparks.xml,data/entities/particles/blood_sparks.xml,data/entities/misc/homing.xml,data/entities/particles/tinyspark_white.xml,data/entities/misc/clipping_shot.xml,data/entities/misc/perks/food_clock.xml,data/entities/misc/perks/food_clock.xml,data/entities/misc/perks/food_clock.xml,data/entities/misc/perks/food_clock.xml,data/entities/misc/perks/food_clock.xml,data/entities/misc/perks/food_clock.xml,data/entities/misc/perks/food_clock.xml,data/entities/misc/perks/food_clock.xml,
        self.strtmp1b = file.read_string()
        self.strtmp2 = file.read_string()
        self.rawtmp2 = file.skip(53)
        self.str4 = file.read_string()  # b'brass'
        self.raw4 = file.skip(8)  # might be 2 empty strings? always 00
        self.str5 = file.read_string()
        self.raw5 = file.skip(11)
        self.str6 = file.read_string()
        #self.raw6 = file.skip(57)
        self.raw6 = file.skip(23)
        #print(self)
        self.str6b = file.read_string()
        self.raw6b = file.skip(30)
        self.str7 = file.read_string()  # b'data/particles/blast_out_electrocution.xml'
        self.raw7 = file.skip(24)
        self.str8 = file.read_string()
        self.raw8 = file.skip(41)
        self.str9 = file.read_string()  # b'fire'
        self.raw9 = file.skip(8)
        self.str10 = file.read_string()  # b'spark'
        self.raw10 = file.skip(95)
        self.str11 = file.read_string()
        self.raw11 = file.skip(30)
        self.str12 = file.read_string()
        self.raw12 = file.skip(19)
        self.str13 = file.read_string()  # b'hittable'
        self.str14 = file.read_string()  # b'player_unit'
        self.raw14 = file.skip(93)
        self.str15 = file.read_string()  # b'data/entities/misc/effect_electricity.xml,'
        self.raw15 = file.skip(7)


class CollisionTriggerComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw = file.skip(12)
        self.target = file.read_string()
        self.raw2 = file.skip(11)


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

min_pfc_raw = 0
class PathFindingComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw = file.skip(70)
        self.subitem_count = file.read_int()
        self.subitems = []
        for i in range(self.subitem_count):
            self.subitems.append(file.skip(12))  # probably 3 floats ex: 5.0, 15.0, 1.0  ??, ??, scale
        self.footer = file.skip(4)

        '''self.auto = raws_and_strings(file, 1000)
        tmp = self.printable_autos_short()
        if tmp and isinstance(tmp[0], str):
            print(tmp)
        if tmp and isinstance(tmp[0], int):
            print(ReadableHex(self.auto[0]))
            global min_pfc_raw
            if min_pfc_raw <= tmp[0]:
                if min_pfc_raw < tmp[0]:
                    min_pfc_raw = tmp[0]
                    print(tmp)'''


class PathFindingGridMarkerComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        #print(ReadableHex(file.peek(100)))
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

min_lec_raw = 999
class LaserEmitterComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(50)
        '''self.auto = raws_and_strings(file, 50)
        tmp = self.printable_autos_short()
        if tmp and isinstance(tmp[0], str):
            print(tmp)
        if tmp and isinstance(tmp[0], int):
            global min_lec_raw
            if min_lec_raw >= tmp[0]:
                #print(ReadableHex(self.auto[0]))
                if min_lec_raw > tmp[0]:
                    min_lec_raw = tmp[0]
                    print(tmp)'''


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

min_gec_raw = 999999
class GameEffectComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(4)
        self.str1 = file.read_string()
        self.raw2 = file.skip(18)
        self.str2 = file.read_string()  # data/entities/props/physics_ragdoll_part_electrified.xml
        self.raw3 = file.skip(64)


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
        #log.warning("UIIconComponent start %s", ReadableHex(file.peek(100)))
        '''ll = log.getEffectiveLevel()
        log.setLevel("WARNING")
        self.auto = raws_and_strings(file, 1000)
        log.warning(self.auto)
        log.setLevel(ll)
        return'''
        self.str1 = file.read_string()  # b'data/ui_gfx/status_indicators/neutralized.png'
        assert self.str1.startswith(b'data/ui_gfx/')
        #log.warning("UIIconComponent s1 %s", ReadableHex(file.peek(100)))
        self.str2 = file.read_string()  # b'$effect_neutralized'
        #log.warning("UIIconComponent s2 %s", ReadableHex(file.peek(100)))
        self.str3 = file.read_string()  # b'$effectdesc_neutralized'
        #log.warning("UIIconComponent s3 %s", ReadableHex(file.peek(100)))
        self.raw1 = file.skip(3)  # 00 01 00

        #log.warning("UIIconComponent self %s", self)
        #return
        '''if self.str2 == b'$perk_respawn':  # handle used lives?
            log.warning("UIIconComponent doing extra %s %s", self, ReadableHex(file.peek(100)))
            self.str1_ex = file.read_string()
            self.str2_ex = file.read_string()
            self.str3_ex = file.read_string()
            self.raw1_ex = file.skip(3)'''


class GameAreaEffectComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(4)  #  A e0 00 00
        self.str1 = file.read_string()  # b'hittable'
        self.raw2 = file.skip(8)  # 00 00 00  d 00 00 00 00


class PhysicsKeepInWorldComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(3)  # 01 01 00


class ShotEffectComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        log.spam("ShotEffectComponent 1 %s", ReadableHex(file.peek(8)))
        self.raw1 = file.skip(8)  # 00 00 00 00 00 00 00 00
        self.str1 = file.read_string()  # b'critical_hit_boost'
        log.spam("ShotEffectComponent 2 %s", ReadableHex(file.peek(9)))


class BlackHoleComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(16)  #  C 8c 00 00  @ c0 00 00  > 80 00 00  = cc cc cd


class MusicEnergyAffectorComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(18)  #  ? 80 00 00 00 00 00 00 01 00 00 00 c8 01 00 00 00 00


class StreamingKeepAliveComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(8)  # 00 00 00 00 00 00 00 00


class InteractableComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(4)  #  A    00 00
        self.str1 = file.read_string()  # b'$ui_longleg_love'
        self.str2 = file.read_string()  # b'longleg_love'
        self.raw2 = file.skip(4)  # 00 00 00 01


class PixelSceneComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.str1 = file.read_string()  # b'data/biome_impl/empty.png'
        self.raw1 = file.skip(4)  # 00 00 00 00
        self.str2 = file.read_string()  # b'data/biome_impl/vault/lab_puzzle_speed_background.png'
        self.raw2 = file.skip(14)  # 00 00 00  # c0 e0 00 00 c0 e0 00 00 01 00
        return
        self.str3 = file.read_string()  # b'data/entities/props/vault_machine_6.xml'
        self.str4 = file.read_string()  # b'pixelsprite'
        self.raw3 = file.skip(24)  #  G 8b  0 80  F 19  < 00  ? 80 00 00  ? 80 00 00 00 00 00 00 00 00 00 03


class LevitationComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(16)  #  A f0 00 00  > 99 99 9a  > e6  f  f 00 00 02  X


class ExplosionComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(9)  # 00 00 00 01 00  B    00 00
        self.str1 = file.read_string()  # b'data/particles/explosion_032.xml'
        self.raw2 = file.skip(24)  # 00 00 01 00 00 00 00  @ a0 00 00 00 00 00 00  ? 80 00 00  A    00 00 01
        self.str2 = file.read_string()  # b'data/entities/particles/particle_explosion/main_gunpowder_tiny.xml'
        self.raw3 = file.skip(41)  # 01  = a3 d7 0a 00 00 00 ff 00 00 00 d9 00 00 00 b4  A 00 00 00 01 01 00 00 00 00 00 00 00 0a 00 00 00 0a  ? 80 00 00 01 01
        self.str3 = file.read_string()  # b'fire'
        self.raw4 = file.skip(8)  # 00 00 00  P 00 00 00 00
        self.str4 = file.read_string()  # b'spark'
        self.raw5 = file.skip(129)  # 00 00  ' 10 00 00 00 05 00 00 00 07 00 00 00 14 00 00 00 01 00 00 00 07 00 00 00 14  > aa  ~ fa 00 00 00 00 00 00 05  W  0 00 00 00 0a 00 00 00 01 00 01 01 00 00 00 00  >  L cc cd  ? 80 00 00  ? 80 00 00  @ a0 00 00  C 16 00 00 00 00 00 00  B c8 00 00 00 00 00 00  ?  @ 00 00 01 00 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ff ff ff ff 00 00 00 00 00 00 00 00 00 01 ff ff ff ff


class AdvancedFishAIComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(8)  #  A 00 00 00  B 80 00 00


class AIAttackComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(28)  # 00 00 00  d  B  $ 00 00  C 96 00 00  B b4 00 00 00 00 00  - 00 00 00  ( 00 00 00  (
        self.str1 = file.read_string()  # b'attack_ranged'
        self.raw2 = file.skip(23)  # 00 00 00 00 04  A 00 00 00 c1  @ 00 00 00 00 00 00 00 00 00 00 00 00
        self.str2 = file.read_string()  # b'data/entities/projectiles/orb_pink_big_explosive.xml'
        self.raw3 = file.skip(18)  # 00 00 00 01 00 00 00 01 00 00  @  @ 00 00  A    00 00


class BossHealthBarComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(7)  # 01 00 00  C af 00 00


class EndingMcGuffinComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(8)  # 00 00 00 00 00 00 00 00


### from autosaves
class AudioListenerComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(4)


class DrugEffectComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(48)


class GameLogComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(3)
        self.log_entry_count = file.read_int()
        self.log_entries = []
        for i in range(self.log_entry_count):
            self.log_entries.append(file.read_string())
        #log.warning(len(self.auto))
        #log.warning(self)


class IngestionComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(32)
        self.str1 = file.read_string()
        self.raw2 = file.skip(4)


class InventoryGuiComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(6)


class KickComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        #self.raw1 = file.skip(61)
        self.raw1 = file.skip(57)
        self.str1 = file.read_string(sanity_check_len=1000)


class LiquidDisplacerComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(12)


class PlatformShooterPlayerComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(54)


class PlayerCollisionComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(8)


class TelekinesisComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(58)


class PhysicsPickUpComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(40)


class WalletComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(25)


class BiomeTrackerComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(4)


class PlayerStatsComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.i1 = file.read_int()
        self.f1 = file.read_float()
        self.f2 = file.read_float()

class DrugEffectModifierComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(48)


class WorldStateComponent(BaseComponent):  # OH LAWD HE COMIN
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        #self.raw1 = file.skip(78)
        ### wiki ###
        self.is_initialized = NoitaBool.from_file(file)  # 77
        self.time = file.read_float()  # 73
        self.time_total = file.read_float()  # 69
        self.time_dt = file.read_float()  # 65
        self.day_count = file.read_int()  # 61
        self.rain = file.read_float()  # 57
        self.rain_target = file.read_float()  # 53
        self.fog = file.read_float()  # 49
        self.fog_target = file.read_float()  # 45
        self.intro_weather = NoitaBool.from_file(file)  # 44
        self.wind = file.read_float()  # 40
        self.wind_speed = file.read_float()  # 36
        self.wind_speed_sin_t = file.read_float()  # 32
        self.wind_speed_sin = file.read_float()  # 28
        self.clouds_01_target = file.read_float()  # 24
        self.clouds_02_target = file.read_float()  # 20
        self.gradient_sky_alpha_target = file.read_float()  # 16
        self.sky_sunset_alpha_target = file.read_float()  # 12
        self.lightning_count = file.read_int()  # 8
        self.unk01 = file.skip(8)
        ### end wiki (partial) ###
        log.warning("WorldStateComponent self premap %s", self)

        self.lua_globals_len = file.read_int()
        self.lua_globals = {}
        for i in range(self.lua_globals_len):
            key = file.read_string()
            value = file.read_string()
            assert key not in self.lua_globals
            self.lua_globals[key] = value
        #self.auto = raws_and_strings(file, 10_000)
        #return
        self.unk02 = file.skip(20)
        self.session_stat_file = file.read_string()
        #self.auto = raws_and_strings(file, 10_000)
        #log.warning("WorldStateComponent auto %s", [i.to_dict() for i in self.auto])
        self.orbs_found_thisrun_count = file.read_int()  # num orbs?
        self.orbs_found_thisrun = []
        for i in range(self.orbs_found_thisrun_count):
            self.orbs_found_thisrun.append(file.read_int())
        self.flags_len = file.read_int()
        self.flags = []
        for i in range(self.flags_len):
            self.flags.append(file.read_string())
        self.changed_materials_len = file.read_int()
        self.changed_materials = []
        for i in range(self.changed_materials_len):
            self.changed_materials.append(file.read_string())
        #self.raw4 = file.skip(91)
        self.player_polymorph_count = file.read_int()  # poly count
        self.player_polymorph_random_count = file.read_int()  # poly rando
        self.player_did_infinite_spell_count = file.read_int()  # inf spell or trick kill mult
        self.player_did_damage_over_1milj = file.read_int()  # player_did_damage_over_1milj
        self.player_living_with_minus_hp = file.read_int()
        self.global_genome_relations_modifier = file.read_float()  # global_genome_relations_modifier
        self.mods_have_been_active_during_this_run = NoitaBool.from_file(file)
        self.twitch_has_been_active_during_this_run = NoitaBool.from_file(file)
        self.next_cut_through_world_id = file.read_int() # TODO uint32
        #self.perk_infinite_spells = NoitaBool.from_file(file) #WRONG
        #self.perk_trick_kills_blood_money = NoitaBool.from_file(file) #WRONG
        self.unk03 = file.skip(28)
        self.unk04 = file.read_float() #1.0 mFlashAlpha? no, 0 and this is 1.0
        self.unk05 = file.skip(29)
        '''self.unk4_09 = file.read_int()
        self.unk4_09_b = file.skip(4)
        self.unk4_10 = file.read_int()
        self.unk4_11 = file.read_int()
        self.unk4_12 = file.read_int()
        self.unk4_13 = file.read_int()
        self.unk4_14 = file.read_int()
        self.unk4_15 = file.read_float()
        self.unk4_16 = file.read_int()
        self.unk4_17 = file.read_int()
        self.unk4_18 = file.skip(4)
        self.unk4_19 = file.skip(4)
        self.unk4_20 = file.read_int()
        self.unk4_21 = file.skip(4)
        self.unk4_22 = file.read_int()
        self.unk4_23 = file.skip(1)'''
        self.material_everything_to_gold = file.read_string()
        self.material_everything_to_gold_static = file.read_string()
        self.unk06 = file.skip(19)
        log.warning("WorldStateComponent self %s", self)
        return
        self.auto = raws_and_strings(file, 10_000)
        log.warning("WorldStateComponent auto %s", [i.to_dict(raw_as="length") for i in self.auto])
        log.warning("WorldStateComponent auto %s", [i.to_dict(raw_as="hex") for i in self.auto])
        return
        next_portal_id = int #uint32 #1
        #?self.next_cut_through_world_id = file.read_int() #0
        self.perk_infinite_spells = bool #1
        self.perk_trick_kills_blood_money = bool #1
        self.perk_hp_drop_chance = int #0
        self.perk_gold_is_forever = bool #0
        self.perk_rats_player_friendly = bool #0
        self.EVERYTHING_TO_GOLD = bool
        #self.material_everything_to_gold = file.read_string()
        #self.material_everything_to_gold_static = file.read_string()
        self.INFINITE_GOLD_HAPPENING = bool
        self.ENDING_HAPPINESS_HAPPENING = bool
        self.ENDING_HAPPINESS_FRAMES = int #0
        self.ENDING_HAPPINESS = bool
        self.mFlashAlpha = file.read_float() #0
        self.DEBUG_LOADED_FROM_AUTOSAVE = int #0
        self.DEBUG_LOADED_FROM_OLD_VERSION = int #0

        ### wiki ###
        #log.warning("WorldStateComponent peak %s", ReadableHex(file.peek(1000)))

    def __str__(self):
        tmp_dict = self.__dict__.copy()
        log.warning(tmp_dict.get("flags"))
        tmp_dict["flags"] = len(tmp_dict.get("flags", []))
        log.warning(tmp_dict.get("lua_globals"))
        tmp_dict["lua_globals"] = len(tmp_dict.get("lua_globals", []))
        for k, v in tmp_dict.items():
            if isinstance(v, NoitaRaw):
                tmp_dict[k] = str(ReadableHex(v))
        return f"WorldStateComponent {pformat(tmp_dict)}"



class TemplateComponent(BaseComponent):
    def __init__(self, file: NoitaBinFile):
        super().__init__(file)
        self.raw1 = file.skip(8)
        log.debug(self)
        log.debug("TemplateComponent next string %s", next_string(file.peek(1000)))
        log.debug("TemplateComponent peek %s", ReadableHex(file.peek(200)))


class Entity:
    def __init__(self, file: "EntityFile | AutosaveFile", peek=False, allow_weird=False):
        self.start_pos = file.read_pos
        log.spam("entity start peek %s", ReadableBytes(file.peek(200)))
        self.name = file.read_string(quiet=peek)
        if not is_valid_string(self.name):
            raise ValueError(f"invalid string for name {self.name}")
        self.b1 = file.read_byte()
        log.spam('name %s %s', self.name, self.b1)
        self.ent_file = file.read_string(quiet=peek)
        #if self.ent_file == b"??SAV/world_state.xml":
        #    log.setLevel("DEBUG")
        if not is_valid_string(self.ent_file):
            raise ValueError(f"invalid string for ent_file {self.ent_file}")
        log.spam("ent file %s", self.ent_file)
        self.tags = file.read_string(quiet=peek)
        if not is_valid_string(self.tags):
            raise ValueError(f"invalid string for tags {self.tags}")
        log.spam('tags %s', self.tags)
        self.transform = Transform.from_file(file, quiet=peek)
        log.spam("transform %s", self.transform)
        self.components = file.read_int()
        log.spam("components %s", self.components)
        is_weird = False
        if not (
            self.name == b"inventory_quick" or
            self.ent_file.startswith(b'??STA/sessions') or (
                self.ent_file in (b"??SAV/player.xml", b"??SAV/world_state.xml") or
                (self.ent_file.startswith(b'data/') and self.ent_file.endswith(b'.xml')) or
                (self.ent_file.startswith(b'??S00/persistent/bones_new/') and self.ent_file.endswith(b'.xml'))
            ) or self.tags == b'perk_entity'
        ) or (
            0 < self.transform.x < 0.001 or 0 < self.transform.y < 0.001 or  # probably not valid floats
            self.tags.endswith(b'.xml')
        ):
            if not allow_weird:
                raise ValueError("bad entity", self)
            start_pos_weird_check = file.read_pos
            try:
                component_check = get_component_class(file)
            except:
                component_check = ""
            file.read_pos = start_pos_weird_check
            if not isinstance(component_check, str) and issubclass(component_check, BaseComponent):
                if peek:
                    log.warning("VERY weird entity (peek) %s %s", self, component_check)
                else:
                    is_weird = True
            else:
                raise ValueError("bad entity", self, component_check)
        if peek:
            file.read_pos = self.start_pos
            return
        log.spam("entity mid peek %s", ReadableBytes(file.peek(200)))
        self.component_items = []
        #if is_weird:
        #    log.warning("VERY weird entity 1 %s %s", self, ReadableHex(file.peek(40)))
        for i in range(self.components):
            log.spam(self)
            log.spam(self.component_items)
            log.spam("at %s / %s", file.read_pos, len(file.contents))
            log.spam("========================================================")
            log.debug("===== file %s  component %s / %s  pos %s/%s ==========", file.short_filename, i+1, self.components, file.read_pos, len(file.contents))
            log.spam("========================================================")
            try:
                component_class = get_component_class(file)
            except Exception as e:
                log.error("error reading entity: %s %s", e.__class__.__name__, e)
                adj = next_component(file)
                log.error("adjustment %s", adj)
                log.error("last component %s", self.component_items[-1].__class__.__name__)
                log.error("last component contents %s", self.component_items[-1])
                # force read as unknown component
                file.read_pos = self.component_items[-1]._start_pos
                comp = BaseComponent(file)
                comp._name = self.component_items[-1].__class__.__name__
                comp.auto = raws_and_strings(file, 100_000)
                for item in comp.auto:
                    if isinstance(item, NoitaRaw):
                        log.error("raw len %s", len(item))
                    else:
                        log.error(item)
                log.error(comp)
                raise
            global next_item
            next_item = "component" if i + 1 < self.components else "entity"
            comp_start_pos = file.read_pos
            if not isinstance(component_class, str):
                try:
                    comp = component_class(file)
                except Exception as e:
                    log.error("error reading component: %s", component_class.__name__, exc_info=True)
                    log.error("last component was %s", (self.component_items[-1] if self.component_items else "(no components)"))
                    file.read_pos = comp_start_pos
                    comp = BaseComponent(file)
                    log.error("base end peek: %s", ReadableHex(file.peek(100)))
                    log.error("base end obj %s", comp)
                    comp._name = component_class.__name__
                    comp.auto = raws_and_strings(file, 100_000)
                    for item in comp.auto:
                        if isinstance(item, NoitaRaw):
                            log.error("raw len %s", len(item))
                        else:
                            log.error(item)
                    log.error(comp)
                    raise

            else:
                log.warning("Unknown component '%s' in file %s attempting auto-read", component_class, file.short_filename)
                try:
                    comp = BaseComponent(file)
                    comp._name = NoitaString(component_class.encode())
                    comp.auto = raws_and_strings(file, 100_000)
                    #for item in comp.auto:
                    #    if isinstance(item, NoitaRaw):
                    #        log.error("raw len %s", len(item))
                    #    else:
                    #        log.error(item)
                    log.info(comp)
                except Exception as e:
                    log.error("error auto-reading component: %s", component_class, exc_info=True)
                    log.error("last component was %s", (self.component_items[-1] if self.component_items else "(no components)"))
                    if self.component_items:
                        file.read_pos = self.component_items[-1]._start_pos
                        last_comp = BaseComponent(file)
                        last_comp.auto = raws_and_strings(file, 100_000)
                        log.error("last comp as auto %s", last_comp)
                    file.read_pos = comp_start_pos
                    log.error("start peek: %s", ReadableHex(file.peek(100)))
                    raise

            #log.debug("---------------------")
            #log.debug(self)
            #log.debug(self.component_items)
            self.component_items.append(comp)
            #log.debug(comp)
            #log.debug("at", file.read_pos, len(file.contents))
            #log.debug(file.peek(1000))
        if self.name == b'' and self.ent_file == b'':  # always cast perk
            log.info('weird entity: %s %s', self, self.component_items)
        self.children = file.read_int()  # count of subitems
        self.child_items = []
        if is_weird:
            log.info("VERY weird entity %s\n%s", self, self.component_items)
        for i in range(self.children):
            log.spam("---==================================================---")
            log.debug("---===== file %s  entity child %s / %s  pos %s/%s ========---", file.short_filename, i+1, self.children, file.read_pos, len(file.contents))
            log.spam("---==================================================---")
            start_pos = file.read_pos
            try:
                ent = Entity(file)
            except Exception as e:
                log.error("error reading child entity: %s %s", e.__class__.__name__, e)
                file.read_pos = start_pos
                last_entity = find_next_entity(file, self)
                # force read as unknown component
                file.read_pos = last_entity.component_items[-1]._start_pos
                comp = BaseComponent(file)
                comp._name = last_entity.component_items[-1].__class__.__name__
                comp.auto = raws_and_strings(file, 100_000)
                for item in comp.auto:
                    if isinstance(item, NoitaRaw):
                        log.error("raw len %s", len(item))
                    else:
                        log.error(item)
                log.error(comp)
                raise
            log.debug("finished reading child entity %s/%s: %s", i+1, self.children, ent)
            self.child_items.append(ent)
        return

    def __str__(self):
        return repr(self)

    def __repr__(self):
        out = f"<Entity "
        for k, v in self.__dict__.items():
            if k == 'start_pos':
                continue
            if isinstance(v, list) and v:
                if k == "component_items":
                    out += f"{k}:{[f'{i}:{ci.__class__.__name__}' for i, ci in enumerate(v, start=1)]} "
                elif k == "child_items" and v:
                    out_str = "\n".join([f'           {i: 3d} {ci}' for i, ci in enumerate(v, start=1)])
                    out += f"\n            {k}:\n{out_str} "
                else:
                    out += f"{k}:[{len(v)} items] "
            elif isinstance(v, Transform) and v == Transform():
                continue
            elif isinstance(v, NoitaString) and v == b'':
                continue
            elif k == 'b1' and v == 0:
                continue
            else:
                out += f"{k}:{v} "
        return out + f" id:{hex(id(self))}>"

    def to_dict(self, sparse=True, **kwargs):
        defaults = {
            'name': b'',
            'b1': 0,
            'ent_file': b'',
            'tags': b'',
            'transform': Transform(0.0, 0.0, 1.0, 1.0, 0.0),
            'component_items': [],
            'child_items': [],
        }
        if sparse:
            ret = {}
            for k, v in defaults.items():
                val = getattr(self, k)
                if val != v:
                    if k in ('component_items', 'child_items'):
                        ret[k] = [c.to_dict(sparse=sparse, **kwargs) for c in val]
                    else:
                        ret[k] = val.to_dict(sparse=sparse, **kwargs)
        else:
            ret = {k: (v.to_dict(sparse=sparse, **kwargs) if not isinstance(v, list) else [i.to_dict(sparse=sparse, **kwargs) for i in v]) for k, v in self.__dict__.items() if k not in ('start_pos', 'component_items', 'child_items')}
            ret["component_items"] = [c.to_dict(sparse=sparse, **kwargs) for c in self.component_items]
            ret["child_items"] = [c.to_dict(sparse=sparse, **kwargs) for c in self.child_items]
        return ret


class EntityFile(NoitaBinFile):
    def __init__(self, filename, contents=b''):
        super().__init__(filename)
        log.debug("start reading %s", self.short_filename)
        #num = int(self.short_filename.split("entities_")[1].split(".bin")[0])
        #log.info("for coords %s", num_to_coords(num))
        self.context = {
            "current_entity": 0,
            "depth": 0,
        }
        self.read_file(contents)
        self.version = self.read_int()  # 2
        if not self.version == 2:
            raise ValueError("invalid header, expected 2 got %s" % self.version)
        self.schema = self.read_string()  # c8ecfb341d22516067569b04563bff9c
        if not self.schema == b'c8ecfb341d22516067569b04563bff9c':
            raise ValueError("invalid header, expected b'c8ecfb341d22516067569b04563bff9c' got %s" % self.schema)
        self.count = self.read_int()
        log.debug('file %s entity count %s', self.short_filename, self.count)
        #if self.count == 0:
        #    return
        self.entities = []
        #i=0
        #while self.read_pos != len(self.contents):
        for i in range(self.count):
            log.spam("========================================================")
            log.debug("======= file %s  entity %s / %s  pos %s/%s ===========", self.short_filename, i+1, self.count, self.read_pos, len(self.contents))
            self.context["current_entity"] = i + 1
            log.spam("========================================================")
            start_pos = self.read_pos
            try:
                ent = Entity(self)
            except Exception as e:
                log.debug("entity read error", exc_info=True)
                self.read_pos = start_pos
                find_next_entity(self)
                raise
            log.debug("finished reading root entity %s/%s: %s", i+1, self.count, ent)
            self.entities.append(ent)
            #i+=1
        if len(self.contents) != self.read_pos:
            raise ValueError("file not fully processed! %s %s" % (self.read_pos, len(self.contents)))

    def to_dict(self, sparse=True, **kwargs):
        ret = {
            self.short_filename: {
                'entities': [e.to_dict(sparse=sparse, **kwargs) for e in self.entities]
            }
        }
        if not sparse:
            ret.update({k: (v.to_dict(sparse=sparse, **kwargs) if not isinstance(v, list) else [i.to_dict(sparse=sparse, **kwargs) for i in v]) for k, v in self.__dict__.items() if k not in ('entities', 'short_filename', 'filename', 'read_pos', 'contents')})
        return ret


next_entity_search_index = list(range(-20, 100))
next_entity_search_index.sort(key=lambda i: abs(i))
next_entity_search_index += list(range(-20, -100, -1))
def find_next_entity(file: EntityFile, last_entity=None):
    log.error("find_next_entity: read entity error, checking nearby")
    if last_entity is None:
        log.debug("last entity not provided")
        last_entity = file.entities[-1]
        log.debug("last root entity determined to be %s", last_entity)
    while len(last_entity.child_items):
        last_entity = last_entity.child_items[-1]
        log.debug("last entity child %s", last_entity)
    log.error(f"find_next_entity: last component of last entity was {last_entity.component_items[-1]}")
    start_pos = file.read_pos
    for i in next_entity_search_index:
        file.read_pos = start_pos + i
        log.spam("find_next_entity: next entity search %s %s %s", i, file.read_pos, start_pos)
        log.spam("find_next_entity: next entity search peek %s", file.peek(40))
        try:
            peek_ent = Entity(file, peek=True)
            log.spam("find_next_entity: entity search peek @ %s %s", i, peek_ent)
            if i:
                log.error(f"find_next_entity: entity read position off by {i}  {ReadableBytes(file.contents[file.read_pos - i:file.read_pos])}")
                return last_entity
            else:
                log.error("find_next_entity: next entity search found, no offset?? %s %s %s %s", i, file.read_pos, start_pos, ReadableHex(file.peek(20)))
                return last_entity
        except Exception as e:
            #pass
            log.spam("find_next_entity: next entity search: no match: %s %s", e.__class__, e)
    log.error("find_next_entity: nothing found in search range!")
    file.read_pos = start_pos
    log.error("find_next_entity: %s", ReadableHex(file.peek(1000)))
    log.error("find_next_entity: %s", last_entity)
    return last_entity


component_stats = {}
next_component_search_index = list(range(-20, 50))
next_component_search_index.sort(key=lambda i: abs(i))
def next_component(file: NoitaBinFile):
    start_pos = file.read_pos
    for i in next_component_search_index:
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
                component_stats[component_type] = component_stats.get(component_type, 0) + 1
                file.read_pos = start_pos + i
                if i:
                    log.warning("next_component adjusting read position! %s %s", i, ReadableBytes(file.contents[file.read_pos-i:file.read_pos]))
                    #with open("entity-bound.txt", "a") as f:
                    #    f.write(f"{file.read_pos: 10d} {ReadableHex(file.contents[file.read_pos-20:file.read_pos+20])} {file.short_filename} comp\n")
                #log.debug(f"found next component after {i}")
                return i
        except Exception as e:
            pass
            #log.debug(e)


def raws_and_strings(file: NoitaBinFile, read_len, next_item_override=""):
    if not next_item_override:
        global next_item
    else:
        next_item = next_item_override
    if next_item == "entity":
        log.info("looking for next entity in %s", ReadableHex(file.peek(1000)))
    log.info("autoread: reading %s next item %s", read_len, next_item)
    out = []
    raw_read = 0
    min_len = 0
    while raw_read < read_len:
        if read_len + file.read_pos > len(file.contents) - 4:  # leave room for final "children" int
            read_len = len(file.contents) - file.read_pos - 4 + raw_read
            log.debug("autoread: len shortened due to EOF: %s", read_len)
        next_str_pos = (next_string(file.peek(read_len-raw_read+500)) or (read_len, ''))[0]
        if next_str_pos < read_len-raw_read:
            if next_item == "component":
                if next_str_pos:
                    log.debug("autoread: skipping to string %s", next_str_pos)
                    out.append(file.skip(next_str_pos))
                    min_len += next_str_pos
                    log.debug("autoread: got raw before str %s", out[-1])
                else:
                    log.debug("autoread: already at next string")
                out.append(file.read_string())
                log.debug("autoread: got string %s", out[-1])
                if out[-1].endswith(b'Component'):
                    compname = out.pop()
                    rewind = len(compname) + 4
                    log.info("autoread: rewinding %s due to hitting next component! %s", rewind, compname)
                    file.read_pos -= rewind
                    min_len -= rewind
                    log.info("min len %s", min_len)
                    for i in out:
                        log.info("%s %s", i.__class__.__name__, i.raw_len)
                    return out
            elif next_item == "entity":
                ent_scan_start_pos = file.read_pos
                if next_str_pos:
                    log.debug("autoread: scanning for entity until string at %s", next_str_pos)
                    err_msgs = []
                    for ent_scan_i in range(next_str_pos+100):
                        file.read_pos = ent_scan_start_pos + ent_scan_i
                        try:
                            peek_entity = Entity(file, peek=True)
                            log.info("autoread: got valid entity after %s, peek: %s", ent_scan_i, peek_entity)
                            raw_to_read = file.read_pos - ent_scan_start_pos - 4  # footer
                            file.read_pos = ent_scan_start_pos
                            out.append(file.skip(raw_to_read))
                            min_len += raw_to_read
                            log.info("min len %s", min_len)
                            for i in out:
                                log.info("%s %s", i.__class__.__name__, i.raw_len)
                            return out
                        except Exception as e:
                            err_msgs.append(str(e.args[0]))
                    log.debug("autoread: no entity in scan %s", err_msgs)
                    file.read_pos = ent_scan_start_pos
                    out.append(file.skip(next_str_pos))
                    min_len += next_str_pos + 4
                    log.debug("autoread: got raw before str (end as int %s) %s", bytes_to_int(out[-1][-4:]), out[-1])
                else:
                    log.debug("autoread: already at next string")
                out.append(file.read_string())
                log.debug("autoread: got string %s", out[-1])
            raw_read += next_str_pos + 4  # raws to get to string + empty string as raw: 0x00 * 4
        else:
            out.append(file.skip(read_len-raw_read))
            log.debug("autoread: got raw only %s %s", out[-1], read_len-raw_read)
            if out[-1] == b'':
                out.pop()
            min_len += read_len-raw_read
            raw_read += read_len-raw_read
    log.info("autoread: complete")
    log.info("autoread: strings %s", len([o for o in out if isinstance(o, NoitaString)]))
    log.info("min len %s", min_len)
    return out


def get_component_class(file: NoitaBinFile) -> Type[BaseComponent] | str:
    log.spam("get_component_class start peek %s", ReadableBytes(file.peek(200)))
    start_pos = file.read_pos
    component_type = file.read_string()
    if not is_valid_string(component_type):
        raise ValueError(f"invalid string for creating component {ReadableBytes(component_type)}")
    component_type = component_type.decode()
    if DEBUG_FORCE_AUTOCOMPONENT:
        return component_type
    return getattr(sys.modules[__name__], component_type, component_type)


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
            log.info("skip %s  # %s", next_pos, ReadableHex(tmp))
            out.append(f"        self.raw{i_raw} = file.skip({next_pos})  # {ReadableHex(tmp)}")
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
            log.debug(ReadableBytes(file.peek(100)))
            return comp
        except:
            file.read_pos = next_pos + start_pos
            tmp = file.read_string()
            log.info("read string  # %s", tmp)
            out.append(f"        self.str{i_str} = file.read_string()  # {tmp}")
            i_str += 1


def main():
    print(log.__dict__)
    process = psutil.Process()
    print(f"mem at start {process.memory_info().rss/1_048_576: .2f} MB")
    log.setLevel("INFO")
    from zipfile import ZipFile
    zip_path = f"{os.environ['LOCALAPPDATA']}/../LocalLow/Noita archive/"
    zipfilelist = [os.path.join(dp, f) for dp, dn, fn in os.walk(zip_path) for f in fn if f.endswith(".zip")]
    start = 0
    for i, zfn in enumerate(zipfilelist):
        if i < start:
            continue
        print(f"zipfile {i:{len(str(len(zipfilelist)))}}/{len(zipfilelist)}  {zfn}  {process.memory_info().rss/1_048_576: .2f} MB")
        zf = ZipFile(zfn, 'r')
        zfl = [f for f in zf.filelist if "entities_" in f.filename]
        for j, f in enumerate(zfl):
            if not j % 2000:
                #print(f"at {i:{len(str(len(filelist)))}}/{len(filelist)}  {100 * i / len(filelist): 3.2f}%...")
                log.info(f"zipfile {zfn} at {j:{len(str(len(zfl)))}}/{len(zfl)}  {100 * j / len(zfl): 3.2f}%... file {f.filename} {f.file_size}  {process.memory_info().rss/1_048_576: .2f} MB")
            try:
                ent = EntityFile(f"{zfn}/{f.filename}", zf.read(f))
            except Exception as e:
                sys.exit(9)
                if isinstance(e, KeyboardInterrupt):
                    raise
                log.setLevel("DEBUG")
                ent = EntityFile(f"{zfn}/{f.filename}", zf.read(f))
            #pprint(ent.to_dict(sparse=True, raw_as="length"))
        #sys.exit(0)
        #del zf

    sys.exit(0)
    path = f"{os.environ['LOCALAPPDATA']}/../LocalLow/Nolla_Games_Noita/save00/world/"
    filelist = [filepath for filepath in os.listdir(path) if filepath.startswith("entities_")]
    start = 0
    log.setLevel("INFO")
    full_dict = {}
    for i in range(start, len(filelist)):
        if not i % 200:
            print(f"at {i:{len(str(len(filelist)))}}/{len(filelist)}  {100 * i / len(filelist): 3.2f}%...")
        try:
            ef = EntityFile(path + filelist[i])
            #if not any([e.children for e in ef.entities]):
            #    continue
            #print(ef.__dict__)
            #sys.exit()
            #print(ef.entities[-1].component_items[-1])
            d = ef.to_dict(sparse=True, raw_as="length")
            #d = to_dict(ef)
            full_dict.update(d)
            #pprint(d)
            #js = json.dumps(d, indent=2)
            #print(js)
            #sys.exit(0)
        except Exception as e:
            log.error(f"{i}/{len(filelist)} {filelist[i]} {e}")
            raise
            log.setLevel('DEBUG')
            try:
                EntityFile(path + filelist[i])
            except:
                pass
            pprint(component_stats)
            log.error(f"{i}/{len(filelist)} {filelist[i]} {e}")
            raise
    js = json.dumps(full_dict, indent=2)
    print(js)
    #with open("./test5.json", "w") as f:
    #    f.write(js)


if __name__ == '__main__':
    main()
    '''try:
        main()
    except KeyboardInterrupt:
        pass'''
    sys.exit()
    import cProfile
    cProfile.run('main()', 'entity_profile_info_full')
