#!/usr/bin/env python
"""Rebuilds tee.glb (one command, fully procedural, deterministic):

    python (with bpy) build.py [--no-cache] [--shots]

  --no-cache  re-run the cloth simulation even if a cached result exists in ./cache (about 5 minutes)
  --shots     run the judging harness afterwards and write ./shots

Pipeline (approach B: model the worn shape, let physics add the folds):
  1. rest shell      teegen/shell.py      implicit surface (boxy superelliptical tube + shoulder roof + sleeve cones)
                                          carrying a structured all-quad grid, relaxed on the surface
  2. mannequin       teegen/mannequin.py  procedural ghost body (collision only, never exported)
  3. simulation      teegen/sim.py        Blender cloth: pinned at the top edge of the collar rib, gravity, the arms
                                          come down from the rest pose, self collision
  4. finishing       teegen/finish.py     Taubin smoothing, hem fairing, cloth thickness (inner shell), rounded hem
                                          rims, thick rib collar, woven neck label, per-vertex ambient occlusion
  5. UVs + textures  teegen/uvs.py, teegen/textures.py   pattern-like islands unwrapped on the rest shape, normal map
                                          (stitches, seams, rib knit, grain) and occlusion map rasterised in UV space
  6. print decal     teegen/printpatch.py arc-length grid laid on the simulated chest, offset along smooth normals
  7. GLB             teegen/glb.py        hand written glTF 2.0 binary (metres, +Y up, front = +Z)
"""
import os, sys, time, json, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
import bpy  # noqa: F401

from teegen.params import P
from teegen import shell, mannequin as mq, sim, finish, uvs, textures, printpatch, imgtool
from teegen.glb import GLB


def log(*a):
    print(*a, flush=True)


def main():
    t0 = time.time()
    use_cache = "--no-cache" not in sys.argv
    out = os.path.join(HERE, "tee.glb")
    work = os.path.join(HERE, "cache")
    os.makedirs(work, exist_ok=True)

    # 1. rest shell
    D, T, rest = shell.build_rest_shell(P, verbose=True)
    # 2. mannequin (rest pose) and clearance
    tv, tf = mq.torso_mesh(P)
    arms = [mq.arm_mesh(P, D.d * np.array([s, 1, 1]), s) for s in (1.0, -1.0)]
    col = mq.Collider([(tv, tf)] + arms)
    rest = col.push_out(rest, 0.0075)
    log(f"[build] rest shell ready ({time.time() - t0:.0f}s)")
    # 3. cloth simulation
    final, _ = sim.simulate(P, D, T, rest, cache_dir=work if use_cache else None, log=log)
    log(f"[build] simulation done ({time.time() - t0:.0f}s)")
    # 4. finishing
    X = finish.smooth_sim(P, T, final, iters=P.smooth_iters, zone=sim.print_zone(P, T, rest))
    X = finish.fair_hems(P, T, X)
    X = finish.separate_layers(T, X, log=log)
    uv_corner, labels, info = uvs.unwrap(P, T, rest)
    for L, d in info.items():
        log(f"[uv] island {L}: {d['size'][0]:.3f} x {d['size'][1]:.3f} m, stretch p1/p99 {d['stretch'][0]:.3f}/{d['stretch'][1]:.3f}")
    G = finish.assemble(P, T, X, rest, uv_corner, labels, log=log)
    # recentre: x on the collar centre, y/z on the fabric bounding box
    c = np.array([X[T.vid[P.NR]][:, 0].mean(), (G.pos[:, 1].max() + G.pos[:, 1].min()) / 2, (G.pos[:, 2].max() + G.pos[:, 2].min()) / 2])
    G.pos = G.pos - c
    ao = finish.ambient_occlusion(G.pos, G.nrm, G.tris, nrays=P.ao_rays, log=log)
    log(f"[build] geometry + AO done ({time.time() - t0:.0f}s)")
    textures.pack(G, atlas=P.atlas, log=log)
    nmap, aomap, dbg = textures.build_maps(G, P, ao, grain=P.grain, wrinkle=P.wrinkle, log=log)
    npath, apath = os.path.join(work, "fabric_normal.jpg"), os.path.join(work, "fabric_ao.jpg")
    imgtool.save(npath, nmap, "JPEG", P.normal_quality)
    half = aomap.reshape(P.atlas // 2, 2, P.atlas // 2, 2).mean((1, 3))
    imgtool.save(apath, half, "JPEG", 88)
    log(f"[build] textures: normal {os.path.getsize(npath) / 1e6:.2f} MB, ao {os.path.getsize(apath) / 1e6:.2f} MB ({time.time() - t0:.0f}s)")
    # 5. print decal
    seam_pt = X[T.vid[P.NR, 0]] - c
    pr = printpatch.build_print(P, G, seam_pt, top_gap=P.print_gap, nu=P.print_nu, nv=P.print_nv, offset=P.print_offset, log=log)
    ppath = os.path.join(work, "print_normal.jpg")
    imgtool.save(ppath, textures.print_normal(P, grain=P.grain * 0.55), "JPEG", 86)
    # 6. GLB
    g = GLB()
    tn = g.add_image(npath, "image/jpeg")
    ta = g.add_image(apath, "image/jpeg")
    tp = g.add_image(ppath, "image/jpeg")
    fabric = g.add_material({
        "name": "Fabric",
        "pbrMetallicRoughness": {"baseColorFactor": [0.043, 0.043, 0.047, 1.0], "metallicFactor": 0.0, "roughnessFactor": 0.9},
        "normalTexture": {"index": tn, "scale": 1.0},
        "occlusionTexture": {"index": ta, "strength": 1.0},
        # The cloth is a closed solid (outer shell + inner shell + rounded rims): the inside of the shirt is real
        # geometry, so the material stays single sided (double sided rendering of a closed shell only adds
        # silhouette acne from the outer shell's own back faces).
        "doubleSided": False,
    })
    printm = g.add_material({
        "name": "Print",
        "pbrMetallicRoughness": {"baseColorFactor": [1.0, 1.0, 1.0, 1.0], "metallicFactor": 0.0, "roughnessFactor": 0.82},
        "normalTexture": {"index": tp, "scale": 1.0},      # the knit shows through the ink
        "alphaMode": "BLEND",
        "doubleSided": False,
    })
    g.add_mesh("Fabric", fabric, G.pos, G.nrm, G.tris, uv=G.uv)
    g.add_mesh("Print", printm, pr["pos"], pr["nrm"], pr["tris"], uv=pr["uv"], tangent=pr["tangent"])
    total = g.write(out)
    size = G.pos.max(0) - G.pos.min(0)
    log(f"[build] wrote {out}: {total / 1e6:.2f} MB, {len(G.tris) + len(pr['tris'])} triangles, fabric bbox {size.round(3)} m ({time.time() - t0:.0f}s)")
    np.savez_compressed(os.path.join(work, "last_build.npz"), pos=G.pos, tris=G.tris, rest=rest, final=final)
    if "--shots" in sys.argv:
        harness = os.path.join(os.path.dirname(HERE), "harness")
        subprocess.run(["node", "shot.js", out, os.path.join(HERE, "shots")], cwd=harness, check=True, stdout=subprocess.DEVNULL)
        st = json.load(open(os.path.join(HERE, "shots", "stats.json")))
        log(f"[build] harness: {st['triangles']} tris, {st['fileBytes']} bytes, warnings: {st['contractWarnings']}, errors: {st['errors']}")


if __name__ == "__main__":
    main()
