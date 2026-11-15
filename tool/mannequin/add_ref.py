"""blender -b <avatar lib .blend> --python add_ref.py -- <desk-break mannequin.blend>
Adds desk-break's own mannequin mesh to the avatar lib as `mannequin_ref` (hidden from renders, deformed by the same
rig): plant_hands.reground() rests the avatar where the builder rested this mesh, frame by frame. Saves the lib."""
import sys

import bpy

SRC = sys.argv[sys.argv.index('--') + 1]
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
old = bpy.data.objects.get('mannequin_ref')
if old:
    bpy.data.objects.remove(old)
with bpy.data.libraries.load(SRC, link=False) as (src, dst):
    dst.objects = ['mannequin']
ref = dst.objects[0]
ref.name = 'mannequin_ref'
for m in ref.modifiers:
    if m.type == 'ARMATURE':
        extra = m.object
        m.object = rig
if ref.parent is not None and ref.parent is not rig:
    mw = ref.matrix_world.copy()
    ref.parent = rig
    ref.matrix_world = mw
for o in list(bpy.data.objects):
    if o.type == 'ARMATURE' and o is not rig and o.users <= 1:
        bpy.data.objects.remove(o)
bpy.context.scene.collection.objects.link(ref)
ref.hide_render = True
for s in ref.material_slots:
    s.material = None
bpy.ops.wm.save_mainfile()
print('OK mannequin_ref', len(ref.data.vertices), 'verts; groups', len(ref.vertex_groups))
