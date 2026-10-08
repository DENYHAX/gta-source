"""Read a GTA SA ped DFF (bytes): frames (names, HAnim ids), skin inverse bind matrices -> bone bind world matrices."""
import struct, numpy as np
def chunks(d, o, end):
    while o + 12 <= end:
        t, sz, v = struct.unpack_from('<III', d, o); yield t, o + 12, o + 12 + sz; o += 12 + sz
def read(d):
    cl = [c for c in chunks(d, 0, len(d)) if c[0] == 0x10][0]
    out = {'raw': d, 'clump': cl}
    for t, s, e in chunks(d, cl[1], cl[2]):
        if t == 0x0E:
            out['framelist'] = (s - 12, e)
            st = [c for c in chunks(d, s, e) if c[0] == 1][0]
            nf, = struct.unpack_from('<I', d, st[1]); fr = []
            for i in range(nf):
                v = struct.unpack_from('<9f3fiI', d, st[1] + 4 + i * 56)
                fr.append({'rot': np.array(v[:9]).reshape(3, 3), 'pos': np.array(v[9:12]), 'parent': v[12]})
            exts = [c for c in chunks(d, s, e) if c[0] == 3]
            for i, (t2, s2, e2) in enumerate(exts):
                fr[i]['name'] = ''; fr[i]['bone'] = None
                for t3, s3, e3 in chunks(d, s2, e2):
                    if t3 == 0x253f2fe: fr[i]['name'] = d[s3:e3].decode('latin1').strip()
                    if t3 == 0x11e:
                        ver, bid, nb = struct.unpack_from('<IiI', d, s3); fr[i]['bone'] = bid
                        if nb:
                            fl, ks = struct.unpack_from('<II', d, s3 + 12)
                            out['hier'] = [struct.unpack_from('<iiI', d, s3 + 20 + 12 * k) for k in range(nb)]
            out['frames'] = fr
        if t == 0x1A:
            g = [c for c in chunks(d, s, e) if c[0] == 0xF][0]
            st = [c for c in chunks(d, g[1], g[2]) if c[0] == 1][0]
            flags, ntri, nv, nm = struct.unpack_from('<IIII', d, st[1])
            ex = [c for c in chunks(d, g[1], g[2]) if c[0] == 3][0]
            for t2, s2, e2 in chunks(d, ex[1], ex[2]):
                if t2 == 0x116:
                    nb, nu, mw, _ = struct.unpack_from('<4B', d, s2); p = s2 + 4 + nu + 20 * nv
                    inv = []
                    for k in range(nb):
                        m = np.frombuffer(d, '<f4', 16, p + 64 * k).reshape(4, 4).astype(np.float64).copy()
                        m[:, 3] = [0, 0, 0, 1]
                        inv.append(m)          # row-vector convention: p_bone = p_model @ M
                    out['invbind'] = inv
        if t == 0x14: out['atomic'] = (s - 12, e)
    # bone order = hierarchy node order; name by matching hanim id
    byid = {f['bone']: f['name'] for f in out['frames'] if f['bone'] is not None}
    out['bones'] = [(nid, byid.get(nid, '?'), flags) for nid, idx, flags in out['hier']]
    W = []
    for m in out['invbind']:
        W.append(np.linalg.inv(m))     # rows: right, up, at, pos (row-vector world matrix)
    out['bindworld'] = W
    return out
