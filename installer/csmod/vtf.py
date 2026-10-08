"""Valve VTF texture reader (the formats CS:S uses) + conversion to a PIL image."""
import io
import struct

from PIL import Image
FMT = {0:'RGBA8888',2:'RGB888',3:'BGR888',12:'BGRA8888',13:'DXT1',14:'DXT3',15:'DXT5',4:'RGB565',16:'BGRX8888'}
def blocks(fmt, w, h):
    if fmt in (13,): return max(1,(w+3)//4)*max(1,(h+3)//4)*8
    if fmt in (14,15): return max(1,(w+3)//4)*max(1,(h+3)//4)*16
    bpp={0:4,2:3,3:3,12:4,16:4,4:2}[fmt]; return w*h*bpp
def read(src):
    d = src if isinstance(src, (bytes, bytearray)) else open(src, 'rb').read()
    assert d[:4] == b'VTF\0'
    vmaj, vmin, hsize = struct.unpack_from('<III', d, 4)
    w, h, flags, frames, first = struct.unpack_from('<HHIHH', d, 16)
    hfmt, = struct.unpack_from('<i', d, 52); mips = d[56]
    lfmt, = struct.unpack_from('<i', d, 57); lw, lh = d[61], d[62]
    off = hsize
    if lfmt != -1 and lfmt != 0xFFFFFFFF and lw: off += blocks(lfmt, lw, lh)
    # mips smallest first; frames per mip
    sizes = []
    for m in range(mips-1, -1, -1):
        mw, mh = max(1, w >> m), max(1, h >> m)
        sizes.append((m, mw, mh, blocks(hfmt, mw, mh) * frames))
    levels = {}
    for m, mw, mh, sz in sizes:
        levels[m] = (mw, mh, d[off:off+blocks(hfmt, mw, mh)]); off += sz
    return dict(w=w, h=h, fmt=hfmt, fmtname=FMT.get(hfmt, hfmt), mips=mips, flags=flags, levels=levels)
def to_image(t, level=0):
    mw, mh, raw = t['levels'][level]; f = t['fmt']
    if f in (13,14,15):
        four = {13:b'DXT1',14:b'DXT3',15:b'DXT5'}[f]
        hdr = b'DDS ' + struct.pack('<7I', 124, 0x1007, mh, mw, len(raw), 0, 1) + b'\0'*44 + struct.pack('<2I4s5I', 32, 4, four, 0,0,0,0,0) + struct.pack('<5I', 0x1000,0,0,0,0)
        return Image.open(io.BytesIO(hdr + raw)).convert('RGBA')
    if f == 12: return Image.frombytes('RGBA', (mw, mh), raw, 'raw', 'BGRA')
    if f == 16: return Image.frombytes('RGBA', (mw, mh), raw, 'raw', 'BGRA').convert('RGB').convert('RGBA')
    if f == 0: return Image.frombytes('RGBA', (mw, mh), raw)
    if f == 2: return Image.frombytes('RGB', (mw, mh), raw).convert('RGBA')
    if f == 3: return Image.frombytes('RGB', (mw, mh), raw, 'raw', 'BGR').convert('RGBA')
    raise ValueError(f)
