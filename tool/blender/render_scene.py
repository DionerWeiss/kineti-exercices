"""Blender side of the 3D renderer: builds the set from the exported props,
poses the Kineti character from the exported motion and renders a PNG
sequence (the video is encoded outside Blender).

    blender -b kineti_character_illustrated.blend --python render_scene.py -- \
        scene.json out_prefix [width] [still|anim] [arm_factor]

Rig coordinates (metres, Y up, near side +Z) map to Blender by
M: (x, y, z) -> (x, -z, y). The character stands facing -Y with its left
side towards +X, so the rig's near side is the character's right (*_r).

Posing: body orientation from the rig's pelvis and thorax frames; spine
follows the rig's spine line; clavicles follow the rig's shoulder joints
(shrug, retraction); arms and legs are two-bone IK on the character's own
lengths, aimed at the rig's hands and ankles with the rig's elbows and knees
as poles, so contacts (feet on the floor, hands on a support) hold even
where the character's proportions differ from the rig's.
"""

import json
import math
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector

argv = sys.argv[sys.argv.index('--') + 1:]
data = json.load(open(argv[0]))
OUT = argv[1]
WIDTH = int(argv[2]) if len(argv) > 2 else 960
MODE = argv[3] if len(argv) > 3 else 'anim'
ARM = float(argv[4]) if len(argv) > 4 else 0.88  # upper arm and forearm length factor (hand unchanged)
ARM = data.get('arm', ARM)  # captured motion brings its own, matched to the performer


def M(p):
    return Vector((p[0], -p[2], p[1]))


scene = bpy.context.scene
rig = bpy.data.objects['Kineti_Rig']
if rig.animation_data:
    rig.animation_data.action = None

# ------------------------------------------------------------------ set
for o in bpy.data.objects:
    if o.users_collection and o.users_collection[0].name == 'Set' and o.name != 'Floor':
        o.hide_render = True
MAT = {
    'wood': bpy.data.objects['BedBase'].active_material,
    'soft': bpy.data.objects['Mattress'].active_material,
    'pillow': bpy.data.objects['Pillow'].active_material,
    'wall': (bpy.data.objects['Wall'].active_material if 'Wall' in bpy.data.objects else None)
            or bpy.data.objects['Mattress'].active_material,
}


def material_for(name, role=''):
    n = name.lower()
    if any(k in n for k in ('pillow', 'cushion', 'towel', 'roll')):
        return MAT['pillow']
    if any(k in n for k in ('mattress', 'mat', 'sheet')) and 'chair' not in n:
        return MAT['soft']
    if any(k in n for k in ('wall', 'door', 'post', 'frame')):
        return MAT['wall']
    return MAT['wood']


def finish(o, mat, bevel=0.006):
    o.data.materials.append(mat)
    if bevel:
        md = o.modifiers.new('bevel', 'BEVEL')
        md.width, md.segments = bevel, 2
    for p in o.data.polygons:
        p.use_smooth = False
    return o


def cube(name, lo, hi, mat, bevel=0.006):
    """Axis-aligned box between two Blender-space corners."""
    lo, hi = Vector([min(a, b) for a, b in zip(lo, hi)]), Vector([max(a, b) for a, b in zip(lo, hi)])
    mesh = bpy.data.meshes.new(name)
    v = [(x, y, z) for x in (lo.x, hi.x) for y in (lo.y, hi.y) for z in (lo.z, hi.z)]
    f = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    mesh.from_pydata(v, [], f)
    o = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(o)
    return finish(o, mat, bevel)


SURFACES = []  # (x0, x1, z0, z1, top) in rig coordinates: where a hand can rest flat


def rig_box(name, lo, hi, mat=None, bevel=0.006):
    if 'wall' not in name and 'leg' not in name:
        SURFACES.append((min(lo[0], hi[0]), max(lo[0], hi[0]), min(lo[2], hi[2]), max(lo[2], hi[2]), max(lo[1], hi[1])))
    return cube(name, M(lo), M(hi), mat or material_for(name), bevel)


def bar(name, a, b, width, mat):
    a, b = M(a), M(b)
    d = b - a
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=width / 2, depth=d.length, location=(a + b) / 2)
    o = bpy.context.active_object
    o.name = name
    o.rotation_mode = 'QUATERNION'
    o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d.normalized())
    o.data.materials.append(mat)
    return o


def panel(name, pts, mat, thick=0.02):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([M(q) for q in pts], [], [list(range(len(pts)))])
    o = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(o)
    md = o.modifiers.new('solid', 'SOLIDIFY')
    md.thickness, md.offset = thick, 0.0
    return finish(o, mat, 0.0)


def chair3d(x, facing=1, z=0.0, backrest=True):
    """The library chair (figure3d.chair), facing +X (or -X with facing=-1)."""
    w, leg = 0.21, 0.015
    fx = lambda a: x + facing * a
    for i, (ax, az) in enumerate([(-0.22, -w), (0.2, -w), (-0.22, w), (0.2, w)]):
        rig_box(f'chair leg {i}', (fx(ax) - leg, 0.0, z + az - leg), (fx(ax) + leg, 0.44, z + az + leg), MAT['wood'])
    rig_box('chair seat', (fx(-0.25), 0.44, z - w - 0.01), (fx(0.23), 0.47, z + w + 0.01), MAT['wood'])
    if backrest:
        for i, az in enumerate((-w, w)):
            rig_box(f'chair post {i}', (fx(-0.29), 0.46, z + az - leg), (fx(-0.25), 1.0, z + az + leg), MAT['wood'])
        rig_box('chair back', (fx(-0.29), 0.7, z - w), (fx(-0.26), 1.0, z + w), MAT['wood'])


def tinted(base, lit, shadow, name):
    """Copy of a set material (the illustration's two-tone group) with new lit and shadow colours."""
    m = base.copy()
    m.name = name
    for node in m.node_tree.nodes:
        if node.type == 'GROUP':
            node.inputs['Lit'].default_value = (*lit, 1.0)
            node.inputs['Shadow'].default_value = (*shadow, 1.0)
    return m


def sphere(name, centre, radius, mat):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=radius, location=M(centre))
    o = bpy.context.active_object
    o.name = name
    o.data.materials.append(mat)
    for poly in o.data.polygons:
        poly.use_smooth = True
    return o


def build_set(props):
    profile = [p for p in props if p['type'] in ('line2d', 'poly2d')]
    chairs = {}
    for p in profile:  # group the profile chair's lines: the seat gives x, the backrest the facing
        if p['name'].startswith('chair'):
            chairs.setdefault('c', {})[p['name']] = p['points']
    if 'c' in chairs and 'chair seat' in chairs['c']:
        (sx0, _), (sx1, _) = chairs['c']['chair seat']
        cx = (sx0 + sx1) / 2 + 0.01
        back = chairs['c'].get('chair back')
        facing = 1 if not back or back[0][0] < cx else -1
        chair3d(cx - facing * 0.0, facing)
    for p in props:
        n, t = p['name'], p['type']
        if t == 'box':
            rig_box(n, p['min'], p['max'])
        elif t == 'bar':
            for i, (a, b) in enumerate(zip(p['points'], p['points'][1:])):
                bar(f'{n} {i}', a, b, p['width'], material_for(n))
        elif t == 'panel':
            panel(n, p['points'], material_for(n))
        elif t == 'sphere':
            sphere(n, p['center'], p['radius'], tinted(MAT['soft'], (0.36, 0.72, 0.98), (0.16, 0.45, 0.82), 'Ball'))
            x, y, z = p['center']
            SURFACES.append((x - 0.1, x + 0.1, z - 0.1, z + 0.1, y + p['radius']))
        elif t in ('line2d', 'poly2d'):
            if n.startswith(('chair', 'floor', 'armrest')):
                continue
            xs, ys = [q[0] for q in p['points']], [q[1] for q in p['points']]
            if 'wall' in n:
                if t == 'poly2d':
                    rig_box(n, (min(xs), 0.0, -1.6), (min(xs) + 0.12, max(ys), 1.6), MAT['wall'])
                continue
            pad = p.get('width', 0.0) / 2
            if t == 'poly2d':
                rig_box(n, (min(xs), min(ys), -0.32), (max(xs), max(ys), 0.32))
            elif 'step' not in n:  # step outlines are covered by the step block
                rig_box(n, (min(xs) - pad, min(ys) - pad, -0.25), (max(xs) + pad, max(ys) + pad, 0.25))


build_set(data['props'])

# elastic bands: a bevelled curve whose points follow the exported polyline
band_mat = tinted(MAT['soft'], (1.0, 0.43, 0.0), (0.82, 0.27, 0.0), 'Band')  # Kineti tertiary, lit and shaded
for name, frames in data['bands'].items():
    n = len(frames[0][1])
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions, cu.bevel_depth, cu.bevel_resolution = '3D', 0.013, 3
    sp = cu.splines.new('POLY')
    sp.points.add(n - 1)
    ob = bpy.data.objects.new(name, cu)
    scene.collection.objects.link(ob)
    ob.data.materials.append(band_mat)
    for fr, pts in frames:
        for i, q in enumerate(pts):
            v = M(q)
            sp.points[i].co = (v.x, v.y, v.z, 1.0)
            sp.points[i].keyframe_insert('co', frame=fr + 1)


def place_along(obj, a, b):
    """Point a Z-up primitive from rig point a to rig point b. Returns both in Blender space."""
    a, b = M(a), M(b)
    d = b - a
    obj.rotation_mode = 'QUATERNION'
    obj.location = (a + b) / 2
    direction = d.normalized() if d.length > 1e-6 else Vector((0.0, 0.0, 1.0))
    obj.rotation_quaternion = Vector((0.0, 0.0, 1.0)).rotation_difference(direction)
    return a, b, d


def key_pose(obj, frame):
    obj.keyframe_insert('location', frame=frame)
    obj.keyframe_insert('rotation_quaternion', frame=frame)
    obj.keyframe_insert('scale', frame=frame)


def build_gadgets(items):
    """Ball, dumbbells and the ankle weight: animated from the exported joints."""
    for i, spec in enumerate(items):
        kind = spec['type']
        if kind == 'ball':
            mat = studio_material(f'Ball {i}', spec['color'], 0.4)
            bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=0.5)
            o = bpy.context.active_object
            o.name = spec['name']
            o.data.materials.append(mat)
            for poly in o.data.polygons:
                poly.use_smooth = True
            for k in spec['keys']:
                depth, height, width = k['scale']  # rig diameters: X, Y, Z
                o.location = M(k['center'])
                o.scale = (depth, width, height)  # radius 0.5, so the scale is the diameter
                o.keyframe_insert('location', frame=k['fr'] + 1)
                o.keyframe_insert('scale', frame=k['fr'] + 1)
        elif kind == 'dumbbell':
            mat = studio_material(spec['name'], (0.16, 0.17, 0.19), 0.32, 0.8)
            bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.016, depth=1.0)
            bar_ob = bpy.context.active_object
            bar_ob.name = spec['name']
            bar_ob.rotation_mode = 'QUATERNION'
            bar_ob.data.materials.append(mat)
            plates = []
            for n in range(2):
                bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.046, depth=0.03)
                plate = bpy.context.active_object
                plate.name = f'{spec["name"]} plate {n}'
                plate.rotation_mode = 'QUATERNION'
                plate.data.materials.append(mat)
                plates.append(plate)
            for k in spec['keys']:
                a, b, d = place_along(bar_ob, k['a'], k['b'])
                bar_ob.scale = (1.0, 1.0, max(d.length, 1e-3))
                key_pose(bar_ob, k['fr'] + 1)
                for plate, end in zip(plates, (a, b)):
                    plate.location = end
                    plate.rotation_quaternion = bar_ob.rotation_quaternion
                    key_pose(plate, k['fr'] + 1)
        elif kind == 'cuff':
            mat = studio_material('Ankle weight', (0.12, 0.12, 0.13), 0.55)
            bpy.ops.mesh.primitive_torus_add(major_segments=40, minor_segments=12, major_radius=0.08, minor_radius=0.02)
            o = bpy.context.active_object
            o.name = spec['name']
            o.data.materials.append(mat)
            for poly in o.data.polygons:
                poly.use_smooth = True
            for k in spec['keys']:
                place_along(o, k['a'], k['b'])
                key_pose(o, k['fr'] + 1)


# The working segment, in the app's tertiary orange. Vertex weight in the
# exported bones drives a mix on top of the existing colour, so the shirt
# print and the form stay visible.
ACCENT = (1.0, 0.427, 0.0, 1.0)  # #FF6D00
_accent_hooked = set()


def tint_material(mat):
    if mat is None or mat.name in _accent_hooked or not mat.node_tree:
        return
    nt = mat.node_tree
    bsdf = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bsdf is None or 'Base Color' not in bsdf.inputs:
        return
    _accent_hooked.add(mat.name)
    mix = nt.nodes.new('ShaderNodeMix')
    mix.name = 'AccentMix'
    mix.data_type = 'RGBA'
    mix.location = (bsdf.location.x - 280, bsdf.location.y)
    factor = next(s for s in mix.inputs if s.name == 'Factor' and s.type == 'VALUE')
    color_a = next(s for s in mix.inputs if s.name == 'A' and s.type == 'RGBA')
    color_b = next(s for s in mix.inputs if s.name == 'B' and s.type == 'RGBA')
    result = next(s for s in mix.outputs if s.name == 'Result' and s.type == 'RGBA')
    attr = nt.nodes.new('ShaderNodeAttribute')
    attr.attribute_name = 'Accent'
    attr.attribute_type = 'GEOMETRY'
    attr.location = (mix.location.x - 420, mix.location.y - 80)
    sep = nt.nodes.new('ShaderNodeSeparateColor')
    sep.location = (mix.location.x - 220, mix.location.y - 120)
    strength = nt.nodes.new('ShaderNodeMath')
    strength.operation = 'MULTIPLY'
    strength.inputs[1].default_value = 0.72
    strength.location = (mix.location.x - 40, mix.location.y - 140)
    base = bsdf.inputs['Base Color']
    if base.is_linked:
        nt.links.new(base.links[0].from_socket, color_a)
    else:
        color_a.default_value = tuple(base.default_value)
    color_b.default_value = ACCENT
    nt.links.new(attr.outputs['Color'], sep.inputs['Color'])
    nt.links.new(sep.outputs['Red'], strength.inputs[0])
    nt.links.new(strength.outputs['Value'], factor)
    nt.links.new(result, base)


def paint_accent(bone_names):
    wanted = set(bone_names)
    if not wanted:
        print('ACCENT none')
        return
    painted = 0
    for obj in bpy.data.objects:
        if obj.type != 'MESH' or not obj.vertex_groups:
            continue
        groups = {g.index: g.name for g in obj.vertex_groups if g.name in wanted}
        if not groups:
            continue
        mesh = obj.data
        attr = mesh.color_attributes.get('Accent')
        if attr is not None and (attr.domain != 'POINT' or attr.data_type != 'FLOAT_COLOR'):
            mesh.color_attributes.remove(attr)
            attr = None
        if attr is None:
            attr = mesh.color_attributes.new('Accent', 'FLOAT_COLOR', 'POINT')
        for v in mesh.vertices:
            w = 0.0
            for g in v.groups:
                if g.group in groups:
                    w = max(w, g.weight)
            attr.data[v.index].color = (w, w, w, 1.0)
            if w > 0.35:
                painted += 1
        for slot in obj.material_slots:
            tint_material(slot.material)
    print('ACCENT', len(wanted), 'bones,', painted, 'verts')


# ------------------------------------------------------------------ camera: the Lottie's orthographic view
yaw, pitch = (math.radians(v) for v in data['camera'])
right = (math.cos(yaw), 0.0, -math.sin(yaw))
up = (-math.sin(yaw) * math.sin(pitch), math.cos(pitch), -math.cos(yaw) * math.sin(pitch))
toward = (math.sin(yaw) * math.cos(pitch), math.sin(pitch), math.cos(yaw) * math.cos(pitch))
left_, right_, bottom, top = data['scene_bounds']
centre = Vector(right) * ((left_ + right_) / 2) + Vector(up) * ((bottom + top) / 2)
cam_data = bpy.data.cameras.new('LibCam')
cam_data.type, cam_data.ortho_scale = 'ORTHO', right_ - left_
cam = bpy.data.objects.new('LibCam', cam_data)
scene.collection.objects.link(cam)
cam.matrix_world = Matrix.Translation(M(centre) + M(toward) * 8.0) @ Matrix((M(right), M(up), M(toward))).transposed().to_4x4()
cam_data.clip_end = 30.0
scene.camera = cam
scene.render.resolution_x = WIDTH
scene.render.resolution_y = int(round(WIDTH * (top - bottom) / (right_ - left_) / 2)) * 2


def studio_material(name, color, rough=0.9, metal=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bsdf:
        bsdf.inputs['Base Color'].default_value = (*color, 1.0)
        bsdf.inputs['Roughness'].default_value = rough
        if 'Metallic' in bsdf.inputs:
            bsdf.inputs['Metallic'].default_value = metal
    return m


build_gadgets(data.get('gadgets', []))


def aim_light(obj, target):
    obj.rotation_mode = 'QUATERNION'
    obj.rotation_quaternion = Vector((0.0, 0.0, -1.0)).rotation_difference(target - obj.location)


def studio(target):
    """Soft three-point light aimed at this shot and a floor that catches a
    contact shadow. The illustrated sun is switched off so the body reads as
    a person in a room, not a cut-out."""
    ee = scene.eevee
    ee.taa_render_samples = 80
    ee.use_raytracing = True
    ee.use_shadows = True
    ee.use_fast_gi = False  # the flat GI wash was erasing the contact shadow
    if scene.world and scene.world.use_nodes:
        for node in scene.world.node_tree.nodes:
            if node.type == 'BACKGROUND' and node.inputs[1].default_value >= 0.9:
                node.inputs[0].default_value = (0.90, 0.93, 0.96, 1.0)
                node.inputs[1].default_value = 0.82
    for attr, value in (('shadow_ray_count', 4), ('shadow_step_count', 10), ('shadow_resolution_scale', 1.5)):
        if hasattr(ee, attr):
            try:
                setattr(ee, attr, value)
            except (TypeError, ValueError):
                pass
    view = M(toward)
    view.z = 0                             # horizontal: target -> camera, so the wall stays vertical
    if view.length < 1e-4:
        view = Vector((0.0, -1.0, 0.0))
    view.normalize()
    side = M(right)
    side.z = 0
    side = (side.normalized() if side.length > 1e-4 else view.cross(Vector((0, 0, 1))).normalized())
    spec = {
        'KeyLight': (target + view * 3.0 + side * 1.7 + Vector((0, 0, 2.4)), 320, (1.0, 0.95, 0.88), 1.8),
        'FillLight': (target + view * 2.6 - side * 2.2 + Vector((0, 0, 1.3)), 40, (0.84, 0.90, 1.0), 3.4),
        'RimLight': (target - view * 2.4 + side * 0.5 + Vector((0, 0, 2.5)), 36, (1.0, 1.0, 1.0), 1.6),
    }
    for obj in bpy.data.objects:
        if obj.type != 'LIGHT':
            continue
        if obj.data.type == 'SUN':
            obj.hide_render = True
            continue
        if obj.name not in spec:
            obj.hide_render = True
            continue
        loc, energy, color, size = spec[obj.name]
        obj.hide_render = False
        obj.location = loc
        obj.data.energy = energy
        obj.data.color = color
        obj.data.size = size
        obj.data.use_shadow = True
        aim_light(obj, target + Vector((0, 0, 0.7)))
    if 'Floor' in bpy.data.objects:
        floor = bpy.data.objects['Floor']
        floor.hide_render = False
        floor.data.materials.clear()
        floor.data.materials.append(studio_material('StudioFloor', (0.80, 0.84, 0.88)))
    # No backdrop plane: at a three-quarter angle its edge cuts into the frame.
    # The floor and the contact shadow are what put the person in the room.


studio(M(centre))

# ------------------------------------------------------------------ posing
arm = rig.data
REST = {b.name: b.matrix_local.copy() for b in arm.bones}
REST_ROT = {n: m.to_quaternion() for n, m in REST.items()}
HEAD = {n: m.translation.copy() for n, m in REST.items()}
DIR = {b.name: (b.tail_local - b.head_local).normalized() for b in arm.bones}
LEN = {b.name: b.length for b in arm.bones}
B0 = Matrix(((0, 0, 1), (0, -1, 0), (-1, 0, 0))).transposed()  # columns: rest body up, front, right
SIDE = {'near': 'r', 'far': 'l'}
ORDER = [b.name for b in arm.bones]  # parents before children
SCALED = ('upperarm_', 'lowerarm_')


def body_rot(frame):
    U, A, L = (M(v) for v in frame)
    return (Matrix((U, A, L)).transposed() @ B0.inverted()).to_quaternion()


def swing(q_parent, bone, target):
    """Parent rotation, then the smallest turn that aims the bone at target."""
    return (q_parent @ DIR[bone]).rotation_difference(Vector(target).normalized()) @ q_parent


def two_bone(root, target, l1, l2, pole):
    d = target - root
    dist = min(max(d.length, abs(l1 - l2) + 1e-4), l1 + l2 - 1e-4)
    axis = d.normalized()
    perp = (pole - root) - axis * (pole - root).dot(axis)
    perp = perp.normalized() if perp.length > 1e-6 else axis.orthogonal().normalized()
    along = (l1 * l1 - l2 * l2 + dist * dist) / (2 * dist)
    mid = root + axis * along + perp * math.sqrt(max(0.0, l1 * l1 - along * along))
    return mid, root + axis * dist


HALF_SHOULDERS = 0.135  # rig shoulder joint, half the shoulder width (figure3d.HALF_SHOULDERS)


def pose_frame(s, lift=0.0):
    qp, qt = body_rot(s['pelvis_frame']), body_rot(s['thorax_frame'])
    hip, lumbar, shoulder = (M(q) for q in s['torso'])
    Q = {'Root': Quaternion(), 'pelvis': qp}
    Q['spine_01'] = swing(qp, 'spine_01', lumbar - hip)
    Q['spine_02'] = swing(qp.slerp(qt, 0.5), 'spine_02', (lumbar - hip) + (shoulder - lumbar))
    Q['spine_03'] = swing(qt, 'spine_03', shoulder - lumbar)
    ut, at = qt @ Vector((0, 0, 1)), qt @ Vector((0, -1, 0))
    side_axis = ut.cross(at).normalized()
    nod = math.radians(s['nod'])
    # Swing-twist of the chest relative to the pelvis about the body's long axis:
    # the head follows the bend in full but only a third of the twist (lying on
    # the side, the face stays level instead of turning into the mattress).
    rel = qp.inverted() @ Q['spine_03']
    twist = Quaternion((rel.w, 0.0, 0.0, rel.z)).normalized()
    head_base = qp @ (rel @ twist.inverted()) @ Quaternion().slerp(twist, 0.35)
    Q['neck_01'] = Quaternion(side_axis, nod * 0.4) @ Q['spine_03'].slerp(head_base, 0.5)
    Q['head'] = Quaternion(side_axis, nod) @ head_base
    lat = M(s['thorax_frame'][2])  # rig thorax L: towards the near side
    for side, sfx in SIDE.items():
        sh, el, _ = (M(q) for q in s[f'{side} arm'])
        sign = 1 if side == 'near' else -1
        delta = sh - (shoulder + lat * (sign * HALF_SHOULDERS))  # what the rig adds: shrug, retraction
        rest_dir = Q['spine_03'] @ DIR[f'clavicle_{sfx}']
        # Scapulohumeral rhythm: past 30 degrees of arm elevation the shoulder girdle
        # rotates up by about a third of the extra elevation (capped).
        elev = math.degrees((el - sh).angle(-ut, 0.0))
        rhythm = math.radians(min(max(elev - 30.0, 0.0) / 3.0, 28.0))
        axis = rest_dir.cross(ut)
        if axis.length > 1e-6:
            rest_dir = Quaternion(axis.normalized(), rhythm) @ rest_dir
        Q[f'clavicle_{sfx}'] = swing(Q['spine_03'], f'clavicle_{sfx}', rest_dir * LEN[f'clavicle_{sfx}'] + delta)
    pose, heads, solved = {}, {}, {}
    flat_hands = set()
    pose_frame.hand_aim = {}
    for name in ORDER:
        b = arm.bones[name]
        parent = b.parent.name if b.parent else None
        if name == 'pelvis':
            head = M(s['torso'][0]) + Vector((0.0, 0.0, lift))
        elif parent is None:
            head = HEAD[name]
        else:
            k = ARM if parent.startswith(SCALED) else 1.0
            head = heads[parent] + Q[parent] @ ((HEAD[name] - HEAD[parent]) * k)
        heads[name] = head
        sfx = name[-1]
        side = 'near' if sfx == 'r' else 'far'
        if MOCAP and name.startswith(('upperarm_', 'lowerarm_', 'thigh_', 'calf_')):
            # captured motion: follow the performer's segment directions (straight stays straight)
            sh_, el_, hd_ = (M(q) for q in s[f'{side} arm'])
            hp_, kn_, an_ = (M(q) for q in s[f'{side} leg'])
            seg = {'upperarm_': el_ - sh_, 'lowerarm_': hd_ - el_, 'thigh_': kn_ - hp_, 'calf_': an_ - kn_}
            Q[name] = swing(Q[parent], name, seg[name[:-1]])
        elif name.startswith('upperarm_'):
            sh_r, _, hd_r = s[f'{side} arm']
            _, el, hd = (M(q) for q in s[f'{side} arm'])
            # Hands crossed on the chest land inside the character's shirt.
            # Rest each palm on the front of the opposite shoulder and point
            # the elbow out, so the fold reads instead of stabbing the torso.
            if hd_r[2] * sh_r[2] < 0 and abs(hd_r[0] - sh_r[0]) < 0.28:
                hd = M((sh_r[0] + 0.22, sh_r[1] - 0.02, hd_r[2] * 0.75))
                el = M((sh_r[0] + 0.02, sh_r[1] - 0.18, sh_r[2] * 2.4))
                pose_frame.hand_aim[sfx] = M((0.0, 0.2, hd_r[2]))
            wx, wy, wz = s[f'{side} arm'][2]
            for x0, x1, z0, z1, top_y in SURFACES:
                # The palm mesh hangs below the wrist bone, and the rest-pose
                # fingers curl further down. A hand on a support is lifted so
                # the skin meets the surface.
                if x0 - 0.04 < wx < x1 + 0.04 and z0 - 0.06 < wz < z1 + 0.06 and -0.04 < wy - top_y < 0.2:
                    hd = Vector(hd)
                    hd.z = max(hd.z, top_y + 0.08)
                    break
            elbow, wrist = two_bone(head, hd, LEN[name] * ARM, LEN[f'lowerarm_{sfx}'] * ARM, el)
            Q[name] = swing(Q[parent], name, elbow - head)
            solved[f'lowerarm_{sfx}'] = wrist
        elif name.startswith('lowerarm_'):
            Q[name] = swing(Q[parent], name, solved[name] - head)
        elif name.startswith('thigh_'):
            _, kn, an = (M(q) for q in s[f'{side} leg'])
            knee, ankle = two_bone(head, an, LEN[name], LEN[f'calf_{sfx}'], kn)
            Q[name] = swing(Q[parent], name, knee - head)
            solved[f'calf_{sfx}'] = ankle
        elif name.startswith('calf_'):
            Q[name] = swing(Q[parent], name, solved[name] - head)
        elif name.startswith('hand_'):
            Q[name] = Q[parent]
            if sfx in pose_frame.hand_aim:
                Q[name] = swing(Q[parent], name, pose_frame.hand_aim[sfx])
            wrist = s[f'{side} arm'][2]
            for x0, x1, z0, z1, top_y in SURFACES:  # wrist just above a support: lay the hand on it
                if x0 - 0.04 < wrist[0] < x1 + 0.04 and z0 - 0.06 < wrist[2] < z1 + 0.06 and -0.04 < wrist[1] - top_y < 0.2:
                    flat_hands.add(sfx)
                    fore = Q[parent] @ DIR[name]
                    flat = Vector((fore.x, fore.y, 0.0))
                    if flat.length < 0.35:  # forearm upright (pushing on the floor): fingers point the way the head does
                        flat = Vector((ut.x, ut.y, 0.0)) if Vector((ut.x, ut.y)).length > 0.2 else Vector((at.x, at.y, 0.0))
                    if flat.length > 1e-3:
                        Q[name] = swing(Q[parent], name, flat.normalized() + Vector((0, 0, 0.16)))
                    break
        elif (sfx in flat_hands or sfx in pose_frame.hand_aim) and any(name.startswith(p) for p in ('index_', 'middle_', 'ring_', 'pinky_', 'thumb_')):
            # Rest-pose fingers curl into the mat. On a support they lie along the hand.
            aim = Q[f'hand_{sfx}'] @ DIR[f'hand_{sfx}']
            if name.startswith('thumb_'):
                aim = aim + lat * (0.55 if sfx == 'r' else -0.55)
            if aim.length > 1e-4:
                Q[name] = swing(Q[parent], name, aim)
        elif name.startswith('foot_'):
            heel, toe = (M(q) for q in s[f'{side} foot'])
            ankle_rig = M(s[f'{side} leg'][2])
            Q[name] = swing(Q[parent], name, toe - ankle_rig)
        Q.setdefault(name, Q[parent] if parent else Quaternion())
        pose[name] = Matrix.Translation(head) @ (Q[name] @ REST_ROT[name]).to_matrix().to_4x4()
        if name.startswith(SCALED):
            pose[name] = pose[name] @ Matrix.Diagonal((1.0, ARM, 1.0, 1.0))  # shorter along the bone, same thickness
    pose_frame.heads = heads
    return pose


MOCAP = data.get('kind') == 'mocap'


def pose_sample(s, lift):
    """Captured motion keeps the performer's angles, so hands and feet land where
    the character's proportions put them: raise or lower the body so the ones
    on the floor in the capture touch the floor."""
    pose = pose_frame(s, lift)
    if not MOCAP:
        return pose
    err = []
    for side, sfx in SIDE.items():
        for end, bone in ((s[f'{side} arm'][2], f'hand_{sfx}'), (s[f'{side} leg'][2], f'foot_{sfx}')):
            if end[1] < 0.15:
                err.append(M(end).z - pose_frame.heads[bone].z)
    if not err:
        return pose
    return pose_frame(s, lift + sum(err) / len(err))


for pb in rig.pose.bones:
    pb.rotation_mode = 'QUATERNION'
for sfx in ('l', 'r'):  # the shortened forearm and the hand keep their own scale
    arm.bones[f'lowerarm_{sfx}'].inherit_scale = 'NONE'
    arm.bones[f'hand_{sfx}'].inherit_scale = 'NONE'
skinned = [md for o in bpy.data.objects for md in o.modifiers if md.type == 'ARMATURE']
layer = bpy.context.view_layer


def key_all(lifts):
    """Poses every sample (mesh deformation off, so updates stay cheap) and keys it."""
    if rig.animation_data:
        rig.animation_data.action = None
    for md in skinned:
        md.show_viewport = False
    for s, lift in zip(data['samples'], lifts):
        pose = pose_sample(s, lift)
        for name in ORDER:
            rig.pose.bones[name].matrix = pose[name]
            layer.update()
        for name in ORDER:
            pb = rig.pose.bones[name]
            for ch in ('location', 'rotation_quaternion', 'scale'):
                pb.keyframe_insert(ch, frame=s['fr'] + 1)
    for md in skinned:
        md.show_viewport = True


def lying_weight(s):
    """1 when the trunk lies flat, 0 from 45 degrees up."""
    up = abs(s['thorax_frame'][0][1])
    return min(max((0.72 - up) / 0.3, 0.0), 1.0)


def support_top(s):
    x, _, z = s['torso'][0]
    tops = [t for x0, x1, z0, z1, t in SURFACES if x0 <= x <= x1 and z0 <= z <= z1]
    return max(tops) if tops else 0.0


# The character is broader and deeper than the rig's figure: lying down it
# would sink into the mattress. Measure the deformed body on each lying frame
# and lift the pelvis until the trunk rests on the support; hands and feet stay
# on the rig's contacts (IK), only the body is raised.
lifts = [0.0] * len(data['samples'])
key_all(lifts)
weights = [lying_weight(s) for s in data['samples']]
if data.get('lift', True) and any(w > 0 for w in weights):
    body = bpy.data.objects['Kineti_Body.male_casualsuit04']  # the clothes: outermost surface, bone-named groups
    groups = {g.index for g in body.vertex_groups
              if g.name.startswith(('pelvis', 'spine', 'clavicle', 'neck', 'head', 'upperarm', 'thigh'))}
    trunk = [v.index for v in body.data.vertices
             if v.groups and max(v.groups, key=lambda e: e.weight).group in groups]
    raw = []
    for s, w in zip(data['samples'], weights):
        if w <= 0:
            raw.append(0.0)
            continue
        scene.frame_set(s['fr'] + 1)
        ev = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh = ev.to_mesh()
        mw = ev.matrix_world
        low = min((mw @ mesh.vertices[i].co).z for i in trunk)
        ev.to_mesh_clear()
        raw.append(min(max(support_top(s) + 0.004 - low, -0.05), 0.25) * w)
    # light smoothing so the lift never jitters between samples
    lifts = [sum(raw[max(0, i - 1):i + 2]) / len(raw[max(0, i - 1):i + 2]) for i in range(len(raw))]
    print('LIFT max', round(max(lifts), 3), 'min', round(min(lifts), 3))
    key_all(lifts)

# ------------------------------------------------------------------ render
scene.frame_start, scene.frame_end = 1, data['frames_total']
scene.render.fps = data['fps']
scene.render.image_settings.file_format = 'PNG'
if MODE == 'still':
    n = data['frames_total']
    for f in (1, n // 4, n // 2, 3 * n // 4):
        scene.frame_set(f)
        scene.render.filepath = f'{OUT}_{f:04d}.png'
        bpy.ops.render.render(write_still=True)
else:
    scene.render.filepath = OUT + '_'
    bpy.ops.render.render(animation=True)
print('DONE', OUT)
