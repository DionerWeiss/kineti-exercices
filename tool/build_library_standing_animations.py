"""Standing batch of the expanded exercise library: eight supported standing
exercises on the same rig as the home exercises.

Built by tool/build_catalog.py (see its docstring).

Profile scenes use the clinical rig in kineti_lottie (feet and hands are
solved from world points every frame, so nothing slides); frontal and
diagonal scenes use figure3d. Every scene is one slow repetition per loop
(start -> execution -> return), has named step markers and passes the rig's
geometric checks plus its own.
"""

import _rig  # noqa: F401  (puts the Kineti rig on sys.path)
import math

from build_hip_exercise_animations import BACKREST_TOP, arm_angles, chair as profile_chair, hip_flexion_leg
from build_home_exercise_animations import COUNTER, check2d, counter, markers, scene3d
from figure3d import (IK_ERRORS, Camera, add, add_figure, arm_fk, arm_ik, blend, body, chair as chair3d,
                      check as check3d, floor_patch, geometry, leg_ik, length, sub, unit)
from kineti_lottie import (ANKLE, FPS, GEOMETRY_WARNINGS, L_SHIN, STAND_HIP, Scene, Track, figure_geometry,
                           pose, smooth, solve_leg, with_)

PEL_Y = STAND_HIP - 0.015  # standing pelvis height of the 3D balance scenes


def repeat(track, at, timings):
    """rest -> move -> hold -> return -> rest on a 0..1 parameter u; at(u)
    returns the pose. Returns the six boundary times."""
    rest, move, hold, back, tail = timings
    t = [0.0, rest, rest + move, rest + move + hold, rest + move + hold + back, rest + move + hold + back + tail]
    track.add(t[0], t[1], lambda x: at(0.0))
    track.add(t[1], t[2], lambda x: at(smooth((x - t[1]) / move)))
    track.add(t[2], t[3], lambda x: at(1.0))
    track.add(t[3], t[4], lambda x: at(1.0 - smooth((x - t[3]) / back)))
    track.add(t[4], t[5], lambda x: at(0.0))
    return t


def every_frame(scene, track):
    for fr in range(scene.frames + 1):
        yield fr, figure_geometry(track.at(fr / FPS))


def rot(v, a):
    c, s = math.cos(a), math.sin(a)
    return (v[0] * c - v[1] * s, v[0] * s + v[1] * c)


def side_chair(s):
    """Chair beside the patient, backrest just ahead of the hip, as in the
    standing hip flexion scene. Returns the planted back-hand point."""
    backrest = profile_chair(s, -0.01, facing=-1)
    return (backrest + 0.01, BACKREST_TOP + 0.01)


# ------------------------------------------------------------------ hip abduction
def standing_hip_abduction():
    """Near-frontal view. The far hand rests on a chair backrest at the
    patient's side; the outside leg, knee straight and toes forward, moves
    out sideways and back while the trunk stays upright."""
    cam = Camera(yaw=80, pitch=14)  # nearly frontal: the leg reads as going out to the side, not back
    chair_x, chair_z = 0.28, -0.55
    hand = (chair_x - 0.275, 1.012, chair_z + 0.19)
    far_ankle = (0.0, ANKLE, -0.09)
    R = PEL_Y - ANKLE

    def at(u):
        shift = -0.03 * u  # weight onto the standing leg
        a = math.radians(28 * u)
        near_ankle = (0.0, PEL_Y - R * math.cos(a), shift + 0.085 + R * math.sin(a))
        return body(pelvis=(0.0, PEL_Y, shift), trunk=2,
                    legs={'near': leg_ik(near_ankle, (1, 0, 0)), 'far': leg_ik(far_ankle, (1, 0, -0.05))},
                    arms={'near': arm_fk(2, 9, abd=6),
                          'far': arm_ik(hand, (-0.4, -1.0, -0.2), local=False)})

    tr = Track()
    t = repeat(tr, at, (0.8, 1.6, 0.8, 1.8, 0.8))
    extra = [(chair_x + dx, y, chair_z + dz) for dx in (-0.3, 0.25) for y in (0.0, 1.0) for dz in (-0.22, 0.22)]
    s = scene3d('Abdução de quadril em pé', cam, tr, extra)
    floor_patch(s, cam, -0.7, 0.8, -1.0, 0.75)
    chair3d(s, cam, x=chair_x, z=chair_z)
    samples = add_figure(s, cam, tr)
    markers(s, ['start', 'lift_leg_out', 'hold', 'lower_leg', 'rest'], t)
    check3d(s, cam, tr, samples, planted=[('far hand', lambda g: g['far arm'][2], hand),
                                          ('far ankle', lambda g: g['far leg'][2], far_ankle)])
    for fr, g in samples:  # the moving leg stays straight and never crosses the midline
        hipj, knee, ankle = g['near leg']
        assert length(sub(ankle, hipj)) > 0.83, ('knee bent', fr)
        assert ankle[2] > 0.08, ('leg crossed', fr)
    return s


# ------------------------------------------------------------------ knee flexion
def standing_knee_flexion():
    """Profile, chair beside the patient, back hand on the backrest. The
    near knee bends, taking the heel toward the buttock while the thigh
    stays still, then the foot returns to the floor."""
    s = Scene('Flexão de joelho em pé', -1.6, 1.8, -0.25, 6.0)
    s.floor()
    hand = side_chair(s)
    base = pose(0.0, STAND_HIP, 0.0, 3.0)
    base = with_(base, ab=arm_angles(base, hand), aa=(2, 10))
    knee0, ankle0 = solve_leg(STAND_HIP, 0.0, ANKLE)
    shin0 = (ankle0[0] - knee0[0], ankle0[1] - knee0[1])

    def at(u):
        k = math.radians(92 * u)
        v = rot(shin0, -k)
        return with_(base, fa=(knee0[0] + v[0], knee0[1] + v[1], -k - 0.25 * u))

    tr = Track()
    t = repeat(tr, at, (0.8, 1.6, 0.8, 1.8, 1.0))
    s.figure(tr)
    markers(s, ['start', 'bend_knee', 'hold', 'lower_foot', 'rest'], t)
    check2d(s, tr, hands=[('back_arm', hand)])
    for fr, g in every_frame(s, tr):  # thigh does not move
        knee = g['front_leg']['leg'][1]
        assert abs(knee[0] - knee0[0]) < 1e-6 and abs(knee[1] - knee0[1]) < 1e-6, ('thigh moved', fr, knee)
    return s


# ------------------------------------------------------------------ mini squat
def mini_squat():
    """Profile, facing the chair with both hands on the backrest. Hips go
    back and down into a small knee bend, heels down, then up again."""
    s = Scene('Miniagachamento com apoio', -1.45, 1.95, -0.25, 6.0)
    s.floor()
    backrest = profile_chair(s, 0.68)
    hand = (backrest + 0.015, BACKREST_TOP + 0.01)

    def at(u):
        p = pose(-0.075 * u, STAND_HIP - 0.13 * u, 0.0, 3 + 19 * u)
        foot = (0.075 * u, ANKLE, 0.0)
        arms = arm_angles(p, hand)
        return with_(p, fa=foot, fb=foot, aa=arms, ab=arms)

    tr = Track()
    t = repeat(tr, at, (0.8, 1.7, 0.7, 1.8, 0.8))
    s.figure(tr)
    markers(s, ['start', 'bend_knees', 'hold', 'stand_up', 'rest'], t)
    check2d(s, tr, hands=[('front_arm', hand), ('back_arm', hand)])
    for fr, g in every_frame(s, tr):  # whole foot stays on the floor
        for part in ('front_leg', 'back_leg'):
            (hx_, hy_), (tx, ty) = g[part]['foot']
            assert abs(hy_ - (ANKLE - 0.03)) < 1e-6 and abs(tx - 0.14) < 1e-6, ('foot moved', fr)
    return s


# ------------------------------------------------------------------ marching
def standing_marching():
    """Profile, back hand on the chair backrest. The knees rise in turn,
    twice each, with the free arm swinging gently against the lifted leg."""
    s = Scene('Marcha estacionária com apoio', -1.6, 1.8, -0.25, 7.0)
    s.floor()
    hand = side_chair(s)
    base = pose(0.0, STAND_HIP, 0.0, 3.0)
    base = with_(base, ab=arm_angles(base, hand), aa=(2, 10))
    rest, up, hold, down = 0.6, 0.65, 0.2, 0.65
    lift = up + hold + down
    amp = 0.8

    def bump(t, t0):
        x = t - t0
        if x <= 0 or x >= lift:
            return 0.0
        return smooth(x / up) if x < up else 1.0 if x < up + hold else 1 - smooth((x - up - hold) / down)

    starts = [rest + i * lift for i in range(4)]  # A, B, A, B

    def at(t):
        ua = bump(t, starts[0]) + bump(t, starts[2])
        ub = bump(t, starts[1]) + bump(t, starts[3])
        swing = 14 * (ub - ua)
        return with_(base, fa=hip_flexion_leg(amp * ua), fb=hip_flexion_leg(amp * ub), aa=(2 + swing, 12 + swing))

    duration = starts[-1] + lift + rest
    tr = Track()
    tr.add(0, duration, at)
    s.figure(tr)
    t = [0.0] + starts + [starts[-1] + lift, duration]
    markers(s, ['start', 'lift_near_knee', 'lift_far_knee', 'lift_near_knee_again', 'lift_far_knee_again', 'rest'], t)
    check2d(s, tr, hands=[('back_arm', hand)])
    for fr, g in every_frame(s, tr):  # one foot always on the floor
        lows = [min(q[1] for q in g[p]['foot']) for p in ('front_leg', 'back_leg')]
        assert min(lows) < 0.06, ('both feet up', fr)
    return s


# ------------------------------------------------------------------ wall push-up
WALL_X, WALL_HAND_Y = 0.85, 1.22
LEG_REACH = 0.88  # ankle to hip, knees almost straight


def wall_pose(lean):
    """Body in one line from the ankles, leaning `lean` degrees toward the
    wall; hands planted on the wall at shoulder height."""
    a = math.radians(lean)
    hx, hy = LEG_REACH * math.sin(a), ANKLE + LEG_REACH * math.cos(a)
    p = pose(hx, hy, 0.0, lean)
    arms = arm_angles(p, (WALL_X, WALL_HAND_Y))
    foot = (-hx, ANKLE, 0.0)
    return with_(p, fa=foot, fb=foot, aa=arms, ab=arms)


def wall_push_up():
    """Profile, facing a wall at arm's length. With the body straight from
    heels to head, the elbows bend to bring the chest toward the wall, then
    the arms push back to straight."""
    s = Scene('Flexão de braços na parede', -1.3, 2.1, -0.25, 5.6)
    top = s.top
    s.floor(x1=WALL_X + 0.02)
    s.polygon('wall face', [(WALL_X + 0.02, -0.09), (s.right, -0.09), (s.right, top), (WALL_X + 0.02, top)],
              'prop-soft')
    s.line('wall', [(WALL_X + 0.02, -0.09), (WALL_X + 0.02, top)], 'prop', 0.03)
    tr = Track()
    t = repeat(tr, lambda u: wall_pose(14 + 11 * u), (0.8, 1.6, 0.6, 1.6, 1.0))
    s.figure(tr)
    markers(s, ['start', 'bend_elbows', 'hold', 'push_away', 'rest'], t)
    check2d(s, tr, hands=[('front_arm', (WALL_X, WALL_HAND_Y)), ('back_arm', (WALL_X, WALL_HAND_Y))])
    for fr, g in every_frame(s, tr):
        hx, hy = g['head']
        assert hx + 0.11 < WALL_X - 0.02, ('head in wall', fr)
        assert g['front_leg']['foot'][1][0] < WALL_X, ('toes in wall', fr)
        elbow = g['front_arm']['arm'][1]
        assert elbow[0] < WALL_X - 0.05, ('elbow in wall', fr)
    return s


# ------------------------------------------------------------------ lateral weight shift
def stand3d(pelvis, near_ankle, far_ankle, arms=None, trunk=2):
    return body(pelvis=pelvis, trunk=trunk,
                legs={'near': leg_ik(near_ankle, (1, 0, 0.06)), 'far': leg_ik(far_ankle, (1, 0, -0.06))},
                arms=arms or {'near': arm_fk(2, 9, abd=6), 'far': arm_fk(2, 9, abd=6)})


def counter_extra():
    x0, x1, z0, z1 = COUNTER
    return [(x, y, z) for x in (x0, x1) for y in (0.0, 0.91) for z in (z0, z1)]


def lateral_weight_shift():
    """Near-frontal view, feet wider than the hips, a counter within reach.
    The pelvis glides over one foot, back through the middle to the other
    foot and returns to the centre; feet stay flat."""
    cam = Camera(yaw=82, pitch=10)
    near_ankle, far_ankle = (0.0, ANKLE, 0.17), (0.0, ANKLE, -0.17)
    y = PEL_Y - 0.01

    def at(z):
        return stand3d((0.0, y - 0.012 * abs(z) / 0.13, z), near_ankle, far_ankle)

    center, near, far = at(0.0), at(0.13), at(-0.13)
    from build_home_exercise_animations import chain
    tr = Track()
    t = chain(tr, [(center, 0.6), (near, 1.3), (near, 0.7), (center, 1.1), (far, 1.1), (far, 0.7),
                   (center, 1.3), (center, 0.4)])
    s = scene3d('Transferência lateral de peso', cam, tr, counter_extra())
    floor_patch(s, cam, -0.8, 1.35, -1.15, 0.75)
    counter(s, cam)
    samples = add_figure(s, cam, tr)
    markers(s, ['start', 'shift_near', 'hold_near', 'back_to_center', 'shift_far', 'hold_far', 'return', 'rest'], t)
    check3d(s, cam, tr, samples, planted=[('near ankle', lambda g: g['near leg'][2], near_ankle),
                                          ('far ankle', lambda g: g['far leg'][2], far_ankle)])
    return s


# ------------------------------------------------------------------ single-leg stance
def single_leg_stance():
    """Diagonal view, far hand resting on a counter. Weight moves onto the
    far leg, the near foot lifts a little behind with the knee bent, holds
    with small natural sway, and is put back down."""
    cam = Camera(yaw=34, pitch=12)
    hand = (0.14, 0.918, -0.42)
    far_ankle = (0.0, ANKLE, -0.08)
    rest_near = (0.0, ANKLE, 0.08)
    lifted = (-0.13, ANKLE + 0.17, 0.08)
    rest_s, lift_s, hold_s, lower_s, tail = 0.6, 1.3, 3.0, 1.3, 0.6
    t1 = rest_s + lift_s
    t2 = t1 + hold_s
    t3 = t2 + lower_s
    duration = t3 + tail

    def at(t):
        u = smooth((t - rest_s) / lift_s) - smooth((t - t2) / lower_s)
        w = smooth((t - t1) / 0.5) * (1 - smooth((t - t2 + 0.5) / 0.5))  # sway envelope
        sway = (0.008 * math.sin(2 * math.pi * (t - t1) / 1.5) * w, 0.0, 0.01 * math.sin(2 * math.pi * (t - t1) / 3.0) * w)
        pelvis = add((0.0, PEL_Y, -0.045 * u), sway)
        foot = add(blend(rest_near, lifted, u), mul3(sway, u))
        toe = unit(blend((1.0, 0.0, 0.0), (1.0, -0.55, 0.0), u))
        return body(pelvis=pelvis, trunk=2 + 1.0 * math.sin(2 * math.pi * (t - t1) / 3.0) * w,
                    legs={'near': leg_ik(foot, toe, (1, 0, 0.1)), 'far': leg_ik(far_ankle, (1, 0, -0.06))},
                    arms={'near': arm_fk(2, 9, abd=8 + 3 * w * math.sin(2 * math.pi * (t - t1) / 1.5)),
                          'far': arm_ik(hand, (-0.4, -1.0, -0.1), local=False)})

    tr = Track()
    tr.add(0, duration, at)
    s = scene3d('Apoio unipodal com apoio', cam, tr, counter_extra())
    floor_patch(s, cam, -0.8, 1.35, -1.15, 0.7)
    counter(s, cam)
    samples = add_figure(s, cam, tr)
    markers(s, ['start', 'lift_foot', 'hold_balance', 'lower_foot', 'rest'], [0, rest_s, t1, t2, t3, duration])
    check3d(s, cam, tr, samples, planted=[('far hand', lambda g: g['far arm'][2], hand),
                                          ('far ankle', lambda g: g['far leg'][2], far_ankle)])
    for fr, g in samples:
        if t1 <= fr / FPS <= t2:
            assert min(q[1] for q in g['near foot']) > 0.12, ('foot too low while holding', fr)
    return s


def mul3(v, k):
    return tuple(c * k for c in v)


# ------------------------------------------------------------------ step-up
STEP_X0, STEP_X1, STEP_H = 0.2, 0.62, 0.17
ON_STEP = 0.38  # ankle x on the step


def walk_pose(st):
    """st: hip (x, y), trunk, feet as world (x, y, pitch), arm swing."""
    (hx, hy), trunk, a, b, swing = st['hip'], st['trunk'], st['a'], st['b'], st['swing']
    p = pose(hx, hy, 0.0, trunk, aa=(4 + swing, 14 + swing), ab=(4 - swing, 14 - swing))
    return with_(p, fa=(a[0] - hx, a[1], a[2]), fb=(b[0] - hx, b[1], b[2]))


def swing_foot(f0, f1, u, up=True, clearance=0.08):
    """Foot path that clears the step edge: going up it rises before moving
    forward, going down it moves back before descending."""
    if up:
        x = f0[0] + (f1[0] - f0[0]) * smooth((u - 0.2) / 0.8)
        y = f0[1] + (f1[1] - f0[1]) * smooth(u / 0.55) + clearance * math.sin(math.pi * u)
    else:
        x = f0[0] + (f1[0] - f0[0]) * smooth(u / 0.65)
        y = f0[1] + (f1[1] - f0[1]) * smooth((u - 0.45) / 0.55) + clearance * math.sin(math.pi * min(u / 0.7, 1))
    pitch = f0[2] + (f1[2] - f0[2]) * smooth(u)
    return (x, y, pitch)


def step_up():
    """Profile, a single step ahead. The near foot steps up, the body rises
    over it and the far foot joins; then the far foot steps back down,
    followed by the near foot."""
    s = Scene('Subida no degrau', -1.45, 2.25, -0.25, 7.0)
    s.floor()
    s.polygon('step side', [(STEP_X0, 0), (STEP_X1, 0), (STEP_X1, STEP_H), (STEP_X0, STEP_H)], 'prop-soft')
    s.line('step top', [(STEP_X0, STEP_H), (STEP_X1, STEP_H)], 'prop', 0.03)
    s.line('step front', [(STEP_X0, 0), (STEP_X0, STEP_H)], 'prop', 0.02)
    s.line('step back', [(STEP_X1, 0), (STEP_X1, STEP_H)], 'prop', 0.02)

    floor = (0.0, ANKLE, 0.0)
    top = (ON_STEP, STEP_H + ANKLE, 0.0)
    toes = (0.0, ANKLE + 0.07, -0.5)  # trailing foot pushing off from the toes
    S = lambda hip, trunk, a, b, swing=0.0: {'hip': hip, 'trunk': trunk, 'a': a, 'b': b, 'swing': swing}
    s0 = S((0.0, STAND_HIP), 3.0, floor, floor)
    s1 = S((0.05, STAND_HIP - 0.02), 8.0, top, floor, 8.0)
    s2 = S((0.22, STAND_HIP + 0.05), 10.0, top, toes, 4.0)
    s3 = S((ON_STEP, STAND_HIP + STEP_H), 3.0, top, top)
    s4 = S((0.17, STAND_HIP + 0.02), 6.0, top, floor, -6.0)
    s5 = s0
    segs = [  # (from, to, seconds, moving foot, up?)
        (s0, s0, 0.6, None, None),
        (s0, s1, 1.1, 'a', True),
        (s1, s2, 0.6, None, None),
        (s2, s3, 0.9, 'b', True),
        (s3, s3, 0.6, None, None),
        (s3, s4, 1.2, 'b', False),
        (s4, s5, 1.2, 'a', False),
        (s5, s5, 0.6, None, None),
    ]
    tr = Track()
    times = [0.0]
    t0 = 0.0
    for a, b, d, foot, up in segs:
        def fn(t, a=a, b=b, d=d, foot=foot, up=up, t0=t0):
            u = (t - t0) / d
            st = {k: blend(a[k], b[k], smooth(u)) for k in a}
            if foot:
                st[foot] = swing_foot(a[foot], b[foot], u, up)
            return walk_pose(st)
        tr.add(t0, t0 + d, fn)
        t0 += d
        times.append(t0)
    s.figure(tr)
    markers(s, ['start', 'near_foot_up', 'rise', 'far_foot_up', 'stand_on_step', 'far_foot_down',
                'near_foot_down', 'rest'], times)
    check2d(s, tr)
    for fr, g in every_frame(s, tr):  # feet never cut into the step
        for part in ('front_leg', 'back_leg'):
            for x, y in g[part]['foot']:
                if STEP_X0 - 0.03 < x < STEP_X1 + 0.03:
                    assert y > STEP_H - 0.005, ('foot in step', fr, part, x, y)
    return s


SCENES = {
    'standing_hip_abduction': standing_hip_abduction,
    'standing_knee_flexion': standing_knee_flexion,
    'mini_squat': mini_squat,
    'standing_marching': standing_marching,
    'wall_push_up': wall_push_up,
    'lateral_weight_shift': lateral_weight_shift,
    'single_leg_stance': single_leg_stance,
    'step_up': step_up,
}
