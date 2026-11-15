"""Layer-2 raw motion data for the humanoid avatar (render_mannequin.py with AVATAR=1 and QA=<dir>).

qa_pose.check() feeds each frame of the finished scene here (collect) and saves it at the end (save):
<dir>/<id>.motion.npz with, per frame,
- q:      rotation of every bone relative to its parent, in the rest-pose world axes (x = the figure's left,
          y = backwards, z = up), as quaternions (w, x, y, z); hips relative to the world;
- heads:  world position of each bone head, and pts/proj: tracked points (bone heads, toe tips, fingertips, head
          top) in world metres and in normalized camera coordinates (x, y in 0..1, depth);
- com:    centre of mass from Winter's segment table; bos: how far its floor projection lies outside the hull of
          the soles of the feet that rest on a support (negative inside), nan when no foot rests;
- gap / cen: each hand and foot's lowest distance to a support and its centre (from qa_pose);
- heel:   per foot, where its contact sits along the foot (heel < 0 < toes), nan without contact;
- vis:    every 3rd frame, the share of each body part's outer vertices the camera sees (ray cast against the
          body and the props), with vis_frames the frames sampled.
motion_review.py turns it into metrics and verdicts (no Blender needed, so thresholds can be tuned).
"""
import os

import bpy
import numpy as np
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector
from mathutils.bvhtree import BVHTree

BONES = ['hips', 'spine', 'neck', 'armL', 'elbowL', 'handL', 'armR', 'elbowR', 'handR',
         'legL', 'kneeL', 'footL', 'legR', 'kneeR', 'footR']
GROUPS = BONES
# Winter (2009) segment masses and the COM position along each segment (from the proximal joint)
SEG = [  # (mass, proximal point, distal point, fraction)
    (0.497, 'hips', 'neck', 0.5),
    (0.081, 'neck', 'headtop', 0.45),
    (0.028, 'armL', 'elbowL', 0.436), (0.016, 'elbowL', 'handL', 0.43), (0.006, 'handL', 'fingL', 0.5),
    (0.028, 'armR', 'elbowR', 0.436), (0.016, 'elbowR', 'handR', 0.43), (0.006, 'handR', 'fingR', 0.5),
    (0.100, 'legL', 'kneeL', 0.433), (0.0465, 'kneeL', 'footL', 0.433), (0.0145, 'footL', 'toeL', 0.45),
    (0.100, 'legR', 'kneeR', 0.433), (0.0465, 'kneeR', 'footR', 0.433), (0.0145, 'footR', 'toeR', 0.45),
]
TRACK = BONES + ['toeL', 'toeR', 'fingL', 'fingR', 'headtop']

_S = None


def _rot(arm, name):
    pb = arm.pose.bones[name]
    return (arm.matrix_world @ pb.matrix).to_3x3() @ arm.data.bones[name].matrix_local.to_3x3().inverted()


def hull(pts):
    """2D convex hull (monotone chain), counter-clockwise."""
    pts = sorted(set(map(tuple, np.round(pts, 4))))
    if len(pts) <= 2:
        return np.array(pts)

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, hi = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(hi) >= 2 and cross(hi[-2], hi[-1], p) <= 0:
            hi.pop()
        hi.append(p)
    return np.array(lo[:-1] + hi[:-1])


def outside(h, p):
    """Distance of point p outside the convex polygon h (negative: inside, by the distance to the nearest edge)."""
    def seg_d(a, b):
        ab, ap = b - a, p - a
        t = np.clip(ap @ ab / max(ab @ ab, 1e-12), 0, 1)
        return np.linalg.norm(ap - t * ab)
    if len(h) == 0:
        return np.nan
    if len(h) == 1:
        return float(np.linalg.norm(p - h[0]))
    if len(h) == 2:
        return seg_d(h[0], h[1])
    ins, d = True, np.inf
    for i in range(len(h)):
        a, b = h[i], h[(i + 1) % len(h)]
        if (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]) < 0:
            ins = False
        d = min(d, seg_d(a, b))
    return -d if ins else d


class State:
    def __init__(self, M, arm, nF):
        rest = M.rest
        self.track_v = {}
        for s in 'LR':
            fv = np.flatnonzero(M.grp == 'foot' + s)
            self.track_v['toe' + s] = int(fv[np.argmin(rest[fv, 1])])  # most forward (-y)
            hv = np.flatnonzero(M.grp == 'hand' + s)
            self.track_v['fing' + s] = int(hv[np.argmin(rest[hv, 2])])  # lowest with the arm hanging
        nv = np.flatnonzero(M.grp == 'neck')
        self.track_v['headtop'] = int(nv[np.argmax(rest[nv, 2])])
        # outer vertices of each part (not the skin hidden under the clothes), 36 per part, fixed seed
        rng = np.random.default_rng(7)
        outer = np.ones(M.n, bool)
        outer[M.hidden] = False
        self.vis_v = {}
        for g in GROUPS:
            v = np.flatnonzero((M.grp == g) & outer)
            self.vis_v[g] = np.sort(rng.choice(v, min(36, len(v)), replace=False)) if len(v) else v
        self.foot_v = {}
        for s in 'LR':   # the sole: the foot's lowest 1.5 cm in the rest pose (the low-poly sole is not flat)
            fv = np.flatnonzero(M.grp == 'foot' + s)
            self.foot_v[s] = fv[rest[fv, 2] < rest[fv, 2].min() + 0.015]
        self.q = np.zeros((nF, len(BONES), 4))
        self.heads = np.zeros((nF, len(BONES), 3))
        self.pts = np.zeros((nF, len(TRACK), 3))
        self.proj = np.zeros((nF, len(TRACK), 3))
        self.com = np.zeros((nF, 3))
        self.cam = np.zeros((nF, 3))
        self.vis, self.vis_frames = [], []
        self.fwd = np.zeros((nF, 2, 3))
        self.sole = [[None, None] for _ in range(nF)]


def init(M, arm, nF):
    global _S
    _S = State(M, arm, nF)


def collect(i, f, scene, arm, cam, P, M, occluders, heavy):
    """Frame i (scene frame f): bone rotations and heads, tracked points, COM; on heavy frames, visibility.
    occluders: BVH trees of the props drawn this frame (static and moving)."""
    S = _S
    R = {b: _rot(arm, b) for b in BONES}
    for k, b in enumerate(BONES):
        pb = arm.pose.bones[b]
        par = pb.parent.name if pb.parent else None
        Rr = R[b] if par is None else R[par].transposed() @ R[b]
        S.q[i, k] = tuple(Rr.to_quaternion())
        S.heads[i, k] = tuple(arm.matrix_world @ pb.head)
    pos = {b: S.heads[i, k] for k, b in enumerate(BONES)}
    for nm, vi in S.track_v.items():
        pos[nm] = P[vi]
    for k, nm in enumerate(TRACK):
        S.pts[i, k] = pos[nm]
        c = world_to_camera_view(scene, cam, Vector(pos[nm]))
        S.proj[i, k] = (c.x, c.y, c.z)
    m = sum(s[0] for s in SEG)
    S.com[i] = sum(w * (pos[a] + (pos[b] - pos[a]) * t) for w, a, b, t in SEG) / m
    S.cam[i] = tuple(cam.matrix_world.translation)
    for j, s in enumerate('LR'):  # the foot's forward direction (rest -y) for the heel/toe split of its contact
        S.fwd[i, j] = tuple(R['foot' + s] @ Vector((0, -1, 0)))
        F = P[S.foot_v[s]]
        # the part of the sole that rests: within 3 cm of its lowest point (a foot pitched 3 deg lifts the heel 1.5 cm
        # and still stands on it; on tiptoe the heel is well above and drops out)
        S.sole[i][j] = F[F[:, 2] < F[:, 2].min() + 0.03, :2]
    if heavy:
        tree = BVHTree.FromPolygons([tuple(p) for p in P], M.polys)
        co = cam.matrix_world.translation
        row = []
        for g in GROUPS:
            vv = S.vis_v[g]
            seen = 0
            for v in vv:
                p = Vector(P[v])
                c = world_to_camera_view(scene, cam, p)
                if c.z <= 0 or not (0 <= c.x <= 1 and 0 <= c.y <= 1):
                    continue
                d = p - co
                L = d.length
                d.normalize()
                ok = True
                for t in [tree] + [o for o in occluders if o is not None]:
                    hit = t.ray_cast(co, d, L - 0.012)
                    if hit[0] is not None:
                        ok = False
                        break
                seen += ok
            row.append(seen / max(len(vv), 1))
        S.vis.append(row)
        S.vis_frames.append(i)


def save(path, frames, gap, cen, contact, floor_z, meta):
    S = _S
    nF = len(frames)
    eff = ['pé E', 'pé D', 'mão E', 'mão D']
    G = np.array([gap[k] for k in eff]).T
    C = np.stack([cen[k] for k in eff], 1)
    # base of support: hull of the foot contacts (only when no hand bears weight)
    bos = np.full(nF, np.nan)
    bos_box = np.full((nF, 4), np.nan)   # the base's bounding box (x min, x max, y min, y max), to check it
    heel = np.full((nF, 2), np.nan)
    for i in range(nF):
        pts = [S.sole[i][j] for j, k in enumerate(('pé E', 'pé D')) if gap[k][i] < 0.01]
        for j, k in enumerate(('pé E', 'pé D')):
            c = contact[k][i]
            if c is not None:
                fw = S.fwd[i, j, :2]
                n = np.linalg.norm(fw)
                if n > 0.2:
                    # the contact centre against the foot centre, along the foot: heel < 0 < toes (metres)
                    heel[i, j] = float((c[1][:, :2].mean(0) - cen[k][i][:2]) @ (fw / n))
        if pts:
            P2 = np.vstack(pts)
            bos[i] = outside(hull(P2), S.com[i, :2])
            bos_box[i] = (*P2.min(0)[:1], *P2.max(0)[:1], P2[:, 1].min(), P2[:, 1].max())

    np.savez_compressed(path, frames=np.array(frames), bones=np.array(BONES), track=np.array(TRACK),
                        q=S.q, heads=S.heads, pts=S.pts, proj=S.proj, com=S.com, cam=S.cam, bos=bos, bos_box=bos_box, heel=heel,
                        gap=G, cen=C, vis=np.array(S.vis), vis_frames=np.array(S.vis_frames),
                        groups=np.array(GROUPS), floor_z=floor_z, **{k: np.array(v) for k, v in meta.items()})
