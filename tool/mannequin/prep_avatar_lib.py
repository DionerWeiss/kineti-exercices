"""blender -b <copy of an avatar .blend> --python prep_avatar_lib.py
Leaves one scene: the one with the rig and the avatar body, with every render-visible skinned mesh (the body, the
hair) linked into it; other scenes (previews, inspection cameras) are removed. Saves the file. Run it on a copy;
then sync_actions.py (desk-break and the rebuilt kineti moves) and add_ref.py."""
import bpy

body = bpy.data.objects['mannequin']
keep = next(s for s in bpy.data.scenes if body.name in s.objects and any(o.type == 'ARMATURE' for o in s.objects)
            and s.name == 'Scene') if 'Scene' in bpy.data.scenes else next(s for s in bpy.data.scenes if body.name in s.objects)
for o in bpy.data.objects:
    if o.type == 'MESH' and not o.hide_render and any(m.type == 'ARMATURE' for m in o.modifiers) and o.name not in keep.objects:
        keep.collection.objects.link(o)
for w in bpy.context.window_manager.windows:
    w.scene = keep
for s in list(bpy.data.scenes):
    if s is not keep:
        bpy.data.scenes.remove(s)
bpy.ops.wm.save_mainfile()
print('OK scene', keep.name, 'render meshes', [o.name for o in keep.objects if o.type == 'MESH' and not o.hide_render])
