"""UV unwrap of the outer shell on its REST shape (so the texture is isometric to the fabric at rest):
islands = front panel, back panel, two sleeves (cut along the underarm line), like the sewing pattern.
Blender's minimum-stretch unwrap flattens each island; islands are then scaled to true size (metres),
rotated upright and packed by a small shelf packer."""
import numpy as np


def face_labels(P, T):
    """0 front, 1 back, 2 sleeve +x, 3 sleeve -x (body quads split along the shoulder/side lines)."""
    lab = np.zeros(len(T.quads), int)
    part, a, b = T.qinfo[:, 0], T.qinfo[:, 1], T.qinfo[:, 2]
    N = P.N
    body = part == 0
    back = body & (b >= N // 4) & (b < 3 * N // 4)
    lab[back] = 1
    lab[part == 1] = 2
    lab[part == 2] = 3
    return lab


def unwrap(P, T, rest, method="MINIMUM_STRETCH"):
    """Returns uv (nquads, 4, 2) in metres, per-island upright; and labels."""
    import bpy
    lab = face_labels(P, T)
    quads = T.quads
    me = bpy.data.meshes.new("uvtmp")
    # Blender frame not needed here: the unwrap is intrinsic
    me.from_pydata([tuple(map(float, v)) for v in rest], [], [tuple(int(i) for i in q) for q in quads])
    me.update()
    ob = bpy.data.objects.new("uvtmp", me)
    bpy.context.scene.collection.objects.link(ob)
    # seams: edges between faces with different labels + sleeve underarm lines + collar seam is a boundary already
    ekey = {}
    for e in me.edges:
        a, b = e.vertices
        ekey[(min(a, b), max(a, b))] = e.index
    efaces = {}
    for fi, q in enumerate(quads):
        for k in range(4):
            a, b = int(q[k]), int(q[(k + 1) % 4])
            efaces.setdefault((min(a, b), max(a, b)), []).append(fi)
    seams = set()
    for k, fl in efaces.items():
        if len(fl) == 2 and lab[fl[0]] != lab[fl[1]]:
            seams.add(k)
    C, K = P.C, P.K
    for s in (0, 1):
        for k in range(K):
            a, b = int(T.sleeve[s][k][C // 2]), int(T.sleeve[s][k + 1][C // 2])
            seams.add((min(a, b), max(a, b)))
    for k in seams:
        me.edges[ekey[k]].use_seam = True
    me.uv_layers.new(name="UVMap")
    for o in bpy.context.scene.objects:
        o.select_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    try:
        bpy.ops.uv.unwrap(method=method, fill_holes=False, correct_aspect=False, margin=0.001, iterations=40)
    except TypeError:
        bpy.ops.uv.unwrap(method=method, margin=0.001)
    bpy.ops.object.mode_set(mode="OBJECT")
    uv = np.empty(len(me.loops) * 2)
    me.uv_layers.active.data.foreach_get("uv", uv)
    uv = uv.reshape(len(quads), 4, 2).astype(np.float64)
    bpy.data.objects.remove(ob)
    bpy.data.meshes.remove(me)

    # sleeve islands: the underarm cut splits the vertex ring at q = C/2 -> two UVs per vertex, handled per face corner
    out = np.zeros_like(uv)
    info = {}
    for L in range(4):
        m = lab == L
        q = quads[m]
        u = uv[m]
        # true-size scale
        p = rest[q]
        a3 = 0.5 * (np.linalg.norm(np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0]), axis=1) +
                    np.linalg.norm(np.cross(p[:, 2] - p[:, 0], p[:, 3] - p[:, 0]), axis=1)).sum()

        def area2(t):
            return 0.5 * ((t[:, 1, 0] - t[:, 0, 0]) * (t[:, 2, 1] - t[:, 0, 1]) - (t[:, 1, 1] - t[:, 0, 1]) * (t[:, 2, 0] - t[:, 0, 0]))
        a2 = (area2(u[:, [0, 1, 2]]) + area2(u[:, [0, 2, 3]])).sum()
        if a2 < 0:                       # mirrored island: flip u
            u = u * np.array([-1.0, 1.0])
            a2 = -a2
        u = u * np.sqrt(a3 / a2)
        # upright: reference direction (hem -> collar for the body, hem -> armhole for the sleeves) maps to +v
        if L < 2:
            col = 0 if L == 0 else P.N // 2
            v_lo, v_hi = T.vid[P.M, col], T.vid[P.NR, col]
        else:
            s = L - 2
            v_lo, v_hi = T.sleeve[s][P.K][0], T.sleeve[s][0][0]

        def uv_of(v):
            fi, ci = np.nonzero(q == v)
            return u[fi[0], ci[0]]
        d = uv_of(v_hi) - uv_of(v_lo)
        ang = np.arctan2(d[0], d[1])
        c, s_ = np.cos(ang), np.sin(ang)
        R = np.array([[c, -s_], [s_, c]])
        u = u @ R.T
        u -= u.reshape(-1, 2).min(0)
        out[m] = u
        # distortion statistics (edge length ratio uv / 3d)
        e3 = np.linalg.norm(p - np.roll(p, -1, 1), axis=2)
        e2 = np.linalg.norm(u - np.roll(u, -1, 1), axis=2)
        r = e2 / e3
        info[L] = dict(size=u.reshape(-1, 2).max(0), area=a3, stretch=(float(np.percentile(r, 1)), float(np.percentile(r, 99))))
    return out, lab, info


def shelf_pack(sizes_px, W, margin):
    """Greedy shelf packing. sizes_px: list of (w, h). Returns list of (x, y) or None if it does not fit in W x W."""
    order = sorted(range(len(sizes_px)), key=lambda k: -sizes_px[k][1])
    pos = [None] * len(sizes_px)
    shelves = []            # [y, height, x_cursor]
    y_next = margin
    for k in order:
        w, h = sizes_px[k]
        placed = False
        for sh in shelves:
            if sh[2] + w + margin <= W and h <= sh[1]:
                pos[k] = (sh[2], sh[0])
                sh[2] += w + margin
                placed = True
                break
        if not placed:
            if y_next + h + margin > W or w + 2 * margin > W:
                return None
            shelves.append([y_next, h, margin + w + margin])
            pos[k] = (margin, y_next)
            y_next += h + margin
    return pos
