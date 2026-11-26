# The lighter shirt on the figure: unfinished

This stage was interrupted about half an hour in (2026-11-26), when the work moved from the cloud to the owner's computer. Nothing here is verified.

What exists:

- `measurements.json`, `fabrics.json`, `settings.json`: the shirt specification (every dimension in one file), the fabric presets and the simulation settings. A second specification later gives the heavier shirt on the same figure.
- `pattern_gc.py`: the sewing pattern through the pattern classes of GarmentCode (pip package `pygarment` 2.0.2, MIT; only its pattern output is used, never its own simulator, whose licence is non-commercial). Outputs in `out/light/`: `pattern.json`, `pattern.png`, and GarmentCode's own files in `out/light/garmentcode/`.
- `teegeom.py`, `mesh.py`: panels to cloth mesh (`out/light/mesh.npz`, `mesh_edges.json`).
- `pose.py`: the figure's pose animation for dressing (`out/light/pose.npz`).
- `drape.py`: the Blender cloth drape. It was being tested when the work stopped; `out/light/drape_test.log` is its last output.
- `na2cfg.py`: shared configuration; the only machine path is `ROOT` (see `../make_root.sh`).

What is missing: a settled drape, the collar rib and hems, both print decals, the neck label, removal of hidden body faces, UVs with baked normal and occlusion maps, the export (`figure.glb`, `shirt-only.glb`, `body-only.glb`), the contract check and the comparison with the reference pictures.

The complete instructions for this stage, as they were given, are in `../../handoff/briefs/model.js` (search for "stage 2"), together with the owner's later update on the two shirt types. The figure builder's notes are in `../body/NOTES-for-garment.md`.
