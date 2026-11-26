"""Step 0: crude but contract-valid stand-in (A-pose base mesh, lofted boxy shirt, analytic decals)."""
import os, sys, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from glbw import GLB, angle_weighted_normals

V, G = load_base()
body_q = G['body']
bi = np.unique(body_q)
ymin, ymax = V[bi, 1].min(), V[bi, 1].max()
sc = 1.68 / (ymax - ymin)
P = (V - [0, ymin, 0]) * sc
print('scale', sc, 'body bbox', P[bi].min(0), P[bi].max(0))

W = load_weights(len(V))
def wsum(names):
    w = np.zeros(len(V))
    for nme in names:
        for b, (i, x) in W.items():
            if b.startswith(nme):
                np.add.at(w, i, x)
    return w
wleg = wsum(['upperleg', 'lowerleg', 'pelvis', 'root', 'spine05'])
tris = quads_to_tris(body_q)
N = np.zeros_like(P); N[:] = angle_weighted_normals(P, tris)

# trousers: leg / pelvis faces between ankle and waist, pushed out along the normal
ok = (wleg > 0.5) & (P[:, 1] > 0.085) & (P[:, 1] < 1.03)
pq = body_q[ok[body_q].all(1)]
Pp = P + N * 0.014
pv, pf, _ = compact(Pp, pq)

# shirt: lofted superellipse tube
EXP = 2.6
def sec(y):
    ys = [0.74, 1.20, 1.33, 1.405, 1.45]
    a = [0.275, 0.275, 0.265, 0.19, 0.085]
    b = [0.175, 0.175, 0.165, 0.125, 0.085]
    c = [0.030, 0.025, 0.015, -0.005, -0.01]
    return np.interp(y, ys, a), np.interp(y, ys, b), np.interp(y, ys, c)
def ring(y, n=96):
    a, b, c = sec(y)
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    x = a * np.sign(np.cos(t)) * np.abs(np.cos(t)) ** (2 / EXP)
    z = c + b * np.sign(np.sin(t)) * np.abs(np.sin(t)) ** (2 / EXP)
    return np.stack([x, np.full(n, y), z], 1)
def loft(rings):
    n = len(rings[0]); vs = np.concatenate(rings); q = []
    for r in range(len(rings) - 1):
        for i in range(n):
            j = (i + 1) % n
            q.append([r * n + i, r * n + j, (r + 1) * n + j, (r + 1) * n + i])
    return vs, np.array(q)
ys = np.concatenate([np.linspace(0.74, 1.20, 24), np.linspace(1.22, 1.45, 16)])
tv, tq = loft([ring(y) for y in ys])
# winding: for theta counter-clockwise seen from +Y and y increasing, quad (i, j, up j, up i) faces inward -> flip
tq = tq[:, ::-1]
# sleeves along the A-pose arm
def sleeve(sign):
    o = np.array([sign * 0.215, 1.385, -0.01]); d = np.array([sign * 0.72, -0.69, 0.0]); d /= np.linalg.norm(d)
    u = np.array([0, 0, 1.0]); w = np.cross(d, u)
    rings = []
    for s in np.linspace(-0.02, 0.27, 10):
        r = 0.085 + 0.02 * s / 0.27
        t = np.linspace(0, 2 * np.pi, 40, endpoint=False)
        rings.append(o + d * s + np.outer(np.cos(t), u) * r + np.outer(np.sin(t), w) * r)
    v, q = loft(rings)
    return v, q
sv = [sleeve(1), sleeve(-1)]
def fix_winding(v, q):
    """make quads face away from the mesh centroid axis (good enough for tubes)"""
    t = quads_to_tris(q); n = np.cross(v[t[:, 1]] - v[t[:, 0]], v[t[:, 2]] - v[t[:, 0]])
    cen = v[t].mean(1) - v.mean(0)
    return q[:, ::-1] if (n * cen).sum() < 0 else q
tq = fix_winding(tv, tq)
off = len(tv); allv = [tv]; allq = [tq]
for v, q in sv:
    q = fix_winding(v, q); allq.append(q + off); allv.append(v); off += len(v)
tee_v = np.concatenate(allv); tee_q = np.concatenate(allq)

# decals on the analytic tube
def zsurf(x, y, sign):
    a, b, c = sec(y)
    return c + sign * b * np.clip(1 - np.abs(x / a) ** EXP, 0, 1) ** (1 / EXP)
def decal(cx, ytop, w, h, nx, ny, sign):
    us = np.linspace(0, 1, nx + 1); vs_ = np.linspace(0, 1, ny + 1)
    uu, vv = np.meshgrid(us, vs_)
    x = cx + sign * (uu - 0.5) * w        # front: u grows with +x ; back: u grows with -x
    y = ytop - vv * h
    z = zsurf(x, y, sign)
    p = np.stack([x, y, z], -1)
    # normals by finite differences
    e = 1e-4
    dzdx = (zsurf(x + e, y, sign) - zsurf(x - e, y, sign)) / (2 * e)
    dzdy = (zsurf(x, y + e, sign) - zsurf(x, y - e, sign)) / (2 * e)
    n = np.stack([-dzdx, -dzdy, np.ones_like(x)], -1) * sign
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    p = p + n * 0.0012
    idx = np.arange((nx + 1) * (ny + 1)).reshape(ny + 1, nx + 1)
    q = np.stack([idx[:-1, :-1], idx[1:, :-1], idx[1:, 1:], idx[:-1, 1:]], -1).reshape(-1, 4)
    t = quads_to_tris(q)
    fn = np.cross(p.reshape(-1, 3)[t[:, 1]] - p.reshape(-1, 3)[t[:, 0]], p.reshape(-1, 3)[t[:, 2]] - p.reshape(-1, 3)[t[:, 0]])
    if (fn[:, 2].mean() > 0) != (sign > 0):
        t = t[:, ::-1]
    return p.reshape(-1, 3), n.reshape(-1, 3), t, np.stack([uu, vv], -1).reshape(-1, 2)

collar_back_y = 1.45
pf_p, pf_n, pf_t, pf_uv = decal(0.095, 1.315, 0.105, 0.070, 24, 16, +1)
pb_p, pb_n, pb_t, pb_uv = decal(0.0, collar_back_y - 0.10, 0.38, 0.507, 60, 80, -1)

g = GLB()
def mat(name, col, rough=0.9, ds=False, blend=False):
    m = {"name": name, "pbrMetallicRoughness": {"baseColorFactor": col, "metallicFactor": 0.0, "roughnessFactor": rough}}
    if ds: m["doubleSided"] = True
    if blend: m["alphaMode"] = "BLEND"
    return g.add_material(m)
m_skin = mat('Skin', [0.84, 0.81, 0.76, 1], 0.62)
m_fab = mat('Fabric', [0.02, 0.02, 0.022, 1], 0.9, ds=True)
m_pants = mat('Pants', [0.2, 0.2, 0.18, 1], 0.9, ds=True)
m_pf = mat('PrintFront', [1, 1, 1, 1], 0.82, blend=True)
m_pb = mat('PrintBack', [1, 1, 1, 1], 0.82, blend=True)

wtor = wsum(['spine', 'breast', 'root', 'pelvis', 'clavicle', 'upperleg', 'shoulder', 'upperarm'])
hide = (wtor > 0.5) & (P[:, 1] > 0.80) & (P[:, 1] < 1.40) & (np.abs(P[:, 0]) < 0.30)
body_q = body_q[~hide[body_q].all(1)]
bv, bf, _ = compact(P, body_q); bt = quads_to_tris(bf)
g.add_mesh('Body', m_skin, bv, angle_weighted_normals(bv, bt), bt)
pt = quads_to_tris(pf)
g.add_mesh('Pants', m_pants, pv, angle_weighted_normals(pv, pt), pt)
tt = quads_to_tris(tee_q)
g.add_mesh('Tee', m_fab, tee_v, angle_weighted_normals(tee_v, tt), tt)
g.add_mesh('PrintFront', m_pf, pf_p, pf_n, pf_t, uv=pf_uv)
g.add_mesh('PrintBack', m_pb, pb_p, pb_n, pb_t, uv=pb_uv)
out = os.path.join(HERE, 'out', 'step0.glb')
print('bytes', g.write(out), out)
