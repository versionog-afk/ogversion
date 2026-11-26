"""Shared helpers for the NA2 figure build (numpy only, no Blender needed here)."""
import os, json
import numpy as np

S = 'work3d'  # run from the repository root
MH = S + '/ext/makehuman/makehuman/data'
HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = S + '/model'


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
