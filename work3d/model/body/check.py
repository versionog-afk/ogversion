"""Mesh hygiene report for a figure GLB (run with the Blender python: needs mathutils).
Usage: python check.py [path.glb]   (default: body.glb next to this file)
Reports per mesh: triangles, loose fragments, open borders, degenerate triangles, flipped shells;
and between meshes: real triangle/triangle intersections (Body x Pants, Pants x Shoes must be 0)."""
import os, sys, json, struct
import numpy as np
import bpy  # noqa: makes mathutils importable
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))

def read_glb(path):
    b = open(path, 'rb').read()
    jl = struct.unpack('<I', b[12:16])[0]; doc = json.loads(b[20:20 + jl]); bin0 = 20 + jl + 8
    def acc(i):
        a = doc['accessors'][i]; v = doc['bufferViews'][a['bufferView']]
        dt = {5126: np.float32, 5123: np.uint16, 5125: np.uint32, 5121: np.uint8}[a['componentType']]
        n = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}[a['type']]
        o = bin0 + v.get('byteOffset', 0) + a.get('byteOffset', 0)
        return np.frombuffer(b, dt, a['count'] * n, o).reshape(-1, n).astype(np.float64 if dt == np.float32 else np.int64)
    out = {}
    for node in doc['nodes']:
        if 'mesh' not in node: continue
        m = doc['meshes'][node['mesh']]; p = m['primitives'][0]
        out[m['name']] = dict(v=acc(p['attributes']['POSITION']), n=acc(p['attributes']['NORMAL']), t=acc(p['indices']).reshape(-1, 3),
                              material=doc['materials'][p['material']]['name'])
    return out

def weld(v, t, eps=1e-5):
    key = np.round(v / eps).astype(np.int64)
    _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    return v[first], inv.reshape(-1)[t]

def components(nv, t):
    parent = np.arange(nv)
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for a, b, c in t:
        ra, rb, rc = find(a), find(b), find(c)
        parent[rb] = ra; parent[rc] = find(ra)
    roots = np.array([find(i) for i in t[:, 0]])
    u, cnt = np.unique(roots, return_counts=True)
    return sorted(cnt.tolist(), reverse=True)

def report(path):
    M = read_glb(path); res = {'file': os.path.basename(path), 'meshes': {}, 'intersections': {}}
    bvh = {}
    for name, m in M.items():
        v, t = weld(m['v'], m['t'])
        e = np.concatenate([t[:, [0, 1]], t[:, [1, 2]], t[:, [2, 0]]]); es = np.sort(e, 1)
        u, cnt = np.unique(es, axis=0, return_counts=True)
        area = 0.5 * np.linalg.norm(np.cross(v[t[:, 1]] - v[t[:, 0]], v[t[:, 2]] - v[t[:, 0]]), axis=1)
        # stored normals against geometric normals (flipped faces)
        fn = np.cross(m['v'][m['t'][:, 1]] - m['v'][m['t'][:, 0]], m['v'][m['t'][:, 2]] - m['v'][m['t'][:, 0]])
        sn = m['n'][m['t']].mean(1)
        flipped = int(((fn * sn).sum(1) < 0).sum())
        comps = components(len(v), t)
        res['meshes'][name] = dict(material=m['material'], tris=len(t), verts=len(m['v']), components=comps[:6], fragments=int(sum(1 for c in comps if c < 40)),
                                   border_edges=int((cnt == 1).sum()), nonmanifold_edges=int((cnt > 2).sum()), degenerate=int((area < 1e-12).sum()),
                                   normals_against_winding=flipped, bbox=[np.round(m['v'].min(0), 4).tolist(), np.round(m['v'].max(0), 4).tolist()])
        bvh[name] = BVHTree.FromPolygons([tuple(x) for x in m['v']], [tuple(int(i) for i in f) for f in m['t']], epsilon=0.0)
        # self-intersections: overlapping triangle pairs that share no (welded) vertex
        wb = BVHTree.FromPolygons([tuple(x) for x in v], [tuple(int(i) for i in f) for f in t], epsilon=0.0)
        so = [(a, b) for a, b in wb.overlap(wb) if a < b and not (set(t[a].tolist()) & set(t[b].tolist()))]
        res['meshes'][name]['self_intersections'] = len(so)
        if so:
            c = v[t[[a for a, _ in so]]].mean(1)
            res['meshes'][name]['self_intersections_bbox'] = [np.round(c.min(0), 3).tolist(), np.round(c.max(0), 3).tolist()]
    names = list(M)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            ov = bvh[names[i]].overlap(bvh[names[j]])
            if ov:
                ta = M[names[i]]['t'][[a for a, _ in ov]]; c = M[names[i]]['v'][ta].mean(1)
                res['intersections'][names[i] + ' x ' + names[j]] = dict(pairs=len(ov), y_range=[round(float(c[:, 1].min()), 3), round(float(c[:, 1].max()), 3)])
    return res

if __name__ == '__main__':
    a = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else ([] if any(x in ('--python', '-P', '-b', '--background') for x in sys.argv[1:]) else sys.argv[1:])
    path = a[0] if a else os.path.join(HERE, 'body.glb')
    r = report(path)
    for k, v in r['meshes'].items(): print('%-10s' % k, json.dumps(v))
    print('intersections', json.dumps(r['intersections']))
    json.dump(r, open(os.path.join(HERE, 'out', 'check.json'), 'w'), indent=1)
