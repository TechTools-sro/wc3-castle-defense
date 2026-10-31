"""Minimal ctypes binding to StormLib (libstorm.so.9) for reading game MPQs
and writing WarCraft III map archives (.w3x = 512-byte HM3W header + MPQ)."""
import ctypes, os, struct, tempfile

_lib = ctypes.CDLL("libstorm.so.9")
H = ctypes.c_void_p
DW = ctypes.c_uint32
_lib.SFileOpenArchive.argtypes = [ctypes.c_char_p, DW, DW, ctypes.POINTER(H)]
_lib.SFileOpenFileEx.argtypes = [H, ctypes.c_char_p, DW, ctypes.POINTER(H)]
_lib.SFileGetFileSize.argtypes = [H, ctypes.POINTER(DW)]
_lib.SFileGetFileSize.restype = DW
_lib.SFileReadFile.argtypes = [H, ctypes.c_void_p, DW, ctypes.POINTER(DW), ctypes.c_void_p]
_lib.SFileCloseFile.argtypes = [H]
_lib.SFileCloseArchive.argtypes = [H]
_lib.SFileHasFile.argtypes = [H, ctypes.c_char_p]
_lib.SFileCreateArchive.argtypes = [ctypes.c_char_p, DW, DW, ctypes.POINTER(H)]
_lib.SFileCreateFile.argtypes = [H, ctypes.c_char_p, ctypes.c_uint64, DW, DW, DW, ctypes.POINTER(H)]
_lib.SFileWriteFile.argtypes = [H, ctypes.c_void_p, DW, DW]
_lib.SFileFinishFile.argtypes = [H]
for f in ("SFileOpenArchive", "SFileOpenFileEx", "SFileReadFile", "SFileCloseFile",
          "SFileCloseArchive", "SFileHasFile", "SFileCreateArchive", "SFileCreateFile",
          "SFileWriteFile", "SFileFinishFile"):
    getattr(_lib, f).restype = ctypes.c_bool

MPQ_OPEN_READ_ONLY = 0x100
MPQ_CREATE_LISTFILE = 0x00100000
MPQ_FILE_COMPRESS = 0x00000200
MPQ_FILE_REPLACEEXISTING = 0x80000000
MPQ_COMPRESSION_ZLIB = 0x02


class Archive:
    def __init__(self, path):
        self.h = H()
        if not _lib.SFileOpenArchive(path.encode(), 0, MPQ_OPEN_READ_ONLY, ctypes.byref(self.h)):
            raise OSError(f"cannot open MPQ {path}")

    def has(self, name):
        return bool(_lib.SFileHasFile(self.h, name.encode()))

    def read(self, name):
        fh = H()
        if not _lib.SFileOpenFileEx(self.h, name.encode(), 0, ctypes.byref(fh)):
            return None
        try:
            size = _lib.SFileGetFileSize(fh, None)
            buf = ctypes.create_string_buffer(size)
            got = DW()
            _lib.SFileReadFile(fh, buf, size, ctypes.byref(got), None)
            return buf.raw[:got.value]
        finally:
            _lib.SFileCloseFile(fh)

    def close(self):
        _lib.SFileCloseArchive(self.h)


class GameData:
    """Reads a file the way the game does: patch MPQ first, base MPQs last."""
    ORDER = ("War3Patch.mpq", "War3xlocal.mpq", "War3x.mpq", "war3.mpq")

    def __init__(self, game_dir):
        self.archives = [Archive(os.path.join(game_dir, n)) for n in self.ORDER
                         if os.path.exists(os.path.join(game_dir, n))]

    def read(self, name):
        for a in self.archives:
            data = a.read(name)
            if data is not None:
                return data
        return None


def write_w3x(out_path, files, map_name, map_flags, max_players):
    """files: dict archived-name -> bytes. Writes HM3W header + MPQ."""
    fd, tmp = tempfile.mkstemp(suffix=".mpq")
    os.close(fd)
    os.unlink(tmp)
    h = H()
    if not _lib.SFileCreateArchive(tmp.encode(), MPQ_CREATE_LISTFILE, max(64, len(files) * 2 + 8), ctypes.byref(h)):
        raise OSError("SFileCreateArchive failed")
    try:
        for name, data in files.items():
            fh = H()
            if not _lib.SFileCreateFile(h, name.encode(), 0, len(data), 0,
                                        MPQ_FILE_COMPRESS | MPQ_FILE_REPLACEEXISTING, ctypes.byref(fh)):
                raise OSError(f"SFileCreateFile failed for {name}")
            if data and not _lib.SFileWriteFile(fh, data, len(data), MPQ_COMPRESSION_ZLIB):
                raise OSError(f"SFileWriteFile failed for {name}")
            if not _lib.SFileFinishFile(fh):
                raise OSError(f"SFileFinishFile failed for {name}")
    finally:
        _lib.SFileCloseArchive(h)
    with open(tmp, "rb") as f:
        mpq = f.read()
    os.unlink(tmp)
    header = b"HM3W" + struct.pack("<i", 0) + map_name.encode("utf-8") + b"\0" + struct.pack("<ii", map_flags, max_players)
    header = header.ljust(512, b"\0")
    with open(out_path, "wb") as f:
        f.write(header + mpq)
