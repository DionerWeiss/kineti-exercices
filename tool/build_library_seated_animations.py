"""Seated batch of the expanded exercise library, authored on the same rig as
the home exercises and the library pilot.

Built by tool/build_catalog.py (see its docstring).

Every scene is one slow repetition per loop (start -> execution -> return),
has named step markers and passes the rig's geometric checks plus its own.
"""

import _rig  # noqa: F401  (puts the Kineti rig on sys.path)
import math

from build_hip_exercise_animations import chair as profile_chair
from build_home_exercise_animations import chain, check2d, markers, seated2d, seated3d, seated_scene
from figure3d import (IK_ERRORS, HALF_SHOULDERS, Camera, add, add_figure, arm_fk, arm_ik, check as check3d,
                      geometry, leg_fk, length, mul, sub, with_body)
from kineti_lottie import (FPS, GEOMETRY_WARNINGS, HALO, Scene, Track, ellipse, figure_geometry, fill, group,
                           path, sit_to_stand_poses, stroke, with_)

SEAT_TOP = 0.46        # chair seat height (figure3d.chair)
SEAT_HALF = 0.22       # chair seat half width, along Z
SEAT_X = (-0.25, 0.23)  # chair seat depth, along X


def hands_clear_of_seat(samples):
    """No hand ends up inside the chair seat volume."""
    for fr, g in samples:
        for side in ('near', 'far'):
            x, y, z = g[f'{side} arm'][2]
            inside = SEAT_X[0] < x < SEAT_X[1] and abs(z) < SEAT_HALF + 0.02 and y < SEAT_TOP + 0.02
            assert not inside, ('hand in seat', fr, side, (x, y, z))


# Hands hang beside the seat, lightly holding its edges.
SIDE_ARMS = {'near': arm_fk(-2, 6, abd=12), 'far': arm_fk(-2, 6, abd=12)}


# ------------------------------------------------------------------ marching
def seated_marching():
    """Sitting tall, hands holding the sides of the seat. One knee lifts a hand
    span, the foot comes back down, then the other side."""
    cam = Camera(yaw=34, pitch=12)
    rest = seated3d(trunk=0, arms=SIDE_ARMS)
    lifted = leg_fk(114, 112, abd=3)
    near_up = with_body(rest, legs={'near': lifted})
    far_up = with_body(rest, legs={'far': lifted})
    tr = Track()
    t = chain(tr, [(rest, 0.6), (near_up, 0.9), (near_up, 0.4), (rest, 0.9),
                   (far_up, 0.9), (far_up, 0.4), (rest, 0.9), (rest, 0.6)])
    s = seated_scene('Marcha sentada', cam, tr)
    samples = add_figure(s, cam, tr)
    markers(s, ['start', 'lift_right', 'hold_right', 'lower_right', 'lift_left', 'hold_left', 'lower_left',
                'rest'], t)
    check3d(s, cam, tr, samples)
    hands_clear_of_seat(samples)
    g0 = geometry(rest)
    lift = max(g['near leg'][2][1] for _, g in samples) - g0['near leg'][2][1]
    assert lift > 0.12, ('foot lift too small to read', lift)
    for fr, g in samples:  # thighs never sink into the seat
        for side in ('near', 'far'):
            assert g[f'{side} leg'][1][1] >= g0[f'{side} leg'][1][1] - 1e-9, ('thigh in seat', fr, side)
    return s


# ------------------------------------------------------------------ shoulder flexion
def seated_shoulder_flexion():
    """Sitting tall, both arms rise forward with the elbows straight until they
    point overhead, then lower slowly back to the sides."""
    cam = Camera(yaw=24, pitch=8)
    rest = seated3d(trunk=0, arms=SIDE_ARMS)
    up = with_body(rest, arms={'near': arm_fk(168, 172, abd=8), 'far': arm_fk(168, 172, abd=8)})
    tr = Track()
    t = chain(tr, [(rest, 0.6), (up, 2.0), (up, 0.6), (rest, 2.2), (rest, 0.6)])
    s = seated_scene('Flexão de ombros sentado', cam, tr)
    samples = add_figure(s, cam, tr)
    markers(s, ['start', 'raise_arms', 'hold', 'lower_arms', 'rest'], t)
    check3d(s, cam, tr, samples)
    hands_clear_of_seat(samples)
    for fr, g in samples:  # elbows stay straight
        for side in ('near', 'far'):
            sh, _, hand = g[f'{side} arm']
            assert length(sub(hand, sh)) > 0.55, ('elbow bent', fr, side)
    return s


# ------------------------------------------------------------------ shoulder abduction
def seated_shoulder_abduction():
    """Sitting tall, both arms rise out to the sides, elbows straight, a little
    above shoulder height, then lower slowly."""
    cam = Camera(yaw=64, pitch=10)
    rest = seated3d(trunk=0, arms=SIDE_ARMS)
    up = with_body(rest, arms={'near': arm_fk(-2, 2, abd=100), 'far': arm_fk(-2, 2, abd=100)})
    tr = Track()
    t = chain(tr, [(rest, 0.6), (up, 1.8), (up, 0.6), (rest, 2.2), (rest, 0.6)])
    s = seated_scene('Abdução de ombros sentado', cam, tr)
    samples = add_figure(s, cam, tr, girdle=True)
    markers(s, ['start', 'raise_arms', 'hold', 'lower_arms', 'rest'], t)
    check3d(s, cam, tr, samples)
    hands_clear_of_seat(samples)
    for fr, g in samples:
        for side in ('near', 'far'):
            sh, _, hand = g[f'{side} arm']
            assert length(sub(hand, sh)) > 0.55, ('elbow bent', fr, side)
    top = geometry(up)
    for side in ('near', 'far'):  # hands end above the shoulders
        assert top[f'{side} arm'][2][1] > top[f'{side} arm'][0][1], ('arms below shoulder height', side)
    return s


# ------------------------------------------------------------------ heel / toe raises
HEEL = (-0.035, -0.03)  # sole points of the profile foot, in the foot frame
TOE = (0.14, -0.04)


def rotated(q, a):
    return (q[0] * math.cos(a) - q[1] * math.sin(a), q[0] * math.sin(a) + q[1] * math.cos(a))


def foot_about(ankle0, pivot, pitch):
    """Ankle (x_local, y, pitch) that keeps a sole point fixed while the foot
    pitches about it (negative pitch lifts the heel, positive lifts the toes)."""
    world = (ankle0[0] + pivot[0], ankle0[1] + pivot[1])
    r = rotated(pivot, pitch)
    return (world[0] - r[0], world[1] - r[1], pitch)


def seated_heel_toe_raises():
    """Sitting, both feet flat. Heels rise with the balls of the feet on the
    floor and come down; then the toes rise with the heels down and come back."""
    s = Scene('Calcanhares e pontas dos pés', -1.35, 2.05, -0.25, 6.4)
    s.floor()
    profile_chair(s, 0.0)
    base = seated2d()
    ankle0 = base['fa']
    heels_up, toes_up = -0.62, 0.42

    def at_heels(u):
        f = foot_about(ankle0, TOE, heels_up * u)
        return with_(base, fa=f, fb=f)

    def at_toes(u):
        f = foot_about(ankle0, HEEL, toes_up * u)
        return with_(base, fa=f, fb=f)

    from kineti_lottie import smooth
    tr = Track()
    seg = [('start', 0.6), ('raise_heels', 1.0), ('hold_heels', 0.4), ('lower_heels', 1.0),
           ('raise_toes', 1.0), ('hold_toes', 0.4), ('lower_toes', 1.0), ('rest', 1.0)]
    t = [0.0]
    for _, d in seg:
        t.append(t[-1] + d)
    fns = [lambda x: base,
           lambda x: at_heels(smooth((x - t[1]) / (t[2] - t[1]))),
           lambda x: at_heels(1),
           lambda x: at_heels(1 - smooth((x - t[3]) / (t[4] - t[3]))),
           lambda x: at_toes(smooth((x - t[4]) / (t[5] - t[4]))),
           lambda x: at_toes(1),
           lambda x: at_toes(1 - smooth((x - t[6]) / (t[7] - t[6]))),
           lambda x: base]
    for i, fn in enumerate(fns):
        tr.add(t[i], t[i + 1], fn)
    s.figure(tr)
    markers(s, [name for name, _ in seg], t)
    check2d(s, tr)
    toe0 = add2(ankle0, TOE)
    heel0 = add2(ankle0, HEEL)
    for fr in range(s.frames + 1):
        x = fr / FPS
        g = figure_geometry(tr.at(x))
        heel, toe = g['front_leg']['foot']
        if t[1] <= x <= t[4]:  # balls of the feet stay on the floor
            assert abs(toe[1] - toe0[1]) < 1e-6, ('toes lifted', fr)
        if t[4] <= x <= t[7]:  # heels stay on the floor
            assert abs(heel[1] - heel0[1]) < 1e-6, ('heels lifted', fr)
    g_h = figure_geometry(at_heels(1))
    g_t = figure_geometry(at_toes(1))
    assert g_h['front_leg']['foot'][0][1] - heel0[1] > 0.07, 'heel lift too small to read'
    assert g_t['front_leg']['foot'][1][1] - toe0[1] > 0.06, 'toe lift too small to read'
    return s


def add2(a, b):
    return (a[0] + b[0], a[1] + b[1])


# ------------------------------------------------------------------ overhead press
DUMBBELL_HALF = 0.075


def press_arms(height, reach):
    """Hands in the thorax frame: `height` above the shoulder line, `reach`
    out from the midline; elbows point down and out."""
    return {side: arm_ik((height, 0.03, sign * reach), (-1.0, 0.0, sign * 0.6))
            for side, sign in (('near', 1), ('far', -1))}


def seated_overhead_press():
    """Sitting tall with a light dumbbell in each hand at shoulder height,
    elbows bent and out. The dumbbells press up until the elbows are almost
    straight, then come back down slowly."""
    cam = Camera(yaw=52, pitch=8)
    rest = seated3d(trunk=0, arms=press_arms(0.06, HALF_SHOULDERS + 0.27))
    up = with_body(rest, arms=press_arms(0.52, HALF_SHOULDERS + 0.075))
    tr = Track()
    t = chain(tr, [(rest, 0.8), (up, 1.4), (up, 0.6), (rest, 1.8), (rest, 0.8)])
    s = seated_scene('Desenvolvimento com halteres', cam, tr)

    def ends(g, side):
        (_, _, _), (_, _, Lt) = g['frames']
        hand = g[f'{side} arm'][2]
        return add(hand, mul(Lt, -DUMBBELL_HALF)), add(hand, mul(Lt, DUMBBELL_HALF))

    def dumbbells(samples):
        for side in ('far', 'near'):
            bar = [(fr, [cam.px(s, q) for q in ends(g, side)]) for fr, g in samples]
            s.layer('dumbbell halo', [group('halo', [path(keys=bar), stroke('stage', s.m(0.075 + 2 * HALO), s.palette)])])
            s.layer('dumbbell bar', [group('bar', [path(keys=bar), stroke('prop', s.m(0.03), s.palette)])])
            for i in (0, 1):
                keys = [(fr, cam.px(s, ends(g, side)[i])) for fr, g in samples]
                d = round(s.m(0.075), 1)
                s.layer('dumbbell plate', [group('plate', [ellipse(size=(d, d), keys=keys), fill('prop', s.palette)])])

    samples = add_figure(s, cam, tr, girdle=True, after_arms=dumbbells)
    markers(s, ['start', 'press_up', 'hold', 'lower', 'rest'], t)
    check3d(s, cam, tr, samples)
    margin = 6 + s.m(0.0375)
    for fr, g in samples:
        for side in ('near', 'far'):
            for q in ends(g, side):  # plates inside the frame
                x, y = cam.px(s, q)
                assert margin < x < s.w - margin and margin < y < s.h - margin, ('dumbbell out of frame', fr)
            hand = g[f'{side} arm'][2]  # dumbbells clear the head
            assert length(sub(hand, g['head'])) > 0.11 + DUMBBELL_HALF, ('dumbbell in head', fr, side)
    g_up = geometry(up)
    for side in ('near', 'far'):
        sh, _, hand = g_up[f'{side} arm']
        assert length(sub(hand, sh)) > 0.5, ('press not extended', side)
    return s


# ------------------------------------------------------------------ sit to stand
def sit_to_stand_exercise():
    """Arms crossed on the chest, one slow stand-up: lean forward, rise to full
    standing, pause, then sit back down under control."""
    s = Scene('Sentar e levantar', -1.2, 2.2, -0.25, 7.0)
    s.floor()
    s.chair()
    crossed = (16, 196)
    seated, lean, lift, stand = [with_(p, aa=crossed, ab=crossed) for p in sit_to_stand_poses(0.0, 0.44)]
    tr = Track()
    t = tr.hold(0, 0.8, seated)
    t1 = tr.keys(t, [seated, lean, lift, stand], [0.6, 0.7, 0.9])
    t2 = tr.hold(t1, t1 + 0.8, stand)
    t3 = tr.keys(t2, [stand, lift, lean, seated], [0.9, 0.8, 0.7])
    tr.hold(t3, 7.0, seated)
    s.figure(tr)
    markers(s, ['start', 'stand_up', 'stand', 'sit_down', 'rest'], [0, t, t1, t2, t3, 7.0])
    check2d(s, tr)
    for fr in range(s.frames + 1):  # feet stay planted
        g = figure_geometry(tr.at(fr / FPS))
        for part in ('front_leg', 'back_leg'):
            assert abs(g[part]['leg'][2][0] - 0.44) < 1e-6, ('foot slid', fr)
    return s


SCENES = {
    'seated_marching': seated_marching,
    'seated_shoulder_flexion': seated_shoulder_flexion,
    'seated_shoulder_abduction': seated_shoulder_abduction,
    'seated_heel_toe_raises': seated_heel_toe_raises,
    'seated_overhead_press': seated_overhead_press,
    'sit_to_stand_exercise': sit_to_stand_exercise,
}
