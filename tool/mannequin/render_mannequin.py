"""Kineti mannequin renderer: desk-break rig + actions, repainted, Kineti mark on the chest, exercise props.

    blender -b <lib.blend> --python render_mannequin.py -- <out_dir> <palette> <logo.png> <job> ...
job = id:view[:prop+prop...[:upper|lower[:move]]]   (move: the action to play, default id)   view = side | front | top3q | side3q | front3q | floor | rside3q | back3q
props: chair, support, wall, roll, ball, cuff, dumbbell
env STILL=<fractions, e.g. 0,0.25,0.5> renders only those points of the motion.
"""
import json
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index('--') + 1:]
OUT, PALETTE, LOGO, JOBS = argv[0], argv[1], argv[2], argv[3:]
W, H = 960, 540
STILL = bool(os.environ.get('STILL'))

PALETTES = {  # body, joints
    'azul': ('#2563EB', '#1E40AF'),
    'areia': ('#D8C3A5', '#B89F80'),
    'cinza': ('#C3C8D0', '#9AA3B0'),
    'ardosia': ('#8FA8C8', '#6B86A8'),
    'salvia': ('#A9BBA8', '#869B85'),
}


def lin(h):
    h = h.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c] + [1]


def principled(m):
    m.use_nodes = True
    nt = m.node_tree
    p = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if p is None:
        p = nt.nodes.new('ShaderNodeBsdfPrincipled')
        out = next((n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'), None) or nt.nodes.new('ShaderNodeOutputMaterial')
        nt.links.new(p.outputs[0], out.inputs['Surface'])
    return nt, p


def mat(name, color, rough=0.6):
    m = bpy.data.materials.new(name)
    _, p = principled(m)
    p.inputs['Base Color'].default_value = lin(color)
    p.inputs['Roughness'].default_value = rough
    return m


scene = bpy.context.scene
arm = next(o for o in scene.objects if o.type == 'ARMATURE')
body = next(o for o in scene.objects if o.type == 'MESH' and any(m.type == 'ARMATURE' for m in o.modifiers))
for o in list(scene.objects):
    if o not in (arm, body):
        bpy.data.objects.remove(o)
ad = arm.animation_data or arm.animation_data_create()
ad.action = None
for b in arm.pose.bones:
    b.rotation_mode = 'QUATERNION'
    b.rotation_quaternion = (1, 0, 0, 0)
    b.location = (0, 0, 0)
bpy.context.view_layer.update()

body_c, joint_c = PALETTES[PALETTE]
BODY, JOINT, PROP = mat('body', body_c, 0.65), mat('joint', joint_c, 0.6), mat('prop', '#94A3B8')
for slot in body.material_slots:
    n = (slot.material.name if slot.material else '').lower()
    slot.material = JOINT if 'joint' in n else PROP if ('plastic' in n or 'mouse' in n) else BODY


def parent_to_bone(o, bone):
    mw = o.matrix_world.copy()
    o.parent, o.parent_type, o.parent_bone = arm, 'BONE', bone
    bpy.context.view_layer.update()
    o.matrix_world = mw


# --- Kineti mark on the chest: a subdivided plane shrink-wrapped onto the chest at rest, then baked and
# parented to the spine bone (the chest is rigid with it).
img = bpy.data.images.load(LOGO)
aspect = img.size[0] / img.size[1]
LW = 0.155
bpy.ops.mesh.primitive_grid_add(x_subdivisions=24, y_subdivisions=16, size=1, location=(0, -0.2, 1.325))
logo = bpy.context.object
logo.scale = (LW, LW / aspect, 1)
logo.rotation_euler = (math.radians(90), 0, 0)  # face -Y (the figure's front)
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
sw = logo.modifiers.new('wrap', 'SHRINKWRAP')
sw.target, sw.wrap_method, sw.offset = body, 'PROJECT', 0.0015
sw.use_project_y, sw.use_negative_direction, sw.use_positive_direction = True, True, True
bpy.context.view_layer.objects.active = logo
bpy.ops.object.modifier_apply(modifier='wrap')
lm = bpy.data.materials.new('logo')
nt, p = principled(lm)
tex = nt.nodes.new('ShaderNodeTexImage')
tex.image = img
tex.extension = 'CLIP'
nt.links.new(tex.outputs['Color'], p.inputs['Base Color'])
nt.links.new(tex.outputs['Alpha'], p.inputs['Alpha'])
p.inputs['Roughness'].default_value = 0.6
if hasattr(lm, 'surface_render_method'):
    lm.surface_render_method = 'BLENDED'
logo.data.materials.append(lm)
parent_to_bone(logo, 'spine')


def to_rest():
    ad.action = None
    for b in arm.pose.bones:
        b.rotation_quaternion = (1, 0, 0, 0)
        b.location = (0, 0, 0)
    bpy.context.view_layer.update()


def to_act(act):
    ad.action = act
    if hasattr(ad, 'action_slot') and getattr(act, 'slots', None):
        ad.action_slot = act.slots[0]


def bone_head(name):
    return arm.matrix_world @ arm.pose.bones[name].head


def palm(side):
    """Palm centre from the deformed mesh: hand vertex group centroid pushed towards the fingertip."""
    deps = bpy.context.evaluated_depsgraph_get()
    ev = body.evaluated_get(deps)
    gi = body.vertex_groups['hand' + side].index
    me = ev.to_mesh()
    pts = [ev.matrix_world @ me.vertices[v.index].co for v in body.data.vertices
           if any(g.group == gi and g.weight > 0.5 for g in v.groups)]
    ev.to_mesh_clear()
    c = sum(pts, Vector()) / len(pts)
    tip = max(pts, key=lambda q: (q - c).length)
    return c + (tip - c) * 0.45


# --- set
bpy.ops.mesh.primitive_plane_add(size=400)
FLOOR = bpy.context.object
FLOORM = mat('floor', '#E6EAF0', 0.95)
FLOOR.data.materials.append(FLOORM)
_fnt = FLOORM.node_tree
_chk = _fnt.nodes.new('ShaderNodeTexChecker')
_chk.inputs['Color1'].default_value = lin('#E6EAF0')
_chk.inputs['Color2'].default_value = lin('#DCE2EA')
_chk.inputs['Scale'].default_value = 400 / 0.6  # 60 cm tiles on the 400 m plane
_bsdf = next(n for n in _fnt.nodes if n.type == 'BSDF_PRINCIPLED')


def floor_tiles(on):
    """Tiles show that the body travels while the camera follows it (walking)."""
    for l in list(_bsdf.inputs['Base Color'].links):
        _fnt.links.remove(l)
    if on:
        _fnt.links.new(_chk.outputs['Color'], _bsdf.inputs['Base Color'])

BED_TOP = 0.5  # with a bed, the mattress top is the mannequin's floor and the room floor sits this far below
MATTC = mat('mattress', '#F1F4F8', 0.9)
BANDC = mat('band', '#FF6D00', 0.5)
SWISSC = mat('swiss', '#5B8DEF', 0.35)
MATC = mat('mat', '#B9C6D6', 0.9)
CHAIRC = mat('chair', '#A0AEC0', 0.7)
STEPC = mat('step', '#8E9BAE', 0.6)
STEPTOP = mat('steptop', '#3D4A5C', 0.85)
WALLC = mat('wall', '#E8ECF1', 0.95)
ROLLC = mat('roll', '#7FB7AE', 0.8)
BALLC = mat('ball', '#F2A65A', 0.45)
CUFFC = mat('cuff', '#3D4A5C', 0.7)
DBC = mat('db', '#46505E', 0.4)
temp = []


def box(loc, size, m):
    bpy.ops.mesh.primitive_cube_add(location=loc)
    o = bpy.context.object
    o.scale = [s / 2 for s in size]
    o.data.materials.append(m)
    temp.append(o)
    return o


def motion_bounds(f0, f1, step=3, part='full'):
    """Box around the body over the whole motion, and a sample of its vertices.
    part = upper (waist up) | lower (knees down) | full."""
    lo, hi, pts = Vector((1e9,) * 3), Vector((-1e9,) * 3), []
    deps = bpy.context.evaluated_depsgraph_get()
    for f in range(f0, f1 + 1, step):
        scene.frame_set(f)
        ev = body.evaluated_get(deps)
        cut_up = bone_head('spine').z + 0.05
        cut_lo = max(bone_head('kneeL').z, bone_head('kneeR').z) + 0.12
        for k, v in enumerate(ev.to_mesh().vertices):
            p_ = ev.matrix_world @ v.co
            if part == 'upper' and p_.z < cut_up or part == 'lower' and p_.z > cut_lo:
                continue
            lo = Vector(map(min, lo, p_)); hi = Vector(map(max, hi, p_))
            if k % 4 == 0:
                pts.append(p_)
        ev.to_mesh_clear()
    scene.frame_set(f0)
    return lo, hi, pts


def chair(y_seat, y_back, back_top=1.0):
    """Seat top at 0.45, seat centred on y_seat, backrest plane at y_back."""
    box((0, y_seat, 0.43), (0.46, 0.44, 0.04), CHAIRC)
    hb = back_top - 0.45
    box((0, y_back, 0.45 + hb / 2), (0.46, 0.03, hb), CHAIRC)
    sgn = 1 if y_back > y_seat else -1
    for x in (-0.2, 0.2):
        for y in (y_seat - 0.19 * sgn, y_back):
            box((x, y, 0.205), (0.03, 0.03, 0.41), CHAIRC)


def rod(r, m):
    """Unit-length cylinder along +Z from its origin, to be placed with seg_matrix."""
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=1, vertices=16, location=(0, 0, 0.5))
    o = bpy.context.object
    bpy.ops.object.transform_apply(location=True)
    o.data.materials.append(m)
    bpy.ops.object.shade_smooth()
    o.rotation_mode = 'QUATERNION'
    temp.append(o)
    return o


def seg_matrix(a, b):
    v = b - a
    return Matrix.LocRotScale(a, Vector((0, 0, 1)).rotation_difference(v), Vector((1, 1, max(v.length, 1e-4))))


def animate(objs_fns, f0, f1):
    """Keyframes each object on every frame from a function of the current pose returning its world matrix."""
    for f in range(f0, f1 + 1):
        scene.frame_set(f)
        for o, fn in objs_fns:
            o.matrix_world = fn()
            for path in ('location', 'rotation_quaternion', 'scale'):
                o.keyframe_insert(path, frame=f)
    scene.frame_set(f0)


def foot_tip(s):
    return arm.matrix_world @ arm.pose.bones['foot' + s].tail


def bed(c, lx, ly):
    """Mattress whose top is the mannequin's floor (z = 0), on a frame, the room floor BED_TOP below."""
    box((c.x, c.y, -0.09), (lx, ly, 0.18), MATTC)['noframe'] = True
    box((c.x, c.y, -0.3), (lx + 0.06, ly + 0.06, 0.24), CHAIRC)['noframe'] = True
    for dx in (-1, 1):
        for dy in (-1, 1):
            box((c.x + dx * (lx / 2 - 0.05), c.y + dy * (ly / 2 - 0.05), -0.46), (0.06, 0.06, 0.08), CHAIRC)['noframe'] = True


def chair_side(x_back, y, out, back_top):
    """Chair beside the body: backrest plane at x_back (the hand rests on it), seat further out (out = +1 or -1)."""
    xs = x_back + 0.22 * out
    box((xs, y, 0.43), (0.44, 0.46, 0.04), CHAIRC)
    hb = back_top - 0.45
    box((x_back, y, 0.45 + hb / 2), (0.03, 0.46, hb), CHAIRC)
    for yy in (y - 0.2, y + 0.2):
        for xx in (xs + 0.19 * out, x_back):
            box((xx, yy, 0.205), (0.03, 0.03, 0.41), CHAIRC)


def cyl(loc, r, depth, axis, m, parent=None):
    rot = {'x': (0, math.radians(90), 0), 'y': (math.radians(90), 0, 0), 'z': (0, 0, 0)}[axis]
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth, location=loc, rotation=rot, vertices=32)
    o = bpy.context.object
    o.data.materials.append(m)
    bpy.ops.object.shade_smooth()
    temp.append(o)
    return o


world = scene.world or bpy.data.worlds.new('w')
scene.world = world
world.use_nodes = True
bg = next((n for n in world.node_tree.nodes if n.type == 'BACKGROUND'), None)
if bg is None:
    bg = world.node_tree.nodes.new('ShaderNodeBackground')
    wo = next((n for n in world.node_tree.nodes if n.type == 'OUTPUT_WORLD'), None) or world.node_tree.nodes.new('ShaderNodeOutputWorld')
    world.node_tree.links.new(bg.outputs[0], wo.inputs['Surface'])
bg.inputs['Color'].default_value = lin('#EEF1F5')
bg.inputs['Strength'].default_value = 0.85

bpy.ops.object.light_add(type='SUN')
sun = bpy.context.object
sun.data.energy, sun.data.angle = 1.9, math.radians(25)
sun.rotation_euler = (math.radians(40), math.radians(15), math.radians(-30))
bpy.ops.object.camera_add()
cam = bpy.context.object
scene.camera = cam
cam.data.lens = 50
for engine in ('BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT'):
    try:
        scene.render.engine = engine
        break
    except TypeError:
        pass
scene.render.resolution_x, scene.render.resolution_y = W, H
scene.render.fps = 30
scene.render.image_settings.file_format = 'PNG'
scene.view_settings.view_transform = 'Standard'

DIRS = {'side': (1, 0, 0.18), 'front': (0, -1, 0.2), 'top3q': (0.55, -0.8, 0.9), 'side3q': (0.85, -0.45, 0.3),
        'front3q': (0.5, -0.85, 0.3), 'floor': (1, -0.3, 0.6), 'rside3q': (-0.85, -0.45, 0.3), 'back3q': (0.8, 0.55, 0.35)}

for job in JOBS:
    parts = job.split(':')
    name, view = parts[0], parts[1]
    props = set(parts[2].split('+')) if len(parts) > 2 and parts[2] else set()
    part = parts[3] if len(parts) > 3 and parts[3] else 'full'
    for o in temp:
        bpy.data.objects.remove(o)
    temp.clear()
    act = bpy.data.actions[parts[4] if len(parts) > 4 and parts[4] else name]  # a job may reuse another move
    ad.action = act
    if hasattr(ad, 'action_slot') and getattr(act, 'slots', None):
        ad.action_slot = act.slots[0]
    f0, f1 = (int(round(v)) for v in act.frame_range)
    scene.frame_start, scene.frame_end = f0, f1
    scene.frame_set(f0)

    seated = bool(props & {'chair', 'ball', 'swissseat'})
    if 'swissseat' in props:  # exercise ball as the seat: 55 cm, squashed a little under the pelvis (seat 0.45)
        hp = bone_head('hips')
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.27, segments=48, ring_count=24, location=(hp.x, hp.y + 0.03, 0.235))
        o = bpy.context.object
        o.scale = (1.05, 1.05, 0.87)
        o.data.materials.append(SWISSC)
        bpy.ops.object.shade_smooth()
        temp.append(o)
    elif seated:
        chair(0.12, 0.33, 1.0)
    floor_tiles('walk' in props)
    if 'chairfit' in props:  # a chair under the pelvis of the first pose (sit to stand: not a seated exercise)
        hp = bone_head('hips')
        top = hp.z - 0.075
        y_back = hp.y + 0.2
        bpy.ops.object.select_all(action='DESELECT')
        n0 = len(temp)
        chair(0.0, 0.21, 1.0)
        for o in temp[n0:]:  # chair() draws around y = 0 with the seat at 0.45: move it under the pelvis
            o.location.x += hp.x
            o.location.y += hp.y - 0.04
            o.location.z += top - 0.45 if o.location.z > 0.3 else 0
            if o.location.z < 0.3:  # legs: stretch to the new seat height
                o.scale.z *= top / 0.45
                o.location.z = top / 2 - 0.02
    gr = json.loads(act['ground']) if 'ground' in act else None  # the height field the move was built on
    if gr:  # each raised box drawn as an aerobic step: grey block, dark rubber top
        base = gr.get('base', 0)
        for x0, x1, y0, y1, h in gr['boxes']:
            if h <= base + 0.03:
                continue
            c = ((x0 + x1) / 2, (y0 + y1) / 2)
            box((*c, (base + h - 0.02) / 2), (x1 - x0, y1 - y0, h - 0.02 - base), STEPC)
            box((*c, h - 0.01), (x1 - x0 + 0.006, y1 - y0 + 0.006, 0.02), STEPTOP)
    blo, bhi, bpts = motion_bounds(f0, f1)
    FLOOR.location.z = -BED_TOP if 'bed' in props else gr.get('base', 0) if gr else 0
    if 'bed' in props:
        c, ext = (blo + bhi) / 2, bhi - blo
        long_x = ext.x > ext.y
        lx = max(ext.x + 0.25, 2.0 if long_x else 0.95)
        ly = max(ext.y + 0.25, 0.95 if long_x else 2.0)
        bed(c, lx, ly)
    elif not seated and not props & {'support', 'side', 'wall', 'walk', 'chairfit', 'wallball', 'wallback', 'table'} and bhi.z < 1.4:
        c, ext = (blo + bhi) / 2, bhi - blo
        long_x = ext.x > ext.y
        lx = max(ext.x + 0.3, 1.9 if long_x else 0.66)
        ly = max(ext.y + 0.3, 0.66 if long_x else 1.9)
        box((c.x, c.y, 0.004), (lx, ly, 0.008), MATC)['noframe'] = True
    if 'support' in props:
        pl, pr = palm('L'), palm('R')
        y = (pl.y + pr.y) / 2
        chair(y - 0.22, y, back_top=min(pl.z, pr.z) - 0.04)
    if 'side' in props:  # one hand on the backrest of a chair beside the body
        hx = bone_head('hips').x
        p_ = max((palm('L'), palm('R')), key=lambda v: abs(v.x - hx))
        out = 1 if p_.x > hx else -1
        chair_side(p_.x + 0.02 * out, p_.y, out, p_.z - 0.04)
    if 'wall' in props:
        y = min(palm('L').y, palm('R').y) - 0.03
        box((0, y - 0.05, 1.2), (1.4, 0.1, 2.4), WALLC)['noframe'] = True
    if 'roll' in props:
        k = bone_head('kneeL')
        r = max(0.05, (k.z - 0.05) / 2)
        cyl((k.x, k.y, r), r, 0.42, 'x', ROLLC)
    if 'cuff' in props:
        for s, sx in (('L', 1), ('R', -1)):
            bpy.ops.mesh.primitive_torus_add(major_radius=0.047, minor_radius=0.024, location=(0, 0, 0))
            o = bpy.context.object
            o.data.materials.append(CUFFC)
            bpy.ops.object.shade_smooth()
            o.scale = (1, 1, 1.5)
            to_rest()
            o.matrix_world = Matrix.Translation(arm.matrix_world @ (arm.pose.bones['foot' + s].head + Vector((0, 0, 0.06))))
            parent_to_bone(o, 'knee' + s)
            to_act(act)
            temp.append(o)
    if 'dumbbell' in props:
        for s in ('L', 'R'):
            to_rest()
            c = palm(s) + Vector((0, 0, 0.005))
            parts_ = [cyl(c, 0.014, 0.16, 'x', DBC)]
            for dx in (-0.075, 0.075):
                parts_.append(cyl(c + Vector((dx, 0, 0)), 0.042, 0.04, 'x', DBC))
            for o in parts_:
                parent_to_bone(o, 'hand' + s)
            to_act(act)
    ball = None
    if 'ball' in props:
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.1, segments=48, ring_count=24)
        ball = bpy.context.object
        ball.data.materials.append(BALLC)
        bpy.ops.object.shade_smooth()
        temp.append(ball)
        for f in range(f0, f1 + 1):
            scene.frame_set(f)
            kl, kr = bone_head('kneeL'), bone_head('kneeR')
            gap = (kl - kr).length - 0.094  # knee balls are 0.047 in radius
            ball.location = (kl + kr) / 2 + Vector((0, 0.06, 0))
            ball.scale = (max(0.6, gap / 0.2), 1.08, 1.08)
            ball.keyframe_insert('location', frame=f)
            ball.keyframe_insert('scale', frame=f)

    if 'table' in props:  # a table under the hand(s) that stay put; it extends away from the body
        travel = {}
        for sd in ('L', 'R'):
            ps = []
            for f in range(f0, f1 + 1, 3):
                scene.frame_set(f)
                ps.append(palm(sd))
            travel[sd] = (max((q - ps[0]).length for q in ps), ps[0])
        scene.frame_set(f0)
        still = [sd for sd in travel if travel[sd][0] < 0.05] or [min(travel, key=lambda k_: travel[k_][0])]
        pc = sum((travel[sd][1] for sd in still), Vector()) / len(still)
        hp = bone_head('hips')
        away = pc - hp
        away.z = 0
        away = away.normalized() if away.length > 0.02 else Vector((0, -1, 0))
        top = pc.z - 0.025
        long_ax = Vector((-away.y, away.x, 0))
        if len(still) == 1:  # one hand on it (Codman): a small side table, clear of the other arm
            c, w_, dpt = pc + away * 0.2, 0.5, 0.5
        else:
            c, w_, dpt = pc + away * 0.3, 1.1, 0.7
        lx, ly = abs(long_ax.x) * w_ + abs(away.x) * dpt, abs(long_ax.y) * w_ + abs(away.y) * dpt
        box((c.x, c.y, top - 0.02), (lx, ly, 0.04), CHAIRC)
        for sx in (-1, 1):
            for sy in (-1, 1):
                box((c.x + sx * (lx / 2 - 0.05), c.y + sy * (ly / 2 - 0.05), (top - 0.04) / 2), (0.04, 0.04, top - 0.04), CHAIRC)
    if 'wallback' in props:  # wall touching the back over the whole motion (wall squat)
        box((0, bhi.y + 0.055, 1.2), (1.4, 0.1, 2.4), WALLC)['noframe'] = True
    if 'wallball' in props:  # wall behind the back, exercise ball between the lower back and the wall
        BR = 0.3
        spine0 = bone_head('spine')
        wall_y = spine0.y + 0.12 + 2 * BR
        box((0, wall_y + 0.05, 1.2), (1.4, 0.1, 2.4), WALLC)['noframe'] = True
        bpy.ops.mesh.primitive_uv_sphere_add(radius=BR, segments=48, ring_count=24)
        sb = bpy.context.object
        sb.data.materials.append(BALLC)
        bpy.ops.object.shade_smooth()
        sb.rotation_mode = 'QUATERNION'
        temp.append(sb)
        animate([(sb, lambda: Matrix.Translation(Vector((bone_head('spine').x, wall_y - BR, bone_head('spine').z + 0.08))))],
                f0, f1)

    # Elastic bands, re-placed on every frame.
    if 'bandhands' in props:  # held between the hands
        animate([(rod(0.008, BANDC), lambda: seg_matrix(palm('L'), palm('R')))], f0, f1)
    if props & {'bandanchor', 'bandanchor1'}:  # tied to a door frame: both hands, or only the hand that moves most
        scene.frame_set(f0)
        sides = ['L', 'R']
        if 'bandanchor1' in props:
            travel = {}
            for sd in sides:
                ps = []
                for f in range(f0, f1 + 1, 3):
                    scene.frame_set(f)
                    ps.append(palm(sd))
                travel[sd] = max((a - ps[0]).length for a in ps)
            sides = [max(travel, key=travel.get)]
            scene.frame_set(f0)
        p0 = sum((palm(sd) for sd in sides), Vector()) / len(sides)
        sh = sum((bone_head('arm' + sd) for sd in sides), Vector()) / len(sides)
        d = p0 - sh
        d.z = 0
        anchor = p0 + (d.normalized() if d.length > 0.05 else Vector((0, -1, 0))) * 0.55
        box((anchor.x, anchor.y, 1.0), (0.05, 0.05, 2.0), CHAIRC)['noframe'] = True
        animate([(rod(0.008, BANDC), lambda sd=sd: seg_matrix(palm(sd), anchor)) for sd in sides], f0, f1)
    if 'bandfeet' in props:  # around the feet, both ends in the hands
        mid = lambda: (foot_tip('L') + foot_tip('R')) / 2
        animate([(rod(0.008, BANDC), lambda sd=sd: seg_matrix(palm(sd), mid())) for sd in ('L', 'R')], f0, f1)
    if 'bandknees' in props:  # a loop around both thighs, just above the knees
        RT = 0.072

        def ring_c(sd):
            k, h = bone_head('knee' + sd), bone_head('leg' + sd)
            return k + (h - k).normalized() * 0.09, (k - h).normalized()

        def ring(sd):
            c, dr = ring_c(sd)
            return Matrix.LocRotScale(c, Vector((0, 0, 1)).rotation_difference(dr), Vector((1, 1, 1)))

        def strand(sgn):
            (cl, dl), (cr, dr_) = ring_c('L'), ring_c('R')
            u = (dl + dr_).normalized().cross(cr - cl).normalized() * RT * sgn
            return seg_matrix(cl + u, cr + u)

        tori = []
        for _ in range(2):
            bpy.ops.mesh.primitive_torus_add(major_radius=RT, minor_radius=0.008, major_segments=32, minor_segments=8)
            o = bpy.context.object
            o.data.materials.append(BANDC)
            o.rotation_mode = 'QUATERNION'
            temp.append(o)
            tori.append(o)
        animate([(tori[0], lambda: ring('L')), (tori[1], lambda: ring('R')),
                 (rod(0.008, BANDC), lambda: strand(1)), (rod(0.008, BANDC), lambda: strand(-1))], f0, f1)

    # Frame the whole motion: the body's vertices over every sampled frame, plus the props (not the mat or wall).
    lo, hi, pts = motion_bounds(f0, f1, part=part) if part != 'full' else (blo.copy(), bhi.copy(), list(bpts))
    if 'walk' in props:  # the camera follows: frame the body around the hips, frame by frame
        pts, h0 = [], bone_head('hips')
        deps = bpy.context.evaluated_depsgraph_get()
        for f in range(f0, f1 + 1, 3):
            scene.frame_set(f)
            dv = bone_head('hips') - h0
            dv.z = 0
            ev = body.evaluated_get(deps)
            pts += [ev.matrix_world @ v.co - dv for k_, v in enumerate(ev.to_mesh().vertices) if k_ % 4 == 0]
            ev.to_mesh_clear()
        scene.frame_set(f0)
        lo = Vector(map(min, *pts)) if False else Vector([min(p_[i] for p_ in pts) for i in range(3)])
        hi = Vector([max(p_[i] for p_ in pts) for i in range(3)])
    if part == 'full':
        scene.frame_set(f0)
        deps = bpy.context.evaluated_depsgraph_get()
        for o in temp:
            if o.get('noframe') or o.type != 'MESH':
                continue
            ev = o.evaluated_get(deps)
            pts += [ev.matrix_world @ v.co for v in ev.to_mesh().vertices]
            ev.to_mesh_clear()
    if 'bed' in props and part == 'full':
        pts += [Vector((p_.x, p_.y, -0.3)) for p_ in pts if p_.z < 0.1]  # some of the bed under the body
    if (seated or props & {'support', 'side', 'chairfit', 'table'}) and part != 'upper':
        pts += [Vector((p_.x, p_.y, 0)) for p_ in pts if p_.z < 0.3]  # keep the floor under the feet in view
    centre, size = (lo + hi) / 2, (hi - lo)
    d = Vector(DIRS[view])
    if size.z < 0.75 * max(size.x, size.y) and size.x > size.y:
        # lying along X: "side" should look across the body, so turn the views 90 degrees
        d = Matrix.Rotation(math.radians(-90), 3, 'Z') @ d
    d = d.normalized()
    th = math.tan(cam.data.angle_x / 2)  # sensor fit AUTO, landscape: angle_x is the width
    tv = th * H / W
    fill = 0.84 if part == 'full' else 0.8
    right = d.cross(Vector((0, 0, 1))).normalized()
    up = right.cross(d).normalized()
    for _ in range(4):  # fit width and height separately, then re-centre on the projected extent
        rel = [p_ - centre for p_ in pts]
        dist = max([(0.5 if part == 'full' else 0.32) / tv] +
                   [r.dot(d) + max(abs(r.dot(right)) / (th * fill), abs(r.dot(up)) / (tv * fill)) for r in rel])
        xs = [r.dot(right) / (dist - r.dot(d)) for r in rel]
        ys = [r.dot(up) / (dist - r.dot(d)) for r in rel]
        centre = centre + right * (max(xs) + min(xs)) / 2 * dist + up * (max(ys) + min(ys)) / 2 * dist
    cam.location = centre + d * dist
    cam.rotation_euler = (centre - cam.location).to_track_quat('-Z', 'Y').to_euler()
    if cam.animation_data:
        cam.animation_data_clear()
    if 'walk' in props:
        base = cam.location.copy()
        h0 = bone_head('hips')
        for f in range(f0, f1 + 1):
            scene.frame_set(f)
            dv = bone_head('hips') - h0
            cam.location = base + Vector((dv.x, dv.y, 0))
            cam.keyframe_insert('location', frame=f)
        scene.frame_set(f0)
    print('JOB', name, f0, f1, sorted(props), 'dist', round(dist, 2), 'npts', len(pts), 'lo', tuple(round(v, 2) for v in lo), 'hi', tuple(round(v, 2) for v in hi))
    scene.render.filepath = f'{OUT}/{name}/f_'
    if STILL:
        for q in (float(x) for x in os.environ['STILL'].split(',')):
            f = f0 + round((f1 - f0) * q)
            scene.frame_set(f)
            scene.render.filepath = f'{OUT}/{name}/f_{f:04d}.png'
            bpy.ops.render.render(write_still=True)
    else:
        bpy.ops.render.render(animation=True)
print('DONE')
