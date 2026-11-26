"""Debug helpers: wireframe contact sheets (numpy rasterised lines) and quick GLB dumps."""
import numpy as np


def save_png(path, img):
    import bpy
    h, w = img.shape[:2]
    if img.ndim == 2:
        img = np.repeat(img[:, :, None], 3, 2)
    rgba = np.ones((h, w, 4), np.float32)
    rgba[:, :, :img.shape[2]] = img
    im = bpy.data.images.new("dbg", w, h, alpha=False)
    im.pixels.foreach_set(rgba[::-1].ravel())
    im.filepath_raw = path
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)


def _view_matrix(yaw, pitch):
    cy, sy, cp, sp = np.cos(yaw), np.sin(yaw), np.cos(pitch), np.sin(pitch)
    right = np.array([cy, 0, -sy])
    fwd = np.array([-sy * cp, -sp, -cy * cp])         # camera looks along fwd
    up = np.cross(right, fwd) * -1
    up = np.cross(fwd, right) * -1
    up = np.array([-sy * -sp, cp, -cy * -sp])
    up = np.cross(right, fwd)
    up = -up if up[1] < 0 else up
    return right, up, fwd


def wire_sheet(path, pos, quads, views=((0, 0.05), (0.6, 0.15), (1.5708, 0.05), (3.1416, 0.05), (0.0, 1.2), (0.45, -0.7)),
               size=700, scale=None, center=None, extra=None):
    pos = np.asarray(pos)
    quads = np.asarray(quads)
    c = (pos.max(0) + pos.min(0)) / 2 if center is None else np.asarray(center)
    ext = (pos.max(0) - pos.min(0)).max() if scale is None else scale
    sc = size * 0.9 / ext
    tiles = []
    fn = np.cross(pos[quads[:, 2]] - pos[quads[:, 0]], pos[quads[:, 3]] - pos[quads[:, 1]])
    fn /= np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-12)
    for yaw, pitch in views:
        right, up, fwd = _view_matrix(yaw, pitch)
        img = np.full((size, size, 3), 0.12, np.float32)
        vis = fn @ fwd < 0
        shade = np.clip(-(fn @ fwd), 0, 1)
        u = (pos - c) @ right * sc + size / 2
        v = size / 2 - (pos - c) @ up * sc
        depth = (pos - c) @ fwd
        # draw back faces first (dim), then front faces
        for front in (False, True):
            qs = quads[vis == front]
            if len(qs) == 0:
                continue
            col = np.array([0.85, 0.9, 1.0]) if front else np.array([0.35, 0.22, 0.22])
            e = np.concatenate([qs[:, [0, 1]], qs[:, [1, 2]], qs[:, [2, 3]], qs[:, [3, 0]]])
            e = np.unique(np.sort(e, 1), axis=0)
            n = 24
            tt = np.linspace(0, 1, n)[None, :]
            xs = (u[e[:, 0]][:, None] * (1 - tt) + u[e[:, 1]][:, None] * tt).ravel()
            ys = (v[e[:, 0]][:, None] * (1 - tt) + v[e[:, 1]][:, None] * tt).ravel()
            xi = np.round(xs).astype(int)
            yi = np.round(ys).astype(int)
            m = (xi >= 0) & (xi < size) & (yi >= 0) & (yi < size)
            img[yi[m], xi[m]] = col
        if extra is not None:
            for pts, colr in extra:
                uu = np.round((pts - c) @ right * sc + size / 2).astype(int)
                vv = np.round(size / 2 - (pts - c) @ up * sc).astype(int)
                m = (uu >= 1) & (uu < size - 1) & (vv >= 1) & (vv < size - 1)
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        img[vv[m] + dy, uu[m] + dx] = colr
        tiles.append(img)
    cols = 3
    rows = int(np.ceil(len(tiles) / cols))
    sheet = np.zeros((rows * size, cols * size, 3), np.float32)
    for k, t in enumerate(tiles):
        r, cc = divmod(k, cols)
        sheet[r * size:(r + 1) * size, cc * size:(cc + 1) * size] = t
    save_png(path, sheet)


def dump_glb(path, parts):
    """parts: list of (name, pos, quads_or_tris)"""
    from .glb import GLB, vertex_normals, quads_to_tris
    g = GLB()
    m = g.add_material({"name": "Fabric", "pbrMetallicRoughness": {"baseColorFactor": [0.05, 0.05, 0.05, 1], "metallicFactor": 0, "roughnessFactor": 0.9}, "doubleSided": True})
    for name, pos, faces in parts:
        faces = np.asarray(faces)
        tris = quads_to_tris(faces) if faces.shape[1] == 4 else faces
        g.add_mesh(name, m, pos, vertex_normals(pos, tris), tris)
    g.write(path)
