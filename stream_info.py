from noita_bin_file import NoitaBinFile


class StreamInfoItem:
    a: float
    b: int
    count: int
    x: float
    y: float
    path: bytes

    def __init__(self, file: NoitaBinFile):
        self.a = file.read_float()
        self.b = file.read_int()
        self.count = file.read_int()
        self.x = file.read_float()
        self.y = file.read_float()
        self.path = file.read_string()

    def __str__(self):
        return f"StreamInfoItem({self.x}, {self.y}) count {self.count} path {self.path[:500]} {self.a} {self.b}"

    def __repr__(self):
        return str(self)
