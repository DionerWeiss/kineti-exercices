"""Style "vector" of the avatar: the flat-illustration fitness man of the LottieFiles workout set (orange tank
top with white trim, black shorts, dark trainers with an orange sole, short brown hair), shaded in two flat
tones like a vector drawing.

It stands in for lowpoly.py inside fit_avatar.py (same prepare / materials / assign / joint_smooth API), so
fit_avatar.py runs unchanged; vector_fit.py does the swap:

    blender -b <lib exercises.blend> --python vector_fit.py -- kineti_man_mixamo.blend <out.blend>

Differences from lowpoly.py:
- a tank top: no sleeves, deep round armholes and a round neck, both with a thin white trim;
- shorts to mid thigh, plain black;
- no decimation and smooth shading (a vector drawing has round silhouettes);
- toon materials: emission of a lit or a shadow colour, chosen by the normal against a light fixed to the
  camera (upper left, in front), so every view is lit like the drawings and the scene lights do not matter.
"""
import bpy
import numpy as np

import lowpoly
from lowpoly import cut, decimate, delete_faces, dominant, edge_free, joint_smooth, lin, seg_t, shell  # noqa: F401

# (lit, shadow), from the Lottie fills
SKIN = ('#F5B39E', '#E0937F')
SHIRT = ('#E96A2A', '#C9561F')
TRIM = ('#FFFFFF', '#E3E0DD')
SHORTS = ('#2A2B2A', '#161616')
HAIR = ('#4A2E1E', '#33200F')
SHOE = ('#2E2E2E', '#1C1C1C')
SOLE = ('#E26927', '#B9521C')
LIGHT = (-0.45, 0.6, 0.66)  # camera space (x right, y up, +z toward the camera)
THRESH = 0.05  # dot(normal, light) above this is lit

SHORTS_T = 0.55  # the shorts end at this fraction of the thigh


def regions(body, mj, bone_key):
    mw = body.matrix_world
    P = np.array([mw @ v.co for v in body.data.vertices])
    Nm = np.array([(mw.to_3x3() @ v.normal).normalized() for v in body.data.vertices])  # noqa: F841
    dom = dominant(body, bone_key)
    x, y, z = P.T
    hips, neck, head = mj('Hips'), mj('Neck'), mj('Head')
    hem_z, waist_z = hips.z - 0.06, hips.z + 0.06
    dx = np.abs(x - neck.x)
    # round neck: deeper in front
    depth = np.where(y < neck.y, 0.06, 0.012) * np.sqrt(np.clip(1 - (dx / 0.095) ** 2, 0, 1))
    collar = (neck.z + 0.004 - depth) - z
    collar = np.maximum(collar, dx - 0.095)
    # armholes: an ellipse (x-z) around each shoulder joint, deep to below the armpit
    hole = np.full(len(P), 1.0)
    for side in ('Left', 'Right'):
        a = mj(side + 'Arm')
        sx = abs(a.x - neck.x)
        cx, cz, rx, rz = sx + 0.03, a.z - 0.035, 0.095, 0.15
        e = np.sqrt(((dx - cx) / rx) ** 2 + ((z - cz) / rz) ** 2)
        same = np.sign(x - neck.x) == np.sign(a.x - neck.x)
        hole = np.where(same, np.minimum(hole, (e - 1) * 0.09), hole)
    trunk = np.isin(dom, ['Spine', 'Spine1', 'Spine2', 'LeftShoulder', 'RightShoulder', 'Neck', 'Hips',
                          'LeftUpLeg', 'RightUpLeg'])
    g_shirt = np.where(trunk, np.minimum(np.minimum(collar, hole), z - hem_z), -1.0)
    white_shirt = 0.006 - np.minimum(collar, hole)
    pelvis = np.isin(dom, ['Hips', 'Spine', 'LeftUpLeg', 'RightUpLeg'])
    g_shorts = np.where(pelvis, waist_z - z, -1.0)
    for side in ('Left', 'Right'):
        on = dom == side + 'UpLeg'
        tl = seg_t(P, mj(side + 'UpLeg'), mj(side + 'Leg'))
        g_shorts = np.where(on, np.minimum(waist_z - z, (SHORTS_T - tl) * (mj(side + 'Leg') - mj(side + 'UpLeg')).length),
                            g_shorts)
    g_shorts = np.minimum(g_shorts, hem_z + 0.04 - z)
    f = np.clip((y - head.y) / 0.1, -1.1, 1.0)
    hairline = head.z + 0.10 - 0.065 * f
    skull = np.isin(dom, ['Head', 'Neck']) | (z > head.z + 0.05)
    g_hair = np.where(skull, z - hairline, -1.0)
    feet = np.isin(dom, ['LeftFoot', 'RightFoot', 'LeftToeBase', 'RightToeBase']) & (z < 0.07)
    return dict(P=P, dom=dom, g_shirt=g_shirt, g_shorts=g_shorts, g_hair=g_hair, white_shirt=white_shirt,
                hairline=hairline, feet=feet, hem_z=hem_z, waist_z=waist_z, neck=neck)


def prepare(baked, mj, bone_key, mark_img, ankle_z):
    body = next(o for o in baked if o.name.startswith('body'))
    R = regions(body, mj, bone_key)
    P, z = R['P'], R['P'][:, 2]
    print('REGIONS', {k: int((R[k] > 0).sum()) for k in ('g_shirt', 'g_shorts', 'g_hair')})
    off_shirt = 0.009 + 0.012 * np.clip((R['hem_z'] + 0.25 - z) / 0.25, 0, 1)
    aspect = mark_img.size[0] / mark_img.size[1]
    mw_, cx, cz = 0.06, R['neck'].x + 0.075, R['neck'].z - 0.135
    uv = np.c_[(P[:, 0] - cx) / mw_ + 0.5, (P[:, 2] - cz) / (mw_ / aspect) + 0.5]
    uv[P[:, 1] > R['neck'].y - 0.03, 0] += 50.0
    sh = shell(body, R['g_shirt'], off_shirt, 'shirt_fit', R['white_shirt'], uv)
    off_shorts = 0.009 + 0.01 * np.clip((R['waist_z'] - z) / 0.15, 0, 1)
    st = shell(body, R['g_shorts'], off_shorts, 'shorts_fit', np.full(len(P), -1.0))
    hl = np.clip((z - R['hairline']) / 0.08, 0, 1)
    ha = shell(body, R['g_hair'], 0.003 + 0.02 * np.sqrt(hl), 'hair_fit')
    delete_faces(body, (R['g_shirt'] > 0.016) | (R['g_shorts'] > 0.03) | (R['g_hair'] > 0.02) | R['feet']
                 | (z < ankle_z - 0.012))
    # light decimation only (keeps round silhouettes); hands and face keep everything
    dom = dominant(body, bone_key)
    free = np.where(np.isin(dom, ['LeftHand', 'RightHand', 'Head']), 0.1, 1.0)
    decimate(body, 0.6, free)
    decimate(ha, 0.6, edge_free(ha, 1))
    return baked + [sh, st, ha]


def toon(name, base, alt=None, mark=None):
    """Emission of base[0] (lit) or base[1] (shadow) by the camera-space normal; with alt, alt's pair where the
    lp_white attribute is > 0; with mark, the image's alpha on UV 'mark' paints white."""
    m = bpy.data.materials.new('vec_' + name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    N = nt.nodes.new
    out = N('ShaderNodeOutputMaterial')
    em = N('ShaderNodeEmission')
    nt.links.new(em.outputs[0], out.inputs['Surface'])
    # the light in world space, built from the camera's axes: I (Incoming) points at the viewer, right =
    # (-I) x up_world, up = right x (-I); light = Lx right + Ly up + Lz I (no camera-space convention involved)
    geo = N('ShaderNodeNewGeometry')

    def vm(op, a, b=None, scale=None):
        n = N('ShaderNodeVectorMath')
        n.operation = op
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, tuple):
                n.inputs[i].default_value = v
            else:
                nt.links.new(v, n.inputs[i])
        if scale is not None:
            n.inputs['Scale'].default_value = scale
        return n.outputs['Vector'] if op != 'DOT_PRODUCT' else n.outputs['Value']

    inc = geo.outputs['Incoming']
    view = vm('SCALE', inc, scale=-1.0)
    right = vm('NORMALIZE', vm('CROSS_PRODUCT', view, (0.0, 0.0, 1.0)))
    up = vm('CROSS_PRODUCT', right, view)
    L = np.array(LIGHT) / np.linalg.norm(LIGHT)
    light = vm('ADD', vm('ADD', vm('SCALE', right, scale=float(L[0])), vm('SCALE', up, scale=float(L[1]))),
               vm('SCALE', inc, scale=float(L[2])))
    dot = vm('DOT_PRODUCT', geo.outputs['Normal'], light)
    dot = dot.node
    gt = N('ShaderNodeMath')
    gt.operation = 'GREATER_THAN'
    gt.inputs[1].default_value = THRESH
    nt.links.new(dot.outputs['Value'], gt.inputs[0])

    def pick(pair):
        mx = N('ShaderNodeMix')
        mx.data_type = 'RGBA'
        mx.inputs['A'].default_value = lin(pair[1])
        mx.inputs['B'].default_value = lin(pair[0])
        nt.links.new(gt.outputs[0], mx.inputs['Factor'])
        return mx.outputs['Result']

    col = pick(base)
    if alt is not None:
        at = N('ShaderNodeAttribute')
        at.attribute_type, at.attribute_name = 'GEOMETRY', 'lp_white'
        w = N('ShaderNodeMath')
        w.operation = 'GREATER_THAN'
        w.inputs[1].default_value = 0.0
        nt.links.new(at.outputs['Fac'], w.inputs[0])
        mx = N('ShaderNodeMix')
        mx.data_type = 'RGBA'
        nt.links.new(w.outputs[0], mx.inputs['Factor'])
        nt.links.new(col, mx.inputs['A'])
        nt.links.new(pick(alt), mx.inputs['B'])
        col = mx.outputs['Result']
    if mark is not None:
        uvn = N('ShaderNodeUVMap')
        uvn.uv_map = 'mark'
        tex = N('ShaderNodeTexImage')
        tex.image, tex.extension = mark, 'CLIP'
        nt.links.new(uvn.outputs['UV'], tex.inputs['Vector'])
        mx = N('ShaderNodeMix')
        mx.data_type = 'RGBA'
        nt.links.new(tex.outputs['Alpha'], mx.inputs['Factor'])
        nt.links.new(col, mx.inputs['A'])
        nt.links.new(pick(TRIM), mx.inputs['B'])
        col = mx.outputs['Result']
    nt.links.new(col, em.inputs['Color'])
    em.inputs['Strength'].default_value = 1.0
    return m


def materials(body, mark_img):
    return {'body': [toon('skin', SKIN)], 'shirt': [toon('shirt', SHIRT, TRIM, mark_img)],
            'shorts': [toon('shorts', SHORTS)], 'hair': [toon('hair', HAIR)], 'shoes': [toon('shoe', SHOE, SOLE)]}


def assign(objs, mats):
    lowpoly.assign(objs, mats)
    for o in objs:
        if any(o.name.startswith(k) for k in mats):
            for p in o.data.polygons:
                p.use_smooth = True
