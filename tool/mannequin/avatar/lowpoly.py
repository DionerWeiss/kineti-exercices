"""Style "lowpoly" of fit_avatar.py: the faceted fitness-app man (blue V-neck shirt with white trim, black
shorts with a white side stripe, navy trainers with white soles, a short "helmet" of hair).

prepare() runs on the baked MPFB meshes before the skinning, in MPFB space (the man faces -Y):
- the shirt, the shorts and the hair are shells cut out of the full-resolution body and pushed out along the
  normals, so they carry the body's Mixamo weights and bend with it;
- the body faces deep under the shirt and the shorts are deleted (nothing can poke through), and so are the feet
  inside the shoes;
- everything is decimated (hands and face less) and shaded flat.
materials() runs on the joined avatar.
"""
import bmesh
import bpy
import numpy as np
from mathutils import Vector

SKIN, SHIRT, TRIM, SHORTS, HAIR, SHOE = '#E8AE8E', '#3E5FC0', '#F3F5F8', '#2B2B2D', '#6A6A70', '#3A465E'
SLEEVE_T = 0.42  # the sleeve ends at this fraction of the upper arm


def lin(h):
    c = [int(h.lstrip('#')[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92 for v in c] + [1]


def seg_t(P, a, b):
    a, b = np.array(a), np.array(b)
    d = b - a
    return np.clip((P - a) @ d / (d @ d), -1, 2)


def dominant(o, bone_key):
    names = {g.index: g.name for g in o.vertex_groups}
    dom = []
    for v in o.data.vertices:
        best, k = 0.0, None
        for ge in v.groups:
            gn = names.get(ge.group, '')
            if gn.startswith('mixamorig:') and ge.weight > best:
                best, k = ge.weight, bone_key(gn)
        dom.append(k)
    return np.array(dom, dtype=object)


def regions(body, mj, bone_key):
    """Signed fields (metres, > 0 inside) for the shirt, the shorts and the hair, so their edges can be cut
    exactly along the zero line; lp_white fields (> 0 is white) for the trims and the stripe."""
    mw = body.matrix_world
    P = np.array([mw @ v.co for v in body.data.vertices])
    Nm = np.array([(mw.to_3x3() @ v.normal).normalized() for v in body.data.vertices])
    dom = dominant(body, bone_key)
    x, y, z = P.T
    hips, neck, head = mj('Hips'), mj('Neck'), mj('Head')
    hem_z, waist_z = hips.z - 0.065, hips.z + 0.06
    # collar: round at the back, a V in front
    vdepth = np.where(y < neck.y, np.maximum(0.0, 0.085 - 1.6 * np.abs(x - neck.x)), 0.0)
    c = z - (neck.z + 0.004 - vdepth)
    collar = -np.where(vdepth > 0, c / np.sqrt(1 + 1.6 ** 2), c)
    collar = np.maximum(collar, np.abs(x - neck.x) - 0.072)  # only around the neck: the shoulder tops stay covered
    trunk = np.isin(dom, ['Spine', 'Spine1', 'Spine2', 'LeftShoulder', 'RightShoulder', 'Neck', 'Hips',
                          'LeftUpLeg', 'RightUpLeg'])
    g_shirt = np.where(trunk, np.minimum(collar, z - hem_z), -1.0)
    trim = np.where(trunk, collar, 1.0)  # distance to a trimmed edge (collar, sleeve ends; not the hem)
    pelvis = np.isin(dom, ['Hips', 'Spine', 'LeftUpLeg', 'RightUpLeg'])
    g_shorts = np.where(pelvis, waist_z - z, -1.0)
    for side in ('Left', 'Right'):
        on = dom == side + 'Arm'
        t = seg_t(P, mj(side + 'Arm'), mj(side + 'ForeArm'))
        sleeve = (SLEEVE_T - t) * (mj(side + 'ForeArm') - mj(side + 'Arm')).length
        g_shirt = np.where(on, sleeve, g_shirt)  # the collar never reaches the arm
        trim = np.where(on, sleeve, trim)
        on = dom == side + 'UpLeg'
        tl = seg_t(P, mj(side + 'UpLeg'), mj(side + 'Leg'))
        g_shorts = np.where(on, np.minimum(waist_z - z, (0.8 - tl) * (mj(side + 'Leg') - mj(side + 'UpLeg')).length), g_shorts)
    white_shirt = 0.013 - trim
    white_shorts = np.where(z < waist_z - 0.012, (np.sign(x) * Nm[:, 0] - 0.985) * 0.6, -0.05)
    # hair: the skull above a hairline that runs from the forehead down to the nape
    f = np.clip((y - head.y) / 0.1, -1.1, 1.0)
    hairline = head.z + 0.10 - 0.065 * f
    skull = np.isin(dom, ['Head', 'Neck']) | (z > head.z + 0.05)  # the crown may carry no Mixamo weight
    g_hair = np.where(skull, z - hairline, -1.0)
    feet = np.isin(dom, ['LeftFoot', 'RightFoot', 'LeftToeBase', 'RightToeBase']) & (z < 0.07)
    # the shorts stop a little above the shirt hem: in a hip fold (squat, lunge) their top would poke through
    g_shorts = np.minimum(g_shorts, hem_z + 0.04 - z)
    return dict(P=P, dom=dom, g_shirt=g_shirt, g_shorts=g_shorts, g_hair=g_hair, white_shirt=white_shirt,
                white_shorts=white_shorts, hairline=hairline, feet=feet, hem_z=hem_z, waist_z=waist_z, neck=neck)


def near_joints(o, mj):
    """1 around the knees, elbows, wrists and ankles (0 elsewhere), per vertex of o."""
    P = np.array([o.matrix_world @ v.co for v in o.data.vertices])
    joint = np.zeros(len(P))
    for side in ('Left', 'Right'):
        for j, r in (('Leg', 0.09), ('ForeArm', 0.07), ('Hand', 0.045), ('Foot', 0.06)):
            d = np.linalg.norm(P - np.array(mj(side + j)), axis=1)
            joint = np.maximum(joint, np.clip(1.5 - d / r, 0, 1))
    return joint


def cut(me, g):
    """Keeps the part of the mesh where g > 0, cut exactly along g = 0 (edges split at the crossing, faces split
    between the new vertices); weights, UVs and attributes are interpolated."""
    bm = bmesh.new()
    bm.from_mesh(me)
    lay = bm.verts.layers.float.new('lp_g')
    bm.verts.ensure_lookup_table()
    for v in bm.verts:
        gv = float(g[v.index])
        v[lay] = gv if abs(gv) > 1e-6 else 1e-6
    new = set()
    for e in list(bm.edges):
        a, b = e.verts
        ga, gb = a[lay], b[lay]
        if (ga > 0) != (gb > 0):
            _, nv = bmesh.utils.edge_split(e, a, ga / (ga - gb))
            nv[lay] = 0.0
            new.add(nv)
    for f in list(bm.faces):
        vs = [v for v in f.verts if v in new]
        if len(vs) == 2 and not any(e.other_vert(vs[0]) is vs[1] for e in vs[0].link_edges):
            try:
                bmesh.utils.face_split(f, vs[0], vs[1])
            except ValueError:
                pass
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v[lay] < 0], context='VERTS')
    bm.verts.layers.float.remove(lay)
    bm.to_mesh(me)
    bm.free()


def shell(body, g, offset, name, white=None, uv=None):
    """A copy of the body where g > 0 (cut along g = 0), pushed out along the normals by offset[v]."""
    me = body.data.copy()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    o.matrix_world = body.matrix_world
    if not o.vertex_groups:
        for vg in body.vertex_groups:
            o.vertex_groups.new(name=vg.name)
    sc = body.matrix_world.to_scale()[0]
    co = np.zeros(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get('co', co)
    nl = np.array([v.normal for v in me.vertices], np.float32)
    co = co.reshape(-1, 3) + nl * (np.broadcast_to(offset, (len(nl),)) / sc)[:, None]
    me.vertices.foreach_set('co', co.astype(np.float32).ravel())
    if uv is not None:
        layer = me.uv_layers.new(name='mark')
        loops = np.zeros(len(me.loops), np.int64)
        me.loops.foreach_get('vertex_index', loops)
        layer.data.foreach_set('uv', uv[loops].astype(np.float32).ravel())
    if white is not None:
        me.attributes.new('lp_white', 'FLOAT', 'POINT').data.foreach_set('value', white.astype(np.float32))
    cut(me, g)
    return o


def edge_free(o, near=1, inner=1.0, edge=0.08):
    """Decimation weights: the open edges (and `near` rings around them) keep their detail."""
    bm = bmesh.new()
    bm.from_mesh(o.data)
    ring = {v for v in bm.verts if v.is_boundary}
    for _ in range(near):
        ring |= {e.other_vert(v) for v in list(ring) for e in v.link_edges}
    free = np.full(len(bm.verts), inner)
    for v in ring:
        free[v.index] = edge
    bm.free()
    return free


def delete_faces(o, drop):
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if all(drop[v.index] for v in f.verts)], context='FACES_ONLY')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bm.to_mesh(o.data)
    bm.free()


def inflate(o, d):
    me = o.data
    sc = o.matrix_world.to_scale()[0]
    co = np.zeros(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get('co', co)
    nl = np.array([v.normal for v in me.vertices], np.float32)
    me.vertices.foreach_set('co', (co.reshape(-1, 3) + nl * (d / sc)).ravel())
    me.update()


def decimate(o, ratio, free=None):
    """Collapse decimation; `free` (per vertex, 0..1) protects the low-weight parts (hands, face, open edges)."""
    m = o.modifiers.new('lp_dec', 'DECIMATE')
    m.ratio = ratio
    if free is not None:
        g = o.vertex_groups.new(name='lp_free')
        for i, w in enumerate(free):
            g.add([i], float(w), 'REPLACE')
        m.vertex_group, m.vertex_group_factor = g.name, 10.0
    dg = bpy.context.evaluated_depsgraph_get()
    new = bpy.data.meshes.new_from_object(o.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    o.modifiers.remove(m)
    old = o.data
    o.data = new
    bpy.data.meshes.remove(old)
    if free is not None:
        o.vertex_groups.remove(o.vertex_groups['lp_free'])
    print('DECIMATED', o.name, len(new.vertices))


def prepare(baked, mj, bone_key, mark_img, ankle_z):
    """ankle_z: the height (MPFB space) of the shoe tops after fit_avatar.py cuts them; the skin inside goes."""
    body = next(o for o in baked if o.name.startswith('body'))
    R = regions(body, mj, bone_key)
    P, z = R['P'], R['P'][:, 2]
    print('REGIONS', {k: int((R[k] > 0).sum()) for k in ('g_shirt', 'g_shorts', 'g_hair')})
    # shirt: looser toward the hem; the Kineti mark on the left chest (UV 'mark', front only)
    off_shirt = 0.011 + 0.015 * np.clip((R['hem_z'] + 0.25 - z) / 0.25, 0, 1)
    aspect = mark_img.size[0] / mark_img.size[1]
    mw_, cx, cz = 0.026, R['neck'].x + 0.07, R['neck'].z - 0.11
    uv = np.c_[(P[:, 0] - cx) / mw_ + 0.5, (P[:, 2] - cz) / (mw_ / aspect) + 0.5]
    uv[P[:, 1] > R['neck'].y - 0.03, 0] += 50.0  # the back: far off the image (a constant would streak across faces)
    sh = shell(body, R['g_shirt'], off_shirt, 'shirt_fit', R['white_shirt'], uv)
    # shorts: snug at the waist, loose on the legs
    off_shorts = 0.009 + 0.008 * np.clip((R['waist_z'] - z) / 0.15, 0, 1)
    st = shell(body, R['g_shorts'], off_shorts, 'shorts_fit', R['white_shorts'])
    # hair: thicker on top
    hl = np.clip((z - R['hairline']) / 0.08, 0, 1)
    ha = shell(body, R['g_hair'], 0.003 + 0.02 * np.sqrt(hl), 'hair_fit')
    # the body under the clothes (and inside the shoes) goes: nothing can poke through
    # (the skin inside the shoes goes up to just under the shoe top, or it shows when the ankle bends)
    delete_faces(body, (R['g_shirt'] > 0.016) | (R['g_shorts'] > 0.03) | (R['g_hair'] > 0.02) | R['feet']
                 | (z < ankle_z - 0.006))
    # body: hands and face keep their detail, and the knees, elbows and wrists rings to bend on
    dom = dominant(body, bone_key)
    free = np.where(np.isin(dom, ['LeftHand', 'RightHand']), 0.15, np.where(dom == 'Head', 0.45, 1.0))
    free = np.minimum(free, 1 - 0.7 * near_joints(body, mj))
    decimate(body, 0.16, free)
    decimate(sh, 0.24, edge_free(sh, 2))
    decimate(st, 0.22, edge_free(st, 2))
    decimate(ha, 0.3, edge_free(ha, 1))
    for o in baked:
        if o.name.startswith('shoes'):
            decimate(o, 0.35)
            inflate(o, 0.004)  # room for the ankle: a bent ankle's skin stays inside the shoe
    return baked + [sh, st, ha]


def materials(body, mark_img):
    def flat(name, color, rough=0.85, white=False):
        """Matte solid colour; with white=True, white where the lp_white attribute is > 0 (trim, stripe, sole)."""
        m = bpy.data.materials.new('lp_' + name)
        m.use_nodes = True
        nt = m.node_tree
        p = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
        p.inputs['Base Color'].default_value = lin(color)
        p.inputs['Roughness'].default_value = rough
        for nm in ('Specular IOR Level', 'Specular'):
            if nm in p.inputs:
                p.inputs[nm].default_value = 0.2
        out = None
        if white:
            at = nt.nodes.new('ShaderNodeAttribute')
            at.attribute_type, at.attribute_name = 'GEOMETRY', 'lp_white'
            gt = nt.nodes.new('ShaderNodeMath')
            gt.operation = 'GREATER_THAN'
            gt.inputs[1].default_value = 0.0
            nt.links.new(at.outputs['Fac'], gt.inputs[0])
            mx = nt.nodes.new('ShaderNodeMix')
            mx.data_type = 'RGBA'
            mx.inputs['A'].default_value = lin(color)
            mx.inputs['B'].default_value = lin(TRIM)
            nt.links.new(gt.outputs[0], mx.inputs['Factor'])
            nt.links.new(mx.outputs['Result'], p.inputs['Base Color'])
            out = mx.outputs['Result']
        return m, nt, p, out

    skin = flat('skin', SKIN, 0.7)[0]
    shirt, nt, p, col = flat('shirt', SHIRT, white=True)
    uvn = nt.nodes.new('ShaderNodeUVMap')
    uvn.uv_map = 'mark'
    tex = nt.nodes.new('ShaderNodeTexImage')
    tex.image, tex.extension = mark_img, 'CLIP'
    nt.links.new(uvn.outputs['UV'], tex.inputs['Vector'])
    mix = nt.nodes.new('ShaderNodeMix')
    mix.data_type = 'RGBA'
    mix.inputs['B'].default_value = lin('#FFFFFF')
    nt.links.new(col, mix.inputs['A'])
    nt.links.new(tex.outputs['Alpha'], mix.inputs['Factor'])
    nt.links.new(mix.outputs['Result'], p.inputs['Base Color'])
    shorts = flat('shorts', SHORTS, white=True)[0]
    hair = flat('hair', HAIR, 0.9)[0]
    shoe = flat('shoe', SHOE, 0.7, white=True)[0]
    return {'body': [skin], 'shirt': [shirt], 'shorts': [shorts], 'hair': [hair], 'shoes': [shoe]}


def assign(objs, mats):
    """One flat material per part (before the join); the shoes get their white sole as lp_white (desk space)."""
    for o in objs:
        key = next((k for k in mats if o.name.startswith(k)), None)
        if key is None:
            continue
        me = o.data
        if key == 'shoes':
            z = np.array([(o.matrix_world @ v.co).z for v in me.vertices])
            me.attributes.new('lp_white', 'FLOAT', 'POINT').data.foreach_set('value', (0.024 - z).astype(np.float32))
        me.materials.clear()
        for m in mats[key]:
            me.materials.append(m)
        me.polygons.foreach_set('material_index', [0] * len(me.polygons))
        for p in me.polygons:
            p.use_smooth = False


JOINTS = [('leg', 'knee'), ('arm', 'elbow'), ('elbow', 'hand')]


def joint_smooth(body, skin_mat):
    """Corrective Smooth (after the Armature) on the skin where two of the bones of a knee, elbow or wrist share
    the weights: linear blend skinning pinches those bends to a point. Only the skin: the clothes are separate
    shells, and smoothing them on their own would slide them off the body."""
    n = len(body.data.vertices)
    gi = {g.name: g.index for g in body.vertex_groups}
    W = {k: np.zeros(n) for k in gi}
    inv = {v: k for k, v in gi.items()}
    for v in body.data.vertices:
        for g in v.groups:
            W[inv[g.group]][v.index] = g.weight
    mi = list(body.data.materials).index(skin_mat)
    skin = np.zeros(n, bool)
    for p in body.data.polygons:
        if p.material_index == mi:
            skin[list(p.vertices)] = True
    blend = np.zeros(n)
    for a, b in JOINTS:
        for x in 'LR':
            wa, wb = W[a + x], W[b + x]
            blend = np.maximum(blend, np.clip(4 * np.minimum(wa, wb) / np.maximum(wa + wb, 1e-9), 0, 1) * ((wa + wb) > 0.8))
    E = np.zeros(len(body.data.edges) * 2, np.int64)
    body.data.edges.foreach_get('vertices', E)
    E = E.reshape(-1, 2)
    for _ in range(2):  # spread a couple of rings, so the smoothing fades out
        acc, cnt = np.zeros(n), np.zeros(n)
        np.add.at(acc, E[:, 0], blend[E[:, 1]])
        np.add.at(acc, E[:, 1], blend[E[:, 0]])
        np.add.at(cnt, E[:, 0], 1)
        np.add.at(cnt, E[:, 1], 1)
        blend = np.maximum(blend, 0.7 * acc / np.maximum(cnt, 1))
    blend *= skin
    g = body.vertex_groups.new(name='lp_joints')
    for i in np.nonzero(blend > 0.02)[0]:
        g.add([int(i)], float(blend[i]), 'REPLACE')
    cs = body.modifiers.new('JointSmooth', 'CORRECTIVE_SMOOTH')
    cs.vertex_group = g.name
    cs.factor, cs.iterations = 0.5, 10
    cs.smooth_type, cs.rest_source, cs.use_only_smooth = 'LENGTH_WEIGHTED', 'ORCO', False
    print('JOINTSMOOTH', int((blend > 0.02).sum()), 'of', n)
