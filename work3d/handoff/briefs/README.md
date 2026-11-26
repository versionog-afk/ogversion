# Task briefs from the cloud session

The three jobs that were running in the cloud when the work moved (2026-11-26) were driven by these scripts. They are kept because the prose inside them is the complete, current instruction set for each job, including the owner's latest decisions:

| file | job | state when stopped |
|---|---|---|
| `page.js` | the page without text: remove text and controls, info block, colour swatches, then the rack and robustness features, a four-lens review, fixes, verification | first stage ("Strip") interrupted; its edits are in `merch/` and `work3d/tests/`, unverified |
| `model.js` | the figure (done), the MPFB2 recipe (done), the lighter shirt (interrupted), critique and refinement (not reached) | see `work3d/model/light/README.md` |
| `intro.js` | shot plan and prompts, opening frame and first-shot animatic, intro player, timed edit, verification | planning stage interrupted: only the data preparation for the opening frame exists (`work3d/intro/src/opening/`) |

They are orchestration scripts, not something to run as they are: read the text between the backticks as the brief for each stage. Paths: `<REPO>` is this repository; `<CLOUD>` was the cloud workspace, whose layout maps onto this repository as follows.

| in the briefs | here |
|---|---|
| `<CLOUD>/na2/model/` | `work3d/model/` (`v1` there is `light` here) |
| `<CLOUD>/na2/harness/` | `work3d/harness/` |
| `<CLOUD>/na2/art/` | `work3d/art/` |
| `<CLOUD>/na2/src/` | `work3d/ref/` (the owner's pictures and video; local only) |
| `<CLOUD>/ext/makehuman`, `<CLOUD>/ext/mpfb2` | `work3d/ext/` (clone again; not in git) |
| `<CLOUD>/v3/node_modules` | `work3d/node_modules` (`npm install` in `work3d/`) |
| `<CLOUD>/bvenv/bin/python` | a Python with `bpy`, or Blender's own |
| `<CLOUD>/tee/cand-B/teegen/` | `work3d/model/teegen/` |

`work3d/model/make_root.sh` recreates the `<CLOUD>` layout as symbolic links for the model scripts.
