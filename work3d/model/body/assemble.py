"""Stage C: cut the hidden skin, add eyes, hair, trousers, shoes; write body.glb, collide.obj (+ arm animation),
landmarks.json and out/body_uncut.glb. Other stages can import this module: figure_meshes(), add_figure(), CUT."""
import os, sys, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from measure import *
import pants as pantsmod
from glbw import GLB, angle_weighted_normals

CUT = dict(neck_keep_radius=0.120, neck_keep_depth=0.060,     # skin kept around the collar opening
           arm_keep_from_joint=0.055,                           # upper arm deleted above this distance from the shoulder joint
           scalp_margin=0.008,                                  # skin kept under the edge of the hair
           sock_top=0.21, sock_margin=0.012, sock_offset=0.0015)  # dark ankle ("sock") inside the trouser leg, part of the Shoes mesh
# Why the cut is generous: light skin that stays behind dark cloth shows up as single bright pixels along its silhouette in
# the WebGL viewer (edge-on triangles get unreliable depth values). So no skin is kept under the trousers at all, and the
# garment stage should keep only a short margin of skin inside the collar and the sleeves.
INFLATE = 0.0025

def hidden_field(P, M, J, L, body_m, cut=CUT):
    """per-vertex field, positive where the skin is hidden by clothes, hair or shoes; the body is cut along its zero level.
    The garment stage can call this with other margins (see standin.py) or add its own field with np.maximum."""
    n = len(P)
    arm = M['warm_only'] >= 0.5
    head = M['whead'] >= 0.5
    nb = L['neck_base']; c = np.array(nb['center']); nrm = np.array(nb['plane_normal'])
    below = (P - c) @ nrm                       # signed height over the neck base plane
    horiz = np.linalg.norm((P - c) - np.outer(below, nrm), axis=1)
    f_neck = np.maximum(-cut['neck_keep_depth'] - below, horiz - cut['neck_keep_radius'])     # < 0 in the skin kept around the collar opening
    # torso and legs: hidden, except around the collar opening
    h = f_neck.copy()
    # arms: the shoulder cap and the top of the upper arm are hidden
    for s in 'LR':
        sh = np.array(L['shoulder_joint_' + s]); el = np.array(L['elbow_' + s]); ax = (el - sh) / np.linalg.norm(el - sh)
        side = (P[:, 0] > 0) if s == 'L' else (P[:, 0] < 0)
        t = (P - sh) @ ax
        m = arm & side
        h[m] = np.minimum(cut['arm_keep_from_joint'] - t, f_neck)[m]
    # head: everything stays, except the scalp under the hair
    h[head] = (body_m - cut['scalp_margin'])[head]
    return h

def mat(g, name, col, rough, ds=False, blend=False):
    m = {"name": name, "pbrMetallicRoughness": {"baseColorFactor": col, "metallicFactor": 0.0, "roughnessFactor": rough}}
    if ds: m["doubleSided"] = True
    if blend: m["alphaMode"] = "BLEND"
    return g.add_material(m)

def figure_meshes(hidden=None):
    """returns the four figure meshes {name: (verts, normals, tris)}, the landmarks, the uncut body and the trousers.
    hidden: optional function (P, field, M, L) -> field, to hide more or less skin than CUT does (positive = hidden),
    e.g. the garment stage can add "deep inside the shirt" computed from the draped cloth."""
    P, G, J, W = load(); L, M = landmarks(P, G, J, W)
    hair = np.load(HERE + '/out/hair.npz'); shoes = np.load(HERE + '/out/shoes.npz')
    pv, pq, pinfo = pantsmod.build(P, G, J, W, L)
    q = M['q']
    # body normals are computed on the full mesh so that the cut borders shade like the uncut surface
    full_t = quads_to_tris(q)
    Nfull = np.zeros_like(P); Nfull[:] = angle_weighted_normals(P, full_t)
    hid = hidden_field(P, M, J, L, hair['body_m'])
    if hidden is not None: hid = hidden(P, hid, M, L)
    bv, bn, bt = clip_tris(P, Nfull, full_t, hid)
    # eyes: plain spheres at the eyeball helpers
    parts_v = [bv]; parts_n = [bn]; parts_t = [bt]; off = len(bv)
    for gname in ('helper-l-eye', 'helper-r-eye'):
        gi = np.unique(G[gname]); c = P[gi].mean(0); r = np.linalg.norm(P[gi] - c, axis=1).mean()
        ev, et = uv_sphere(c, r * 0.985, 18, 12)
        parts_v.append(ev); parts_n.append((ev - c) / np.linalg.norm(ev - c, axis=1, keepdims=True)); parts_t.append(et + off); off += len(ev)
        L['eye_' + ('L' if 'l-eye' in gname else 'R')] = c.tolist()
    body = (np.concatenate(parts_v), np.concatenate(parts_n), np.concatenate(parts_t))
    hv, ht, hn = autosmooth(hair['v'], hair['t'], 55)
    sv, st, sn = autosmooth(shoes['v'], shoes['t'], 48)
    # socks: the ankles between shoe and trouser leg in the shoe material (only ever seen from below the hem)
    y0 = float(shoes['collar']) - CUT['sock_margin']
    sock_f = np.maximum(P[:, 1] - CUT['sock_top'], y0 - P[:, 1]); sock_f[M['warm'] >= 0.5] = 1.0
    kv, kn, kt = clip_tris(P + Nfull * CUT['sock_offset'], Nfull, full_t, sock_f)
    st = np.concatenate([st, kt + len(sv)]); sv = np.concatenate([sv, kv]); sn = np.concatenate([sn, kn])
    pv_s, pt, pn = autosmooth(pv, quads_to_tris(pq), 62)          # smooth cloth, hard edge only at the turned-in hem
    L['top_of_head'] = hair['v'][np.argmax(hair['v'][:, 1])].tolist()
    L['hair_bbox'] = [hair['v'].min(0).tolist(), hair['v'].max(0).tolist()]
    sec = []
    for y in np.arange(0.70, pinfo['y_top'] + 1e-6, 0.03):
        c = pv[np.abs(pv[:, 1] - y) < 0.012]
        if len(c): sec.append(dict(y=round(float(y), 3), half_width=float(np.abs(c[:, 0]).max()), z_front=float(c[:, 2].max()), z_back=float(c[:, 2].min())))
    L['pants'] = dict(y_top=pinfo['y_top'], y_crotch=pinfo['y_crotch'], y_hem=pinfo['y_hem'], half_width_at_hip=pinfo['x_out_hip'], sections=sec)
    L['figure_height'] = float(max(hair['v'][:, 1].max(), P[M['body'], 1].max()))
    ank = abs(L['ankle_L'][0]) * 2
    L['pose'] = ('relaxed standing, symmetric; upper arms %.0f degrees away from the body, elbows bent %.0f degrees (hands a little forward), '
                 'palms facing the thighs, fingers gently curled; ankle centres %.2f m apart; head straight'
                 % (L['upper_arm_abduction_deg'], L['elbow_bend_deg'], ank))
    full = dict(P=P, q=q, N=Nfull, G=G, J=J, M=M)
    return dict(Body=body, Hair=(hv, hn, ht), Pants=(pv_s, pn, pt), Shoes=(sv, sn, st)), L, full, (pv, pq, pinfo)

def add_figure(g, meshes):
    ms = mat(g, 'Skin', [0.84, 0.81, 0.76, 1], 0.62)
    mh = mat(g, 'Hair', [0.027, 0.022, 0.018, 1], 0.7)
    mp = mat(g, 'Pants', [0.035, 0.034, 0.03, 1], 0.9, ds=True)
    msh = mat(g, 'Shoes', [0.006, 0.006, 0.007, 1], 0.55)
    for name, m in (('Body', ms), ('Hair', mh), ('Pants', mp), ('Shoes', msh)):
        v, n, t = meshes[name]
        g.add_mesh(name, m, v, n, t)

def write_collide(path, full, pants):
    P, q, N = full['P'], full['q'], full['N']
    bv, bf, used = compact(P + N * INFLATE, q)
    pv, pq, pinfo = pants
    cv, ct = pantsmod.closed(pv, pq, pinfo)
    cn = angle_weighted_normals(cv, ct)
    cv = cv + cn * INFLATE
    with open(path, 'w') as f:
        f.write('# NA2 figure collision set: metres, Y up, +Z front. Closed meshes, inflated by %.1f mm.\n' % (INFLATE * 1000))
        f.write('o body\n')
        for v in bv: f.write('v %.5f %.5f %.5f\n' % tuple(v))
        for qd in bf: f.write('f %d %d %d %d\n' % tuple(qd + 1))
        o = len(bv)
        f.write('o pants\n')
        for v in cv: f.write('v %.5f %.5f %.5f\n' % tuple(v))
        for t in ct: f.write('f %d %d %d\n' % tuple(t + 1 + o))
    # the same collision body while the arms come down from the A-pose (frame 0) to the final pose (last frame)
    d = np.load(HERE + '/out/figure.npz'); frames = []
    for Pf in d['anim']:
        Nf = np.zeros_like(Pf); Nf[:] = angle_weighted_normals(Pf, quads_to_tris(q))
        frames.append((Pf + Nf * INFLATE)[used])
    np.savez_compressed(HERE + '/collide_anim.npz', body_frames=np.array(frames, dtype=np.float32), t=d['anim_t'], body_quads=bf.astype(np.int32),
                        pants_verts=cv.astype(np.float32), pants_tris=ct.astype(np.int32))
    write_obj(HERE + '/collide_apose.obj', frames[0], bf, 'body_apose')
    # checks: closed, consistently outward
    def closed(faces):
        k = faces.shape[1]; e = np.concatenate([faces[:, [i, (i + 1) % k]] for i in range(k)])
        key = e[:, 0] * 10 ** 7 + e[:, 1]; rev = e[:, 1] * 10 ** 7 + e[:, 0]
        return len(np.unique(key)) == len(key) and np.isin(rev, key).all()
    def volume(v, t):
        return float(np.einsum('ij,ij->i', v[t[:, 0]], np.cross(v[t[:, 1]], v[t[:, 2]])).sum() / 6)
    print('collide body closed', closed(bf), 'volume %.4f m3' % volume(bv, quads_to_tris(bf)), '| pants closed', closed(ct), 'volume %.4f m3' % volume(cv, ct))
    return len(bv), len(bf), len(cv), len(ct)

if __name__ == '__main__':
    meshes, L, full, pants = figure_meshes()
    for k, (v, n, t) in meshes.items(): print('%-6s verts %6d tris %6d' % (k, len(v), len(t)))
    g = GLB(); add_figure(g, meshes)
    out = HERE + '/body.glb'
    print('body.glb bytes', g.write(out))
    print('collide', write_collide(HERE + '/collide.obj', full, pants))
    # the uncut body (for inspection and for anyone who wants to re-cut with other margins)
    g2 = GLB(); ms = mat(g2, 'Skin', [0.84, 0.81, 0.76, 1], 0.62)
    v, f, used = compact(full['P'], full['q'])
    g2.add_mesh('Body', ms, v, full['N'][used], quads_to_tris(f))
    g2.write(HERE + '/out/body_uncut.glb')
    json.dump(L, open(HERE + '/landmarks.json', 'w'), indent=1)
