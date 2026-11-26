"""Sew and drape: Blender cloth simulation of the flat-lay garment mesh on the figure of stage 1.

The garment starts lying flat with every seam closed (sewing springs of zero length); the figure starts paper-thin between the
front and the back layer with its arms along the flat-lay sleeves. It is inflated to its real depth, the arms come down to the
relaxed pose, and the cloth settles under gravity with collision against body and trousers and with self collision.
The rest shape of the cloth is the flat pattern (per panel), so nothing is pre-shaped.

    <bpy python> drape.py [spec.json]     ->  out/<name>/drape.npz        (NA2_FRAMES_SCALE=0.5 for a quick test)"""
import os, sys, json, math, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from na2cfg import *
import teegeom as tg
import mesh as meshmod
import bpy
from mathutils.bvhtree import BVHTree


def to_b(p):
    p = np.asarray(p); return np.stack([p[..., 0], -p[..., 2], p[..., 1]], -1)


def from_b(p):
    p = np.asarray(p); return np.stack([p[..., 0], p[..., 2], -p[..., 1]], -1)


def smooth(t):
    t = min(max(t, 0.0), 1.0); return t * t * t * (t * (t * 6 - 15) + 10)


def poly_dist(P2, pts):
    return meshmod.seg_dist(P2, pts[:-1], pts[1:])


def weights(M, G, E, fab):
    """per-vertex bending-stiffness multipliers (hems, seams, neckline, printed areas) and the neckline flag"""
    pat, pid, names = G['pat'], G['pid'], [str(x) for x in G['names']]
    n = len(pat); mult = np.ones(n); neck = np.zeros(n); hemd = np.full(n, 1e9); seamd = np.full(n, 1e9)
    sim = fab['sim']
    for key, idx in E['named'].items():
        panel, label = key.split('.'); k = names.index(panel); m = pid == k
        d = np.full(n, 1e9); d[m] = poly_dist(pat[m], pat[idx])
        if label == 'hem': hemd = np.minimum(hemd, d)
        elif label.startswith('neck'): neck = np.maximum(neck, np.clip(1 - d / 0.018, 0, 1))
        else: seamd = np.minimum(seamd, d)
    ha = max(M['body']['hem_allowance'], M['sleeve']['hem_allowance'])
    mult = np.maximum(mult, 1 + (sim['hem_stiff'] - 1) * np.clip(1.25 - hemd / ha, 0, 1))
    mult = np.maximum(mult, 1 + (sim['seam_stiff'] - 1) * np.clip(1 - seamd / 0.012, 0, 1))
    mult = np.maximum(mult, 1 + (sim.get('neck_stiff', 5.0) - 1) * neck)
    # printed areas: the ink film stiffens the cloth
    D = tg.design(M); L = D['L']
    for panel, pr in (('front', M['print_front']), ('back', M['print_back'])):
        k = names.index(panel); m = pid == k
        if panel == 'front':
            cx = pr['center_x']; cy = L - D['fd'] - pr['center_below_front_collar_seam']; hw, hh = pr['canvas_width'] * 0.44, pr['canvas_height'] * 0.5
        else:
            cx = -pr['center_x']; top = L - D['bd'] - pr['art_top_below_back_collar_seam']; hh = pr['canvas_height'] * 0.84 / 2; cy = top - hh; hw = pr['canvas_width'] * 0.485
        dx = np.abs(pat[:, 0] - cx) - hw; dy = np.abs(pat[:, 1] - cy) - hh
        inside = np.clip(1 - np.maximum(dx, dy) / 0.02, 0, 1) * m
        mult = np.maximum(mult, 1 + (sim['print_stiff'] - 1) * inside)
    return mult, neck, hemd, seamd


def main():
    M = load_spec(); out = out_dir(M); fab = M['_fabric']; sim = fab['sim']
    Sg = json.load(open(os.path.join(HERE, 'settings.json'))); St = Sg['sim']
    G = dict(np.load(os.path.join(out, 'mesh.npz'))); E = json.load(open(os.path.join(out, 'mesh_edges.json')))
    PZ = np.load(os.path.join(out, 'pose.npz'))
    h = float(G['h']); n = len(G['X0']); tris = G['tris']; sew = G['sew']
    fs = float(os.environ.get('NA2_FRAMES_SCALE', 1.0))
    FI, FA, FS = [max(4, int(round(St[k] * fs))) for k in ('frames_inflate', 'frames_arms', 'frames_settle')]
    total = FI + FA + FS
    keys = PZ['frames'].astype(np.float64); quads = PZ['quads']; pv, pt = PZ['pants_verts'].astype(np.float64), PZ['pants_tris']
    zmid = 0.5 * (keys[0][:, 2].max() + min(keys[0][:, 2].min(), pv[:, 2].min()))

    def body_at(f):
        """collision body (verts) and trousers at frame f"""
        ys = St['yscale0'] + (1 - St['yscale0']) * smooth((f - 1) / FI)
        u = smooth((f - FI) / FA) * (len(keys) - 1)
        i = min(int(u), len(keys) - 2); t = u - i
        b = (1 - t) * keys[i] + t * keys[i + 1]
        b = b.copy(); b[:, 2] = zmid + ys * (b[:, 2] - zmid)
        p = pv.copy(); p[:, 2] = zmid + ys * (p[:, 2] - zmid)
        return b, p, ys

    # ---- start height: the lowest position in which the flat garment clears the flat body ----
    b0, p0, _ = body_at(1)
    bvh = BVHTree.FromPolygons([tuple(v) for v in b0], [tuple(int(i) for i in q) for q in quads])
    X0 = G['X0'].copy(); X0[:, 2] += zmid
    L = M['body']['length_hps_to_hem']; LM = json.load(open(os.path.join(BODY, 'landmarks.json')))
    y_off = LM['side_neck_L'][1] - L - 0.03
    while True:
        # (the flat body is at most 2 cm thick, so a clearance test is enough: no cloth vertex can be deep inside it)
        Xs = X0 + np.array([0, y_off, 0]); dmin = 1e9
        for p in Xs:
            dmin = min(dmin, bvh.find_nearest(tuple(p))[3])
            if dmin <= St['start_clearance']: break
        if dmin > St['start_clearance']: break
        y_off += 0.003
        if y_off > LM['side_neck_L'][1] - L + 0.25: raise SystemExit('no collision free start position for the flat garment')
    X0 = X0 + np.array([0, y_off, 0])
    log('start: garment HPS at y = %.3f (side neck point of the body %.3f), clearance %.1f mm, frames %d + %d + %d' % (y_off + L, LM['side_neck_L'][1], dmin * 1000, FI, FA, FS))

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene; scene.frame_start = 1; scene.frame_end = total + 5

    def collider(name, verts, faces):
        me = bpy.data.meshes.new(name); me.from_pydata([tuple(v) for v in to_b(verts)], [], [tuple(int(i) for i in f) for f in faces]); me.update()
        ob = bpy.data.objects.new(name, me); scene.collection.objects.link(ob)
        ob.modifiers.new('Collision', 'COLLISION')
        ob.collision.thickness_outer = St['collider_outer']; ob.collision.thickness_inner = 0.02
        ob.collision.cloth_friction = St['collider_friction']; ob.collision.damping = 0.6
        return me
    mb = collider('Body', b0, quads); mp = collider('Pants', p0, pt)

    cm = bpy.data.meshes.new('Cloth')
    cm.from_pydata([tuple(v) for v in to_b(X0)], [tuple(int(i) for i in e) for e in sew], [tuple(int(i) for i in t) for t in tris]); cm.update()
    cloth = bpy.data.objects.new('Cloth', cm); scene.collection.objects.link(cloth)
    cloth.shape_key_add(name='Basis'); rest = cloth.shape_key_add(name='Rest')
    rest.data.foreach_set('co', np.ascontiguousarray(G['rest'], dtype=np.float32).ravel())
    # the simulation starts from the arranged shape (frame 1); from frame 2 on the animated base mesh is the flat pattern, which the
    # solver ("dynamic base mesh") uses for rest lengths and rest angles
    rest.value = 0.0; rest.keyframe_insert('value', frame=1); rest.value = 1.0; rest.keyframe_insert('value', frame=2)

    mult, neck, hemd, seamd = weights(M, G, E, fab)
    mmax = float(mult.max())
    vg_b = cloth.vertex_groups.new(name='bend'); vg_s = cloth.vertex_groups.new(name='struct'); vg_c = cloth.vertex_groups.new(name='selfcol')
    for i in np.nonzero(mult > 1.0)[0]: vg_b.add([int(i)], float((mult[i] - 1) / (mmax - 1)), 'REPLACE')
    for i in np.nonzero(neck > 0)[0]: vg_s.add([int(i)], float(neck[i]), 'REPLACE')
    vg_c.add(list(range(n)), 1.0, 'REPLACE')

    bending = float(os.environ.get('NA2_BENDING') or sim['bending'])
    cal = sim.get('bending_calibrated_at_edge')
    if cal and abs(cal - h) > 2e-4:
        bending *= (cal / h) ** 4.8
        log('bending stiffness rescaled from the calibration edge %.1f mm to %.1f mm: %.3f' % (cal * 1000, h * 1000, bending))
    md = cloth.modifiers.new('Cloth', 'CLOTH'); cs = md.settings; cc = md.collision_settings
    cs.quality = St['quality']; cs.mass = St['mass']
    cs.tension_stiffness = sim['tension']; cs.compression_stiffness = sim['compression']; cs.shear_stiffness = sim['shear']
    cs.bending_model = 'ANGULAR'; cs.bending_stiffness = bending
    cs.tension_damping = sim['tension_damping']; cs.compression_damping = sim['compression_damping']; cs.shear_damping = sim['shear_damping']
    cs.bending_damping = sim['bending_damping']; cs.air_damping = sim['air_damping']
    cs.use_sewing_springs = True; cs.sewing_force_max = 0.0
    cs.use_dynamic_mesh = True
    cs.vertex_group_bending = 'bend'; cs.bending_stiffness_max = bending * mmax
    cs.vertex_group_structural_stiffness = 'struct'
    cs.tension_stiffness_max = sim['tension'] * sim.get('neck_tension', 3.0); cs.compression_stiffness_max = sim['compression'] * sim.get('neck_tension', 3.0)
    cc.use_collision = True; cc.distance_min = sim['collision_distance']; cc.collision_quality = St['collision_quality']; cc.friction = sim['friction']
    cc.use_self_collision = bool(St['self_collision']); cc.self_distance_min = sim['self_distance']; cc.self_friction = sim['self_friction']
    cc.vertex_group_self_collisions = 'selfcol'
    md.point_cache.frame_start = 1; md.point_cache.frame_end = total + 5
    log('cloth: %d verts, edge %.1f mm, mass %.3f, tension %.1f, compression %.1f, shear %.1f, bending %.3f (x%.1f max), quality %d'
        % (n, h * 1000, cs.mass, cs.tension_stiffness, cs.compression_stiffness, cs.shear_stiffness, bending, mmax, cs.quality))

    def read():
        dg = bpy.context.evaluated_depsgraph_get(); ev = cloth.evaluated_get(dg)
        buf = np.empty(n * 3); ev.data.vertices.foreach_get('co', buf)
        return from_b(buf.reshape(n, 3))

    e_all = np.unique(np.sort(np.concatenate([tris[:, [0, 1]], tris[:, [1, 2]], tris[:, [2, 0]]]), axis=1), axis=0)
    r = G['rest']; el0 = np.linalg.norm(r[e_all[:, 0]] - r[e_all[:, 1]], axis=1)
    hem_idx = np.array(E['named']['front.hem'] + E['named']['back.hem'])
    scene.frame_set(1); prev = read(); t0 = time.time(); keep = {}
    for f in range(2, total + 1):
        b, p, ys = body_at(f)
        if f == total - St['frames_freeze']: cs.air_damping = St['air_damping_end']        # heavy drag at the very end calms the last jitter
        mb.vertices.foreach_set('co', np.ascontiguousarray(to_b(b), dtype=np.float32).ravel()); mb.update()
        if f <= FI + 1:
            mp.vertices.foreach_set('co', np.ascontiguousarray(to_b(p), dtype=np.float32).ravel()); mp.update()
        scene.frame_set(f)
        if f % 10 == 0 or f == total or f in (FI, FI + FA):
            X = read()
            if not np.isfinite(X).all(): raise SystemExit('simulation exploded at frame %d' % f)
            mv = np.linalg.norm(X - prev, axis=1); prev = X
            el = np.linalg.norm(X[e_all[:, 0]] - X[e_all[:, 1]], axis=1); strain = el / el0 - 1
            gap = np.linalg.norm(X[sew[:, 0]] - X[sew[:, 1]], axis=1)
            log('frame %3d/%d  %6.0fs  depth %.2f  move max %6.2f mm mean %5.2f mm  strain mean %+.2f%% p1 %+.2f%% p99 %+.2f%%  seam gap max %.2f mm  hem y %.3f..%.3f  top y %.3f'
                % (f, total, time.time() - t0, ys, mv.max() * 1000, mv.mean() * 1000, strain.mean() * 100, np.percentile(strain, 1) * 100, np.percentile(strain, 99) * 100,
                   gap.max() * 1000, X[hem_idx, 1].min(), X[hem_idx, 1].max(), X[:, 1].max()))
            if f in (FI, FI + FA): keep['f%d' % f] = X
    # the last frames are averaged (removes residual sub-millimetre collision jitter)
    acc = read().copy(); k = 1
    np.savez_compressed(os.path.join(out, 'drape.npz'), X=acc, X0=X0, mult=mult, neck=neck, hemd=hemd, seamd=seamd, bending=bending, **keep)
    log('drape saved: %s  (%.0f s)' % (os.path.join(out, 'drape.npz'), time.time() - t0))


if __name__ == '__main__':
    main()
