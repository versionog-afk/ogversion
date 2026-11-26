"""Chest print decal: a regular grid laid on the simulated front, parametrised by arc length along the surface
(so it is 0.30 m x 0.2466 m measured on the cloth and the image is not stretched), pushed out along the fabric's
smooth normals."""
import numpy as np


def build_print(P, G, seam_pt, top_gap=0.085, W=0.30, aspect=3600.0 / 2959.0, nu=56, nv=46, offset=0.0012, log=print):
    import bpy  # noqa: F401
    from mathutils.bvhtree import BVHTree
    from mathutils import Vector
    H = W / aspect
    pos, nrm, tris = G.pos, G.nrm, G.outer_tris
    tree = BVHTree.FromPolygons([tuple(map(float, p)) for p in pos], [tuple(int(i) for i in t) for t in tris])
    down = Vector((0, 0, -1))

    def cast(x, y):
        loc, n, idx, dist = tree.ray_cast(Vector((float(x), float(y), 2.0)), down)
        if loc is None:
            return None
        return np.array(loc), idx

    def smooth_normal(p, idx):
        a, b, c = tris[idx]
        A, B, C = pos[a], pos[b], pos[c]
        v0, v1, v2 = B - A, C - A, p - A
        d00, d01, d11, d20, d21 = v0 @ v0, v0 @ v1, v1 @ v1, v2 @ v0, v2 @ v1
        den = d00 * d11 - d01 * d01
        v = (d11 * d20 - d01 * d21) / den
        w = (d00 * d21 - d01 * d20) / den
        u = 1 - v - w
        n = u * nrm[a] + v * nrm[b] + w * nrm[c]
        return n / np.linalg.norm(n)

    x0 = float(seam_pt[0])
    # centre front line: arc length from the collar seam downwards
    ys = seam_pt[1] - np.arange(0, 0.46, 0.001)
    cz = []
    for y in ys:
        h = cast(x0, y - 1e-5)
        cz.append(h[0][2] if h is not None else np.nan)
    cz = np.array(cz)
    ok = np.isfinite(cz)
    ys, cz = ys[ok], cz[ok]
    arc = np.concatenate([[0], np.cumsum(np.hypot(np.diff(ys), np.diff(cz)))])
    rows_arc = top_gap + np.arange(nv + 1) * H / nv
    row_y = np.interp(rows_arc, arc, ys)
    xs = np.arange(-W / 2 - 0.05, W / 2 + 0.0501, 0.001)
    Ppos = np.zeros((nv + 1, nu + 1, 3))
    Pn = np.zeros((nv + 1, nu + 1, 3))
    miss = 0
    for k in range(nv + 1):
        y = row_y[k]
        zz = np.full(len(xs), np.nan)
        for i, x in enumerate(xs):
            h = cast(x0 + x, y)
            if h is not None:
                zz[i] = h[0][2]
        good = np.isfinite(zz)
        zz = np.interp(xs, xs[good], zz[good])
        a = np.concatenate([[0], np.cumsum(np.hypot(np.diff(xs), np.diff(zz)))])
        a -= np.interp(0.0, xs, a)                       # signed arc from the centre line
        tx = np.interp((np.arange(nu + 1) / nu - 0.5) * W, a, xs)
        for j in range(nu + 1):
            h = cast(x0 + tx[j], y)
            if h is None:
                miss += 1
                p = np.array([x0 + tx[j], y, np.interp(tx[j], xs, zz)])
                n = np.array([0, 0, 1.0])
            else:
                p, idx = h
                n = smooth_normal(p, idx)
            Ppos[k, j] = p + n * offset
            Pn[k, j] = n
    # tangents (+u), orthogonal to the normal
    T = np.empty_like(Ppos)
    T[:, 1:-1] = Ppos[:, 2:] - Ppos[:, :-2]
    T[:, 0] = Ppos[:, 1] - Ppos[:, 0]
    T[:, -1] = Ppos[:, -1] - Ppos[:, -2]
    T -= (T * Pn).sum(2, keepdims=True) * Pn
    T /= np.linalg.norm(T, axis=2, keepdims=True)
    uu, vv = np.meshgrid(np.arange(nu + 1) / nu, np.arange(nv + 1) / nv)
    uv = np.stack([uu, vv], 2).reshape(-1, 2)
    idx = np.arange((nv + 1) * (nu + 1)).reshape(nv + 1, nu + 1)
    tl, bl, br, tr = idx[:-1, :-1].ravel(), idx[1:, :-1].ravel(), idx[1:, 1:].ravel(), idx[:-1, 1:].ravel()
    tri = np.concatenate([np.stack([tl, bl, br], 1), np.stack([tl, br, tr], 1)])
    tang = np.concatenate([T.reshape(-1, 3), np.ones(((nv + 1) * (nu + 1), 1))], 1)
    # measured size along the surface
    wm = np.linalg.norm(np.diff(Ppos, axis=1), axis=2).sum(1)
    hm = np.linalg.norm(np.diff(Ppos, axis=0), axis=2).sum(0)
    log(f"[print] grid {nu}x{nv}, surface width {wm.min():.4f}-{wm.max():.4f} m, height {hm.min():.4f}-{hm.max():.4f} m, "
        f"top edge {top_gap * 100:.1f} cm below the rib, ray misses {miss}")
    return dict(pos=Ppos.reshape(-1, 3), nrm=Pn.reshape(-1, 3), uv=uv, tris=tri, tangent=tang)
