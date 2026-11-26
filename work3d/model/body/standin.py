"""Contract-valid stand-in for the page team: the real figure plus a crude lofted boxy shirt and analytic decals.
The real shirt comes from the garment stage; this only keeps names, scale, orientation and UV directions right."""
import os, sys, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
import assemble as A
from glbw import GLB, angle_weighted_normals

EXP = 2.7
def make(out_path):
    cut = dict(A.CUT); cut.update(neck_keep_radius=0.082, neck_keep_depth=0.028, arm_keep_from_joint=0.185)   # skin starts 2.5 cm inside the stand-in sleeves
    A.CUT.update(cut)
    meshes, L, full, pants = A.figure_meshes()
    nb = L['neck_base']; ncy = nb['center'][1]; ncz = nb['center'][2]
    hem = L['crotch_height'] - 0.02
    cf = L['chest_front']['point']; ub = L['upper_back']['point']
    zc_ch = 0.5 * (cf[2] + ub[2]); zc_hip = 0.5 * (L['hip']['z_front'] + L['seat_back']['z'])
    ys = [hem, 1.20, 1.335, 1.39, ncy + 0.032]
    a = [0.228, 0.228, 0.215, 0.165, 0.074]
    b = [0.135, 0.142, 0.135, 0.105, 0.070]
    c = [zc_hip, zc_ch, zc_ch - 0.004, ncz - 0.004, ncz + 0.004]
    def sec(y): return np.interp(y, ys, a), np.interp(y, ys, b), np.interp(y, ys, c)
    def ring(y, n=96):
        aa, bb, cc = sec(y); t = np.linspace(0, 2 * np.pi, n, endpoint=False)
        return np.stack([aa * np.sign(np.cos(t)) * np.abs(np.cos(t)) ** (2 / EXP), np.full(n, y), cc + bb * np.sign(np.sin(t)) * np.abs(np.sin(t)) ** (2 / EXP)], 1)
    def loft(rings):
        n = len(rings[0]); vs = np.concatenate(rings); q = []
        for r in range(len(rings) - 1):
            for i in range(n):
                j = (i + 1) % n; q.append([r * n + i, r * n + j, (r + 1) * n + j, (r + 1) * n + i])
        return vs, np.array(q)
    def outward(v, q):
        t = quads_to_tris(q); n = np.cross(v[t[:, 1]] - v[t[:, 0]], v[t[:, 2]] - v[t[:, 0]])
        return q[:, ::-1] if (n * (v[t].mean(1) - v.mean(0))).sum() < 0 else q
    yy = np.concatenate([np.linspace(hem, 1.20, 26), np.linspace(1.215, ys[-1], 20)])
    tv, tq = loft([ring(y) for y in yy]); tq = outward(tv, tq)
    allv = [tv]; allq = [tq]; off = len(tv)
    for s, sx in (('L', 1), ('R', -1)):
        sh = np.array(L['shoulder_joint_' + s]); el = np.array(L['elbow_' + s]); d = (el - sh); ln = np.linalg.norm(d); d /= ln
        u = np.array([0, 0, 1.0]); w = np.cross(d, u); w /= np.linalg.norm(w); u = np.cross(w, d)
        rings = []
        for sdist in np.linspace(-0.03, ln - 0.03, 12):
            r = 0.078 + 0.012 * sdist / ln; t = np.linspace(0, 2 * np.pi, 40, endpoint=False)
            rings.append(sh + d * sdist + np.outer(np.cos(t), u) * r + np.outer(np.sin(t), w) * r)
        v, q = loft(rings); q = outward(v, q); allv.append(v); allq.append(q + off); off += len(v)
    tee_v = np.concatenate(allv); tee_q = np.concatenate(allq); tt = quads_to_tris(tee_q)
    def zsurf(x, y, sign):
        aa, bb, cc = sec(y)
        return cc + sign * bb * np.clip(1 - np.abs(x / aa) ** EXP, 0, 1) ** (1 / EXP)
    def decal(cx, ytop, w, h, nx, ny, sign):
        uu, vv = np.meshgrid(np.linspace(0, 1, nx + 1), np.linspace(0, 1, ny + 1))
        x = cx + sign * (uu - 0.5) * w; y = ytop - vv * h; z = zsurf(x, y, sign); e = 1e-4
        dzdx = (zsurf(x + e, y, sign) - zsurf(x - e, y, sign)) / (2 * e); dzdy = (zsurf(x, y + e, sign) - zsurf(x, y - e, sign)) / (2 * e)
        n = np.stack([-dzdx, -dzdy, np.ones_like(x)], -1) * sign; n /= np.linalg.norm(n, axis=-1, keepdims=True)
        p = (np.stack([x, y, z], -1) + n * 0.0012).reshape(-1, 3)
        idx = np.arange((nx + 1) * (ny + 1)).reshape(ny + 1, nx + 1)
        q = np.stack([idx[:-1, :-1], idx[1:, :-1], idx[1:, 1:], idx[:-1, 1:]], -1).reshape(-1, 4); t = quads_to_tris(q)
        fn = np.cross(p[t[:, 1]] - p[t[:, 0]], p[t[:, 2]] - p[t[:, 0]])
        if (fn[:, 2].mean() > 0) != (sign > 0): t = t[:, ::-1]
        return p, n.reshape(-1, 3), t, np.stack([uu, vv], -1).reshape(-1, 2)
    collar_front_y = nb['front'][1]; collar_back_y = nb['back'][1] + 0.01
    pf = decal(0.095, collar_front_y - 0.09, 0.105, 0.070, 24, 16, +1)
    pb = decal(0.0, collar_back_y - 0.10, 0.38, 0.507, 60, 80, -1)
    g = GLB(); A.add_figure(g, meshes)
    mf = A.mat(g, 'Fabric', [0.012, 0.012, 0.014, 1], 0.9, ds=True)
    g.add_mesh('Tee', mf, tee_v, angle_weighted_normals(tee_v, tt), tt)
    g.add_mesh('PrintFront', A.mat(g, 'PrintFront', [1, 1, 1, 1], 0.82, blend=True), pf[0], pf[1], pf[2], uv=pf[3])
    g.add_mesh('PrintBack', A.mat(g, 'PrintBack', [1, 1, 1, 1], 0.82, blend=True), pb[0], pb[1], pb[2], uv=pb[3])
    return g.write(out_path)

if __name__ == '__main__':
    out = script_args()[0] if script_args() else HERE + '/out/standin.glb'
    print('standin bytes', make(out), out)
