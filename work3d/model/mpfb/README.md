# NA2 figure with MPFB2: recipe for the owner's PC

MPFB2 (the MakeHuman plugin for Blender) makes the same figure as the numpy stage in `../body/`, but inside Blender,
as a live, rigged human that can be posed and used as the collision body for cloth. One script does it:
`make_figure.py`. No asset pack is needed.

Tried here: MPFB 2.0.18 (git `650c5c5`, 22 Nov 2026) in Blender 5.3.0 as the `bpy` Python module, headless, Linux.
**Not tried here:** a Blender with a window, Windows, macOS, and the build that extensions.blender.org serves
(that site and the MPFB documentation site are blocked on the build machine). See "Not verified" at the end.

## 1. Install MPFB2 (Windows and macOS)

MPFB 2.x needs Blender 4.2 or newer and is an *extension* (not a legacy add-on).

1. Open Blender, then `Edit > Preferences` (Windows Ctrl+, / macOS Cmd+, ; on macOS it is also in the `Blender` menu).
2. `Get Extensions`. The first time Blender asks to "Allow Online Access": allow it (this is only needed to browse
   extensions.blender.org; the recipe itself never goes online).
3. Search `MPFB`, press `Install`. It is enabled at once. In the 3D viewport press `N`: there is a new sidebar tab
   called `MPFB v2.0.x`.
4. Without online access: download the MPFB zip from `https://extensions.blender.org/add-ons/mpfb/` in a browser, then
   in `Get Extensions` use the arrow menu at the top right, `Install from Disk...`, and pick the zip (or drag the zip
   into the Blender window).

Installed this way the Python package is `bl_ext.blender_org.mpfb` (extension id `mpfb` in `blender_manifest.toml`).
The script finds it under any repository name.

## 2. Run the recipe

Copy this folder (`make_figure.py` is enough) anywhere. Outputs go to `out/` next to the script
(change `ROOT` at the top of the script, or set the environment variable `NA2_ROOT`).

| how | command |
|---|---|
| Windows, with a window | `"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --python make_figure.py` (adjust the version folder) |
| macOS, with a window | `/Applications/Blender.app/Contents/MacOS/Blender --python make_figure.py` |
| no window | add `-b` before `--python` |
| inside Blender | `Scripting` workspace, `Text > Open` the file, `Run Script`; or in the Python console / from an assistant that drives Blender: `import runpy; runpy.run_path(r"<folder>/make_figure.py", run_name="__main__")` |
| `bpy` module (how it was run here) | `NA2_MPFB_SRC=<clone>/mpfb2/src python make_figure.py` |

Do not start Blender with `--factory-startup`: it ignores the preferences in which MPFB is enabled.
It takes about 2 seconds. It prints lines starting with `NA2`; `NA2 problems: none` means everything worked.

What it does, in order:

1. Finds MPFB and enables it if needed (if it is not installed and `NA2_MPFB_SRC` points at the `src` folder of a
   source clone, it registers that folder as a local extension repository).
2. Removes the collection `NA2_figure` from an earlier run and makes it again. Nothing else in the scene is touched.
3. `HumanService.create_human(...)` with the macro values of the settings block (85 % female, young adult, slim,
   slightly low muscle, small bust, an even blend of the three ethnic macros), plus two bundled expression targets
   (lowered eyelids, 0.42).
4. `HumanService.add_builtin_rig(basemesh, "default")`.
5. Poses the rig: arms 16 degrees from the body, elbows bent 14 degrees, relaxed fingers and thumb, legs turned in
   4.4 degrees, neck straightened by 6 degrees. Adds two weighted Smooth modifiers (shoulder cap / armpit, web of
   the thumb).
6. Does 1-5 twice: the first pass only measures the posed height (1.618 m at MPFB's default scale), the second is
   made 1.0209 times larger so that the body is 1.652 m without any object scale. The rig is then lifted 16 mm (shoe
   sole) and moved 30 mm back, so the skull top is at 1.668 m; hair brings the figure to about 1.68 m.
7. Keys the arm bones: frame 1 = A-pose arms (as the base mesh comes), frame 41 = final pose, 9 keys. This is for
   draping: sew the shirt on frame 1, let the arms come down.
8. Bakes the static mesh `Body` (object and mesh name `Body`, material `Skin`, base mesh body faces only, plus two
   plain eyeball spheres at the base mesh's eye helpers), exports `out/body_mpfb.glb` (metres, Y up, faces +Z,
   wearer's left = +X), writes `out/figure.npz`, `out/figure_report.json`, saves `out/figure_mpfb.blend`.

In the saved scene: `Body` (static, the one that is exported), `NA2_basemesh` (hidden in the viewport because it sits
exactly inside `Body`; unhide it to use it as the cloth collision body, it follows the rig) and `NA2_rig`.

After changing things by hand (pose keys on `NA2_rig`, MPFB target sliders / shape keys on `NA2_basemesh`), write the
outputs again without rebuilding: `blender out/figure_mpfb.blend --python make_figure.py -- rebake` (or
`python make_figure.py rebake`). Key your pose changes on the last frame (`I`), because the bake steps through the
frames. `rebake` does not need MPFB. Running the script without `rebake` throws the hand-made changes away.

## 3. Settings (top of `make_figure.py`)

| numpy stage `../body/figure.py` `CFG` | here `FIG` | note |
|---|---|---|
| `female=0.85` | `gender=0.15` | MPFB: 0 = female, 1 = male |
| `slim=0.45` | `weight=0.2705` | `(1 - slim) * 0.50998 - 0.01` |
| `lowmuscle=0.25` | `muscle=0.3725` | `(1 - lowmuscle) * 0.50998 - 0.01` |
| `cup=-0.6` | `cupsize=0.194` | `(1 - 0.6) * 0.50998 - 0.01` |
| young, even ethnic blend | `age=0.5`, `race` 1/3 each | |
| `extra` (eyelids) | `extra_targets` | same target files |
| `body_height`, `sole`, `zshift=-0.030` | `body_height`, `sole`, `shift_back=0.030` | |
| `arm_abduction`, `elbow_flex`, `leg_in`, `thumb_*`, `neck_back` | same names | the pose code is a port of `figure.py` to Blender axes |

`height=0.5` and `proportions=0.5` mean "no target" in MPFB (0.49-0.51 is a dead zone for height). Height is set by
uniform scale, because the height target also changes proportions.

`../body/figure.py` was edited by the figure stage three times while this recipe was written (legs 2.6 -> 4.4
degrees, a closed thumb, a straightened neck). The values here match its state of 26 Nov 2026 12:00 UTC. If it has
changed again, change `FIG` and, for new pose logic, `pose_rotations()`; the comparison in section 4 shows at once
whether the two are in step (well under 1 mm on average when they are, several mm when they are not).

## 4. How it relates to the numpy stage in `../body/`

Both use the same CC0 MakeHuman data: base mesh `hm08` (19158 vertices in the same order: 13380 body + helper
geometry), the same target files (MPFB ships them gzipped), the same "default" skeleton (163 bones, same names) and
weights. The numpy stage reads the files itself; MPFB does it inside Blender and leaves a rigged human behind.

Measured, MPFB figure against `../body/out/figure.npz` (body vertices):

- unposed shape: mean 0.23 mm, 99 % under 1.8 mm, max 2.4 mm (bust: MPFB blends the four muscle/weight variants of
  the bust target as MakeHuman does, the numpy stage uses one);
- final pose: mean 0.25 mm, max 2.7 mm; shoulder, elbow, wrist, hip, knee, ankle joints within 0.4 mm;
- some joints *inside* limbs differ (up to 11 mm at `upperleg02`): MPFB's rig file places them differently from
  MakeHuman's `default.mhskel`. No effect on the surface.

`out/figure.npz` has the format of `../body/out/figure.npz` (`P`, `rest`, `anim`, `anim_t`, `jn`, `jh`, `jt`), so the
later numpy stages run on the MPFB figure unchanged:

    cp out/figure.npz ../body/out/figure.npz
    cd ../body && $BPY hair_bl.py && $BPY shoes_bl.py && python3 assemble.py      # build.sh without its figure.py line

Checked on a *copy* of `../body` (that folder belongs to the figure stage): result
`out/figure_mpfb_with_numpy_stages.glb` (Body 18772, Hair 5593, Pants 14496, Shoes 5600 triangles), renders in
`shots/with_numpy_stages/`.

Use the numpy stage for unattended rebuilds; use MPFB on the PC when the figure has to be touched in Blender.
`../current.glb` was not touched by this work.

## 5. Using MPFB from Python: what was found

- Services are reached by module name tail, because the package sits at `bl_ext.<repository>.mpfb`
  (`mp("mpfb.services.humanservice", "HumanService")` in the script; MPFB's own `script_samples/` do the same).
- Useful calls: `HumanService.create_human(scale=0.1, macro_detail_dict=...)` (0.1 = metres),
  `TargetService.get_default_macro_info_dict()`, `TargetService.load_target(obj, path, weight=...)`,
  `LocationService.get_mpfb_data("targets")`, `HumanService.add_builtin_rig(basemesh, "default")`
  (also `default_no_toes`, `game_engine`, `mixamo`, `mixamo_unity`, `cmu_mb`, `openpose`, `rigify.human`),
  `HumanService.add_mhclo_asset(path, basemesh, asset_type=...)`, `AssetService.find_asset_absolute_path(...)`.
- Gender: 0 = female, 1 = male (`data/targets/macrodetails/macro.json`). `script_samples/01` sets `gender 1.0` and
  all races 0 and calls it a woman: that comment is wrong.
- After creation the macro sliders are object properties (`HumanObjectProperties.set_value("gender", 0.15,
  entity_reference=basemesh)`, stored as `MPFB_HUM_gender` ...); apply with
  `TargetService.reapply_macro_details(basemesh)`. In the UI: sidebar tab `MPFB v2.0.x` > `Model` > `phenotype`.
- The buttons work from Python too, also without a window: `bpy.ops.mpfb.create_human()` reads the scene properties
  `MPFB_NH_*` (panel `New human > From scratch`; presets such as `phenotype_gender="female"` with
  `phenotype_influence`, not exact slider values), `bpy.ops.mpfb.add_standard_rig()` reads `MPFB_ADR_standard_rig`
  (panel `Rigging > Standard rig`).

Headless (no window) findings:

1. It works. `addon_utils.enable("bl_ext.<repo>.mpfb", default_set=True)` registers 151 operators in 0.5 s; a human
   is created in 0.25 s.
2. MPFB must be loaded as an extension. A plain `import mpfb` from `sys.path` fails in `register()` with
   `ValueError: The "package" does not name an extension` (it asks Blender for its extension user folder).
   From a source clone: add a local repository whose folder contains `mpfb/`
   (`preferences.extensions.repos.new(name=..., module=..., custom_directory=<clone>/src, source='USER')`), then enable.
3. Do not call `bpy.ops.wm.read_factory_settings()` after enabling MPFB: it removes the extension repositories and
   MPFB's lazy imports then fail (`'bl_ext' is not a package`). Reset first, enable afterwards.
4. MPFB writes logs and settings into Blender's user folder (`extensions/.user/<repo>/mpfb/` and `mpfb/`). To keep a
   test run away from the real user folder set `BLENDER_USER_RESOURCES` to an empty folder before starting.
5. The preference `mpfb_user_data` cannot be set before the first load (the preference class is registered inside
   `register()`); defaults are fine. `mh_user_data` takes effect at once.
6. The `bpy` pip module prints "Draco / MeshOptimizer library not found" on glTF export: harmless, no compression
   is used.

## 6. What is bundled and what needs asset packs

Bundled in the extension (`src/mpfb/data`, 74 MB), all CC0: the base mesh, 1258 target files (576 macro and bust
targets, 102 expression units, the rest detail targets), the rigs listed above with weights, a T-pose per rig, node tree definitions for skin and
eye shaders, a few small mask textures, UV layer and mesh metadata.

Not bundled: skins, eye meshes, eyebrows, eyelashes, hair, teeth, tongue, clothes, proxies ("topologies"), BVH poses,
ink layers. On a fresh install every library section is empty (checked: 0 assets in each).

| pack | needed for | where | licence |
|---|---|---|---|
| `makehuman_system_assets` | the standard skins, eyes, eyebrows, eyelashes, teeth, tongue, hair, clothes, proxies of MakeHuman; MPFB warns when it is missing | the page MPFB's "Get system assets" button opens: `https://static.makehumancommunity.org/assets/assetpacks/makehuman_system_assets.html` | **not stated in the repository.** These are the MakeHuman application's assets, which MakeHuman's `LICENSE.md` section C puts under CC0; confirm on the download page |
| other community packs (more skins, hair, clothes, poses ...) | optional | `http://static.makehumancommunity.org/assets/assetpacks.html` (button "All asset packs") | **not stated in the repository**, set per pack on its page. Assets carry their own licence line; MPFB's loader knows CC0, CC-BY and AGPL, so do not assume CC0 |
| MakeHuman's own `data` folder (already in `ext/makehuman`) | low-poly and high-poly eyes, default skin | no download: set the preference `mh_user_data` to that folder | CC0 (MakeHuman `LICENSE.md` section C) |

Install a pack: sidebar `MPFB` tab > `Apply assets` > `Library Settings` > `Load pack from zip file`
(`bpy.ops.mpfb.load_pack(filepath=...)`; the zip is unpacked into MPFB's user data folder). Not tried: no pack was
downloaded, the host is blocked here. Tried instead: with `mh_user_data` pointing at MakeHuman's `data` folder,
`HumanService.add_mhclo_asset(".../eyes/low-poly/low-poly.mhclo", basemesh, asset_type="Eyes")` loads and rigs the
eyes headless.

**This project needs none of them**: the figure is one plaster colour, the eyes are plain spheres, hair, trousers
and shoes are our own meshes.

## 7. Licences (as written in the MPFB repository)

- Add-on code, `LICENSE.md` section B: "The MPFB source (as defined per the above) is released under GPLv3."
  Manifest: `license = ["SPDX:GPL-3.0-or-later"]`.
- Bundled assets, section C: "The base mesh and proxies; Targets and modifiers; Textures; Clothes (any MHCLO-based
  asset); Rigs, poses and expressions; JSON data with mesh information" ... "These assets have been released under
  CC0 1.0 Universal."
- Output, section D: "regardless of whether you use the UI as such or if you call functions of MPFB via a script
  (such as an addon that extends MPFB), what you get is a combination of assets and your own creative input. As the
  assets have been released under CC0, there is no limitation on what you can do with this combined output." ...
  "the MakeHuman team makes no claim whatsoever over output such as: Exports to files (FBX, OBJ, DAE, MHX2...),
  Graphical data generated via scripting or plugins, Renderings, Screenshots, Saved model files".

`make_figure.py` calls MPFB but copies no MPFB code. The GLB contains only CC0 mesh data and our own numbers.

## 8. What remains manual

- **Hair, trousers, shoes**: not made here. Use the numpy stages on `out/figure.npz` (section 4) or model them in
  Blender.
- **Cutting the hidden body faces**: `body_mpfb.glb` is the whole body, 27548 triangles (the contract aims at 25k for
  the *visible* parts). `../body/assemble.py` cuts by rule (18772 left); the final cut should be made against the
  real shirt.
- **Shirt and prints**: other stages.
- **Changing the shape by hand** (MPFB `Model` sliders): afterwards press MPFB's refit for the rig, check the height
  in `figure_report.json` after `rebake` (the script does not rescale or re-ground on `rebake`).
- **A look at the face** by a person: it is an even blend of MakeHuman's stock macro targets and uses nothing from
  the reference photos, but nobody has judged it on a large screen.

## 9. Not verified

- Running in a Blender with a window, on Windows or macOS (`blender --python`, Text Editor). The script avoids
  window-only calls and was run through `runpy` inside an already running `bpy` session, twice in a row, but that is
  not the same thing.
- The MPFB build on extensions.blender.org: its version and that the site lists it at all (blocked host). If a call
  in the script does not exist there, update MPFB, or clone the repository at `650c5c5` and set `NA2_MPFB_SRC`.
- The installation clicks in section 1 and the panel names: from Blender's and MPFB's sources and documents, not
  from a screen.
- Asset pack names, contents and licences beyond what the repository says; installing a pack.
- Blender versions other than 5.3.0 (MPFB declares 4.2.0 as minimum).

## 10. Files

- `make_figure.py`: the recipe.
- `out/body_mpfb.glb`, `out/figure_mpfb.blend`, `out/figure.npz`, `out/figure_report.json`: its outputs.
- `out/figure_mpfb_with_numpy_stages.glb`: MPFB body + hair, trousers, shoes from a copy of the numpy stages.
- `shots/`: shared checker on `body_mpfb.glb` (warnings: no shirt, no prints, no trousers, as expected);
  `shots/with_numpy_stages/`: on the combined GLB (warnings: no shirt, no prints).
- `probe/`: the small scripts behind the findings above (`p01` load, `p02` human, `p04` operators and assets,
  `p05` plain import, `p06` installed extension and double run, `p07` rebake). They expect `_work/ext_repo/mpfb`
  to be a link to `<clone>/mpfb2/src/mpfb`.
- `_work/`: scratch (sandboxed Blender user folder, the link above, checker logs). Safe to delete.
