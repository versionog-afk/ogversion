"""NA2 figure, MPFB2 route: shape, rig, pose and a static "Body" GLB made inside Blender with MPFB2.

Run it in any of these ways (see README.md):
    blender --python make_figure.py              GUI Blender, MPFB installed from extensions.blender.org
    blender -b --python make_figure.py           the same without a window
    python make_figure.py                        the "bpy" Python module (set NA2_MPFB_SRC if MPFB is not installed)
    Blender > Scripting > Text > Open make_figure.py > Run Script
After changes made by hand in Blender (pose keys on NA2_rig, shape keys on NA2_basemesh) write the outputs again with
    blender out/figure_mpfb.blend --python make_figure.py -- rebake        or        python make_figure.py rebake

What it makes, all under OUT:
    figure_mpfb.blend       the live MPFB human ("NA2_basemesh" + "NA2_rig", arms animated from the A-pose down to
                            the final pose, for cloth draping) and the baked static mesh "Body" (material "Skin")
    body_mpfb.glb           "Body" only: metres, Y up, the figure faces +Z, wearer's left = +X
    figure.npz              the same figure in the format of ../body/out/figure.npz, so the existing numpy stages
                            (hair, trousers, shoes, cutting of hidden faces, collision set, landmarks) run on it unchanged
    figure_report.json      versions, macro values, the target stack MPFB applied, sizes, joints

Only bundled MPFB2 data is used (base mesh, targets, default rig and weights: all CC0). No asset pack is needed.
"""
import os, sys, json, math, time, importlib

# =====================================================================================================================
# SETTINGS  (the only block to edit)
# ROOT is the single machine dependent location; by default it is the folder this file is in.
ROOT = os.environ.get("NA2_ROOT") or os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "out")
# Only when MPFB is NOT installed as an extension: the "src" folder of a clone of github.com/makehumancommunity/mpfb2
# (the folder that contains the package folder "mpfb"). Empty = use the installed extension.
MPFB_SRC = os.environ.get("NA2_MPFB_SRC", "")

FIG = dict(
    # --- shape: the macro sliders of MPFB ("New human" / "Model > Phenotype"), all 0..1 -------------------------
    gender=0.15,          # 0 = female, 1 = male          (85 % female)
    age=0.5,              # 0.5 = young adult (about 25)
    muscle=0.3725,        # 0.5 = average; this is 25 % "minmuscle" + 75 % "averagemuscle"
    weight=0.2705,        # 0.5 = average; this is 45 % "minweight"  + 55 % "averageweight"   (slim)
    proportions=0.5,      # 0.5 = no proportion target
    height=0.5,           # 0.5 = no height target; the final height is set by uniform scale, see body_height
    cupsize=0.194,        # 60 % "mincup"
    firmness=0.5,
    race=dict(asian=1 / 3, caucasian=1 / 3, african=1 / 3),          # an even blend: a generic face, nobody's likeness
    # extra targets from the bundled target folder: (path below data/targets without ".target.gz", weight)
    extra_targets=[("expression/units/caucasian/eye-left-closure", 0.42),      # calm, lowered lids
                   ("expression/units/caucasian/eye-right-closure", 0.42)],
    # --- size and placement ---------------------------------------------------------------------------------------
    body_height=1.652,    # metres, sole of the foot to the top of the skull, in the final pose (hair adds about 1 cm)
    sole=0.016,           # the bare foot stands this high above the floor (thickness of the shoe sole)
    shift_back=0.030,     # the figure is moved this far towards its back, so that the torso is centred on the origin
    # --- rig and pose ---------------------------------------------------------------------------------------------
    rig="default",        # MPFB built-in rig; the pose code below expects the bone names of "default"
    arm_abduction=16.0,   # final angle of the upper arm from the vertical, degrees
    elbow_flex=14.0,      # final bend of the elbow, degrees
    leg_in=4.4,           # each leg turned inwards by this many degrees (ankles about 0.23 m apart)
    finger_close=0.55,    # 0..1, how much the fan of the fingers is closed
    thumb_adduct=0.75,    # share of the rest angle between thumb and index finger that is closed
    thumb_palmar=0.7,     # how far in front of the palm the closed thumb aims (0 = straight at the index finger)
    thumb_curl=(6.0, 10.0, 12.0),      # flexion of the three thumb bones, degrees
    neck_back=6.0,        # degrees the neck is straightened by (the head is turned back by the same: the face stays level)
    shoulder_smooth=(0.5, 3),          # Smooth modifier (factor, repeat) where the arm blends into the torso; None = off
    thumb_web_smooth=(0.6, 4),         # the same for the web between thumb and index finger; None = off
    anim_frames=(1, 41),  # the arms go from the A-pose (first frame) to the final pose (last frame), 9 keys
    anim_samples=9,
    # --- output ---------------------------------------------------------------------------------------------------
    eyes="spheres",       # "spheres": plain eyeballs at the base mesh's eye helpers, joined into Body; "none": empty sockets
    skin_colour=(0.84, 0.81, 0.76, 1.0), skin_roughness=0.62,
    save_blend=True, write_npz=True,
)
# =====================================================================================================================

if "bpy" not in sys.modules and MPFB_SRC and not os.environ.get("BLENDER_USER_RESOURCES") and os.environ.get("NA2_SANDBOX"):
    # optional, bpy module only: keep Blender's and MPFB's user files (logs, preferences) inside ROOT
    os.environ["BLENDER_USER_RESOURCES"] = os.path.join(ROOT, "_work", "blender_user")

import bpy
import numpy as np
from mathutils import Vector, Matrix

PROBLEMS = []          # things that did not work as planned; printed at the end and written into the report


def note(msg):
    print("NA2 !", msg); PROBLEMS.append(msg)


# ---------------------------------------------------------------------------------------------------------------------
# MPFB: find it, enable it, reach its services
def _mpfb_module():
    for name, mod in list(sys.modules.items()):
        if name.endswith(".mpfb") and (getattr(mod, "MPFB_CONTEXTUAL_INFORMATION", None) or getattr(mod, "ClassManager", None)):
            return name                                            # imported AND registered
    return None


def ensure_mpfb():
    """returns the module name of the enabled MPFB extension (normally "bl_ext.blender_org.mpfb")"""
    import addon_utils
    name = _mpfb_module()
    if name:
        return name
    tried = []
    installed = [m.__name__ for m in addon_utils.modules(refresh=True) if m.__name__.split(".")[-1] == "mpfb"]
    for cand in installed:
        tried.append(cand)
        if addon_utils.enable(cand, default_set=True) is not None and _mpfb_module():
            return _mpfb_module()
    if MPFB_SRC:
        src = os.path.abspath(MPFB_SRC)
        if not os.path.isfile(os.path.join(src, "mpfb", "blender_manifest.toml")):
            raise RuntimeError("NA2_MPFB_SRC must be the folder that contains mpfb/blender_manifest.toml: " + src)
        repos = bpy.context.preferences.extensions.repos
        if "na2_mpfb_src" not in [r.module for r in repos]:
            repos.new(name="NA2 MPFB source", module="na2_mpfb_src", custom_directory=src, source='USER')
        tried.append("bl_ext.na2_mpfb_src.mpfb")
        if addon_utils.enable("bl_ext.na2_mpfb_src.mpfb", default_set=True) is not None and _mpfb_module():
            return _mpfb_module()
    raise RuntimeError("MPFB2 is not available (tried %s). Install it: Edit > Preferences > Get Extensions > search "
                       "\"MPFB\" > Install, or set NA2_MPFB_SRC to the src folder of a source clone." % (tried or "nothing"))


def mp(package_tail, key):
    """MPFB lives at an unknown place in the module tree (bl_ext.<repository>.mpfb), so look it up by its tail"""
    for name in list(sys.modules):
        if name.endswith(package_tail):
            return getattr(importlib.import_module(name), key)
    raise ImportError("MPFB module not loaded: " + package_tail)


# ---------------------------------------------------------------------------------------------------------------------
# scene helpers
COLLECTION = "NA2_figure"


def fresh_collection():
    """remove what an earlier run of this script made, make the collection again and make it the active one"""
    old = bpy.data.collections.get(COLLECTION)
    if old:
        for ob in list(old.all_objects):
            data = ob.data
            bpy.data.objects.remove(ob, do_unlink=True)
            if data is not None and data.users == 0:
                if isinstance(data, bpy.types.Mesh):
                    bpy.data.meshes.remove(data)
                elif isinstance(data, bpy.types.Armature):
                    bpy.data.armatures.remove(data)
        bpy.data.collections.remove(old)
    for act in [a for a in bpy.data.actions if a.name.startswith("NA2_")]:
        bpy.data.actions.remove(act)
    col = bpy.data.collections.new(COLLECTION)
    bpy.context.scene.collection.children.link(col)
    lc = bpy.context.view_layer.layer_collection.children.get(COLLECTION)
    if lc is not None:
        bpy.context.view_layer.active_layer_collection = lc
    return col


def into_collection(ob, col):
    for c in list(ob.users_collection):
        if c is not col:
            c.objects.unlink(ob)
    if ob.name not in col.objects:
        col.objects.link(ob)


def world_coords(ob):
    """evaluated (shape keys + modifiers) vertex positions in world space, Blender axes"""
    dg = bpy.context.evaluated_depsgraph_get(); dg.update()
    ev = ob.evaluated_get(dg); me = ev.to_mesh()
    co = np.empty(len(me.vertices) * 3, dtype=np.float32); me.vertices.foreach_get("co", co)
    M = np.array(ev.matrix_world, dtype=np.float64)
    ev.to_mesh_clear()
    return co.reshape(-1, 3).astype(np.float64) @ M[:3, :3].T + M[:3, 3]


def gl(a):
    """Blender axes (Z up, the figure looks along -Y) -> model contract axes (Y up, the figure looks along +Z)"""
    a = np.asarray(a, dtype=np.float64)
    return np.stack([a[..., 0], a[..., 2], -a[..., 1]], axis=-1)


# ---------------------------------------------------------------------------------------------------------------------
# shape
def macro_dict(cfg):
    TargetService = mp("mpfb.services.targetservice", "TargetService")
    m = TargetService.get_default_macro_info_dict()
    for k in ("gender", "age", "muscle", "weight", "proportions", "height", "cupsize", "firmness"):
        m[k] = float(cfg[k])
    m["race"] = {k: float(v) for k, v in cfg["race"].items()}
    return m


def create_human(cfg, scale):
    HumanService = mp("mpfb.services.humanservice", "HumanService")
    TargetService = mp("mpfb.services.targetservice", "TargetService")
    LocationService = mp("mpfb.services.locationservice", "LocationService")
    bm = HumanService.create_human(mask_helpers=True, detailed_helpers=True, extra_vertex_groups=True,
                                   feet_on_ground=True, scale=scale, macro_detail_dict=macro_dict(cfg))
    troot = LocationService.get_mpfb_data("targets")
    for rel, w in cfg["extra_targets"]:
        path = os.path.join(troot, *rel.split("/")) + ".target.gz"
        if not os.path.exists(path):
            note("extra target not found, skipped: " + rel); continue
        TargetService.load_target(bm, path, weight=float(w))
    return bm


# ---------------------------------------------------------------------------------------------------------------------
# pose: the same construction as ../body/figure.py, written for Blender axes.
# Every rotation is given in armature space about the rest head of its bone and composed down the hierarchy.
def pose_rotations(arm, cfg, arm_t=1.0):
    B = arm.data.bones
    FRONT = Vector((0.0, -1.0, 0.0))                 # MPFB humans look along -Y
    head = lambda b: B[b].head_local.copy()
    tail = lambda b: B[b].tail_local.copy()
    R = lambda axis, deg: Matrix.Rotation(math.radians(deg), 3, axis.normalized())
    rots = {}; info = {}
    for side, sx in (("L", 1.0), ("R", -1.0)):
        sh, el, wr = head("upperarm01." + side), head("lowerarm01." + side), head("wrist." + side)
        d = el - sh
        ang0 = math.degrees(math.atan2(sx * d.x, -d.z))            # abduction of the rest (A-pose) arm
        total = (ang0 - cfg["arm_abduction"]) * arm_t
        sgn = -sx                                                  # bringing the left arm down is negative about FRONT
        rots["clavicle." + side] = R(FRONT, sgn * 1.0 * arm_t)
        rots["shoulder01." + side] = R(FRONT, sgn * 5.5 * arm_t)
        rots["upperarm01." + side] = R(FRONT, sgn * (total - 6.5 * arm_t))
        u = d.normalized(); f = (wr - el).normalized()
        bend0 = math.degrees(u.angle(f))
        rots["lowerarm01." + side] = R(u.cross(f), (cfg["elbow_flex"] - bend0) * arm_t)
        info[side] = dict(rest_abduction=round(ang0, 2), rest_elbow_bend=round(bend0, 2))
        # fingers: a gentle curl towards the palm, the fan of the fingers closed a little
        th, pk, ix = head("finger1-1." + side), head("finger5-1." + side), head("finger2-1." + side)
        npalm = (ix - wr).normalized().cross(th - pk).normalized()
        if npalm.z > 0:
            npalm = -npalm                                         # in the A-pose the palm looks down / inwards
        mid = (tail("finger3-1." + side) - head("finger3-1." + side)).normalized()
        for k, angs in {2: (12, 20, 12), 3: (16, 26, 14), 4: (20, 30, 16), 5: (24, 32, 18)}.items():
            for j, a in zip((1, 2, 3), angs):
                b = "finger%d-%d.%s" % (k, j, side)
                dd = (tail(b) - head(b)).normalized()
                rot = R(dd.cross(npalm), a)
                if j == 1 and k != 3:
                    dp = dd - dd.dot(npalm) * npalm; mp_ = mid - mid.dot(npalm) * npalm
                    ang = math.degrees(math.atan2(dp.cross(mp_).dot(npalm), dp.dot(mp_)))
                    rot = rot @ R(npalm, cfg["finger_close"] * ang)
                rots[b] = rot
        # thumb: the base mesh holds it wide open; bring it next to the index finger (relaxed hand), then a slight curl
        tdir = (tail("finger1-3." + side) - head("finger1-1." + side)).normalized()
        idir = (tail("finger2-1." + side) - head("metacarpal1." + side)).normalized()
        idir = (idir + cfg["thumb_palmar"] * npalm).normalized()   # aim a little in front of the palm, not into its edge
        axt = tdir.cross(idir)
        open_ang = math.degrees(math.asin(min(1.0, axt.length)))
        r_adduct = R(axt, cfg["thumb_adduct"] * open_ang)
        target = -0.8 * (th - pk).normalized() + 0.45 * npalm       # the thumb flexes across the palm and a little into it
        for j, a in zip((1, 2, 3), cfg["thumb_curl"]):
            b = "finger1-%d.%s" % (j, side)
            dd = (tail(b) - head(b)).normalized()
            rot = R(dd.cross(target), a)
            rots[b] = (r_adduct @ rot) if j == 1 else rot
        info[side]["thumb_opening_at_rest"] = round(open_ang, 2)
        rots["upperleg01." + side] = R(FRONT, -sx * cfg["leg_in"])
        rots["foot." + side] = R(FRONT, sx * cfg["leg_in"])        # the sole stays flat on the floor
    # posture: the base mesh carries the head a little forward; bring it back over the shoulders, face level
    nk = cfg.get("neck_back", 0.0)
    if nk:
        X = Vector((1.0, 0.0, 0.0))
        rots["neck01"] = R(X, -0.6 * nk); rots["neck02"] = R(X, -0.4 * nk); rots["head"] = R(X, nk)
    return rots, info


def apply_pose(arm, rots):
    for name, rot in rots.items():
        pb = arm.pose.bones[name]
        m3 = arm.data.bones[name].matrix_local.to_3x3()
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = (m3.inverted() @ rot @ m3).to_quaternion()
    bpy.context.view_layer.update()


def add_blend_smooth(bm, label, prefixes, factor_repeat, z_min=None):
    """a weighted Smooth modifier after the armature, strongest where the listed bones share a vertex half and half
    with the rest of the body (the same corrective smoothing as ../body/figure.py does in numpy)"""
    if not factor_repeat:
        return
    n = len(bm.data.vertices); w = np.zeros(n)
    gidx = {g.index for g in bm.vertex_groups if g.name.startswith(prefixes)}
    for v in bm.data.vertices:
        for g in v.groups:
            if g.group in gidx:
                w[v.index] += g.weight
    mask = np.clip(4 * w * (1 - w), 0, 1)
    if z_min is not None:
        mask *= np.array([(bm.matrix_world @ v.co).z for v in bm.data.vertices]) > z_min
    vg = bm.vertex_groups.new(name="NA2_" + label)
    for i in np.where(mask > 0.02)[0]:
        vg.add([int(i)], float(mask[i]), 'REPLACE')
    mod = bm.modifiers.new("NA2 " + label, 'SMOOTH')
    mod.factor, mod.iterations = factor_repeat
    mod.vertex_group = vg.name


def build_rigged(cfg, scale, col):
    """base mesh + targets + rig + final pose. returns (basemesh, armature, pose info)"""
    HumanService = mp("mpfb.services.humanservice", "HumanService")
    bm = create_human(cfg, scale)
    arm = HumanService.add_builtin_rig(bm, cfg["rig"])
    if arm is None:
        raise RuntimeError("MPFB could not create the rig " + cfg["rig"])
    into_collection(bm, col); into_collection(arm, col)
    z_spine = (arm.matrix_world @ arm.data.bones["spine02"].head_local).z
    add_blend_smooth(bm, "shoulder_smooth", ("upperarm", "shoulder01", "lowerarm"), cfg["shoulder_smooth"], z_min=z_spine)
    add_blend_smooth(bm, "thumb_web_smooth", ("finger1-",), cfg["thumb_web_smooth"] if cfg["thumb_adduct"] > 0 else None)
    rots, info = pose_rotations(arm, cfg, 1.0)
    apply_pose(arm, rots)
    return bm, arm, info


def body_mask(bm):
    gi = bm.vertex_groups["body"].index
    return np.array([any(g.group == gi for g in v.groups) for v in bm.data.vertices])


def group_verts(bm, name):
    gi = bm.vertex_groups[name].index
    return np.array([v.index for v in bm.data.vertices if any(g.group == gi for g in v.groups)])


def full_coords(bm, smooth=True):
    """all 19158 base mesh vertices (helpers included) as posed now"""
    hidden = [m for m in bm.modifiers if (m.type == 'MASK' or (m.type == 'SMOOTH' and not smooth)) and m.show_viewport]
    for m in hidden:
        m.show_viewport = False
    co = world_coords(bm)
    for m in hidden:
        m.show_viewport = True
    return co


# ---------------------------------------------------------------------------------------------------------------------
# the static Body mesh
def uv_sphere(c, r, nu=18, nv=12):
    vs = []; fs = []
    for j in range(nv + 1):
        ph = math.pi * j / nv
        for i in range(nu):
            th = 2 * math.pi * i / nu
            vs.append((c[0] + r * math.sin(ph) * math.cos(th), c[1] + r * math.sin(ph) * math.sin(th), c[2] + r * math.cos(ph)))
    for j in range(nv):
        for i in range(nu):
            a = j * nu + i; b = j * nu + (i + 1) % nu; cc = (j + 1) * nu + (i + 1) % nu; d = (j + 1) * nu + i
            if j > 0: fs.append((a, d, cc))
            if j < nv - 1: fs.append((a, cc, b))
    return vs, fs


def make_body(bm, P, inbody, cfg, col):
    polys = [tuple(p.vertices) for p in bm.data.polygons]
    polys = [p for p in polys if all(inbody[i] for i in p)]
    used = np.unique(np.array([i for p in polys for i in p]))
    remap = -np.ones(len(P), dtype=np.int64); remap[used] = np.arange(len(used))
    verts = [tuple(v) for v in P[used]]
    faces = [tuple(int(remap[i]) for i in p) for p in polys]
    eyes = {}
    if cfg["eyes"] == "spheres":
        for side, g in (("L", "helper-l-eye"), ("R", "helper-r-eye")):
            gi = group_verts(bm, g); c = P[gi].mean(0); r = float(np.linalg.norm(P[gi] - c, axis=1).mean())
            sv, sf = uv_sphere(c, r * 0.985)
            o = len(verts); verts += sv; faces += [tuple(i + o for i in f) for f in sf]
            eyes[side] = dict(center=c, radius=r)
    me = bpy.data.meshes.new("Body")
    me.from_pydata(verts, [], faces); me.update()
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    mat = bpy.data.materials.get("Skin") or bpy.data.materials.new("Skin")
    if not (mat.node_tree and mat.node_tree.nodes):
        mat.use_nodes = True                                       # Blender 4.x; from 5.0 on materials always have nodes
    mat.use_backface_culling = True                                # -> "doubleSided": false in the GLB
    bsdf = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bsdf:
        bsdf.inputs["Base Color"].default_value = cfg["skin_colour"]
        bsdf.inputs["Roughness"].default_value = cfg["skin_roughness"]
        bsdf.inputs["Metallic"].default_value = 0.0
    mat.diffuse_color = cfg["skin_colour"]
    me.materials.append(mat)
    old = bpy.data.objects.get("Body")
    if old is not None:
        old.name = "Body.old"; note("an object called Body already existed outside %s; it was renamed Body.old" % COLLECTION)
    ob = bpy.data.objects.new("Body", me)
    col.objects.link(ob)
    return ob, eyes, len(used)


def export_glb(ob, path):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    ob.select_set(True); bpy.context.view_layer.objects.active = ob
    want = dict(filepath=path, export_format='GLB', use_selection=True, export_yup=True, export_apply=False,
                export_texcoords=False, export_normals=True, export_materials='EXPORT', export_animations=False,
                export_skins=False, export_morph=False, export_cameras=False, export_lights=False, export_extras=False)
    known = {p.identifier for p in bpy.ops.export_scene.gltf.get_rna_type().properties}
    bpy.ops.export_scene.gltf(**{k: v for k, v in want.items() if k in known})


def read_glb(path):
    """mesh / material names, triangle count and bounding box of a GLB, to check what was really written"""
    import struct
    with open(path, "rb") as f:
        data = f.read()
    n = struct.unpack_from("<I", data, 12)[0]
    j = json.loads(data[20:20 + n].decode("utf-8"))
    out = dict(bytes=len(data), meshes=[])
    for node in j.get("nodes", []):
        if "mesh" not in node:
            continue
        m = j["meshes"][node["mesh"]]
        tris = 0; lo = [1e9] * 3; hi = [-1e9] * 3; mats = []
        for p in m["primitives"]:
            tris += j["accessors"][p["indices"]]["count"] // 3
            a = j["accessors"][p["attributes"]["POSITION"]]
            lo = [min(x, y) for x, y in zip(lo, a["min"])]; hi = [max(x, y) for x, y in zip(hi, a["max"])]
            mats.append(j["materials"][p["material"]]["name"] if "material" in p else None)
        out["meshes"].append(dict(node=node.get("name"), mesh=m.get("name"), materials=mats, triangles=tris,
                                  min=[round(x, 4) for x in lo], max=[round(x, 4) for x in hi],
                                  node_has_transform=any(k in node for k in ("matrix", "rotation", "scale", "translation"))))
    return out


# ---------------------------------------------------------------------------------------------------------------------
def sample_frames(cfg):
    f0, f1 = cfg["anim_frames"]
    ts = np.linspace(0.0, 1.0, int(cfg["anim_samples"]))
    return ts, [int(round(f0 + (f1 - f0) * float(t))) for t in ts]


def key_animation(arm, cfg):
    """keys on the posed bones: first frame = A-pose arms ... last frame = final pose. True if it worked"""
    scene = bpy.context.scene
    ts, frs = sample_frames(cfg)
    try:
        posed = list(pose_rotations(arm, cfg, 1.0)[0])
        for t, fr in zip(ts, frs):
            apply_pose(arm, pose_rotations(arm, cfg, float(t))[0])
            for b in posed:
                arm.pose.bones[b].keyframe_insert("rotation_quaternion", frame=fr)
        if arm.animation_data and arm.animation_data.action:
            arm.animation_data.action.name = "NA2_arms_down"
        scene.frame_start, scene.frame_end = frs[0], frs[-1]
        scene.frame_set(frs[-1])
        return True
    except Exception as e:                                         # the static outputs do not depend on the keys
        note("could not key the arm animation: %r" % (e,))
        apply_pose(arm, pose_rotations(arm, cfg, 1.0)[0])
        return False


def bake(bm, arm, cfg, col, set_sample, report):
    """the static outputs from the live figure: Body, body_mpfb.glb, figure.npz, figure_report.json, figure_mpfb.blend.
    set_sample(t, frame) must put the rig into the pose of the arm animation at t (0 = A-pose arms, 1 = final)"""
    t0 = time.time()
    try:
        bm.hide_set(False)                                         # a hidden object is not evaluated
    except RuntimeError:
        pass
    old = bpy.data.objects.get("Body")
    if old is not None and col in old.users_collection:            # the one an earlier bake made
        me = old.data; bpy.data.objects.remove(old, do_unlink=True)
        if me.users == 0:
            bpy.data.meshes.remove(me)
    inbody = body_mask(bm)
    ts, frs = sample_frames(cfg)
    frames = []
    for t, fr in zip(ts, frs):
        set_sample(float(t), fr)
        frames.append(full_coords(bm))
    P = frames[-1]
    joints = {pb.name: (np.array(arm.matrix_world @ pb.head), np.array(arm.matrix_world @ pb.tail)) for pb in arm.pose.bones}
    arm.data.pose_position = 'REST'; bpy.context.view_layer.update()
    rest = full_coords(bm, smooth=False)
    arm.data.pose_position = 'POSE'; bpy.context.view_layer.update()

    body, eyes, n_body_verts = make_body(bm, P, inbody, cfg, col)
    glb = os.path.join(OUT, "body_mpfb.glb")
    export_glb(body, glb)
    written = read_glb(glb)
    body.select_set(False)
    bm.hide_render = True                                          # the baked Body is the one to look at;
    try:                                                           # the live base mesh sits exactly inside it
        bm.hide_set(True)
    except RuntimeError:
        pass

    if cfg["write_npz"]:
        names = list(joints.keys())
        np.savez(os.path.join(OUT, "figure.npz"), P=gl(P), rest=gl(rest), anim=np.array([gl(f) for f in frames]), anim_t=ts,
                 jn=np.array(names), jh=np.array([gl(joints[k][0]) for k in names]), jt=np.array([gl(joints[k][1]) for k in names]))
    keys = bm.data.shape_keys.key_blocks if bm.data.shape_keys else []
    J = lambda b, i=0: [round(float(x), 5) for x in gl(joints[b][i])] if b in joints else None
    Pb = gl(P[inbody])
    report = dict(report)
    report.update(
        blender=bpy.app.version_string, background=bool(bpy.app.background), settings={k: v for k, v in cfg.items()},
        shape_keys=[[k.name, round(k.value, 4)] for k in keys],
        units="metres, Y up, the figure faces +Z, wearer's left = +X, floor y = 0",
        body_bbox=[[round(float(x), 4) for x in Pb.min(0)], [round(float(x), 4) for x in Pb.max(0)]],
        base_mesh_vertices=int(len(P)), body_vertices=int(n_body_verts),
        eyes={k: dict(center=[round(float(x), 5) for x in gl(v["center"])], radius=round(v["radius"], 5)) for k, v in eyes.items()},
        joints={n: J(b) for n, b in (("shoulder_joint_L", "upperarm01.L"), ("elbow_L", "lowerarm01.L"), ("wrist_L", "wrist.L"),
                                     ("hip_joint_L", "upperleg01.L"), ("knee_L", "lowerleg01.L"), ("ankle_L", "foot.L"),
                                     ("neck_base", "neck01"), ("head", "head"))},
        fingertip_L=J("finger3-3.L", 1), glb=written, problems=PROBLEMS)
    report["seconds"] = round(report.get("seconds", 0.0) + time.time() - t0, 1)
    with open(os.path.join(OUT, "figure_report.json"), "w") as f:
        json.dump(report, f, indent=1, default=lambda o: list(o) if isinstance(o, (tuple, set)) else str(o))
    if cfg["save_blend"]:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "figure_mpfb.blend"))
    print("NA2 body bbox %s .. %s" % (report["body_bbox"][0], report["body_bbox"][1]))
    print("NA2 wrote", glb, json.dumps(written))
    print("NA2 problems:", PROBLEMS or "none")
    return report


def main(cfg=FIG):
    """make the figure from nothing"""
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    modname = ensure_mpfb()
    mpfb = importlib.import_module(modname)
    TargetService = mp("mpfb.services.targetservice", "TargetService")
    print("NA2 MPFB", getattr(mpfb, "VERSION", "?"), "as", modname, "| Blender", bpy.app.version_string,
          "| background" if bpy.app.background else "| GUI")
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'; scene.unit_settings.scale_length = 1.0

    # pass 1 at MPFB's default scale: only to measure the posed body height
    col = fresh_collection()
    bm, arm, info = build_rigged(cfg, 0.1, col)
    inbody = body_mask(bm)
    P = full_coords(bm)
    h_natural = float(P[inbody, 2].max() - P[inbody, 2].min())
    scale = 0.1 * cfg["body_height"] / h_natural

    # pass 2 at the final scale, so that mesh and rig are in true metres without any object scale
    col = fresh_collection()
    bm, arm, info = build_rigged(cfg, scale, col)
    bm.name = bm.data.name = "NA2_basemesh"; arm.name = arm.data.name = "NA2_rig"
    P = full_coords(bm)
    arm.location = Vector((0.0, cfg["shift_back"], cfg["sole"] - float(P[inbody, 2].min())))
    bpy.context.view_layer.update()
    P = full_coords(bm)

    # the arms coming down, for draping: the shirt is sewn on the A-pose and the arms then go down
    if key_animation(arm, cfg):
        dev = float(np.abs(full_coords(bm) - P).max())
        if dev > 1e-4:
            note("the keyed final frame differs from the directly posed mesh by %.2f mm" % (dev * 1000))
        set_sample = lambda t, fr: scene.frame_set(fr)
    else:
        set_sample = lambda t, fr: apply_pose(arm, pose_rotations(arm, cfg, t)[0])

    report = dict(mpfb_version=list(getattr(mpfb, "VERSION", [])), mpfb_module=modname,
                  target_stack=TargetService.calculate_target_stack_from_macro_info_dict(macro_dict(cfg)),
                  natural_body_height_m=round(h_natural, 4), uniform_scale=round(scale / 0.1, 5), pose=info,
                  seconds=time.time() - t0)
    report = bake(bm, arm, cfg, col, set_sample, report)
    f0, f1 = cfg["anim_frames"]
    print("NA2 natural height %.4f m, uniform scale %.4f, done in %.1f s" % (h_natural, scale / 0.1, time.time() - t0))
    print("NA2 in the scene: collection %s with Body (static, exported), NA2_basemesh (hidden; the live MPFB human, use it as "
          "the collision body) and NA2_rig (frames %d..%d bring the arms down)" % (COLLECTION, f0, f1))
    return report


def rebake(cfg=FIG):
    """after changes made by hand to NA2_rig / NA2_basemesh (pose keys, shape keys): write Body, the GLB, figure.npz and
    the report again from what is in the scene. Nothing is created or re-posed; MPFB is not needed for this step."""
    os.makedirs(OUT, exist_ok=True)
    blend = os.path.join(OUT, "figure_mpfb.blend")
    if bpy.data.objects.get("NA2_basemesh") is None and os.path.exists(blend):
        bpy.ops.wm.open_mainfile(filepath=blend)
    bm, arm, col = bpy.data.objects.get("NA2_basemesh"), bpy.data.objects.get("NA2_rig"), bpy.data.collections.get(COLLECTION)
    if bm is None or arm is None or col is None:
        raise RuntimeError("NA2_basemesh / NA2_rig / collection %s not found: run main() first" % COLLECTION)
    scene = bpy.context.scene
    return bake(bm, arm, cfg, col, lambda t, fr: scene.frame_set(fr), dict(rebake=True))


if __name__ == "__main__":
    _args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    if "rebake" in _args:
        rebake()
    else:
        main()
