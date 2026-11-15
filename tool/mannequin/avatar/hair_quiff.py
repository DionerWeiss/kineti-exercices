"""A short quiff for the low-poly man (fit_avatar.py, style lowpoly) in place of his "beanie" hair shell: the
side profile of Dinh's "Burpee and Jump" Lottie character (a fringe swept up and forward over the forehead,
a sideburn in front of the ear, the back tapering into the nape), faceted like the rest of the figure.

    blender -b <avatar lib.blend> --python hair_quiff.py -- <out.blend>

Adds the object `SM_Char_Avatar_Hair` (render_mannequin.py, AVATAR=1, renders every skinned mesh of the lib):
a closed solid weighted to the `neck` bone. The old shell stays in the body (the scalp under it was cut away) and
takes the new colour; the new hair wraps it, so nothing of the body changes.
"""
import math
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

NAME = 'SM_Char_Avatar_Hair'
COLOR = '#4A3B32'
C = np.array([0.0, -0.025, 1.63])            # centre of the skull (front is -Y)
AX, AYF, AYB, AZ, EXP = 0.090, 0.110, 0.109, 0.099, 2.6
NSEG, NRING = 26, 9                          # facets around / from the crown to the hairline
INNER, RIM = 0.016, 0.005                    # thickness of the solid: on top, at the hairline
COVER = 0.004                                # least distance kept over the head and the old shell
FRINGE, LIFT = 0.022, 0.014                  # how far the fringe leans forward, how much the top rises to it
# hairline height by azimuth (0 = front, 180 = back): forehead, temple, sideburn tip, over/behind the ear, nape
LINE = [(0, 1.712), (25, 1.708), (42, 1.692), (56, 1.668), (66, 1.618), (74, 1.628), (82, 1.644),
        (98, 1.640), (112, 1.606), (130, 1.592), (150, 1.582), (180, 1.576)]


def smooth(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def lin(hexcolor):
    def f(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return [f(int(hexcolor[k:k + 2], 16) / 255) for k in (1, 3, 5)] + [1.0]


def unit(phi, el):
    return np.array([math.sin(phi) * math.cos(el), -math.cos(phi) * math.cos(el), math.sin(el)])


def build():
    man = bpy.data.objects['mannequin']
    rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    bm = bmesh.new()
    bm.from_mesh(man.data)
    bvh = BVHTree.FromBMesh(bm)
    bm.free()

    def skull(u):
        """Outermost radius of the head along u, or 0."""
        hit = bvh.ray_cast(Vector(C + u * 0.4), Vector(-u))
        return (hit[0] - Vector(C)).length if hit[0] is not None else 0.0

    # a smooth envelope of the head on an (azimuth, elevation) lattice: dilate, then blur, so the hair clears
    # the facets under it without copying them
    step = 3
    els = np.arange(-60, 91, step)
    phs = np.arange(0, 360, step)
    env = np.array([[skull(unit(math.radians(a), math.radians(e))) for e in els] for a in phs])
    env[env == 0] = 0.07
    env = np.minimum(env, 0.125)                                  # the shoulders, seen from below
    for _ in range(2):
        env = np.maximum.reduce([env, np.roll(env, 1, 0), np.roll(env, -1, 0),
                                 np.pad(env, ((0, 0), (1, 0)), 'edge')[:, :-1],
                                 np.pad(env, ((0, 0), (0, 1)), 'edge')[:, 1:]])
    for _ in range(6):
        up, dn = np.pad(env, ((0, 0), (1, 0)), 'edge')[:, :-1], np.pad(env, ((0, 0), (0, 1)), 'edge')[:, 1:]
        env = 0.4 * env + 0.15 * (np.roll(env, 1, 0) + np.roll(env, -1, 0) + up + dn)

    def envelope(phi, el):
        a = (math.degrees(phi) % 360) / step
        e = min(max((math.degrees(el) + 60) / step, 0), len(els) - 1.001)
        a0, e0 = int(a) % len(phs), int(e)
        fa, fe = a - int(a), e - e0
        a1 = (a0 + 1) % len(phs)
        return ((env[a0, e0] * (1 - fa) + env[a1, e0] * fa) * (1 - fe)
                + (env[a0, e0 + 1] * (1 - fa) + env[a1, e0 + 1] * fa) * fe)

    def surf(phi, el):
        u = unit(phi, el)
        ay = AYF if u[1] < 0 else AYB
        r = (abs(u[0] / AX) ** EXP + abs(u[1] / ay) ** EXP + abs(u[2] / AZ) ** EXP) ** (-1 / EXP)
        rs = envelope(phi, el)
        r = max(r, rs + COVER)
        # below the temples the hair hugs the head, so it tapers into the nape instead of flaring
        w = smooth((1.662 - (C[2] + r * u[2])) / 0.05)
        return C + u * ((1 - w) * r + w * (rs + COVER))

    px, pz = zip(*LINE)
    cols = []
    for j in range(NSEG):
        deg = 360.0 * j / NSEG
        phi = math.radians(deg)
        zb = float(np.interp(deg if deg <= 180 else 360 - deg, px, pz))
        lo, hi = math.radians(-60), math.radians(60)
        for _ in range(30):                                       # elevation where this column meets the hairline
            mid = (lo + hi) / 2
            if surf(phi, mid)[2] > zb:
                hi = mid
            else:
                lo = mid
        el_b = (lo + hi) / 2
        cols.append([surf(phi, math.radians(90) + (el_b - math.radians(90)) * (i / NRING) ** 0.85)
                     for i in range(1, NRING + 1)])
    P = np.array(cols)                                            # (NSEG, NRING, 3)
    ztop = surf(0.0, math.radians(90))[2]

    def quiff(p):
        """Sweep the front up and forward into a pointed fringe."""
        d = p - C
        deg = math.degrees(math.atan2(abs(d[0]), -d[1]))
        wf = float(smooth((80 - deg) / 55))                       # 1 in front, 0 past the temples
        t = (p[2] - LINE[0][1]) / (ztop - LINE[0][1])             # 0 at the forehead hairline, 1 on top
        front = float(smooth(-d[1] / 0.075))
        # the front wall leans out from the hairline to a tip near the top; the top is stretched flat up to it
        fwd = FRINGE * wf * float(smooth(t / 0.8)) ** 1.4 * front * (1 - 0.5 * (abs(d[0]) / AX) ** 2)
        up = LIFT * float(smooth((-d[1] + 0.03) / 0.11)) * float(smooth((t - 0.4) / 0.5))
        return p + np.array([0, -fwd, up])

    outer = np.array([quiff(np.array([C[0], C[1], ztop]))] + [quiff(P[j, i]) for j in range(NSEG) for i in range(NRING)])
    d = C - outer
    ring = np.array([0.0] + [(i + 1) / NRING for j in range(NSEG) for i in range(NRING)])
    thick = RIM + (INNER - RIM) * (1 - ring ** 3)                 # a thin edge at the hairline
    inner = outer + d / np.linalg.norm(d, axis=1)[:, None] * thick[:, None]
    n = len(outer)
    verts = [tuple(v) for v in outer] + [tuple(v) for v in inner]

    def idx(j, i):
        return 1 + (j % NSEG) * NRING + i

    faces = []
    for j in range(NSEG):
        faces.append((0, idx(j + 1, 0), idx(j, 0)))
        faces.append((n, n + idx(j, 0), n + idx(j + 1, 0)))
        for i in range(NRING - 1):
            faces.append((idx(j, i), idx(j + 1, i), idx(j + 1, i + 1), idx(j, i + 1)))
            faces.append((n + idx(j, i), n + idx(j, i + 1), n + idx(j + 1, i + 1), n + idx(j + 1, i)))
        e = NRING - 1                                             # rim between the two walls
        faces.append((idx(j, e), idx(j + 1, e), n + idx(j + 1, e), n + idx(j, e)))

    old = bpy.data.objects.get(NAME)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    me = bpy.data.meshes.new(NAME)
    me.from_pydata(verts, [], faces)
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.triangulate(bm, faces=bm.faces)                     # facets, like the body
    for f in bm.faces:
        f.smooth = False
    bm.to_mesh(me)
    bm.free()

    mat = next(m for m in man.data.materials if m.name.startswith('lp_hair'))  # also recolours the old shell
    p = next(nd for nd in mat.node_tree.nodes if nd.type == 'BSDF_PRINCIPLED')
    p.inputs['Base Color'].default_value = lin(COLOR)
    mat.diffuse_color = lin(COLOR)
    me.materials.append(mat)

    ob = bpy.data.objects.new(NAME, me)
    for coll in man.users_collection:
        coll.objects.link(ob)
    ob.parent = rig
    ob.vertex_groups.new(name='neck').add(range(len(me.vertices)), 1.0, 'REPLACE')
    ob.modifiers.new('Armature', 'ARMATURE').object = rig
    return ob


ob = build()
print('HAIR', ob.name, len(ob.data.vertices), 'verts', len(ob.data.polygons), 'faces')
if '--' in sys.argv and len(sys.argv) > sys.argv.index('--') + 1:
    out = sys.argv[sys.argv.index('--') + 1]
    bpy.ops.wm.save_as_mainfile(filepath=out)
    print('DONE', out)
