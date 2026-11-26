"""Shared helpers for the NA2 figure build (numpy only, no Blender needed here)."""
import os, json
import numpy as np

# ---------------------------------------------------------------------------------------------------------------
# ROOT: the only machine-specific path of the Python scripts. It is the folder that holds
#   ext/makehuman/   (a checkout of the MakeHuman repository: CC0 base mesh, targets, rig)   and   na2/   (this project).
# Change it here, or set the environment variable NA2_ROOT (build.sh does that for every step).
ROOT = os.environ.get('NA2_ROOT') or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '_root'))  # see ../README.md
# ---------------------------------------------------------------------------------------------------------------
S = ROOT
MH = os.environ.get('NA2_MAKEHUMAN') or (ROOT + '/ext/makehuman/makehuman/data')
HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = os.path.dirname(HERE)


def script_args():
    """command line arguments of the script, also when it is run as  blender --background --python script.py -- args"""
    import sys
    a = sys.argv
    if '--' in a: return a[a.index('--') + 1:]
    if any(x in ('--python', '-P', '--background', '-b') for x in a[1:]): return []
    return a[1:]


def load_base():
    """returns verts (N,3) in decimetres, dict group -> list of quads (0-based), uv not needed"""
    vs = []; groups = {}; cur = None
    for l in open(MH + '/3dobjs/base.obj'):
        if l.startswith('v '):
            vs.append([float(x) for x in l.split()[1:4]])
        elif l.startswith('g '):
            cur = l.split()[1]; groups.setdefault(cur, [])
        elif l.startswith('f '):
            groups[cur].append([int(t.split('/')[0]) - 1 for t in l.split()[1:]])
    return np.array(vs, dtype=np.float64), {k: np.array(v, dtype=np.int64) for k, v in groups.items() if len(v)}


def load_target(path, n):
    d = np.zeros((n, 3))
    full = path if os.path.isabs(path) else MH + '/targets/' + path
    for l in open(full):
        if l.startswith('#') or not l.strip():
            continue
        p = l.split()
        d[int(p[0])] = [float(p[1]), float(p[2]), float(p[3])]
    return d


def load_weights(n):
    d = json.load(open(MH + '/rigs/default_weights.mhw'))['weights']
    return {b: (np.array([x[0] for x in w], dtype=np.int64), np.array([x[1] for x in w])) for b, w in d.items()}


def quads_to_tris(q):
    q = np.asarray(q)
    return np.concatenate([q[:, [0, 1, 2]], q[:, [0, 2, 3]]], axis=0)


def compact(verts, faces):
    """drop unused vertices; returns new verts, faces, old index map"""
    used = np.unique(faces)
    remap = -np.ones(len(verts), dtype=np.int64); remap[used] = np.arange(len(used))
    return verts[used], remap[faces], used


def write_obj(path, verts, faces, name='mesh'):
    with open(path, 'w') as f:
        f.write('o %s\n' % name)
        for v in verts:
            f.write('v %.6f %.6f %.6f\n' % tuple(v))
        for q in faces:
            f.write('f ' + ' '.join(str(int(i) + 1) for i in q) + '\n')


def tri_normals(v, t):
    n = np.cross(v[t[:, 1]] - v[t[:, 0]], v[t[:, 2]] - v[t[:, 0]])
    return n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-20)


def autosmooth(v, t, angle_deg=50.0):
    """split vertices where adjacent faces meet at more than angle_deg; returns new verts, tris, normals (angle weighted)"""
    t = np.asarray(t); fn = tri_normals(v, t); cosr = np.cos(np.radians(angle_deg))
    nf = len(t)
    # corner id = 3 * face + k ; union corners of the same vertex across smooth edges
    parent = np.arange(3 * nf)
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    edge = {}
    for f in range(nf):
        for k in range(3):
            a, b = int(t[f, k]), int(t[f, (k + 1) % 3])
            key = (min(a, b), max(a, b))
            edge.setdefault(key, []).append((f, k))
    for key, lst in edge.items():
        if len(lst) != 2: continue
        (f1, k1), (f2, k2) = lst
        if fn[f1] @ fn[f2] < cosr: continue
        for vv in key:
            c1 = 3 * f1 + [k for k in range(3) if t[f1, k] == vv][0]
            c2 = 3 * f2 + [k for k in range(3) if t[f2, k] == vv][0]
            r1, r2 = find(c1), find(c2)
            if r1 != r2: parent[r1] = r2
    roots = np.array([find(i) for i in range(3 * nf)])
    uniq, inv = np.unique(roots, return_inverse=True)
    nt = inv.reshape(nf, 3)
    nv = np.zeros((len(uniq), 3)); nv[nt.reshape(-1)] = v[t.reshape(-1)]
    nn = np.zeros_like(nv)
    for k in range(3):
        a = nv[nt[:, (k + 1) % 3]] - nv[nt[:, k]]; b = nv[nt[:, (k + 2) % 3]] - nv[nt[:, k]]
        a /= np.maximum(np.linalg.norm(a, axis=1, keepdims=True), 1e-20); b /= np.maximum(np.linalg.norm(b, axis=1, keepdims=True), 1e-20)
        ang = np.arccos(np.clip((a * b).sum(1), -1, 1))
        np.add.at(nn, nt[:, k], fn * ang[:, None])
    nn /= np.maximum(np.linalg.norm(nn, axis=1, keepdims=True), 1e-20)
    return nv, nt, nn


def uv_sphere(c, r, nu=16, nv=10):
    vs = []; q = []
    for j in range(nv + 1):
        ph = np.pi * j / nv
        for i in range(nu):
            th = 2 * np.pi * i / nu
            vs.append([c[0] + r * np.sin(ph) * np.cos(th), c[1] + r * np.cos(ph), c[2] + r * np.sin(ph) * np.sin(th)])
    t = []
    for j in range(nv):
        for i in range(nu):
            a = j * nu + i; b = j * nu + (i + 1) % nu; cc = (j + 1) * nu + (i + 1) % nu; d = (j + 1) * nu + i
            if j > 0: t.append([a, b, cc])
            if j < nv - 1: t.append([a, cc, d])
    vs = np.array(vs); t = np.array(t)
    n = tri_normals(vs, t); cen = vs[t].mean(1) - np.asarray(c)
    if (n * cen).sum() < 0: t = t[:, ::-1]
    return vs, t


def clip_tris(v, n, tris, h):
    """cut a triangle mesh along the zero level of the per-vertex field h and keep the part with h < 0.
    New vertices are created on the crossed edges (shared between neighbours), so the border is a clean curve.
    returns verts, normals, tris"""
    v = np.asarray(v); n = np.asarray(n); tris = np.asarray(tris); h = np.asarray(h, float)
    keep = h < 0
    k = keep[tris]; cnt = k.sum(1)
    out_t = [tris[cnt == 3]]
    new_v = []; new_n = []; cache = {}; base = len(v)
    def cut(a, b):          # a kept, b hidden
        key = (a, b)
        if key not in cache:
            t = h[a] / (h[a] - h[b]); t = min(max(t, 0.02), 0.98)
            cache[key] = base + len(new_v)
            new_v.append(v[a] + t * (v[b] - v[a])); nn = n[a] + t * (n[b] - n[a]); new_n.append(nn / max(np.linalg.norm(nn), 1e-20))
        return cache[key]
    extra = []
    for tri, kk in zip(tris[(cnt == 1) | (cnt == 2)], k[(cnt == 1) | (cnt == 2)]):
        tri = [int(x) for x in tri]
        if kk.sum() == 1:
            i = int(np.argmax(kk)); a, b, c = tri[i], tri[(i + 1) % 3], tri[(i + 2) % 3]
            extra.append([a, cut(a, b), cut(a, c)])
        else:
            i = int(np.argmin(kk)); c, a, b = tri[i], tri[(i + 1) % 3], tri[(i + 2) % 3]       # c hidden, a and b kept (order a, b, c keeps the winding)
            ac = cut(a, c); bc = cut(b, c)
            extra.append([a, b, bc]); extra.append([a, bc, ac])
    allv = np.concatenate([v, np.array(new_v).reshape(-1, 3)]); alln = np.concatenate([n, np.array(new_n).reshape(-1, 3)])
    allt = np.concatenate([out_t[0], np.array(extra, dtype=np.int64).reshape(-1, 3)])
    vv, tt, used = compact(allv, allt)
    return vv, alln[used], tt
