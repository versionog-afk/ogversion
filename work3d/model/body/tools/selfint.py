"""Where does a mesh of a GLB intersect itself? Usage: python tools/selfint.py file.glb [MeshName]  (Blender python)"""
import sys, os, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import check
from mathutils.bvhtree import BVHTree
M = check.read_glb(sys.argv[1]); name = sys.argv[2] if len(sys.argv) > 2 else 'Body'
v, t = check.weld(M[name]['v'], M[name]['t'])
wb = BVHTree.FromPolygons([tuple(x) for x in v], [tuple(int(i) for i in f) for f in t], epsilon=0.0)
so = [(a, b) for a, b in wb.overlap(wb) if a < b and not (set(t[a].tolist()) & set(t[b].tolist()))]
c = v[t[[a for a, _ in so]]].mean(1) if so else np.zeros((0, 3))
regions = {'toes/feet (y<0.1)': c[:, 1] < 0.1, 'hands (|x|>0.2, y<1.0)': (np.abs(c[:, 0]) > 0.2) & (c[:, 1] < 1.0) & (c[:, 1] > 0.1),
           'head (y>1.45)': c[:, 1] > 1.45, 'armpit/torso': (c[:, 1] > 1.0) & (c[:, 1] <= 1.45), 'legs/crotch': (c[:, 1] >= 0.1) & (c[:, 1] <= 1.0) & (np.abs(c[:, 0]) <= 0.2)}
for k, m in regions.items():
    print('%-26s %5d' % (k, m.sum()), (np.round(c[m].min(0), 3).tolist(), np.round(c[m].max(0), 3).tolist()) if m.any() else '')
