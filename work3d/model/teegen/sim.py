"""Blender cloth simulation: the rest shell hangs on the mannequin (pinned at the top edge of the collar rib)
while the mannequin's arms come down from the rest pose to the relaxed pose."""
import hashlib, json, math, os, time
import numpy as np
from . import mannequin as mq


def to_b(p):
    p = np.asarray(p)
    return np.stack([p[..., 0], -p[..., 2], p[..., 1]], -1)


def from_b(p):
    p = np.asarray(p)
    return np.stack([p[..., 0], p[..., 2], -p[..., 1]], -1)


def _mesh_obj(bpy, name, verts_b, faces, location=(0, 0, 0)):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(map(float, v)) for v in verts_b], [], [tuple(int(i) for i in f) for f in faces])
    me.update()
    ob = bpy.data.objects.new(name, me)
    ob.location = location
    bpy.context.scene.collection.objects.link(ob)
    return ob


def print_zone(P, T, rest):
    """Soft mask (0..1) of the chest print area in the rest metric. A printed area is stiffer than plain jersey
    (ink film), so it gets extra bending stiffness in the simulation and folds form around it, not through it."""
    N, NR, M = P.N, P.NR, P.M
    w = np.zeros(T.n)
    def ss(a, b, x):
        t = np.clip((x - a) / (b - a), 0, 1)
        return t * t * (3 - 2 * t)
    hem = rest[T.vid[M]]
    col_w = np.linalg.norm(np.roll(hem, -1, 0) - hem, axis=1).sum() / N
    for i in list(range(0, N // 4)) + list(range(3 * N // 4, N)):
        isg = i if i < N // 2 else i - N
        zu = 1 - ss(0.155, 0.200, abs(isg) * col_w)
        if zu <= 0:
            continue
        acc = 0.0
        for j in range(NR + 1, M + 1):
            a, b = T.vid[j, i], T.vid[j - 1, i]
            if a < 0 or b < 0:
                break
            acc += np.linalg.norm(rest[a] - rest[b])
            w[a] = zu * ss(0.045, 0.075, acc) * (1 - ss(0.370, 0.430, acc))
    return w


def groups(P, T, rest=None):
    """Per-vertex weights: pin (top edge of the rib) and stiff (rib, hems, seams)."""
    n = T.n
    pin = np.zeros(n)
    stiff = np.zeros(n)
    row, sk = T.row, T.sk
    body = row >= 0
    pin[body & (row == 0)] = 1.0
    stiff[body & (row <= P.NR)] = 1.0
    stiff[body & (row == P.NR + 1)] = 0.4
    for k, w in ((0, 1.0), (1, 1.0), (2, 0.8), (3, 0.4)):          # bottom hem (~2.5 cm)
        stiff[body & (row == P.M - k)] = w
    for k, w in ((0, 1.0), (1, 1.0), (2, 0.8), (3, 0.4)):          # sleeve hems
        stiff[sk == P.K - k] = w
    for lp in T.loops:                                              # armhole seams
        stiff[lp] = np.maximum(stiff[lp], 0.35)
    if rest is not None and P.sim.print_stiff > 0:
        stiff = np.maximum(stiff, P.sim.print_stiff * print_zone(P, T, rest))
    noself = np.zeros(n)
    noself[body & (row <= P.NR + 5)] = 1.0                          # dense collar rows: no self collision
    return pin, stiff, noself


def simulate(P, D, T, rest, cache_dir=None, log=print, keep_frames=()):
    S = P.sim
    key_src = json.dumps({k: (v if not isinstance(v, float) else round(v, 9)) for k, v in sorted(vars(S).items())}) + \
        json.dumps([P.alpha_L, P.alpha_R, P.fwd_L, P.fwd_R, P.jx, P.jy, P.jz, P.arm_r]) + \
        json.dumps(mq.torso_sections(P)) + hashlib.sha1(np.round(rest, 6).tobytes()).hexdigest() + "v4"
    key = hashlib.sha1(key_src.encode()).hexdigest()[:16]
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)
        cp = os.path.join(cache_dir, f"sim_{key}.npz")
        if os.path.exists(cp):
            log(f"[sim] using cached result {cp}")
            z = np.load(cp)
            return z["final"], {int(k[1:]): z[k] for k in z.files if k != "final"}
    import bpy
    from mathutils import Vector
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    F = S.f_settle0 + S.f_move + S.f_settle1
    sc.frame_start, sc.frame_end = 1, F
    # ---- colliders ----
    tv, tf = mq.torso_mesh(P)
    torso = _mesh_obj(bpy, "Torso", to_b(tv), tf)
    arms = []
    for sgn, alpha, fwd in ((1.0, P.alpha_L, P.fwd_L), (-1.0, P.alpha_R, P.fwd_R)):
        d_rest = D.d * np.array([sgn, 1, 1])
        av, af = mq.arm_mesh(P, d_rest, sgn)
        J = np.array([sgn * P.jx, P.jy, P.jz])
        ob = _mesh_obj(bpy, "ArmL" if sgn > 0 else "ArmR", to_b(av - J), af, tuple(to_b(J)))
        ob.rotation_mode = "QUATERNION"
        d_fin = mq.arm_dir(alpha, fwd, sgn)
        arms.append((ob, Vector(to_b(d_rest)), Vector(to_b(d_fin))))
    for ob in [torso] + [a[0] for a in arms]:
        ob.modifiers.new("col", "COLLISION")
        ob.collision.thickness_outer = S.collider_outer
        ob.collision.thickness_inner = 0.03
        ob.collision.cloth_friction = S.friction
        ob.collision.damping = 0.6

    def pose(f):
        u = min(max((f - S.f_settle0) / float(S.f_move), 0.0), 1.0)
        u = u * u * u * (u * (u * 6 - 15) + 10)           # smootherstep
        for ob, d0, d1 in arms:
            q = d0.rotation_difference(d1)
            from mathutils import Quaternion
            ob.rotation_quaternion = Quaternion().slerp(q, u)
            ob.keyframe_insert("rotation_quaternion", frame=f)

    for f in range(1, F + 1):
        pose(f)
    # ---- cloth ----
    cloth = _mesh_obj(bpy, "Cloth", to_b(rest), T.quads)
    for poly in cloth.data.polygons:
        poly.use_smooth = True
    pin, stiff, noself = groups(P, T, rest)
    for name, w in (("pin", pin), ("stiff", stiff), ("noself", noself)):
        vg = cloth.vertex_groups.new(name=name)
        for i in np.nonzero(w > 0)[0]:
            vg.add([int(i)], float(w[i]), "REPLACE")
    md = cloth.modifiers.new("cloth", "CLOTH")
    cs, col = md.settings, md.collision_settings
    cs.quality = S.quality
    cs.mass = S.mass
    cs.air_damping = S.air_damping
    cs.bending_model = "ANGULAR"
    cs.tension_stiffness = S.tension
    cs.compression_stiffness = S.compression
    cs.shear_stiffness = S.shear
    cs.bending_stiffness = S.bending
    cs.tension_damping = S.tension_damp
    cs.compression_damping = S.compression_damp
    cs.shear_damping = S.shear_damp
    cs.bending_damping = S.bending_damp
    cs.vertex_group_mass = "pin"
    cs.pin_stiffness = 1.0
    cs.vertex_group_bending = "stiff"
    cs.bending_stiffness_max = S.stiff_bending
    cs.vertex_group_structural_stiffness = "stiff"
    cs.tension_stiffness_max = S.stiff_tension
    cs.compression_stiffness_max = S.stiff_tension
    col.use_collision = True
    col.distance_min = S.dist
    col.collision_quality = S.coll_quality
    col.friction = S.friction
    col.use_self_collision = True
    col.self_distance_min = S.self_dist
    col.self_friction = S.self_friction
    col.vertex_group_self_collisions = "noself"
    md.point_cache.frame_start, md.point_cache.frame_end = 1, F

    def grab():
        dg = bpy.context.evaluated_depsgraph_get()
        ev = cloth.evaluated_get(dg)
        me = ev.to_mesh()
        co = np.empty(len(me.vertices) * 3)
        me.vertices.foreach_get("co", co)
        ev.to_mesh_clear()
        return from_b(co.reshape(-1, 3))

    t0 = time.time()
    prev = rest.copy()
    kept = {}
    el0 = np.linalg.norm(rest[T.edges[:, 0]] - rest[T.edges[:, 1]], axis=1)
    for f in range(1, F + 1):
        sc.frame_set(f)
        if f % 10 == 0 or f == F or f in keep_frames:
            cur = grab()
            sp = np.linalg.norm(cur - prev, axis=1)
            el = np.linalg.norm(cur[T.edges[:, 0]] - cur[T.edges[:, 1]], axis=1)
            strain = el / el0 - 1
            log(f"[sim] frame {f:3d}/{F}  {time.time() - t0:6.1f}s  move(last 10f) max {sp.max() * 1000:6.1f} mm mean {sp.mean() * 1000:5.2f} mm"
                f"  strain mean {strain.mean() * 100:+.2f}% p99 {np.percentile(strain, 99) * 100:+.2f}%  hem y {cur[T.vid[P.M]][:, 1].mean():.3f}")
            if not np.isfinite(cur).all():
                raise RuntimeError("simulation exploded")
            prev = cur
            if f in keep_frames:
                kept[f] = cur
    final = grab()
    if cache_dir:
        np.savez_compressed(cp, final=final, **{f"f{k}": v for k, v in kept.items()})
    return final, kept
