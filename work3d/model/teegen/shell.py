"""Rest ("worn, arms half raised") shell of the tee: an implicit surface (boxy tube + shoulder roof + sleeve
cones, smoothly blended) carrying a structured all-quad grid:
  * one tube of N columns x (M+1) rows from the neckline to the hem ("poncho" layout: rows are loops around
    the neck that turn into horizontal body loops), with a rectangular hole per armhole,
  * one tube of C columns x K rings per sleeve, whose first ring is the hole boundary.
The grid is relaxed on the implicit surface (Laplacian smoothing + Newton projection)."""
import math
import numpy as np


def smin(a, b, k):
    h = np.maximum(k - np.abs(a - b), 0.0) / k
    return np.minimum(a, b) - h * h * h * k / 6.0


def smax(a, b, k):
    return -smin(-a, -b, k)


class Design:
    def __init__(self, P):
        self.P = P
        self.ts = math.tan(P.sigma)
        self.tgf = math.tan(P.gamma_f)
        self.tgfc = math.tan(P.gamma_fc)
        self.tgb = math.tan(P.gamma_b)
        self.nf = math.sqrt(1 + self.ts ** 2 + self.tgf ** 2)
        self.nb = math.sqrt(1 + self.ts ** 2 + self.tgb ** 2)
        b = P.beta_rest
        self.d = np.array([math.cos(b), -math.sin(b), 0.0])     # sleeve axis direction (+x side)
        self.n = np.array([math.sin(b), math.cos(b), 0.0])      # "top of the sleeve" direction
        J = np.array([P.jx, P.jy, P.jz])
        T0 = J + (P.arm_r + P.arm_clear) * self.n
        # ridge line: y = y_hps - ts * (x - neck_w); sleeve top line through T0 with direction d
        # solve T0 + c d on the ridge
        c = (P.y_hps - self.ts * (T0[0] - P.neck_w) - T0[1]) / (self.d[1] + self.ts * self.d[0])
        self.SP = T0 + c * self.d                                # where the shoulder line bends into the sleeve
        self.ridge_to_sp = (self.SP[0] - P.neck_w) / math.cos(P.sigma)
        self.t_seam = P.ridge_len - self.ridge_to_sp            # along the sleeve top from SP
        self.t_hem = self.t_seam + P.sleeve_len
        self.dr = (P.r_hem - P.r_seam) / P.sleeve_len
        self.A0 = self.SP - self.r_of(0.0) * self.n              # sleeve axis point under SP
        self.A0[2] = P.jz
        self.y0 = P.y_hps
        self.gap_th = None
        # funnel: make the surface pass exactly through the designed collar seam
        th = np.linspace(-np.pi, np.pi, 721)
        seam = self._neck_curve(th)
        self.gap_th = th
        self.gap_val = self.roof_height(seam[:, 0], seam[:, 2]) - seam[:, 1]
        # seam plane: contains the z direction, through the seam top point and the armpit point
        top = self.SP + self.t_seam * self.d
        # underside of the tube where it meets the plane x = body_a + 0.004
        xa = P.body_a + 0.004
        t_pit = (xa - self.A0[0] + P.r_seam * self.n[0]) / self.d[0]
        pit = self.A0 + t_pit * self.d - P.r_seam * self.n
        self.t_pit = t_pit
        self.seam_top, self.seam_pit = top, pit
        e = top - pit
        nrm = np.array([e[1], -e[0], 0.0])
        nrm /= np.linalg.norm(nrm)
        if nrm[0] < 0:
            nrm = -nrm
        self.seam_n, self.seam_o = nrm, top
        # axis exit through the body side wall (centre of the armhole on the vest)
        self.y_exit = self.A0[1] - (P.body_a - self.A0[0]) * math.tan(b)

    def r_of(self, t):
        return np.clip(self.P.r_seam + self.dr * (t - self.t_seam), 0.045, 0.09)

    # ------------------------------------------------------------------ implicit surface
    def sdf(self, p, g=1.0):
        P = self.P
        x, y, z = p[:, 0], p[:, 1], p[:, 2]
        d_t = self.tube_dist(x, z)
        roof = y - self.roof_height(x, z) + self.funnel(x, z)
        d = smax(roof * 0.72, d_t, P.k_tube)
        if g > 0:
            for sgn in (1.0, -1.0):
                m = np.array([sgn, 1.0, 1.0])
                pa = p - self.A0 * m
                dd = self.d * m
                t = pa @ dd
                tc = np.clip(t, 0.02, self.t_hem + 0.12)
                q = pa - tc[:, None] * dd
                da = np.linalg.norm(q, axis=1) - self.r_of(tc) * g
                d = smin(d, da, P.k_arm)
        return d

    def tube_dist(self, x, z):
        """First-order distance to the superelliptical body cross-section."""
        P = self.P
        n = P.body_n
        u = np.abs(x) / P.body_a + 1e-9
        v = np.abs(z - P.body_zc) / P.body_b + 1e-9
        r = (u ** n + v ** n) ** (1.0 / n)
        gx = u ** (n - 1) / P.body_a * r ** (1 - n)
        gz = v ** (n - 1) / P.body_b * r ** (1 - n)
        return (r - 1.0) / np.sqrt(gx * gx + gz * gz)

    def roof_height(self, x, z):
        P = self.P
        v = np.abs(x) - P.neck_w
        m = 0.5 * (v + np.sqrt(v * v + P.eps_x ** 2)) - P.eps_x / 2
        u = z - P.z_ridge
        sg = 0.5 + 0.5 * np.tanh(u / 0.02)
        q = np.clip(np.abs(x) / 0.13, 0, 1)
        tgf = self.tgfc + (self.tgf - self.tgfc) * q * q * (3 - 2 * q)
        tg = self.tgb + (tgf - self.tgb) * sg
        return self.y0 - self.ts * m - tg * (np.sqrt(u * u + P.c_roof ** 2) - P.c_roof)

    def _neck_dz(self, c):
        P = self.P
        return P.neck_back + (P.neck_front - P.neck_back) * (1 + c) / 2

    def _neck_curve(self, th):
        P = self.P
        c, s = np.cos(th), np.sin(th)
        x = P.neck_w * s
        z = P.z_ridge + self._neck_dz(c) * c
        y = P.y_hps - P.neck_drop_f * np.maximum(c, 0) ** 1.25 - P.neck_drop_b * np.maximum(-c, 0) ** 1.6
        return np.stack([x, y, z], 1)

    def funnel(self, x, z):
        """Height by which the roof is lowered so that it passes through the collar seam."""
        if self.gap_th is None:
            return 0.0
        P = self.P
        u = z - P.z_ridge
        dzm = (P.neck_front + P.neck_back) / 2
        th = np.arctan2(x / P.neck_w, u / dzm)
        for _ in range(3):
            th = np.arctan2(x / P.neck_w, u / self._neck_dz(np.cos(th)))
        dz = self._neck_dz(np.cos(th))
        rell = np.sqrt((x / P.neck_w) ** 2 + (u / dz) ** 2)
        rho = np.maximum(rell - 1.0, 0.0) * (P.neck_w + dz) / 2
        gap = np.interp(th, self.gap_th, self.gap_val)
        return gap * np.exp(-(rho / P.funnel_r) ** 2)

    def grad(self, p, g=1.0, h=1e-4):
        gr = np.empty_like(p)
        for k in range(3):
            e = np.zeros(3)
            e[k] = h
            gr[:, k] = (self.sdf(p + e, g) - self.sdf(p - e, g)) / (2 * h)
        return gr

    def project(self, p, g=1.0, iters=2, weight=None):
        for _ in range(iters):
            d = self.sdf(p, g)
            gr = self.grad(p, g)
            g2 = np.maximum((gr * gr).sum(1), 0.25)
            step = (d / g2)[:, None] * gr
            sl = np.linalg.norm(step, axis=1)
            step *= np.minimum(1.0, 0.012 / np.maximum(sl, 1e-12))[:, None]
            if weight is not None:
                step = step * weight[:, None]
            p = p - step
        return p

    # ------------------------------------------------------------------ design curves
    def neckline(self, n):
        """Collar seam loop, n points equally spaced by arc length, index 0 at the centre front,
        increasing towards +x."""
        P = self.P
        def arc(t0, t1, m):
            th = np.linspace(t0, t1, 2001)
            pts = self._neck_curve(th)
            L = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))])
            tgt = np.arange(m) * L[-1] / m
            return np.stack([np.interp(tgt, L, pts[:, k]) for k in range(3)], 1), L[-1]
        q = n // 4
        a, la = arc(0, np.pi / 2, q)                 # centre front -> +x shoulder (HPS at index q)
        b, lb = arc(np.pi / 2, np.pi, q)             # shoulder -> centre back
        c, _ = arc(np.pi, 1.5 * np.pi, q)
        d, _ = arc(1.5 * np.pi, 2 * np.pi, q)
        return np.concatenate([a, b, c, d]), 2 * (la + lb)

    def rib_rings(self, n, nr):
        """Rings of the collar rib: index 0 = top edge (the opening), index nr = the seam (neckline)."""
        P = self.P
        seam, L = self.neckline(n)
        tan = np.roll(seam, -1, 0) - np.roll(seam, 1, 0)
        tan /= np.linalg.norm(tan, axis=1, keepdims=True)
        h = np.stack([-tan[:, 2], np.zeros(n), tan[:, 0]], 1)        # horizontal normal of the loop
        cen = np.array([0.0, 0.0, P.z_ridge + (P.neck_front - P.neck_back) / 2])
        flip = ((cen - seam) * h).sum(1) < 0
        h[flip] *= -1
        h /= np.linalg.norm(h, axis=1, keepdims=True)
        c = (seam[:, 2] - cen[2]) / np.abs(seam[:, 2] - cen[2]).max()
        ef, es, eb = [math.radians(a) for a in P.rib_elev]
        el = es + (ef - es) * np.maximum(c, 0) ** 2 + (eb - es) * np.maximum(-c, 0) ** 2
        d = np.cos(el)[:, None] * h + np.sin(el)[:, None] * np.array([0, 1.0, 0])
        rings = [seam + d * P.rib_w * (1 - k / nr) for k in range(nr + 1)]
        return np.array(rings), d
    def stadium(self, n):
        """n points on the body cross-section, equally spaced by arc length, index 0 at centre front
        (z = +b), increasing towards +x. Returns (x, z, perimeter)."""
        P = self.P
        th = np.linspace(0, 2 * np.pi, 20001)
        c, s = np.cos(th), np.sin(th)
        e = 2.0 / P.body_n
        x = P.body_a * np.sign(s) * np.abs(s) ** e
        z = P.body_b * np.sign(c) * np.abs(c) ** e
        L = np.concatenate([[0], np.cumsum(np.hypot(np.diff(x), np.diff(z)))])
        q = n // 4
        tq = np.interp(np.array([0, 0.5, 1.0, 1.5, 2.0]) * np.pi, th, L)      # arc at the four axis points
        tgt = np.concatenate([np.linspace(tq[k], tq[k + 1], q, endpoint=False) for k in range(4)])
        return np.interp(tgt, L, x), np.interp(tgt, L, z) + P.body_zc, L[-1]


class Topology:
    def __init__(self, P):
        N, S, J0, R, K, M = P.N, P.S, P.J0, P.R, P.K, P.M
        J1 = P.J1
        hs = S // 2
        C = P.C
        self.P = P
        removed = np.zeros((M + 1, N), bool)
        for c in (N // 4, 3 * N // 4):
            removed[J0 + 1:J1, c - hs + 1:c + hs] = True
        vid = -np.ones((M + 1, N), int)
        vid[~removed] = np.arange((~removed).sum())
        self.removed, self.vid = removed, vid
        nb = int((~removed).sum())
        self.n_body = nb
        self.n = nb + 2 * K * C
        # grid coordinates of every vertex
        self.row = np.full(self.n, -1)
        self.col = np.full(self.n, -1)
        jj, ii = np.nonzero(~removed)
        self.row[vid[jj, ii]] = jj
        self.col[vid[jj, ii]] = ii
        quads = []
        qinfo = []          # (part, a, b): part 0 body (row j, col i), 1/2 sleeves (ring k, q)
        for j in range(M):
            for i in range(N):
                i1 = (i + 1) % N
                ids = (vid[j, i], vid[j, i1], vid[j + 1, i1], vid[j + 1, i])
                if min(ids) < 0:
                    continue
                c = N // 4 if i < N // 2 else 3 * N // 4
                if J0 <= j < J1 and c - hs <= i < c + hs:
                    continue
                quads.append((ids[0], ids[3], ids[2], ids[1]))
                qinfo.append((0, j, i))
        self.loops = []
        self.sleeve = []      # sleeve[s][k][q] -> vertex id, k = 0..K (k=0 is the hole loop)
        self.sk = np.full(self.n, -1)   # sleeve ring index per vertex (-1 for body)
        self.sq = np.full(self.n, -1)
        self.ss = np.full(self.n, -1)
        for s, (c, dn) in enumerate(((N // 4, -1), (3 * N // 4, 1))):
            loop = []
            for k in range(0, hs + 1):
                loop.append(vid[J0, (c + dn * k) % N])
            for j in range(J0 + 1, J1 + 1):
                loop.append(vid[j, (c + dn * hs) % N])
            for k in range(hs - 1, -hs - 1, -1):
                loop.append(vid[J1, (c + dn * k) % N])
            for j in range(J1 - 1, J0 - 1, -1):
                loop.append(vid[j, (c - dn * hs) % N])
            for k in range(-hs + 1, 0):
                loop.append(vid[J0, (c + dn * k) % N])
            assert len(loop) == C and min(loop) >= 0 and len(set(loop)) == C
            self.loops.append(np.array(loop))
            rings = [np.array(loop)]
            base = nb + s * K * C
            for k in range(1, K + 1):
                ids = base + (k - 1) * C + np.arange(C)
                rings.append(ids)
                self.sk[ids] = k
                self.sq[ids] = np.arange(C)
                self.ss[ids] = s
            self.sleeve.append(rings)
            for k in range(K):
                for q in range(C):
                    q1 = (q + 1) % C
                    a, b_, c_, d_ = rings[k][q], rings[k][q1], rings[k + 1][q1], rings[k + 1][q]
                    quads.append((a, b_, c_, d_) if s == 0 else (a, d_, c_, b_))
                    qinfo.append((1 + s, k, q))
        self.quads = np.array(quads)
        self.qinfo = np.array(qinfo)
        # adjacency (padded)
        e = np.concatenate([self.quads[:, [0, 1]], self.quads[:, [1, 2]], self.quads[:, [2, 3]], self.quads[:, [3, 0]]])
        e = np.unique(np.sort(e, axis=1), axis=0)
        self.edges = e
        cnt = np.zeros(self.n, int)
        nbr = -np.ones((self.n, 6), int)
        for a, b_ in e:
            nbr[a, cnt[a]] = b_
            cnt[a] += 1
            nbr[b_, cnt[b_]] = a
            cnt[b_] += 1
        self.nbr, self.cnt = nbr, cnt
        # mirror map: body (j, i) <-> (j, -i); sleeves: s0 (k, q) <-> s1 (k, q)
        mir = np.arange(self.n)
        for j in range(M + 1):
            for i in range(N):
                if vid[j, i] >= 0:
                    mir[vid[j, i]] = vid[j, (-i) % N]
        for k in range(1, K + 1):
            mir[self.sleeve[0][k]] = self.sleeve[1][k]
            mir[self.sleeve[1][k]] = self.sleeve[0][k]
        self.mirror = mir

    def nbr_avg(self, p, power=0.0):
        """Neighbour average; power > 0 weights neighbours by edge length**power (equalises edge lengths)."""
        nb = self.nbr
        acc = np.zeros_like(p)
        wsum = np.zeros(len(p))
        for k in range(nb.shape[1]):
            m = nb[:, k] >= 0
            q = p[nb[m, k]]
            if power > 0:
                w = np.linalg.norm(q - p[m], axis=1) ** power + 1e-9
            else:
                w = np.ones(m.sum())
            acc[m] += q * w[:, None]
            wsum[m] += w
        return acc / wsum[:, None]


def build_rest_shell(P, verbose=True):
    D = Design(P)
    T = Topology(P)
    N, S, J0, R, K, M, J1, C = P.N, P.S, P.J0, P.R, P.K, P.M, P.J1, P.C
    NR = P.NR
    neck, neck_len = D.neckline(N)
    rib, rib_dir = D.rib_rings(N, NR)
    sx, sz, per = D.stadium(N)
    if verbose:
        ro = np.linalg.norm(np.roll(rib[0], -1, 0) - rib[0], axis=1).sum()
        print(f"[shell] neck seam length {neck_len:.3f} m, rib opening {ro:.3f} m, body circumference {per:.3f} m, SP {D.SP.round(3)}, "
              f"t_seam {D.t_seam:.3f}, t_hem {D.t_hem:.3f}, t_pit {D.t_pit:.3f}, seam top {D.seam_top.round(3)}, "
              f"pit {D.seam_pit.round(3)}, y_exit {D.y_exit:.3f}")
    # ---------------- phase 1: full grid on the vest (no arms) -------------------------------
    half_h = 0.085
    y_top_hole = D.y_exit + half_h
    y_pit = D.y_exit - half_h
    G = np.zeros((M + 1, N, 3))
    ys = y_pit * (1 - (np.arange(J1, M + 1) - J1) / (M - J1))
    for jj, j in enumerate(range(J1, M + 1)):
        G[j, :, 0], G[j, :, 1], G[j, :, 2] = sx, ys[jj], sz
    ci = np.arange(N)
    dside = np.minimum(np.abs(ci - N // 4), np.abs(ci - 3 * N // 4))
    w = np.exp(-(dside / 7.0) ** 2)
    pJ1 = G[J1]
    chord_mid = neck + (pJ1 - neck) * ((J0 - NR) / (J1 - NR))
    side_mid = np.stack([sx * 0.96, np.full(N, y_top_hole), sz * 0.9 + P.z_ridge * 0.1], 1)
    mid = chord_mid * (1 - w[:, None]) + side_mid * w[:, None]
    for j in range(0, NR + 1):
        G[j] = rib[j]
    for j in range(NR, J0 + 1):
        G[j] = neck + (mid - neck) * ((j - NR) / (J0 - NR))
    for j in range(J0, J1 + 1):
        G[j] = mid + (pJ1 - mid) * ((j - J0) / (J1 - J0))
    fixed_rows = np.zeros(M + 1, bool)
    fixed_rows[:NR + 1] = True
    fixed_rows[J1 + 10:] = True
    wrow = (np.arange(M + 1) > NR).astype(float)          # rib rows are designed, everything else lives on the surface
    wgrid = np.repeat(wrow[:, None], N, 1)
    flat = G.reshape(-1, 3)
    flat[:] = np.where(fixed_rows.repeat(N)[:, None], flat, D.project(flat.copy(), 0.0, 3, wgrid.reshape(-1)))
    for it in range(60):
        avg = (np.roll(G, 1, 1) + np.roll(G, -1, 1)) / 2
        avg[1:-1] = (avg[1:-1] + (G[:-2] + G[2:]) / 2) / 2
        Gn = G + 0.5 * (avg - G)
        Gn[fixed_rows] = G[fixed_rows]
        fl = D.project(Gn.reshape(-1, 3), 0.0, 1, wgrid.reshape(-1)).reshape(G.shape)
        fl[fixed_rows] = G[fixed_rows]
        G = fl
    # ---------------- phase 2: holes + sleeves, arms inflate ----------------------------------
    p = np.zeros((T.n, 3))
    jj, ii = np.nonzero(~T.removed)
    p[T.vid[jj, ii]] = G[jj, ii]
    phi = 2 * np.pi * np.arange(C) / C

    def sleeve_ring(s, k, g):
        f = k / K
        t_loop = D.t_seam + (1 - np.cos(phi)) / 2 * (D.t_pit - D.t_seam)
        t = t_loop + (D.t_hem - t_loop) * f
        r = D.r_of(t) * g
        pts = D.A0[None] + t[:, None] * D.d[None] + r[:, None] * (np.cos(phi)[:, None] * D.n[None] + np.sin(phi)[:, None] * np.array([0, 0, 1.0])[None])
        if s == 1:
            pts = pts * np.array([-1.0, 1, 1])
        return pts

    free = np.ones(T.n, bool)
    for j in range(NR + 1):
        free[T.vid[j]] = False
    for j in range(J1 + 10, M + 1):
        free[T.vid[j]] = False
    wv = np.ones(T.n)
    body = T.row >= 0
    wv[body] = wrow[T.row[body]]
    loop_all = np.concatenate(T.loops)
    hem_ids = [T.sleeve[s][K] for s in (0, 1)]
    sgn = [np.array([1.0, 1, 1]), np.array([-1.0, 1, 1])]

    def constrain(p, seam=True):
        if seam:
            for s in (0, 1):
                ids = T.loops[s]
                nrm, o = D.seam_n * sgn[s], D.seam_o * sgn[s]
                p[ids] -= ((p[ids] - o) @ nrm)[:, None] * nrm
        for s in (0, 1):
            ids = hem_ids[s]
            dd, o = D.d * sgn[s], (D.A0 + D.t_hem * D.d) * sgn[s]
            p[ids] -= ((p[ids] - o) @ dd)[:, None] * dd
        return p

    steps = 50
    for a in range(steps + 1):
        g = 0.25 + 0.75 * a / steps
        for s in (0, 1):
            for k in range(1, K + 1):
                p[T.sleeve[s][k]] = sleeve_ring(s, k, g)
        for it in range(6):
            avg = T.nbr_avg(p)
            pn = p + 0.5 * (avg - p)
            pn = D.project(pn, g, 1, wv)
            keep = ~free | (T.sk > 0)
            pn[keep] = p[keep]
            p = pn
    for it in range(700):
        avg = T.nbr_avg(p, 1.0 if it > 250 else 0.0)
        pn = p + 0.6 * (avg - p)
        pn = constrain(pn)
        pn = D.project(pn, 1.0, 1, wv)
        pn = constrain(pn)
        pn[~free] = p[~free]
        if it % 10 == 9:
            m = pn[T.mirror] * np.array([-1.0, 1, 1])
            pn = 0.5 * (pn + m)
        p = pn
    p = D.project(p, 1.0, 2, wv)
    p = constrain(p)
    # re-space every sleeve column uniformly by arc length (the relaxation bunches rings in the armpit)
    for _ in range(3):
        for s in (0, 1):
            cols = np.array([p[T.sleeve[s][k]] for k in range(K + 1)])      # (K+1, C, 3)
            seg = np.linalg.norm(np.diff(cols, axis=0), axis=2)
            L = np.concatenate([np.zeros((1, C)), np.cumsum(seg, 0)], 0)
            for q in range(C):
                tgt = np.linspace(0, L[-1, q], K + 1)
                for k3 in range(3):
                    cols[:, q, k3] = np.interp(tgt, L[:, q], cols[:, q, k3])
            for k in range(1, K):
                p[T.sleeve[s][k]] = cols[k]
        p = D.project(p, 1.0, 2, wv)
        p = constrain(p)
    m = p[T.mirror] * np.array([-1.0, 1, 1])
    p = 0.5 * (p + m)
    if verbose:
        el = np.linalg.norm(p[T.edges[:, 0]] - p[T.edges[:, 1]], axis=1)
        print(f"[shell] verts {T.n}, quads {len(T.quads)}, edge len min/med/max {el.min()*1000:.1f}/{np.median(el)*1000:.1f}/{el.max()*1000:.1f} mm")
    return D, T, p
