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
| `handoff/briefs/` | the complete instructions of the three jobs that were running in the cloud, with the path mapping |
| `intro/` | the cinematic intro: the owner's brief, the shot plan and prompts, the opening frame, the edit; `intro/ref/` holds the game frames and is local only |
| `out/`, `ext/`, `fonts/` | local outputs and downloads, not in git |

Scripts in `model/` were written for one fixed directory layout and then path-mapped to this one; they are meant to be run from the repository root and may need small path fixes. `model/body/common.py` expects the CC0 human base mesh at `work3d/ext/makehuman` (`git clone --depth 1 https://github.com/makehumancommunity/makehuman work3d/ext/makehuman`). Blender scripts need Python with `bpy` (Blender's own Python, or `pip install bpy`); set `BLENDER_PY` to that interpreter.

## State on 2026-11-26, 13:00 UTC

Decisions the owner made after the first version of this file (the sources are `spec/OWNER-FACTS.md` and `intro/BRIEF.md`; where older text in the spec disagrees, they win until the spec is updated):

- No visible text on the page except the giant „NA2“ behind the figure and one info block (material and price per shirt type, shipping). Two round colour swatches without text.
- Two shirt types, each in black and in white: a lighter, cheaper one (220 g/m² jersey) and a heavier, more expensive one (370 g/m² interlock). The figure wears both, switchable. A material view ("inspect") shows how the two differ, from the owner's text.
- A cinematic intro of about 12 seconds plays before the shop (`intro/BRIEF.md`), generated at 4K for every shot; the workspace of the generation service is on a paid plan since that day.
- The prints are built from the owner's original artwork (done: `art/`).

Done and in the repository: the page core (sign, figure, spin, camera walk, lights-out beat, static fallback), the build with budgets, both print textures, the figure (body, hair, trousers, shoes: `model/body/`, also as an MPFB2 recipe in `model/mpfb/`), the research notes, the merged spec.

The cloud session was stopped by the owner on 2026-11-26 at about 13:10 UTC and writes nothing more to this branch: the work continues locally. Three jobs were interrupted; their partial results are in the repository and none of them is verified. The full instructions each was working from are in `handoff/briefs/`.

1. The page without text (`merch/index.html`, `merch/v/src/`, `tests/`): the first stage was about forty minutes in. The visible controls module is being replaced (`merch/v/src/controls.js`), the plates are being removed and the timeline retimed. Start by building it and looking at it; expect loose ends. `spec/SPEC.md` and `spec/CONTENT-RULES.md` had not been updated to the owner's decision yet.
2. The lighter shirt on the figure: pattern generated, cloth mesh built, the drape was being tested (`model/light/README.md`). `model/current.glb` still carries a crude shirt shell.
3. The intro: only the data preparation for the opening frame exists (`intro/src/opening/`, sources in `intro/SOURCES.md`). The shot plan with prompts, the opening frame itself, the first-shot animatic, the intro player and the timed edit were not reached.

Not started:

- The heavier shirt (its pictures are `ref/shirt-heavy-*.png`), then the type switch and the material view on the page.
- Wiring the intro into the page and the screen recording the brief asks for.
- Generating the intro footage: it needs the four game frames in `intro/ref/`, which exist only on the owner's computer.
- The info block's values: prices and shipping have not been supplied.

What only the owner's computer can do, and where a local session should start: put the four game frames and the camera notes into `work3d/intro/ref/`; generate the intro shots as `intro/BRIEF.md` and `intro/PROMPTS.md` say (the street descent from frame 02 to frame 03 first); look at the page on a real GPU and on real phones; use Blender with a window; capture the street move in the game engine if the generator loses the street layout.

The model scripts expect one fixed directory layout; `model/make_root.sh` builds it from this repository's folders.

## House rules

- Work on branch `claude/friendly-cori-d4z8b5`. No pull request, no merge to `main` and nothing on the live site without the owner's explicit go-ahead. The page keeps `<meta name="robots" content="noindex">` until then.
- The repository is public. Never commit raw photos or video of a person, credentials, or third-party assets without a recorded licence.
- No fake shop mechanics (price, sizes, cart, stock, editions) and no unverified facts on the page: see `spec/CONTENT-RULES.md`.
- Everything the page loads is self-hosted under `/merch/`; no external requests.
- Third-party material and its licences are recorded in [`THIRD-PARTY.md`](THIRD-PARTY.md); add to it before using anything new.
