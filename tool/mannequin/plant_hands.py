"""Flat palms on the floor for the humanoid avatar (render_mannequin.py, AVATAR=1).

The desk-break moves were posed for the mannequin's block hand, so in a plank, a push-up, all fours or a long sit
the hand stands on its fingertips. plant() re-bakes a job's action frame by frame:
1. a hand counts as a support when it is near the floor with the forearm standing on it and the elbow off the floor
   (weight w, smoothed in time);
2. the wrist turns so the palm lies flat: palm down, fingers toward the head (trunk lying) or the front (trunk up);
3. the hand now hovers by about a hand length, so the body comes down by that much: with the trunk held off the
   floor, the whole body turns about its other floor contacts (toes, knees); otherwise (seated, or prone with the
   chest down) the arm swings at the shoulder.
Face down on the hands (plank, push-up, all fours) the neck also extends a little, so the head lines up with the
spine instead of hanging. Frames without a support keep the original pose. Returns (action, {side: support weight per frame}); the action
is the same one, with no weights, when nothing changes.

reground() runs first: the builder rests the mannequin's mesh on the floor (or the move's ground boxes), and the
avatar's shoes reach 1.2 cm lower than the mannequin's feet (other parts differ too), so on every frame where the
avatar touches or sinks into its support, the whole body is moved up or down so it rests exactly on it.
"""
import os

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector
from mathutils.bvhtree import BVHTree

UP = Vector((0, 0, 1))
PALM_REST = {'L': Vector((-1, 0, 0)), 'R': Vector((1, 0, 0))}  # palms face the thighs at rest, fingers down
FINGERS_REST = Vector((0, 0, -1))
CONTACT_Z = 0.004  # the palm's lowest point after planting
NECK_EXT = np.radians(18)  # face down on the hands, the head comes up into line with the spine
WRIST_MAX = 94.0  # deg: a planted hand's wrist bend off the forearm (motion_review allows 90 + 5 under load)
ARM_GROUPS = ('armL', 'armR', 'elbowL', 'elbowR', 'handL', 'handR')


def smooth(x, a, b):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def frame_rot(d0, a0, d1, a1):
    def basis(d, a):
        d = d.normalized()
        a = (a - d * a.dot(d)).normalized()
        return Matrix((d, a, d.cross(a))).transposed()
    return basis(d1, a1) @ basis(d0, a0).transposed()


def horiz(v):
    return Vector((v.x, v.y, 0))


class Planter:
    def __init__(self, scene, arm, body, hf=None):
        self.scene, self.arm, self.body = scene, arm, body
        self.hf = hf or height_field(None)  # support height under each point (floor + the move's ground boxes)
        n = len(body.data.vertices)
        gi = {g.name: g.index for g in body.vertex_groups}
        W = {k: np.zeros(n) for k in gi}
        inv = {v: k for k, v in gi.items()}
        for v in body.data.vertices:
            for g in v.groups:
                W[inv[g.group]][v.index] = g.weight
        self.hand = {s: W['hand' + s] > 0.5 for s in 'LR'}
        self.chest = W['spine'] > 0.5
        self.pelvis = W['hips'] > 0.5
        arm_w = sum(W[g] for g in ARM_GROUPS if g in W)
        self.rest_of_body = arm_w < 0.2

    def update(self):
        bpy.context.view_layer.update()

    def verts(self):
        deps = bpy.context.evaluated_depsgraph_get()
        ev = self.body.evaluated_get(deps)
        me = ev.to_mesh()
        co = np.empty(len(me.vertices) * 3)
        me.vertices.foreach_get('co', co)
        ev.to_mesh_clear()
        M = np.array(ev.matrix_world)
        return co.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]

    def head(self, name):
        return self.arm.matrix_world @ self.arm.pose.bones[name].head

    def world(self, name):
        return self.arm.matrix_world @ self.arm.pose.bones[name].matrix

    def set_world(self, name, M):
        self.arm.pose.bones[name].matrix = self.arm.matrix_world.inverted() @ M
        self.update()

    def trunk_lying(self):
        t = self.head('neck') - self.head('hips')
        return abs(t.normalized().z) < 0.6

    def finger_target(self, s):
        if self.trunk_lying():
            d = horiz(self.head('neck') - self.head('hips'))
        else:  # seated: fingers to the body's front
            R = (self.world('hips').to_3x3() @ self.arm.data.bones['hips'].matrix_local.to_3x3().inverted())
            d = horiz(R @ Vector((0, -1, 0)))
        return d.normalized() if d.length > 1e-4 else Vector((0, -1, 0))

    def rest_rot(self, name):
        return self.world(name).to_3x3() @ self.arm.data.bones[name].matrix_local.to_3x3().inverted()

    def face_down(self):
        return (self.rest_rot('spine') @ Vector((0, -1, 0))).z < -0.5

    def lift_head(self, ang):
        """Extends the neck by ang (the avatar's neck leans forward at rest: face down, the head would hang)."""
        k = self.rest_rot('spine') @ Vector((1, 0, 0))
        N = self.head('neck')
        self.set_world('neck', Matrix.Translation(N) @ Matrix.Rotation(-ang, 4, k) @ Matrix.Translation(-N) @ self.world('neck'))

    def flatten(self, s, w, fingers=None):
        """Turns hand s at the wrist (by w) so the palm faces down, the fingers towards `fingers` (default
        finger_target: the head when lying, the front when upright)."""
        name = 'hand' + s
        M = self.world(name)
        R = M.to_3x3() @ self.arm.data.bones[name].matrix_local.to_3x3().inverted()
        fd, pn = R @ FINGERS_REST, R @ PALM_REST[s]
        Q = frame_rot(fd, pn, fingers if fingers is not None else self.finger_target(s), Vector((0, 0, -1))).to_quaternion()
        # at most WRIST_MAX of bend off the forearm (approved 13/11: 90 deg with the palm bearing weight): a forearm
        # leaning back past vertical leaves the heel of the hand a little up instead of over-extending the wrist
        fa = (self.head(name) - self.head('elbow' + s)).normalized()
        bend = lambda q: np.degrees((q @ fd).angle(fa)) if (q @ fd).length > 1e-6 else 0.0  # noqa: E731
        if bend(Quaternion().slerp(Q, w)) > WRIST_MAX:
            lo, hi = 0.0, w
            for _ in range(20):
                mid = (lo + hi) / 2
                lo, hi = (mid, hi) if bend(Quaternion().slerp(Q, mid)) <= WRIST_MAX else (lo, mid)
            w = lo
        Q = Quaternion().slerp(Q, w)
        wr = M.translation.copy()
        self.set_world(name, Matrix.Translation(wr) @ Q.to_matrix().to_4x4() @ Matrix.Translation(-wr) @ M)

    def above(self, P):
        return P[:, 2] - self.hf(P)

    def lift(self, s, P=None):
        P = self.verts() if P is None else P
        return self.above(P[self.hand[s]]).min() - CONTACT_Z

    def tilt(self, drop, at):
        """Turns the whole body about its other floor contacts so the point `at` comes down by `drop`."""
        P = self.verts()
        z = self.above(P)
        low = self.rest_of_body & (z < z[self.rest_of_body].min() + 0.04)
        piv = Vector(P[low].mean(0))
        e = horiz(at - piv)
        L = e.length
        if L < 0.3:
            return False
        e.normalize()
        th = -np.arctan2(drop, L)
        k = e.cross(UP).normalized()
        Rm = Matrix.Translation(piv) @ Matrix.Rotation(th, 4, k) @ Matrix.Translation(-piv)
        self.set_world('hips', Rm @ self.world('hips'))
        return True

    def leg_up(self, s, d):
        """Two-bone IK: moves the ankle of leg s straight up by d (the knee bends in its own plane, the thigh
        swings at the hip), so the foot keeps its place on the floor plan."""
        H, K, A = self.head('leg' + s), self.head('knee' + s), self.head('foot' + s)
        L1, L2 = (K - H).length, (A - K).length
        A2 = A + UP * d
        D, D2 = (A - H).length, min((A2 - H).length, 0.999 * (L1 + L2))
        cos = lambda x: np.clip((L1 * L1 + L2 * L2 - x * x) / (2 * L1 * L2), -1, 1)  # noqa: E731
        dth = np.arccos(cos(D2)) - np.arccos(cos(D))  # change of the inner knee angle
        n = (K - H).cross(A - K)
        n = n.normalized() if n.length > 1e-6 else (self.world('knee' + s).to_3x3() @ Vector((1, 0, 0))).normalized()
        best = None
        for sg in (1, -1):  # the hinge's sign: keep the one that reaches the new distance with the knee still bending
            # forwards (both signs reach it; the other one flipped a step-up knee 94 deg backwards in a frame)
            M0 = self.world('knee' + s)
            self.set_world('knee' + s, Matrix.Translation(K) @ Matrix.Rotation(sg * dth, 4, n) @ Matrix.Translation(-K) @ M0)
            err = abs((self.head('foot' + s) - H).length - D2)
            bend = self.arm.pose.bones['knee' + s].matrix_basis.to_euler('YZX').x
            err += 1.0 if bend < np.radians(-3) else 0.0
            if best is None or err < best[0]:
                best = (err, self.world('knee' + s).copy())
            self.set_world('knee' + s, M0)
        self.set_world('knee' + s, best[1])
        v, v2 = self.head('foot' + s) - H, A2 - H
        q = v.rotation_difference(v2)
        self.set_world('leg' + s, Matrix.Translation(H) @ q.to_matrix().to_4x4() @ Matrix.Translation(-H) @ self.world('leg' + s))

    def reach_arm(self, s, T):
        """Two-bone IK: the wrist of arm s onto T (the elbow bends in its own plane, keeping its bend direction; the
        upper arm turns at the shoulder); out of reach the arm straightens towards T."""
        S, E, Wr = self.head('arm' + s), self.head('elbow' + s), self.head('hand' + s)
        L1, L2 = (E - S).length, (Wr - E).length
        D, D2 = (Wr - S).length, min((T - S).length, 0.999 * (L1 + L2))
        cos = lambda x: np.clip((L1 * L1 + L2 * L2 - x * x) / (2 * L1 * L2), -1, 1)  # noqa: E731
        dth = np.arccos(cos(D2)) - np.arccos(cos(D))  # change of the inner elbow angle
        n = (E - S).cross(Wr - E)
        if n.length > 1e-6 and abs(dth) > 1e-5:
            n.normalize()
            best = None
            for sg in (1, -1):
                M0 = self.world('elbow' + s)
                self.set_world('elbow' + s, Matrix.Translation(E) @ Matrix.Rotation(sg * dth, 4, n) @ Matrix.Translation(-E) @ M0)
                err = abs((self.head('hand' + s) - S).length - D2)
                if best is None or err < best[0]:
                    best = (err, self.world('elbow' + s).copy())
                self.set_world('elbow' + s, M0)
            self.set_world('elbow' + s, best[1])
        v, v2 = self.head('hand' + s) - S, T - S
        q = v.rotation_difference(v2)
        self.set_world('arm' + s, Matrix.Translation(S) @ q.to_matrix().to_4x4() @ Matrix.Translation(-S) @ self.world('arm' + s))

    def swing(self, s, drop):
        """Swings the arm at the shoulder (elbow angle kept) so the wrist comes down by `drop`."""
        S, Wr = self.head('arm' + s), self.head('hand' + s)
        v = Wr - S
        r = v.length
        h = horiz(v)
        e = h.normalized() if h.length > 1e-3 else Vector((0, -1, 0))
        vz = max(v.z - drop, -0.999 * r)
        v2 = e * np.sqrt(max(r * r - vz * vz, 0)) + UP * vz
        q = v.rotation_difference(v2)
        M = self.world('arm' + s)
        self.set_world('arm' + s, Matrix.Translation(S) @ q.to_matrix().to_4x4() @ Matrix.Translation(-S) @ M)


def is_cyclic(basis, frames):
    """A looping move: the last frame's pose is the first one (arm bones left out: the steps before may have moved
    them, and they are what is being smoothed)."""
    b0, b1 = basis[frames[0]], basis[frames[-1]]
    keys = [k for k in b0 if not k.startswith(('arm', 'elbow', 'hand'))]
    return all(abs(b0[k].to_quaternion().dot(b1[k].to_quaternion())) > 0.999 and (b0[k].translation - b1[k].translation).length < 0.005 for k in keys)


def smooth_track(x, cyc, half_max=3, avg=13):
    """No pops: max over +-half_max frames, then a moving average; around the seam for a looping move."""
    x = np.asarray(x, float)
    y = x[:-1] if cyc else x
    n_ = len(y)
    mode = 'wrap' if cyc else 'edge'
    yp = np.pad(y, half_max, mode=mode)
    w = np.array([yp[i:i + 2 * half_max + 1].max() for i in range(n_)])
    w = np.convolve(np.pad(w, avg // 2, mode=mode), np.ones(avg) / avg, mode='valid')
    return np.r_[w, w[:1]] if cyc else w


def height_field(ground):
    """Support height under (x, y): the floor (base) or the highest ground box there (kineti_builder "ground")."""
    base = ground.get('base', 0.0) if ground else 0.0
    boxes = np.array(ground.get('boxes', []) if ground else [], float).reshape(-1, 5)

    def hf(P):
        h = np.full(len(P), base)
        for x0, x1, y0, y1, hb in boxes:
            inside = (P[:, 0] >= x0) & (P[:, 0] <= x1) & (P[:, 1] >= y0) & (P[:, 1] <= y1)
            h[inside] = np.maximum(h[inside], hb)
        return h
    return hf


GROUPS = ('hips', 'spine', 'neck', 'armL', 'elbowL', 'armR', 'elbowR', 'legL', 'kneeL', 'footL', 'legR', 'kneeR', 'footR')


def dominant_groups(mesh):
    """Index into GROUPS of each vertex's strongest body group (-1: hands, the mouse prop, unweighted)."""
    gi = {g.index: g.name for g in mesh.vertex_groups}
    out = np.full(len(mesh.data.vertices), -1)
    for v in mesh.data.vertices:
        gs = [g for g in v.groups if gi[g.group] in GROUPS + ('handL', 'handR')]
        if gs:
            n = gi[max(gs, key=lambda g: g.weight).group]
            out[v.index] = GROUPS.index(n) if n in GROUPS else -1
    return out


def group_lows(P, dom, hf):
    """Lowest height above the support of each body group (inf when it has no vertex)."""
    z = P[:, 2] - hf(P)
    lows = np.full(len(GROUPS), np.inf)
    np.minimum.at(lows, dom[dom >= 0], z[dom >= 0])
    return lows


def reground(scene, arm, body, act, ground, set_action, ref=None, target=None):
    """Rests the avatar where the builder rested its own mesh (ref: desk-break's mannequin on the same rig, hidden),
    frame by frame, part by part. The body parts the mannequin rests on its support (lowest point within 1 cm of
    it) are the contacts: the avatar moves up or down so its own parts rest there too, none of them below (the
    avatar's shoes, knees and back differ from the mannequin's). Parts the builder pushed into the floor (a
    landing heel in a walk) are not contacts: clear_limbs() lifts those. With no contact (a jump), the avatar keeps
    the mannequin's height. Without ref, the lowest gap is closed below 1 cm and the correction fades out by 4 cm.
    Returns (action, target): the action (a copy with the pelvis moved, or the same one when nothing changes by
    more than 2 mm) and the per-frame contact heights to pass back as `target` on a second call (the reference
    moves with the rig, so after a first correction it no longer shows where the builder put the body)."""
    f0, f1 = (int(round(v)) for v in act.frame_range)
    frames = list(range(f0, f1 + 1))
    pl = Planter(scene, arm, body)
    hf = height_field(ground)
    dom_a = dominant_groups(body)
    rp = None
    if ref is not None and target is None:
        rp = Planter(scene, arm, ref)
        dom_r = dominant_groups(ref)
    set_action(act)
    lows_a, loc = [], []
    tgt = [] if target is None else list(target[0])
    target_pen = None if target is None else target[1]
    PEN = []
    hips = arm.pose.bones['hips']
    for f in frames:
        scene.frame_set(f)
        lows_a.append(group_lows(pl.verts(), dom_a, hf))
        if rp is not None:
            lr = group_lows(rp.verts(), dom_r, hf)
            PEN.append(lr < -0.01)
            m = lr[np.isfinite(lr)].min()
            # contacts: parts within 1 cm above the support (and not below it); else (airborne) the lowest part
            tgt.append(np.where((lr > -0.01) & (lr < 0.01), np.maximum(lr, 0), np.nan) if m > -0.01 or np.any((lr > -0.01) & (lr < 0.01))
                       else np.where(lr == m, max(m, 0), np.nan))
            if not np.any(np.isfinite(tgt[-1])):
                tgt[-1] = np.where(lr == m, max(m, 0), np.nan)
        loc.append(hips.location.copy())
    lows_a = np.array(lows_a)
    if tgt:
        T = np.array(tgt)
        # move so that every contact part is at or above its height, the deepest one exactly on it, and no other
        # part is below the support (unless the builder put it there too: those are clear_limbs' job)
        corr = np.nanmax(np.where(np.isfinite(T), T - lows_a, np.nan), axis=1)
        corr = np.where(np.isfinite(corr), corr, -np.inf)
        pen_ok = np.array(PEN) if target is None else np.array(target_pen)
        corr = np.maximum(corr, np.where(pen_ok, -np.inf, -lows_a).max(1))
        corr = np.where(np.isfinite(corr), corr, 0)
    else:
        gap = lows_a.min(1)
        corr = -gap * (1 - smooth(gap, 0.01, 0.04))
    corr = np.convolve(np.pad(corr, 2, mode='edge'), np.ones(5) / 5, mode='valid')  # no pops
    if np.abs(corr).max() < 0.002:
        return act, ((tgt, PEN if PEN else target_pen) if tgt else None)
    new = act.copy()
    new.name = act.name + '~ground'
    new.use_fake_user = False
    set_action(new)
    # world z -> the root bone's location channels (hips has no parent)
    R = (arm.matrix_world.to_3x3() @ arm.data.bones['hips'].matrix_local.to_3x3()).inverted()
    for f, c, l0 in zip(frames, corr, loc):
        hips.location = l0 + R @ Vector((0, 0, float(c)))
        hips.keyframe_insert('location', frame=f)
    print('GROUND', act.name, 'ref' if tgt else 'gap', 'corr', round(float(corr.min()), 3), '..', round(float(corr.max()), 3))
    return new, ((tgt, PEN if PEN else target_pen) if tgt else None)


def clear_limbs(scene, arm, body, act, ground, set_action):
    """The avatar's shoes and forearms are thicker than the mannequin's segments, so where the builder put a
    mannequin heel or forearm on the floor the avatar's goes through it (a heel landing in a walk, forearms lying
    by the body). On every frame, an arm or leg whose lowest point is below its support by more than 5 mm swings up
    at the shoulder / hip (the elbow / knee kept) until it rests on it. The hands are left to plant(). Returns the
    action (a re-baked copy, or the same one when nothing goes through)."""
    f0, f1 = (int(round(v)) for v in act.frame_range)
    frames = list(range(f0, f1 + 1))
    pl = Planter(scene, arm, body, height_field(ground))
    gi = {g.name: g.index for g in body.vertex_groups}
    dom = np.full(len(body.data.vertices), -1)
    for v in body.data.vertices:
        gs = [g for g in v.groups if g.group not in (gi.get('lp_joints'), gi.get('prop'))]
        if gs:
            dom[v.index] = max(gs, key=lambda g: g.weight).group
    LIMBS = {'L': ('armL', ('elbowL',)), 'R': ('armR', ('elbowR',)), 'lL': ('legL', ('kneeL', 'footL')), 'lR': ('legR', ('kneeR', 'footR'))}
    masks = {k: np.isin(dom, [gi[g] for g in gs]) for k, (_, gs) in LIMBS.items()}
    set_action(act)
    depth = {k: np.zeros(len(frames)) for k in LIMBS}
    for i, f in enumerate(frames):
        scene.frame_set(f)
        P = pl.verts()
        for k in LIMBS:
            depth[k][i] = max(0.0, -pl.above(P[masks[k]]).min() - 0.002)
    if max(d.max() for d in depth.values()) < 0.005:
        return act
    basis = {}
    for f in frames:
        scene.frame_set(f)
        basis[f] = {pb.name: pb.matrix_basis.copy() for pb in arm.pose.bones}
    cyc = is_cyclic(basis, frames)
    for k in LIMBS:  # no pops (around the seam for a looping move)
        depth[k] = smooth_track(depth[k], cyc, 2, 7)
    set_action(None)
    new = bpy.data.actions.new(act.name + '~clear')
    new.use_fake_user = False
    if 'ground' in act:
        new['ground'] = act['ground']
    keys = {pb.name: [] for pb in arm.pose.bones}
    for i, f in enumerate(frames):
        for pb in arm.pose.bones:
            pb.matrix_basis = basis[f][pb.name]
        pl.update()
        for k, (root, _) in LIMBS.items():
            want = depth[k][i]  # the smoothed depth: the lift ramps in and out instead of snapping at the first contact
            for it in range(2 if want > 0.002 else 0):
                P = pl.verts()
                z = pl.above(P[masks[k]])
                d = max(-z.min() - 0.002, want if it == 0 else 0)
                if d <= 0.001:
                    break
                low = Vector(P[masks[k]][int(np.argmin(z))])
                if k.startswith('l'):  # a leg: lift the foot straight up (bend the knee, swing the thigh)
                    pl.leg_up(k[1], d)
                    continue
                S = pl.head(root)
                v = low - S
                r = v.length
                h = horiz(v)
                e = h.normalized() if h.length > 1e-3 else Vector((0, -1, 0))
                vz = min(v.z + d, 0.999 * r)
                v2 = e * np.sqrt(max(r * r - vz * vz, 0)) + UP * vz
                q = v.rotation_difference(v2)
                pl.set_world(root, Matrix.Translation(S) @ q.to_matrix().to_4x4() @ Matrix.Translation(-S) @ pl.world(root))
        for pb in arm.pose.bones:
            keys[pb.name].append((f, pb.matrix_basis.copy()))
    set_action(new)
    for name, ks in keys.items():
        pb = arm.pose.bones[name]
        for f, mb in ks:
            pb.matrix_basis = mb
            pb.keyframe_insert('rotation_quaternion', frame=f)
            pb.keyframe_insert('location', frame=f)
    print('CLEAR', act.name, {k: round(float(d.max()), 3) for k, d in depth.items() if d.max() > 0.004})
    return new


def unclip_arms(scene, arm, body, act, set_action, support=None):
    """The avatar's trunk, thighs and head are thicker than the mannequin's, so a forearm or hand the builder laid
    on them (arms crossed, hands on the thighs, on the hips, behind the head) sinks a few cm in. On every frame the
    deepest forearm / hand vertex inside the trunk, the legs or the head (signed distance to those parts' faces,
    beyond what it is at rest) is measured; the arm then swings at the shoulder (the elbow kept) so that point
    comes back out to the surface. The depth is smoothed in time (no pops) and frames where the hand bears weight
    on a support (plant) are left alone. Returns the action (a re-baked copy, or the same one)."""
    f0, f1 = (int(round(v)) for v in act.frame_range)
    frames = list(range(f0, f1 + 1))
    pl = Planter(scene, arm, body)
    gi = {g.name: g.index for g in body.vertex_groups}
    dom = np.full(len(body.data.vertices), -1)
    for v in body.data.vertices:
        gs = [g for g in v.groups if g.group not in (gi.get('lp_joints'), gi.get('prop'))]
        if gs:
            dom[v.index] = max(gs, key=lambda g: g.weight).group
    pg = np.array([np.bincount(dom[list(p.vertices)][dom[list(p.vertices)] >= 0], minlength=len(gi)).argmax()
                   if (dom[list(p.vertices)] >= 0).any() else -1 for p in body.data.polygons])
    polys = [tuple(p.vertices) for p in body.data.polygons]
    # the body without the arms: one surface (separate part shells are open at the joints, and a hand by the thigh
    # read 11 cm "inside" its open top: the push drove the arm into the trunk)
    tgts = [[polys[k] for k in np.flatnonzero(np.isin(pg, [gi[g] for g in ('spine', 'hips', 'neck', 'legL', 'legR', 'kneeL', 'kneeR', 'footL', 'footR') if g in gi]))]]
    A = {s: np.flatnonzero(np.isin(dom, [gi['elbow' + s], gi['hand' + s]])) for s in 'LR'}

    def depth(P, idx, base=None):
        """Deepest vertex of idx inside one of the shells, beyond its own depth at rest (base: {vertex: [per shell]})."""
        V = [tuple(p) for p in P]
        best, at, nrm = 0.0, None, None
        out = {}
        for t, tgt in enumerate(tgts):
            tr = BVHTree.FromPolygons(V, tgt)
            for k in idx:
                v = Vector(P[k])
                loc, nor, _, d = tr.find_nearest(v, 0.12)
                di = d if loc is not None and (v - loc).dot(nor) < -0.7 * d else 0.0
                out.setdefault(k, []).append(di)
                if base is not None:
                    di -= base[k][t]
                if di > best:
                    best, at, nrm = di, v, nor
        return best, at, nrm, out
    set_action(act)
    scene.frame_set(f0)
    for pb in arm.pose.bones:  # baseline: how deep each vertex is at rest (open shells, parts that already touch)
        pb.matrix_basis = Matrix()
    pl.update()
    P0 = pl.verts()
    base = {}
    for s in 'LR':
        base.update(depth(P0, A[s])[3])
    scene.frame_set(f0)
    raw = {s: np.zeros(len(frames)) for s in 'LR'}
    for i, f in enumerate(frames):
        scene.frame_set(f)
        P = pl.verts()
        for s in 'LR':
            if support and support.get(s) is not None and support[s][i] > 0.5:
                continue
            raw[s][i] = max(0.0, depth(P, A[s][::2], base)[0] - 0.01)
    if os.environ.get('PLANT_DEBUG'):
        print('UNCLIPDBG', act.name, 'raw', {s: round(float(r.max()), 3) for s, r in raw.items()})
    if max(r.max() for r in raw.values()) < 0.005:
        return act
    basis = {}
    for f in frames:
        scene.frame_set(f)
        basis[f] = {pb.name: pb.matrix_basis.copy() for pb in arm.pose.bones}
    cyc = is_cyclic(basis, frames)
    want = {s: smooth_track(raw[s], cyc, 2, 7) for s in 'LR'}
    set_action(None)
    new = bpy.data.actions.new(act.name + '~unclip')
    new.use_fake_user = False
    if 'ground' in act:
        new['ground'] = act['ground']
    # pass A: the raw extra shoulder turn per frame (rotation vector), pass B: smoothed in time (around the seam for
    # a looping move; frame-by-frame turns swung with the surface normal: a 46 deg pop behind the back), pass C: baked
    raw_c = {s: np.zeros((len(frames), 3)) for s in 'LR'}
    for i, f in enumerate(frames):
        for pb in arm.pose.bones:
            pb.matrix_basis = basis[f][pb.name]
        pl.update()
        for s in 'LR':
            M0 = pl.world('arm' + s).copy()
            for it in range(3 if want[s][i] > 0.002 else 0):
                P = pl.verts()
                d, at, nor, _ = depth(P, A[s], base)
                d = max(d - 0.008, want[s][i] if it == 0 else 0)
                if d <= 0.002 or at is None:
                    break
                S = pl.head('arm' + s)
                q = (at - S).rotation_difference(at + nor * d - S)
                pl.set_world('arm' + s, Matrix.Translation(S) @ q.to_matrix().to_4x4() @ Matrix.Translation(-S) @ pl.world('arm' + s))
            c = pl.world('arm' + s).to_quaternion() @ M0.to_quaternion().inverted()
            if c.w < 0:
                c.negate()
            raw_c[s][i] = np.array(c.axis) * c.angle
    sm = {s: np.stack([smooth_track(raw_c[s][:, k], cyc, 0, 9) for k in range(3)], 1) for s in 'LR'}
    keys = {pb.name: [] for pb in arm.pose.bones}
    for i, f in enumerate(frames):
        for pb in arm.pose.bones:
            pb.matrix_basis = basis[f][pb.name]
        pl.update()
        for s in 'LR':
            v = Vector(sm[s][i])
            if v.length > 1e-6:
                S = pl.head('arm' + s)
                R = Quaternion(v.normalized(), v.length).to_matrix().to_4x4()
                pl.set_world('arm' + s, Matrix.Translation(S) @ R @ Matrix.Translation(-S) @ pl.world('arm' + s))
        for pb in arm.pose.bones:
            keys[pb.name].append((f, pb.matrix_basis.copy()))
    set_action(new)
    for name, ks in keys.items():
        pb = arm.pose.bones[name]
        for f, mb in ks:
            pb.matrix_basis = mb
            pb.keyframe_insert('rotation_quaternion', frame=f)
            pb.keyframe_insert('location', frame=f)
    print('UNCLIP', act.name, {s: round(float(w.max()), 3) for s, w in want.items() if w.max() > 0.004})
    return new


def plant(scene, arm, body, act, sides, set_action, ground=None, flat=(), pin_sides=()):
    """sides: the hands that may plant (not holding anything). set_action(a) assigns a to the armature.
    ground: the move's height field (kineti_builder "ground"): hands also plant on its boxes (a chair seat, a step,
    the bed). flat: hands resting on a prop that is drawn under them afterwards (table, chair back): they only turn
    palm down, on every frame, and the body does not move."""
    flat = [s for s in flat if s in sides]
    sides = [s for s in sides if s not in flat]
    if not sides and not flat:
        return act, {}
    f0, f1 = (int(round(v)) for v in act.frame_range)
    frames = list(range(f0, f1 + 1))
    pl = Planter(scene, arm, body, height_field(ground))
    set_action(act)
    basis = {}
    for f in frames:
        scene.frame_set(f)
        basis[f] = {pb.name: pb.matrix_basis.copy() for pb in arm.pose.bones}

    def pose(f):
        for pb in arm.pose.bones:
            pb.matrix_basis = basis[f][pb.name]
        pl.update()

    # 1. support weights from the original pose; Rw: a hand lying on the floor at the end of a lying forearm (arms
    # by the sides in a bridge, on the floor overhead): palm down, fingers on along the forearm, resting on it
    W = {s: np.zeros(len(frames)) for s in sides}
    Rw = {s: np.zeros(len(frames)) for s in sides}
    dbg = {s: [9.0, -9.0] for s in sides}
    lying = np.zeros(len(frames), bool)
    down = np.zeros(len(frames), bool)
    chest_z = np.zeros(len(frames))
    pelvis_z = np.zeros(len(frames))
    trunk_z = np.zeros(len(frames))
    ftg = {s: [None] * len(frames) for s in sides}  # where the fingers of a planted hand point
    for i, f in enumerate(frames):
        scene.frame_set(f)
        P = pl.verts()
        for s in sides:
            ftg[s][i] = pl.finger_target(s)
        lying[i] = pl.trunk_lying()
        down[i] = lying[i] and pl.face_down()
        chest_z[i] = pl.above(P[pl.chest]).min()  # how far the chest is off the floor
        pelvis_z[i] = pl.above(P[pl.pelvis]).min()
        trunk_z[i] = abs((pl.head('neck') - pl.head('hips')).normalized().z)
        for s in sides:
            low = pl.above(P[pl.hand[s]]).min()
            el, wr = pl.head('elbow' + s), pl.head('hand' + s)
            fore = el.z - wr.z
            steep = fore / max((el - wr).length, 1e-6)  # 1 = forearm standing upright on the hand
            dbg[s] = [min(dbg[s][0], low), max(dbg[s][1], fore)]
            el_up = el.z - pl.hf(np.array([el]))[0]
            # a hand support: hand on the floor, forearm standing on it and the elbow off the floor
            # (prone on the elbows the wrist can sit a little lower than the elbow: not a support)
            # (the bottom of a push-up, elbows back, leaves the forearm at ~75 degrees from vertical: still a support)
            # (up to 12 cm: the avatar's hand hangs fingers down below the mannequin's block hand, so in a plank the
            # keys left it 7-8 cm over the floor and it was never planted)
            # (and the hand well away from the feet: a standing windmill reaching for the opposite foot is not a hand
            # support; tilting the body onto it tipped the figure over)
            near_foot = min(horiz(wr - pl.head('foot' + t)).length for t in 'LR')
            W[s][i] = smooth(-low, -0.12, -0.06) * smooth(near_foot, 0.3, 0.4) * smooth(fore, 0.03, 0.06) * smooth(steep, 0.12, 0.25) * smooth(el_up, 0.08, 0.12)
            Rw[s][i] = (smooth(-low, -0.05, -0.025) * (1 - smooth(steep, 0.12, 0.3)) * (1 - smooth(el_up, 0.14, 0.2))
                        * (1 - smooth(abs(steep) if fore < 0 else 0, 0.5, 0.7)))
            if os.environ.get('PLANT_DEBUG') and i % 6 == 0:
                print('PLANTDBG', f, s, round(low, 3), round(fore, 3), round(steep, 2), round(el_up, 3), 'W', round(W[s][i], 2), 'R', round(Rw[s][i], 2))
    # a looping move (last frame = first) is smoothed around the seam, or the hand turns at the loop (94 deg)
    cyc = is_cyclic(basis, frames)
    if os.environ.get('PLANT_DEBUG'):
        b0, b1 = basis[frames[0]], basis[frames[-1]]
        print('PLANTDBG cyc', cyc, {k: (round(abs(b0[k].to_quaternion().dot(b1[k].to_quaternion())), 5), round((b0[k].translation - b1[k].translation).length, 4)) for k in b0 if not k.startswith(('arm', 'elbow', 'hand'))})
    for s in sides:  # (the wrist may turn > 100 deg to lie flat: over 13 frames that stays under ~10 deg per frame)
        W[s] = smooth_track(W[s], cyc, 3, 21)  # (a hand leaving the floor in a bird dog turned 18 deg/frame over 13)
        Rw[s] = smooth_track(Rw[s], cyc)
        Rw[s] = Rw[s] * (1 - np.clip(W[s], 0, 1))  # a support wins
    # a hand on the floor does not turn: through each stretch of support its fingers keep the direction they have
    # where it bears most weight (finger_target switches from "to the head" to "to the front" as the trunk rises:
    # in a table-to-down-dog the planted hand spun 134 deg in a frame)
    for s in sides:
        on = W[s] > 0.02
        i = 0
        while i < len(frames):
            if not on[i]:
                i += 1
                continue
            j = i
            while j < len(frames) and on[j]:
                j += 1
            k = i + int(np.argmax(W[s][i:j]))
            for t in range(i, j):
                ftg[s][t] = ftg[s][k]
            i = j
        if cyc and on[0] and on[-1] and not on.all():  # a stretch across the loop seam is one stretch
            a = int(np.argmin(on))                       # first frame off
            b = len(frames) - int(np.argmin(on[::-1]))   # first frame of the last stretch
            idx = list(range(b, len(frames))) + list(range(0, a))
            k = idx[int(np.argmax([W[s][t] for t in idx]))]
            for t in idx:
                ftg[s][t] = ftg[s][k]
    rest = [s for s in sides if Rw[s].max() >= 0.05]
    if not flat and not rest and max(W[s].max() for s in sides) < 0.05:
        print('PLANT', act.name, 'none', {s: [round(v, 3) for v in dbg[s]] for s in sides})
        return act, {}
    sides = [s for s in sides if W[s].max() >= 0.05]
    for s in flat:
        W[s] = np.ones(len(frames))
    peak = int(np.argmax(sum(W[s] for s in sides))) if sides else 0
    # tilt only when the trunk is held off the floor (plank, push-up, all fours); prone with the chest down or
    # seated, the arm swings instead
    # (knee push-up, incline push-up on a chair: the trunk is held off the floor even when it is not near horizontal;
    # a long sit or a seated body has its pelvis down)
    mode = 'tilt' if chest_z[peak] > 0.2 and pelvis_z[peak] > 0.12 and trunk_z[peak] < 0.85 else 'swing'
    print('PLANT', act.name, mode, 'frames', int(sum(max(W[s][i] for s in sides) > 0.5 for i in range(len(frames)))) if sides else 0,
          '/', len(frames), 'flat', ''.join(flat), 'rest', ''.join(f'{s}{int(sum(Rw[s] > 0.5))}' for s in rest))

    # 2. re-bake every frame into a new action
    set_action(None)
    new = bpy.data.actions.new(act.name + '~planted')
    new.use_fake_user = False
    if 'ground' in act:  # the height field the move was built on (render_mannequin draws the steps from it)
        new['ground'] = act['ground']
    keys = {pb.name: [] for pb in arm.pose.bones}
    pin = {}  # hands holding a chair back / a chair beside (pin_sides) stay where they rest on the first frame (the
    if pin_sides:  # chair is drawn there): the arm reaches for it as the body rises or lowers
        pose(frames[0])
        pin = {s: pl.head('hand' + s).copy() for s in pin_sides}
    for i, f in enumerate(frames):
        pose(f)
        active = [s for s in sides if W[s][i] > 0.01]
        for s in pin:
            pl.reach_arm(s, pin[s])
        for s in flat:
            pl.flatten(s, 1.0)
        for s in rest:
            if Rw[s][i] > 0.01:
                for _ in range(2):
                    fd = horiz(pl.head('hand' + s) - pl.head('elbow' + s))
                    pl.flatten(s, Rw[s][i], fd.normalized() if fd.length > 1e-3 else None)
                    pl.swing(s, Rw[s][i] * pl.lift(s))
        mode_f = mode  # (per frame: a tilt that fails falls back to a swing on this frame only; switching for good
        # made the last frame of a loop differ from the first, an 8 cm pelvis jump at the seam of a plank)
        for _ in range(2 if active else 0):
            for s in active:
                pl.flatten(s, W[s][i], ftg[s][i])
            if mode_f == 'tilt':
                wsum = sum(W[s][i] for s in active)
                drop = sum(W[s][i] * pl.lift(s) for s in active) / wsum
                at = sum((pl.head('hand' + s) * W[s][i] for s in active), Vector()) / wsum
                if not pl.tilt(drop * min(1.0, wsum), at):
                    mode_f = 'swing'
            if mode_f == 'swing':
                for s in active:
                    pl.swing(s, W[s][i] * pl.lift(s))
        for s in active:
            pl.flatten(s, W[s][i], ftg[s][i])
        if active and down[peak]:
            pl.lift_head(NECK_EXT * max(W[s][i] for s in active))
        for pb in arm.pose.bones:
            keys[pb.name].append((f, pb.matrix_basis.copy()))
    set_action(new)
    for name, ks in keys.items():
        pb = arm.pose.bones[name]
        for f, mb in ks:
            pb.matrix_basis = mb
            pb.keyframe_insert('rotation_quaternion', frame=f)
            pb.keyframe_insert('location', frame=f)
    for s in rest:
        W[s] = np.maximum(W.get(s, 0), Rw[s])
    return new, W
