"""Stage A: morph + pose the body, save everything the later stages need to out/figure.npz (metres, Y up, +Z front)."""
import os, sys, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from shape import *

CFG = dict(female=0.85, slim=0.45, lowmuscle=0.25, cup=-0.6,
           extra=[('expression/units/caucasian/eye-left-closure', 0.42), ('expression/units/caucasian/eye-right-closure', 0.42)],   # calm, lowered lids
           arm_abduction=16.0,             # final angle of the upper arm from vertical, degrees
           elbow_flex=14.0,                # final elbow bend
           leg_in=2.6,                     # each leg rotated inwards by this
           body_height=1.652, sole=0.016, zshift=-0.030)

def expr(unit, w):
    return [('expression/units/%s/%s' % (r, unit), w / 3.0) for r in ('caucasian', 'asian', 'african')]

def build(cfg=CFG, verbose=True, arm_t=1.0, frame=None):
    """arm_t: 1 = final relaxed arms, 0 = the base mesh A-pose arms (legs, face and scale stay final). frame = (scale, offset) to reuse."""
    V, G = load_base()
    if os.environ.get('NA2_EXTRA'):
        cfg = dict(cfg); cfg['extra'] = list(cfg['extra']) + [tuple(x) for x in json.loads(os.environ['NA2_EXTRA'])]
    V1 = mix_targets(V, default_mix(cfg['female'], cfg['slim'], cfg['lowmuscle'], cfg['cup']) + list(cfg['extra']))
    rig = Rig(V1); W = load_weights(len(V))
    pose = {}
    Z = np.array([0, 0, 1.0])
    for side, sx in (('L', 1.0), ('R', -1.0)):
        sh = rig.head('upperarm01.' + side); el = rig.head('lowerarm01.' + side); wr = rig.head('wrist.' + side)
        d = el - sh
        ang0 = np.degrees(np.arctan2(sx * d[0], -d[1]))            # abduction in the frontal plane
        total = (ang0 - cfg['arm_abduction']) * arm_t
        # the rotation that brings the left arm down is negative about +Z (x towards 0, y down), mirrored for the right
        sgn = -sx
        pose['clavicle.' + side] = rot(Z, sgn * 1.0 * arm_t)
        pose['shoulder01.' + side] = rot(Z, sgn * 5.5 * arm_t)
        pose['upperarm01.' + side] = rot(Z, sgn * (total - 6.5 * arm_t))
        # elbow: reduce the rest bend to the requested one, about the axis perpendicular to both arm segments
        u = d / np.linalg.norm(d); f = (wr - el) / np.linalg.norm(wr - el)
        ax = np.cross(u, f); ax /= np.linalg.norm(ax)
        bend0 = np.degrees(np.arccos(np.clip(u @ f, -1, 1)))
        pose['lowerarm01.' + side] = rot(ax, (cfg['elbow_flex'] - bend0) * arm_t)
        if verbose: print(side, 'rest abduction %.1f elbow bend %.1f arm_t %.2f' % (ang0, bend0, arm_t))
        # fingers: gentle curl towards the palm
        th = rig.head('finger1-1.' + side); pk = rig.head('finger5-1.' + side); ix = rig.head('finger2-1.' + side)
        hand_dir = ix - wr; hand_dir /= np.linalg.norm(hand_dir)
        width = th - pk
        npalm = np.cross(hand_dir, width); npalm /= np.linalg.norm(npalm)
        if npalm[1] > 0: npalm = -npalm          # in the A-pose the palm looks down / inwards
        curls = {2: (12, 20, 12), 3: (16, 26, 14), 4: (20, 30, 16), 5: (24, 32, 18)}
        mid = rig.tail('finger3-1.' + side) - rig.head('finger3-1.' + side); mid /= np.linalg.norm(mid)
        for k, angs in curls.items():
            for j, a in zip((1, 2, 3), angs):
                b = 'finger%d-%d.%s' % (k, j, side)
                dd = rig.tail(b) - rig.head(b); dd /= np.linalg.norm(dd)
                axf = np.cross(dd, npalm); axf /= np.linalg.norm(axf)
                R = rot(axf, a)
                if j == 1 and k != 3:
                    # close the fan of the fingers a little: turn towards the middle finger about the palm normal
                    dp = dd - (dd @ npalm) * npalm; mp_ = mid - (mid @ npalm) * npalm
                    sgn_ang = np.degrees(np.arctan2(np.cross(dp, mp_) @ npalm, dp @ mp_))
                    R = R @ rot(npalm, cfg.get('finger_close', 0.55) * sgn_ang)
                pose[b] = R
        # thumb: slight curl
        for j, a in zip((2, 3), (8, 10)):
            b = 'finger1-%d.%s' % (j, side)
            dd = rig.tail(b) - rig.head(b); dd /= np.linalg.norm(dd)
            axf = np.cross(dd, npalm); axf /= np.linalg.norm(axf)
            pose[b] = rot(axf, a)
        # legs a little closer
        pose['upperleg01.' + side] = rot(Z, -sx * -cfg['leg_in'] * -1.0)
        pose['foot.' + side] = rot(Z, sx * -cfg['leg_in'] * -1.0)
    Vp, joint, Gm, has = skin(V1, rig, pose, W)
    # corrective smoothing where the arm blends into the torso (shoulder cap, armpit folds)
    n = len(V1); wa = np.zeros(n)
    for b, (i, x) in W.items():
        if b.startswith(('upperarm', 'shoulder01', 'lowerarm')): np.add.at(wa, i, x)
    mask = np.clip(4 * wa * (1 - wa), 0, 1) * (V1[:, 1] > rig.head('spine02')[1])
    q = G['body']; nb = [[] for _ in range(n)]
    for f in q:
        for a, b in zip(f, np.roll(f, -1)):
            nb[a].append(b); nb[b].append(a)
    idx = np.array([i for i in np.where(mask > 0.02)[0] if nb[i]])
    for _ in range(cfg.get('corrective_iters', 3)):
        avg = np.array([Vp[nb[i]].mean(0) for i in idx])
        Vp[idx] += 0.5 * mask[idx, None] * (avg - Vp[idx])
    # to metres, feet on the sole plane
    bi = np.unique(G['body'])
    h = Vp[bi, 1].max() - Vp[bi, 1].min()
    sc = cfg['body_height'] / h
    off = np.array([0, -Vp[bi, 1].min() * sc + cfg['sole'], cfg['zshift']])
    if frame is not None: sc, off = frame
    P = Vp * sc + off
    J = {}
    for b in rig.bones:
        J[b] = (joint(b, 'head') * sc + off, joint(b, 'tail') * sc + off)
    return dict(P=P, G=G, J=J, W=W, sc=sc, off=off, rest=V1 * sc + off)

if __name__ == '__main__':
    r = build()
    P, G, J = r['P'], r['G'], r['J']
    bi = np.unique(G['body'])
    print('bbox', P[bi].min(0).round(3), P[bi].max(0).round(3))
    for b in ['upperarm01.L', 'lowerarm01.L', 'wrist.L', 'finger3-3.L', 'upperleg01.L', 'lowerleg01.L', 'foot.L', 'neck01', 'head']:
        print(b, J[b][0].round(3), J[b][1].round(3))
    # arm animation for draping: the same body with the arms going from the A-pose (t = 0) down to the final pose (t = 1)
    ts = np.linspace(0, 1, 9)
    frames = [build(verbose=False, arm_t=t, frame=(r['sc'], r['off']))['P'] for t in ts]
    np.savez(os.path.join(HERE, 'out', 'figure.npz'), P=P, rest=r['rest'], anim=np.array(frames), anim_t=ts,
             jn=np.array(list(J.keys())), jh=np.array([J[k][0] for k in J]), jt=np.array([J[k][1] for k in J]))
    print('max diff last frame vs final', np.abs(frames[-1] - P).max())
    # quick look GLB: body + eyeballs
    from glbw import GLB, angle_weighted_normals
    g = GLB()
    m = g.add_material({"name": "Skin", "pbrMetallicRoughness": {"baseColorFactor": [0.84, 0.81, 0.76, 1], "metallicFactor": 0, "roughnessFactor": 0.62}})
    q = np.concatenate([G['body'], G['helper-l-eye'], G['helper-r-eye']])
    v, f, _ = compact(P, q); t = quads_to_tris(f)
    g.add_mesh('Body', m, v, angle_weighted_normals(v, t), t)
    g.write(os.path.join(HERE, 'out', 'look.glb'))
