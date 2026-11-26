# Third-party material

Record everything here before it is used, with the licence and where it ends up.

## Shipped to visitors

| what | where | licence | notes |
|---|---|---|---|
| three.js r187 (renderer, GLTFLoader, meshopt decoder) | bundled into `merch/v/app.js` | MIT | npm `three@0.187.0` |
| Human base mesh and morph targets from the MakeHuman project | the figure's body in `merch/v/figure.glb` (shape and pose changed by our scripts) | CC0 1.0 | asset licence in the project's `LICENSE.md`, sections C and D: assets and exported output carry no restrictions |

## Build and test tools (not shipped)

| what | licence |
|---|---|
| esbuild | MIT |
| sharp | Apache-2.0 |
| @gltf-transform/cli | MIT |
| Playwright | Apache-2.0 |
| Blender (`bpy`) | GPL; applies to the program, not to models made with it |

## Chosen for the next phases (approved by the owner, not installed yet)

| what | used for | licence | notes |
|---|---|---|---|
| MPFB2 (`makehumancommunity/mpfb2`) | the human figure in Blender | add-on GPL-3.0-or-later; bundled assets and exported output CC0 1.0 | separately downloaded asset packs carry their own licences: check each pack |
| GarmentCode (`maria-korosteleva/GarmentCode`) | sewing patterns for the shirt | MIT | use the pattern output only; its draping step needs a simulator fork under a non-commercial licence |
| Blender cloth simulation | draping | part of Blender | default choice |
| `st-tech/ppf-contact-solver` | optional higher-quality draping | solver Apache-2.0, Blender add-on GPL-3.0-or-later | its own FAQ calls it not production ready |
| TRELLIS.2 through ComfyUI, or Modly | optional shape reference from a photo | see `research/photo-to-3d.md` | never ship a generated mesh without re-checking the licence chain |

## Fonts

No font files are shipped. If lettering in a print texture is re-set rather than traced, use only fonts under the SIL Open Font License and name them here.

## Owner's own material

The shirt artwork (front lettering, back map), the nine gallery photos and the product photos belong to the brand.
