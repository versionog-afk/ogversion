"""Trousers: wide straight legs, lofted rings around the posed legs and pelvis (numpy only)."""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from measure import *

PP = dict(M=96, y_hem=0.064, y_top=1.035, crotch_drop=0.028, leg_dy=0.026, top_dy=0.022,
          x_out_hip_ease=0.014, flare=0.004,       # outer side line: straight down from the hip (plus this much at the hem)
          x_in_hem=0.026,                          # inner side line at the hem (gap between the legs = twice this)
          rz_top=0.100, rz_hem=0.104, cz_top=-0.012, cz_hem=0.020,   # half depth and centre of a leg in z (drifts forward over the foot)
          expo=2.3, fold_amp=0.011, clear=0.010, shoe_clear=0.008, ease_hip=0.013, ease_waist=0.008, hem_lip=0.004)

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
    sh = np.load(HERE + '/out/shoes.npz'); shoe_v = sh['v']; shoe_t = sh['t']
    keep = (shoe_v[shoe_t][:, :, 0] > 0).all(1); shoe_t = shoe_t[keep]            # left shoe
    y_shoe_top = float(shoe_v[:, 1].max())
    for y in ys:
        s = (y_c - y) / (y_c - pp['y_hem'])
        x_out = x_hip_out + pp['flare'] * s
        x_in = -0.040 + (pp['x_in_hem'] + 0.040) * smoothstep(s / 0.30) ** 0.8
        cx = (x_out + x_in) / 2; rx = (x_out - x_in) / 2
        cz = pp['cz_top'] + (pp['cz_hem'] - pp['cz_top']) * s; rz = pp['rz_top'] + (pp['rz_hem'] - pp['rz_top']) * s
        n = pp['expo']
        r = (np.abs(np.cos(th) / rx) ** n + np.abs(np.sin(th) / rz) ** n) ** (-1 / n)
        # a few soft vertical folds, growing towards the hem and turning slowly with the height
        A = pp['fold_amp'] * smoothstep((s - 0.10) / 0.55)
        fold = 0.55 * np.cos(3 * th + ph[0] + 0.9 * s) + 0.33 * np.cos(5 * th + ph[1] - 1.4 * s) + 0.12 * np.cos(7 * th + ph[2] + 1.8 * s)
        r = r + A * fold
        env = envelope(section_pts(P, legL_t, y), cx, cz)
        need = np.where(env_at(env, th) > 0, env_at(env, th) + pp['clear'], 0)
        if y < y_shoe_top + 0.03:
            # near the hem the cloth also has to clear the shoe (its upper at this height and a little below)
            es = np.max([envelope(section_pts(shoe_v, shoe_t, yy), cx, cz) for yy in (y - 0.005, y, y + 0.004) if yy > 0.004], 0)
            need = np.maximum(need, np.where(env_at(es, th) > 0, env_at(es, th) + pp['shoe_clear'], 0))
        r = np.maximum(r, circ_smooth(need, 2))
        r = np.maximum(r, need)
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
    # the hem is turned in by a few millimetres, so that the edge reads as thick cloth
    lip_L = idx_L[-1].copy(); lip_R = idx_R[-1].copy()
    if pp.get('hem_lip', 0) > 0:
        cxh, czh = rings[-1][0], rings[-1][1]
        lip_L = np.zeros(M, int); lip_R = np.zeros(M, int)
        for k in range(M):
            p = Lr[-1, k].copy(); dirn = np.array([p[0] - cxh, 0.0, p[2] - czh]); dirn /= np.linalg.norm(dirn)
            p = p - dirn * pp['hem_lip']; p[1] += 0.0015
            lip_L[k] = add(p); lip_R[k] = add(p * [-1, 1, 1])
        for k in range(M):
            k2 = (k + 1) % M
            quads.append([idx_L[-1, k], idx_L[-1, k2], lip_L[k2], lip_L[k]])
            quads.append([idx_R[-1, k], lip_R[k], lip_R[k2], idx_R[-1, k2]])
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
    info = dict(y_crotch=float(y_c), y_top=float(pp['y_top']), y_hem=float(pp['y_hem']), hem_L=[int(i) for i in lip_L], hem_R=[int(i) for i in lip_R], top=prev,
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
