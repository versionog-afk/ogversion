#!/bin/bash
# Rebuilds the whole figure stage (about one minute).   Usage: bash build.sh [publish]
#   publish: also rebuild the stand-in (figure + crude shirt + decals), run the contract check on it and,
#            only if it has no warnings, atomically replace ../current.glb
# ---------------------------------------------------------------------------------------------------------------
# ROOT: the only machine-specific path. The folder that holds ext/makehuman (MakeHuman checkout), na2/ (this project)
# and, for the renders, v3/node_modules/three. Override with the environment variable NA2_ROOT.
ROOT="${NA2_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)/_root}"   # see ../README.md
# ---------------------------------------------------------------------------------------------------------------
export NA2_ROOT="$ROOT"
PY="${NA2_PY:-python3}"                         # any Python 3 with numpy
BPY="${NA2_BPY:-$ROOT/bvenv/bin/python}"        # a Python that can "import bpy"; with a normal Blender: NA2_BPY="blender --background --python"
HARNESS="$ROOT/na2/harness"                     # shared viewer and contract checker (optional: skipped when missing)
set -e
B="$(cd "$(dirname "$0")" && pwd)"
cd "$B"; mkdir -p out shots
$PY figure.py   > out/figure.log 2>&1           # shape + pose               -> out/figure.npz
$BPY hair_bl.py  > out/hair.log 2>&1            # hair                       -> out/hair.npz
$BPY shoes_bl.py > out/shoes.log 2>&1           # shoes                      -> out/shoes.npz
$PY assemble.py > out/assemble.log 2>&1         # trousers, cut, eyes        -> body.glb, collide.obj, collide_anim.npz, collide_apose.obj, landmarks.json
tail -8 out/assemble.log
$BPY check.py -- "$B/body.glb" > out/check.log 2>&1 || true     # mesh hygiene: fragments, borders, intersections -> out/check.json
grep -E "^(Body|Hair|Pants|Shoes|intersections)" out/check.log | cut -c1-230
if [ -f "$HARNESS/shot.js" ]; then
  (cd "$HARNESS" && node shot.js "$B/body.glb" "$B/shots/body" > "$B/out/shot-body.log" 2>&1) || true
  grep -A6 contractWarnings out/shot-body.log || true
fi
if [ "$1" = "publish" ]; then
  $PY standin.py "$B/out/standin.glb"
  (cd "$HARNESS" && node shot.js "$B/out/standin.glb" "$B/shots/standin" > "$B/out/shot-standin.log" 2>&1)
  if grep -q '"contractWarnings": \[\]' out/shot-standin.log && grep -q '"errors": \[\]' out/shot-standin.log; then
    cp out/standin.glb "$B/../current.tmp.glb" && mv "$B/../current.tmp.glb" "$B/../current.glb" && echo "published current.glb"
  else
    echo "stand-in has contract warnings or errors, not published"; grep -A8 contractWarnings out/shot-standin.log
  fi
fi
