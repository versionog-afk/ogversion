"""Collision bodies for the drape: the figure of stage 1 in a row of arm poses, from the pose in which the shirt can lie flat
around it (arms along the flat-lay sleeves) down to the final relaxed pose. Uses the scripts of the figure stage (../body);
numpy only.   python3 pose.py [spec.json]   ->  out/<name>/pose.npz"""
import os, sys, json, math
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from na2cfg import *
sys.path.insert(0, BODY)
import common as bc, figure as fig, measure as bm, assemble as asm          # noqa: E402  (figure stage modules)
from glbw import angle_weighted_normals                                    # noqa: E402


def main():
    M = load_spec(); out = out_dir(M)
    St = json.load(open(os.path.join(HERE, 'settings.json')))['sim']
    a0 = 90.0 - M['sleeve']['angle_flat_deg']                   # arm angle from vertical that matches the flat-lay sleeve
    a1 = fig.CFG['arm_abduction']
    final = fig.build(verbose=False)
    P, G, J, W = bm.load()
    if np.abs(final['P'] - P).max() > 1e-6: raise SystemExit('figure stage output (out/figure.npz) does not match figure.py: rebuild ../body first')
    Mk = bm.masks(P, G, W); q = Mk['q']; tri = bc.quads_to_tris(q)
    used = np.unique(q); remap = -np.ones(len(P), dtype=np.int64); remap[used] = np.arange(len(used)); quads = remap[q]
    angles = np.linspace(a0, a1, St['arm_keys'])
    frames = []
    for a in angles:
        Pk = fig.build(cfg=dict(fig.CFG, arm_abduction=float(a)), verbose=False, frame=(final['sc'], final['off']))['P']
        Nk = np.zeros_like(Pk); Nk[:] = angle_weighted_normals(Pk, tri)
        frames.append((Pk + Nk * asm.INFLATE)[used])
    frames = np.array(frames, dtype=np.float32)
    # the last key must be the collision body of stage 1
    ca = np.load(os.path.join(BODY, 'collide_anim.npz'))
    d = float(np.abs(frames[-1] - ca['body_frames'][-1]).max()) if ca['body_frames'].shape[1] == frames.shape[1] else float('nan')
    np.savez_compressed(os.path.join(out, 'pose.npz'), frames=frames, angles=angles, quads=quads.astype(np.int32),
                        pants_verts=ca['pants_verts'], pants_tris=ca['pants_tris'])
    log('pose keys: %d, arm angle %.1f -> %.1f deg from vertical, %d verts; last key vs stage 1 collide body: %.2e m' % (len(angles), a0, a1, frames.shape[1], d))


if __name__ == '__main__':
    main()
