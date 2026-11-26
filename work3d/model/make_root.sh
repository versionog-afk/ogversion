#!/bin/sh
# The model scripts were written for one fixed directory layout ("NA2_ROOT"). This creates that layout inside
# work3d/_root as symbolic links onto the folders of this repository, so the scripts run unchanged:
#
#   sh work3d/model/make_root.sh          (from the repository root, once)
#   NA2_ROOT=work3d/_root is then the default of the scripts in work3d/model/body/
#
# Needs: work3d/ext/makehuman (git clone --depth 1 https://github.com/makehumancommunity/makehuman work3d/ext/makehuman),
#        work3d/node_modules (npm install in work3d/), and a Python with bpy for the Blender steps:
#        export BLENDER_PY=/path/to/python-with-bpy   (pip install bpy, or Blender's own Python)
set -e
W="$(cd "$(dirname "$0")/.." && pwd)"
R="$W/_root"
mkdir -p "$R/na2" "$R/ext" "$R/v3" "$R/bvenv/bin"
ln -sfn "$W/model"   "$R/na2/model"
ln -sfn "$W/harness" "$R/na2/harness"
ln -sfn "$W/art"     "$R/na2/art"
ln -sfn "$W/ref"     "$R/na2/src"
ln -sfn "$W/ext/makehuman" "$R/ext/makehuman"
ln -sfn "$W/node_modules"  "$R/v3/node_modules"
[ -n "$BLENDER_PY" ] && ln -sfn "$BLENDER_PY" "$R/bvenv/bin/python"
echo "layout ready in $R"
