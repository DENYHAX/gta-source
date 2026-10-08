"""Source MDL/VVD/VTX loading (through SourceIO, without Blender) and CPU skinning / animation sampling."""
import numpy as np

# SourceIO is downloaded by the installer into installer/_deps and put on sys.path before this import
from SourceIO.library.utils import FileBuffer
from SourceIO.library.models.mdl.v49.mdl_file import MdlV49
from SourceIO.library.models.mdl.v44.mdl_file import MdlV44
from SourceIO.library.models.vvd import Vvd
from SourceIO.library.models.vtx.v7.vtx import Vtx
from SourceIO.library.utils.common import get_slice

def merge_strip_groups(vtx_mesh):
    ia, va, off = [], [], 0
    for sg in vtx_mesh.strip_groups:
        ia.append(np.add(sg.indices, off))
        va.append(sg.vertexes['original_mesh_vertex_index'].reshape(-1).astype(np.uint32))
        off += sum(s.vertex_count for s in sg.strips)
    return np.hstack(ia), np.hstack(va), off

def load(base, bodies=None):
    mdl = MdlV44.from_buffer(FileBuffer(base + '.mdl'))
    vvd = Vvd.from_buffer(FileBuffer(base + '.vvd'))
    vtx = Vtx.from_buffer(FileBuffer(base + '.dx90.vtx'))
    allv = vvd.lod_data[0]
    out = []   # list of (verts structured, tris, matidx)
    for bp_i, (vtx_bp, bp) in enumerate(zip(vtx.body_parts, mdl.body_parts)):
        models = list(zip(vtx_bp.models, bp.models))
        sel = 0 if bodies is None else bodies.get(bp.name, 0)
        for mi, (vtx_model, model) in enumerate(models):
            if mi != sel or model.vertex_count == 0: continue
            mv = get_slice(allv, model.vertex_offset, model.vertex_count)
            lod = vtx_model.model_lods[0]
            acc = 0
            for vtx_mesh, mesh in zip(lod.meshes, model.meshes):
                if not vtx_mesh.strip_groups: continue
                idx, verts, off = merge_strip_groups(vtx_mesh)
                v = mv[np.add(verts, mesh.vertex_index_start)]
                out.append((bp.name, model.name, v, np.flip(idx).reshape(-1, 3), mesh.material_index))
    return mdl, out




def qmat(q):
    x,y,z,w = q
    return np.array([[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
                     [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
                     [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])
def local(pos, q):
    m = np.identity(4); m[:3,:3] = qmat(q); m[:3,3] = pos; return m

def _slerp(q0, q1, t):
    q0 = np.asarray(q0, np.float64); q1 = np.asarray(q1, np.float64)
    d = float(np.dot(q0, q1))
    if d < 0: q1 = -q1; d = -d
    if d > 0.9995:
        q = q0 + t * (q1 - q0)
    else:
        th = np.arccos(d); q = (np.sin((1 - t) * th) * q0 + np.sin(t * th) * q1) / np.sin(th)
    return q / np.linalg.norm(q)

def bone_worlds(mdl, frames=None, f=0):
    # f may be fractional: bones are interpolated between keyframes (lerp pos, slerp rot) like the Source engine
    W = []
    for b in mdl.bones:
        if frames is not None and b.name in frames:
            seq = frames[b.name]; n = len(seq)
            f0 = int(np.floor(f)); t = f - f0
            f0 = max(0, min(f0, n - 1)); f1 = min(f0 + 1, n - 1)
            a, c = seq[f0], seq[f1]
            if t > 1e-6 and f1 != f0:
                L = local(a['pos'] * (1 - t) + c['pos'] * t, _slerp(a['rot'], c['rot'], t))
            else:
                L = local(a['pos'], a['rot'])
        else:
            L = local(b.position, b.quat)
        W.append(L if b.parent_id < 0 else W[b.parent_id] @ L)
    return W

def skin(mdl, verts, W):
    S = []
    for b, w in zip(mdl.bones, W):
        p2b = np.identity(4); p2b[:3,:4] = np.array(b.pose_to_bone, dtype=np.float64).reshape(4,3).T
        S.append(w @ p2b)
    S = np.array(S)
    pos = verts['vertex'].astype(np.float64); nrm = verts['normal'].astype(np.float64)
    ids = verts['bone_id']; wts = verts['weight']; cnt = verts['bone_count'] if 'bone_count' in verts.dtype.names else None
    P = np.zeros_like(pos); N = np.zeros_like(nrm)
    for k in range(3):
        wk = wts[:, k].astype(np.float64)
        if cnt is not None: wk = np.where(cnt > k, wk, 0)
        M = S[ids[:, k]]
        P += wk[:,None] * (np.einsum('nij,nj->ni', M[:,:3,:3], pos) + M[:,:3,3])
        N += wk[:,None] * np.einsum('nij,nj->ni', M[:,:3,:3], nrm)
    N /= np.linalg.norm(N, axis=1, keepdims=True) + 1e-9
    return P, N

def anim_frames(mdl, base, name_part):
    buf = FileBuffer(base + '.mdl')
    for ad in mdl.anim_descs:
        if name_part in ad.name:
            return ad.read_animations(buf, mdl.bones, None, None), ad
    return None, None

