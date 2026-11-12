"""Side-view figure matched to the Dinh split-jump drawing, on the mannequin rig.

Each body part is one clean mesh with one flat colour, parented to its joint. Pieces overlap at the
knee, elbow, hip and shoulder so a bend does not open a hole. No voxel remesh: that painted the
clothes in stripes.

    blender -b <kineti exercises.blend> --python humanoid_jump.py -- <out dir> [--full]
"""
import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:]
OUT = argv[0]
FULL = '--full' in argv
ACTION = 'kineti-jumping-lunge'

# The drawing: peach skin, orange tank, black shorts, brown hair, black trainer, orange sole.
SKIN = ('#F6C3AE', '#E39A86')
SHIRT = ('#F07A2A', '#D4621C')
SHORTS = ('#2C2C2C', '#1A1A1A')
HAIR = ('#5C4034', '#3D291F')
SHOE = ('#2A2A2A', '#141414')
SOLE = ('#E36A28', '#C45418')
LIGHT = Vector((0.15, -0.35, 0.85)).normalized()


def lin(h):
    c = [int(h.lstrip('#')[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92 for v in c] + [1]


def toon(name, pair):
    m = bpy.data.materials.new('hum_' + name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    em = nt.nodes.new('ShaderNodeEmission')
    geo = nt.nodes.new('ShaderNodeNewGeometry')
    dot = nt.nodes.new('ShaderNodeVectorMath')
    dot.operation = 'DOT_PRODUCT'
    dot.inputs[1].default_value = (LIGHT.x, LIGHT.y, LIGHT.z)
    nt.links.new(geo.outputs['Normal'], dot.inputs[0])
    gt = nt.nodes.new('ShaderNodeMath')
    gt.operation = 'GREATER_THAN'
    gt.inputs[1].default_value = 0.12
    nt.links.new(dot.outputs['Value'], gt.inputs[0])
    mix = nt.nodes.new('ShaderNodeMix')
    mix.data_type = 'RGBA'
    mix.inputs['A'].default_value = lin(pair[1])
    mix.inputs['B'].default_value = lin(pair[0])
    nt.links.new(gt.outputs['Value'], mix.inputs['Factor'])
    nt.links.new(mix.outputs['Result'], em.inputs['Color'])
    nt.links.new(em.outputs['Emission'], out.inputs['Surface'])
    return m


scene = bpy.context.scene
arm = next(o for o in scene.objects if o.type == 'ARMATURE')
ad = arm.animation_data or arm.animation_data_create()
ad.action = None
for pb in arm.pose.bones:
    pb.rotation_mode = 'QUATERNION'
    pb.rotation_quaternion = (1, 0, 0, 0)
    pb.location = (0, 0, 0)
bpy.context.view_layer.update()

# The wooden doll stays in the file (hidden) so the library actions are untouched.
wood = bpy.data.objects.get('mannequin')
if wood is not None:
    wood.hide_render = True
    wood.hide_viewport = True

MATS = {k: toon(k, v) for k, v in {
    'skin': SKIN, 'shirt': SHIRT, 'shorts': SHORTS, 'hair': HAIR, 'shoe': SHOE, 'sole': SOLE,
}.items()}


def lathe(profile, n, axis):
    bm = bmesh.new()
    rings = []
    for along, ra, rb in profile:
        if axis == 'Y':
            point = lambda a, b, along=along: (a, along, b)
        else:
            point = lambda a, b, along=along: (a, b, along)
        if ra <= 1e-6 and rb <= 1e-6:
            rings.append([bm.verts.new(point(0.0, 0.0))])
            continue
        ring = []
        for i in range(n):
            t = 2 * math.pi * i / n
            ring.append(bm.verts.new(point(ra * math.cos(t), rb * math.sin(t))))
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        if len(a) == 1:
            for i in range(len(b)):
                bm.faces.new((a[0], b[(i + 1) % len(b)], b[i]))
        elif len(b) == 1:
            for i in range(len(a)):
                bm.faces.new((a[i], a[(i + 1) % len(a)], b[0]))
        else:
            m = len(a)
            for i in range(m):
                j = (i + 1) % m
                bm.faces.new((a[i], b[i], b[j], a[j]))
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    return bm


def capsule(y0, y1, r0, r1, sx=1.0, sz=1.0):
    sign0 = 1 if y0 >= y1 else -1
    pts = []
    for k in range(5, 0, -1):
        ang = math.pi / 2 * k / 5
        rad = math.cos(ang)
        pts.append((y0 + math.sin(ang) * r0 * sign0, rad * r0 * sx, rad * r0 * sz))
    for i in range(6):
        t = i / 5
        r = r0 + (r1 - r0) * t
        pts.append((y0 + (y1 - y0) * t, r * sx, r * sz))
    sign1 = -sign0
    for k in range(1, 6):
        ang = math.pi / 2 * k / 5
        rad = math.cos(ang)
        pts.append((y1 + math.sin(ang) * r1 * sign1, rad * r1 * sx, rad * r1 * sz))
    return lathe(pts, 28, 'Y')


def sphere(center, radius, scale):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=28, v_segments=16, radius=1.0)
    for v in bm.verts:
        v.co.x = v.co.x * scale[0] * radius + center[0]
        v.co.y = v.co.y * scale[1] * radius + center[1]
        v.co.z = v.co.z * scale[2] * radius + center[2]
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    return bm


def add(name, bm, bone, material):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(MATS[material])
    obj = bpy.data.objects.new(name, me)
    scene.collection.objects.link(obj)
    obj.parent = arm
    obj.parent_type = 'BONE'
    obj.parent_bone = bone
    obj.matrix_world = arm.matrix_world @ arm.data.bones[bone].matrix_local
    # palm() in the library renderer reads these groups. One group per part is enough for the hand.
    if bone.startswith('hand'):
        vg = obj.vertex_groups.new(name=bone)
        vg.add(list(range(len(me.vertices))), 1.0, 'REPLACE')
    return obj


# Tank: one solid volume on the spine. Bone +Z is the direction he faces.
tank = [
    (-0.08, 0, 0), (-0.04, 0.130, 0.110), (0.08, 0.148, 0.125),
    (0.20, 0.158, 0.132), (0.32, 0.142, 0.118), (0.365, 0.092, 0.072), (0.390, 0, 0),
]
add('hum_tank', lathe(tank, 32, 'Y'), 'spine', 'shirt')

# Shorts pelvis, plus a cuff on each thigh that swings with the leg and hides the skin under it.
pelvis = [
    (0.12, 0, 0), (0.06, 0.150, 0.115), (-0.02, 0.160, 0.125),
    (-0.08, 0.135, 0.105), (-0.11, 0, 0),
]
add('hum_pelvis', lathe(pelvis, 32, 'Y'), 'hips', 'shorts')

add('hum_neck', capsule(0.105, -0.04, 0.052, 0.058), 'neck', 'skin')
add('hum_head', sphere((0, 0.155, 0.012), 0.105, (0.96, 1.05, 1.0)), 'neck', 'skin')
# Hair sits on the crown and the back. The face (bone +Z) stays bare.
add('hum_hair', sphere((0, 0.21, -0.055), 0.125, (1.05, 0.82, 1.2)), 'neck', 'hair')

for side, sign in (('L', 1), ('R', -1)):
    add(f'hum_shoulder{side}', sphere((-0.02 * sign, 0.01, 0.01), 0.062, (1, 1, 1)), 'arm' + side, 'skin')
    # upper arm reaches past the elbow; forearm starts above it. The two skins overlap.
    add(f'hum_arm{side}', capsule(0.03, -0.34, 0.050, 0.042), 'arm' + side, 'skin')
    add(f'hum_elbow{side}', sphere((0, 0, 0), 0.048, (1, 1, 1)), 'elbow' + side, 'skin')
    add(f'hum_fore{side}', capsule(0.04, -0.24, 0.042, 0.034, 1.0, 0.92), 'elbow' + side, 'skin')
    # flat mitt, wider than the wrist
    add(f'hum_hand{side}', capsule(0.02, -0.13, 0.030, 0.042, 1.45, 0.62), 'hand' + side, 'skin')

for side in ('L', 'R'):
    # shorts cuff is fatter than the skin, so the thigh never shows through the hem
    add(f'hum_short{side}', capsule(0.05, -0.20, 0.088, 0.078, 1.02, 1.0), 'leg' + side, 'shorts')
    # Both limbs end in a cap centred on the joint, so the bend is a ball instead of a peg with a hole.
    add(f'hum_thigh{side}', capsule(-0.16, -0.42, 0.066, 0.060), 'leg' + side, 'skin')
    add(f'hum_knee{side}', sphere((0, 0, -0.01), 0.078, (1.05, 1, 1.05)), 'knee' + side, 'skin')
    add(f'hum_shin{side}', capsule(0.0, -0.40, 0.058, 0.050, 1.0, 0.96), 'knee' + side, 'skin')
    # fat ankle on the shin itself, so it stays inside the shoe when the foot turns
    add(f'hum_ankle{side}', sphere((0, -0.36, 0), 0.070, (1.05, 1.05, 1.05)), 'knee' + side, 'skin')
    shoe = [
        (-0.05, 0, 0), (-0.015, 0.062, 0.090), (0.04, 0.056, 0.055),
        (0.12, 0.044, 0.034), (0.17, 0, 0),
    ]
    add(f'hum_shoe{side}', lathe([(z, rx, ry) for z, rx, ry in shoe], 28, 'Z'), 'foot' + side, 'shoe')
    # orange stripe embedded in the sole, narrower than the shoe so it cannot float past the toe
    sole = [(0.01, 0, 0), (0.05, 0.040, 0.010), (0.11, 0.036, 0.009), (0.145, 0, 0)]
    add(f'hum_sole{side}', lathe(sole, 24, 'Z'), 'foot' + side, 'sole')
    sole_obj = bpy.data.objects[f'hum_sole{side}']
    for v in sole_obj.data.vertices:
        v.co.y -= 0.030
        v.co.z += 0.015

# Soft floor oval, behind the body so it cannot cover a shoe. The library renderer deletes it.
sh_bm = bmesh.new()
sh_bm.faces.new([sh_bm.verts.new((0, math.cos(a), math.sin(a))) for a in (2 * math.pi * i / 40 for i in range(40))])
sh_me = bpy.data.meshes.new('shadow')
sh_bm.to_mesh(sh_me)
sh_bm.free()
sh = bpy.data.objects.new('hum_shadow', sh_me)
scene.collection.objects.link(sh)
sh.data.materials.append(toon('shadow', ('#E4EAF0', '#E4EAF0')))


def place_shadow(scene):
    fl = arm.matrix_world @ arm.pose.bones['footL'].head
    fr = arm.matrix_world @ arm.pose.bones['footR'].head
    h = arm.matrix_world @ arm.pose.bones['hips'].head
    span = abs(fl.y - fr.y)
    k = max(0.5, 1.0 - max(0.0, h.z - 0.95) * 1.2)
    sh.location = (-0.6, (fl.y + fr.y) * 0.5, 0.04)
    sh.scale = (1, max(0.5, span * 0.45 + 0.28) * k, 0.06 * k)


world = scene.world or bpy.data.worlds.new('World')
scene.world = world
world.use_nodes = True
nt = world.node_tree
nt.nodes.clear()
bg = nt.nodes.new('ShaderNodeBackground')
bg.inputs['Color'].default_value = (1, 1, 1, 1)
bg.inputs['Strength'].default_value = 1
nt.links.new(bg.outputs['Background'], nt.nodes.new('ShaderNodeOutputWorld').inputs['Surface'])

engines = {e.identifier for e in scene.render.bl_rna.properties['engine'].enum_items}
scene.render.engine = 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in engines else 'BLENDER_EEVEE'
scene.view_settings.view_transform = 'Standard'
scene.render.resolution_x = scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGB'
ee = getattr(scene, 'eevee', None)
if ee and hasattr(ee, 'taa_render_samples'):
    ee.taa_render_samples = 8

cam_data = bpy.data.cameras.new('cam')
cam_data.type = 'ORTHO'
cam_data.ortho_scale = 2.2
cam = bpy.data.objects.new('cam', cam_data)
scene.collection.objects.link(cam)
scene.camera = cam


def shot(name, frame):
    scene.frame_set(frame)
    place_shadow(scene)
    target = Vector((0, -0.05, 0.9))
    cam.location = (4.5, -0.05, 0.9)
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = os.path.join(folder, name + '.png')
    bpy.ops.render.render(write_still=True)
    print('FRAME', name)


os.makedirs(OUT, exist_ok=True)
folder = os.path.join(OUT, 'frames' if FULL else 'stills')
os.makedirs(folder, exist_ok=True)

act = bpy.data.actions[ACTION]
ad.action = act
if hasattr(ad, 'action_slot') and len(act.slots):
    ad.action_slot = act.slots[0]
scene.frame_start, scene.frame_end = 1, int(act.frame_range[1])
scene.render.fps = 30

if FULL:
    for f in range(scene.frame_start, scene.frame_end + 1):
        shot(f'f_{f:04d}', f)
else:
    shot('pose_lunge', 1)
    shot('pose_air', 28)

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'humanoid.blend'))
print('DONE')
