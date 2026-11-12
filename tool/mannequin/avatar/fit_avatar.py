"""Prototype: swap the desk-break wooden mannequin for a humanoid avatar (the MPFB Kineti woman) on the SAME rig,
so every baked action, prop and camera of render_mannequin.py keeps working (no retargeting).

    blender -b <lib exercises.blend> --python fit_avatar.py -- <kineti_woman_mixamo.blend> <out.blend> [flat|real]

How:
1. The MPFB meshes (body, suit, shoes, hair, eyes, brows, lashes) are baked (shape-key mix + clothing masks).
2. Each vertex is moved by linear blend skinning with one transform per Mixamo bone, so the avatar's joints land
   exactly on the desk-break joints (rest pose: arms straight down, palms to the thighs, legs straight):
   a uniform scale to the mannequin's height, plus per-limb stretch and rotation for legs, clavicles, arms, hands.
3. The Mixamo weights are summed into the 15 desk-break groups, the meshes are joined into one object named
   'mannequin' (render_mannequin.py picks it up as the body) and bound to the rig. The wooden mannequin is deleted.
4. The rig has no finger bones, so the Mixamo finger weights become shape keys grip_L / grip_R (a closed hand);
   render_mannequin.py (AVATAR=1) turns them on for jobs whose props are held (dumbbell, band, stick, cane...).
5. Style "flat" (default) swaps the MPFB materials for matte solid colours, like a fitness-app character: plain
   skin, solid hair, the Kineti shirt and plain trousers (kineti_suit_flat.png, saved next to <out.blend>).
   The shoes lose their sock tops, which poked through the trousers.
   Style "lowpoly" (lowpoly.py) is the faceted fitness-app man built by build_man.py: blue V-neck shirt, black
   shorts and hair are shells of the body, everything is decimated and shaded flat, the Kineti mark is on the chest.
   The shoes follow the foot only, and a Corrective Smooth on the skin of the knees, elbows and wrists keeps those
   bends round (linear blend skinning pinches them). With an avatar, render_mannequin.py also plants the palms
   flat on floor supports (plant_hands.py).

    blender -b --python build_man.py -- kineti_man_mixamo.blend
    blender -b <lib exercises.blend> --python fit_avatar.py -- kineti_man_mixamo.blend <out.blend> lowpoly
"""
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index('--') + 1:]
SRC, OUT = argv[0], argv[1]
STYLE = argv[2] if len(argv) > 2 else 'flat'  # flat | real | lowpoly (lowpoly.py: faceted man, shirt, shorts)

scene = bpy.context.scene
rig = next(o for o in scene.objects if o.type == 'ARMATURE')
old = next(o for o in scene.objects if o.type == 'MESH' and any(m.type == 'ARMATURE' for m in o.modifiers))
rig.animation_data_create().action = None
for pb in rig.pose.bones:
    pb.rotation_mode = 'QUATERNION'
    pb.rotation_quaternion = (1, 0, 0, 0)
    pb.location = (0, 0, 0)
bpy.context.view_layer.update()


def dj(name):  # desk-break joint (bone head) in world space, rest pose
    return rig.matrix_world @ rig.data.bones[name].head_local


desk_top = max((old.matrix_world @ v.co).z for v in old.data.vertices)

# --- 1. append the MPFB avatar
with bpy.data.libraries.load(SRC, link=False) as (src, dst):
    dst.objects = list(src.objects)
for o in dst.objects:
    scene.collection.objects.link(o)
mrig = next(o for o in dst.objects if o.type == 'ARMATURE')
mrig.animation_data_create().action = None
for pb in mrig.pose.bones:
    pb.matrix_basis = Matrix()
meshes = [o for o in dst.objects if o.type == 'MESH']
for o in meshes:
    for m in o.modifiers:
        # lowpoly keeps the whole body under the shoes: the shoe tops are cut to the ankle, so the skin shows
        if m.type in ('ARMATURE', 'SUBSURF') or STYLE == 'lowpoly' and m.type == 'MASK' and m.name.startswith('Delete'):
            m.show_viewport = m.show_render = False
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()

baked = []
for o in meshes:
    me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    no = bpy.data.objects.new(o.name.split('.')[-1] + '_fit', me)
    scene.collection.objects.link(no)
    no.matrix_world = o.matrix_world
    if not no.vertex_groups:  # older Blender keeps group names on the object; the weights came with the mesh
        for vg in o.vertex_groups:
            no.vertex_groups.new(name=vg.name)
    assert [g.name for g in no.vertex_groups] == [g.name for g in o.vertex_groups], o.name
    baked.append(no)
print('BAKED', [(o.name, len(o.data.vertices)) for o in baked])


def mj(name):  # MPFB joint in world space, rest pose
    return mrig.matrix_world @ mrig.data.bones['mixamorig:' + name].head_local


# --- 2. one world transform per Mixamo bone
body = next(o for o in baked if o.name.startswith('body'))
mpfb_top = max((body.matrix_world @ v.co).z for v in body.data.vertices)
mpfb_bot = min((o.matrix_world @ v.co).z for o in baked for v in o.data.vertices)
s = (desk_top - 0.0) / (mpfb_top - mpfb_bot)
hips_y = mj('Hips').y
foot_z = (mj('LeftFoot').z + mj('RightFoot').z) / 2
G = Matrix.Translation((0, -hips_y * s, dj('footL').z - foot_z * s)) @ Matrix.Scale(s, 4)
print(f'SCALE {s:.4f} mpfb height {mpfb_top - mpfb_bot:.3f} -> {desk_top:.3f}')


def rot_between(a, b):
    return a.normalized().rotation_difference(b.normalized()).to_matrix()


def frame_rot(d0, a0, d1, a1):
    """Rotation taking direction d0 to d1 and the across-vector a0 (made orthogonal to d0) to a1."""
    def basis(d, a):
        d = d.normalized()
        a = (a - d * a.dot(d)).normalized()
        return Matrix((d, a, d.cross(a))).transposed()
    return basis(d1, a1) @ basis(d0, a0).transposed()


def limb(h_r, t_r, h_t, t_t, R=None):
    """Takes the rest segment h_r->t_r onto h_t->t_t: rotates, stretches along the bone (girth scales by s)."""
    u = (t_r - h_r).normalized()
    k = (t_t - h_t).length / (t_r - h_r).length
    M = Matrix.Identity(3) * s + (k - s) * Matrix([[u[i] * u[j] for j in range(3)] for i in range(3)])
    R = R if R is not None else rot_between(t_r - h_r, t_t - h_t)
    return Matrix.Translation(h_t) @ (R @ M).to_4x4() @ Matrix.Translation(-h_r)


D = {}
DOWN, FWD = Vector((0, 0, -1)), Vector((0, -1, 0))
for side, x in (('Left', 'L'), ('Right', 'R')):
    D[side + 'UpLeg'] = limb(mj(side + 'UpLeg'), mj(side + 'Leg'), dj('leg' + x), dj('knee' + x))
    D[side + 'Leg'] = limb(mj(side + 'Leg'), mj(side + 'Foot'), dj('knee' + x), dj('foot' + x))
    foot = Matrix.Translation(dj('foot' + x) - G @ mj(side + 'Foot')) @ G  # the foot keeps flat, only moves
    D[side + 'Foot'] = D[side + 'ToeBase'] = foot
    D[side + 'Shoulder'] = limb(mj(side + 'Shoulder'), mj(side + 'Arm'), G @ mj(side + 'Shoulder'), dj('arm' + x))
    D[side + 'Arm'] = limb(mj(side + 'Arm'), mj(side + 'ForeArm'), dj('arm' + x), dj('elbow' + x))
    # hand: fingers down, thumb side forward (palm faces the thigh); the forearm takes half of the twist
    hd = mj(side + 'HandMiddle1') - mj(side + 'Hand')
    ha = mj(side + 'HandIndex1') - mj(side + 'HandPinky1')
    Rh = frame_rot(hd, ha, DOWN, FWD)
    Rmin = rot_between(hd, DOWN)
    q = (Rh @ Rmin.transposed()).to_quaternion()
    axis, ang = q.to_axis_angle()
    ang = ang if axis.dot(DOWN) >= 0 else -ang
    print(f'TWIST {side} {np.degrees(ang):.1f} deg')
    Rf = Matrix.Rotation(ang / 2, 3, DOWN) @ rot_between(mj(side + 'Hand') - mj(side + 'ForeArm'), DOWN)
    D[side + 'ForeArm'] = limb(mj(side + 'ForeArm'), mj(side + 'Hand'), dj('elbow' + x), dj('hand' + x), Rf)
    D[side + 'Hand'] = Matrix.Translation(dj('hand' + x)) @ (Rh * s).to_4x4() @ Matrix.Translation(-mj(side + 'Hand'))

GROUP = {'Hips': 'hips', 'Spine': 'spine', 'Spine1': 'spine', 'Spine2': 'spine', 'Neck': 'neck', 'Head': 'neck'}
for side, x in (('Left', 'L'), ('Right', 'R')):
    GROUP.update({side + 'Shoulder': 'spine', side + 'Arm': 'arm' + x, side + 'ForeArm': 'elbow' + x,
                  side + 'Hand': 'hand' + x, side + 'UpLeg': 'leg' + x, side + 'Leg': 'knee' + x,
                  side + 'Foot': 'foot' + x, side + 'ToeBase': 'foot' + x})


def bone_key(g):
    """Mixamo group -> the key of D / GROUP (fingers follow the hand, toes the foot, head ends the head)."""
    n = g.replace('mixamorig:', '')
    for side in ('Left', 'Right'):
        if n.startswith(side + 'Hand'):
            return side + 'Hand'
        if n.startswith(side + 'Toe'):
            return side + 'ToeBase'
    if n.startswith('Head') or 'Eye' in n:
        return 'Head'
    return n if n in GROUP else None


# --- grip: the desk-break rig has no finger bones, so a closed hand is a shape key (fingers curled around a
# 3-4 cm handle). Each phalanx turns about its own joint, toward the palm (palms face the thighs at rest).
GRIP = {'Thumb': (20, 25, 30), 'Index': (55, 85, 50), 'Middle': (62, 90, 50), 'Ring': (68, 90, 50), 'Pinky': (74, 90, 50)}
FW = {}


def rot_about(J, u, deg):
    return Matrix.Translation(J) @ Matrix.Rotation(np.radians(deg), 4, u) @ Matrix.Translation(-J)


def finger_pose(out, FW, wsum, side, angles):
    """Offsets (N, 3) that curl the fingers of one side by `angles` (degrees per phalanx), in the fitted space."""
    hand = D[side + 'Hand']
    palm = Vector((-1, 0, 0)) if side == 'Left' else Vector((1, 0, 0))  # toward the body's midline
    outh = np.c_[out, np.ones(len(out))]
    dlt = np.zeros_like(out)
    bones = mrig.data.bones
    for f, degs in angles.items():
        T = Matrix()
        for i, deg in enumerate(degs, 1):
            nm = f'{side}Hand{f}{i}'
            if 'mixamorig:' + nm not in bones:
                break
            J = hand @ mj(nm)
            nxt = f'mixamorig:{side}Hand{f}{i + 1}'
            E = hand @ (mrig.matrix_world @ (bones[nxt].head_local if nxt in bones else bones['mixamorig:' + nm].tail_local))
            u = (E - J).cross(palm).normalized()
            T = T @ rot_about(J, u, deg)
            w = FW.get(nm)
            if w is not None and w.any():
                dlt += (w / np.maximum(wsum, 1e-9))[:, None] * ((outh @ np.array(T).T)[:, :3] - out)
    return dlt


if STYLE == 'lowpoly':  # faceted man: the shirt, shorts and hair are shells of the body (lowpoly.py)
    import os
    HERE = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, HERE)
    import lowpoly
    MARK = bpy.data.images.load(os.path.join(HERE, '..', 'kineti_mark.png'))
    SHOE_TOP = 0.105  # desk space: the shoe tops are cut here (below)
    baked = lowpoly.prepare(baked, mj, bone_key, MARK, foot_z + (SHOE_TOP - dj('footL').z) / s)

# --- 3. skin every vertex, then regroup the weights onto the desk-break bones
desk_names = [b.name for b in rig.data.bones]
for o in baked:
    me = o.data
    n = len(me.vertices)
    P = np.array([o.matrix_world @ v.co for v in me.vertices])
    Ph = np.c_[P, np.ones(n)]
    acc, wsum = np.zeros((n, 3)), np.zeros(n)
    W = {d: np.zeros(n) for d in desk_names}
    names = {g.index: g.name for g in o.vertex_groups}
    unknown = set()
    lowpoly_shoe = STYLE == 'lowpoly' and o.name.startswith('shoes')
    for v in me.vertices:
        for ge in v.groups:
            if ge.weight <= 0:
                continue
            gname = names.get(ge.group, '')
            if not gname.startswith('mixamorig:'):
                continue
            k = bone_key(gname)
            if lowpoly_shoe and k in ('LeftLeg', 'RightLeg'):  # the shoe follows the foot only: no crumpled upper
                k = k.replace('Leg', 'Foot')
            if k is None:
                unknown.add(gname)
                continue
            M = np.array(D.get(k, G))
            acc[v.index] += ge.weight * (M @ Ph[v.index])[:3]
            wsum[v.index] += ge.weight
            W[GROUP[k]][v.index] += ge.weight
            if k.endswith('Hand') and gname != 'mixamorig:' + k:  # a finger phalanx: kept for the grip keys
                FW.setdefault(gname[len('mixamorig:'):], np.zeros(n))[v.index] += ge.weight
    free = wsum == 0
    Gm = np.array(G)
    out = np.where(free[:, None], (Ph @ Gm.T)[:, :3], acc / np.maximum(wsum, 1e-9)[:, None])
    inv = np.array(rig.matrix_world.inverted())
    loc = (np.c_[out, np.ones(n)] @ inv.T)[:, :3]
    me.vertices.foreach_set('co', loc.astype(np.float32).ravel())
    for side, x in (('Left', 'L'), ('Right', 'R')):  # closed-hand offsets, rest space; joined later as shape keys
        dlt = finger_pose(out, FW, wsum, side, GRIP) @ inv[:3, :3].T
        a = me.attributes.new('grip_' + x, 'FLOAT_VECTOR', 'POINT')
        a.data.foreach_set('vector', dlt.astype(np.float32).ravel())
    FW.clear()
    o.matrix_world = rig.matrix_world.copy()
    o.vertex_groups.clear()
    for d in desk_names:
        g = o.vertex_groups.new(name=d)
        idx = np.nonzero(W[d] > 0)[0]
        for i in idx:
            g.add([int(i)], float(W[d][i]), 'REPLACE')
    if free.any():  # pin unweighted verts to the closest weighted vertex's dominant group
        from mathutils.kdtree import KDTree
        kd = KDTree(int((~free).sum()))
        wi = np.nonzero(~free)[0]
        for j, i in enumerate(wi):
            kd.insert(Vector(out[i]), j)
        kd.balance()
        Wm = np.stack([W[d] for d in desk_names], 1)
        for i in np.nonzero(free)[0]:
            _, j, _ = kd.find(Vector(out[i]))
            o.vertex_groups[desk_names[int(Wm[wi[j]].argmax())]].add([int(i)], 1.0, 'REPLACE')
    me.update()
    print('SKINNED', o.name, n, 'free', int(free.sum()), 'unknown', sorted(unknown)[:8])

# the shoes come with socks up the shin, which poke through the trousers when the knee bends: keep the shoe only
import bmesh  # noqa: E402

for o in baked:
    if o.name.startswith('shoes'):
        bm = bmesh.new()
        bm.from_mesh(o.data)
        cut = [v for v in bm.verts if (o.matrix_world @ v.co).z > (SHOE_TOP if STYLE == 'lowpoly' else 0.14)]
        bmesh.ops.delete(bm, geom=cut, context='VERTS')
        bm.to_mesh(o.data)
        bm.free()
        print('SHOES cut', len(cut))

if STYLE == 'lowpoly':
    mats_lp = lowpoly.materials(body, MARK)
    lowpoly.assign(baked, mats_lp)

# --- 4. one body object bound to the desk-break rig; drop the wooden mannequin and the MPFB originals
for o in list(dst.objects) + [old]:
    bpy.data.objects.remove(o, do_unlink=True)
for o in bpy.context.selected_objects:
    o.select_set(False)
for o in baked:
    o.select_set(True)
bpy.context.view_layer.objects.active = body
with bpy.context.temp_override(active_object=body, selected_editable_objects=baked, object=body):
    bpy.ops.object.join()
body.name = body.data.name = 'mannequin'
body.parent = rig
body.matrix_parent_inverse = rig.matrix_world.inverted()
am = body.modifiers.new('Armature', 'ARMATURE')
am.object = rig
if STYLE == 'lowpoly':  # the skin at the knees, elbows and wrists: no collapsed, pointed bends
    lowpoly.joint_smooth(body, mats_lp['body'][0])
if STYLE != 'lowpoly':  # lowpoly stays faceted
    sub = body.modifiers.new('Subdivision', 'SUBSURF')
    sub.levels, sub.render_levels = 0, 1  # render_mannequin indexes evaluated verts by the base mesh: viewport stays 0
    for p in body.data.polygons:
        p.use_smooth = True

# grip offsets -> shape keys grip_L / grip_R (render_mannequin.py turns them on for jobs that hold something)
me = body.data
nv = len(me.vertices)
base = np.zeros(nv * 3, np.float32)
me.vertices.foreach_get('co', base)
body.shape_key_add(name='Basis', from_mix=False)
for x in 'LR':
    a = me.attributes['grip_' + x]
    dlt = np.zeros(nv * 3, np.float32)
    a.data.foreach_get('vector', dlt)
    body.shape_key_add(name='grip_' + x, from_mix=False).data.foreach_set('co', base + dlt)
    print(f'GRIP {x} max offset {np.abs(dlt).reshape(-1, 3).max(0).round(3)}')
    me.attributes.remove(me.attributes['grip_' + x])


# --- 5. look: "flat" = matte solid colours like a fitness-app character (no skin pores, no denim wear), "real" = MPFB
def flat_materials():
    import os

    def lin(h):
        c = [int(h.lstrip('#')[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        return [((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92 for v in c] + [1]

    def tex_of(m, key=''):
        return next((n.image for n in m.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image
                     and key in n.image.name.lower() and 'normal' not in n.image.name.lower()
                     and '_ao' not in n.image.name.lower() and 'sss' not in n.image.name.lower()), None)

    def rebuild(m, color, rough, image=None, mix=0.0, alpha=False, sss=0.0):
        nt = m.node_tree
        nt.nodes.clear()
        out = nt.nodes.new('ShaderNodeOutputMaterial')
        p = nt.nodes.new('ShaderNodeBsdfPrincipled')
        nt.links.new(p.outputs[0], out.inputs['Surface'])
        p.inputs['Roughness'].default_value = rough
        p.inputs['Base Color'].default_value = lin(color)
        for nm in ('Specular IOR Level', 'Specular'):
            if nm in p.inputs:
                p.inputs[nm].default_value = 0.25
        if sss:
            p.inputs['Subsurface Weight'].default_value = sss
            p.inputs['Subsurface Radius'].default_value = (1.0, 0.45, 0.3)
            p.inputs['Subsurface Scale'].default_value = 0.012
        if image is not None:
            t = nt.nodes.new('ShaderNodeTexImage')
            t.image = image
            if mix >= 1:
                nt.links.new(t.outputs['Color'], p.inputs['Base Color'])
            elif mix > 0:
                mx = nt.nodes.new('ShaderNodeMix')
                mx.data_type = 'RGBA'
                mx.inputs['Factor'].default_value = mix
                mx.inputs['A'].default_value = lin(color)
                nt.links.new(t.outputs['Color'], mx.inputs['B'])
                nt.links.new(mx.outputs['Result'], p.inputs['Base Color'])
            if alpha:
                nt.links.new(t.outputs['Alpha'], p.inputs['Alpha'])
                if hasattr(m, 'surface_render_method'):
                    m.surface_render_method = 'DITHERED'
                else:
                    m.blend_method = 'HASHED'

    def flatten_suit(img):
        """The Kineti suit print is brand colour x cloth luminance (tool/mixamo/suit_texture.py): squeeze the
        luminance so shirt and trousers read as solid colours; the print and the trim stay as they are."""
        w, h = img.size
        px = np.array(img.pixels[:], np.float32).reshape(h, w, 4)
        rgb = px[..., :3] * 255
        S = np.array((8, 88, 162), np.float32)
        rel = rgb @ S / (S @ S)
        res = np.linalg.norm(rgb - rel[..., None] * S, axis=-1)
        m = (res < 0.06 * np.linalg.norm(rgb, axis=-1) + 3) & (rel > 0.35) & (rel < 1.7)
        rgb[m] = S * (1 + (rel[m, None] - 1) * 0.22)
        # trousers: everything outside suit_texture.py's shirt regions (image rows top-down there), one solid
        # colour, so seams, pockets and the denim wear disappear
        yy, xx = np.mgrid[0:h, 0:w]
        yy = h - 1 - yy
        sleeves = (xx > 1480) & (yy > 1180) & ~((xx < 1580) & (yy < 1330))
        logo = (xx >= 1440) & (xx < 1790) & (yy >= 300) & (yy < 650)
        rgb[~((yy < 880) | sleeves | logo)] = (44, 57, 85)
        px[..., :3] = np.clip(rgb / 255, 0, 1)
        new = bpy.data.images.new('kineti_suit_flat', w, h, alpha=True)
        new.pixels.foreach_set(px.ravel())
        new.filepath_raw = os.path.join(os.path.dirname(OUT), 'kineti_suit_flat.png')
        new.file_format = 'PNG'
        new.save()
        return new

    for m in body.data.materials:
        n = m.name.lower()
        if n.endswith('.body'):
            rebuild(m, '#D9A588', 0.55, sss=0.15)
        elif 'casualsuit' in n:
            rebuild(m, '#0858A2', 0.8, flatten_suit(tex_of(m, 'suit')), mix=1)
        elif 'shoes' in n:
            rebuild(m, '#EEF1F4', 0.6, tex_of(m), mix=0.35)
        elif 'ponytail' in n or 'hair' in n:
            rebuild(m, '#4A3426', 0.5, tex_of(m), mix=0.2, alpha=True)
        elif 'eyebrow' in n or 'eyelash' in n:
            rebuild(m, '#35261C', 0.6, tex_of(m), mix=0.0, alpha=True)
        print('MAT', m.name)


if STYLE == 'flat':
    flat_materials()

lo = min((body.matrix_world @ v.co).z for v in body.data.vertices)
hi = max((body.matrix_world @ v.co).z for v in body.data.vertices)
print(f'AVATAR verts {len(body.data.vertices)} z {lo:.3f}..{hi:.3f} mats {[m.name for m in body.data.materials]}')
bpy.ops.file.make_paths_absolute()
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print('DONE', OUT)
