"""Shared configuration of the NA2 garment stage (stage 2: the shirt on the figure). Pure Python, no Blender needed."""
import os, sys, json

# ---------------------------------------------------------------------------------------------------------------
# ROOT: the only machine-specific path of the Python scripts. It is the folder that holds
#   na2/ (this project: na2/model/body = the figure stage, na2/model/light = this garment stage, na2/art, na2/harness).
# Change it here, or set the environment variable NA2_ROOT (build.sh does that for every step).
ROOT = os.environ.get('NA2_ROOT') or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '_root'))  # see ../make_root.sh
# ---------------------------------------------------------------------------------------------------------------
HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = os.path.dirname(HERE)
BODY = os.path.join(MODEL, 'body')                 # the figure stage (scripts are imported from there, outputs are read)
ART = os.path.join(ROOT, 'na2', 'art')             # print artwork (read only)


def script_args():
    """command line arguments, also when run as  blender --background --python script.py -- args"""
    a = sys.argv
    if '--' in a: return a[a.index('--') + 1:]
    if any(x in ('--python', '-P', '--background', '-b') for x in a[1:]): return []
    return a[1:]


def load_spec(path=None):
    """the shirt specification (measurements.json by default, or the file given as first argument / NA2_SPEC)"""
    args = script_args()
    path = path or (args[0] if args and args[0].endswith('.json') else None) or os.environ.get('NA2_SPEC') or os.path.join(HERE, 'measurements.json')
    M = json.load(open(path))
    M['_path'] = os.path.abspath(path)
    fabs = json.load(open(os.path.join(HERE, 'fabrics.json')))
    if M['fabric'] not in fabs: raise SystemExit('fabric preset %r is not in fabrics.json' % M['fabric'])
    M['_fabric'] = fabs[M['fabric']]
    return M


def out_dir(M):
    """all intermediate and final files of one shirt specification live in out/<name>/"""
    d = os.path.join(HERE, 'out', M['name'])
    os.makedirs(d, exist_ok=True)
    return d


def log(*a):
    print(*a, flush=True)
