"""Procedural ghost mannequin (collision body only, never exported): lofted torso + neck with static shoulder
balls, and two separate arms that rotate about the shoulder joints. Garment frame (y up, z front)."""
import math
import numpy as np

def torso_sections(P):
    """y, half width a, half depth b, z centre, superellipse exponent. The shoulder girdle follows the joint."""
    jx, jy = P.jx, P.jy
    top = jy + P.arm_r + 0.002             # top of the shoulder
    nb = (0.064, 0.737)                    # neck base point of the trapezius line
    def trap(y):
        return nb[0] + (nb[1] - y) / (nb[1] - top) * (jx + 0.004 - nb[0])
    return [
        (-0.30, 0.150, 0.092, 0.000, 2.3),
        (-0.10, 0.168, 0.102, -0.002, 2.3),
        (0.05, 0.176, 0.108, -0.004, 2.4),
        (0.16, 0.166, 0.104, -0.002, 2.4),
        (0.27, 0.150, 0.098, 0.001, 2.4),
        (0.36, 0.158, 0.101, 0.003, 2.4),
        (0.45, 0.174, 0.106, 0.005, 2.6),
        (0.52, 0.186, 0.108, 0.006, 2.9),
        (jy - 0.065, jx - 0.029, 0.106, 0.004, 3.0),
        (jy - 0.015, jx - 0.012, 0.098, -0.003, 3.0),
        (jy + 0.025, jx - 0.004, 0.080, -0.011, 2.6),
        (jy + 0.045, jx + 0.000, 0.066, -0.014, 2.3),
        (top, jx + 0.004, 0.052, -0.016, 2.0),
        (0.5 * (top + 0.725), trap(0.5 * (top + 0.725)), 0.046, -0.016, 2.0),
        (0.725, trap(0.725), 0.040, -0.013, 2.0),
        (0.737, 0.064, 0.038, -0.010, 2.0),
        (0.755, 0.046, 0.036, -0.007, 2.0),
        (0.790, 0.040, 0.036, -0.004, 2.0),
        (0.900, 0.038, 0.036, 0.000, 2.0),
    ]


def _smooth(v, n=2):
    for _ in range(n):
        v = np.concatenate([[v[0]], (v[:-2] + 2 * v[1:-1] + v[2:]) / 4, [v[-1]]])
    return v


def _loft(rings, cap=True):
    """rings (m, n, 3): closed rings stacked along the loft. Returns verts, faces (list of tuples)."""
    m, n, _ = rings.shape
    verts = rings.reshape(-1, 3)
    faces = []
    for j in range(m - 1):
        for i in range(n):
            i1 = (i + 1) % n
            faces.append((j * n + i, j * n + i1, (j + 1) * n + i1, (j + 1) * n + i))
    if cap:
        c0 = rings[0].mean(0)
        c1 = rings[-1].mean(0)
        verts = np.concatenate([verts, [c0, c1]])
        i0, i1c = m * n, m * n + 1
        for i in range(n):
            i1 = (i + 1) % n
            faces.append((i0, i1, i))
            faces.append((i1c, (m - 1) * n + i, (m - 1) * n + i1))
    return verts, faces


def _orient(verts, faces):
    vol = 0.0
    for f in faces:
        a = verts[f[0]]
        for k in range(1, len(f) - 1):
            vol += np.dot(a, np.cross(verts[f[k]], verts[f[k + 1]]))
    if vol < 0:
        faces = [tuple(reversed(f)) for f in faces]
    return faces


def torso_mesh(P, nseg=72, dy=0.006):
    t = np.array(torso_sections(P))
    ys = np.arange(t[0, 0], t[-1, 0] + 1e-9, dy)
    a = _smooth(np.interp(ys, t[:, 0], t[:, 1]), 3)
    b = _smooth(np.interp(ys, t[:, 0], t[:, 2]), 3)
    zc = _smooth(np.interp(ys, t[:, 0], t[:, 3]), 3)
    ex = np.interp(ys, t[:, 0], t[:, 4])
    th = np.linspace(0, 2 * np.pi, nseg, endpoint=False)
    rings = np.empty((len(ys), nseg, 3))
    for k in range(len(ys)):
        c, s = np.cos(th), np.sin(th)
        e = 2.0 / ex[k]
        rings[k, :, 0] = a[k] * np.sign(s) * np.abs(s) ** e
        rings[k, :, 2] = zc[k] + b[k] * np.sign(c) * np.abs(c) ** e
        rings[k, :, 1] = ys[k]
    v, f = _loft(rings)
    f = _orient(v, f)
    parts = [(v, f)]
    # static shoulder balls (fill the joint when the arms rotate)
    for sgn in (1, -1):
        sv, sf = sphere_mesh(np.array([sgn * P.jx, P.jy, P.jz]), P.arm_r + 0.001, 20, 14)
        parts.append((sv, sf))
    return merge(parts)


def sphere_mesh(c, r, nu=20, nv=12):
    rings = []
    for k in range(1, nv):
        ph = math.pi * k / nv
        th = np.linspace(0, 2 * np.pi, nu, endpoint=False)
        rings.append(np.stack([r * math.sin(ph) * np.cos(th), np.full(nu, r * math.cos(ph)), r * math.sin(ph) * np.sin(th)], 1))
    rings = np.array(rings) + c
    v, f = _loft(rings)
    v[-2] = c + np.array([0, r, 0])
    v[-1] = c - np.array([0, r, 0])
    return v, _orient(v, f)


def arm_dir(alpha, fwd, sgn=1.0):
    return np.array([sgn * math.sin(alpha), -math.cos(alpha) * math.cos(fwd), math.cos(alpha) * math.sin(fwd)])


def arm_mesh(P, direction, sgn=1.0, nseg=28):
    """Arm as a tapered capsule from the shoulder joint, in world (garment) coordinates."""
    J = np.array([sgn * P.jx, P.jy, P.jz])
    d = direction / np.linalg.norm(direction)
    e1 = np.cross(d, [0, 0, 1.0])
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(d, e1)
    st = np.array([0.0, 0.06, 0.16, 0.30, 0.36, 0.60])
    rr = np.array([P.arm_r, P.arm_r, 0.049, 0.043, 0.041, 0.034])
    s = np.arange(0, 0.6001, 0.01)
    r = _smooth(np.interp(s, st, rr), 2)
    th = np.linspace(0, 2 * np.pi, nseg, endpoint=False)
    rings = []
    # start cap (hemisphere), tube, end cap
    for k in range(6, 0, -1):
        a = (math.pi / 2) * k / 7
        rings.append(J - d * r[0] * math.sin(a) + r[0] * math.cos(a) * (np.cos(th)[:, None] * e1 + np.sin(th)[:, None] * e2))
    for sk, rk in zip(s, r):
        rings.append(J + d * sk + rk * (np.cos(th)[:, None] * e1 + np.sin(th)[:, None] * e2))
    for k in range(1, 7):
        a = (math.pi / 2) * k / 7
        rings.append(J + d * (s[-1] + r[-1] * math.sin(a)) + r[-1] * math.cos(a) * (np.cos(th)[:, None] * e1 + np.sin(th)[:, None] * e2))
    v, f = _loft(np.array(rings))
    return v, _orient(v, f)


def merge(parts):
    vs, fs, off = [], [], 0
    for v, f in parts:
        vs.append(v)
        fs += [tuple(int(i) + off for i in face) for face in f]
        off += len(v)
    return np.concatenate(vs), fs


def tri_faces(faces):
    out = []
    for f in faces:
        for k in range(1, len(f) - 1):
            out.append((f[0], f[k], f[k + 1]))
    return np.array(out)


class Collider:
    """Signed distance queries against a set of closed meshes (union)."""

    def __init__(self, parts):
        import bpy  # noqa: F401 (makes mathutils importable)
        from mathutils.bvhtree import BVHTree
        self.trees = [BVHTree.FromPolygons([tuple(map(float, p)) for p in v], [tuple(f) for f in f_]) for v, f_ in parts]

    def signed(self, pts):
        """Returns (signed distance, outward direction) for each point (union of the parts)."""
        best = np.full(len(pts), 1e9)
        dirs = np.zeros((len(pts), 3))
        for tr in self.trees:
            for i, p in enumerate(pts):
                loc, nrm, idx, dist = tr.find_nearest((float(p[0]), float(p[1]), float(p[2])))
                if loc is None:
                    continue
                v = np.array(p) - np.array(loc)
                s = 1.0 if np.dot(v, nrm) >= 0 else -1.0
                sd = s * dist
                if sd < best[i]:
                    best[i] = sd
                    dirs[i] = (v / dist * s) if dist > 1e-7 else np.array(nrm)
        return best, dirs

    def push_out(self, pts, clearance, movable=None, iters=3):
        pts = pts.copy()
        for _ in range(iters):
            sd, dr = self.signed(pts)
            m = sd < clearance
            if movable is not None:
                m &= movable
            if not m.any():
                break
            pts[m] += dr[m] * (clearance - sd[m])[:, None]
        return pts
