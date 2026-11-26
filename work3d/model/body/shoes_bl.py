"""Shoes: plain low shoes grown around the posed feet (blurred signed distance field, surface nets, decimate).
Run with the Blender python."""
import os, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
import bpy
from mathutils.bvhtree import BVHTree
from hair_bl import surface_nets, mesh_obj, to_np, smin, smax, smoothstep

SP = dict(h=0.002, offset=0.0065, blur=3, collar=0.086, collar_slope=0.10, sole=0.021, welt=0.0035, target_tris=2800)

def box_blur(f, r, passes=3):
    for _ in range(passes):
        for ax in range(3):
            c = np.cumsum(np.concatenate([np.repeat(np.take(f, [0], ax), r + 1, ax), f, np.repeat(np.take(f, [-1], ax), r, ax)], ax), ax)
            n = f.shape[ax]
            hi = np.take(c, np.arange(2 * r + 1, 2 * r + 1 + n), ax); lo = np.take(c, np.arange(0, n), ax)
            f = (hi - lo) / (2 * r + 1)
    return f

def build(sp=SP):
    t0 = time.time()
    d = np.load(os.path.join(HERE, 'out', 'figure.npz')); P = d['P']
    V, G = load_base(); q = G['body']
    keep = ((P[q][:, :, 1] < 0.32) & (P[q][:, :, 0] > 0)).all(1)
    fv, fq, _ = compact(P, q[keep])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    foot = mesh_obj('foot', fv, fq)
    mod = foot.modifiers.new('ss', 'SUBSURF'); mod.levels = 1
    dg = bpy.context.evaluated_depsgraph_get(); me = bpy.data.meshes.new_from_object(foot.evaluated_get(dg))
    dv = np.zeros(len(me.vertices) * 3); me.vertices.foreach_get('co', dv); dv = dv.reshape(-1, 3)
    polys = [tuple(p.vertices) for p in me.polygons]
    bvh = BVHTree.FromPolygons([tuple(x) for x in dv], polys)
    low = fv[fv[:, 1] < 0.10]
    lo = np.array([low[:, 0].min() - 0.03, -0.008, low[:, 2].min() - 0.03]); hi = np.array([low[:, 0].max() + 0.03, 0.125, low[:, 2].max() + 0.03])
    h = sp['h']; n = np.ceil((hi - lo) / h).astype(int) + 1
    gx, gy, gz = [lo[i] + np.arange(n[i]) * h for i in range(3)]
    pts = np.stack(np.meshgrid(gx, gy, gz, indexing='ij'), -1).reshape(-1, 3)
    dist = np.full(len(pts), 0.04); fn = bvh.find_nearest
    for i in range(len(pts)):
        r = fn(pts[i], 0.04)
        if r[0] is not None:
            l, nr, _, dd = r; pp = pts[i]
            dist[i] = dd if (pp[0] - l[0]) * nr[0] + (pp[1] - l[1]) * nr[1] + (pp[2] - l[2]) * nr[2] >= 0 else -dd
    f = box_blur(dist.reshape(n), sp['blur'])
    X, Y, Z = np.meshgrid(gx, gy, gz, indexing='ij')
    upper = f - sp['offset']
    zmid = 0.5 * (low[:, 2].max() + low[:, 2].min())
    collar = sp['collar'] - sp['collar_slope'] * (Z - zmid) * 0.0 + 0.012 * smoothstep((zmid - 0.02 - Z) / 0.06)   # a little higher at the heel
    upper = np.maximum(upper, Y - collar)
    foot2d = upper.min(axis=1, keepdims=True)                 # footprint of the upper
    k = 0.005
    sole = smax(smax(np.broadcast_to(foot2d - sp['welt'], upper.shape), Y - sp['sole'], k), -Y - 0.0005, k)
    upper = np.maximum(upper, -Y)
    g = smin(upper, sole, 0.004)
    v, qd = surface_nets(g, lo, h)
    c0 = v.mean(0); tq = quads_to_tris(qd); nn = np.cross(v[tq[:, 1]] - v[tq[:, 0]], v[tq[:, 2]] - v[tq[:, 0]])
    if (nn * (v[tq].mean(1) - c0)).sum() < 0: qd = qd[:, ::-1]
    ob = mesh_obj('Shoe', v, qd)
    bpy.context.view_layer.objects.active = ob; ob.select_set(True)
    sm = ob.modifiers.new('sm', 'LAPLACIANSMOOTH'); sm.iterations = 6; sm.lambda_factor = 0.6; sm.use_volume_preserve = True
    bpy.ops.object.modifier_apply(modifier='sm')
    dec = ob.modifiers.new('dec', 'DECIMATE'); dec.ratio = min(1.0, sp['target_tris'] / (2 * len(qd)))
    bpy.ops.object.modifier_apply(modifier='dec')
    sv, st = to_np(ob)
    sv[:, 1] = np.maximum(sv[:, 1], 0.0)
    print('shoe', len(sv), len(st), 'bbox', sv.min(0).round(3), sv.max(0).round(3), '%.1fs' % (time.time() - t0))
    return sv, st

if __name__ == '__main__':
    v, t = build()
    v2 = v * [-1, 1, 1]; t2 = t[:, ::-1] + len(v)
    np.savez(os.path.join(HERE, 'out', 'shoes.npz'), v=np.concatenate([v, v2]), t=np.concatenate([t, t2]), collar=SP['collar'])
