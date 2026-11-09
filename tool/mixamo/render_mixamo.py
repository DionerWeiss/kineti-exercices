"""Blender side of the Mixamo pilot: drives the Kineti woman (MPFB, Mixamo
skeleton) with a Mixamo FBX and renders a PNG sequence.

    blender -b kineti_woman_mixamo.blend --python render_mixamo.py -- <spec.json>

spec.json:
    fbx        Mixamo FBX, "Without Skin"
    out        PNG prefix (frames are <out>_0001.png ...)
    timeline   [[src_from, src_to, n_frames], ...] segments of source time,
               played at any speed or backwards (trim, slow down, ping-pong)
    yaw        camera around the body, degrees: 0 front, 90 her left side
    chair      true: a chair under the hips at the frame `chair_frame` (output frame)
    width      render width (height is width * 10 / 16)
    still      list of output frames to render instead of the whole loop

Retarget: for each bone, world rotation = source world rotation @ C, where
C = src_rest^-1 @ R_align @ tgt_rest and R_align turns the target rest bone
onto the source rest bone (the source is a T-pose, MPFB an A-pose). Hip
translation is scaled by the ratio of hip heights.
"""

import json
import math
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector

spec = json.load(open(sys.argv[sys.argv.index('--') + 1]))
scene = bpy.context.scene
SKINNED = spec.get('skinned', False)  # the FBX brings its own character (Mixamo "With Skin")
HIPS = 'mixamorig:Hips'
HIP_PATH = []  # world hip position on every output frame


def rot(m):
    return m.to_3x3().normalized().to_quaternion()


if SKINNED:
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.ops.import_scene.fbx(filepath=spec['fbx'])
    tgt = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    src = tgt
    names = [b.name for b in tgt.data.bones]
    HIPS = next(n for n in names if n.split(':')[-1] == 'Hips')  # prefix varies: mixamorig1:, mixamorig9:...
    TW = tgt.matrix_world.copy()

    def pose_at(t):
        """The character's own pose at source time t."""
        scene.frame_set(int(math.floor(t)), subframe=t - math.floor(t))
        HIP_PATH.append(TW @ tgt.pose.bones[HIPS].head)
        return {n: tgt.pose.bones[n].matrix_basis.copy() for n in names}

    if spec.get('motion_glb'):
        # Motion from the desk-break library (MIT): a 15-bone mannequin whose bones all
        # point up and whose rest pose is standing, arms down. Each source bone's world
        # rotation away from its rest is applied to the character's matching bones,
        # taken from her rest pose with the arms brought down to her sides.
        tgt.animation_data.action = None
        scene.render.fps = 30  # so the glTF importer keys the 30 fps animations on whole frames
        bpy.ops.import_scene.gltf(filepath=spec['motion_glb'])
        db = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and o is not tgt)
        for o in bpy.data.objects:
            if o.type == 'MESH' and (o.parent is db or any(m.type == 'ARMATURE' and m.object is db for m in o.modifiers)):
                o.hide_render = True
            if o.type == 'MESH' and o.name == 'Icosphere':
                o.hide_render = True
        act = bpy.data.actions[spec['motion']]
        db.animation_data.action = act
        if hasattr(db.animation_data, 'action_slot') and db.animation_data.action_slot is None and act.slots:
            db.animation_data.action_slot = act.slots[0]
        print('motion', act.name, tuple(act.frame_range))
        MOTION_RANGE = tuple(act.frame_range)
        DW = db.matrix_world.copy()
        P = HIPS.split(':')[0] + ':'
        SRC = {'Hips': 'hips', 'Spine2': 'spine', 'Head': 'neck'}
        for side, s in (('Left', 'L'), ('Right', 'R')):
            SRC.update({f'{side}Shoulder': 'spine', f'{side}Arm': f'arm{s}', f'{side}ForeArm': f'elbow{s}',
                        f'{side}Hand': f'hand{s}', f'{side}UpLeg': f'leg{s}', f'{side}Leg': f'knee{s}',
                        f'{side}Foot': f'foot{s}', f'{side}ToeBase': f'foot{s}'})
        down = Vector((0.0, 0.0, -1.0))
        REF = {}
        for n in names:
            tb = tgt.data.bones[n]
            r = rot(TW @ tb.matrix_local)
            short = n.split(':')[-1]
            if short.startswith(('LeftArm', 'RightArm', 'LeftForeArm', 'RightForeArm')) or 'Hand' in short:
                d = (TW.to_3x3() @ (tb.tail_local - tb.head_local)).normalized()
                # arms (and hands and fingers) down by the sides, as the mannequin stands
                side_axis = Vector((1.0 if short.startswith('Left') else -1.0, 0.0, 0.0))
                horiz = Vector((d.x, d.y, 0.0))
                if horiz.length > 0.3 and horiz.normalized().dot(side_axis) > 0.5:
                    r = d.rotation_difference(down) @ r
            if short in ('Hips', 'Spine', 'Spine1', 'Spine2', 'Neck', 'Head'):
                # the mannequin's trunk, neck and head stand dead straight: so does her reference
                d = (TW.to_3x3() @ (tb.tail_local - tb.head_local)).normalized()
                r = d.rotation_difference(Vector((0.0, 0.0, 1.0))) @ r
            REF[n] = r
        db_rest = {b.name: rot(DW @ b.matrix_local) for b in db.data.bones}
        db_hips_rest = DW @ db.data.bones['hips'].head_local
        t_hips_rest_w = TW @ tgt.data.bones[HIPS].head_local
        KH = t_hips_rest_w.z / db_hips_rest.z
        TWR = TW.to_quaternion()
        TWI = TW.inverted()

        def pose_at(t):
            scene.frame_set(int(math.floor(t)), subframe=t - math.floor(t))
            D = {b.name: rot(DW @ db.pose.bones[b.name].matrix) @ db_rest[b.name].inverted() for b in db.data.bones}
            H, S, N = D['hips'], D['spine'], D['neck']
            rel = H.inverted() @ S
            Qw = {}
            for n in names:
                short = n.split(':')[-1]
                if short == 'Spine':
                    Qw[n] = H @ Quaternion().slerp(rel, 1 / 3) @ REF[n]
                elif short == 'Spine1':
                    Qw[n] = H @ Quaternion().slerp(rel, 2 / 3) @ REF[n]
                elif short == 'Neck':
                    Qw[n] = S @ Quaternion().slerp(S.inverted() @ N, 0.5) @ REF[n]
                elif short in SRC:
                    Qw[n] = D[SRC[short]] @ REF[n]
                elif short.startswith(('LeftHand', 'RightHand')):  # fingers ride on the hand
                    Qw[n] = D['hand' + ('L' if short.startswith('Left') else 'R')] @ REF[n]
            pose_arm, basis = {}, {}
            for n in names:
                b = tgt.data.bones[n]
                rest = b.matrix_local
                if b.parent:
                    prest = b.parent.matrix_local
                    follow = pose_arm[b.parent.name] @ (prest.inverted() @ rest)
                else:
                    follow = rest.copy()
                if n in Qw:
                    head = follow.translation
                    if n == HIPS:
                        now = DW @ db.pose.bones['hips'].head
                        head = TWI @ (t_hips_rest_w + (now - db_hips_rest) * KH)
                    m = Matrix.Translation(head) @ (TWR.inverted() @ Qw[n]).to_matrix().to_4x4()
                else:
                    m = follow
                pose_arm[n] = m
                if n == HIPS:
                    HIP_PATH.append(TW @ m.translation)
                if b.parent:
                    basis[n] = (prest.inverted() @ rest).inverted() @ pose_arm[b.parent.name].inverted() @ m
                else:
                    basis[n] = rest.inverted() @ m
            return basis
else:
    tgt = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    bpy.ops.import_scene.fbx(filepath=spec['fbx'])
    src = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and o is not tgt)
    src.hide_render = True
    for o in src.children:
        o.hide_render = True

    names = [b.name for b in tgt.data.bones]  # parents before children
    shared = [n for n in names if n in src.data.bones]
    SW, TW = src.matrix_world.copy(), tgt.matrix_world.copy()
    TWI = TW.inverted()
    C = {}
    for n in shared:
        sb, tb = src.data.bones[n], tgt.data.bones[n]
        s_rest, t_rest = rot(SW @ sb.matrix_local), rot(TW @ tb.matrix_local)
        s_dir = (SW.to_3x3() @ (sb.tail_local - sb.head_local)).normalized()
        t_dir = (TW.to_3x3() @ (tb.tail_local - tb.head_local)).normalized()
        align = t_dir.rotation_difference(s_dir)
        C[n] = s_rest.inverted() @ align @ t_rest

    s_hips_rest = SW @ src.data.bones[HIPS].head_local
    t_hips_rest = TW @ tgt.data.bones[HIPS].head_local
    K = t_hips_rest.z / s_hips_rest.z
    print('hip ratio', round(K, 3))

    def pose_at(t):
        """Armature-space basis matrices for the target at source time t."""
        scene.frame_set(int(math.floor(t)), subframe=t - math.floor(t))
        pose_arm, basis = {}, {}
        for n in names:
            b = tgt.data.bones[n]
            rest = b.matrix_local
            if b.parent:
                prest = b.parent.matrix_local
                follow = pose_arm[b.parent.name] @ (prest.inverted() @ rest)
            else:
                follow = rest.copy()
            if n in C:
                q = TW.to_quaternion().inverted() @ rot(SW @ src.pose.bones[n].matrix) @ C[n]
                head = follow.translation
                if n == HIPS:
                    s_now = SW @ src.pose.bones[n].head
                    head = TWI @ (t_hips_rest + (s_now - s_hips_rest) * K)
                m = Matrix.Translation(head) @ q.to_matrix().to_4x4()
            else:
                m = follow
            pose_arm[n] = m
            if n == HIPS:
                HIP_PATH.append(TW @ m.translation)
            if b.parent:
                basis[n] = (prest.inverted() @ rest).inverted() @ pose_arm[b.parent.name].inverted() @ m
            else:
                basis[n] = rest.inverted() @ m
        return basis


# ------------------------------------------------------------------ bake
times = []
if spec['timeline'] == 'auto':  # the library clip as authored, one loop, 30 fps
    a, b = MOTION_RANGE
    spec['timeline'] = [[a, b - 1, int(round(b - a))]]
for a, b, n in spec['timeline']:
    times += [a + (b - a) * i / max(n - 1, 1) for i in range(n)] if n > 1 else [a]
for pb in tgt.pose.bones:
    pb.rotation_mode = 'QUATERNION'
baked = [pose_at(t) for t in times]
src.animation_data.action = None  # source no longer needed; the scene timeline is the output now
if tgt.animation_data:
    tgt.animation_data.action = None
tgt.animation_data_create()
for f, basis in enumerate(baked, start=1):
    for n, m in basis.items():
        pb = tgt.pose.bones[n]
        pb.matrix_basis = m
        pb.keyframe_insert('location', frame=f)
        pb.keyframe_insert('rotation_quaternion', frame=f)
scene.frame_start, scene.frame_end = 1, len(times)
scene.render.fps = 30
print('frames', len(times))

# ------------------------------------------------------------------ set
body_objs = [o for o in bpy.data.objects if o.type == 'MESH' and any(m.type == 'ARMATURE' and m.object is tgt for m in o.modifiers)]


def fix_materials(objs):
    """Mixamo FBX materials come in glossy (shininess and specular maps read as low
    roughness) and hair without its alpha: make cloth matte, skin satin, hair cut out."""
    seen = set()
    for o in objs:
        for slot in o.material_slots:
            m = slot.material
            if not m or m.name in seen or not m.node_tree:
                continue
            seen.add(m.name)
            nt = m.node_tree
            bsdf = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
            if not bsdf:
                continue
            name = m.name.lower()
            kind = ('hair' if any(k in name for k in ('hair', 'lash', 'brow')) else
                    'skin' if any(k in name for k in ('body', 'skin', 'face', 'head', 'arm', 'leg')) else 'cloth')
            for sock, val in (('Roughness', {'hair': 0.55, 'skin': 0.5, 'cloth': 0.85}[kind]),
                              ('Metallic', 0.0), ('Specular IOR Level', {'skin': 0.35}.get(kind, 0.2)),
                              ('Coat Weight', 0.0), ('Sheen Weight', 0.0)):
                if sock in bsdf.inputs:
                    for link in list(bsdf.inputs[sock].links):
                        nt.links.remove(link)
                    bsdf.inputs[sock].default_value = val
            if kind == 'skin' and 'Subsurface Weight' in bsdf.inputs:
                bsdf.inputs['Subsurface Weight'].default_value = 0.15
                bsdf.inputs['Subsurface Radius'].default_value = (1.0, 0.45, 0.25)
                bsdf.inputs['Subsurface Scale'].default_value = 0.01
            base = bsdf.inputs['Base Color']
            img = base.links[0].from_node if base.is_linked and base.links[0].from_node.type == 'TEX_IMAGE' else None
            if kind == 'hair' and img is not None and not bsdf.inputs['Alpha'].is_linked:
                nt.links.new(img.outputs['Alpha'], bsdf.inputs['Alpha'])
            print('MAT', m.name, kind, 'img' if img else '-')


fix_materials(body_objs)


def lowest_points():
    """Deformed body vertices (world) at the current frame."""
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    for o in body_objs:
        ev = o.evaluated_get(dg)
        mesh = ev.to_mesh()
        mw = ev.matrix_world
        pts += [mw @ v.co for v in mesh.vertices]
        ev.to_mesh_clear()
    return pts


MAT_TOP = 0.012
if spec.get('ground') == 'mat':
    # The mannequin's grounding was baked for its own body: put HER lowest point on the mat
    # on every frame (lightly smoothed so contact never jitters).
    base = tgt.location.copy()
    raw = []
    for f in range(scene.frame_start, scene.frame_end + 1):
        scene.frame_set(f)
        raw.append(MAT_TOP - min(p.z for p in lowest_points()))
    dz = [sum(raw[max(0, i - 2):i + 3]) / len(raw[max(0, i - 2):i + 3]) for i in range(len(raw))]
    for f, d in zip(range(scene.frame_start, scene.frame_end + 1), dz):
        tgt.location = base + Vector((0, 0, d))
        tgt.keyframe_insert('location', frame=f)
    scene.frame_set(scene.frame_start)
    pts = lowest_points()
    xs, ys = [p.x for p in pts], [p.y for p in pts]
    print('ground dz', round(min(dz), 3), round(max(dz), 3))



def box(name, lo, hi, color):
    mesh = bpy.data.meshes.new(name)
    v = [(x, y, z) for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]
    f = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    mesh.from_pydata(v, [], f)
    o = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(o)
    o.data.materials.append(material(name, color, 0.6))
    md = o.modifiers.new('bevel', 'BEVEL')
    md.width, md.segments = 0.006, 2
    return o


def material(name, color, rough=0.85):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs['Base Color'].default_value = (*color, 1.0)
    bsdf.inputs['Roughness'].default_value = rough
    return m


def chair_at(frame):
    """Seat under the thighs at `frame`, the backrest behind the hips (she faces -Y)."""
    scene.frame_set(frame)
    dg = bpy.context.evaluated_depsgraph_get()
    hips = TW @ tgt.pose.bones[HIPS].head
    pts = []
    for o in body_objs:  # every skinned mesh: the lowest cloth under the hips is the seat
        ev = o.evaluated_get(dg)
        mesh = ev.to_mesh()
        pts += [ev.matrix_world @ v.co for v in mesh.vertices]
        ev.to_mesh_clear()
    under = [p.z for p in pts if abs(p.x - hips.x) < 0.2 and -0.25 < p.y - hips.y < 0.1 and p.z < hips.z]
    top = min(under) if under else hips.z - 0.12
    wood = (0.72, 0.52, 0.33)
    x0, x1 = hips.x - 0.23, hips.x + 0.23
    back, front = hips.y + 0.16, hips.y - 0.30
    leg = 0.016
    for i, (x, y) in enumerate([(x0 + leg, front + leg), (x1 - leg, front + leg), (x0 + leg, back - leg), (x1 - leg, back - leg)]):
        box(f'chair leg {i}', (x - leg, y - leg, 0), (x + leg, y + leg, top - 0.03), wood)
    box('chair seat', (x0, front, top - 0.03), (x1, back, top), wood)
    for i, x in enumerate((x0 + leg, x1 - leg)):
        box(f'chair post {i}', (x - leg, back - 0.03, top), (x + leg, back, top + 0.5), wood)
    box('chair back', (x0, back - 0.025, top + 0.24), (x1, back, top + 0.5), wood)
    print('chair seat top', round(top, 3))


if spec.get('chair'):
    chair_at(spec['chair_frame'])
if spec.get('ground') == 'mat':
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    w, l = max(max(xs) - min(xs), 0.5) / 2 + 0.25, max(max(ys) - min(ys), 0.5) / 2 + 0.3
    mat = box('exercise mat', (cx - w, cy - l, 0.0), (cx + w, cy + l, MAT_TOP), (0.20, 0.42, 0.55))

yaw = math.radians(spec.get('yaw', 30))
view = Vector((math.sin(yaw), -math.cos(yaw), 0.0))
side = Vector((math.cos(yaw), math.sin(yaw), 0.0))
mid = sum(HIP_PATH, Vector()) / len(HIP_PATH)
target = Vector((mid.x, mid.y + spec.get('shift_y', 0.0), spec.get('look_z', 0.82)))


def cyclorama(wall=3.0, radius=2.0):
    """Studio sweep: floor that curves up into a wall behind her, facing the camera. No horizon."""
    prof = [(-12.0, 0.0), (wall - radius, 0.0)]
    for i in range(1, 17):
        a = math.pi / 2 * i / 16
        prof.append((wall - radius + radius * math.sin(a), radius - radius * math.cos(a)))
    prof.append((wall, 10.0))
    verts, faces = [], []
    for x in (-14.0, 14.0):
        verts += [(x, y, z) for y, z in prof]
    n = len(prof)
    faces = [(i, i + 1, n + i + 1, n + i) for i in range(n - 1)]
    mesh = bpy.data.meshes.new('Cyclorama')
    mesh.from_pydata(verts, [], faces)
    for p in mesh.polygons:
        p.use_smooth = True
    o = bpy.data.objects.new('Cyclorama', mesh)
    scene.collection.objects.link(o)
    o.location = (target.x, target.y, 0.0)
    o.rotation_euler = (0.0, 0.0, yaw)  # local +Y (the wall) points away from the camera
    o.data.materials.append(material('Floor', (0.70, 0.75, 0.80), 0.95))
    return o


cyclorama()

world = scene.world or bpy.data.worlds.new('World')
scene.world = world
world.use_nodes = True
bg = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
bg.inputs[0].default_value = (0.90, 0.93, 0.96, 1.0)
bg.inputs[1].default_value = 0.45

# ------------------------------------------------------------------ camera and light
cam_data = bpy.data.cameras.new('Cam')
cam_data.lens = 85
cam_data.sensor_width = 36
cam = bpy.data.objects.new('Cam', cam_data)
scene.collection.objects.link(cam)
dist = spec.get('distance', 7.2)
cam.location = target + view * dist + Vector((0, 0, spec.get('cam_height', 0.55)))
cam.rotation_mode = 'QUATERNION'
cam.rotation_quaternion = (target - cam.location).to_track_quat('-Z', 'Y')
scene.camera = cam
for o in bpy.data.objects:
    if o.type == 'LIGHT':
        o.hide_render = True
for name, loc, energy, color, size in (
        ('Key', view * 3.0 + side * 1.7 + Vector((0, 0, 2.6)), 260, (1.0, 0.95, 0.88), 1.8),
        ('Fill', view * 2.6 - side * 2.2 + Vector((0, 0, 1.4)), 45, (0.84, 0.90, 1.0), 3.4),
        ('Rim', -view * 2.4 + side * 0.5 + Vector((0, 0, 2.6)), 60, (1.0, 1.0, 1.0), 1.6)):
    ld = bpy.data.lights.new(name, 'AREA')
    ld.energy, ld.color, ld.size = energy, color, size
    lo = bpy.data.objects.new(name, ld)
    scene.collection.objects.link(lo)
    lo.location = target + loc
    lo.rotation_mode = 'QUATERNION'
    lo.rotation_quaternion = (target - lo.location).to_track_quat('-Z', 'Y')

if spec.get('engine') == 'CYCLES':
    # Path tracing on the GPU (OptiX), denoised: soft contact shadows and skin that reads as skin.
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'OPTIX'
    prefs.get_devices()
    for d in prefs.devices:
        d.use = d.type == 'OPTIX'
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'GPU'
    scene.cycles.samples = spec.get('samples', 96)
    scene.cycles.use_denoising = True
    scene.cycles.denoiser = 'OPTIX'
    scene.cycles.max_bounces = 6
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
else:
    scene.render.engine = 'BLENDER_EEVEE'
    ee = scene.eevee
    ee.taa_render_samples = 64
    for attr, value in (('use_raytracing', True), ('use_shadows', True)):
        if hasattr(ee, attr):
            setattr(ee, attr, value)
    scene.view_settings.view_transform = 'Standard'
width = spec.get('width', 1280)
scene.render.resolution_x, scene.render.resolution_y = width, width * 10 // 16
scene.render.image_settings.file_format = 'PNG'

if spec.get('still'):
    for f in spec['still']:
        scene.frame_set(f)
        scene.render.filepath = f"{spec['out']}_{f:04d}.png"
        bpy.ops.render.render(write_still=True)
else:
    scene.render.filepath = spec['out'] + '_'
    bpy.ops.render.render(animation=True)
print('DONE')
