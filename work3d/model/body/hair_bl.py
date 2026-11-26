"""Hair: a sculpted cap pulled back into a low bun. Built as a signed distance field around the head
(nearest-surface queries with Blender's BVH), meshed with surface nets, smoothed and decimated in Blender.
Run with the Blender python: bvenv/bin/python hair_bl.py"""
import os, sys, json, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
import bpy, bmesh
from mathutils.bvhtree import BVHTree
from mathutils import Vector

# all positions are relative to E = midpoint between the eyeball centres
HP = dict(h=0.002, C=(0.0, 0.014, -0.070),
          # hairline: azimuth from the front (deg) -> elevation (deg) about C
          line=[(0, 28.5), (25, 30), (45, 30), (58, 25), (66, 14), (70, 2), (76, -6), (86, -9), (100, -12), (112, -22), (135, -43), (160, -51), (180, -53)],
          ear_a=(0.076, -0.039, -0.077), ear_b=(0.076, 0.011, -0.087), ear_r=0.019,
          t_edge=0.0028, t_body=0.0062, t_back=0.0035,
          bun_c=(0.0, -0.028, -0.180), bun_r=(0.041, 0.037, 0.031), bun_k=0.016, gather=0.007,
          strands=24, strand_amp=0.0008,
          target_tris=5600)

def smoothstep(x):
    x = np.clip(x, 0, 1); return x * x * (3 - 2 * x)

def smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b * (1 - h) + a * h - k * h * (1 - h)

def smax(a, b, k):
    return -smin(-a, -b, k)

def hairline_m(q, hp=HP, E=np.zeros(3)):
    q = q - E
    """smooth scalar on head surface points: > 0 inside the hair region, roughly metres from the hairline"""
    C = np.array(hp['C']); rel = q - C
    ax = np.abs(rel[:, 0])
    phi = np.degrees(np.arctan2(ax, rel[:, 2]))
    theta = np.degrees(np.arctan2(rel[:, 1], np.sqrt(ax ** 2 + rel[:, 2] ** 2)))
    lp = np.array(hp['line'], float)
    # smooth the polyline a little by dense resampling + box filter
    xs = np.linspace(0, 180, 361); ys = np.interp(xs, lp[:, 0], lp[:, 1])
    k = 8; pad = np.concatenate([ys[k:0:-1], ys, ys[-2:-k - 2:-1]]); ys = np.convolve(pad, np.ones(2 * k + 1) / (2 * k + 1), 'valid')
    th = np.interp(phi, xs, ys)
    m = np.radians(theta - th) * 0.095
    # the ears stay free: capsule around each ear
    a = np.array(hp['ear_a']); b = np.array(hp['ear_b'])
    p = np.stack([ax, q[:, 1], q[:, 2]], 1)
    ab = b - a; t = np.clip(((p - a) @ ab) / (ab @ ab), 0, 1)
    de = np.linalg.norm(p - (a + t[:, None] * ab), axis=1) - hp['ear_r']
    return smin(m, de, 0.006), phi

def eye_mid(P, G):
    return 0.5 * (P[np.unique(G['helper-l-eye'])].mean(0) + P[np.unique(G['helper-r-eye'])].mean(0))

def surface_nets(f, origin, h):
    """naive surface nets on a regular grid, returns verts (N,3) and quads (M,4) with outward (towards f > 0) winding"""
    nx, ny, nz = f.shape
    cs = np.zeros((nx - 1, ny - 1, nz - 1, 3)); cn = np.zeros((nx - 1, ny - 1, nz - 1))
    idx = np.indices(f.shape).transpose(1, 2, 3, 0).astype(np.float64)
    edges = []
    for ax in range(3):
        sl0 = [slice(None)] * 3; sl1 = [slice(None)] * 3
        sl0[ax] = slice(0, -1); sl1[ax] = slice(1, None)
        f0 = f[tuple(sl0)]; f1 = f[tuple(sl1)]
        cross = (f0 < 0) != (f1 < 0)
        t = np.where(cross, f0 / np.where(cross, f0 - f1, 1), 0)
        pos = idx[tuple(sl0)].copy(); pos[..., ax] += t
        pos = pos * cross[..., None]
        # distribute to the 4 cells sharing each edge
        o = [a for a in range(3) if a != ax]
        for da in (0, 1):
            for db in (0, 1):
                src = [slice(None)] * 3; dst = [slice(None)] * 3
                # edge index along o[0] = e ; cells e-1 and e  -> for da=0 cell = e (needs e <= n-2), da=1 cell = e-1 (needs e >= 1)
                for oo, dd in ((o[0], da), (o[1], db)):
                    n = f.shape[oo]
                    if dd == 0: src[oo] = slice(0, n - 1); dst[oo] = slice(0, n - 1)
                    else: src[oo] = slice(1, n); dst[oo] = slice(0, n - 1)
                cs[tuple(dst)] += pos[tuple(src)]; cn[tuple(dst)] += cross[tuple(src)]
        edges.append((cross, f0 < 0))
    has = cn > 0
    vid = -np.ones(cn.shape, dtype=np.int64); vid[has] = np.arange(has.sum())
    verts = cs[has] / cn[has][:, None] * h + np.asarray(origin)
    quads = []
    for ax in range(3):
        cross, neg0 = edges[ax]
        o = [a for a in range(3) if a != ax]
        e = np.argwhere(cross)
        ok = (e[:, o[0]] >= 1) & (e[:, o[1]] >= 1) & (e[:, o[0]] <= f.shape[o[0]] - 2) & (e[:, o[1]] <= f.shape[o[1]] - 2)
        e = e[ok]
        def cell(d0, d1):
            c = e.copy(); c[:, o[0]] -= d0; c[:, o[1]] -= d1
            return vid[c[:, 0], c[:, 1], c[:, 2]]
        q = np.stack([cell(1, 1), cell(0, 1), cell(0, 0), cell(1, 0)], 1)
        inside_first = neg0[e[:, 0], e[:, 1], e[:, 2]]
        # orientation: for axis order (ax, o0, o1) cyclic the quad above is counter-clockwise seen from +ax
        cyc = (ax, o[0], o[1]) in ((0, 1, 2), (1, 2, 0), (2, 0, 1))
        flip = inside_first != cyc
        flip = ~flip if False else flip
        q[flip] = q[flip][:, ::-1]
        quads.append(q)
    quads = np.concatenate(quads)
    quads = quads[(quads >= 0).all(1)]
    return verts, quads

def mesh_obj(name, v, faces):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(x) for x in v], [], [tuple(int(i) for i in f) for f in faces])
    me.update()
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    return ob

def to_np(ob):
    me = ob.data
    v = np.zeros(len(me.vertices) * 3); me.vertices.foreach_get('co', v)
    me.calc_loop_triangles()
    t = np.zeros(len(me.loop_triangles) * 3, dtype=np.int32); me.loop_triangles.foreach_get('vertices', t)
    return v.reshape(-1, 3), t.reshape(-1, 3).astype(np.int64)

def build(hp=HP, debug_mask=False):
    t0 = time.time()
    d = np.load(os.path.join(HERE, 'out', 'figure.npz')); P = d['P']
    V, G = load_base(); q = G['body']
    E = eye_mid(P, G)
    keep = (P[q][:, :, 1] > E[1] - 0.16).all(1)
    hv, hq, _ = compact(P, q[keep])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    head = mesh_obj('head', hv, hq)
    mod = head.modifiers.new('ss', 'SUBSURF'); mod.levels = 2; mod.render_levels = 2
    dg = bpy.context.evaluated_depsgraph_get(); ev = head.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev)
    dv = np.zeros(len(me.vertices) * 3); me.vertices.foreach_get('co', dv); dv = dv.reshape(-1, 3)
    polys = [tuple(p.vertices) for p in me.polygons]
    bvh = BVHTree.FromPolygons([tuple(x) for x in dv], polys)
    print('dense head', len(dv), len(polys), 'bvh %.1fs' % (time.time() - t0))
    if debug_mask:
        m, _ = hairline_m(dv, hp, E)
        return dv, np.array(polys), m
    h = hp['h']
    lo = E + np.array([-0.112, -0.121, -0.24]); hi = E + np.array([0.112, 0.139, 0.035])
    n = np.ceil((hi - lo) / h).astype(int) + 1
    gx, gy, gz = [lo[i] + np.arange(n[i]) * h for i in range(3)]
    pts = np.stack(np.meshgrid(gx, gy, gz, indexing='ij'), -1).reshape(-1, 3)
    # cheap prefilter: only voxels within a band of the head's bounding ellipsoid get exact queries
    c0 = (dv.max(0) + dv.min(0)) / 2
    loc = np.zeros_like(pts); dist = np.full(len(pts), 0.05); sgn = np.ones(len(pts))
    fn = bvh.find_nearest
    for i in range(len(pts)):
        r = fn(pts[i], 0.045)
        if r[0] is not None:
            l, nr, _, dd = r
            loc[i] = l; dist[i] = dd
            pp = pts[i]
            if (pp[0] - l[0]) * nr[0] + (pp[1] - l[1]) * nr[1] + (pp[2] - l[2]) * nr[2] < 0: sgn[i] = -1
    print('sdf %d voxels %.1fs' % (len(pts), time.time() - t0))
    near = dist < 0.0449
    dh = dist * sgn
    m = np.full(len(pts), -0.05); phi = np.zeros(len(pts))
    mm, ph = hairline_m(loc[near], hp, E); m[near] = mm; phi[near] = ph
    bc = np.array(hp['bun_c']) + E; br = np.array(hp['bun_r'])
    dbun_c = np.linalg.norm(pts - bc, axis=1)
    Cw = np.array(hp['C']) + E
    back = smoothstep((Cw[2] - loc[:, 2]) / 0.07)
    T = hp['t_edge'] + hp['t_body'] * smoothstep(m / 0.028) + hp['t_back'] * back * smoothstep(m / 0.022) \
        + hp['gather'] * np.exp(-(dbun_c / 0.075) ** 2) * smoothstep(m / 0.02)
    # broad combed-back bands that run from the hairline to the bun
    if hp.get('strand_amp', 0) > 0:
        A = (Cw + np.array([0, 0.065, 0.085])) - bc; A /= np.linalg.norm(A)
        rel = pts - bc; along = rel @ A; perp = rel - np.outer(along, A)
        u = np.array([1.0, 0, 0]); w = np.cross(A, u); w /= np.linalg.norm(w)
        psi = np.arctan2(perp @ w, perp @ u); rp = np.linalg.norm(perp, axis=1)
        band = np.cos(hp['strands'] * psi)
        T = T + hp['strand_amp'] * band * smoothstep(m / 0.03) * smoothstep((rp - 0.03) / 0.04) * smoothstep((along - 0.0) / 0.04)
    cap = smax(dh - T, -m, 0.0025 + 0.0045 * back)        # the edge is rounder at the nape, where the neck falls away under it
    cap = np.maximum(cap, -(dh + 0.006))
    cap[~near] = 0.03
    bun = (np.linalg.norm((pts - bc) / br, axis=1) - 1) * br.min()
    f = smin(cap, bun, hp['bun_k'])
    f = np.maximum(f, -(dh + 0.006))
    f = f.reshape(n)
    v, qd = surface_nets(f, lo, h)
    print('surface nets', len(v), len(qd), '%.1fs' % (time.time() - t0))
    # orientation check: normals must point away from the head centre on average
    tq = quads_to_tris(qd); nn = np.cross(v[tq[:, 1]] - v[tq[:, 0]], v[tq[:, 2]] - v[tq[:, 0]])
    if (nn * (v[tq].mean(1) - c0)).sum() < 0:
        qd = qd[:, ::-1]
    # drop what sits inside the head
    vd = np.array([bvh.find_nearest(x)[3] * (1 if (Vector(x) - bvh.find_nearest(x)[0]).dot(bvh.find_nearest(x)[1]) >= 0 else -1) for x in v])
    keepq = (vd[qd] > -0.0035).any(1)
    v2, q2, _ = compact(v, qd[keepq])
    ob = mesh_obj('Hair', v2, q2)
    bpy.context.view_layer.objects.active = ob; ob.select_set(True)
    sm = ob.modifiers.new('sm', 'LAPLACIANSMOOTH'); sm.iterations = 3; sm.lambda_factor = 0.6; sm.lambda_border = 0.0; sm.use_volume_preserve = True
    bpy.ops.object.modifier_apply(modifier='sm')
    dec = ob.modifiers.new('dec', 'DECIMATE'); dec.decimate_type = 'COLLAPSE'
    ntri = len(q2) * 2
    dec.ratio = min(1.0, hp['target_tris'] / ntri)
    bpy.ops.object.modifier_apply(modifier='dec')
    # tidy up after the decimation: no zero-area faces, no doubled vertices, no loose bits
    bm = bmesh.new(); bm.from_mesh(ob.data)
    bmesh.ops.dissolve_degenerate(bm, dist=2e-5, edges=bm.edges[:])
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=2e-5)
    loose = [v for v in bm.verts if not v.link_faces]
    if loose: bmesh.ops.delete(bm, geom=loose, context='VERTS')
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.to_mesh(ob.data); bm.free(); ob.data.update()
    hv2, ht2 = to_np(ob)
    print('hair', len(hv2), len(ht2), '%.1fs' % (time.time() - t0))
    return hv2, ht2

if __name__ == '__main__':
    if script_args()[:1] == ['mask']:
        dv, polys, m = build(debug_mask=True)
        np.savez(os.path.join(HERE, 'out', 'hairmask.npz'), v=dv, q=polys, m=m)
    else:
        v, t = build()
        P = np.load(os.path.join(HERE, 'out', 'figure.npz'))['P']
        V, G = load_base(); E = eye_mid(P, G)
        bm, _ = hairline_m(P, HP, E); bm[P[:, 1] < E[1] - 0.12] = -1.0
        np.savez(os.path.join(HERE, 'out', 'hair.npz'), v=v, t=t, body_m=bm)
