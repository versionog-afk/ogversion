"""Is the skin visible through the trousers? Casts a grid of rays from the side and reports rays that reach the body first.
Usage: python tools/raytest.py [file.glb]  (Blender python)"""
import sys, os, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import check
from mathutils.bvhtree import BVHTree
from mathutils import Vector
M = check.read_glb(sys.argv[1] if len(sys.argv) > 1 else os.path.join(check.HERE, 'body.glb'))
bv = {k: BVHTree.FromPolygons([tuple(x) for x in m['v']], [tuple(int(i) for i in f) for f in m['t']], epsilon=0.0) for k, m in M.items()}
bad = []
for yaw in (90, 35, 215, 0, 180):
    a = np.radians(yaw); cam = np.array([np.sin(a) * 4.2, 0.84, np.cos(a) * 4.2]); right = np.array([np.cos(a), 0, -np.sin(a)])
    n = 0; nb = 0
    for y in np.arange(0.10, 0.295, 0.0015):
        for s in np.arange(-0.25, 0.25, 0.0015):
            tgt = np.array([0, y, 0]) + right * s; d = tgt - cam; d /= np.linalg.norm(d)
            hp = bv['Pants'].ray_cast(Vector(cam), Vector(d)); hb = bv['Body'].ray_cast(Vector(cam), Vector(d))
            if hb[0] is None: continue
            n += 1
            if hp[0] is None or hb[3] < hp[3] - 1e-6:
                nb += 1; bad.append((yaw, np.round(np.array(hb[0]), 4).tolist(), None if hp[0] is None else round(hp[3] - hb[3], 4)))
    print('yaw', yaw, 'rays that meet the shins', n, 'skin in front of the cloth', nb)
for b in bad[:12]: print(b)
