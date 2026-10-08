"""CS:S t_phoenix player model retargeted onto a GTA SA ped skeleton.

The GTA template DFF (male01.dff for the in-game ped, csplay.dff for the cutscene player with its face rig) gives
the frame list, the HAnim hierarchy and the skin inverse bind matrices. The Source mesh is moved bone by bone onto
the matching GTA joints and its weights are merged onto the GTA bones.
"""
import struct

import numpy as np

from . import gtaped, rw, vtf
from .srcmodel import bone_worlds, load

ALIAS = {'Spine': ['Spine', 'Spine 1'], 'Spine1': ['Spine1', 'Spine 2']}   # csplay names its spine bones differently
MAP = {'Pelvis': 'Pelvis', 'Spine': 'Spine', 'Spine2': 'Spine1', 'Neck1': 'Neck', 'Head1': 'Head',
       'L_Clavicle': 'Bip01 L Clavicle', 'L_UpperArm': 'L UpperArm', 'L_Forearm': 'L ForeArm', 'L_Hand': 'L Hand',
       'L_Finger2': 'L Finger', 'L_Finger21': 'L Finger01',
       'R_Clavicle': 'Bip01 R Clavicle', 'R_UpperArm': 'R UpperArm', 'R_Forearm': 'R ForeArm', 'R_Hand': 'R Hand',
       'R_Finger2': 'R Finger', 'R_Finger21': 'R Finger01',
       'L_Thigh': 'L Thigh', 'L_Calf': 'L Calf', 'L_Foot': 'L Foot', 'L_Toe0': 'L Toe0',
       'R_Thigh': 'R Thigh', 'R_Calf': 'R Calf', 'R_Foot': 'R Foot', 'R_Toe0': 'R Toe0'}
THUMBS = {'L_Finger0': 'LThumb1', 'L_Finger01': 'LThumb2', 'R_Finger0': 'RThumb1', 'R_Finger01': 'RThumb2'}
DIRS = {'Spine': ('Spine2', 'Spine1'), 'Spine2': ('Neck1', 'Neck'),
        'L_Clavicle': ('L_UpperArm', 'L UpperArm'), 'L_UpperArm': ('L_Forearm', 'L ForeArm'), 'L_Forearm': ('L_Hand', 'L Hand'), 'L_Hand': ('L_Finger2', 'L Finger'),
        'R_Clavicle': ('R_UpperArm', 'R UpperArm'), 'R_UpperArm': ('R_Forearm', 'R ForeArm'), 'R_Forearm': ('R_Hand', 'R Hand'), 'R_Hand': ('R_Finger2', 'R Finger'),
        'L_Thigh': ('L_Calf', 'L Calf'), 'L_Calf': ('L_Foot', 'L Foot'), 'L_Foot': ('L_Toe0', 'L Toe0'),
        'R_Thigh': ('R_Calf', 'R Calf'), 'R_Calf': ('R_Foot', 'R Foot'), 'R_Foot': ('R_Toe0', 'R Toe0')}
CSS_FILES = ['models/player/t_phoenix.mdl', 'models/player/t_phoenix.vvd', 'models/player/t_phoenix.dx90.vtx',
             'materials/models/player/t_phoenix/t_phoenix.vtf']


def _align(a, b):
    a = a / np.linalg.norm(a); b = b / np.linalg.norm(b)
    v = np.cross(a, b); c = a @ b
    if np.linalg.norm(v) < 1e-8:
        return np.identity(3) if c > 0 else -np.identity(3)
    K = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.identity(3) + K + K @ K * (1 / (1 + c))


def build_dff(template_bytes, mdl_base, texname='t_phoenix'):
    T = gtaped.read(template_bytes)
    gnames = [n for _, n, _ in T['bones']]
    gidx = {n: i for i, n in enumerate(gnames)}
    for k, alts in ALIAS.items():
        for a_ in alts:
            if a_ in gidx:
                gidx.setdefault(k, gidx[a_])
    GJ = np.array([W[3, :3] for W in T['bindworld']])         # GTA joints (skin space)
    mdl, parts = load(mdl_base)
    SW = bone_worlds(mdl)
    snames = [b.name.replace('ValveBiped.Bip01_', '').replace('ValveBiped.', '') for b in mdl.bones]
    sidx = {n: i for i, n in enumerate(snames)}
    pel_h = SW[sidx['Pelvis']][2, 3]
    up = GJ[gidx['Head']] - GJ[gidx['Pelvis']]; up /= np.linalg.norm(up)
    lf = GJ[gidx['L UpperArm']] - GJ[gidx['R UpperArm']]; lf -= up * (lf @ up); lf /= np.linalg.norm(lf)
    fw = np.cross(lf, up)
    if (GJ[gidx['L Toe0']] - GJ[gidx['L Foot']]) @ fw < 0:
        fw = -fw
    bottom = min(GJ[gidx['L Toe0']] @ up, GJ[gidx['R Toe0']] @ up) - 0.008
    SC = (GJ[gidx['Pelvis']] @ up - bottom) / (pel_h * 0.0254)   # pelvis height ratio
    CR = np.stack([lf, -fw, up], 1)                               # Source x, y, z -> template skin space
    assert np.linalg.det(CR) > 0, 'mirrored axes'

    def conv(p):
        return (np.asarray(p, float) * 0.0254 * SC) @ CR.T
    SJ = conv(np.array([W[:3, 3] for W in SW]))
    SJ += GJ[gidx['Pelvis']] - SJ[sidx['Pelvis']]
    mp = dict(MAP, **(THUMBS if 'LThumb1' in gnames else {}))
    R = [None] * len(snames); t = [None] * len(snames); gb = [None] * len(snames)
    for i, n in enumerate(snames):
        par = mdl.bones[i].parent_id
        if n in mp:
            g = gidx[mp[n]]; gb[i] = g
            Ri = np.identity(3)
            if n in DIRS:
                sc_, gc = DIRS[n]
                Ri = _align(SJ[sidx[sc_]] - SJ[i], GJ[gidx[gc]] - GJ[g])
            elif par >= 0 and R[par] is not None:
                Ri = R[par]
            R[i] = Ri; t[i] = GJ[g] - Ri @ SJ[i]
        else:
            R[i] = R[par] if par >= 0 else np.identity(3)
            t[i] = t[par] if par >= 0 else np.zeros(3)
            gb[i] = gb[par] if par >= 0 else gidx['Pelvis']
    _, _, v, tris, _ = parts[0]
    P0 = conv(v['vertex']); P0 += GJ[gidx['Pelvis']] - conv(SW[sidx['Pelvis']][:3, 3])
    N0 = np.asarray(v['normal'], float) @ CR.T
    ids = v['bone_id']; wts = v['weight'].astype(float)
    cnt = v['bone_count'] if 'bone_count' in v.dtype.names else np.full(len(v), 3)
    P = np.zeros_like(P0); N = np.zeros_like(N0)
    nv = len(P0); bi = np.zeros((nv, 4), np.uint8); bw = np.zeros((nv, 4), np.float32)
    for k in range(nv):
        acc = {}
        for j in range(3):
            if j >= cnt[k] or wts[k, j] <= 0:
                continue
            s = ids[k, j]; w = wts[k, j]
            P[k] += w * (R[s] @ P0[k] + t[s]); N[k] += w * (R[s] @ N0[k])
            acc[gb[s]] = acc.get(gb[s], 0) + w
        tot = sum(acc.values()) or 1
        for j, (g, w) in enumerate(sorted(acc.items(), key=lambda x: -x[1])[:4]):
            bi[k, j] = g; bw[k, j] = w / tot
    N /= np.linalg.norm(N, axis=1, keepdims=True) + 1e-9
    UV = np.asarray(v['uv'], float)
    TR = np.asarray(tris, np.int64)
    return _write_dff(T, P, N, UV, TR, bi, bw, texname)


def _write_dff(T, P, N, UV, TR, bi, bw, texname):
    d = T['raw']; ch = rw.chunk; ext = rw.ext

    def sub(t0):
        for tt, s, e in gtaped.chunks(d, T['clump'][1], T['clump'][2]):
            if tt == t0:
                return d[s - 12:e]
    clump_struct = sub(1); framelist = sub(0x0E); atomic = sub(0x14)
    n, m = len(P), len(TR)
    flags = 0x2 | 0x4 | 0x10 | 0x20 | (1 << 16)
    g = struct.pack('<IIII', flags, m, n, 1) + UV.astype('<f4').tobytes()
    tri = np.zeros((m, 4), '<u2'); tri[:, 0] = TR[:, 1]; tri[:, 1] = TR[:, 0]; tri[:, 2] = 0; tri[:, 3] = TR[:, 2]
    g += tri.tobytes()
    c = (P.min(0) + P.max(0)) / 2; r = float(np.linalg.norm(P - c, axis=1).max())
    g += struct.pack('<4f', *c, r) + struct.pack('<II', 1, 1) + P.astype('<f4').tobytes() + N.astype('<f4').tobytes()
    tex = ch(6, ch(1, struct.pack('<I', 0x00011106)) + rw.string(texname) + rw.string('') + ext())
    mat = ch(7, ch(1, struct.pack('<I4BIi3f', 0, 255, 255, 255, 255, 0, 1, 1.0, 0.0, 1.0)) + tex + ext())
    matlist = ch(8, ch(1, struct.pack('<I', 1) + struct.pack('<i', -1)) + mat)
    idx = TR.reshape(-1)
    binmesh = ch(0x50E, struct.pack('<III', 0, 1, len(idx)) + struct.pack('<II', len(idx), 0) + idx.astype('<u4').tobytes())
    nb = len(T['bones']); used = sorted(set(bi[bw > 0].tolist()))
    tg = [c_ for c_ in gtaped.chunks(d, T['clump'][1], T['clump'][2]) if c_[0] == 0x1A][0]
    tgeo = [c_ for c_ in gtaped.chunks(d, tg[1], tg[2]) if c_[0] == 0xF][0]
    tst = [c_ for c_ in gtaped.chunks(d, tgeo[1], tgeo[2]) if c_[0] == 1][0]
    _, _, tnv, _ = struct.unpack_from('<IIII', d, tst[1])
    tex_ = [c_ for c_ in gtaped.chunks(d, tgeo[1], tgeo[2]) if c_[0] == 3][0]
    tsk = [c_ for c_ in gtaped.chunks(d, tex_[1], tex_[2]) if c_[0] == 0x116][0]
    tnb, tnu = struct.unpack_from('<BB', d, tsk[1])
    mats = d[tsk[1] + 4 + tnu + 20 * tnv: tsk[1] + 4 + tnu + 20 * tnv + 64 * tnb]
    skin = struct.pack('<4B', nb, len(used), 4, 0) + bytes(used) + bi.astype('u1').tobytes() + bw.astype('<f4').tobytes() + mats + b'\0' * 12
    geom = ch(0xF, ch(1, g) + matlist + ext(binmesh, ch(0x116, skin), ch(0x253F2FD, b'\0' * 4)))
    geomlist = ch(0x1A, ch(1, struct.pack('<I', 1)) + geom)
    return ch(0x10, clump_struct + framelist + geomlist + atomic + ext())


def build_txd(vtf_bytes, texname='t_phoenix'):
    t = vtf.read(vtf_bytes)
    mips = [t['levels'][i][2] for i in range(t['mips']) if max(t['levels'][i][0], t['levels'][i][1]) >= 4]
    four = {13: b'DXT1', 14: b'DXT3', 15: b'DXT5'}.get(t['fmt'], b'DXT1')
    return rw.txd([(texname, t['w'], t['h'], mips, four)])
