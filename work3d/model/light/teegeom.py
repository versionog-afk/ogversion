"""The cut of the tee as plain geometry: key points and seam curves from the measurements (metres).
Used by pattern_gc.py (which feeds them to GarmentCode / pygarment) and by pattern_own.py (fallback without pygarment).

Flat-lay frame of the body panels: x to the wearer's left (the viewer's right when looking at the front), y up from the hem
(hem y = 0, high point shoulder HPS at y = length). The sleeve is designed in the flat-lay too: its fold (top) line leaves
the shoulder point S at `angle_flat_deg` below the horizontal, so the sleeve cap is the armhole curve itself and the
garment can lie flat with every seam closed - the state the cloth simulation starts from.
Sleeve panel frame: p along the fold line from S to the hem, q across (q > 0 = front half)."""
import math
import numpy as np

KAPPA = 0.5522847498


def bez(p0, p1, p2, p3, n=200):
    t = np.linspace(0, 1, n)[:, None]
    p0, p1, p2, p3 = (np.asarray(p, float) for p in (p0, p1, p2, p3))
    return (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3


def polylen(p):
    return float(np.linalg.norm(np.diff(p, axis=0), axis=1).sum())


def design(M):
    b, n, s = M['body'], M['neck'], M['sleeve']
    L = b['length_hps_to_hem']; W = b['chest_width_flat'] / 2; Wh = b['hem_width_flat'] / 2
    nh = n['width_seam_to_seam'] / 2; xs = b['shoulder_to_shoulder'] / 2
    sig = math.radians(b['shoulder_slope_deg'])
    N = np.array([nh, L]); S = np.array([xs, L - (xs - nh) * math.tan(sig)])
    ad = b['armhole_straight']
    if W - xs >= ad: raise ValueError('armhole_straight is shorter than the horizontal distance shoulder point - side seam')
    U = np.array([W, S[1] - math.sqrt(ad ** 2 - (W - xs) ** 2)])
    al = math.radians(s['angle_flat_deg'])
    ds = np.array([math.cos(al), -math.sin(al)])            # along the sleeve fold line
    dh = np.array([-math.sin(al), -math.cos(al)])           # across the sleeve, towards the underarm
    chord = float(np.linalg.norm(U - S)); k = b.get('armhole_curve', 0.3)
    tU = np.array([math.sin(math.radians(38)), -math.cos(math.radians(38))])
    arm = [S, S + dh * chord * k, U - tU * chord * k * 0.8, U]       # cubic Bezier S -> U; leaves S square to the sleeve fold line
    T = S + ds * s['length_from_shoulder_seam']; H = T + dh * s['opening_flat']
    D = dict(L=L, W=W, Wh=Wh, nh=nh, N=N, S=S, U=U, T=T, H=H, ds=ds, dh=dh, arm=[np.asarray(p, float) for p in arm],
             fd=n['front_drop'], bd=n['back_drop'], rib=n['rib_width'])
    to_pq = lambda P: np.stack([(np.asarray(P) - S) @ ds, (np.asarray(P) - S) @ dh], -1)
    D['to_pq'] = to_pq
    D['sleeve'] = dict(cap=[to_pq(p) for p in arm], U=to_pq(U), H=to_pq(H), T=to_pq(T))
    # neckline: two quarter ellipses per panel, HPS -> centre
    def neck(drop):
        return [np.array([nh, L]), np.array([nh, L - KAPPA * drop]), np.array([nh * KAPPA, L - drop]), np.array([0.0, L - drop])]
    D['neck_front'] = neck(D['fd']); D['neck_back'] = neck(D['bd'])
    D['neck_len'] = 2 * polylen(bez(*D['neck_front'])) + 2 * polylen(bez(*D['neck_back']))
    D['armhole_len'] = polylen(bez(*arm))
    D['collar_len'] = D['neck_len'] * n['rib_length_ratio']
    return D


def report(M):
    """derived dimensions a tape measure would give on the finished shirt"""
    D = design(M); sl = D['sleeve']
    return dict(shoulder_seam=float(np.linalg.norm(D['S'] - D['N'])), armhole_curve_length=D['armhole_len'],
                sleeve_width_at_armhole_flat=float(sl['U'][1]), sleeve_underarm_seam=float(np.linalg.norm(sl['H'] - sl['U'])),
                side_seam=float(np.hypot(D['U'][0] - D['Wh'], D['U'][1])), neckline_seam_length=D['neck_len'],
                collar_band_cut_length=D['collar_len'], hps_to_sleeve_hem=float(np.linalg.norm(D['S'] - D['N'])) + M['sleeve']['length_from_shoulder_seam'],
                centre_back_length=D['L'] - D['bd'], centre_front_length=D['L'] - D['fd'],
                chest_circumference=4 * D['W'], sleeve_opening_circumference=2 * M['sleeve']['opening_flat'])


def panels(M):
    """Panels as loops of named edges. Each edge: (name, start vertex id, end vertex id, bezier control points or None).
    Body panels are in the flat-lay frame, sleeves in their (q, -p) frame (hem at the bottom of the drawing), the collar band
    as a straight strip (cut length x twice the rib width, folded double along its length)."""
    D = design(M); W, Wh, L = D['W'], D['Wh'], D['L']
    mir = np.array([-1.0, 1.0])
    out = {}
    for name, nk in (('front', D['neck_front']), ('back', D['neck_back'])):
        S, N, U = D['S'], D['N'], D['U']; C = nk[3]
        V = [np.array([-Wh, 0.0]), np.array([Wh, 0.0]), U, S, N, C, N * mir, S * mir, U * mir]
        a = D['arm']
        E = [('hem', 0, 1, None), ('side_L', 1, 2, None), ('armhole_L', 2, 3, [a[2], a[1]]), ('shoulder_L', 3, 4, None),
             ('neck_L', 4, 5, [nk[1], nk[2]]), ('neck_R', 5, 6, [nk[2] * mir, nk[1] * mir]), ('shoulder_R', 6, 7, None),
             ('armhole_R', 7, 8, [a[1] * mir, a[2] * mir]), ('side_R', 8, 0, None)]
        out[name] = dict(vertices=V, edges=E, role=name)
    sl = D['sleeve']; f = lambda pq: np.array([pq[1], -pq[0]])          # drawing frame of the sleeve: x = q, y = -p
    cap = [f(c) for c in sl['cap']]; Uq, Hq = f(sl['U']), f(sl['H'])
    for side in ('L', 'R'):
        V = [cap[0], Uq * mir, Hq * mir, Hq, Uq]
        E = [('cap_B', 0, 1, [cap[1] * mir, cap[2] * mir]), ('under_B', 1, 2, None), ('hem', 2, 3, None), ('under_F', 3, 4, None),
             ('cap_F', 4, 0, [cap[2], cap[1]])]
        out['sleeve_' + side] = dict(vertices=[v.copy() for v in V], edges=E, role='sleeve', side=side)
    cl = D['collar_len']; rw = 2 * D['rib']
    V = [np.array([0.0, 0.0]), np.array([cl, 0.0]), np.array([cl, rw]), np.array([0.0, rw])]
    out['collar'] = dict(vertices=V, edges=[('seam', 0, 1, None), ('end_B', 1, 2, None), ('seam_fold', 2, 3, None), ('end_A', 3, 0, None)], role='collar')
    return out, D


# seams: (name, (panel, edge), (panel, edge)).  A list entry on one side = several edges sewn end to end to the other side.
def seams():
    s = []
    for x in 'LR':
        s += [('side_' + x, ('front', 'side_' + x), ('back', 'side_' + x)),
              ('shoulder_' + x, ('front', 'shoulder_' + x), ('back', 'shoulder_' + x)),
              ('armhole_front_' + x, ('front', 'armhole_' + x), ('sleeve_' + x, 'cap_F')),
              ('armhole_back_' + x, ('back', 'armhole_' + x), ('sleeve_' + x, 'cap_B')),
              ('underarm_' + x, ('sleeve_' + x, 'under_F'), ('sleeve_' + x, 'under_B'))]
    # the collar band starts at the wearer's left shoulder seam, runs along the back neck to the right shoulder and returns along the front
    s += [('collar', ('collar', 'seam'), [('back', 'neck_L'), ('back', 'neck_R'), ('front', 'neck_R'), ('front', 'neck_L')]),
          ('collar_close', ('collar', 'end_A'), ('collar', 'end_B'))]
    return s
