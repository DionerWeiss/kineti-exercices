"""Pilot of the expanded exercise library: three generic exercises authored on
the same rig as the home exercises, one per scene type (lying, standing,
seated), to size the effort of a larger catalogue.

Built by tool/build_catalog.py (see its docstring).

Every scene is one slow repetition per loop (start -> execution -> return),
has named step markers and passes the rig's geometric checks plus its own.
"""

import _rig  # noqa: F401  (puts the Kineti rig on sys.path)
import math

from build_home_exercise_animations import MAT, chain, hook_lying, markers, mat, scene3d, seated3d, seated_scene
from figure3d import (IK_ERRORS, Camera, add, add_figure, arm_ik, body, check as check3d, floor_patch,
                      geometry, leg_fk, leg_ik, length, mul, sub, unit, with_body)
from kineti_lottie import ANKLE, FPS, GEOMETRY_WARNINGS, STAND_HIP, W_TORSO, Track, smooth



def ramp(t, t0, t1):
    """0 before t0, eased to 1 at t1."""
    return smooth(min(max((t - t0) / (t1 - t0), 0.0), 1.0))


# ------------------------------------------------------------------ crunch
def abdominal_crunches():
    """Supine, knees bent, fingertips behind the head and elbows out. The
    upper trunk curls until the shoulder blades clear the mat while the lower
    back stays down; the chin tucks slightly, eyes toward the knees."""
    cam = Camera(yaw=16, pitch=26)
    hands = {'near': arm_ik((0.2, -0.035, 0.07), (0.1, 0.25, 1.0)),
             'far': arm_ik((0.2, -0.035, -0.07), (0.1, 0.25, -1.0))}
    down = hook_lying(arms=hands, nod=6)
    up = with_body(down, curl=34, nod=18)
    tr = Track()
    t = chain(tr, [(down, 0.8), (up, 1.4), (up, 0.8), (down, 1.8), (down, 0.8)])
    s = scene3d('Abdominal (crunch)', cam, tr, [(-1.05, 0, 0.42), (0.95, 0, -0.42)])
    s.floor()
    mat(s, cam)
    samples = add_figure(s, cam, tr, shadow=False)
    markers(s, ['start', 'curl_up', 'hold', 'lower', 'rest'], t)
    check3d(s, cam, tr, samples, floor=False)
    lumbar0 = geometry(down)['torso'][1]
    for fr, g in samples:
        hip, lumbar, shoulder = g['torso']
        assert length(sub(lumbar, lumbar0)) < 1e-9, ('lower back moved', fr)
        assert hip[1] - W_TORSO / 2 >= MAT - 1e-9, ('pelvis in mat', fr)
        assert shoulder[1] - W_TORSO / 2 >= MAT - 1e-9, ('shoulders in mat', fr)
        for side in ('near', 'far'):
            assert min(q[1] for q in g[f'{side} foot']) - 0.075 / 2 > MAT - 0.006, ('foot in mat', fr)
    return s


# ------------------------------------------------------------------ arm circles
REACH = 0.555  # hand to shoulder joint with the elbow almost straight


def arm_circle_hand(side, abduction, phase, radius):
    """Hand in the thorax frame (U, A, L from the shoulder centre): the arm
    abducted by `abduction` degrees, the hand drawing a circle of `radius`
    around that line. phase 0 is the top; it then moves forward."""
    sign = 1 if side == 'near' else -1
    a = math.radians(abduction)
    axis = (-math.cos(a), 0.0, sign * math.sin(a))        # shoulder -> hand
    up = (math.sin(a), 0.0, sign * math.cos(a))           # perpendicular, headward
    fwd = (0.0, 1.0, 0.0)
    c, s_ = math.cos(math.radians(phase)), math.sin(math.radians(phase))
    hand = add((0.0, 0.0, sign * 0.135), mul(axis, REACH), mul(up, radius * c), mul(fwd, radius * s_))
    return arm_ik(hand, (-0.2, -1.0, sign * 0.15))


def arm_circles():
    """Standing tall, both arms rise sideways to shoulder height, draw small
    forward circles and come back down."""
    rest_s, raise_s, circles, per, lower_s, tail = 0.6, 1.2, 4, 1.1, 1.2, 0.6
    t1 = rest_s + raise_s
    t2 = t1 + circles * per
    t3 = t2 + lower_s
    duration = t3 + tail
    feet = {'near': leg_ik((0.0, ANKLE, 0.09), (1, 0, 0.05)), 'far': leg_ik((0.0, ANKLE, -0.09), (1, 0, -0.05))}

    def at(t):
        abd = 6 + 84 * (ramp(t, rest_s, t1) - ramp(t, t2, t3))
        phase = 360 * circles * min(max((t - t1) / (t2 - t1), 0.0), 1.0)
        r = 0.07 * ramp(t, t1, t1 + 0.5) * (1 - ramp(t, t2 - 0.5, t2))
        return body(pelvis=(0.0, STAND_HIP - 0.015, 0.0), trunk=2, legs=feet,
                    arms={side: arm_circle_hand(side, abd, phase, r) for side in ('near', 'far')})

    tr = Track()
    tr.add(0, duration, at)
    cam = Camera(yaw=62, pitch=10)
    s = scene3d('Círculos com os braços', cam, tr, width=3.0)
    floor_patch(s, cam, -0.7, 0.7, -0.9, 0.9)
    samples = add_figure(s, cam, tr)
    markers(s, ['start', 'raise_arms', 'circles', 'lower_arms', 'rest'], [0, rest_s, t1, t2, t3, duration])
    planted = [(f'{side} ankle', lambda g, side=side: g[f'{side} leg'][2], feet[side]['ankle'])
               for side in ('near', 'far')]
    check3d(s, cam, tr, samples, planted=planted)
    for fr, g in samples:  # elbows stay nearly straight: the circle comes from the shoulder
        for side in ('near', 'far'):
            sh, _, hand = g[f'{side} arm']
            assert length(sub(hand, sh)) > 0.5, ('elbow bent', fr, side)
    return s


# ------------------------------------------------------------------ ankle circles
def ankle_circles():
    """Seated, back against the chair. One foot lifts a little off the floor
    and the ankle draws slow circles, two each way, with the knee and thigh
    still; then the foot returns to the floor."""
    cam = Camera(yaw=44, pitch=18)
    rest = seated3d(trunk=0)
    lifted = seated3d(trunk=0, legs={'near': leg_fk(90, 58, abd=3)})
    g0, g1 = geometry(rest), geometry(lifted)
    floor_ankle, air_ankle = g0['near leg'][2], g1['near leg'][2]
    toe0 = g1['near toe axis']
    shin = unit(sub(g1['near leg'][2], g1['near leg'][1]))
    lateral = (0.0, 0.0, 1.0)
    sagittal = unit(sub(shin, mul(toe0, sum(a * b for a, b in zip(shin, toe0)))))  # toe down direction
    knee_hint = (1.0, 0.0, 0.05)

    def toe(phase, r):
        a = math.radians(phase)
        return unit(add(toe0, mul(lateral, r * math.sin(a)), mul(sagittal, r * math.cos(a))))

    rest_s, lift_s, per, lower_s, tail = 0.6, 0.9, 1.25, 0.9, 0.5
    t1 = rest_s + lift_s
    t2 = t1 + 2 * per          # two circles one way
    t3 = t2 + 2 * per          # two circles the other way
    t4 = t3 + lower_s
    duration = t4 + tail
    flat = (1.0, 0.0, 0.0)
    far_ankle = g0['far leg'][2]

    def at(t):
        if t1 <= t <= t3:  # foot in the air, circling; radius eases in and out
            if t < t2:
                phase = 720 * (t - t1) / (t2 - t1)
            else:
                phase = 720 - 720 * (t - t2) / (t3 - t2)
            r = 0.55 * ramp(t, t1, t1 + 0.4) * (1 - ramp(t, t3 - 0.4, t3))
            ankle, direction = air_ankle, toe(phase, r)
        else:  # lifting or lowering the foot
            u = ramp(t, rest_s, t1) - ramp(t, t3, t4)
            ankle = add(mul(floor_ankle, 1 - u), mul(air_ankle, u))
            direction = unit(add(mul(flat, 1 - u), mul(toe0, u)))
        return with_body(rest, legs={'near': leg_ik(ankle, direction, knee_hint),
                                     'far': leg_ik(far_ankle, flat, knee_hint)})

    tr = Track()
    tr.add(0, duration, at)
    s = seated_scene('Círculos com o tornozelo', cam, tr)
    samples = add_figure(s, cam, tr)
    markers(s, ['start', 'lift_foot', 'circle_out', 'circle_in', 'lower_foot', 'rest'],
            [0, rest_s, t1, t2, t3, t4, duration])
    far_ankle = geometry(rest)['far leg'][2]
    check3d(s, cam, tr, samples, planted=[('far ankle', lambda g: g['far leg'][2], far_ankle)])
    for fr, g in samples:
        if t1 <= fr / FPS <= t3:  # shin is still while the ankle circles
            assert length(sub(g['near leg'][2], air_ankle)) < 1e-6, ('shin moved', fr)
            assert length(sub(g['near leg'][1], g1['near leg'][1])) < 2e-3, ('knee moved', fr)
    return s


SCENES = {
    'abdominal_crunches': abdominal_crunches,
    'arm_circles': arm_circles,
    'ankle_circles': ankle_circles,
}
