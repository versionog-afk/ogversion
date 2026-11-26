#!/bin/bash
# Rebuilds the whole figure stage. Usage: bash build.sh [publish]
# publish: also rebuild the stand-in (figure + crude shirt + decals), check it and atomically replace ../current.glb
set -e
S=work3d   # run from the repository root
B=$S/model/body
BPY=${BLENDER_PY:-python}
cd $B; mkdir -p out shots
python3 figure.py > out/figure.log 2>&1          # shape + pose  -> out/figure.npz
$BPY hair_bl.py   > out/hair.log 2>&1            # hair          -> out/hair.npz
$BPY shoes_bl.py  > out/shoes.log 2>&1           # shoes         -> out/shoes.npz
python3 assemble.py > out/assemble.log 2>&1      # trousers, cut, body.glb, collide.obj, collide_anim.npz, landmarks.json
tail -8 out/assemble.log
(cd $S/harness && node shot.js $B/body.glb $B/shots/body > $B/out/shot-body.log 2>&1) || true
grep -A6 contractWarnings out/shot-body.log
if [ "$1" = "publish" ]; then
  python3 standin.py $B/out/standin.glb
  (cd $S/harness && node shot.js $B/out/standin.glb $B/shots/standin > $B/out/shot-standin.log 2>&1)
  if grep -q '"contractWarnings": \[\]' out/shot-standin.log; then
    cp out/standin.glb $S/model/current.tmp.glb && mv $S/model/current.tmp.glb $S/model/current.glb && echo "published current.glb"
  else
    echo "stand-in has contract warnings, not published"; grep -A8 contractWarnings out/shot-standin.log
  fi
fi
