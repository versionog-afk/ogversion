# NA2 figure (stage 1): body, hair, trousers, shoes

A stylised, generic, slim adult figure (1.68 m with hair) in a relaxed standing pose, built only from scripts.
It is the mannequin for the NA2 oversized T-shirt: the garment stage drapes the shirt on `collide.obj` and ships
`body.glb` together with the shirt. Units are metres, Y is up, the figure faces +Z, the wearer's left is +X, the floor is y = 0.

## Rebuild

    bash build.sh            # about one minute: everything below, plus mesh check and render sheets
    bash build.sh publish    # also rebuilds the stand-in and, if the contract check is clean, replaces ../current.glb

What it needs:

| need | used for | note |
|---|---|---|
| Python 3 with numpy | `figure.py`, `assemble.py`, `standin.py` | Blender's own Python works too |
| a Python that can `import bpy` (Blender 4.x / 5.x) | `hair_bl.py`, `shoes_bl.py`, `check.py` | with a normal Blender install: `NA2_BPY="blender --background --python" bash build.sh` |
| a checkout of github.com/makehumancommunity/makehuman at `ROOT/ext/makehuman` | base mesh, targets, rig | only the data files are read, no MakeHuman code runs |
| Node, playwright, three.js at `ROOT/v3/node_modules/three`, the shared viewer `ROOT/na2/harness` | render sheets only | optional, the model builds without them |

**ROOT** is the only machine-specific path. It is set once at the top of `build.sh`, `common.py` and `tools/myshot.js`;
the environment variable `NA2_ROOT` overrides all three. (`NA2_MAKEHUMAN` can point straight at a `makehuman/data` folder.)
The build is deterministic: the same inputs give byte-identical files.

## Outputs

| file | what |
|---|---|
| `body.glb` | meshes `Body` (material `Skin`), `Hair` (`Hair`), `Pants` (`Pants`, double sided), `Shoes` (`Shoes`). Skin that is hidden by clothes, hair and shoes is already cut away (see "Cutting") |
| `collide.obj` | collision set for draping: object `body` = the whole posed body with torso, head, hands (closed, quads) and object `pants` = the trousers with caps on waist and hems (closed). Both inflated by 2.5 mm. Blender import: forward -Z, up Y |
| `collide_anim.npz` | the same collision body in 9 steps while the arms come down from the base A-pose (`body_frames[0]`) to the final pose (`body_frames[8]`); `body_quads`, `pants_verts`, `pants_tris`. Legs, head and fingers are final in every step |
| `collide_apose.obj` | step 0 of the above as an OBJ |
| `landmarks.json` | measured on the posed body, metres. Neck base (centre, plane, radii, loop of points), side neck points, shoulder points, acromion, shoulder line and slope, armpits, chest front, upper back, waist, hip width and depth, seat, crotch height, elbows, wrists, fingertips, top of head, eye centres, arm lengths and girths, chest / waist / hip / neck girths, torso profile every centimetre, where the arm is next to the torso, trouser sections, pose description |
| `out/body_uncut.glb` | the whole body uncut, for inspection or other cuts |
| `out/standin.glb` | figure + crude lofted shirt + analytic decals: a contract-valid placeholder until the real shirt exists |
| `out/check.json`, `shots/` | mesh report and render sheets of the last build |

## Scripts

| script | python | does |
|---|---|---|
| `common.py` | numpy | ROOT, loaders for the MakeHuman base mesh / targets / weights, small mesh helpers (`autosmooth`, `clip_tris`) |
| `shape.py` | numpy | target mixing, the default rig, linear blend skinning |
| `figure.py` | numpy | shape and pose (`CFG` at the top): 85 % female, slim, even mix of the three ethnic macros, lowered eyelids; arms 16 degrees from the body, elbows 14 degrees, relaxed fingers and thumb, legs closer, neck straightened; corrective smoothing at shoulders, armpits and the thumb web. Writes `out/figure.npz` (also the arm animation) |
| `hair_bl.py` | bpy | hair as a signed distance field around the head (hairline as a polar curve, cap, low bun, soft combed-back ridges), surface nets, smoothing, decimation, clean-up (`HP` at the top). Writes `out/hair.npz` |
| `shoes_bl.py` | bpy | plain low shoes grown around the feet (blurred distance field, sole slab), `SP` at the top. Writes `out/shoes.npz` |
| `measure.py` | numpy | landmarks and region masks |
| `pants.py` | numpy | wide straight trousers lofted around legs and pelvis: straight outer line from the hip, even hem at 6.4 cm, a few soft vertical folds, clearance to legs and shoes, turned-in hem (`PP` at the top) |
| `assemble.py` | numpy | cuts hidden skin (`CUT`), adds plain eyeballs and dark ankle stubs, writes `body.glb`, `collide.obj`, `collide_anim.npz`, `collide_apose.obj`, `landmarks.json`, `out/body_uncut.glb` |
| `standin.py` | numpy | the placeholder shirt and decals around the figure |
| `glbw.py` | numpy | minimal GLB writer |
| `check.py` | bpy | per mesh: fragments, open borders, non-manifold edges, zero-area faces, flipped normals, self-intersections; between meshes: real triangle intersections |
| `tools/look.sh`, `tools/myshot.js`, `tools/myview.html`, `tools/views.json` | node | close-up contact sheets, e.g. `bash tools/look.sh body.glb head shots/head.png clay` |
| `tools/subset.py`, `tools/landmarks_debug.py`, `tools/raytest.py`, `tools/selfint*.py`, `tools/import_test.py` | | inspection helpers (single meshes, landmark balls, "is skin visible through cloth", where the body intersects itself, Blender import test) |

## Cutting hidden skin

`assemble.hidden_field()` gives every body vertex a number that is positive where the skin is covered; `common.clip_tris()`
cuts the mesh along its zero level, so the borders are clean curves. `CUT` holds the margins (collar opening, sleeve, scalp).
`standin.py` shows how to call it with other margins. Keep the margins short: in the shared WebGL viewer light skin that
stays behind dark cloth shows up as single bright pixels along its silhouette. That is why no skin is kept under the trousers
(the ankles inside the trouser legs are dark stubs that belong to `Shoes`).

## Known state of `out/check.json`

- `Body x Hair` intersections are intended (the hair edge is sunk into the scalp), `Body` self-intersections are the eyelids
  touching the eyeballs. `Body x Pants`, `Pants x Shoes` and all fragment / degenerate counts are 0.
- `Shoes` self-intersections are the dark ankle stubs, which are sunk 12 mm into the closed shoes on purpose.
- Open borders are the cuts (neck, sleeves, scalp), the trouser waist and hems, the top of the ankle stubs and the
  inner side of the hair shell.

## Outside assets and licences

- MakeHuman base mesh, morph targets, default rig and skin weights (`makehuman/data/3dobjs/base.obj`, `targets/`,
  `rigs/default.mhskel`, `rigs/default_weights.mhw`), repository github.com/makehumancommunity/makehuman, commit a8bc2d5:
  **CC0 1.0** (LICENSE.md section C; section D: no claim on output). Only these data files are read.
- No MakeHuman or MPFB2 program code, no other models, textures, photos or services. Hair, shoes, trousers, eyes and all
  code in this folder were written for this project. Blender (GPL) is used as a tool only; its output carries no licence.
- The person in the reference photos was used only to judge fit and proportions; nothing of her likeness is in the model.

## Continuing in Blender with a GUI

File > Import > glTF `body.glb` (already Y-up to Z-up converted by the importer) and Wavefront `collide.obj` with
forward -Z, up Y. To change the pose or shape, edit `CFG` in `figure.py` and run `bash build.sh`; hair, shoes and trousers
follow the body automatically.

`../mpfb/` is separate work by another builder (an MPFB2 recipe that repeats the `CFG` values of `figure.py` inside
Blender). `build.sh` does not use it; if `CFG` changes here, that recipe needs the same change.
