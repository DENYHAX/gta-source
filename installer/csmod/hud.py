"""models/txd/cshud.txd: CS:S buy menu icons, AWP scope quadrants and GTA's own mouse cursor."""
import numpy as np

from . import gtarw, rw, vtf

ICONS = {'b_ak47': 'ak47', 'b_m4a1': 'm4a1', 'b_awp': 'awp', 'b_mp5': 'mp5', 'b_m3': 'm3', 'b_glock': 'glock18',
         'b_usp': 'usp45', 'b_deag': 'deserteagle', 'b_kev': 'kevlar', 'b_kevh': 'kevlar_helmet', 'b_na': 'not_available'}
SCOPE = 'materials/sprites/scope_arc.vtf'
CSS_FILES = [f'materials/vgui/gfx/vgui/{v}.vtf' for v in ICONS.values()] + [SCOPE]


def _argb(img_rgba):
    a = np.asarray(img_rgba.convert('RGBA'), np.uint8)
    return a[:, :, [2, 1, 0, 3]].tobytes()              # D3DFMT_A8R8G8B8 = B, G, R, A in memory


def build(read_css, fronten_txd_bytes):
    """read_css(path) -> bytes of a CS:S file. Names stay <= 7 characters (LOAD_SPRITE reads only 7)."""
    texs = []
    for name, src in ICONS.items():
        im = vtf.to_image(vtf.read(read_css(f'materials/vgui/gfx/vgui/{src}.vtf')))
        texs.append((name, im.width, im.height, [_argb(im)], b'ARGB'))
    arc = np.asarray(vtf.to_image(vtf.read(read_css(SCOPE))).convert('RGBA'))
    quads = {'scp_br': arc, 'scp_bl': arc[:, ::-1], 'scp_tr': arc[::-1], 'scp_tl': arc[::-1, ::-1]}
    for name, q in quads.items():
        q = np.ascontiguousarray(q)
        texs.append((name, q.shape[1], q.shape[0], [q[:, :, [2, 1, 0, 3]].tobytes()], b'ARGB'))
    for t in gtarw.read_txd(fronten_txd_bytes):
        if t['name'].lower() == 'mouse':
            texs.append(('mouse', t['w'], t['h'], t['mips'][:1], t['four'], 1))   # point filtering, like GTA's own cursor
            break
    return rw.txd(texs)
