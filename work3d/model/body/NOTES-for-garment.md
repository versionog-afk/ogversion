# Notes from the figure stage for whoever drapes the shirt

Written by the builder of the figure when that stage finished (2026-11-26). Paths in it refer to the layout that `../make_root.sh` creates (`na2/model/...` is `work3d/model/...`).

## Summary

The figure stage is finished: `body.glb`, `collide.obj`, `landmarks.json` and `README.md` are rebuilt, and `current.glb` has been replaced atomically with a new stand-in that passes the contract check with no warnings or errors.

What changed from the interrupted build:
- **Pose:** the thumbs now rest beside the index fingers (they stuck out before), the legs are closer (ankle centres 0.23 m apart, was 0.28) and the neck is straightened by 6 degrees with the face kept level. Arms stay 16 degrees from the body with a 14 degree elbow bend.
- **Shoulders, armpits, elbows, wrists:** nothing collapsed or twisted; apart from the eyelids touching the eyeballs, the body has no self-intersections.
- **Head and hair:** face unchanged (closed mouth, lowered lids over plain eyeballs, no lashes or teeth). The hair keeps its low bun and clean hairline; I rounded the nape edge and removed six zero-area faces that formed a small nub under the bun.
- **Trousers:** rebuilt as straight wide legs with an even hem at 6.4 cm and a few soft folds. The old hem was spiky and the legs flared.
- **Skin cuts:** hidden skin is now cut along clean curves instead of ragged quad borders, and no skin is kept under the trousers. The ankles inside the trouser legs are dark stubs that belong to `Shoes`.
- **Bright dots on the trousers:** these turned out to be hidden skin showing as single pixels in the shared viewer, not real poke-through. A ray test found no skin geometrically visible, and the dots went away once the hidden skin was removed.
- **Landmarks:** now also include girths, arm and back lengths and a loop of points around the neck base.
- **Scripts:** one `ROOT` variable (overridable with `NA2_ROOT`); the build is deterministic and takes about half a minute without publishing.

The mesh check reports no fragments, zero-area faces, non-manifold edges or flipped normals, and no trouser intersections with body or shoes. On `body.glb` the contract checker gives only the three expected warnings (no shirt, no prints).

A sibling folder `model/mpfb` appeared during my run. It is another builder's MPFB2 recipe that repeats my pose values; I did not touch or verify it.

## How it was built

The figure is built by scripts only, from the CC0 MakeHuman data files read with our own numpy code (no MakeHuman or MPFB2 program code runs).

1. `figure.py` mixes the morph targets, poses the default rig with linear blend skinning and applies corrective smoothing.
2. `hair_bl.py` and `shoes_bl.py` grow hair and shoes as distance fields around the head and feet in Blender's Python, then mesh, smooth and decimate them.
3. `assemble.py` lofts the trousers (`pants.py`), measures the landmarks (`measure.py`), cuts hidden skin, adds eyeballs and ankle stubs, and writes `body.glb`, `collide.obj`, `collide_anim.npz`, `collide_apose.obj` and `landmarks.json`.
4. `check.py` writes the mesh report; the shared `shot.js` renders the sheets.
5. With `publish`, `standin.py` adds the placeholder shirt and decals, and `current.glb` is replaced only if the contract check is clean.

Rebuild everything:

`bash <NA2_ROOT>/na2/model/body/build.sh publish`

Without `publish` it rebuilds the figure only. On another machine set `NA2_ROOT`; with a normal Blender install also set `NA2_BPY="blender --background --python"`.

## Notes for the garment stage

Everything is in `<NA2_ROOT>/na2/model/body/`; read `README.md` there first. Frame: metres, Y up, figure faces +Z, wearer's left is +X, floor y = 0.

**Files to use**
- `collide.obj`: objects `body` (whole posed body, closed) and `pants` (closed, capped), both inflated 2.5 mm. Blender import: forward -Z, up Y.
- `collide_anim.npz`: the same body in 9 steps from the base A-pose (frame 0) to the final pose (frame 8); only the arms move. Sew on frame 0 and let the arms come down, or drape directly on the final pose.
- `landmarks.json`: all numbers below and more (torso profile every centimetre, neck base loop, where the arm sits next to the torso).
- `out/body_uncut.glb`: the uncut body.

**Pose**
- Symmetric, height 1.676 m with hair (skin top 1.668).
- Upper arms 16 degrees from the body, elbows bent 14 degrees, forearms about 15 degrees forward, palms facing the thighs.
- Shoulder joint (±0.158, 1.318, -0.009), elbow (±0.224, 1.086, -0.006), wrist (±0.284, 0.879, 0.050), fingertips y = 0.739.

**Neck and collar**
- Neck base centre (0, 1.400, -0.011), plane normal (0, 0.95, 0.31): the plane tilts so the front is 3 cm lower than the back.
- Pit of the neck (0, 1.385, 0.035), back of the neck (0, 1.415, -0.057), side neck points (±0.066, 1.416, -0.021).
- Neck base girth 0.426. Neck column at y = 1.43: half-width 0.054, half-depth 0.046.
- Lowest hair is at y = 1.496, so the bun is clear of the collar.

**Shoulders and torso**
- Shoulder points (±0.185, 1.353, -0.013), acromion (±0.153, 1.377, -0.024), slope 22 degrees, width over the deltoids 0.43.
- Armpits (±0.137, 1.260, -0.007).
- Chest front z = 0.120 at y = 1.21 (0.109 on the midline), chest girth 0.81. Upper back z = -0.097 at y = 1.30.
- Waist y = 1.07, half-width 0.117, girth 0.65.
- Hips: width 0.343, depth 0.184 at y = 0.80; girth 0.905 at y = 0.82. Seat z = -0.117 at y = 0.88. Crotch y = 0.784.
- Arms: upper arm 0.240, forearm 0.224, upper arm girth 0.24, shoulder point to elbow 0.27.

**Trousers the shirt falls on**
- Waist top y = 1.035 (must stay under the shirt), half-width 0.186 at the hip, front z about 0.105, back z about -0.13 at the seat.

**What matters for draping**
1. The shoulders slope steeply and the chest is small, so the shirt hangs from the neck seam, shoulders and upper back. Fix the collar seam to the neck base loop early.
2. The wrists are at |x| 0.26 to 0.31 and y 0.88, close to where the side of the hem will be. My reading of the photos puts the hem near y = 0.78 to 0.80 (crotch level), but measure it yourself. Consider removing the fingers from the collision mesh.
3. Skin behind dark cloth sparkles as bright pixels in the shared viewer, so re-cut the body for the real shirt and keep only 2 to 3 cm of skin inside the collar and the sleeve ends.
   - Call `assemble.figure_meshes(hidden=fn)` with `fn(P, field, M, L)` returning a field that is positive where skin is hidden, or change `assemble.CUT`. `standin.py` is a working example.
   - `common.clip_tris` makes the clean cut; `assemble.add_figure(glb, meshes)` writes the four figure meshes with the right names and materials.
4. The figure uses 43.6k triangles (Body 17.9k before your re-cut, Hair 5.6k, Pants 14.5k, Shoes 5.7k), which leaves about 86k for shirt and prints.

**Publishing and pose changes**
- `current.glb` is the stand-in from `standin.py`. Replace it only through a contract-clean build; `bash build.sh publish` shows the pattern.
- Do not change `CFG` in `figure.py` without need: `collide.obj`, the landmarks and the sibling `model/mpfb` recipe all follow it.

## Known issues

- My build does not use MPFB2. I kept the earlier builder's route (MakeHuman CC0 data plus own numpy code). The MPFB2 recipe in `model/mpfb` is someone else's work and I did not verify it.
- Light skin left behind dark cloth shows as single bright pixels along its silhouette in the shared viewer. My explanation (unreliable depth on edge-on triangles in the software renderer) is a hypothesis. It will recur wherever an arm or the neck sits behind the shirt.
- A faint dashed light rim remains along the trouser silhouette in the exact side view of the studio look. It appears with the trousers alone, so I take it to be the viewer's cloth sheen and left it.
- The trouser hem is 6.4 cm above the floor, slightly cropped, not floor-length as in the reference photos. An even hem any lower would cut through the shoe.
- From a camera below the hem looking up, one sees dark ankle stubs, not skin.
- The hair has soft combed-back ridges, sculpted and not strand geometry. If 'no strands' means fully smooth, set `strand_amp=0` in `HP` in `hair_bl.py`.
- In `body.glb` the arms are cut 5.5 cm below the shoulder joint and the skin around the neck is kept to a 12 cm radius. These margins are placeholders until the real shirt exists.
- The stand-in shirt in `current.glb` is a crude lofted box with tube sleeves. It only keeps names, scale, orientation and UV directions valid.
- Shoes are simple chunky slip-ons with slightly uneven collar edges.
- `collide.obj` includes the hands with thin fingers, which can snag cloth.
- Only the bpy module on Linux was run. The `blender --background --python` route and Windows or macOS are untested.

## Outside material used

- MakeHuman base mesh, morph targets, default rig and skin weights (data files only, from github.com/makehumancommunity/makehuman, commit a8bc2d5): CC0 1.0, per LICENSE.md sections C and D
- Blender 5.3 as the bpy Python module (BVH queries, subdivision, smoothing, decimation): GPL, used as a tool only
- numpy: BSD-3-Clause
- three.js and Playwright through the shared viewer, for renders only: MIT and Apache-2.0
- Not used in this stage: MPFB2, pygarment / GarmentCode, ppf-contact-solver, any other model, texture, photo or service
