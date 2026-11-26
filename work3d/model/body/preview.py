import numpy as np, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from glbw import GLB, angle_weighted_normals
d = np.load(HERE + '/out/figure.npz'); P = d['P']
V, G = load_base()
g = GLB()
ms = g.add_material({"name": "Skin", "pbrMetallicRoughness": {"baseColorFactor": [0.84, 0.81, 0.76, 1], "metallicFactor": 0, "roughnessFactor": 0.62}})
mh = g.add_material({"name": "Hair", "pbrMetallicRoughness": {"baseColorFactor": [0.1, 0.1, 0.1, 1], "metallicFactor": 0, "roughnessFactor": 0.7}})
q = np.concatenate([G['body'], G['helper-l-eye'], G['helper-r-eye']])
v, f, _ = compact(P, q); t = quads_to_tris(f)
g.add_mesh('Body', ms, v, angle_weighted_normals(v, t), t)
h = np.load(HERE + '/out/hair.npz')
g.add_mesh('Hair', mh, h['v'], angle_weighted_normals(h['v'], h['t']), h['t'])
g.write(HERE + '/out/preview.glb')
