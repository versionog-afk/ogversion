"""Cloth mesh from the sewing pattern: every panel of pattern.json is triangulated (boundary sampled at the mesh edge length,
identical sampling on both sides of a seam; hexagonal lattice inside; constrained Delaunay), the seams become pairs of
vertices, and the garment is arranged in its flat-lay (all seams closed, front and back layers a few millimetres apart).
Needs Blender's Python (mathutils).   <bpy python> mesh.py [spec.json]   ->  out/<name>/mesh.npz"""
import os, sys, json, math
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from na2cfg import *
import teegeom as tg
import bpy  # noqa: F401  (makes mathutils importable)
from mathutils import geometry, Vector


def edge_points(pn, e, n):
    """n + 1 points on a panel edge, uniform in arc length"""
    v = np.array(pn['vertices']); a, b = v[e['v'][0]], v[e['v'][1]]
    dense = tg.bez(a, e['bezier'][0], e['bezier'][1], b, 600) if 'bezier' in e else np.array([a, b])
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(dense, axis=0), axis=1))]
    s = np.linspace(0, d[-1], n + 1)
    p = np.c_[np.interp(s, d, dense[:, 0]), np.interp(s, d, dense[:, 1])]; p[0], p[-1] = a, b
    return p, float(d[-1])


def in_poly(P, poly):
    x, y = P[:, 0], P[:, 1]; inside = np.zeros(len(P), bool); n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]; x2, y2 = poly[(i + 1) % n]
        inside ^= ((y1 > y) != (y2 > y)) & (x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-30) + x1)
    return inside


def seg_dist(P, A, B):
    """distance of points P (n,2) to the segments A[i] -> B[i]"""
    out = np.full(len(P), 1e9); AB = B - A; L2 = np.maximum((AB ** 2).sum(1), 1e-18)
    step = max(1, int(3e6 // max(1, len(A))))
    for s in range(0, len(P), step):
        p = P[s:s + step, None, :]
        t = np.clip(((p - A[None]) * AB[None]).sum(2) / L2[None], 0, 1)
        out[s:s + step] = np.linalg.norm(p - (A[None] + t[..., None] * AB[None]), axis=2).min(1)
    return out


def cdt(pts, cons):
    v, e, f, ov, oe, of = geometry.delaunay_2d_cdt([Vector(p) for p in pts], [tuple(map(int, c)) for c in cons], [], 1, 1e-8, True)
    if len(v) != len(pts): raise RuntimeError('triangulation added or merged vertices (%d -> %d)' % (len(pts), len(v)))
    remap = np.array([o[0] for o in ov]); tris = remap[np.array(f, int)]
    a = pts[tris[:, 1]] - pts[tris[:, 0]]; b = pts[tris[:, 2]] - pts[tris[:, 0]]
    flip = (a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0]) < 0; tris[flip] = tris[flip][:, ::-1]
    return tris


def mesh_panel(loop, h, relax=5):
    """loop: boundary points in order (closed). Returns points (boundary first, same order) and CCW triangles."""
    nb = len(loop); cons = np.c_[np.arange(nb), (np.arange(nb) + 1) % nb]
    lo, hi = loop.min(0), loop.max(0); dy = h * math.sqrt(3) / 2
    lat = []
    for j, y in enumerate(np.arange(lo[1] + dy * 0.5, hi[1], dy)):
        xs = np.arange(lo[0] + (0.5 * h if j % 2 else 0.0) - h, hi[0] + h, h)
        lat.append(np.c_[xs, np.full(len(xs), y)])
    lat = np.concatenate(lat); lat = lat[in_poly(lat, loop)]
    lat = lat[seg_dist(lat, loop, np.roll(loop, -1, 0)) > 0.6 * h]
    pts = np.concatenate([loop, lat]); tris = cdt(pts, cons)
    for _ in range(relax):
        acc = np.zeros((len(pts), 2)); cnt = np.zeros(len(pts))
        for a, b in ((0, 1), (1, 2), (2, 0)):
            np.add.at(acc, tris[:, a], pts[tris[:, b]]); np.add.at(cnt, tris[:, a], 1)
            np.add.at(acc, tris[:, b], pts[tris[:, a]]); np.add.at(cnt, tris[:, b], 1)
        new = acc / np.maximum(cnt, 1)[:, None]
        pts[nb:] = 0.5 * pts[nb:] + 0.5 * new[nb:]
        tris = cdt(pts, cons)
    return pts, tris


def build(M, pat, h):
    P = pat['panels']; names = [n for n in P if P[n]['role'] != 'collar']
    FL = pat['flat_lay']; S, ds, dh = np.array(FL['S']), np.array(FL['ds']), np.array(FL['dh'])
    # number of segments per edge: the same on both sides of a seam
    nseg = {}
    for s in pat['seams']:
        if P[s['a']['panel']]['role'] == 'collar': continue
        n = max(2, int(round(0.5 * (s['length_a'] + s['length_b']) / h)))
        nseg[(s['a']['panel'], s['a']['edge'])] = n; nseg[(s['b']['panel'], s['b']['edge'])] = n
    panels = {}; off = 0
    for name in names:
        pn = P[name]; loop = []; eidx = []
        for i, e in enumerate(pn['edges']):
            n = nseg.get((name, i))
            if n is None:
                n = max(2, int(round(edge_points(pn, e, 2)[1] / (h * 0.9))))        # free edges (hems, neckline) a little denser
            pts, ln = edge_points(pn, e, n)
            start = len(loop); loop += [p for p in pts[:-1]]; eidx.append((start, n))
        loop = np.array(loop); nb = len(loop)
        pts, tris = mesh_panel(loop, h)
        edges = {i: [(st + k) % nb for k in range(n + 1)] for i, (st, n) in enumerate(eidx)}
        panels[name] = dict(pts=pts, tris=tris, edges=edges, off=off, nb=nb); off += len(pts)
    n = off
    pat2 = np.zeros((n, 2)); pid = np.zeros(n, int); flat = np.zeros((n, 2)); layer = np.zeros(n); tris = []; bnd = np.zeros(n, bool)
    for k, name in enumerate(names):
        d = panels[name]; o = d['off']; m = len(d['pts']); p = d['pts']
        pat2[o:o + m] = p; pid[o:o + m] = k; bnd[o:o + d['nb']] = True
        role = P[name]['role']
        if role == 'sleeve':
            pp, q = -p[:, 1], p[:, 0]
            X = S[None] + pp[:, None] * ds[None] + np.abs(q)[:, None] * dh[None]
            if P[name].get('side') == 'R': X[:, 0] *= -1
            flat[o:o + m] = X; layer[o:o + m] = np.sign(np.where(np.abs(q) < 1e-9, 0, q))
        else:
            flat[o:o + m] = p; layer[o:o + m] = 1.0 if role == 'front' else -1.0
        tris.append(d['tris'] + o)
    tris = np.concatenate(tris)
    # seams -> vertex pairs
    sew = []; seam_of = {}
    for s in pat['seams']:
        if P[s['a']['panel']]['role'] == 'collar': continue
        A = [panels[s['a']['panel']]['off'] + i for i in panels[s['a']['panel']]['edges'][s['a']['edge']]]
        B = [panels[s['b']['panel']]['off'] + i for i in panels[s['b']['panel']]['edges'][s['b']['edge']]]
        if s['reversed']: B = B[::-1]
        if len(A) != len(B): raise SystemExit('seam %s: %d / %d vertices' % (s['name'], len(A), len(B)))
        gap = np.linalg.norm(flat[A] - flat[B], axis=1).max()
        if gap > 1e-4: raise SystemExit('seam %s is open in the flat-lay by %.4f m' % (s['name'], gap))
        for a, b in zip(A, B):
            if a != b: sew.append((min(a, b), max(a, b)))
        seam_of[s['name']] = [A, B]
    sew = np.array(sorted(set(sew)))
    # named open edges
    named = {}
    for name in names:
        d = panels[name]
        for i, e in enumerate(P[name]['edges']):
            named['%s.%s' % (name, e['label'])] = [d['off'] + j for j in d['edges'][i]]
    return dict(names=names, pat=pat2, pid=pid, flat=flat, layer=layer, tris=tris, sew=sew, bnd=bnd, named=named, seam_of=seam_of)


def arrange(G, M, pat, St):
    """flat-lay in the figure's frame (metres, y up, +z front): x = flat x, y = flat y (hem at 0), z = +-gap; the gap closes at the seams"""
    D = tg.design(M); mir = np.array([-1.0, 1.0])
    A = [np.array([D['Wh'], 0.0]), D['U'], D['T'], D['S']]; B = [D['U'], D['H'], D['S'], D['N']]
    q = np.c_[np.abs(G['flat'][:, 0]), G['flat'][:, 1]]
    dist = seg_dist(q, np.array(A), np.array(B))
    w = np.clip(dist / St['layer_ramp'], 0, 1) ** 0.7
    z = G['layer'] * (St['layer_gap_min'] + (St['layer_gap'] - St['layer_gap_min']) * w)
    return np.c_[G['flat'][:, 0], G['flat'][:, 1], z]


def main():
    M = load_spec(); out = out_dir(M)
    Sg = json.load(open(os.path.join(HERE, 'settings.json')))
    h = float(os.environ.get('NA2_MESH_EDGE') or Sg['mesh_edge'])
    pat = json.load(open(os.path.join(out, 'pattern.json')))
    G = build(M, pat, h)
    X0 = arrange(G, M, pat, Sg['sim'])
    # triangle winding: outside of the garment = +z on the front layer, -z on the back layer
    tris = G['tris']; n = np.cross(X0[tris[:, 1]] - X0[tris[:, 0]], X0[tris[:, 2]] - X0[tris[:, 0]])[:, 2]
    lay = G['layer'][tris].sum(1)
    for k in range(len(G['names'])):
        m = G['pid'][tris[:, 0]] == k
        if (n[m] * lay[m]).sum() < 0: tris[m] = tris[m][:, ::-1]
    n = np.cross(X0[tris[:, 1]] - X0[tris[:, 0]], X0[tris[:, 2]] - X0[tris[:, 0]])[:, 2]
    bad = int(((n * lay) < 0).sum())
    # rest shape: every panel flat, panels stacked 1 m apart (only lengths and angles inside a panel matter)
    rest = np.c_[G['pat'][:, 0], G['pat'][:, 1], 1.0 * G['pid']]
    p = G['pat']; a = p[tris[:, 1]] - p[tris[:, 0]]; b = p[tris[:, 2]] - p[tris[:, 0]]
    area = 0.5 * np.abs(a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0])
    e = np.concatenate([np.linalg.norm(p[tris[:, i]] - p[tris[:, (i + 1) % 3]], axis=1) for i in range(3)])
    np.savez_compressed(os.path.join(out, 'mesh.npz'), X0=X0, rest=rest, pat=G['pat'], pid=G['pid'], flat=G['flat'], layer=G['layer'], tris=tris,
                        sew=G['sew'], bnd=G['bnd'], h=h, names=np.array(G['names']))
    json.dump(dict(named=G['named'], seams=G['seam_of']), open(os.path.join(out, 'mesh_edges.json'), 'w'))
    log('mesh: %d vertices, %d triangles, %d sewing pairs, edge %.1f mm (min %.1f, mean %.1f, max %.1f), cloth area %.3f m2, min triangle area %.1f mm2, wrongly wound %d'
        % (len(p), len(tris), len(G['sew']), h * 1000, e.min() * 1000, e.mean() * 1000, e.max() * 1000, area.sum(), area.min() * 1e6, bad))
    for k, nme in enumerate(G['names']):
        m = G['pid'][tris[:, 0]] == k
        log('  %-9s %6d verts %6d tris  area %.4f m2' % (nme, int((G['pid'] == k).sum()), int(m.sum()), area[m].sum()))


if __name__ == '__main__':
    main()
