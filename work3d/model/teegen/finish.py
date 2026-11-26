"""From the simulated outer surface to the exported solid garment:
light smoothing, cloth thickness (inner shell), rounded hem rims, a thick rib collar built on the simulated
rib rows, UV islands, per-vertex texture attributes and ambient occlusion."""
import math
import numpy as np

NA = 9.0   # "not applicable" distance value for texture attributes
CH_DHEM, CH_DNECK, CH_DSH, CH_DSLV, CH_DARM, CH_AHEM, CH_ANECK, CH_ASLV = range(8)
ISL_FRONT, ISL_BACK, ISL_SL, ISL_SR, ISL_COLLAR = 0, 1, 2, 3, 4
ISL_INNER = 5        # inner copies are ISL_INNER + outer island id
ISL_LABEL = 9        # woven size label inside the back neck


# ------------------------------------------------------------------------------------------ smoothing
def boundary_rings(P, T):
    return [T.vid[0].copy(), T.vid[P.M].copy(), T.sleeve[0][P.K].copy(), T.sleeve[1][P.K].copy()]


def smoothing_neighbours(P, T):
    nbr = T.nbr.copy()
    for ring in boundary_rings(P, T):
        n = len(ring)
        for k in range(n):
            nbr[ring[k]] = -1
            nbr[ring[k], 0] = ring[(k - 1) % n]
            nbr[ring[k], 1] = ring[(k + 1) % n]
    return nbr


def _avg(nbr, X):
    acc = np.zeros_like(X)
    cnt = np.zeros(len(X))
    for k in range(nbr.shape[1]):
        m = nbr[:, k] >= 0
        acc[m] += X[nbr[m, k]]
        cnt[m] += 1
    return acc / cnt[:, None]


def smooth_sim(P, T, X, iters=4, lam=0.5, mu=-0.53, hem_iters=12, zone=None, zone_iters=10, sleeve_iters=8):
    """Taubin smoothing (removes solver jitter without shrinking) + fairing of the hem lines.
    zone: optional per-vertex weights of an area that gets extra fairing (the print area must stay calm)."""
    nbr = smoothing_neighbours(P, T)
    X = X.copy()
    for _ in range(iters):
        X += lam * (_avg(nbr, X) - X)
        X += mu * (_avg(nbr, X) - X)
    if zone is not None:
        wz = zone[:, None]
        for _ in range(zone_iters):
            X += wz * lam * (_avg(nbr, X) - X)
            X += wz * mu * (_avg(nbr, X) - X)
    # sleeves: the fabric bunches between arm and body; fair away pinches but keep the broad folds
    ws = np.zeros(len(X))
    ws[T.sk > 0] = 1.0
    for lp in T.loops:
        ws[lp] = 0.6
    for _ in range(2):                                   # soft falloff onto the body around the armhole
        ext = np.concatenate([ws, [0.0]])
        ws = np.maximum(ws, 0.6 * ext[T.nbr].max(1))
    for _ in range(sleeve_iters):
        X += ws[:, None] * lam * (_avg(nbr, X) - X)
        X += ws[:, None] * mu * (_avg(nbr, X) - X)
    # hems: low-pass the rings themselves a little more (wobbly hems read as cheap)
    def ring_smooth(rings_w):
        for ring, w in rings_w:
            for _ in range(hem_iters):
                a = 0.25 * (np.roll(X[ring], 1, 0) + np.roll(X[ring], -1, 0)) + 0.5 * X[ring]
                b = 0.25 * (np.roll(a, 1, 0) + np.roll(a, -1, 0)) + 0.5 * a      # second pass with ...
                # ... Taubin-like inverse step to limit shrinkage of the ring
                X[ring] += w * ((a + (a - b) * 1.0) - X[ring])
    rw = []
    for k, w in ((0, 0.6), (1, 0.45), (2, 0.3), (3, 0.15)):
        rw.append((T.vid[P.M - k], w))
    ring_smooth(rw)
    rw = []
    for k, w in ((0, 0.9), (1, 0.75), (2, 0.55), (3, 0.35), (4, 0.2)):     # sleeve hems: no pleats in the stiff hem
        for s in (0, 1):
            rw.append((T.sleeve[s][P.K - k], w))
    for _ in range(3):
        ring_smooth(rw)
    return X


def separate_layers(T, X, d_min=0.0035, iters=4, log=print):
    """Where two outer cloth layers face each other closer than d_min (sleeve against the body, tight folds)
    push them apart along their normals, so that the smoothed surfaces never poke through each other."""
    import bpy  # noqa: F401
    from mathutils.bvhtree import BVHTree
    from mathutils import Vector
    X = X.copy()
    q = T.quads
    st = np.concatenate([q[:, [0, 1, 2]], q[:, [0, 2, 3]]])
    faces = [tuple(int(i) for i in f) for f in st]
    total = 0
    for it in range(iters):
        Nrm = outer_normals(T, X)
        tree = BVHTree.FromPolygons([tuple(map(float, p)) for p in X], faces)
        disp = np.zeros_like(X)
        cnt = 0
        for v in range(len(X)):
            n0 = Nrm[v]
            hit = tree.ray_cast(Vector(X[v] + n0 * 0.0003), Vector(n0), d_min)
            if hit[0] is not None:
                d = hit[3] + 0.0003
                if d < d_min:
                    disp[v] = -n0 * (d_min - d) * 0.6
                    cnt += 1
        if cnt == 0:
            break
        # spread the correction a little so that it does not dent single vertices
        nb = T.nbr
        ext = np.concatenate([disp, np.zeros((1, 3))])
        avg = ext[nb].sum(1) / T.cnt[:, None]
        X += 0.7 * disp + 0.3 * avg
        total = max(total, cnt)
    log(f"[finish] layer separation: up to {total} vertices closer than {d_min * 1000:.1f} mm to another layer were pushed apart")
    return X


def fourier_ring(pts, hmax):
    """Low-pass of a closed polyline: keep only the first hmax harmonics (removes pleats and pinches)."""
    f = np.fft.rfft(pts, axis=0)
    f[hmax + 1:] = 0
    return np.fft.irfft(f, n=len(pts), axis=0)


def fair_hems(P, T, X):
    """Hems are double layered and stitched: they hang in smooth broad waves, never in small pleats."""
    X = X.copy()
    K, M = P.K, P.M
    for s in (0, 1):
        for d in range(0, 13):
            w = min(1.0, 1.25 * (1.0 - d / 13.0))
            w = w * w * (3 - 2 * w)
            ring = T.sleeve[s][K - d]
            X[ring] += w * (fourier_ring(X[ring], 3 + d // 2) - X[ring])
    for d, w in ((0, 0.8), (1, 0.65), (2, 0.45), (3, 0.25), (4, 0.1)):
        ring = T.vid[M - d]
        X[ring] += w * (fourier_ring(X[ring], 14) - X[ring])
    return X


def outer_normals(T, X):
    q = T.quads
    fn = np.cross(X[q[:, 2]] - X[q[:, 0]], X[q[:, 3]] - X[q[:, 1]])
    n = np.zeros_like(X)
    for k in range(4):
        np.add.at(n, q[:, k], fn)
    return n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-20)


# ------------------------------------------------------------------------------------------ rest metric
def rest_metrics(P, T, rest):
    """Arc lengths in the rest shape used to place stitches, seams and hems in the textures."""
    N, M, NR, J0, K, C = P.N, P.M, P.NR, P.J0, P.K, P.C
    n = T.n
    d_hem = np.full(n, NA)
    d_neck = np.full(n, NA)
    d_sh = np.full(n, NA)
    a_neck = np.zeros(N + 1)
    vid = T.vid
    # column arcs on the body (columns interrupted by the armhole simply stop there)
    for i in range(N):
        acc = 0.0
        d_hem[vid[M, i]] = 0.0
        for j in range(M - 1, NR - 1, -1):
            if vid[j, i] < 0 or vid[j + 1, i] < 0:
                break
            acc += np.linalg.norm(rest[vid[j, i]] - rest[vid[j + 1, i]])
            d_hem[vid[j, i]] = acc
        acc = 0.0
        d_neck[vid[NR, i]] = 0.0
        for j in range(NR + 1, M + 1):
            if vid[j, i] < 0 or vid[j - 1, i] < 0:
                break
            acc += np.linalg.norm(rest[vid[j, i]] - rest[vid[j - 1, i]])
            d_neck[vid[j, i]] = acc
    # shoulder seam: arc along the row away from column N/4 (and 3N/4), unsigned
    for c in (N // 4, 3 * N // 4):
        for j in range(NR, J0 + 1):
            d_sh[vid[j, c]] = 0.0
            for dn in (1, -1):
                acc = 0.0
                for k in range(1, 7):
                    a, b = vid[j, (c + dn * k) % N], vid[j, (c + dn * (k - 1)) % N]
                    acc += np.linalg.norm(rest[a] - rest[b])
                    d_sh[a] = acc
    ring = rest[vid[NR]]
    seg = np.linalg.norm(np.roll(ring, -1, 0) - ring, axis=1)
    a_neck[1:] = np.cumsum(seg)                      # arc at column i (0..N), column N == column 0
    hem = rest[vid[M]]
    hem_len = np.linalg.norm(np.roll(hem, -1, 0) - hem, axis=1).sum()
    # sleeves
    arc_seam = np.zeros((2, K + 1, C))
    arc_hem = np.zeros((2, K + 1, C))
    slv_len = np.zeros(2)
    for s in (0, 1):
        pts = np.array([rest[T.sleeve[s][k]] for k in range(K + 1)])
        seg = np.linalg.norm(np.diff(pts, axis=0), axis=2)
        arc_seam[s, 1:] = np.cumsum(seg, 0)
        arc_hem[s] = arc_seam[s, -1][None, :] - arc_seam[s]
        hr = pts[K]
        slv_len[s] = np.linalg.norm(np.roll(hr, -1, 0) - hr, axis=1).sum()
    return dict(d_hem=d_hem, d_neck=d_neck, d_sh=d_sh, a_neck=a_neck, neck_len=a_neck[-1], hem_len=hem_len,
                arc_seam=arc_seam, arc_hem=arc_hem, slv_len=slv_len)


# ------------------------------------------------------------------------------------------ collar profile
def collar_profile(P, t_body):
    """2D cross-section of the rib (s along the rib from the seam, h outwards), in metres, with 2D normals.
    Runs from the outer seam, up the outer face, over the folded top edge, down the inner face to the inner seam."""
    W = P.rib_w
    h_out, h_in = 0.0016, -0.0032          # outer face proud of the body, inner face
    rf = (h_out - 0.0003 - h_in) / 2       # fold radius
    hc = h_out - 0.0003 - rf
    sc = W - rf
    pts = [(0.0, 0.0), (0.0006, 0.00060), (0.0018, 0.00120), (0.0045, h_out - 0.0001), (0.0090, h_out), (0.0140, h_out), (0.0180, h_out - 0.0001)]
    for a in (0, 30, 60, 90, 120, 150, 180):
        ar = math.radians(a)
        pts.append((sc + rf * math.sin(ar), hc + rf * math.cos(ar)))
    pts += [(0.0150, h_in - 0.0001), (0.0080, h_in - 0.0001), (0.0025, h_in), (0.0007, -t_body - 0.0004), (0.0, -t_body)]
    pts = np.array(pts)
    tan = np.empty_like(pts)
    tan[1:-1] = pts[2:] - pts[:-2]
    tan[0] = pts[1] - pts[0]
    tan[-1] = pts[-1] - pts[-2]
    tan /= np.linalg.norm(tan, axis=1, keepdims=True)
    nrm = np.stack([-tan[:, 1], tan[:, 0]], 1)
    arc = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))])
    return pts, nrm, arc


def _catmull(Q, t):
    """Q: (m, n, 3) control points along the first axis, t in [0, m-1]. Returns position and derivative."""
    m = Q.shape[0]
    ext = np.concatenate([2 * Q[:1] - Q[1:2], Q, 2 * Q[-1:] - Q[-2:-1]], 0)
    k = int(min(max(math.floor(t), 0), m - 2))
    u = t - k
    p0, p1, p2, p3 = ext[k], ext[k + 1], ext[k + 2], ext[k + 3]
    pos = 0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3)
    der = 0.5 * ((-p0 + p2) + 2 * (2 * p0 - 5 * p1 + 4 * p2 - p3) * u + 3 * (-p0 + 3 * p1 - 3 * p2 + p3) * u * u)
    return pos, der


# ------------------------------------------------------------------------------------------ assembly
class Garment:
    pass


def assemble(P, T, X, rest, uv_corner, labels, log=print):
    """X: smoothed simulated positions of the sim mesh. Returns a Garment with export arrays."""
    N, M, NR, J0, J1, K, C = P.N, P.M, P.NR, P.J0, P.J1, P.K, P.C
    Nrm = outer_normals(T, X)
    RM = rest_metrics(P, T, rest)
    quads, qinfo = T.quads, T.qinfo
    nq = len(quads)
    # exported outer faces: everything except the rib rows
    keep = ~((qinfo[:, 0] == 0) & (qinfo[:, 1] < NR))
    # ---- corner grid coordinates -> island-continuous column coordinate "ci"
    part, qa, qb = qinfo[:, 0], qinfo[:, 1], qinfo[:, 2]
    cc = np.zeros((nq, 4))
    body = part == 0
    cc[body] = qb[body][:, None] + np.array([0, 0, 1, 1])[None, :]
    off = np.where(labels == ISL_BACK, N // 2, np.where(qb >= 3 * N // 4, N, 0))
    cc[body] -= off[body][:, None]
    s0, s1 = part == 1, part == 2
    cc[s0] = qb[s0][:, None] + np.array([0, 1, 1, 0])[None, :]
    cc[s1] = qb[s1][:, None] + np.array([0, 0, 1, 1])[None, :]
    slv = s0 | s1
    cc[slv] -= np.where(qb[slv] >= C // 2, C, 0)[:, None]
    # ---- unique export vertices (sim vertex, island, ci)
    fk = np.nonzero(keep)[0]
    v_c = quads[fk].reshape(-1)
    l_c = np.repeat(labels[fk], 4)
    ci_c = cc[fk].reshape(-1)
    key = v_c.astype(np.int64) * 100000 + l_c * 10000 + np.round(ci_c + 2000).astype(np.int64)
    uk, first, inv = np.unique(key, return_index=True, return_inverse=True)
    ne = len(uk)
    e_sv, e_isl, e_ci = v_c[first], l_c[first], ci_c[first]
    e_uv = uv_corner[fk].reshape(-1, 2)[first]
    dev = np.abs(uv_corner[fk].reshape(-1, 2) - e_uv[inv]).max()
    log(f"[finish] outer export verts {ne}, uv duplicate deviation {dev * 1000:.3f} mm")
    oq = inv.reshape(-1, 4)                                  # outer quads in export indices
    key_to_e = {int(k): i for i, k in enumerate(uk)}

    def find(v, isl, ci):
        return key_to_e[int(v) * 100000 + int(isl) * 10000 + int(round(ci + 2000))]

    # ---- thickness field
    t = np.full(T.n, P.thickness)
    t_hem = 0.0030
    for k, w in ((0, 1.0), (1, 1.0), (2, 0.5)):
        t[T.vid[M - k]] = P.thickness + (t_hem - P.thickness) * w
        for s in (0, 1):
            t[T.sleeve[s][K - k]] = P.thickness + (t_hem - P.thickness) * w
    # never let the inner shell cross another cloth layer: thin the cloth locally inside tight folds
    import bpy  # noqa: F401
    from mathutils.bvhtree import BVHTree
    from mathutils import Vector
    st = np.concatenate([quads[:, [0, 1, 2]], quads[:, [0, 2, 3]]])
    tree = BVHTree.FromPolygons([tuple(map(float, p)) for p in X], [tuple(int(i) for i in f) for f in st])
    tmax = np.full(T.n, 1.0)
    for v in range(T.n):
        n0 = Nrm[v]
        hit = tree.ray_cast(Vector(X[v] - n0 * 0.0005), Vector(-n0), 0.014)
        if hit[0] is not None:
            tmax[v] = max(0.0003, (hit[3] + 0.0005 - 0.0010) / 2)
    for _ in range(2):                                  # spread the limit to the neighbours
        nb = T.nbr
        ext = np.concatenate([tmax, [1.0]])
        tmax = np.minimum(tmax, ext[nb].min(1) * 1.15)
    n_thin = int((tmax < t).sum())
    t = np.minimum(t, tmax)
    for _ in range(2):
        ext = np.concatenate([t, [0.0]])
        avg = (ext[T.nbr] * (T.nbr >= 0)).sum(1) / T.cnt
        t = np.minimum(t, 0.5 * t + 0.5 * avg)
    log(f"[finish] cloth thinned inside tight folds at {n_thin} vertices (min thickness {t.min() * 1000:.2f} mm)")
    Xin = X - t[:, None] * Nrm

    # ---- attributes of the outer export vertices
    A = np.full((ne, 8), NA)
    A[:, CH_AHEM] = 0.0
    A[:, CH_ANECK] = 0.0
    A[:, CH_ASLV] = 0.0
    bm = e_isl < 2
    A[bm, CH_DHEM] = RM["d_hem"][e_sv[bm]]
    A[bm, CH_DNECK] = RM["d_neck"][e_sv[bm]]
    A[bm, CH_DSH] = RM["d_sh"][e_sv[bm]]
    A[bm, CH_AHEM] = e_ci[bm] * RM["hem_len"] / N
    col_abs = np.where(e_isl == ISL_BACK, e_ci + N // 2, e_ci)       # may be negative on the front
    an = RM["a_neck"]
    A[bm, CH_ANECK] = np.where(col_abs[bm] >= 0, an[np.clip(col_abs[bm].astype(int), 0, N)],
                               an[np.clip((col_abs[bm] + N).astype(int), 0, N)] - an[-1])
    loop_q = [{int(v): q for q, v in enumerate(T.loops[s])} for s in (0, 1)]
    e_k = np.zeros(ne, int)
    e_q = np.zeros(ne, int)
    for e in np.nonzero(~bm)[0]:
        s = e_isl[e] - 2
        v = e_sv[e]
        k = T.sk[v] if T.sk[v] > 0 else 0
        q = T.sq[v] if k > 0 else loop_q[s][int(v)]
        e_k[e], e_q[e] = k, q
        A[e, CH_DSLV] = RM["arc_hem"][s, k, q]
        A[e, CH_DARM] = RM["arc_seam"][s, k, q]
        A[e, CH_ASLV] = e_ci[e] * RM["slv_len"][s] / C

    pos = [X[e_sv]]
    nrm = [Nrm[e_sv]]
    isl = [e_isl.copy()]
    uvm = [e_uv.copy()]
    att = [A]
    quads_out = [oq]
    count = ne

    # ---- inner shell (same UV layout, own islands)
    pos.append(Xin[e_sv])
    nrm.append(-Nrm[e_sv])
    isl.append(e_isl + ISL_INNER)
    uvm.append(e_uv.copy())
    att.append(A.copy())
    quads_out.append(oq[:, ::-1] + ne)
    count += ne

    # ---- hem rims
    angs = [math.radians(a) for a in (45, 90, 135, 180)]
    hem_edges = []                     # (export a, export b)
    up_of = {}
    for f_local, f in enumerate(fk):
        p_, a_, b_ = qinfo[f]
        q = oq[f_local]
        if p_ == 0 and a_ == M - 1:
            hem_edges.append((q[1], q[2]))
            up_of[q[1]] = q[0]
            up_of[q[2]] = q[3]
        elif p_ == 1 and a_ == K - 1:
            hem_edges.append((q[3], q[2]))
            up_of[q[3]] = q[0]
            up_of[q[2]] = q[1]
        elif p_ == 2 and a_ == K - 1:
            hem_edges.append((q[1], q[2]))
            up_of[q[1]] = q[0]
            up_of[q[2]] = q[3]
    hem_e = sorted(up_of.keys())
    chain = {}
    r_pos, r_nrm, r_isl, r_uv, r_att = [], [], [], [], []
    for e in hem_e:
        v, vu = e_sv[e], e_sv[up_of[e]]
        n0 = Nrm[v]
        rho = t[v] / 2
        tau = X[v] - X[vu]
        tau -= tau.dot(n0) * n0
        tau /= np.linalg.norm(tau)
        duv = e_uv[e] - e_uv[up_of[e]]
        duv /= np.linalg.norm(duv)
        ids = [e]
        for a in angs:
            if a < math.pi - 1e-6:
                r_pos.append(X[v] + rho * math.sin(a) * tau + (-rho + rho * math.cos(a)) * n0)
            else:
                r_pos.append(Xin[v])
            nn = math.sin(a) * tau + math.cos(a) * n0
            r_nrm.append(nn / np.linalg.norm(nn))
            r_isl.append(e_isl[e])
            r_uv.append(e_uv[e] + duv * rho * a)
            aa = A[e].copy()
            ch = CH_DHEM if e_isl[e] < 2 else CH_DSLV
            aa[ch] = -rho * a
            r_att.append(aa)
            ids.append(count + len(r_pos) - 1)
        chain[e] = ids
    rq = []
    for a, b in hem_edges:
        ca, cb = chain[a], chain[b]
        for k in range(len(angs)):
            rq.append((ca[k], cb[k], cb[k + 1], ca[k + 1]))
    r_pos, r_nrm = np.array(r_pos), np.array(r_nrm)
    pos.append(r_pos); nrm.append(r_nrm); isl.append(np.array(r_isl)); uvm.append(np.array(r_uv)); att.append(np.array(r_att))
    rq = np.array(rq)
    quads_out.append(rq)
    count += len(r_pos)

    # ---- collar
    prof, pnrm, parc = collar_profile(P, P.thickness)
    Q = np.array([X[T.vid[NR - r]] for r in range(NR + 1)])          # (NR+1, N, 3): seam ... top edge
    nprof = len(prof)
    ring_pos = np.zeros((nprof, N, 3))
    ring_nrm = np.zeros((nprof, N, 3))
    seam_n = Nrm[T.vid[NR]]
    for k in range(nprof):
        s, h = prof[k]
        cpos, cder = _catmull(Q, s / P.rib_w * NR)
        tau = cder / np.linalg.norm(cder, axis=1, keepdims=True)
        g = np.roll(cpos, -1, 0) - np.roll(cpos, 1, 0)
        m = np.cross(g, tau)
        m /= np.linalg.norm(m, axis=1, keepdims=True)
        m *= np.sign((m * seam_n).sum(1))[:, None]
        # keep m perpendicular to tau, and tau continuous
        ring_pos[k] = cpos + h * m
        nn = pnrm[k, 0] * tau + pnrm[k, 1] * m
        ring_nrm[k] = nn / np.linalg.norm(nn, axis=1, keepdims=True)
    ring_pos[0] = X[T.vid[NR]]
    ring_pos[-1] = Xin[T.vid[NR]]
    strip = (np.arange(N + 1) + N // 2) % N
    c_pos = ring_pos[:, strip].reshape(-1, 3)
    c_nrm = ring_nrm[:, strip].reshape(-1, 3)
    c_uv = np.stack([np.tile(np.arange(N + 1) / N * RM["neck_len"], nprof), np.repeat(parc, N + 1)], 1)
    c_att = np.full((len(c_pos), 8), NA)
    c_att[:, CH_DHEM] = np.repeat(parc, N + 1)                      # profile arc
    c_att[:, CH_DNECK] = np.repeat(prof[:, 0], N + 1)               # height above the seam
    c_att[:, CH_AHEM] = c_uv[:, 0]
    c_att[:, CH_ANECK] = 0.0
    c_att[:, CH_ASLV] = 0.0
    cq = []
    for k in range(nprof - 1):
        for c in range(N):
            a = count + k * (N + 1) + c
            cq.append((a, a + 1, a + (N + 1) + 1, a + (N + 1)))
    cq = np.array(cq)
    pos.append(c_pos); nrm.append(c_nrm); isl.append(np.full(len(c_pos), ISL_COLLAR)); uvm.append(c_uv); att.append(c_att)
    quads_out.append(cq)
    count += len(c_pos)

    # ---- woven label sewn inside the back neck (follows the inner surface of the back panel)
    tree_in = BVHTree.FromPolygons([tuple(map(float, p)) for p in Xin], [tuple(int(i) for i in f) for f in st[:, ::-1]])
    cb = N // 2
    O = Xin[T.vid[NR, cb]]
    e_d = Xin[T.vid[NR + 5, cb]] - O
    e_d /= np.linalg.norm(e_d)
    n_in = -Nrm[T.vid[NR + 2, cb]]
    n_in = n_in - n_in.dot(e_d) * e_d
    n_in /= np.linalg.norm(n_in)
    e_x = np.cross(e_d, n_in)
    us = np.array([-18, -17.2, -12, -6, 0, 6, 12, 17.2, 18]) * 1e-3
    vs = np.array([4, 4.8, 10, 16, 22, 28, 34, 40, 46, 51.2, 52]) * 1e-3
    l_pos, l_uv = [], []
    for jv, v in enumerate(vs):
        for ju, u in enumerate(us):
            Qp = O + u * e_x + v * e_d + 0.03 * n_in
            hit = tree_in.ray_cast(Vector(Qp), Vector(-n_in), 0.08)
            Hp = np.array(hit[0]) if hit[0] is not None else Qp - 0.03 * n_in
            edge = ju in (0, len(us) - 1) or jv in (0, len(vs) - 1)
            l_pos.append(Hp + n_in * (0.00012 if edge else 0.0010))
            l_uv.append((u, -v))
    l_pos = np.array(l_pos)
    nu_, nv_ = len(us), len(vs)
    lq = []
    for jv in range(nv_ - 1):
        for ju in range(nu_ - 1):
            a = count + jv * nu_ + ju
            lq.append((a, a + 1, a + nu_ + 1, a + nu_))
    lq = np.array(lq)
    lql = lq - count
    fnl = np.cross(l_pos[lql[:, 2]] - l_pos[lql[:, 0]], l_pos[lql[:, 3]] - l_pos[lql[:, 1]])
    if (fnl @ n_in).sum() < 0:
        lq = lq[:, ::-1]
        lql = lql[:, ::-1]
        fnl = -fnl
    l_nrm = np.zeros_like(l_pos)
    for k in range(4):
        np.add.at(l_nrm, lql[:, k], fnl)
    l_nrm /= np.linalg.norm(l_nrm, axis=1, keepdims=True)
    l_att = np.full((len(l_pos), 8), NA)
    l_att[:, CH_DHEM] = np.array(l_uv)[:, 0]
    l_att[:, CH_DNECK] = -np.array(l_uv)[:, 1]
    l_att[:, CH_AHEM] = 0.0
    l_att[:, CH_ANECK] = 0.0
    l_att[:, CH_ASLV] = 0.0
    pos.append(l_pos); nrm.append(l_nrm); isl.append(np.full(len(l_pos), ISL_LABEL)); uvm.append(np.array(l_uv)); att.append(l_att)
    quads_out.append(lq)
    count += len(l_pos)

    G = Garment()
    G.pos = np.concatenate(pos)
    G.nrm = np.concatenate(nrm)
    G.isl = np.concatenate(isl)
    G.uvm = np.concatenate(uvm)
    G.att = np.concatenate(att)
    # orientation of generated strips: make faces agree with their vertex normals
    allq = []
    for bi, qs in enumerate(quads_out):
        qs = np.asarray(qs)
        fn = np.cross(G.pos[qs[:, 2]] - G.pos[qs[:, 0]], G.pos[qs[:, 3]] - G.pos[qs[:, 1]])
        vn = G.nrm[qs].sum(1)
        flip = (fn * vn).sum(1) < 0
        if bi < 2:
            # outer / inner shell: orientation is given by the topology; only report folded-over quads
            log(f"[finish] shell batch {bi}: {int(flip.sum())} quads whose geometric normal opposes their vertex normals")
        else:
            qs = qs.copy()
            qs[flip] = qs[flip][:, ::-1]
        allq.append(qs)
    G.n_outer_quads = len(oq)
    G.quads = np.concatenate(allq)
    # triangulate along the shorter diagonal
    q = G.quads
    d02 = np.linalg.norm(G.pos[q[:, 0]] - G.pos[q[:, 2]], axis=1)
    d13 = np.linalg.norm(G.pos[q[:, 1]] - G.pos[q[:, 3]], axis=1)
    alt = d13 < d02
    t1 = np.where(alt[:, None], q[:, [0, 1, 3]], q[:, [0, 1, 2]])
    t2 = np.where(alt[:, None], q[:, [1, 2, 3]], q[:, [0, 2, 3]])
    G.tris = np.concatenate([t1, t2])
    G.outer_tris = np.concatenate([t1[:len(oq)], t2[:len(oq)]])        # outer shell only (print projection)
    G.n_outer_verts = ne
    G.e_sv, G.e_isl = e_sv, e_isl
    G.rest_metrics = RM
    G.Nrm_sim, G.X = Nrm, X
    log(f"[finish] export mesh: {len(G.pos)} verts, {len(G.tris)} tris (outer {2 * len(oq)}, collar {2 * len(cq)}, rims {2 * len(rq)})")
    return G


# ------------------------------------------------------------------------------------------ ambient occlusion
def ambient_occlusion(pos, nrm, tris, nrays=48, dmax=0.30, seed=7, log=print):
    import bpy  # noqa: F401
    from mathutils.bvhtree import BVHTree
    from mathutils import Vector
    tree = BVHTree.FromPolygons([tuple(map(float, p)) for p in pos], [tuple(int(i) for i in t) for t in tris])
    rng = np.random.default_rng(seed)
    # cosine weighted directions in tangent space (stratified)
    u1 = (np.arange(nrays) + 0.5) / nrays
    u2 = (np.arange(nrays) * 0.61803398875) % 1.0
    r = np.sqrt(u1)
    th = 2 * np.pi * u2
    loc = np.stack([r * np.cos(th), r * np.sin(th), np.sqrt(1 - u1)], 1)
    ao = np.ones(len(pos))
    rot = rng.uniform(0, 2 * np.pi, len(pos))
    for i in range(len(pos)):
        n = nrm[i]
        a = np.array([1.0, 0, 0]) if abs(n[0]) < 0.8 else np.array([0, 1.0, 0])
        t = np.cross(n, a)
        t /= np.linalg.norm(t)
        b = np.cross(n, t)
        c, s = math.cos(rot[i]), math.sin(rot[i])
        t2, b2 = c * t + s * b, -s * t + c * b
        dirs = loc[:, 0:1] * t2 + loc[:, 1:2] * b2 + loc[:, 2:3] * n
        o = Vector(pos[i] + n * 0.0012)
        occ = 0.0
        for d in dirs:
            hit = tree.ray_cast(o, Vector(d), dmax)
            if hit[0] is not None:
                x = hit[3] / dmax
                occ += 1.0 - x * x
        ao[i] = 1.0 - occ / nrays
    return ao
