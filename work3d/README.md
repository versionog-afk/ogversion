# work3d: tooling and hand-over for the 3D /merch page

Nothing in this folder is deployed (`.vercelignore` excludes it). It holds the spec, the build and test tools, the model and print pipelines and the notes needed to continue the work on another machine.

The owner-facing plan with the phases is in [`PLANAS.md`](PLANAS.md) (Lithuanian).

## What is being built

`/merch` (file `merch/index.html`, assets in `merch/v/`) as an interactive 3D page: a stylised human figure wearing the brand's real black oversized NA2 T-shirt (small „NA2“ lettering made of banknotes on the left chest, a white line map of Šilainiai on the back). The visitor spins the figure with a finger; scrolling pushes the camera into the chest print, walks it round to the back, switches the lights off so that only the map glows, and ends at a rack of nine photos. Without WebGL the same document is a flat page.

Binding documents: [`spec/SPEC.md`](spec/SPEC.md) (design, model contract, storyboard, budgets, tests) and [`spec/CONTENT-RULES.md`](spec/CONTENT-RULES.md) (facts, voice, allowed links).

## Quick start

```
git checkout claude/friendly-cori-d4z8b5
cd work3d && npm install            # three r187, esbuild, sharp, gltf-transform, playwright
npx playwright install chromium     # once, for the tests
npm run build                       # rebuilds merch/v/app.js and re-checks budgets (keeps committed assets)
npm run serve                       # http://127.0.0.1:8361/merch
npm run check-model                 # renders model/current.glb with the shared viewer into out/model-check/
PORT=8361 node tests/shots-na2.js 390x664     # storyboard screenshots into tests/shots-na2/
```

- `npm run build:full` rebuilds the model, print textures and photos too; it needs the owner's photos in `ref/` (see [`ref/README.md`](ref/README.md)).
- Headless Chromium renders WebGL in software, which the page's gate rejects on purpose: test URLs need `?3d=1`. Other hooks: `?3d=0`, `?q=0..3`, `?s=<scroll in screens>`, `window.__m`.
- On a real GPU and on real phones nothing has been measured yet. Do that early.

## Folder map

| path | what |
|---|---|
| `spec/` | the current build spec and the content rules |
| `harness/` | shared model viewer and contract checker (`shot.js`); every model version is judged with it, do not fork it per model |
| `tests/` | static server, storyboard screenshots, interaction and fallback tests for the page |
| `model/current.glb` | the model the page is built from: for now a stand-in (real body, crude shirt shell, two decals) |
| `model/body/` | figure pipeline: shape and pose from a CC0 base mesh, hair, trousers, shoes (`build.sh`), plus `body.glb` |
| `model/teegen/` | an earlier garment pipeline for a regular-fit tee: lofted shell, Blender cloth simulation, decal projection, normal / occlusion bake, GLB export. Reuse for the oversized shirt |
| `art/` | print textures the build reads (`front.png` 3:2, `back.png` 3:4, `meta.json`) and the unfinished scripts that were recovering them from the photos |
| `ref/` | owner's originals; mostly local-only |
| `research/` | notes on tools found on GitHub, with licences and hardware needs |
| `out/`, `ext/`, `fonts/` | local outputs and downloads, not in git |

Scripts in `model/` and `art/` were written for one fixed directory layout and then path-mapped to this one; they are meant to be run from the repository root and may need small path fixes. `model/body/common.py` expects the CC0 human base mesh at `work3d/ext/makehuman` (`git clone --depth 1 https://github.com/makehumancommunity/makehuman work3d/ext/makehuman`). Blender scripts need Python with `bpy` (Blender's own Python, or `pip install bpy`); set `BLENDER_PY` to that interpreter.

## State when the work moved

Works (seen in screenshots, not yet reviewed independently):

- Build pipeline with budgets; two-mode document (flat page and 3D page); loader line; gate; first paint without JavaScript.
- Scene: „NA2“ sign behind a transparent canvas, plaster figure, black shirt, trousers fading into the dark, both prints, lit copy of the back print, red line under the caption.
- Spin with inertia and front / back detents; the scroll story from the hero to the figure standing beside the rail; „Šviesa“, „Priekis“, „Nugara“, „Iš arti“.

Unfinished or unverified:

- The page builder was interrupted before its own verification finished: the interaction tests (`tests/test-int-na2.js`) and the layout sweep across viewports have not been run to the end, and the fallback tests (static mode, blocked files, timeout, no WebGL) still have to be written for this layout. Start there.
- The rack (nine photo panels, flick, tap to lightbox), the quality governor, context-loss recovery, calm mode with „Įjungti 3D“ and the opaque escape hatch are not built (`merch/v/src/rack.js` is a stub with the seam documented at the top).
- Model: only the body stage ran (figure, hair, trousers, shoes). The oversized shirt has not been simulated; the shirt in `current.glb` is a crude shell.
- Prints: `art/front.png` and `art/back.png` are rough threshold cut-outs. The clean front matte and the vector redraw of the map were in progress. Ask the owner for the original print files first.

## Phase 0 dry run in a cloud container (2026-11-26)

The hand-over prompt was run in a cloud session again, not on the owner's computer (no computer was attached). Everything that does not need the owner's hardware was checked there; the rest of phase 0 is still open.

Machine: Ubuntu 24.04 VM, 4 vCPU Intel Xeon 2.3 GHz, 15 GB RAM, no GPU (WebGL through SwiftShader), Node 22.23.5, Git 2.43.0, Python 3.13.18, no Blender.

- `npm install` and `npm run build`: ok; the build output is byte-identical to the committed files. First view 1198.5 KB of 2355.2 KB.
- `npm run check-model`: no contract warnings (63,307 triangles, 1.21 MB, 7 meshes).
- Page with `?3d=1` at 390 × 664: ready, tier 1, 6 to 9 draw calls, 63,311 triangles (67,503 in the dark beat), no console errors. Without `?3d=1` the inline gate rejects the software renderer and `app.js` is never loaded, so `window.__m` does not exist in flat mode.
- `tests/test-int-na2.js` ran to the end for the first time: 59 of 61 pass (3.5 min on software GL). The two failures:
  - Tab order. On a freshly loaded page the order is exactly the expected one. In the test it runs after the lightbox checks: the first Tab starts from the last opener (blurring does not reset the browser's starting point), and after the wrap to the top the four HUD controls are skipped because the keys are pressed with no pause while the HUD is still inert. Fix the test state (reload, or focus the top first); then check with a real keyboard whether the skip after the wrap can also happen at human speed.
  - Wiggle in the dark beat. The test wants the yaw to stay within ±35.5°; the page gives 45.5° for 180 px because the limit is soft (35°, then 0.35 of the travel), which is what the desktop close-up check accepts (35° to 70°). `spec/SPEC.md` has to say which is right.
- `npm run build:full` stops at `photo missing: work3d/ref/worn-back.jpg`, as expected without the owner's photos. It has already rewritten `merch/v/figure.glb` by then (63,307 triangles and 374,292 bytes against the committed 63,311 and 373,912): if the run fails, restore the file with `git checkout -- merch/v/figure.glb`.
- `package-lock.json` is now committed so that every machine resolves the same tool versions.
- In a cloud container the browser is pre-installed and `npx playwright install` must not be run: install the matching version instead (`npm install --no-save playwright@1.63.0` for Chromium build 1243). `blender.org` is not reachable from there; `bpy` 5.3.0 is on PyPI.

Still open from phase 0, all of it on the owner's computer: the hardware list (GPU and its memory), Blender, the page on a real GPU without `?3d=1` (`window.__m`, smooth spin and scroll), the originals in `ref/` and a full `npm run build:full`. `spec/` was not on the branch yet at the time of this run.

## House rules

- Work on branch `claude/friendly-cori-d4z8b5`. No pull request, no merge to `main` and nothing on the live site without the owner's explicit go-ahead. The page keeps `<meta name="robots" content="noindex">` until then.
- The repository is public. Never commit raw photos or video of a person, credentials, or third-party assets without a recorded licence.
- No fake shop mechanics (price, sizes, cart, stock, editions) and no unverified facts on the page: see `spec/CONTENT-RULES.md`.
- Everything the page loads is self-hosted under `/merch/`; no external requests.
- Third-party material and its licences are recorded in [`THIRD-PARTY.md`](THIRD-PARTY.md); add to it before using anything new.
