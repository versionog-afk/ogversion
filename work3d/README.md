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
| `art/` | print textures the build reads (`front.png` 3:2, `back.png` 3:4, `meta.json`) and `make_textures.py`, which builds them from the owner's original artwork |
| `ref/` | owner's originals; mostly local-only |
| `research/` | notes on tools found on GitHub, with licences and hardware needs |
| `out/`, `ext/`, `fonts/` | local outputs and downloads, not in git |

Scripts in `model/` were written for one fixed directory layout and then path-mapped to this one; they are meant to be run from the repository root and may need small path fixes. `model/body/common.py` expects the CC0 human base mesh at `work3d/ext/makehuman` (`git clone --depth 1 https://github.com/makehumancommunity/makehuman work3d/ext/makehuman`). Blender scripts need Python with `bpy` (Blender's own Python, or `pip install bpy`); set `BLENDER_PY` to that interpreter.

## State when the work moved

Works (seen in screenshots, not yet reviewed independently):

- Build pipeline with budgets; two-mode document (flat page and 3D page); loader line; gate; first paint without JavaScript.
- Scene: „NA2“ sign behind a transparent canvas, plaster figure, black shirt, trousers fading into the dark, both prints, lit copy of the back print, red line under the caption.
- Spin with inertia and front / back detents; the scroll story from the hero to the figure standing beside the rail; „Šviesa“, „Priekis“, „Nugara“, „Iš arti“.

Unfinished or unverified:

- The page builder was interrupted before its own verification finished: the interaction tests (`tests/test-int-na2.js`) and the layout sweep across viewports have not been run to the end, and the fallback tests (static mode, blocked files, timeout, no WebGL) still have to be written for this layout. Start there.
- The rack (nine photo panels, flick, tap to lightbox), the quality governor, context-loss recovery, calm mode with „Įjungti 3D“ and the opaque escape hatch are not built (`merch/v/src/rack.js` is a stub with the seam documented at the top).
- Model: only the body stage ran (figure, hair, trousers, shoes). The oversized shirt has not been simulated; the shirt in `current.glb` is a crude shell.
- Prints: done. `art/front.png` and `art/back.png` are built from the owner's original artwork by `art/make_textures.py` (the originals are in `ref/originals/`, local only). The back canvas is 3:4 with the artwork top-aligned at its true proportions, so the band under the caption is empty; `art/meta.json` holds the boxes of the artwork, the map and the caption. Ask the owner how wide the back print really is in centimetres.

## House rules

- Work on branch `claude/friendly-cori-d4z8b5`. No pull request, no merge to `main` and nothing on the live site without the owner's explicit go-ahead. The page keeps `<meta name="robots" content="noindex">` until then.
- The repository is public. Never commit raw photos or video of a person, credentials, or third-party assets without a recorded licence.
- No fake shop mechanics (price, sizes, cart, stock, editions) and no unverified facts on the page: see `spec/CONTENT-RULES.md`.
- Everything the page loads is self-hosted under `/merch/`; no external requests.
- Third-party material and its licences are recorded in [`THIRD-PARTY.md`](THIRD-PARTY.md); add to it before using anything new.
