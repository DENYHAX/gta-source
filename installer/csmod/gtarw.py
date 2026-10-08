"""Minimal GTA SA RenderWare readers: DFF (static geometry) and TXD (D3D8/D3D9 texture natives). Input: bytes."""
import struct, numpy as np
def chunks(d, o, end):
    while o + 12 <= end:
        t, sz, ver = struct.unpack_from('<III', d, o)
        yield t, o + 12, o + 12 + sz
        o += 12 + sz
def find(d, o, end, t):
    return [(s, e) for tt, s, e in chunks(d, o, end) if tt == t]
def read_dff(d):
    (cs, ce), = find(d, 0, len(d), 0x10)
    # frames
    (fs, fe), = find(d, cs, ce, 0x0E)
    (ss, se), = find(d, fs, fe, 1)
    nf, = struct.unpack_from('<I', d, ss); frames = []
    for i in range(nf):
        v = struct.unpack_from('<9f3fiI', d, ss + 4 + i * 56)
        R = np.array(v[:9]).reshape(3, 3); p = np.array(v[9:12]); frames.append((R, p, v[12]))
    def world(i):
        R, p, par = frames[i]
        M = np.identity(4); M[:3, :3] = R.T; M[:3, 3] = p    # RW stores right/up/at rows
        return M if par < 0 else world(par) @ M
    (gs, ge), = find(d, cs, ce, 0x1A)
    geoms = []
    for s, e in find(d, gs, ge, 0x0F):
        (ss, se), = find(d, s, e, 1)
        flags, ntri, nv, nm = struct.unpack_from('<IIII', d, ss); p = ss + 16
        if flags & 8: p += 4 * nv
        nuv = (flags >> 16) & 0xFF or (2 if flags & 0x80 else (1 if flags & 4 else 0))
        uv = np.frombuffer(d, '<f4', nv * 2, p).reshape(nv, 2).copy() if nuv else np.zeros((nv, 2)); p += 8 * nv * nuv
        tri = np.frombuffer(d, '<u2', ntri * 4, p).reshape(ntri, 4).astype(np.int64); p += 8 * ntri
        p += 16; hasv, hasn = struct.unpack_from('<II', d, p); p += 8
        P = np.frombuffer(d, '<f4', nv * 3, p).reshape(nv, 3).astype(np.float64); p += 12 * nv
        N = np.frombuffer(d, '<f4', nv * 3, p).reshape(nv, 3).astype(np.float64) if hasn else None
        T = np.stack([tri[:, 1], tri[:, 0], tri[:, 3]], 1); M = tri[:, 2]
        (ms, me), = find(d, s, e, 0x08); texs = []
        for m0, m1 in find(d, ms, me, 0x07):
            tx = find(d, m0, m1, 0x06); name = ''
            if tx:
                strs = find(d, tx[0][0], tx[0][1], 2)
                name = d[strs[0][0]:strs[0][1]].split(b'\0')[0].decode()
            texs.append(name)
        geoms.append(dict(P=P, N=N, UV=uv, T=T, M=M, tex=texs))
    atoms = []
    for s, e in find(d, cs, ce, 0x14):
        (ss, se), = find(d, s, e, 1)
        fi, gi = struct.unpack_from('<II', d, ss); atoms.append((fi, gi))
    out = []
    for fi, gi in atoms:
        g = dict(geoms[gi]); W = world(fi)
        g['P'] = g['P'] @ W[:3, :3].T + W[:3, 3]
        if g['N'] is not None: g['N'] = g['N'] @ W[:3, :3].T
        out.append(g)
    return out
def read_txd(d):
    (ts, te), = find(d, 0, len(d), 0x16); res = []
    for s, e in find(d, ts, te, 0x15):
        (ss, se), = find(d, s, e, 1)
        plat, = struct.unpack_from('<I', d, ss)
        name = d[ss + 8:ss + 40].split(b'\0')[0].decode()
        rf, = struct.unpack_from('<I', d, ss + 72)
        four = d[ss + 76:ss + 80]
        w, h, depth, nl, rt, comp = struct.unpack_from('<HHBBBB', d, ss + 80)
        if plat == 8:
            four = {1: b'DXT1', 3: b'DXT3'}.get(comp, b'\0\0\0\0')
        p = ss + 88; mips = []
        for i in range(nl):
            sz, = struct.unpack_from('<I', d, p); mips.append(d[p + 4:p + 4 + sz]); p += 4 + sz
        res.append(dict(name=name, w=w, h=h, four=four, mips=mips, rf=rf))
    return res
