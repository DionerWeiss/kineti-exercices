"""Automatic pose checks for the humanoid avatar (render_mannequin.py with AVATAR=1 and QA=<dir>).

Runs on the finished scene of one job (action after plant_hands, props, camera) and writes <dir>/<id>.json with the
measured values and a list of issues, each with a severity (1 = suspeito, 2 = quebrado):
- contato: a hand or foot standing still a little above its support (2-6 cm), or any part of the body inside the
  floor or a prop (signed distance to the floor plane and to the prop meshes; a point beside a prop's edge, whose
  offset to the nearest point is not along the face normal, is outside);
- skate: a planted hand or foot that slides. The same vertices that touch the support on two frames in a row are
  followed, so a foot rolling heel to toe does not count;
- ponta dos dedos: a hand resting on a support with its centre far from it (standing on the fingertips); seated
  or lying on a prop, only hands on the floor (a hand on the chair grips its edge);
- auto-interseção: a limb inside another part of the body (signed distance to that part's faces), measured
  against the rest pose so the shells that already touch at rest do not count;
- roupa: the skin hidden under the shirt or shorts coming out through it, or a hem moving away from the body;
- props: a balls off the body (or through it), a gripping hand away from the stick / band / handle it holds;
- cabelo: the hair mesh inside the head (beyond the rest pose), the floor or a prop;
- câmera: body vertices outside the frame (close-ups: only the part framed, waist up / knees down), or the camera
  looking at the figure's back.
Thresholds are in TH. The checks only read the scene: they never change the pose.
"""
import json
import os
from collections import defaultdict

import bpy
import numpy as np

import motion_qa
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector
from mathutils.bvhtree import BVHTree

TH = dict(
    float_lo=0.02, float_hi=0.06, float_run=10,      # still effector hovering above a support
    still=0.004,                                     # m/frame: an effector counts as still below this speed
    pen=0.02, pen_bad=0.04,                          # body inside the floor / a prop
    skate=0.03, skate_bad=0.08,                      # metres slid during one contact
    tip=0.6,                                         # supporting palm: cos of its angle to the support (flat = 1)
    self=0.015, self_bad=0.035, self_n=3,            # limb inside the body (beyond the rest pose)
    seam=0.006, flare=0.03,                          # skin out through the clothes, hem away from the body
    ball=0.025, ball_pen=0.04, held=0.035,           # props
    cam_out=0.002,                                   # fraction of the body's vertices outside the frame
    skate_v=0.005,                                   # m/frame: a planted contact sliding faster than this
    hair_head=0.008, hair_pen=0.01,                  # hair inside the head (beyond rest) / the floor or a prop
)
HELD_MATS = {'band', 'stick', 'towel', 'db', 'grip', 'walker'}
NOT_ENV = HELD_MATS | {'mat', 'tape', 'ladder', 'mark', 'logo', 'cuff'}  # (an ankle cuff sits around the leg)
BALL_MATS = {'swiss', 'ball', 'tennis'}
JUMPY = ('jump', 'hop', 'skip', 'jack', 'burpee', 'bound', 'tuck', 'jog', 'run', 'sprint', 'high-knee', 'butt-kick',
         'skater', 'pop-squat', 'star', 'lunge-switch', 'scissor')
EFFECTORS = {'pé E': {'footL'}, 'pé D': {'footR'}, 'mão E': {'handL'}, 'mão D': {'handR'}}
GROUP_PT = {'hips': 'quadril', 'spine': 'tronco', 'neck': 'cabeça', 'armL': 'braço E', 'elbowL': 'antebraço E',
            'handL': 'mão E', 'armR': 'braço D', 'elbowR': 'antebraço D', 'handR': 'mão D', 'legL': 'coxa E',
            'kneeL': 'perna E', 'footL': 'pé E', 'legR': 'coxa D', 'kneeR': 'perna D', 'footR': 'pé D'}
ARM_L, ARM_R = {'elbowL', 'handL'}, {'elbowR', 'handR'}
# parts that may press into a prop a little where they rest on it: hands and feet always; seated or lying on a
# prop (chair, bed, pillows, a roll under the knees), also the pelvis, thighs, back and calves
OK_HITS = ({'handL', 'handR', 'footL', 'footR'}, {'hips', 'legL', 'legR', 'spine', 'kneeL', 'kneeR', 'neck'})
# (label, part A (vertices), part B (faces), joint whose surroundings are skipped in A, radius)
PAIRS = [
    ('antebraço/mão E no tronco', ARM_L, {'spine', 'hips'}, None, 0),
    ('antebraço/mão D no tronco', ARM_R, {'spine', 'hips'}, None, 0),
    ('braço E no tronco', {'armL'}, {'spine', 'hips'}, 'armL', 0.13),
    ('braço D no tronco', {'armR'}, {'spine', 'hips'}, 'armR', 0.13),
    ('braço no outro braço', ARM_L, ARM_R, None, 0),
    ('perna na outra perna', {'kneeL', 'footL'}, {'kneeR', 'footR'}, None, 0),
    ('coxa na outra coxa', {'legL'}, {'legR'}, 'legL', 0.14),
    ('mão/antebraço na perna', ARM_L | ARM_R, {'legL', 'legR', 'kneeL', 'kneeR'}, None, 0),
    ('perna no tronco', {'kneeL', 'kneeR', 'footL', 'footR'}, {'spine', 'neck'}, None, 0),
    ('mão/antebraço na cabeça', ARM_L | ARM_R, {'neck'}, None, 0),
]

_M = None  # the body model, built once per Blender launch at rest (init)


def _mname(o):
    m = o.active_material
    return m.name.split('.')[0] if m else ''


def coords(obj):
    deps = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(deps)
    me = ev.to_mesh()
    co = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get('co', co)
    ev.to_mesh_clear()
    M = np.array(ev.matrix_world)
    return co.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]


def sdist(tree, P, maxd=0.2, faces=False):
    """Signed distance of each point to the tree's faces (outside > 0), inf beyond maxd; with faces, also the
    index of the nearest face (-1 when none)."""
    out = np.full(len(P), np.inf)
    fi = np.full(len(P), -1)
    for i, p in enumerate(P):
        v = Vector(p)
        loc, nor, k, d = tree.find_nearest(v, maxd)
        if loc is not None:
            # inside a (convex) prop the nearest point lies on a face, straight against its normal; beside an edge or
            # corner the offset is not along the normal (dot ~ 0, its sign is noise): outside
            out[i] = -d if (v - loc).dot(nor) < -0.7 * d else d
            fi[i] = k
    return (out, fi) if faces else out


class Model:
    def __init__(self, body, arm):
        me = body.data
        n = len(me.vertices)
        names = [g.name for g in body.vertex_groups]
        W = np.zeros((n, len(names)))
        for v in me.vertices:
            for g in v.groups:
                W[v.index, g.group] = g.weight
        for k, nm in enumerate(names):
            if nm in ('lp_joints', 'prop'):
                W[:, k] = -1
        self.grp = np.array(names)[W.argmax(1)]
        mats = [(s.material.name.split('.')[0] if s.material else '') for s in body.material_slots]
        self.polys = [tuple(p.vertices) for p in me.polygons]
        self.pmat = np.array([mats[p.material_index] for p in me.polygons])
        self.poly_grp = [max(set(self.grp[list(p)]), key=list(self.grp[list(p)]).count) for p in self.polys]
        vmat = np.array([''] * n, dtype=object)
        for p, m in zip(self.polys, self.pmat):
            for i in p:
                vmat[i] = m
        self.vmat = vmat
        # islands (shirt, shorts, shoes, arm skin...) and open edges
        parent = list(range(n))

        def find(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a
        ec = defaultdict(int)
        for p in self.polys:
            for a, b in zip(p, p[1:] + p[:1]):
                ec[(min(a, b), max(a, b))] += 1
                ra, rb = find(a), find(b)
                if ra != rb:
                    parent[ra] = rb
        self.island = np.array([find(i) for i in range(n)])
        self.bnd = np.zeros(n, bool)
        for (a, b), c in ec.items():
            if c == 1:
                self.bnd[a] = self.bnd[b] = True
        self.n = n
        self.cloth = np.isin(self.vmat, ['lp_shirt', 'lp_shorts'])
        self.skin = self.vmat == 'lp_skin'
        P = coords(body)  # rest pose
        self.rest = P
        jt = {nm: np.array(arm.matrix_world @ arm.pose.bones[nm].head) for nm in ('armL', 'armR', 'legL', 'legR')}
        self.pairs = []
        for label, A, B, joint, rad in PAIRS:
            a = np.isin(self.grp, list(A))
            if joint:
                a &= np.linalg.norm(P - jt[joint], axis=1) > rad
            bm = np.isin(self.grp, list(B))
            bp = [k for k, p in enumerate(self.polys) if all(bm[i] for i in p)]
            if not a.any() or not bp:
                continue
            ai = np.flatnonzero(a)
            base = sdist(self.tree(P, bp), P[ai], 0.1)
            self.pairs.append((label, ai, bp, np.minimum(base, 0)))  # parts already inside at rest keep that depth
        cp = [k for k, m in enumerate(self.pmat) if m in ('lp_shirt', 'lp_shorts')]
        self.cloth_polys = cp
        d = sdist(self.tree(P, cp), P, 0.05)
        # skin covered by the clothes at rest (not the hands, feet or head, which only pass near the shorts / collar)
        body_skin = self.skin & np.isin(self.grp, ['armL', 'armR', 'legL', 'legR', 'hips', 'spine'])
        self.hidden = np.flatnonzero(body_skin & (d < 0.002) & (d > -0.04))
        self.hidden_base = d[self.hidden]
        # cloth faces at an opening (collar, sleeve, waist, leg hems): skin may leave through those
        self.cloth_open = np.array([any(self.bnd[i] for i in self.polys[k]) for k in cp])
        self.hem = np.flatnonzero(self.cloth & self.bnd)
        self.hem_polys = {}
        hd = np.full(len(self.hem), np.inf)
        for isl in set(self.island[self.hem]):
            others = [k for k, p in enumerate(self.polys) if self.island[p[0]] != isl]
            sel = np.flatnonzero(self.island[self.hem] == isl)
            self.hem_polys[isl] = (sel, others)
            hd[sel] = np.abs(sdist(self.tree(P, others), P[self.hem[sel]], 0.15))
        self.hem_base = hd
        # the hair (its own skinned mesh): distance of its vertices to the head faces at rest
        self.hair = next((o for o in bpy.data.objects if o.type == 'MESH' and 'hair' in o.name.lower() and not o.hide_render
                          and any(m.type == 'ARMATURE' for m in o.modifiers)), None)
        if self.hair is not None:
            Hr = coords(self.hair)
            self.head_polys = [k for k, p in enumerate(self.polys) if all(self.grp[i] == 'neck' for i in p)]
            self.hair_sub = np.arange(0, len(Hr), max(1, len(Hr) // 400))
            self.hair_base = np.minimum(sdist(self.tree(P, self.head_polys), Hr[self.hair_sub], 0.1), 0)
            self.hair_base[~np.isfinite(self.hair_base)] = 0
        print('QAINIT hair', self.hair.name if self.hair is not None else None)
        print('QAINIT pairs', [(p[0], len(p[1])) for p in self.pairs], 'hidden', len(self.hidden), 'hem', len(self.hem))

    def tree(self, P, polys):
        return BVHTree.FromPolygons([tuple(p) for p in P], [self.polys[k] for k in polys])


def init(body, arm):
    global _M
    _M = Model(body, arm)


def env_objects(temp):
    """Supports: everything drawn except held things, floor marks and balls that are held or fly."""
    return [o for o in temp if o.type == 'MESH' and _mname(o) not in NOT_ENV and not o.get('qa_free') and not o.get('qa_held')]


def env_tree(objs):
    verts, polys = [], []
    deps = bpy.context.evaluated_depsgraph_get()
    for o in objs:
        ev = o.evaluated_get(deps)
        me = ev.to_mesh()
        M = ev.matrix_world
        b = len(verts)
        verts += [M @ v.co for v in me.vertices]
        polys += [tuple(b + i for i in p.vertices) for p in me.polygons]
        ev.to_mesh_clear()
    return BVHTree.FromPolygons(verts, polys) if polys else None


def runs(mask):
    out, s = [], None
    for i, m in enumerate(list(mask) + [False]):
        if m and s is None:
            s = i
        elif not m and s is not None:
            out.append((s, i))
            s = None
    return out


def check(name, view, props, scene, arm, body, figure, cam, temp, floor_z, f0, f1, palm, grips, out_dir, part='full', seated=False):
    M = _M
    frames = list(range(f0, f1 + 1))
    nF = len(frames)
    issues = []

    def issue(code, sev, msg, **kw):
        issues.append(dict(code=code, sev=sev, msg=msg, **kw))

    seated_like = seated or bool(props & {'chair', 'stool', 'swissseat', 'chairfit', 'bedfit', 'bed', 'pillow', 'chairbox', 'roll', 'kneepillow'})  # (seated: the render put a chair under the pelvis, e.g. a ball between the knees)
    envs = env_objects(temp)
    held = [o for o in temp if o.type == 'MESH' and _mname(o) in HELD_MATS]
    balls = [o for o in temp if o.type == 'MESH' and _mname(o) in BALL_MATS and not o.get('qa_free')]
    # props that move (support balls, walkergo...): their contacts do not count for skating
    scene.frame_set(f0)
    m0 = {o.name: o.matrix_world.copy() for o in envs}
    moving = set()
    for f in (f0 + (f1 - f0) // 3, f0 + 2 * (f1 - f0) // 3, f1):
        scene.frame_set(f)
        for o in envs:
            if (o.matrix_world.translation - m0[o.name].translation).length > 1e-4:
                moving.add(o.name)
    static_envs = [o for o in envs if o.name not in moving]
    scene.frame_set(f0)
    static_tree = env_tree(static_envs)
    eff_idx = {k: np.flatnonzero(np.isin(M.grp, list(g))) for k, g in EFFECTORS.items()}
    holding = {'mão E': grips(props, 'L'), 'mão D': grips(props, 'R')}

    gap = {k: np.zeros(nF) for k in EFFECTORS}         # lowest signed distance of the effector to any support
    cen = {k: np.zeros((nF, 3)) for k in EFFECTORS}
    tipness = {k: np.zeros(nF) for k in EFFECTORS}
    el_up = {k: np.zeros(nF) for k in EFFECTORS}
    touchf = {k: np.ones(nF) for k in EFFECTORS}  # supporting hands: palm normal . down
    on_floor = {k: np.zeros(nF, bool) for k in EFFECTORS}  # the nearest support is the floor (not a prop)
    contact = {k: [None] * nF for k in EFFECTORS}      # (vertex ids, positions) touching a static support
    pen = np.zeros(nF)
    hits = defaultdict(int)  # body part -> frames whose faces cross a prop's faces
    pen_grp = [''] * nF
    body_gap = np.zeros(nF)
    selfd = defaultdict(lambda: np.zeros(nF))
    seam, flare = np.zeros(nF), np.zeros(nF)
    seam_grp, flare_grp = [''] * nF, [''] * nF
    hair_in, hair_pen = np.zeros(nF), np.zeros(nF)
    ball_gap = {o.name: [] for o in balls}
    held_gap = {k: [] for k in ('mão E', 'mão D') if holding[k]}
    cam_out, back = [], []
    P_all = []
    motion_qa.init(M, arm, nF)
    for i, f in enumerate(frames):
        scene.frame_set(f)
        P = coords(body)
        heavy = i % 3 == 0 or i == nF - 1
        mov = [o for o in envs if o.name in moving]
        mtree = env_tree(mov) if mov else None
        motion_qa.collect(i, f, scene, arm, cam, P, M, [static_tree, mtree], heavy)
        # supports: floor plane, static props, moving props
        def sup(idx, maxd=0.2):
            g = P[idx, 2] - floor_z
            st = sdist(static_tree, P[idx], maxd) if static_tree else np.full(len(idx), np.inf)
            mv = sdist(mtree, P[idx], maxd) if mtree else np.full(len(idx), np.inf)
            return np.minimum(np.minimum(g, st), mv), np.minimum(g, st) <= mv
        for k, idx in eff_idx.items():
            g, is_static = sup(idx)
            gap[k][i] = g.min()
            c = P[idx].mean(0)
            cen[k][i] = c
            on_floor[k][i] = g.min() == (P[idx, 2] - floor_z).min()
            if on_floor[k][i]:
                tipness[k][i] = c[2] - floor_z - g.min()
            else:
                tc = sdist(static_tree, c[None], 1.0)[0] if static_tree else np.inf
                if not np.isfinite(tc) and mtree:
                    tc = sdist(mtree, c[None], 1.0)[0]
                tipness[k][i] = tc - g.min() if np.isfinite(tc) else 0
            if k.startswith('mão'):  # forearm standing on the hand (the hand bears weight): elbow over the contact
                el_up[k][i] = (arm.matrix_world @ arm.pose.bones['elbow' + k[-1].replace('E', 'L').replace('D', 'R')].head).z - P[idx, 2].min()
            if k.startswith('mão'):  # palm facing down (1) or standing on edge / fingertips (0)
                sd = 'L' if k == 'mão E' else 'R'
                Rh = (arm.matrix_world @ arm.pose.bones['hand' + sd].matrix).to_3x3() @ arm.data.bones['hand' + sd].matrix_local.to_3x3().inverted()
                touchf[k][i] = -(Rh @ Vector((-1 if sd == 'L' else 1, 0, 0))).z
            on = (g < 0.003) & is_static
            contact[k][i] = (idx[on], P[idx[on]]) if on.any() else None
            if os.environ.get('QA_DEBUG') in EFFECTORS[k] and i % 8 == 0:
                print('QADBG', f, k, 'gap', round(float(g.min()), 3), 'n_on', int(on.sum()),
                      'contact', np.round(P[idx[on]].mean(0), 3) if on.any() else '-', 'lowest', np.round(P[idx[np.argmin(g)]], 3))
        if heavy:
            g, _ = sup(np.arange(M.n), 0.25)
            body_gap[i] = g.min()
            if seated_like:  # sitting / lying on a prop: the parts resting on it may sink in a little
                g = np.where(np.isin(M.grp, list(OK_HITS[1])), np.maximum(g, 0), g)
            j = int(np.argmin(g))
            pen[i], pen_grp[i] = -g[j], M.grp[j]
            if os.environ.get('QA_PEN') and pen[i] > 0.03:
                loc, nor, _k, _d = static_tree.find_nearest(Vector(P[j]), 0.25) if static_tree else (None,) * 4
                print('QAPEN', f, M.grp[j], np.round(P[j], 3), 'floor', round(float(P[j, 2] - floor_z), 3),
                      'loc', np.round(loc, 3) if loc else '-', 'nor', np.round(nor, 2) if nor else '-')
            # faces crossing a prop's faces (a thin board through the head has no body vertex inside it)
            bt = BVHTree.FromPolygons([tuple(p) for p in P], M.polys)
            for tr in [t for t in (static_tree, mtree) if t is not None]:
                for a, _ in {(M.poly_grp[a], 0) for a, b in bt.overlap(tr)}:
                    hits[a] += 1
            for label, ai, bp, base in M.pairs:
                d = sdist(M.tree(P, bp), P[ai], 0.1) - base
                deep = np.sort(-d[np.isfinite(d)])[::-1]
                selfd[label][i] = deep[TH['self_n'] - 1] if len(deep) >= TH['self_n'] else 0
            if len(M.hidden):
                d, fi = sdist(M.tree(P, M.cloth_polys), P[M.hidden], 0.08, faces=True)
                d = d - M.hidden_base
                d[~np.isfinite(d) | (fi < 0)] = 0
                d[(fi >= 0) & M.cloth_open[np.maximum(fi, 0)]] = 0  # out through an opening, not through the cloth
                j = int(np.argmax(d))
                seam[i], seam_grp[i] = d[j], M.grp[M.hidden[j]]
            fl = np.zeros(len(M.hem))
            for isl, (sel, others) in M.hem_polys.items():
                d = np.abs(sdist(M.tree(P, others), P[M.hem[sel]], 0.2))
                d[~np.isfinite(d)] = 0.2
                fl[sel] = d - M.hem_base[sel]
            j = int(np.argmax(fl))
            flare[i], flare_grp[i] = fl[j], M.grp[M.hem[j]]
            if M.hair is not None:
                Hc = coords(M.hair)[M.hair_sub]
                d = sdist(M.tree(P, M.head_polys), Hc, 0.1) - M.hair_base
                d = d[np.isfinite(d)]
                hair_in[i] = float(-d.min()) if len(d) else 0
                g = Hc[:, 2] - floor_z
                if static_tree:
                    g = np.minimum(g, sdist(static_tree, Hc, 0.1))
                if mtree:
                    g = np.minimum(g, sdist(mtree, Hc, 0.1))
                hair_pen[i] = float(max(-g.min(), 0))
            for o in balls:
                bt = env_tree([o])
                lo_, hi_ = np.array(o.matrix_world.translation) - 0.6, np.array(o.matrix_world.translation) + 0.6
                near = np.flatnonzero(np.all((P > lo_) & (P < hi_), axis=1))
                d = sdist(bt, P[near], 0.3) if len(near) else np.array([np.inf])
                ball_gap[o.name].append(float(d.min()))
            for k in held_gap:
                s = 'L' if k == 'mão E' else 'R'
                ht = env_tree(held) if held else None
                held_gap[k].append(abs(float(sdist(ht, np.array([palm(s)]), 0.5)[0])) if ht else np.inf)
            # camera: every figure vertex inside the frame, and the chest facing it
            Q = np.vstack([P] + [coords(o)[::2] for o in figure if o is not body])
            if part == 'upper':  # close-ups frame only the waist up / the knees down (render_mannequin.motion_bounds)
                Q = Q[Q[:, 2] > (arm.matrix_world @ arm.pose.bones['spine'].head).z + 0.08]
            elif part == 'lower':
                Q = Q[Q[:, 2] < max((arm.matrix_world @ arm.pose.bones[b].head).z for b in ('kneeL', 'kneeR')) + 0.09]
            out = 0
            for q in Q[::2]:
                c = world_to_camera_view(scene, cam, Vector(q))
                if c.z <= 0 or not (0 <= c.x <= 1 and 0 <= c.y <= 1):
                    out += 1
            cam_out.append(out / len(Q[::2]))
            pb = arm.pose.bones['spine']
            R = (arm.matrix_world @ pb.matrix).to_3x3() @ arm.data.bones['spine'].matrix_local.to_3x3().inverted()
            chest = R @ Vector((0, -1, 0))
            to_cam = (cam.matrix_world.translation - arm.matrix_world @ pb.head).normalized()
            back.append((chest.z, chest.dot(to_cam)))
        P_all.append(P)
    scene.frame_set(f0)

    jumpy = any(w in name for w in JUMPY)
    res = dict(id=name, view=view, props=sorted(props), frames=nF)
    # 1. contacts: hovering, inside, on the fingertips, skating
    for k in EFFECTORS:
        sp = np.r_[0, np.linalg.norm(np.diff(cen[k], axis=0), axis=1)]
        still = sp < TH['still']
        hov = still & (gap[k] > TH['float_lo']) & (gap[k] < TH['float_hi'])
        worst = 0
        for a, b in runs(hov):
            if b - a >= TH['float_run']:
                worst = max(worst, float(np.median(gap[k][a:b])))
        if worst and not (k.startswith('mão') and holding[k]):
            issue('flutua', 1, f'{k} parado {worst * 100:.0f} cm acima do apoio', part=k, value=round(worst, 3))
        res[f'gap_{k}'] = round(float(gap[k].min()), 3)
        if k.startswith('mão') and not holding[k]:
            sup_ = still & (gap[k] < 0.015) & (el_up[k] > 0.12)
            if seated_like:  # a seated hand on the chair / bed grips its edge or rests on it: only the floor counts
                sup_ &= on_floor[k]
            tips = [float(np.median(touchf[k][a:b])) for a, b in runs(sup_) if b - a >= 8]
            res[f'palm_{k}'] = round(min(tips), 3) if tips else None
            if tips and min(tips) < TH['tip']:
                ang = np.degrees(np.arccos(np.clip(min(tips), -1, 1)))
                issue('ponta_dedos', 2, f'{k} apoiada sem a palma no apoio (palma a {ang:.0f}° do apoio)',
                      part=k, value=round(min(tips), 3))
        # skating: the same vertices touching on consecutive frames, horizontal slide
        # (the per-frame slides are summed as vectors, so jitter cancels; the drift is the furthest the contact
        # gets from where it was put down)
        slide = np.full((nF, 2), np.nan)
        for i in range(nF - 1):
            a, b = contact[k][i], contact[k][i + 1]
            if a is None or b is None:
                continue
            common, ia, ib = np.intersect1d(a[0], b[0], return_indices=True)
            if len(common) < 2:
                continue
            v_ = np.median(b[1][ib, :2] - a[1][ia, :2], axis=0)
            slide[i] = v_ if np.linalg.norm(v_) > 0.0015 else 0  # (a foot pivoting on its toe moves its contact verts a little)
            if os.environ.get('QA_DEBUG') in EFFECTORS[k] and np.linalg.norm(v_) > 0.0015:
                print('QADBG slide', frames[i], k, np.round(v_ * 1000, 1), 'n', len(common))
        worst, wr = 0.0, None
        for a, b in runs(~np.isnan(slide[:, 0])):
            if b - a >= 3:
                d = float(np.linalg.norm(np.cumsum(slide[a:b], axis=0), axis=1).max())
                if d > worst:
                    worst, wr = d, [frames[a], frames[b - 1] + 1]
        vmax, vf = 0.0, None
        for a, b in runs(~np.isnan(slide[:, 0])):
            if b - a >= 3:
                v_ = np.linalg.norm(slide[a:b], axis=1)
                v2 = np.minimum(v_[:-1], v_[1:]) if len(v_) > 1 else v_  # two frames in a row (one-frame jitter is not a slide)
                j = int(np.argmax(v2))
                if v2[j] > vmax:
                    vmax, vf = float(v2[j]), frames[a + j]
        res[f'skate_v_{k}'] = round(vmax * 100, 2)
        if vmax > TH['skate_v'] and worst <= TH['skate']:
            issue('skate', 1, f'{k} plantado desliza {vmax * 100:.1f} cm/quadro (quadro {vf})', part=k, value=round(vmax, 4), frame=vf)
        res[f'skate_{k}'] = round(worst, 3)
        if worst > TH['skate']:
            issue('skate', 2 if worst > TH['skate_bad'] else 1, f'{k} plantado desliza {worst * 100:.0f} cm (quadros {wr[0]}-{wr[1]})',
                  part=k, value=round(worst, 3), frame=wr)
    hv = np.flatnonzero(np.arange(nF) % 3 == 0)
    pmax = float(pen[hv].max())
    res['pen'] = round(pmax, 3)
    if pmax > TH['pen']:
        j = hv[int(np.argmax(pen[hv]))]
        issue('atravessa', 2 if pmax > TH['pen_bad'] else 1,
              f'{GROUP_PT.get(pen_grp[j], pen_grp[j])} atravessa o chão/apoio {pmax * 100:.0f} cm', value=round(pmax, 3),
              frame=frames[j])
    bad_hits = {g: n for g, n in hits.items() if g not in OK_HITS[0] and not (g in OK_HITS[1] and seated_like)}
    res['hits'] = dict(hits)
    if bad_hits:
        g = max(bad_hits, key=bad_hits.get)
        frac = bad_hits[g] / len(hv)
        issue('atravessa', 2 if g in ('neck', 'spine') or frac > 0.2 else 1,
              f"{', '.join(GROUP_PT.get(k, k) for k in sorted(bad_hits))} cruza um acessório ({frac * 100:.0f}% do vídeo)", value=round(frac, 2))
    air = float(np.mean(body_gap[hv] > TH['float_lo']))
    res['air'] = round(air, 2)
    if air > 0.15 and not jumpy:
        issue('no_ar', 1, f'corpo inteiro no ar em {air * 100:.0f}% do vídeo', value=round(air, 2))
    # 2. self-intersection
    for label, v in selfd.items():
        m = float(v[hv].max())
        res['self_' + label] = round(m, 3)
        lo_, hi_ = (TH['self'], TH['self_bad']) if not label.startswith(('braço E', 'braço D', 'coxa')) else (0.03, 0.09)
        if m > lo_:  # (an upper arm or thigh pressing 2-3 cm into the trunk / other thigh is hidden in the armpit / crotch)
            issue('auto', 2 if m > hi_ else 1, f'{label}: {m * 100:.0f} cm para dentro', part=label, value=round(m, 3),
                  frame=frames[hv[int(np.argmax(v[hv]))]])
    # 3. clothes
    m = float(seam[hv].max())
    res['seam'] = round(m, 3)
    if m > TH['seam']:
        j = hv[int(np.argmax(seam[hv]))]
        # (at the collar the trunk seam reads 2-4 cm on a neck tilt / shrug that looks right: quebrado over 4 cm there;
        # between the thighs, feet together or the hip flexed, 2-3 cm out of the shorts is hidden: over 3 cm)
        lim = {'spine': 0.04, 'legL': 0.03, 'legR': 0.03}.get(seam_grp[j], 0.02)
        issue('roupa', 1 if m < lim else 2, f'pele sai pela roupa ({GROUP_PT.get(seam_grp[j], seam_grp[j])}) {m * 100:.1f} cm',
              value=round(m, 3), frame=frames[j])
    m = float(flare[hv].max())
    res['flare'] = round(m, 3)
    if m > TH['flare']:
        j = hv[int(np.argmax(flare[hv]))]
        issue('roupa', 1, f'barra da roupa descola ({GROUP_PT.get(flare_grp[j], flare_grp[j])}) {m * 100:.0f} cm',
              value=round(m, 3), frame=frames[j])
    # 3b. hair
    if M.hair is not None:
        hi_, hp_ = float(hair_in[hv].max()), float(hair_pen[hv].max())
        res['hair_in'], res['hair_pen'] = round(hi_, 3), round(hp_, 3)
        if hi_ > TH['hair_head']:
            issue('cabelo', 2 if hi_ > 0.02 else 1, f'cabelo entra na cabeça {hi_ * 100:.1f} cm', value=round(hi_, 3),
                  frame=frames[hv[int(np.argmax(hair_in[hv]))]])
        if hp_ > TH['hair_pen']:
            issue('cabelo', 2 if hp_ > 0.025 else 1, f'cabelo atravessa o chão/apoio {hp_ * 100:.1f} cm', value=round(hp_, 3),
                  frame=frames[hv[int(np.argmax(hair_pen[hv]))]])
    # 4. props
    for o in balls:
        g = np.array(ball_gap[o.name])
        if not len(g):
            continue
        lo_, hi_ = float(g.min()), float(np.median(g))
        res['ball_' + o.name] = [round(lo_, 3), round(hi_, 3)]
        if hi_ > TH['ball']:
            issue('prop', 2 if hi_ > 0.06 else 1, f'bola sem contato com o corpo ({hi_ * 100:.0f} cm)', value=round(hi_, 3))
        if lo_ < -TH['ball_pen']:
            issue('prop', 1, f'bola entra no corpo {-lo_ * 100:.0f} cm', value=round(lo_, 3))
    if 'bandanchor1' in props and len(held_gap) == 2:  # one hand holds the band (render: the one that moves most):
        # the other is free, judge only the hand nearer to it
        far = max(held_gap, key=lambda k: float(np.median(held_gap[k])))
        held_gap.pop(far)
    for k in [k for k, g in held_gap.items() if not np.isfinite(np.min(g)) or np.min(g) > 0.12]:
        held_gap.pop(k)  # never within 12 cm of it: this hand is not meant to hold it (arms crossed / hands off a walker)
    for k, g in held_gap.items():
        g = np.array(g)
        bad = float(np.mean(g > TH['held']))
        res['held_' + k] = round(float(g.max()), 3)
        if bad > 0.1:
            issue('prop', 2 if bad > 0.3 else 1, f'{k} fora do acessório em {bad * 100:.0f}% do vídeo (até {g.max() * 100:.0f} cm)',
                  value=round(float(g.max()), 3))
    # 5. camera
    co = float(max(cam_out))
    res['cam_out'] = round(co, 4)
    if co > TH['cam_out']:
        issue('camera', 2 if co > 0.01 else 1, f'câmera corta o corpo ({co * 100:.1f}% dos vértices fora)', value=round(co, 4))
    if view not in ('back', 'back3q'):
        bk = [d for cz, d in back if cz > -0.5]  # face down on the floor the camera sees the back anyway
        if bk and np.mean(np.array(bk) < -0.3) > 0.5:
            issue('camera', 2, 'câmera mostra o boneco de costas', value=round(float(np.mean(bk)), 2))
    os.makedirs(out_dir, exist_ok=True)
    rx, ry = scene.render.resolution_x, scene.render.resolution_y
    motion_qa.save(os.path.join(out_dir, name + '.motion.npz'), frames, gap, cen, contact, floor_z,
                   dict(view=view, props='+'.join(sorted(props)), res=[rx, ry], seated=seated_like))
    res['issues'] = issues
    res['status'] = 'quebrado' if any(x['sev'] >= 2 for x in issues) else 'suspeito' if issues else 'ok'
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, name + '.json'), 'w', encoding='utf-8') as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    print('QA', name, res['status'], '; '.join(x['msg'] for x in issues))
    return res
