"""Landmarks and region masks measured on the posed body (metres)."""
import os, sys, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

ARM = ['upperarm', 'lowerarm', 'wrist', 'finger', 'metacarpal']
ARMSH = ARM + ['shoulder01']
LEG = ['upperleg', 'lowerleg', 'foot', 'toe']
HEADB = ['head', 'jaw', 'neck', 'eye', 'oris', 'levator', 'oculi', 'orbicularis', 'risorius', 'special', 'tongue']

def load():
    d = np.load(os.path.join(HERE, 'out', 'figure.npz'))
    V, G = load_base()
    J = {str(n): (h, t) for n, h, t in zip(d['jn'], d['jh'], d['jt'])}
    W = load_weights(len(V))
    return d['P'], G, J, W

def wsum(W, n, prefixes, side=None):
    w = np.zeros(n)
    for b, (i, x) in W.items():
        if any(b.startswith(p) for p in prefixes) and (side is None or b.endswith('.' + side)):
            np.add.at(w, i, x)
    return w

def edges_of(faces):
    f = np.asarray(faces); k = f.shape[1]
    e = np.concatenate([f[:, [i, (i + 1) % k]] for i in range(k)]); e.sort(1)
    return np.unique(e, axis=0)

def cut(P, edges, normal=(0, 1, 0), d=0.0):
    """intersection points of mesh edges with the plane normal . p = d"""
    nrm = np.asarray(normal, float); nrm = nrm / np.linalg.norm(nrm)
    s = P @ nrm - d
    a, b = edges[:, 0], edges[:, 1]
    m = (s[a] < 0) != (s[b] < 0)
    a, b = a[m], b[m]
    t = s[a] / (s[a] - s[b])
    return P[a] + t[:, None] * (P[b] - P[a])

def components_at(P, tris, y):
    """connected loops of the cross-section y = const: list of point arrays"""
    s = P[:, 1] - y
    st = s[tris] < 0
    crossing = st.any(1) & ~st.all(1)
    t = tris[crossing]
    # each crossing triangle has exactly two crossed edges -> a segment; link by shared edges
    parent = {}
    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    pts = {}
    for tri in t:
        es = []
        for i in range(3):
            a, b = int(tri[i]), int(tri[(i + 1) % 3])
            if (s[a] < 0) != (s[b] < 0):
                k = (min(a, b), max(a, b)); es.append(k)
                if k not in pts:
                    tt = s[a] / (s[a] - s[b]); pts[k] = P[a] + tt * (P[b] - P[a])
        if len(es) == 2:
            parent[find(es[0])] = find(es[1])
    comps = {}
    for k in pts:
        comps.setdefault(find(k), []).append(pts[k])
    return [np.array(v) for v in comps.values()]

def hull_perimeter(xy):
    """tape-measure length around a set of 2D points (convex hull, monotone chain)"""
    p = np.unique(np.round(np.asarray(xy, float), 6), axis=0)
    if len(p) < 3: return 0.0
    p = p[np.lexsort((p[:, 1], p[:, 0]))]
    def half(pts):
        h = []
        for q in pts:
            while len(h) >= 2 and (h[-1][0] - h[-2][0]) * (q[1] - h[-2][1]) - (h[-1][1] - h[-2][1]) * (q[0] - h[-2][0]) <= 0: h.pop()
            h.append(q)
        return h
    hull = half(p)[:-1] + half(p[::-1])[:-1]
    hull = np.array(hull)
    return float(np.linalg.norm(hull - np.roll(hull, -1, 0), axis=1).sum())

def masks(P, G, W):
    n = len(P)
    body = np.zeros(n, bool); body[np.unique(G['body'])] = True
    warm = wsum(W, n, ARMSH); whead = wsum(W, n, HEADB); wleg = wsum(W, n, LEG)
    warm_only = wsum(W, n, ARM)
    q = G['body']
    return dict(body=body, warm=warm, warm_only=warm_only, whead=whead, wleg=wleg, q=q,
                wlegL=wsum(W, n, LEG, 'L'), wlegR=wsum(W, n, LEG, 'R'))

def landmarks(P, G, J, W):
    M = masks(P, G, W); q = M['q']; body = M['body']
    torso_v = body & (M['warm'] < 0.5)
    tq = q[torso_v[q].all(1)]            # torso + head + legs, no arms
    te = edges_of(tq)
    ae = edges_of(q)
    L = {}
    L['units'] = 'metres, Y up, figure faces +Z, wearer left = +X, floor y = 0'
    L['top_of_head_skin'] = P[body][np.argmax(P[body, 1])].tolist()
    for s in 'LR':
        L['shoulder_joint_' + s] = J['upperarm01.' + s][0].tolist()
        L['elbow_' + s] = J['lowerarm01.' + s][0].tolist()
        L['wrist_' + s] = J['wrist.' + s][0].tolist()
        L['hip_joint_' + s] = J['upperleg01.' + s][0].tolist()
        L['knee_' + s] = J['lowerleg01.' + s][0].tolist()
        L['ankle_' + s] = J['foot.' + s][0].tolist()
        L['fingertip_' + s] = J['finger3-3.' + s][1].tolist()
    sh, el, wr = [np.array(L[k + '_L']) for k in ('shoulder_joint', 'elbow', 'wrist')]
    ua = el - sh; fa = wr - el
    L['upper_arm_angle_from_vertical_deg'] = float(np.degrees(np.arctan2(np.hypot(ua[0], ua[2]), -ua[1])))
    L['upper_arm_abduction_deg'] = float(np.degrees(np.arctan2(ua[0], -ua[1])))
    L['forearm_abduction_deg'] = float(np.degrees(np.arctan2(fa[0], -fa[1])))
    L['forearm_forward_deg'] = float(np.degrees(np.arctan2(fa[2], -fa[1])))
    L['elbow_bend_deg'] = float(np.degrees(np.arccos(ua @ fa / np.linalg.norm(ua) / np.linalg.norm(fa))))
    prof = []
    for y in np.arange(0.60, 1.471, 0.01):
        c = cut(P, te, (0, 1, 0), y)
        if len(c) < 6: continue
        mid = c[np.abs(c[:, 0]) < 0.012]
        prof.append(dict(y=round(float(y), 3), half_width=float(np.abs(c[:, 0]).max()), z_front=float(c[:, 2].max()), z_back=float(c[:, 2].min()),
                         z_front_mid=float(mid[:, 2].max()) if len(mid) > 1 else None, z_back_mid=float(mid[:, 2].min()) if len(mid) > 1 else None))
    L['torso_profile'] = prof
    # crotch: slices of the median strip
    cz = None
    for y in np.arange(0.90, 0.60, -0.002):
        c = cut(P, te, (0, 1, 0), y)
        if len(c) and (np.abs(c[:, 0]) < 0.004).sum() == 0 and np.abs(c[:, 0]).min() > 0.004:
            cz = y; break
    L['crotch_height'] = float(cz)
    def best(lo, hi, key, fn):
        c = [p for p in prof if lo <= p['y'] <= hi and p[key] is not None]
        return fn(c, key=lambda p: p[key])
    w = best(0.98, 1.16, 'half_width', min)
    L['waist'] = dict(y=w['y'], half_width=w['half_width'], z_front=w['z_front'], z_back=w['z_back'])
    h = best(0.80, 0.96, 'half_width', max)
    L['hip'] = dict(y=h['y'], width=2 * h['half_width'], depth=h['z_front'] - h['z_back'], z_front=h['z_front'], z_back=h['z_back'])
    b = best(0.80, 0.96, 'z_back', min)
    L['seat_back'] = dict(y=b['y'], z=b['z_back'])
    cf = best(1.14, 1.32, 'z_front', max)
    c = cut(P, te, (0, 1, 0), cf['y']); i = np.argmax(c[:, 2])
    L['chest_front'] = dict(point=[0.0, cf['y'], cf['z_front']], x_of_max=float(abs(c[i, 0])), z_on_midline=cf['z_front_mid'], half_width=cf['half_width'])
    ub = best(1.20, 1.40, 'z_back', min)
    c = cut(P, te, (0, 1, 0), ub['y']); i = np.argmin(c[:, 2])
    L['upper_back'] = dict(point=[0.0, ub['y'], ub['z_back']], x_of_min=float(abs(c[i, 0])), z_on_midline=ub['z_back_mid'])
    for sgn, s_ in ((1, 'L'), (-1, 'R')):
        j = J['upperarm01.' + s_][0]
        near = body & (np.abs(P[:, 0] - j[0]) < 0.012) & (np.abs(P[:, 2] - j[2]) < 0.03) & (P[:, 1] > j[1])
        L['acromion_' + s_] = P[near][np.argmax(P[near, 1])].tolist()
        reg = body & (P[:, 1] > j[1] - 0.05) & (P[:, 1] < j[1] + 0.03) & (sgn * P[:, 0] > 0)
        L['deltoid_outer_' + s_] = P[reg][np.argmax(sgn * P[reg, 0])].tolist()
    # armpit: highest slice where the arm is a loop of its own
    nohead = q[(M['whead'][q] < 0.5).all(1)]
    tris = quads_to_tris(nohead); tris = tris[(P[tris][:, :, 0] > 0.0).any(1)]
    ya = None
    for y in np.arange(1.36, 1.10, -0.002):
        comps = components_at(P, tris, y)
        arm = [c for c in comps if c[:, 0].mean() > 0.13 and len(c) > 5 and c[:, 0].min() > 0.06]
        if arm:
            tor = [c for c in comps if c is not arm[0] and len(c) > 8]
            ya = y; break
    a = arm[0]; t = np.concatenate(tor)
    ia = np.argmin(a[:, 0]); it = np.argmin(np.linalg.norm(t - a[ia], axis=1))
    ap = (a[ia] + t[it]) / 2; ap[1] = ya
    L['armpit_L'] = ap.tolist(); L['armpit_R'] = (ap * [-1, 1, 1]).tolist()
    # neck base: tilted plane through the pit of the neck (front) and the base of the neck at the back (C7)
    pm = {p['y']: p for p in prof}
    yf = float(J['neck01'][0][1]) - 0.029; yb = yf + 0.030      # pit of the neck sits 29 mm below the first neck joint on this mesh
    F = np.array([0, yf, np.interp(yf, [p['y'] for p in prof if p['z_front_mid'] is not None], [p['z_front_mid'] for p in prof if p['z_front_mid'] is not None])])
    Bk = np.array([0, yb, np.interp(yb, [p['y'] for p in prof if p['z_back_mid'] is not None], [p['z_back_mid'] for p in prof if p['z_back_mid'] is not None])])
    t = Bk - F; nrm = np.array([0, -t[2], t[1]]); nrm /= np.linalg.norm(nrm)
    if nrm[1] < 0: nrm = -nrm
    c = cut(P, te, nrm, nrm @ F)
    c = c[np.abs(c[:, 0]) < 0.13]
    cen = (F + Bk) / 2
    ex = np.array([1.0, 0, 0]); ez = np.cross(ex, nrm); c0_neck = np.stack([(c - cen) @ ex, (c - cen) @ ez], 1)
    order = np.argsort(np.arctan2(c0_neck[:, 1], c0_neck[:, 0])); loop = c[order][::max(1, len(c) // 32)]
    sidez = c[np.argmax(c[:, 0])]
    L['neck_base'] = dict(center=cen.tolist(), plane_normal=nrm.tolist(), front=F.tolist(), back=Bk.tolist(),
                          radius_mean=float(np.linalg.norm(c - cen, axis=1).mean()), radius_x=float(np.abs(c[:, 0]).max()), radius_z=float(np.linalg.norm(Bk - F) / 2),
                          loop=np.round(loop, 4).tolist(),
                          note='plane through the pit of the neck and the base of the back of the neck; the cross-section includes the trapezius slopes, so radius_x is the width at shoulder-line level')
    for nm, yy in (('neck_column_low', 1.43), ('neck_column_mid', 1.455)):
        c = cut(P, te, (0, 1, 0), yy)
        L[nm] = dict(y=yy, center=[0.0, yy, float((c[:, 2].max() + c[:, 2].min()) / 2)], radius_x=float(np.abs(c[:, 0]).max()), radius_z=float((c[:, 2].max() - c[:, 2].min()) / 2))
    # side neck point (where the shoulder line leaves the neck): the trapezius ridge point at x = neck column radius + 1 cm
    xs = L['neck_column_low']['radius_x'] + 0.012
    ridge = []
    for sx in (xs,):
        c = cut(P, te, (1, 0, 0), sx); c = c[(c[:, 1] > 1.30) & (c[:, 1] < 1.47)]
        i = np.argmax(c[:, 1]); ridge = c[i]
    L['side_neck_L'] = ridge.tolist(); L['side_neck_R'] = (ridge * [-1, 1, 1]).tolist()
    # shoulder line seen from the front: the top of the body for each x, from the neck out over the deltoid
    ne = edges_of(q[(M['whead'][q] < 0.5).all(1)])
    line = []
    for x in np.arange(0.05, 0.2301, 0.005):
        c = cut(P, ne, (1, 0, 0), x); c = c[c[:, 1] > 1.15]
        if len(c): line.append(c[np.argmax(c[:, 1])])
    line = np.array(line)
    L['shoulder_line_L'] = np.round(line, 4).tolist()
    sl = np.degrees(np.arctan2(-(line[2:, 1] - line[:-2, 1]), line[2:, 0] - line[:-2, 0])); xm = line[1:-1, 0]
    i45 = np.where(sl > 45)[0][0]
    sp = line[1:-1][i45]
    L['shoulder_point_L'] = sp.tolist(); L['shoulder_point_R'] = (sp * [-1, 1, 1]).tolist()
    seg = (xm > ridge[0] + 0.01) & (xm < 0.15)
    L['shoulder_slope_deg'] = float(np.mean(sl[seg]))
    L['shoulder_width_at_shoulder_points'] = float(2 * sp[0])
    L['shoulder_width_deltoid'] = float(2 * L['deltoid_outer_L'][0])
    # left arm cross-sections: where the arm is, next to the torso (for sleeve and side-seam clearances)
    armq = q[(M['warm_only'][q] >= 0.5).all(1) & (P[q][:, :, 0] > 0).all(1)]; aedges = edges_of(armq)
    tab = []
    for y in np.arange(0.74, 1.301, 0.02):
        c = cut(P, aedges, (0, 1, 0), y)
        t = cut(P, te, (0, 1, 0), y)
        if len(c) < 4: continue
        tab.append(dict(y=round(float(y), 3), arm_x_inner=float(c[:, 0].min()), arm_x_outer=float(c[:, 0].max()), arm_z_back=float(c[:, 2].min()), arm_z_front=float(c[:, 2].max()),
                        torso_half_width=float(np.abs(t[:, 0]).max()) if len(t) else None))
    L['arm_L_sections'] = tab
    # tape measures (convex girths of the body without the arms) and lengths, for pattern making
    def girth(y): return hull_perimeter(cut(P, te, (0, 1, 0), y)[:, [0, 2]])
    gy = {p['y']: girth(p['y']) for p in prof if 0.80 <= p['y'] <= 1.32}
    L['girths'] = dict(chest=girth(L['chest_front']['point'][1]), waist=girth(L['waist']['y']),
                       hip=max(v for y, v in gy.items() if y <= 0.96), hip_y=max((v, y) for y, v in gy.items() if y <= 0.96)[1],
                       neck_base=hull_perimeter(c0_neck), note='metres; tape-measure girths of the bare body (no ease)')
    armq2 = edges_of(q[(M['warm_only'][q] >= 0.5).all(1) & (P[q][:, :, 0] > 0).all(1)])
    sh, el, wr = [np.array(L[k + '_L']) for k in ('shoulder_joint', 'elbow', 'wrist')]
    def arm_girth(c, axis):
        pts = cut(P, armq2, axis, axis @ c); pts = pts[np.linalg.norm(pts - c, axis=1) < 0.09]
        u = np.cross(axis, [0, 0, 1.0]); u /= np.linalg.norm(u); w = np.cross(axis, u)
        return hull_perimeter(np.stack([pts @ u, pts @ w], 1))
    ua = (el - sh) / np.linalg.norm(el - sh); fa = (wr - el) / np.linalg.norm(wr - el)
    L['arm'] = dict(upper_arm_length=float(np.linalg.norm(el - sh)), forearm_length=float(np.linalg.norm(wr - el)),
                    shoulder_point_to_elbow=float(np.linalg.norm(el - np.array(L['shoulder_point_L']))),
                    upper_arm_girth=arm_girth((sh + el) / 2, ua), elbow_girth=arm_girth(el, (ua + fa) / np.linalg.norm(ua + fa)),
                    wrist_girth=arm_girth(wr, fa), upper_arm_axis_L=ua.tolist(), forearm_axis_L=fa.tolist())
    nbk = np.array(L['neck_base']['back'])
    L['lengths'] = dict(back_neck_to_waist=float(nbk[1] - L['waist']['y']), back_neck_to_hip=float(nbk[1] - L['hip']['y']),
                        back_neck_to_crotch=float(nbk[1] - L['crotch_height']), back_neck_to_floor=float(nbk[1]),
                        side_neck_to_shoulder_point=float(np.linalg.norm(np.array(L['side_neck_L']) - np.array(L['shoulder_point_L']))),
                        across_back_at_armpit_height=float(2 * np.interp(L['armpit_L'][1], [p['y'] for p in prof], [p['half_width'] for p in prof])))
    L['notes'] = {'acromion': 'surface point straight above the shoulder joint', 'shoulder_point': 'where the front silhouette of the shoulder turns 45 degrees down into the arm',
                  'armpit': 'highest point of the gap between arm and torso', 'side_neck': 'on the shoulder ridge 12 mm outside the neck column',
                  'torso_profile': 'cross-sections every 1 cm of the body without the arms (legs included below the crotch)'}
    return L, M

if __name__ == '__main__':
    P, G, J, W = load()
    L, M = landmarks(P, G, J, W)
    for k, v in L.items():
        if k != 'torso_profile': print(k, np.round(v, 3) if isinstance(v, list) else ({a: (np.round(b, 3).tolist() if not isinstance(b, str) else b) for a, b in v.items()} if isinstance(v, dict) else v))
    for p in L['torso_profile'][::2]:
        print({k: (round(v, 3) if v is not None else None) for k, v in p.items()})
