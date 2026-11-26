import bpy, sys, numpy as np
B = sys.argv[1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.obj_import(filepath=B + '/collide.obj', forward_axis='NEGATIVE_Z', up_axis='Y')
for o in bpy.data.objects:
    me = o.data; co = np.array([o.matrix_world @ v.co for v in me.vertices])
    print('OBJ', o.name, len(me.vertices), len(me.polygons), 'bbox(blender Z-up)', co.min(0).round(3), co.max(0).round(3))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=B + '/body.glb')
for o in bpy.data.objects:
    if o.type != 'MESH': continue
    me = o.data; co = np.array([o.matrix_world @ v.co for v in me.vertices])
    print('GLB', o.name, [m.name for m in me.materials], len(me.vertices), len(me.polygons), co.min(0).round(3), co.max(0).round(3))
d = np.load(B + '/collide_anim.npz')
print({k: d[k].shape for k in d.files}, 't', d['t'])
print('apose bbox', d['body_frames'][0].min(0).round(3), d['body_frames'][0].max(0).round(3), 'final bbox', d['body_frames'][-1].min(0).round(3), d['body_frames'][-1].max(0).round(3))
