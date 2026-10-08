"""Minimal RenderWare 3.6 (GTA SA) writers: DFF (one static atomic), TXD (D3D9), COL1 and IMG VER2 archives."""
import os
import struct
import tempfile

import numpy as np

V = 0x1803FFFF   # RW 3.6.0.3, as used by GTA SA


def chunk(t, payload):
    return struct.pack('<III', t, len(payload), V) + payload


def string(s):
    b = s.encode() + b'\0'
    b += b'\0' * ((4 - len(b) % 4) % 4)
    return chunk(2, b)


def ext(*parts):
    return chunk(3, b''.join(parts))


def dff(name, P, N, UV, T, M, texnames):
    """P, N: (n,3) float; UV (n,2); T (m,3) int; M (m,) material index; texnames: list of texture names."""
    n, m = len(P), len(T)
    fr = struct.pack('<I', 1) + struct.pack('<9f', 1, 0, 0, 0, 1, 0, 0, 0, 1) + struct.pack('<3f', 0, 0, 0) + struct.pack('<iI', -1, 0)
    framelist = chunk(0xE, chunk(1, fr) + ext(chunk(0x253F2FE, name.encode())))
    flags = 0x2 | 0x4 | 0x10 | 0x20 | (1 << 16)
    g = struct.pack('<IIII', flags, m, n, 1)
    g += UV.astype('<f4').tobytes()
    tri = np.zeros((m, 4), '<u2')
    tri[:, 0] = T[:, 1]; tri[:, 1] = T[:, 0]; tri[:, 2] = M; tri[:, 3] = T[:, 2]
    g += tri.tobytes()
    c = (P.min(0) + P.max(0)) / 2
    r = float(np.linalg.norm(P - c, axis=1).max())
    g += struct.pack('<4f', *c, r) + struct.pack('<II', 1, 1)
    g += P.astype('<f4').tobytes() + N.astype('<f4').tobytes()
    mats = b''
    for tn in texnames:
        tex = chunk(6, chunk(1, struct.pack('<I', 0x00011106)) + string(tn) + string('') + ext())
        mats += chunk(7, chunk(1, struct.pack('<I4BIi3f', 0, 255, 255, 255, 255, 0, 1, 1.0, 0.0, 1.0)) + tex + ext())
    matlist = chunk(8, chunk(1, struct.pack('<I', len(texnames)) + struct.pack('<i', -1) * len(texnames)) + mats)
    bm = b''
    total = cnt = 0
    for mi in range(len(texnames)):
        idx = T[M == mi].reshape(-1)
        if len(idx) == 0:
            continue
        bm += struct.pack('<II', len(idx), mi) + idx.astype('<u4').tobytes()
        total += len(idx); cnt += 1
    binmesh = chunk(0x50E, struct.pack('<III', 0, cnt, total) + bm)
    geom = chunk(0xF, chunk(1, g) + matlist + ext(binmesh))
    geomlist = chunk(0x1A, chunk(1, struct.pack('<I', 1)) + geom)
    atomic = chunk(0x14, chunk(1, struct.pack('<IIII', 0, 0, 5, 0)) + ext())
    return chunk(0x10, chunk(1, struct.pack('<III', 1, 0, 0)) + framelist + geomlist + atomic + ext())


def txd(textures):
    """textures: list of (name, w, h, [mip bytes, largest first], fourcc[, filter]).
    fourcc b'DXT1' / b'DXT3' / b'DXT5' = compressed, b'ARGB' = 32-bit B,G,R,A bytes (D3DFMT_A8R8G8B8)."""
    out = b''
    for tex in textures:
        name, w, h, mips, four = tex[:5]
        many = len(mips) > 1
        filt = tex[5] if len(tex) > 5 else (6 if many else 2)
        if four == b'ARGB':
            rf = 0x0500 | (0x8000 if many else 0)
            d3dfmt = struct.pack('<I', 21)
            depth, flags = 32, 0x01           # alpha
        else:
            rf = (0x0200 if four == b'DXT1' else 0x0300) | (0x8000 if many else 0)
            d3dfmt = four
            depth, flags = 16, 0x08 | (1 if four != b'DXT1' else 0)   # compressed (+ alpha)
        s = struct.pack('<IBBH', 9, filt, 0x11, 0)
        s += name.encode().ljust(32, b'\0')[:32] + b''.ljust(32, b'\0')
        s += struct.pack('<I4sHHBBBB', rf, d3dfmt, w, h, depth, len(mips), 4, flags)
        for mb in mips:
            s += struct.pack('<I', len(mb)) + mb
        out += chunk(0x15, chunk(1, s) + ext())
    return chunk(0x16, chunk(1, struct.pack('<HH', len(textures), 2)) + out + ext())


def col1(name, bmin, bmax):
    """COL1 entry with one tiny sphere (an empty col model crashes CObject creation)."""
    bmin = np.array(bmin, float); bmax = np.array(bmax, float)
    c = (bmin + bmax) / 2
    r = float(np.linalg.norm(bmax - c))
    body = name.encode().ljust(22, b'\0')[:22] + struct.pack('<H', 0)
    body += struct.pack('<f3f3f3f', r, *c, *bmin, *bmax)
    body += struct.pack('<I', 1) + struct.pack('<f3f4B', 0.05, *c, 0, 0, 0, 0)
    body += struct.pack('<IIII', 0, 0, 0, 0)
    return b'COLL' + struct.pack('<I', len(body)) + body


class ImgWriter:
    """Streams an IMG VER2 archive: entries go to a temporary data file, the directory is written at close()."""
    S = 2048

    def __init__(self, path):
        self.path = path
        self.names = set()
        self.entries = []          # (name, offset_sectors_in_data, sectors)
        self.sectors = 0
        fd, self.tmp = tempfile.mkstemp(prefix='img_', suffix='.dat', dir=os.path.dirname(path) or '.')
        self.f = os.fdopen(fd, 'wb')

    def add(self, name, data):
        if len(name) > 23:
            raise ValueError(f'IMG entry name too long: {name}')
        if name.lower() in self.names:
            raise ValueError(f'duplicate IMG entry: {name}')
        self.names.add(name.lower())
        sec = (len(data) + self.S - 1) // self.S
        self.f.write(data + b'\0' * (sec * self.S - len(data)))
        self.entries.append((name, self.sectors, sec))
        self.sectors += sec

    def close(self):
        self.f.close()
        n = len(self.entries)
        hdr_sectors = (8 + 32 * n + self.S - 1) // self.S
        head = b'VER2' + struct.pack('<I', n)
        for name, off, sec in self.entries:
            head += struct.pack('<IHH24s', off + hdr_sectors, sec, 0, name.encode())
        head += b'\0' * (hdr_sectors * self.S - len(head))
        with open(self.path, 'wb') as out, open(self.tmp, 'rb') as src:
            out.write(head)
            while True:
                b = src.read(1 << 22)
                if not b:
                    break
                out.write(b)
        os.remove(self.tmp)
        return n


def read_img(path, wanted=None):
    """Read entries of an IMG VER2 archive -> {lowercase name: bytes} (only `wanted` names if given)."""
    want = {w.lower() for w in wanted} if wanted else None
    out = {}
    with open(path, 'rb') as f:
        if f.read(4) != b'VER2':
            raise ValueError(f'{path}: not an IMG VER2 archive')
        n, = struct.unpack('<I', f.read(4))
        dirs = [struct.unpack('<IHH24s', f.read(32)) for _ in range(n)]
        for off, sec, sec2, name in dirs:
            nm = name.split(b'\0')[0].decode('latin1').lower()
            if want is not None and nm not in want:
                continue
            f.seek(off * 2048)
            out[nm] = f.read((sec or sec2) * 2048)
    return out
