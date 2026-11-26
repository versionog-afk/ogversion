"""Trousers: wide straight legs, lofted rings around the posed legs and pelvis (numpy only)."""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from measure import *

PP = dict(M=60, y_hem=0.034, y_top=1.035, crotch_drop=0.028, leg_dy=0.0165, top_dy=0.019,
          x_out_hip_ease=0.014, x_out_hem=0.222, x_in_hem=0.030, rz_top=0.100, rz_hem=0.100, cz_top=-0.012, cz_hem=-0.012,
          expo=2.25, fold_amp=0.0125, clear=0.010, ease_hip=0.013, ease_waist=0.008)

def smoothstep(x):
    x = np.clip(x, 0, 1); return x * x * (3 - 2 * x)

def section_pts(P, tris, y, k=5):
    s = P[:, 1] - y
    st = s[tris] < 0
    t = tris[st.any(1) & ~st.all(1)]
    out = []
    for i in range(3):
        a = t[:, i]; b = t[:, (i + 1) % 3]; c = t[:, (i + 2) % 3]
        # edges (a,b) and (a,c) crossed when a is alone on its side
        alone = ((s[a] < 0) != (s[b] < 0)) & ((s[a] < 0) != (s[c] < 0))
        a, b, c = a[alone], b[alone], c[alone]
        p1 = P[a] + (s[a] / (s[a] - s[b]))[:, None] * (P[b] - P[a])
        p2 = P[a] + (s[a] / (s[a] - s[c]))[:, None] * (P[c] - P[a])
        for u in np.linspace(0, 1, k):
            out.append(p1 * (1 - u) + p2 * u)
    return np.concatenate(out) if out else np.zeros((0, 3))

def envelope(pts, cx, cz, nb=180):
    """max radius of the section points per polar angle bin about (cx, cz); bins without points are filled by neighbours"""
    if len(pts) == 0: return np.zeros(nb)
    a = np.arctan2(pts[:, 2] - cz, pts[:, 0] - cx); r = np.hypot(pts[:, 0] - cx, pts[:, 2] - cz)
    b = np.floor((a % (2 * np.pi)) / (2 * np.pi) * nb).astype(int) % nb
    env = np.zeros(nb); np.maximum.at(env, b, r)
    for _ in range(3):   # dilate so sparse bins are covered
        env = np.maximum(env, np.maximum(np.roll(env, 1), np.roll(env, -1)) * 0.999)
    return env

def env_at(env, theta):
    nb = len(env); b = (theta % (2 * np.pi)) / (2 * np.pi) * nb - 0.5
    i0 = np.floor(b).astype(int); f = b - i0
    return env[i0 % nb] * (1 - f) + env[(i0 + 1) % nb] * f

def circ_smooth(a, it=2):
    for _ in range(it):
        a = 0.25 * np.roll(a, 1, -1) + 0.5 * a + 0.25 * np.roll(a, -1, -1)
    return a

def build(P, G, J, W, L, pp=PP, rng_seed=3):
    Mk = masks(P, G, W); q = Mk['q']
    legL = q[((Mk['wlegL'][q] > 0.3) | ((Mk['warm'][q] < 0.5) & (P[q][:, :, 0] > 0.0) & (P[q][:, :, 1] < 1.0))).all(1) & (Mk['warm'][q] < 0.5).all(1)]
    legL_t = quads_to_tris(legL)
    torso = q[(Mk['warm'][q] < 0.5).all(1)]; torso_t = quads_to_tris(torso)
    M = pp['M']; th = 2 * np.pi * np.arange(M) / M
    y_c = L['crotch_height'] - pp['crotch_drop']
    ys = np.linspace(y_c, pp['y_hem'], int(round((y_c - pp['y_hem']) / pp['leg_dy'])) + 1)
    x_hip_out = L['hip']['width'] / 2 + pp['x_out_hip_ease']
    rings = []
    rs = np.random.RandomState(rng_seed); ph = rs.uniform(0, 2 * np.pi, 4)
    for y in ys:
        s = (y_c - y) / (y_c - pp['y_hem'])
        x_out = x_hip_out + (pp['x_out_hem'] - x_hip_out) * s
        x_in = -0.040 + (pp['x_in_hem'] + 0.040) * smoothstep(s / 0.30) ** 0.8
        cx = (x_out + x_in) / 2; rx = (x_out - x_in) / 2
        cz = pp['cz_top'] + (pp['cz_hem'] - pp['cz_top']) * s; rz = pp['rz_top'] + (pp['rz_hem'] - pp['rz_top']) * s
        n = pp['expo']
        r = (np.abs(np.cos(th) / rx) ** n + np.abs(np.sin(th) / rz) ** n) ** (-1 / n)
        # soft vertical folds, growing towards the hem
        A = pp['fold_amp'] * smoothstep((s - 0.08) / 0.55)
        fold = 0.50 * np.cos(3 * th + ph[0] + 0.9 * s) + 0.35 * np.cos(5 * th + ph[1] - 1.6 * s) + 0.15 * np.cos(8 * th + ph[2] + 2.2 * s)
        # a little break above the shoe
        brk = 0.004 * np.exp(-((y - pp['y_hem'] - 0.05) / 0.035) ** 2) * (0.6 + 0.4 * np.cos(2 * th + ph[3]))
        r = r + A * fold + brk
        if y >= 0.125:
            env = envelope(section_pts(P, legL_t, y), cx, cz)
        else:   # below the ankle the cloth hangs straight, but it still has to clear the instep above the shoe collar
            env = np.max([envelope(section_pts(P, legL_t, yy), cx, cz) for yy in (0.078, 0.09, 0.105, 0.125)], 0)
        need = env_at(env, th) + pp['clear']
        r = np.maximum(r, np.where(env_at(env, th) > 0, need, 0))
        rings.append((cx, cz, r, y))
    # smooth radii along the height a little (keeps folds, removes steps from the enclosure test), then re-apply the enclosure
    R = np.array([r for _, _, r, _ in rings])
    Rs = R.copy()
    for _ in range(2):
        Rs[1:-1] = 0.25 * Rs[:-2] + 0.5 * Rs[1:-1] + 0.25 * Rs[2:]
    R = np.maximum(Rs, R * 0.0 + np.minimum(R, Rs + 0.004))
    Lr = []
    for (cx, cz, _, y), r in zip(rings, R):
        p = np.stack([cx + r * np.cos(th), np.full(M, y), cz + r * np.sin(th)], 1)
        Lr.append(p)
    Lr = np.array(Lr)                                  # (rings, M, 3) left leg, ring 0 at the crotch level
    # inner side: never cross the centre plane; ring 0 clamps to exactly x = 0 (the crotch seam)
    seam = Lr[0, :, 0] <= 0.0
    ks = np.where(seam)[0]; ka, kb = ks.min(), ks.max()
    assert (kb - ka + 1) == len(ks), 'seam must be contiguous'
    Lr[0, seam, 0] = 0.0
    gap = 0.004 * smoothstep(np.arange(len(ys)) / 6.0)
    for j in range(1, len(ys)):
        Lr[j, :, 0] = np.maximum(Lr[j, :, 0], gap[j])
    nL = len(ys)
    # ---- the hem breaks on the shoe: lift each column so that its lower end sits on the shoe upper
    sh = np.load(HERE + '/out/shoes.npz')['v']; sh = sh[sh[:, 0] > 0]
    cell = 0.004; ox, oz = sh[:, 0].min() - 0.02, sh[:, 2].min() - 0.02
    nxg = int((sh[:, 0].max() + 0.02 - ox) / cell) + 1; nzg = int((sh[:, 2].max() + 0.02 - oz) / cell) + 1
    H = np.zeros((nxg, nzg)); np.maximum.at(H, (((sh[:, 0] - ox) / cell).astype(int), ((sh[:, 2] - oz) / cell).astype(int)), sh[:, 1])
    for _ in range(2):
        Hp = np.pad(H, 1); H = np.max([Hp[1:-1, 1:-1], Hp[:-2, 1:-1], Hp[2:, 1:-1], Hp[1:-1, :-2], Hp[1:-1, 2:]], 0)
    def shoe_h(x, z):
        i = ((x - ox) / cell).astype(int); k = ((z - oz) / cell).astype(int)
        ok = (i >= 0) & (i < nxg) & (k >= 0) & (k < nzg)
        out = np.zeros(len(x)); out[ok] = H[i[ok], k[ok]]; return out
    y_ref = 0.36
    lowj = [j for j in range(nL) if ys[j] < 0.12]
    hk = np.max([shoe_h(Lr[j, :, 0], Lr[j, :, 2]) for j in lowj], 0)
    hk = np.maximum(pp['y_hem'], np.where(hk > 0, hk + 0.005, 0))
    hs = hk.copy()
    for _ in range(3):
        hs = np.maximum(hk, 0.25 * np.roll(hs, 1) + 0.5 * hs + 0.25 * np.roll(hs, -1))
    for j in range(nL):
        if ys[j] < y_ref:
            Lr[j, :, 1] = hs + (ys[j] - pp['y_hem']) * (y_ref - hs) / (y_ref - pp['y_hem'])
    # ---- indexing
    verts = []; idx_L = np.zeros((nL, M), int); idx_R = np.zeros((nL, M), int)
    def add(p):
        verts.append(np.asarray(p, float)); return len(verts) - 1
    for j in range(nL):
        for k in range(M):
            idx_L[j, k] = add(Lr[j, k])
    for j in range(nL):
        for k in range(M):
            if j == 0 and seam[k]: idx_R[j, k] = idx_L[j, k]
            else: idx_R[j, k] = add(Lr[j, k] * [-1, 1, 1])
    quads = []
    for j in range(nL - 1):
        for k in range(M):
            k2 = (k + 1) % M
            quads.append([idx_L[j, k], idx_L[j, k2], idx_L[j + 1, k2], idx_L[j + 1, k]])
            quads.append([idx_R[j, k], idx_R[j + 1, k], idx_R[j + 1, k2], idx_R[j, k2]])
    # ---- pelvis tube
    outer_front = list(range(0, ka)); outer_back = list(range(kb + 1, M))
    ring0 = [idx_L[0, k] for k in outer_front] + [idx_L[0, ka]] + [idx_R[0, k] for k in outer_front[::-1]] + [idx_R[0, k] for k in outer_back[::-1]] + [idx_L[0, kb]] + [idx_L[0, k] for k in outer_back]
    N = len(ring0)
    p0 = np.array([verts[i] for i in ring0])
    czp = 0.5 * (p0[:, 2].max() + p0[:, 2].min())
    al = np.arctan2(p0[:, 2] - czp, p0[:, 0]); r0 = np.hypot(p0[:, 0], p0[:, 2] - czp)
    yt = np.linspace(y_c, pp['y_top'], int(round((pp['y_top'] - y_c) / pp['top_dy'])) + 1)[1:]
    prev = ring0; up = []
    for y in yt:
        u = (y - y_c) / (pp['y_top'] - y_c)
        env = circ_smooth(envelope(section_pts(P, torso_t, y), 0.0, czp), 3)
        ease = pp['ease_hip'] + (pp['ease_waist'] - pp['ease_hip']) * u
        rb = env_at(env, al) + ease
        blend = smoothstep((y - y_c) / 0.11)
        r = np.maximum(r0 * (1 - blend) + rb * blend, rb - ease + 0.006)
        up.append(r)
    up = np.array(up)
    for _ in range(2):
        up[1:-1] = np.maximum(up[1:-1], 0.25 * up[:-2] + 0.5 * up[1:-1] + 0.25 * up[2:])
    up = circ_smooth(up, 1)
    rings_top = [ring0]
    for y, r in zip(yt, up):
        cur = [add([r[i] * np.cos(al[i]), y, czp + r[i] * np.sin(al[i])]) for i in range(N)]
        for i in range(N):
            i2 = (i + 1) % N
            quads.append([prev[i], cur[i], cur[i2], prev[i2]])
        prev = cur; rings_top.append(cur)
    V = np.array(verts); Q = np.array(quads)
    info = dict(y_crotch=float(y_c), y_top=float(pp['y_top']), y_hem=float(pp['y_hem']), hem_L=idx_L[-1].tolist(), hem_R=idx_R[-1].tolist(), top=prev,
                x_out_hip=float(x_hip_out))
    return V, Q, info

def closed(V, Q, info):
    """collision version: caps on the hems and the waist (triangle fans)"""
    V = list(V); T = [t for t in quads_to_tris(Q)]
    for loop, flip in ((info['hem_L'], False), (info['hem_R'], True), (info['top'], True)):
        c = np.mean([V[i] for i in loop], 0); ci = len(V); V.append(c)
        for a, b in zip(loop, loop[1:] + loop[:1]):
            T.append([ci, a, b] if not flip else [ci, b, a])
    return np.array(V), np.array(T)

if __name__ == '__main__':
    P, G, J, W = load(); L, _ = landmarks(P, G, J, W)
    V, Q, info = build(P, G, J, W, L)
    print('pants verts', len(V), 'quads', len(Q), 'tris', 2 * len(Q), {k: v for k, v in info.items() if not isinstance(v, list)})
    # orientation check
    t = quads_to_tris(Q); n = np.cross(V[t[:, 1]] - V[t[:, 0]], V[t[:, 2]] - V[t[:, 0]]); c = V[t].mean(1)
    axis_x = np.where(c[:, 1] < info['y_crotch'], np.sign(c[:, 0]) * 0.13, 0.0)
    out = c - np.stack([axis_x, c[:, 1], np.full(len(c), -0.012)], 1)
    print('outward fraction', ((n * out).sum(1) > 0).mean())
    np.savez(HERE + '/out/pants.npz', v=V, q=Q)
