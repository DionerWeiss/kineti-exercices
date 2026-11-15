"""blender -b <target lib .blend> --python sync_actions.py -- <source .blend> [<action> ...]
Copies actions from another lib on the same desk-break rig into the target and saves it: the named ones replace
the target's (a fixed move rebuilt from kineti_moves.json); without names, every action the target lacks is added
(desk-break's own moves into the avatar lib)."""
import sys

import bpy

argv = sys.argv[sys.argv.index('--') + 1:]
SRC, NAMES = argv[0], set(argv[1:])
tgt_rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
with bpy.data.libraries.load(SRC, link=False) as (src, dst):
    dst.actions = [n for n in src.actions if (n in NAMES if NAMES else n not in bpy.data.actions)]
    dst.objects = [n for n in src.objects if n == 'rig']
src_rig = next((o for o in dst.objects if o and o.type == 'ARMATURE'), None)
if src_rig is not None:
    a, b = {x.name for x in src_rig.data.bones}, {x.name for x in tgt_rig.data.bones}
    assert a == b, f'different rigs: {sorted(a ^ b)}'
    for x in src_rig.data.bones:
        d = (x.head_local - tgt_rig.data.bones[x.name].head_local).length
        assert d < 1e-4, f'bone {x.name} differs by {d:.4f} m'
n = 0
for new in dst.actions:
    base = new.name.rsplit('.', 1)[0] if new.name[-4:-3] == '.' and new.name[-3:].isdigit() else new.name
    old = bpy.data.actions.get(base)
    if old is not None and old is not new:
        old.user_remap(new)
        bpy.data.actions.remove(old)
    new.name = base
    new.use_fake_user = True
    n += 1
for o in dst.objects:
    if o:
        bpy.data.objects.remove(o)
bpy.ops.wm.save_mainfile()
print('OK synced', n, 'actions; total', len(bpy.data.actions), 'in', bpy.data.filepath)
