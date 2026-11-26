"""Inspection file: the uncut body with a dark ball on every landmark -> out/landmarks_debug.glb (system python)."""
import os, sys, json
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common import *
from glbw import GLB, angle_weighted_normals
import assemble as A
L = json.load(open(HERE + '/landmarks.json'))
meshes, _, full, _ = A.figure_meshes()
g = GLB(); ms = A.mat(g, 'Skin', [0.84, 0.81, 0.76, 1], 0.62); mm = A.mat(g, 'Shoes', [0.01, 0.01, 0.01, 1], 0.5)
v, f, used = compact(full['P'], full['q']); g.add_mesh('Body', ms, v, full['N'][used], quads_to_tris(f))
pts = []
for k, val in L.items():
    if isinstance(val, list) and len(val) == 3 and not isinstance(val[0], list): pts.append(val)
for k in ('chest_front', 'upper_back'): pts.append(L[k]['point'])
nb = L['neck_base']; pts += [nb['center'], nb['front'], nb['back']]
w = L['waist']; pts += [[w['half_width'], w['y'], 0], [-w['half_width'], w['y'], 0], [0, w['y'], w['z_front']], [0, w['y'], w['z_back']]]
h = L['hip']; pts += [[h['width'] / 2, h['y'], 0], [-h['width'] / 2, h['y'], 0], [0, h['y'], h['z_front']], [0, h['y'], h['z_back']]]
pts.append([0, L['crotch_height'], 0.0]); pts.append([0, L['seat_back']['y'], L['seat_back']['z']])
pts += L['shoulder_line_L'][::3]
vs = []; ts = []; off = 0
for p in pts:
    sv, st = uv_sphere(np.array(p, float), 0.006, 10, 6); vs.append(sv); ts.append(st + off); off += len(sv)
vs = np.concatenate(vs); ts = np.concatenate(ts)
g.add_mesh('Shoes_markers', mm, vs, angle_weighted_normals(vs, ts), ts)
g.write(HERE + '/out/landmarks_debug.glb'); print(len(pts), 'markers')
