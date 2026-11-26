"""Write a GLB with only some of the figure meshes (inspection). Usage: python3 tools/subset.py out.glb Body Pants ..."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common import *
import assemble as A
from glbw import GLB
meshes, L, full, pants = A.figure_meshes()
g = GLB(); mats = {'Body': ('Skin', [0.84, 0.81, 0.76, 1], 0.62, False), 'Hair': ('Hair', [0.027, 0.022, 0.018, 1], 0.7, False),
                   'Pants': ('Pants', [0.035, 0.034, 0.03, 1], 0.9, True), 'Shoes': ('Shoes', [0.006, 0.006, 0.007, 1], 0.55, False)}
for name in script_args()[1:]:
    mn, col, r, ds = mats[name]; v, n, t = meshes[name]
    g.add_mesh(name, A.mat(g, mn, col, r, ds=ds), v, n, t)
g.write(script_args()[0])
