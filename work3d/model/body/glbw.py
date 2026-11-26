"""Minimal glTF 2.0 binary (GLB) writer. Coordinates are written as given:
metres, +Y up, +Z front (the garment frame used everywhere in this project)."""
import json, struct
import numpy as np


class GLB:
    def __init__(self):
        self.bin = bytearray()
        self.views = []
        self.accessors = []
        self.meshes = []
        self.nodes = []
        self.materials = []
        self.textures = []
        self.images = []
        self.samplers = [{"magFilter": 9729, "minFilter": 9987, "wrapS": 10497, "wrapT": 10497}]

    def _view(self, data: bytes, target=None):
        while len(self.bin) % 4:
            self.bin.append(0)
        off = len(self.bin)
        self.bin += data
        v = {"buffer": 0, "byteOffset": off, "byteLength": len(data)}
        if target:
            v["target"] = target
        self.views.append(v)
        return len(self.views) - 1

    def _acc(self, arr, ctype, atype, target=None, minmax=False, normalized=False):
        arr = np.ascontiguousarray(arr)
        v = self._view(arr.tobytes(), target)
        a = {"bufferView": v, "componentType": ctype, "count": int(arr.shape[0]), "type": atype}
        if normalized:
            a["normalized"] = True
        if minmax:
            a["min"] = [float(x) for x in arr.min(axis=0)]
            a["max"] = [float(x) for x in arr.max(axis=0)]
        self.accessors.append(a)
        return len(self.accessors) - 1

    def add_image(self, path, mime):
        with open(path, "rb") as f:
            data = f.read()
        v = self._view(data)
        self.images.append({"bufferView": v, "mimeType": mime})
        self.textures.append({"sampler": 0, "source": len(self.images) - 1})
        return len(self.textures) - 1

    def add_material(self, m):
        self.materials.append(m)
        return len(self.materials) - 1

    def add_mesh(self, name, material, pos, nrm, tris, uv=None, uv1=None, tangent=None):
        attrs = {
            "POSITION": self._acc(pos.astype(np.float32), 5126, "VEC3", 34962, minmax=True),
            "NORMAL": self._acc(nrm.astype(np.float32), 5126, "VEC3", 34962),
        }
        if uv is not None:
            attrs["TEXCOORD_0"] = self._acc(uv.astype(np.float32), 5126, "VEC2", 34962)
        if uv1 is not None:
            attrs["TEXCOORD_1"] = self._acc(uv1.astype(np.float32), 5126, "VEC2", 34962)
        if tangent is not None:
            attrs["TANGENT"] = self._acc(tangent.astype(np.float32), 5126, "VEC4", 34962)
        tris = np.asarray(tris).reshape(-1)
        if len(pos) < 65535:
            idx = self._acc(tris.astype(np.uint16), 5123, "SCALAR", 34963)
        else:
            idx = self._acc(tris.astype(np.uint32), 5125, "SCALAR", 34963)
        self.meshes.append({"name": name, "primitives": [{"attributes": attrs, "indices": idx, "material": material, "mode": 4}]})
        self.nodes.append({"name": name, "mesh": len(self.meshes) - 1})

    def write(self, path):
        while len(self.bin) % 4:
            self.bin.append(0)
        doc = {
            "asset": {"version": "2.0", "generator": "teegen (procedural, Blender cloth)"},
            "scene": 0,
            "scenes": [{"name": "Tee", "nodes": list(range(len(self.nodes)))}],
            "nodes": self.nodes,
            "meshes": self.meshes,
            "materials": self.materials,
            "accessors": self.accessors,
            "bufferViews": self.views,
            "buffers": [{"byteLength": len(self.bin)}],
        }
        if self.images:
            doc["images"] = self.images
            doc["textures"] = self.textures
            doc["samplers"] = self.samplers
        js = json.dumps(doc, separators=(",", ":")).encode()
        while len(js) % 4:
            js += b" "
        total = 12 + 8 + len(js) + 8 + len(self.bin)
        with open(path, "wb") as f:
            f.write(struct.pack("<III", 0x46546C67, 2, total))
            f.write(struct.pack("<II", len(js), 0x4E4F534A))
            f.write(js)
            f.write(struct.pack("<II", len(self.bin), 0x004E4942))
            f.write(self.bin)
        return total


def vertex_normals(pos, tris):
    """Area+angle agnostic (area weighted) smooth vertex normals."""
    p = pos
    fn = np.cross(p[tris[:, 1]] - p[tris[:, 0]], p[tris[:, 2]] - p[tris[:, 0]])
    n = np.zeros_like(p)
    for k in range(3):
        np.add.at(n, tris[:, k], fn)
    l = np.linalg.norm(n, axis=1, keepdims=True)
    return n / np.maximum(l, 1e-20)


def angle_weighted_normals(pos, tris):
    p = pos
    n = np.zeros_like(p)
    fn = np.cross(p[tris[:, 1]] - p[tris[:, 0]], p[tris[:, 2]] - p[tris[:, 0]])
    fn /= np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-20)
    for k in range(3):
        a = p[tris[:, (k + 1) % 3]] - p[tris[:, k]]
        b = p[tris[:, (k + 2) % 3]] - p[tris[:, k]]
        a /= np.maximum(np.linalg.norm(a, axis=1, keepdims=True), 1e-20)
        b /= np.maximum(np.linalg.norm(b, axis=1, keepdims=True), 1e-20)
        ang = np.arccos(np.clip((a * b).sum(1), -1, 1))
        np.add.at(n, tris[:, k], fn * ang[:, None])
    l = np.linalg.norm(n, axis=1, keepdims=True)
    return n / np.maximum(l, 1e-20)


def quads_to_tris(quads):
    q = np.asarray(quads)
    return np.concatenate([q[:, [0, 1, 2]], q[:, [0, 2, 3]]], axis=0)
