#!/bin/bash
# Close-up contact sheets with the inspection viewer. Usage: bash tools/look.sh <model.glb> <view set name from tools/views.json> <out.png> [look=studio|clay|dark] [tile]
T=$(cd "$(dirname "$0")" && pwd)
V=$(python3 -c "import json,sys;print(json.dumps(json.load(open('$T/views.json'))['$2']))")
node $T/myshot.js "$1" "$3" "${4:-studio}" "$V" "${5:-520}"
