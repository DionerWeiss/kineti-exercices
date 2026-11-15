"""blender -b <lib exercises.blend> --python export_joints.py -- <out.json> <action> [<action>...]
World positions of the desk-break joints (bone heads and tails) on every frame of each action.
Per frame also `_low` (lowest mesh point of each hand/foot), `_palm` (palm centre as render_mannequin.palm():
hand vertices pushed 45% towards the fingertip) and `_tip` (the fingertip); per action `_ground[action]` is the
height field the move was built on (kineti_builder "ground": raised boxes under hands/feet), when it has one."""
import json
import sys

import bpy

argv = sys.argv[sys.argv.index('--') + 1:]
OUT, ACTS = argv[0], argv[1:]
scene = bpy.context.scene
arm = next(o for o in scene.objects if o.type == 'ARMATURE')
ad = arm.animation_data or arm.animation_data_create()
res = {'bones': [b.name for b in arm.data.bones], 'parents': {b.name: b.parent.name if b.parent else None for b in arm.data.bones}}
import numpy as np
body = next(o for o in scene.objects if o.type == 'MESH' and any(m.type == 'ARMATURE' for m in o.modifiers))
gi = {g.index: g.name for g in body.vertex_groups}
dom = np.array([gi[max(v.groups, key=lambda e: e.weight).group] if len(v.groups) else '' for v in body.data.vertices])
ENDS = {e: np.flatnonzero(dom == e) for e in ('footL', 'footR', 'handL', 'handR')}
HANDV = {s: np.array([v.index for v in body.data.vertices if any(
    g.weight > 0.5 and gi.get(g.group) == 'hand' + s for g in v.groups)], int) for s in 'LR'}


def lowest_points():
    """Per foot/hand: the lowest point of its mesh (world xyz) - the real floor contact (toes on tiptoe)."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = body.evaluated_get(dg)
    me = ev.to_mesh()
    co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get('co', co)
    ev.to_mesh_clear()
    M = np.array(ev.matrix_world)
    W = co.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]
    out = {}
    for e, idx in ENDS.items():
        if len(idx):
            k = idx[W[idx, 2].argmin()]
            out[e] = [round(float(v), 4) for v in W[k]]
    palm, tip = {}, {}
    for s, idx in HANDV.items():
        if len(idx):
            P = W[idx]
            c = P.mean(0)
            t = P[np.linalg.norm(P - c, axis=1).argmax()]
            palm[s] = [round(float(v), 4) for v in c + (t - c) * 0.45]
            tip[s] = [round(float(v), 4) for v in t]
    return out, palm, tip

ad.action = None
for pb in arm.pose.bones:
    pb.rotation_mode = 'QUATERNION'
    pb.rotation_quaternion = (1, 0, 0, 0)
    pb.location = (0, 0, 0)
bpy.context.view_layer.update()
res['rest'] = {b.name: [list(arm.matrix_world @ b.head), list(arm.matrix_world @ b.tail)] for b in arm.pose.bones}
for name in ACTS:
    if name not in bpy.data.actions:
        print('MISSING', name)
        continue
    act = bpy.data.actions[name]
    ad.action = act
    if hasattr(ad, 'action_slot') and getattr(act, 'slots', None):
        ad.action_slot = act.slots[0]
    f0, f1 = (int(round(x)) for x in act.frame_range)
    frames = []
    for f in range(f0, f1 + 1):
        scene.frame_set(f)
        fr = {b.name: [list(arm.matrix_world @ b.head), list(arm.matrix_world @ b.tail)] for b in arm.pose.bones}
        fr['_low'], fr['_palm'], fr['_tip'] = lowest_points()
        frames.append(fr)
    res[name] = frames
    if 'ground' in act:
        res.setdefault('_ground', {})[name] = json.loads(act['ground'])
    print('ACT', name, f0, f1)
json.dump(res, open(OUT, 'w'))
print('DONE', OUT)
