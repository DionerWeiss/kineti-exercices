"""Floor exercises of the expanded library (lote 3): prone, quadruped and
side-lying, all on the mat.

Built by tool/build_catalog.py (see its docstring).

Poses use figure3d: pitch=+90 lays the trunk face down (head towards +X),
pitch=-90 with roll=-90 lies on the near side with the chest towards +Z.
Contacts with the mat (forearms, hands, knees, feet) are solved with
world-space IK so they stay planted. Every scene is one slow repetition per
loop, has named step markers, passes check3d and asserts that no segment
sinks into the mat.
"""

import _rig  # noqa: F401  (puts the Kineti rig on sys.path)
import math

from build_home_exercise_animations import MAT, markers, mat, scene3d
from figure3d import (Camera, add, add_figure, arm_ik, blend, body, check as check3d, floor_patch, geometry,
                      leg_fk, leg_ik, length, mul, rotate, sub, unit, with_body)
from kineti_lottie import (HEAD_R, HIP_Z, L_FORE, L_SHIN, L_THIGH, L_UP, W_ARM, W_FOOT, W_LEG, W_TORSO, Track,
                           smooth)

ON_MAT_ARM = MAT + W_ARM / 2    # centre of a forearm or hand resting on the mat
ON_MAT_LEG = MAT + W_LEG / 2    # centre of a knee or shin resting on the mat
TOL = 0.006                     # same contact tolerance as the supine scenes
SIDES = (('near', 1), ('far', -1))


# ------------------------------------------------------------------ shared
def timeline(track, at, steps, ease=smooth):
    """steps: [(value, seconds)] with value a number or tuple; the first value
    is held, each next one is reached from the previous with easing. The pose
    is at(value). Returns the boundary times."""
    times, t, prev = [0.0], 0.0, steps[0][0]
    for i, (v, d) in enumerate(steps):
        if i == 0 or v == prev:
            track.add(t, t + d, lambda x, v=v: at(v))
        else:
            track.add(t, t + d, lambda x, a=prev, b=v, t0=t, d=d: at(blend(a, b, ease((x - t0) / d))))
        t += d
        times.append(t)
        prev = v
    return times


def above_mat(samples, skip=()):
    """No drawn segment dips into the mat (stroke half-widths included)."""
    widths = {'torso': W_TORSO, 'near leg': W_LEG, 'far leg': W_LEG, 'near foot': W_FOOT, 'far foot': W_FOOT,
              'near arm': W_ARM, 'far arm': W_ARM}
    for fr, g in samples:
        for key, w in widths.items():
            if key in skip:
                continue
            low = min(q[1] for q in g[key]) - w / 2
            assert low >= MAT - TOL, ('sinks into the mat', key, fr, round(low - MAT, 4))
        assert g['head'][1] - HEAD_R >= MAT - TOL, ('head in the mat', fr)


def joints(p):
    """Shoulder and hip joints of pose p (they do not depend on the limbs)."""
    g = geometry(p)
    return ({s: g[f'{s} arm'][0] for s, _ in SIDES}, {s: g[f'{s} leg'][0] for s, _ in SIDES})


def mat_box(x0, x1, z):
    return [(x, y, zz) for x in (x0, x1) for y in (0.0, MAT) for zz in (-z, z)]


# ------------------------------------------------------------------ prone
PRONE_Y = MAT + W_TORSO / 2 + 0.005
PRONE_HIP = math.degrees(math.asin((PRONE_Y - ON_MAT_LEG - 0.002) / L_THIGH))  # thighs resting on the mat


def prone_leg(lift=0.0):
    """Leg resting on the mat face down (shin level, toes pointed back); lift
    0..1 raises the straight leg by hip extension, about 11 degrees: enough to
    read, small enough that the pelvis and lower back stay down."""
    return leg_fk(hip=PRONE_HIP + (-6 - PRONE_HIP) * lift, knee=PRONE_HIP * (1 - lift) + 1.0 * lift, plantar=78)


def prone(**changes):
    p = body(pelvis=(0.0, PRONE_Y, 0.0), pitch=90, trunk=0,
             legs={'near': prone_leg(), 'far': prone_leg()})
    return with_body(p, **changes)


def forearm_on_mat(sh, sign, spread, medial):
    """Elbow on the mat at upper-arm length from the shoulder, `spread`
    degrees from straight ahead towards the side, forearm on the mat turned
    `medial` degrees inwards. Returns an arm_ik that lands exactly there."""
    r = math.sqrt(max(L_UP ** 2 - (sh[1] - ON_MAT_ARM) ** 2, 0.0))
    a = math.radians(spread)
    elbow = (sh[0] + r * math.cos(a), ON_MAT_ARM, sh[2] + sign * r * math.sin(a))
    b = math.radians(-medial)
    hand = (elbow[0] + L_FORE * math.cos(b), ON_MAT_ARM, elbow[2] + sign * L_FORE * math.sin(b))
    mid = mul(add(sh, hand), 0.5)
    return arm_ik(hand, sub(elbow, mid), local=False), elbow


def prone_press_up_on_elbows():
    """Face down, forearms on the mat beside the head. The chest rises onto
    the forearms, the elbows come in under the shoulders and the pelvis stays
    on the mat; hold, then lower slowly."""
    elbows = {}

    def at(u):
        p = prone(trunk=-18 * u, curl=-26 * u, nod=22 * u)
        shoulders, _ = joints(p)
        arms = {}
        for side, sign in SIDES:
            arms[side], elbows[side] = forearm_on_mat(shoulders[side], sign, 62 * (1 - u), 40 - 28 * u)
        return with_body(p, arms=arms)

    tr = Track()
    t = timeline(tr, at, [(0.0, 0.7), (1.0, 1.7), (1.0, 1.2), (0.0, 1.8), (0.0, 0.6)])
    cam = Camera(yaw=18, pitch=20)
    extra = mat_box(-1.1, 0.95, 0.5)
    s = scene3d('Extensão de tronco apoiado nos cotovelos', cam, tr, extra)
    floor_patch(s, cam, -1.3, 1.15, -0.75, 0.75)
    mat(s, cam, -1.1, 0.95, 0.5)
    samples = add_figure(s, cam, tr, shadow=False)
    markers(s, ['start', 'press_up', 'hold', 'lower', 'rest'], t)
    check3d(s, cam, tr, samples, floor=False)
    above_mat(samples)
    hip0 = geometry(at(0.0))['torso'][0]
    for fr, g in samples:
        assert length(sub(g['torso'][0], hip0)) < 1e-9, ('pelvis moved', fr)
        for side, _ in SIDES:
            _, elbow, hand = g[f'{side} arm']
            assert abs(elbow[1] - ON_MAT_ARM) < 2e-3 and abs(hand[1] - ON_MAT_ARM) < 2e-3, ('forearm left the mat', fr)
    top = geometry(at(1.0))
    for side, _ in SIDES:  # elbows end under the shoulders
        sh, elbow, _ = top[f'{side} arm']
        assert math.hypot(elbow[0] - sh[0], elbow[2] - sh[2]) < 0.06, ('elbow not under the shoulder', side)
    return s


def prone_hip_extension():
    """Face down, forehead resting on the stacked hands. One leg, knee
    straight, lifts a little off the mat by hip extension and lowers; the
    pelvis stays down."""
    rest = prone(nod=-12)
    shoulders, _ = joints(rest)
    arms = {}
    for side, sign in SIDES:  # elbows on the mat out to the side, hands meeting under the forehead
        sh = shoulders[side]
        r = math.sqrt(L_UP ** 2 - (sh[1] - ON_MAT_ARM) ** 2)
        spread = 35
        elbow_z = abs(sh[2]) + r * math.sin(math.radians(spread))
        medial = math.degrees(math.asin((elbow_z - 0.04) / L_FORE))
        arms[side], _ = forearm_on_mat(sh, sign, spread, medial)
    rest = with_body(rest, arms=arms)

    def at(u):
        return with_body(rest, legs={'near': prone_leg(u)})

    tr = Track()
    t = timeline(tr, at, [(0.0, 0.8), (1.0, 1.4), (1.0, 1.2), (0.0, 1.8), (0.0, 0.8)])
    cam = Camera(yaw=14, pitch=22)
    extra = mat_box(-1.15, 0.95, 0.42)
    s = scene3d('Extensão de quadril em decúbito ventral', cam, tr, extra)
    floor_patch(s, cam, -1.35, 1.15, -0.7, 0.7)
    mat(s, cam, -1.15, 0.95, 0.42)
    samples = add_figure(s, cam, tr, shadow=False)
    markers(s, ['start', 'lift_leg', 'hold', 'lower_leg', 'rest'], t)
    hands = {side: geometry(rest)[f'{side} arm'][2] for side, _ in SIDES}
    check3d(s, cam, tr, samples, floor=False,
            planted=[(f'{side} hand', lambda g, side=side: g[f'{side} arm'][2], hands[side]) for side, _ in SIDES])
    above_mat(samples)
    g0 = geometry(rest)
    for fr, g in samples:
        assert g['torso'] == g0['torso'] and g['far leg'] == g0['far leg'], ('only the near leg moves', fr)
    lifted = geometry(at(1.0))['near leg'][2][1] - g0['near leg'][2][1]
    assert 0.12 < lifted < 0.17, ('lift outside a small, readable range', lifted)
    return s


# ------------------------------------------------------------------ quadruped
KNEE_Y = ON_MAT_LEG
QUAD_HIP_Y = KNEE_Y + L_THIGH                    # thighs vertical
QUAD_REACH = 0.558                               # hand to shoulder, elbow just soft
QUAD_PITCH = 90 - math.degrees(math.asin((ON_MAT_ARM + QUAD_REACH - QUAD_HIP_Y) / 0.42))


def quadruped(**changes):
    """Hands under the shoulders, knees under the hips, shins and insteps on
    the mat. Returns the pose and its planted points."""
    p = body(pelvis=(0.0, QUAD_HIP_Y, 0.0), pitch=QUAD_PITCH, trunk=0, nod=8)
    p = with_body(p, **changes)
    shoulders, hips = joints(p)
    hands = {s: (sh[0], ON_MAT_ARM, sh[2]) for s, sh in shoulders.items()}
    knees = {s: (h[0], KNEE_Y, h[2]) for s, h in hips.items()}
    ankles = {s: (k[0] - L_SHIN, KNEE_Y, k[2]) for s, k in knees.items()}
    p = with_body(p, arms={s: arm_ik(hands[s], (-1.0, 0.0, 0.0), local=False) for s in hands},
                  legs={s: leg_ik(ankles[s], (-1.0, 0.12, 0.0), (0.7, -0.7, 0.0)) for s in ankles})
    return p, hands, knees


def quad_mat(s, cam):
    floor_patch(s, cam, -1.25, 1.05, -0.7, 0.7)
    mat(s, cam, -1.05, 0.85, 0.42)


def bird_dog():
    """On hands and knees, back level. One arm reaches forward and the
    opposite leg reaches back to the horizontal, hold, return; then the other
    pair."""
    base, hands, knees = quadruped()
    shoulders, hips = joints(base)
    reach_arm = {s: (arm_ik(add(shoulders[s], (QUAD_REACH, 0.0, 0.0)), (0.0, -1.0, 0.0), local=False))
                 for s in shoulders}
    reach_leg = {s: leg_ik(add(hips[s], (-(L_THIGH + L_SHIN - 0.01), 0.0, 0.0)), (-1.0, -0.2, 0.0), (0.0, -1.0, 0.0))
                 for s in hips}

    def at(v):
        a, b = v  # a: near arm + far leg, b: far arm + near leg
        return with_body(base,
                         arms={'near': blend(base['arms']['near'], reach_arm['near'], a),
                               'far': blend(base['arms']['far'], reach_arm['far'], b)},
                         legs={'far': blend(base['legs']['far'], reach_leg['far'], a),
                               'near': blend(base['legs']['near'], reach_leg['near'], b)})

    tr = Track()
    t = timeline(tr, at, [((0.0, 0.0), 0.6), ((1.0, 0.0), 1.2), ((1.0, 0.0), 0.8), ((0.0, 0.0), 1.0),
                          ((0.0, 1.0), 1.2), ((0.0, 1.0), 0.8), ((0.0, 0.0), 1.0), ((0.0, 0.0), 0.4)])
    cam = Camera(yaw=14, pitch=14)
    s = scene3d('Quatro apoios com braço e perna alternados', cam, tr, mat_box(-1.05, 0.85, 0.42))
    quad_mat(s, cam)
    samples = add_figure(s, cam, tr, shadow=False)
    markers(s, ['start', 'reach_first_pair', 'hold_first', 'return_first', 'reach_second_pair', 'hold_second',
                'return_second', 'rest'], t)
    check3d(s, cam, tr, samples, floor=False)
    above_mat(samples)
    g0 = geometry(base)
    for fr, g in samples:
        assert g['torso'] == g0['torso'], ('trunk moved', fr)
        for side, _ in SIDES:  # a support limb never leaves its spot
            arm_up = length(sub(g[f'{side} arm'][2], hands[side])) > 2e-3
            leg_up = length(sub(g[f'{side} leg'][1], knees[side])) > 2e-3
            other = 'far' if side == 'near' else 'near'
            if arm_up:  # its diagonal partner is the other-side leg; the same-side knee must hold
                assert length(sub(g[f'{side} leg'][1], knees[side])) < 2e-3, ('same-side knee slid', fr)
                assert length(sub(g[f'{other} arm'][2], hands[other])) < 2e-3, ('other hand slid', fr)
            if leg_up:
                assert length(sub(g[f'{other} leg'][1], knees[other])) < 2e-3, ('other knee slid', fr)
    for side in ('near', 'far'):  # the reaching limbs get to the horizontal
        g = geometry(at((1.0, 0.0) if side == 'near' else (0.0, 1.0)))
        sh, _, hand = g[f'{side} arm']
        assert abs(hand[1] - sh[1]) < 0.02, ('arm not level', side)
        other = 'far' if side == 'near' else 'near'
        hip, _, ankle = g[f'{other} leg']
        assert abs(ankle[1] - hip[1]) < 0.02, ('leg not level', other)
    return s


def cat_camel():
    """On hands and knees. The back rounds up with the head dropping, passes
    through neutral and sags gently with the head lifting, then returns;
    hands and knees stay where they are."""
    base, hands, knees = quadruped()
    arms, legs = base['arms'], base['legs']

    def at(v):
        lordosis, nod = v
        return with_body(base, lordosis=lordosis, nod=nod, arms=arms, legs=legs)

    neutral, cat, cow = (0.0, 8.0), (-0.085, 42.0), (0.095, -24.0)
    tr = Track()
    t = timeline(tr, at, [(neutral, 0.6), (cat, 1.5), (cat, 0.8), (neutral, 1.1), (cow, 1.1), (cow, 0.8),
                          (neutral, 1.3), (neutral, 0.4)])
    cam = Camera(yaw=0, pitch=10)
    s = scene3d('Gato-camelo', cam, tr, mat_box(-1.05, 0.85, 0.42))
    quad_mat(s, cam)
    samples = add_figure(s, cam, tr, shadow=False)
    markers(s, ['start', 'round_back', 'hold_round', 'to_neutral', 'sag_back', 'hold_sag', 'return', 'rest'], t)
    planted = [(f'{s_} hand', lambda g, s_=s_: g[f'{s_} arm'][2], hands[s_]) for s_, _ in SIDES]
    planted += [(f'{s_} knee', lambda g, s_=s_: g[f'{s_} leg'][1], knees[s_]) for s_, _ in SIDES]
    check3d(s, cam, tr, samples, floor=False, planted=planted)
    above_mat(samples)
    g0 = geometry(base)
    hump = geometry(at(cat))['torso'][1][1] - g0['torso'][1][1]
    sag = g0['torso'][1][1] - geometry(at(cow))['torso'][1][1]
    assert hump > 0.07 and sag > 0.045, ('spine motion too small to read', hump, sag)
    return s


# ------------------------------------------------------------------ side-lying
SIDE_Y = MAT + W_LEG / 2 + HIP_Z   # lower thigh resting on the mat
SIDE_TWIST = -40                    # top shoulder rolls forward, lower shoulder clears the mat


def side_lying(**changes):
    """Lying on the near side, chest towards +Z, head towards -X, the lower
    arm stretched under the head as a pillow."""
    p = body(pelvis=(0.0, SIDE_Y, 0.0), pitch=-90, roll=-90, trunk=0, twist=SIDE_TWIST)
    p = with_body(p, **changes)
    shoulders, _ = joints(p)
    sh = shoulders['near']
    pillow = arm_ik((sh[0] - 0.53, ON_MAT_ARM + 0.003, sh[2] + 0.13), (0.0, 0.25, 1.0), local=False)
    return with_body(p, arms={'near': pillow})


def clam_legs(open_deg, base):
    """Lower leg: hips and knees bent. Upper leg starts stacked on it (feet
    together) and opens by turning the knee about the hip-ankle line."""
    g = geometry(base)
    hip_top = g['far leg'][0]
    knee_low, ankle_low = g['near leg'][1], g['near leg'][2]
    up = (0.0, W_LEG + 0.004, 0.0)
    knee_top, ankle_top = add(knee_low, up), add(ankle_low, up)
    axis = unit(sub(ankle_top, hip_top))
    mid = add(hip_top, mul(axis, (L_THIGH ** 2 - L_SHIN ** 2 + length(sub(ankle_top, hip_top)) ** 2)
                       / (2 * length(sub(ankle_top, hip_top)))))
    hint = rotate(unit(sub(knee_top, mid)), axis, open_deg)
    return leg_ik(ankle_top, g['near toe axis'], hint)


def side_lying_clamshell():
    """Lying on the side, hips and knees bent, feet together, head on the
    lower arm and the upper hand on the mat in front. The upper knee opens
    like a shell, the feet stay together, and closes slowly."""
    p = side_lying(legs={'near': leg_fk(hip=45, knee=90, plantar=5), 'far': leg_fk(hip=45, knee=90, plantar=5)})
    shoulders, _ = joints(p)
    sh = shoulders['far']
    p = with_body(p, arms={'far': arm_ik((sh[0] + 0.12, ON_MAT_ARM + 0.003, sh[2] + 0.26), (0.2, 0.7, 0.6),
                                         local=False)})
    sign = 1 if geometry(with_body(p, legs={'far': clam_legs(10, p)}))['far leg'][1][1] > \
        geometry(with_body(p, legs={'far': clam_legs(0, p)}))['far leg'][1][1] else -1

    def at(u):
        return with_body(p, legs={'far': clam_legs(sign * 42 * u, p)})

    tr = Track()
    t = timeline(tr, at, [(0.0, 0.8), (1.0, 1.4), (1.0, 1.0), (0.0, 1.8), (0.0, 0.8)])
    cam = Camera(yaw=6, pitch=14)
    extra = mat_box(-1.15, 0.95, 0.5)
    s = scene3d('Concha deitado de lado', cam, tr, extra)
    floor_patch(s, cam, -1.35, 1.15, -0.8, 0.8)
    mat(s, cam, -1.15, 0.95, 0.5)
    samples = add_figure(s, cam, tr, front=('far',), shadow=False)
    markers(s, ['start', 'open_knee', 'hold', 'close_knee', 'rest'], t)
    hands = {side: geometry(at(0.0))[f'{side} arm'][2] for side, _ in SIDES}
    ankle_top = geometry(at(0.0))['far leg'][2]
    planted = [(f'{side} hand', lambda g, side=side: g[f'{side} arm'][2], hands[side]) for side, _ in SIDES]
    planted.append(('upper ankle', lambda g: g['far leg'][2], ankle_top))
    check3d(s, cam, tr, samples, floor=False, planted=planted)
    above_mat(samples)
    g0, g1 = geometry(at(0.0)), geometry(at(1.0))
    assert g1['far leg'][1][1] - g0['far leg'][1][1] > 0.15, 'knee opening too small to read'
    for fr, g in samples:
        assert g['near leg'] == g0['near leg'] and g['torso'] == g0['torso'], ('only the upper leg moves', fr)
    return s


def side_lying_hip_abduction():
    """Lying on the side, lower knee bent for stability, upper hand resting
    on the hip. The upper leg, straight and in line with the trunk, lifts
    and lowers slowly."""
    p = side_lying(legs={'near': leg_fk(hip=42, knee=85, plantar=5), 'far': leg_fk(hip=-4, knee=0, abd=-8)})
    shoulders, hips = joints(p)
    on_hip = (hips['far'][0] - 0.12, SIDE_Y + W_TORSO / 2 + W_ARM / 2, 0.0)  # hand resting on the waist
    p = with_body(p, arms={'far': arm_ik(on_hip, (0.0, 1.0, -0.4), local=False)})

    def at(u):
        return with_body(p, legs={'far': leg_fk(hip=-4, knee=0, abd=-8 + 36 * u)})

    tr = Track()
    t = timeline(tr, at, [(0.0, 0.8), (1.0, 1.4), (1.0, 1.0), (0.0, 1.8), (0.0, 0.8)])
    cam = Camera(yaw=180, pitch=26)
    extra = mat_box(-1.15, 1.05, 0.45)
    s = scene3d('Abdução de quadril deitado de lado', cam, tr, extra)
    floor_patch(s, cam, -1.35, 1.25, -0.75, 0.75)
    mat(s, cam, -1.15, 1.05, 0.45)
    samples = add_figure(s, cam, tr, front=('far',), shadow=False)
    markers(s, ['start', 'lift_leg', 'hold', 'lower_leg', 'rest'], t)
    hands = {side: geometry(p)[f'{side} arm'][2] for side, _ in SIDES}
    check3d(s, cam, tr, samples, floor=False,
            planted=[(f'{side} hand', lambda g, side=side: g[f'{side} arm'][2], hands[side]) for side, _ in SIDES])
    above_mat(samples)
    g0, g1 = geometry(at(0.0)), geometry(at(1.0))
    assert g1['far leg'][2][1] - g0['far leg'][2][1] > 0.3, 'lift too small to read'
    for fr, g in samples:
        assert g['near leg'] == g0['near leg'] and g['torso'] == g0['torso'], ('only the upper leg moves', fr)
    return s


SCENES = {
    'prone_press_up_on_elbows': prone_press_up_on_elbows,
    'prone_hip_extension': prone_hip_extension,
    'bird_dog': bird_dog,
    'cat_camel': cat_camel,
    'side_lying_clamshell': side_lying_clamshell,
    'side_lying_hip_abduction': side_lying_hip_abduction,
}
