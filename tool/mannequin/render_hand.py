"""Mannequin-style hand close-ups: wooden segments with ball joints, forearm resting on a table.
Poses come from export_hand.py (the Lottie hand kinematics), so contacts and timing are the same.

    blender -b --factory-startup --python render_hand.py -- <scene.json> <out_dir> <palette> [still fractions]

Without still fractions it renders every frame to <out_dir>/f_####.png.
"""
import json
import math
import sys

import bpy
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index('--') + 1:]
SRC, OUT, PALETTE = argv[0], argv[1], argv[2]
STILL = [float(x) for x in argv[3].split(',')] if len(argv) > 3 and argv[3] else None
W, H = 960, 540
PALETTES = {'azul': ('#2563EB', '#1E40AF'), 'areia': ('#D8C3A5', '#B89F80'), 'cinza': ('#C3C8D0', '#9AA3B0'),
            'ardosia': ('#8FA8C8', '#6B86A8'), 'salvia': ('#A9BBA8', '#869B85')}
data = json.load(open(SRC))
FR = data['frames']
WID = data['widths']


def lin(h):
    h = h.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c] + [1]


def mat(name, color, rough=0.6):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    p.inputs['Base Color'].default_value = lin(color)
    p.inputs['Roughness'].default_value = rough
    return m


def V(q):
    """Builder axes (x along the forearm, y up, z to the camera side) -> Blender (z up)."""
    return Vector((q[0], -q[2], q[1]))


for o in list(bpy.data.objects):
    bpy.data.objects.remove(o)
scene = bpy.context.scene
body_c, joint_c = PALETTES[PALETTE]
BODY, JOINT = mat('body', body_c, 0.65), mat('joint', joint_c, 0.6)
TOP, SIDE = mat('table', '#E2E8F0', 0.7), mat('floor', '#D5DCE6', 0.8)
BALLM = mat('ball', '#F2A65A', 0.45)


def sphere(r, m):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, segments=32, ring_count=16)
    o = bpy.context.object
    o.data.materials.append(m)
    bpy.ops.object.shade_smooth()
    return o


def rod(r, m):
    """Unit-length cylinder along +Z from the origin (scaled to each segment's length)."""
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=1, vertices=32, location=(0, 0, 0.5))
    o = bpy.context.object
    bpy.ops.object.transform_apply(location=True)
    o.data.materials.append(m)
    bpy.ops.object.shade_smooth()
    return o


# Segment chains: (key, width, joint spheres at the inner points, tip sphere)
CHAINS = [('forearm', WID['forearm'])] + [(k, WID[k]) for k in ('thumb', 'index', 'middle', 'ring', 'little')]
parts = []  # (object, kind, key, index)
for key, w in CHAINS:
    n = len(FR[0][key])
    for i in range(n - 1):
        parts.append((rod(w / 2, BODY), 'rod', key, i))
    for i in range(n):
        last = i == n - 1
        r = w / 2 * (1.0 if last else 1.04)
        parts.append((sphere(r, BODY if last else JOINT), 'ball', key, i))

# Palm: the outline plate of the first frame, solidified and bevelled, moved rigidly frame by frame.
P0 = [V(q) for q in FR[0]['palm']]


def palm_basis(pts):
    o = pts[0]
    a = (pts[2] - o).normalized()
    n = a.cross(pts[5] - o).normalized()
    return Matrix((a, n.cross(a), n)).transposed(), o


B0, O0 = palm_basis(P0)
me = bpy.data.meshes.new('palm')
me.from_pydata([B0.transposed() @ (p - O0) for p in P0], [], [list(range(len(P0)))])
palm = bpy.data.objects.new('palm', me)
scene.collection.objects.link(palm)
palm.data.materials.append(BODY)
sol = palm.modifiers.new('sol', 'SOLIDIFY')
sol.thickness, sol.offset = WID['palm'], 0
bev = palm.modifiers.new('bev', 'BEVEL')
bev.width, bev.segments = WID['palm'] * 0.45, 4
bpy.context.view_layer.objects.active = palm
bpy.ops.object.shade_smooth()

# Table: top at height 0, from far behind the forearm to the edge.
edge = data['edge']
bpy.ops.mesh.primitive_cube_add(location=((edge - 1.2) / 2, 0, -0.03))
tab = bpy.context.object
tab.scale = ((edge + 1.2) / 2, 0.45, 0.03)
tab.data.materials.append(TOP)
bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, -0.75))
bpy.context.object.data.materials.append(SIDE)


ball = None
if 'ball' in FR[0]:
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=48, ring_count=24)
    ball = bpy.context.object
    ball.data.materials.append(BALLM)
    bpy.ops.object.shade_smooth()


def pose(fr):
    f = FR[fr]
    if ball is not None:  # ellipsoid from its centre and semi-axis vectors
        a = [V(v) for v in f['ball']['axes']]
        M = Matrix((a[0], a[1], a[2])).transposed().to_4x4()
        M.translation = V(f['ball']['c'])
        ball.matrix_world = M
    for o, kind, key, i in parts:
        pts = f[key]
        if kind == 'ball':
            o.matrix_world = Matrix.Translation(V(pts[i]))
        else:
            a, b = V(pts[i]), V(pts[i + 1])
            q = Vector((0, 0, 1)).rotation_difference(b - a)
            o.matrix_world = Matrix.LocRotScale(a, q, Vector((1, 1, (b - a).length)))
    B, O = palm_basis([V(q) for q in f['palm']])
    palm.matrix_world = Matrix.Translation(O) @ B.to_4x4()


# Light and world like the body mannequin.
world = scene.world or bpy.data.worlds.new('w')
scene.world = world
world.use_nodes = True
bg = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
bg.inputs['Color'].default_value = lin('#EEF1F5')
bg.inputs['Strength'].default_value = 0.85
bpy.ops.object.light_add(type='SUN')
sun = bpy.context.object
sun.data.energy, sun.data.angle = 1.9, math.radians(25)
sun.rotation_euler = (math.radians(35), math.radians(10), math.radians(-30))
for engine in ('BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT'):
    try:
        scene.render.engine = engine
        break
    except TypeError:
        pass
scene.render.resolution_x, scene.render.resolution_y = W, H
scene.render.fps = data['fps']
scene.view_settings.view_transform = 'Standard'

# Camera on the side the Lottie camera looked from, fitted to every point of every frame.
right, up = V(data['cam_right']), V(data['cam_up'])
back = right.cross(up).normalized()
bpy.ops.object.camera_add()
cam = bpy.context.object
scene.camera = cam
cam.data.lens = 50
pts = [V(q) for f in FR[::2] for k in ('palm', 'thumb', 'index', 'middle', 'ring', 'little') for q in f[k]]
if 'ball' in FR[0]:
    pts += [V(FR[0]['ball']['c']) + V(v) * sg for v in FR[0]['ball']['axes'] for sg in (1, -1)]
pts.append(V(FR[0]['forearm'][1]) + Vector((-0.08, 0, 0)))  # a bit of the forearm
th = math.tan(cam.data.angle_x / 2)
tv = th * H / W
fill = 0.74
centre = sum(pts, Vector()) / len(pts)
for _ in range(4):
    rel = [p - centre for p in pts]
    dist = max(r.dot(back) + max(abs(r.dot(right)) / (th * fill), abs(r.dot(up)) / (tv * fill)) for r in rel)
    xs = [r.dot(right) / (dist - r.dot(back)) for r in rel]
    ys = [r.dot(up) / (dist - r.dot(back)) for r in rel]
    centre = centre + right * (max(xs) + min(xs)) / 2 * dist + up * (max(ys) + min(ys)) / 2 * dist
cam.location = centre + back * dist
cam.rotation_euler = (centre - cam.location).to_track_quat('-Z', 'Y').to_euler()
cam.data.clip_start = 0.01

frames = [round((len(FR) - 1) * q) for q in STILL] if STILL else range(len(FR))
for fr in frames:
    pose(fr)
    scene.render.filepath = f'{OUT}/f_{fr + 1:04d}.png'
    bpy.ops.render.render(write_still=True)
print('DONE', data['slug'], len(frames))
