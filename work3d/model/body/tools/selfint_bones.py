"""Which bones own the self-intersecting triangles of the posed body (out/figure.npz)? Blender python."""
import sys, os, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common import *
import bpy
from mathutils.bvhtree import BVHTree
d = np.load(os.path.join(HERE, 'out', 'figure.npz')); P = d['P']
V, G = load_base(); W = load_weights(len(V))
q = G['body']; t = quads_to_tris(q)
names = list(W); dom = np.zeros(len(V), int); best = np.zeros(len(V))
for k, b in enumerate(names):
    i, x = W[b]; m = x > best[i]; dom[i[m]] = k; best[i[m]] = x[m]
wb = BVHTree.FromPolygons([tuple(x) for x in P], [tuple(int(i) for i in f) for f in t], epsilon=0.0)
so = [(a, b) for a, b in wb.overlap(wb) if a < b and not (set(t[a].tolist()) & set(t[b].tolist()))]
lo, hi = float(sys.argv[1]), float(sys.argv[2])
for a, b in so:
    c = P[t[a]].mean(0)
    if lo < c[1] < hi and c[0] > 0:
        print(np.round(c, 3), sorted(set(names[k] for k in dom[t[a]])), 'x', sorted(set(names[k] for k in dom[t[b]])))
