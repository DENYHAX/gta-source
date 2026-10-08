"""CS:S first-person weapon models -> GTA SA flipbook models (one static DFF per animation frame).

Everything is computed from the user's own CS:S files: the MDL skeleton animations are sampled at a fixed rate,
the meshes are skinned on the CPU and written as plain RenderWare geometry for GTA SA.
"""
import os

import numpy as np

from . import gtarw, rw, vtf
from .srcmodel import anim_frames, bone_worlds, load, skin

U = 0.0254                                                    # Source unit (inch) -> metre
FWD_SQUASH = np.tan(np.radians(27)) / np.tan(np.radians(45))  # viewmodel_fov 54 vs fov 90
VMAT = 'materials/models/weapons/v_models/'
# material name -> VTF path below VMAT
TEX = {'v_hands': 'hands/v_hands', 'rif_ak47skin1': 'rif_ak47/rif_ak47skin1', 'rif_m4a1': 'rif_m4a1/rif_m4a1',
       'mp5_1': 'smg_mp5/mp5_1', 'deagle_skin1': 'pist_deagle/deagle_skin1', 'glock18': 'pist_glock18/glock18',
       'pist_usp': 'pist_usp/pist_usp', 'shot_m3super90': 'shot_m3super90/shot_m3super90',
       'v_awp': 'snip_awp/v_awp', 'v_awp_scope': 'snip_awp/v_awp_scope', 'knife_t': 'knife_t/knife_t'}
# weapon id -> (mdl, short name, {anim: (sequence, frames per second, max frames)}); 1 frame = static pose
WEAP = {
    'knife':  ('v_knife_t', 'knife', {'idle': ('@idle', 0, 1), 'draw': ('@draw', 60, 200), 'slash': ('@midslash1', 60, 200), 'slash2': ('@midslash2', 60, 200), 'stab': ('@stab', 60, 200)}),
    'glock':  ('v_pist_glock18', 'glock', {'idle': ('@glock_idle', 0, 1), 'shoot': ('@glock_firesingle', 60, 200), 'reload': ('@glock_reload', 40, 200), 'draw': ('@glock_draw', 60, 200)}),
    'usp':    ('v_pist_usp', 'usp', {'idle': ('@idle_unsil', 0, 1), 'shoot': ('@shoot1_unsil', 60, 200), 'reload': ('@reload_unsil', 40, 200), 'draw': ('@draw_unsil', 60, 200),
                                     'sidle': ('@idle', 0, 1), 'sshoot': ('@shoot1', 60, 200), 'sreload': ('@reload', 40, 200), 'sdraw': ('@draw', 60, 200),
                                     'attach': ('@add_silencer', 30, 200), 'detach': ('@detach_silencer', 30, 200)}),
    'deagle': ('v_pist_deagle', 'deagle', {'idle': ('@idle1', 0, 1), 'shoot': ('@shoot1', 60, 200), 'reload': ('@reload', 40, 200), 'draw': ('@draw', 60, 200)}),
    'm3':     ('v_shot_m3super90', 'm3', {'idle': ('@idle', 0, 1), 'shoot': ('@shoot1', 60, 200), 'start_reload': ('@start_reload', 60, 200), 'insert': ('@insert', 60, 200), 'after_reload': ('@after_reload', 60, 200), 'draw': ('@draw', 60, 200)}),
    'mp5':    ('v_smg_mp5', 'mp5', {'idle': ('@idle', 0, 1), 'shoot': ('@shoot1', 60, 200), 'reload': ('@reload1', 40, 200), 'draw': ('@draw', 60, 200)}),
    'ak47':   ('v_rif_ak47', 'ak47', {'idle': ('@ak47_idle', 0, 1), 'shoot': ('@ak47_fire1', 60, 200), 'reload': ('@ak47_reload', 40, 200), 'draw': ('@ak47_draw', 60, 200)}),
    'm4a1':   ('v_rif_m4a1', 'm4a1', {'idle': ('@idle_unsil', 0, 1), 'shoot': ('@shoot1_unsil', 60, 200), 'reload': ('@reload_unsil', 40, 200), 'draw': ('@draw_unsil', 60, 200),
                                      'sidle': ('@idle', 0, 1), 'sshoot': ('@shoot1', 60, 200), 'sreload': ('@reload', 40, 200), 'sdraw': ('@draw', 60, 200),
                                      'attach': ('@add_silencer', 30, 200), 'detach': ('@detach_silencer', 30, 200)}),
    'awp':    ('v_snip_awp', 'awp', {'idle': ('@awm_idle', 0, 1), 'shoot': ('@awm_fire', 60, 200), 'reload': ('@awm_reload', 40, 200), 'draw': ('@awm_draw', 60, 200)}),
}
RIGHT_HANDED = {'knife'}      # CS:S BuiltRightHanded; the rest are mirrored like cl_righthand 1
NOCULL = {'v_awp_scope'}      # VMT "$nocull 1" -> double sided
SPRAY_MDL = 'v_eq_smokegrenade'


def css_files():
    """CS:S files (VPK paths) the viewmodels need."""
    out = []
    for mdl in [w[0] for w in WEAP.values()] + [SPRAY_MDL]:
        for e in ('.mdl', '.vvd', '.dx90.vtx'):
            out.append(f'models/weapons/{mdl}{e}')
    out += [f'{VMAT}{p}.vtf' for p in TEX.values()]
    return out


def to_gta(P, N, mirror=True):
    """Source view space (x fwd, y left, z up, inch) -> GTA ped space (x right, y fwd, z up, metre)."""
    sgn = 1 if mirror else -1
    G = np.stack([sgn * P[:, 1], P[:, 0] * FWD_SQUASH, P[:, 2]], 1) * U
    Ng = np.stack([sgn * N[:, 1], N[:, 0] / FWD_SQUASH, N[:, 2]], 1)
    Ng /= np.linalg.norm(Ng, axis=1, keepdims=True) + 1e-9
    return G, Ng


def frame_times(ad, fps, cap):
    fc = ad.frame_count
    dur = fc / ad.fps
    nf = 1 if cap == 1 else max(2, min(cap, int(round(dur * fps)) + 1))
    times = [0.0] if nf == 1 else [i / (nf - 1) for i in range(nf)]
    return fc, dur, times


def dxt_mips(t):
    return [t['levels'][i][2] for i in range(t['mips']) if max(t['levels'][i][0], t['levels'][i][1]) >= 4]


class Output:
    """Collects models for one IMG + IDE: DFF/TXD entries, IDE lines, COL1 entries."""

    def __init__(self, img_path, ids):
        self.img = rw.ImgWriter(img_path)
        self.ids = ids
        self.objs, self.peds, self.hier = [], [], []
        self.cols = b''

    def add_object(self, name, dff_bytes, txd, bmin, bmax):
        mid = self.ids.take()
        self.img.add(name + '.dff', dff_bytes)
        self.objs.append(f'{mid}, {name}, {txd}, 30, 0')
        self.cols += rw.col1(name, bmin, bmax)
        return mid


def build_weapons(css_dir, out, log=print, only=None):
    """All CS:S weapons -> out (Output). Returns the VMDATA manifest {weapon: {anims: {anim: {ids, duration}}}}."""
    manifest = {}
    for wid, (mdlname, short, anims) in WEAP.items():
        if only and wid not in only:
            continue
        base = os.path.join(css_dir, 'models', 'weapons', mdlname)
        mdl, parts = load(base)
        txdname = 'cs_' + short
        texnames = [m.name.lower() for m in mdl.materials]
        texs = []
        for tn in texnames:
            t = vtf.read(os.path.join(css_dir, *(VMAT + TEX[tn] + '.vtf').split('/')))
            texs.append((tn, t['w'], t['h'], dxt_mips(t), b'DXT1'))
        out.img.add(txdname + '.txd', rw.txd(texs))
        manifest[wid] = {'anims': {}}
        mirror = wid not in RIGHT_HANDED
        for an, (seq, fps, cap) in anims.items():
            frames, ad = anim_frames(mdl, base, seq)
            if frames is None:
                raise RuntimeError(f'sequence {seq} missing in {mdlname}.mdl')
            fc, dur, times = frame_times(ad, fps, cap)
            ids = []
            for k, t in enumerate(times):
                W = bone_worlds(mdl, frames, t * (fc - 1))
                Ps, Ns, UVs, Ts, Ms = [], [], [], [], []
                off = 0
                for bp, mn, v, tr, mi in parts:
                    P, N = skin(mdl, v, W)
                    G, Ng = to_gta(P, N, mirror)
                    Ps.append(G); Ns.append(Ng); UVs.append(v['uv'].astype(np.float64))
                    tt = (tr[:, ::-1] if mirror else tr) + off            # mirrored -> flip the winding
                    Ts.append(tt); Ms.append(np.full(len(tr), mi))
                    if mdl.materials[mi].name.lower() in NOCULL:
                        Ts.append(tt[:, ::-1]); Ms.append(np.full(len(tr), mi))
                    off += len(v)
                P = np.vstack(Ps)
                name = f'cs_{short}_{an[:6]}_{k}'
                d = rw.dff(name, P, np.vstack(Ns), np.vstack(UVs), np.vstack(Ts).astype(np.int64), np.concatenate(Ms), texnames)
                ids.append(out.add_object(name, d, txdname, P.min(0).tolist(), P.max(0).tolist()))
            manifest[wid]['anims'][an] = {'ids': ids, 'duration': round(dur, 3)}
        log(f'  {wid}: ' + ', '.join(f'{a} {len(m["ids"])}' for a, m in manifest[wid]['anims'].items()))
    return manifest


def build_spray(css_dir, out, spraycan_dff, spraycan_txd, log=print):
    """CS:S hands (v_eq_smokegrenade arms + animations) holding GTA SA's spray can instead of the smoke grenade."""
    INCH = 0.0254
    base = os.path.join(css_dir, 'models', 'weapons', SPRAY_MDL)
    mdl, parts = load(base)
    hands = [p for p in parts if mdl.materials[p[4]].name.lower() == 'v_hands'][0]
    gren = [p for p in parts if mdl.materials[p[4]].name.lower() == 'smokegrenade'][0]
    gv = gren[2]
    G0 = gv['vertex'].astype(np.float64)
    c = G0.mean(0)
    _, _, Vt = np.linalg.svd(G0 - c)
    a = Vt[0]
    if a[2] < 0:
        a = -a
    sc = gtarw.read_dff(spraycan_dff)[0]
    scale, along = 0.75, -2.2
    P = sc['P'] / INCH * scale
    N = sc['N'] if sc['N'] is not None else np.zeros_like(P)
    ctr = np.array([0.046, 0.028, (sc['P'][:, 2].min() + sc['P'][:, 2].max()) / 2]) / INCH * scale
    fwd = np.array([1.0, 0, 0]); n = fwd - a * (fwd @ a); n /= np.linalg.norm(n)
    R = np.stack([n, np.cross(a, n), a], 1)           # can X -> n (nozzle forward), can Z -> a (up)
    sv = np.zeros(len(P), dtype=gv.dtype)
    sv['vertex'] = (P - ctr) @ R.T + c + a * along
    sv['normal'] = N @ R.T
    sv['uv'] = sc['UV']
    sv['bone_id'] = gv['bone_id'][0]
    w = np.zeros_like(gv['weight'][0]); w[0] = 1
    sv['weight'] = w
    if 'bone_count' in gv.dtype.names:
        sv['bone_count'] = 1
    sT, sM, stex = sc['T'], sc['M'], sc['tex']
    texnames = ['v_hands'] + stex
    t = vtf.read(os.path.join(css_dir, *(VMAT + TEX['v_hands'] + '.vtf').split('/')))
    texs = [('v_hands', t['w'], t['h'], dxt_mips(t), b'DXT1')]
    for gt in gtarw.read_txd(spraycan_txd):
        if gt['name'] in stex:
            texs.append((gt['name'], gt['w'], gt['h'], gt['mips'], gt['four']))
    out.img.add('cs_spray.txd', rw.txd(texs))
    man = {}
    for an, (seq, fps, cap) in {'idle': ('@idle', 0, 1), 'draw': ('@deploy', 60, 200)}.items():
        frames, ad = anim_frames(mdl, base, seq)
        fc, dur, times = frame_times(ad, fps, cap)
        ids = []
        for k, tt in enumerate(times):
            W = bone_worlds(mdl, frames, tt * (fc - 1))
            Hp, Hn = skin(mdl, hands[2], W)
            Sp, Sn = skin(mdl, sv, W)
            Ps, Ns, UVs, Ts, Ms = [], [], [], [], []
            off = 0
            for P_, N_, uv, T_, M_ in [(Hp, Hn, hands[2]['uv'], hands[3], np.zeros(len(hands[3]), int)), (Sp, Sn, sv['uv'], sT, sM + 1)]:
                G, Ng = to_gta(P_, N_, True)
                Ps.append(G); Ns.append(Ng); UVs.append(uv.astype(np.float64)); Ts.append(T_[:, ::-1] + off); Ms.append(M_)
                off += len(G)
            P_ = np.vstack(Ps)
            name = f'cs_spray_{an[:6]}_{k}'
            d = rw.dff(name, P_, np.vstack(Ns), np.vstack(UVs), np.vstack(Ts).astype(np.int64), np.concatenate(Ms), texnames)
            ids.append(out.add_object(name, d, 'cs_spray', P_.min(0).tolist(), P_.max(0).tolist()))
        man[an] = {'ids': ids, 'duration': round(dur, 3)}
    log('  spray: ' + ', '.join(f'{a} {len(m["ids"])}' for a, m in man.items()))
    return {'anims': man}
