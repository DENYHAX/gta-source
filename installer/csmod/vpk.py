"""Read-only access to Valve VPK (v1/v2) archives, e.g. cstrike/cstrike_pak_dir.vpk."""
import os
import struct


class VPK:
    def __init__(self, dir_path):
        self.dir_path = dir_path
        self.base = dir_path[:-len('_dir.vpk')] if dir_path.lower().endswith('_dir.vpk') else None
        with open(dir_path, 'rb') as f:
            sig, ver, tree_size = struct.unpack('<III', f.read(12))
            if sig != 0x55AA1234:
                raise ValueError(f'not a VPK file: {dir_path}')
            if ver == 2:
                f.read(16)
            elif ver != 1:
                raise ValueError(f'unsupported VPK version {ver}')
            self.header_size = f.tell()
            tree = f.read(tree_size)
        self.data_offset = self.header_size + tree_size
        self.entries = {}
        p = 0

        def cstr():
            nonlocal p
            e = tree.index(b'\0', p)
            s = tree[p:e].decode('latin1')
            p = e + 1
            return s

        while True:
            ext = cstr()
            if not ext:
                break
            while True:
                path = cstr()
                if not path:
                    break
                while True:
                    name = cstr()
                    if not name:
                        break
                    crc, pre_len, arc, off, length, term = struct.unpack_from('<IHHIIH', tree, p)
                    p += 18
                    pre = tree[p:p + pre_len]
                    p += pre_len
                    full = (f'{path}/{name}.{ext}' if path.strip() != '' else f'{name}.{ext}').lower()
                    self.entries[full] = (arc, off, length, pre)

    def has(self, path):
        return path.lower().replace('\\', '/') in self.entries

    def read(self, path):
        arc, off, length, pre = self.entries[path.lower().replace('\\', '/')]
        if length == 0:
            return pre
        if arc == 0x7FFF:
            fn, off = self.dir_path, self.data_offset + off
        else:
            fn = f'{self.base}_{arc:03d}.vpk'
        with open(fn, 'rb') as f:
            f.seek(off)
            return pre + f.read(length)

    def extract(self, path, dest):
        data = self.read(path)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, 'wb') as f:
            f.write(data)
        return dest


class SourceFS:
    """Looks a file up in several VPKs (first hit wins), like the Source engine search path."""

    def __init__(self, vpk_paths):
        self.vpks = [VPK(p) for p in vpk_paths if os.path.isfile(p)]
        if not self.vpks:
            raise FileNotFoundError('no VPK archive found')

    def has(self, path):
        return any(v.has(path) for v in self.vpks)

    def read(self, path):
        for v in self.vpks:
            if v.has(path):
                return v.read(path)
        raise FileNotFoundError(path)

    def extract(self, path, dest):
        data = self.read(path)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, 'wb') as f:
            f.write(data)
        return dest
