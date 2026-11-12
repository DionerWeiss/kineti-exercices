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
"""
import os

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

UP = Vector((0, 0, 1))
PALM_REST = {'L': Vector((-1, 0, 0)), 'R': Vector((1, 0, 0))}  # palms face the thighs at rest, fingers down
FINGERS_REST = Vector((0, 0, -1))
CONTACT_Z = 0.004  # the palm's lowest point after planting
NECK_EXT = np.radians(18)  # face down on the hands, the head comes up into line with the spine
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
    def __init__(self, scene, arm, body):
        self.scene, self.arm, self.body = scene, arm, body
        n = len(body.data.vertices)
        gi = {g.name: g.index for g in body.vertex_groups}
        W = {k: np.zeros(n) for k in gi}
        inv = {v: k for k, v in gi.items()}
        for v in body.data.vertices:
            for g in v.groups:
                W[inv[g.group]][v.index] = g.weight
        self.hand = {s: W['hand' + s] > 0.5 for s in 'LR'}
        self.chest = W['spine'] > 0.5
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

    def flatten(self, s, w):
        name = 'hand' + s
        M = self.world(name)
        R = M.to_3x3() @ self.arm.data.bones[name].matrix_local.to_3x3().inverted()
        fd, pn = R @ FINGERS_REST, R @ PALM_REST[s]
        Q = frame_rot(fd, pn, self.finger_target(s), Vector((0, 0, -1))).to_quaternion()
        Q = Quaternion().slerp(Q, w)
        wr = M.translation.copy()
        self.set_world(name, Matrix.Translation(wr) @ Q.to_matrix().to_4x4() @ Matrix.Translation(-wr) @ M)

    def lift(self, s, P=None):
        P = self.verts() if P is None else P
        return P[self.hand[s], 2].min() - CONTACT_Z

    def tilt(self, drop, at):
        """Turns the whole body about its other floor contacts so the point `at` comes down by `drop`."""
        P = self.verts()
        low = self.rest_of_body & (P[:, 2] < P[self.rest_of_body, 2].min() + 0.04)
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


def plant(scene, arm, body, act, sides, set_action):
    """sides: the hands that may plant (not holding anything). set_action(a) assigns a to the armature."""
    if not sides:
        return act, {}
    f0, f1 = (int(round(v)) for v in act.frame_range)
    frames = list(range(f0, f1 + 1))
    pl = Planter(scene, arm, body)
    set_action(act)
    basis = {}
    for f in frames:
        scene.frame_set(f)
        basis[f] = {pb.name: pb.matrix_basis.copy() for pb in arm.pose.bones}

    def pose(f):
        for pb in arm.pose.bones:
            pb.matrix_basis = basis[f][pb.name]
        pl.update()

    # 1. support weights from the original pose
    W = {s: np.zeros(len(frames)) for s in sides}
    dbg = {s: [9.0, -9.0] for s in sides}
    lying = np.zeros(len(frames), bool)
    down = np.zeros(len(frames), bool)
    chest_z = np.zeros(len(frames))
    for i, f in enumerate(frames):
        scene.frame_set(f)
        P = pl.verts()
        lying[i] = pl.trunk_lying()
        down[i] = lying[i] and pl.face_down()
        chest_z[i] = P[pl.chest, 2].min()  # how far the chest is off the floor
        for s in sides:
            low = P[pl.hand[s], 2].min()
            el, wr = pl.head('elbow' + s), pl.head('hand' + s)
            fore = el.z - wr.z
            steep = fore / max((el - wr).length, 1e-6)  # 1 = forearm standing upright on the hand
            dbg[s] = [min(dbg[s][0], low), max(dbg[s][1], fore)]
            # a hand support: hand on the floor, forearm standing on it and the elbow off the floor
            # (prone on the elbows the wrist can sit a little lower than the elbow: not a support)
            W[s][i] = smooth(-low, -0.075, -0.035) * smooth(fore, 0.05, 0.1) * smooth(steep, 0.25, 0.4) * smooth(el.z, 0.08, 0.12)
            if os.environ.get('PLANT_DEBUG') and s == 'L' and i % 6 == 0:
                print('PLANTDBG', f, round(low, 3), round(fore, 3), round(steep, 2), round(el.z, 3))
    for s in sides:  # no pops: max over +-2 frames, then a moving average
        w = np.array([W[s][max(0, i - 2):i + 3].max() for i in range(len(frames))])
        W[s] = np.convolve(np.pad(w, 3, mode='edge'), np.ones(7) / 7, mode='valid')
    if max(W[s].max() for s in sides) < 0.05:
        print('PLANT', act.name, 'none', {s: [round(v, 3) for v in dbg[s]] for s in sides})
        return act, {}
    peak = int(np.argmax(sum(W[s] for s in sides)))
    # tilt only when the trunk is held off the floor (plank, push-up, all fours); prone with the chest down or
    # seated, the arm swings instead
    mode = 'tilt' if lying[peak] and chest_z[peak] > 0.2 else 'swing'
    print('PLANT', act.name, mode, 'frames', int(sum(max(W[s][i] for s in sides) > 0.5 for i in range(len(frames)))), '/', len(frames))

    # 2. re-bake every frame into a new action
    set_action(None)
    new = bpy.data.actions.new(act.name + '~planted')
    new.use_fake_user = False
    keys = {pb.name: [] for pb in arm.pose.bones}
    for i, f in enumerate(frames):
        pose(f)
        active = [s for s in sides if W[s][i] > 0.01]
        for _ in range(2 if active else 0):
            for s in active:
                pl.flatten(s, W[s][i])
            if mode == 'tilt':
                wsum = sum(W[s][i] for s in active)
                drop = sum(W[s][i] * pl.lift(s) for s in active) / wsum
                at = sum((pl.head('hand' + s) * W[s][i] for s in active), Vector()) / wsum
                if not pl.tilt(drop * min(1.0, wsum), at):
                    mode = 'swing'
            if mode == 'swing':
                for s in active:
                    pl.swing(s, W[s][i] * pl.lift(s))
        for s in active:
            pl.flatten(s, W[s][i])
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
    return new, W
