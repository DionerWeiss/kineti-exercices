"""Supine batch of the expanded exercise library: six exercises lying on the
mat, authored on the same rig as the home exercises (figure3d).

Built by tool/build_catalog.py (see its docstring).

Every scene is one slow repetition per loop (start -> execution -> return),
has named step markers and passes the rig's geometric checks plus its own:
body never sinks into the mat, planted feet and hands do not slide, the
moving joint does what the exercise asks and nothing else moves.
"""

import _rig  # noqa: F401  (puts the Kineti rig on sys.path)
import math

from build_home_exercise_animations import MAT, chain, hook_lying, markers, mat, scene3d
from figure3d import (DOWN, IK_ERRORS, Camera, add, add_figure, arm_fk, arm_ik, check as check3d, dot,
                      geometry, leg_fk, leg_ik, length, mul, poly3, sub, unit, with_body)
from kineti_lottie import FPS, GEOMETRY_WARNINGS, HEAD_R, W_ARM, W_FOOT, W_LEG, W_TORSO, Track, smooth

HIP_Y = MAT + W_TORSO / 2          # pelvis centre when lying on the mat
SHOULDER_REST = (-0.42, HIP_Y, 0.0)  # shoulder centre of hook_lying
STRAIGHT = 0.884                   # hip-ankle distance of a straight leg, inside full reach
MAT_EXTENT = [(-1.05, 0, 0.42), (0.95, 0, -0.42)]
LONG_MAT = 1.12                    # mat end for scenes with a straight leg, so the foot stays on it


# ------------------------------------------------------------------ helpers
def ramp(t, t0, t1):
    """0 before t0, eased to 1 at t1."""
    return smooth(min(max((t - t0) / (t1 - t0), 0.0), 1.0))


def bisect(f, lo, hi, n=60):
    """Root of an increasing or decreasing f on [lo, hi]."""
    flo = f(lo)
    for _ in range(n):
        mid = (lo + hi) / 2
        if (f(mid) > 0) == (flo > 0):
            lo, flo = mid, f(mid)
        else:
            hi = mid
    return (lo + hi) / 2


def foot_bottom(g, side):
    """Lowest surface point of the drawn foot."""
    return min(q[1] for q in g[f'{side} foot']) - W_FOOT / 2


def leg_bottom(g, side):
    """Lowest surface of the thigh and shin strokes, ignoring the ankle end
    (the ankle is narrower than the stroke)."""
    hip, knee, ankle = g[f'{side} leg']
    inner = add(knee, mul(sub(ankle, knee), 0.75))
    return min(hip[1], knee[1], inner[1]) - W_LEG / 2


def ik_ankle_height(toe):
    """Ankle height that rests the lowest point of an IK foot with toe
    direction `toe` just on the mat (same foot drawing as figure3d)."""
    t = unit(toe)
    n = unit(sub(DOWN, mul(t, dot(DOWN, t))))
    heel = add(mul(n, 0.03), mul(t, -0.035))
    tip = add(mul(n, 0.04), mul(t, 0.14))
    return MAT + W_FOOT / 2 + 0.002 - min(heel[1], tip[1])


def straight_ankle(side, toe):
    """Ankle of a straight leg lying on the mat, heel just touching it."""
    sign = 1 if side == 'near' else -1
    y = ik_ankle_height(toe)
    z = sign * 0.11
    hip = (0.0, HIP_Y, sign * 0.085)
    dy, dz = y - hip[1], z - hip[2]
    return (math.sqrt(STRAIGHT ** 2 - dy * dy - dz * dz), y, z)


TOE_UP = (0.45, 0.89, 0.0)     # relaxed foot of a straight leg lying down
TOE_FLAT = (1.0, 0.0, 0.0)


def lying_leg(side):
    """IK straight leg resting on the mat."""
    sign = 1 if side == 'near' else -1
    return leg_ik(straight_ankle(side, TOE_UP), TOE_UP, (0, 1, sign * 0.12))


def hook_leg(side):
    """IK bent leg of hook_lying, sole flat on the mat."""
    return hook_lying()['legs'][side]


def rest_fk_leg(plantar=18, abd=2):
    """FK straight leg lying on the mat; the hip angle rests the heel on it."""
    def gap(h):
        g = geometry(hook_lying(legs={'near': leg_fk(h, 0, plantar, abd)}))
        return foot_bottom(g, 'near') - (MAT + 0.002)
    return leg_fk(bisect(gap, -8.0, 6.0), 0.0, plantar, abd)


def common_checks(samples, feet=('near', 'far'), legs=('near', 'far')):
    for fr, g in samples:
        hip, _, shoulder = g['torso']
        assert hip[1] - W_TORSO / 2 >= MAT - 1e-6, ('pelvis in mat', fr)
        assert shoulder[1] - W_TORSO / 2 >= MAT - 1e-6, ('shoulders in mat', fr)
        assert g['head'][1] - HEAD_R >= MAT - 1e-6, ('head in mat', fr)
        for side in feet:
            assert foot_bottom(g, side) > MAT - 0.003, ('foot in mat', fr, side)
        for side in legs:
            assert leg_bottom(g, side) > MAT - 0.006, ('leg in mat', fr, side)
        for side in ('near', 'far'):
            assert min(q[1] for q in g[f'{side} arm']) - W_ARM / 2 > MAT - 0.008, ('arm in mat', fr, side)


def planted(get_name, target):
    return (get_name, lambda g: g[get_name][2], target)


def supine_scene(title, cam, tr, extra=MAT_EXTENT, mat_z=0.42, mat_x1=0.95, width=3.3):
    extra = list(extra) + [(mat_x1, 0, mat_z), (mat_x1, 0, -mat_z)]
    s = scene3d(title, cam, tr, extra, width=width)
    s.floor()
    mat(s, cam, x1=mat_x1, z=mat_z)
    return s


# ------------------------------------------------------------------ bridge
def bridge_pose(lift):
    """Hook lying with the pelvis raised `lift` degrees about the shoulders:
    the shoulder centre stays on the mat, the trunk inclines, the head stays
    level on the mat, feet and hands stay planted."""
    phi = math.radians(lift)
    hip = add(SHOULDER_REST, (0.42 * math.cos(phi), 0.42 * math.sin(phi), 0.0))
    return hook_lying(pelvis=hip, pitch=-90 - lift, nod=4 + lift)


def bridge():
    rest = hook_lying()
    g0 = geometry(rest)
    hands = {side: arm_ik(g0[f'{side} arm'][2], (0.2, 1.0, 0.4 * (1 if side == 'near' else -1)), local=False)
             for side in ('near', 'far')}
    feet = {side: g0[f'{side} leg'][2] for side in ('near', 'far')}
    LIFT = 27

    def at(u):
        return with_body(bridge_pose(LIFT * u), arms=hands)

    tr = Track()
    t = [0, 0.8, 2.3, 3.5, 5.3, 6.1]  # rest, lift, hold, lower, rest
    tr.add(t[0], t[1], lambda x: at(0))
    tr.add(t[1], t[2], lambda x: at(smooth((x - t[1]) / (t[2] - t[1]))))
    tr.add(t[2], t[3], lambda x: at(1))
    tr.add(t[3], t[4], lambda x: at(1 - smooth((x - t[3]) / (t[4] - t[3]))))
    tr.add(t[4], t[5], lambda x: at(0))
    cam = Camera(yaw=0, pitch=16)
    s = supine_scene('Ponte', cam, tr)
    samples = add_figure(s, cam, tr, shadow=False)
    markers(s, ['start', 'lift_hips', 'hold', 'lower_hips', 'rest'], t)
    check3d(s, cam, tr, samples, floor=False,
            planted=[planted(f'{side} leg', feet[side]) for side in feet] +
                    [planted(f'{side} arm', g0[f'{side} arm'][2]) for side in feet])
    common_checks(samples)
    for fr, g in samples:
        assert length(sub(g['torso'][2], SHOULDER_REST)) < 1e-9, ('shoulders left the mat', fr)
    top = geometry(at(1))
    sh, hip, knee = top['torso'][2], top['torso'][0], top['near leg'][1]
    flat = lambda v: unit((v[0], v[1], 0.0))  # sagittal plane: the knees sit a little wide of the hips
    bend = math.degrees(math.acos(dot(flat(sub(hip, sh)), flat(sub(knee, hip)))))
    assert bend < 12, ('shoulders, hips and knees not aligned at the top', bend)
    return s


# ------------------------------------------------------------------ heel slides
def heel_slides():
    """Both legs straight. The near heel slides toward the buttock until the
    sole is flat, then slides back; it never leaves the mat."""
    far = lying_leg('far')
    a0, a1 = straight_ankle('near', TOE_UP), hook_leg('near')['ankle']

    def at(u):
        toe = unit(add(mul(TOE_UP, 1 - u), mul(TOE_FLAT, u)))
        x = a0[0] + (a1[0] - a0[0]) * u
        z = a0[2] + (a1[2] - a0[2]) * u
        near = leg_ik((x, ik_ankle_height(toe), z), toe, (0, 1, 0.12))
        return hook_lying(legs={'near': near, 'far': far})

    tr = Track()
    t = [0, 0.7, 2.6, 3.3, 5.4, 6.0]
    tr.add(t[0], t[1], lambda x: at(0))
    tr.add(t[1], t[2], lambda x: at(smooth((x - t[1]) / (t[2] - t[1]))))
    tr.add(t[2], t[3], lambda x: at(1))
    tr.add(t[3], t[4], lambda x: at(1 - smooth((x - t[3]) / (t[4] - t[3]))))
    tr.add(t[4], t[5], lambda x: at(0))
    cam = Camera(yaw=10, pitch=20)
    s = supine_scene('Deslizamento do calcanhar', cam, tr, mat_x1=LONG_MAT)
    samples = add_figure(s, cam, tr, shadow=False)
    markers(s, ['start', 'slide_heel_in', 'hold', 'slide_heel_out', 'rest'], t)
    check3d(s, cam, tr, samples, floor=False, planted=[planted('far leg', far['ankle'])])
    common_checks(samples)
    for fr, g in samples:  # the foot keeps contact with the mat
        assert abs(foot_bottom(g, 'near') - (MAT + 0.002)) < 1e-3, ('foot left the mat', fr)
    return s


# ------------------------------------------------------------------ straight leg raise
def straight_leg_raise():
    """Far knee bent, sole flat. The near leg, knee straight, lifts until the
    thighs are parallel, holds and lowers back to the mat."""
    rest = rest_fk_leg()
    g_hook = geometry(hook_lying())
    hip, knee = g_hook['far leg'][0], g_hook['far leg'][1]
    thigh = math.degrees(math.atan2(knee[1] - hip[1], knee[0] - hip[0]))
    up = dict(rest, hip=thigh)
    down_pose = hook_lying(legs={'near': rest})
    up_pose = hook_lying(legs={'near': up})
    tr = Track()
    t = chain(tr, [(down_pose, 0.8), (up_pose, 1.7), (up_pose, 1.0), (down_pose, 2.2), (down_pose, 0.7)])
    cam = Camera(yaw=10, pitch=18)
    s = supine_scene('Elevação da perna estendida', cam, tr, mat_x1=LONG_MAT)
    samples = add_figure(s, cam, tr, shadow=False)
    markers(s, ['start', 'lift_leg', 'hold', 'lower_leg', 'rest'], t)
    far_ankle = g_hook['far leg'][2]
    check3d(s, cam, tr, samples, floor=False, planted=[planted('far leg', far_ankle)])
    common_checks(samples)
    for fr, g in samples:  # knee stays straight
        h, k, a = g['near leg']
        assert length(sub(a, h)) > 0.889, ('knee bent', fr)
    return s


# ------------------------------------------------------------------ hip abduction
def supine_hip_abduction():
    """Both legs straight on the mat. The near leg slides out to the side,
    toes up, and comes back; seen from above so the sweep reads."""
    rest = rest_fk_leg(abd=2)
    out = dict(rest, abd=26)
    arms = {'near': arm_fk(-7, -7, abd=28), 'far': arm_fk(-7, -7, abd=28)}  # clear of the hip seen from above
    base = hook_lying(legs={'near': rest, 'far': rest}, arms=arms)
    moved = hook_lying(legs={'near': out, 'far': rest}, arms=arms)
    tr = Track()
    t = chain(tr, [(base, 0.8), (moved, 1.8), (moved, 0.8), (base, 1.9), (base, 0.7)])
    cam = Camera(yaw=6, pitch=52)
    extra = [(-1.05, 0, 0.62), (1.05, 0, -0.42)]
    s = supine_scene('Abdução de quadril deitado', cam, tr, extra, mat_z=0.62, mat_x1=LONG_MAT)
    s.layers = [l for l in s.layers if l['nm'] not in ('floor', 'floor plane')]  # seen from above: mat only
    samples = add_figure(s, cam, tr, shadow=False)
    markers(s, ['start', 'slide_out', 'hold', 'slide_in', 'rest'], t)
    far_ankle = geometry(base)['far leg'][2]
    check3d(s, cam, tr, samples, floor=False, planted=[planted('far leg', far_ankle)])
    common_checks(samples)
    for fr, g in samples:  # the leg slides on the mat, never lifts
        assert abs(g['near leg'][2][1] - g['far leg'][2][1]) < 0.01, ('leg lifted', fr)
        assert g['near leg'][2][2] - W_LEG / 2 < 0.62, ('foot off the mat', fr)
    return s


# ------------------------------------------------------------------ knee to chest
def fk_from_hook(side='near'):
    """FK angles of the hook_lying leg (hip, knee flexion, flat sole)."""
    g = geometry(hook_lying())
    hip, knee, ankle = g[f'{side} leg']
    thigh = math.degrees(math.atan2(knee[1] - hip[1], knee[0] - hip[0]))
    shin = math.degrees(math.atan2(ankle[1] - knee[1], ankle[0] - knee[0]))
    return thigh, thigh - shin


def single_knee_to_chest():
    """Hook lying. The near knee rises, both hands hold the shin just below
    the knee and draw it toward the chest; hold, release and lower."""
    h0, k0 = fk_from_hook()
    cam = Camera(yaw=10, pitch=18)
    far = hook_leg('far')
    g_rest = geometry(hook_lying(legs={'near': leg_fk(h0, k0, h0 - k0 + 90, 3)}))
    # resting hands on the mat, elbows just short of full reach so IK can solve them
    rest_hands = {side: add(g_rest[f'{side} arm'][0], mul(sub(g_rest[f'{side} arm'][2], g_rest[f'{side} arm'][0]), 0.985))
                  for side in ('near', 'far')}
    bends = {'near': (-0.2, -0.2, 1.0), 'far': (-0.2, -0.2, -1.0)}
    GRIP_H, GRIP_K, PULL_H, PULL_K = 118, 118, 132, 132

    def leg(h, k):
        return leg_fk(h, k, h - k + 90 - 20 * min(1.0, max(0.0, (h - h0) / (GRIP_H - h0))), 3)

    def grip_points(g):
        _, knee, ankle = g['near leg']
        c = add(knee, mul(sub(ankle, knee), 0.12))
        return {'near': add(c, (0, 0.0, 0.07)), 'far': add(c, (0, 0.0, -0.07))}

    def pose(h, k, reach):
        p = hook_lying(legs={'near': leg(h, k), 'far': far})
        g = geometry(p)
        grip = grip_points(g)
        arms = {}
        for side in ('near', 'far'):
            target = add(mul(rest_hands[side], 1 - reach), mul(grip[side], reach))
            sh = g[f'{side} arm'][0]
            d = sub(target, sh)
            if length(d) > 0.552:  # on the way to the shin the hand stays within reach
                target = add(sh, mul(unit(d), 0.552))
            arms[side] = arm_ik(target, bends[side], local=False)
        return with_body(p, arms=arms)

    rest_s, lift_s, pull_s, hold_s, rel_s, low_s, tail = 0.6, 1.5, 1.2, 1.0, 1.1, 1.5, 0.6
    t = [0]
    for d in (rest_s, lift_s, pull_s, hold_s, rel_s, low_s, tail):
        t.append(t[-1] + d)

    def at(x):
        lift = ramp(x, t[1], t[2]) - ramp(x, t[5], t[6])
        pull = ramp(x, t[2], t[3]) - ramp(x, t[4], t[5])
        h = h0 + (GRIP_H - h0) * lift + (PULL_H - GRIP_H) * pull
        k = k0 + (GRIP_K - k0) * lift + (PULL_K - GRIP_K) * pull
        return pose(h, k, lift)

    tr = Track()
    tr.add(0, t[-1], at)
    s = supine_scene('Joelho ao peito', cam, tr)
    samples = add_figure(s, cam, tr, shadow=False)
    markers(s, ['start', 'lift_knee', 'pull_to_chest', 'hold', 'release', 'lower_leg', 'rest'], t)
    check3d(s, cam, tr, samples, floor=False, planted=[planted('far leg', far['ankle'])])
    common_checks(samples)
    for fr, g in samples:
        if t[2] <= fr / FPS <= t[5]:  # hands stay on the shin while holding
            grip = grip_points(g)
            for side in ('near', 'far'):
                assert length(sub(g[f'{side} arm'][2], grip[side])) < 2e-3, ('hand off the shin', fr, side)
    return s


# ------------------------------------------------------------------ short arc quad
ROLL_R = 0.075


def roll(s, cam, cx, z0, z1, r=ROLL_R):
    """Towel roll lying across the mat (axis along Z): silhouette band and
    the cap facing the camera, as soft-filled polygons."""
    cy = MAT + r
    ring = lambda z: [(cx + r * math.cos(a), cy + r * math.sin(a), z)
                      for a in (2 * math.pi * i / 32 for i in range(32))]
    # silhouette: extreme points of the cap ellipse perpendicular to the axis on screen
    ax = sub(cam.screen((0, 0, 1)), (0, 0))
    perp = (-ax[1], ax[0])
    cap0, cap1 = ring(z0), ring(z1)
    key = lambda q: dot(cam.screen(q), perp)
    hi0, lo0 = max(cap0, key=key), min(cap0, key=key)
    hi1, lo1 = max(cap1, key=key), min(cap1, key=key)
    poly3(s, cam, 'towel roll side', [hi0, hi1, lo1, lo0], 'prop-soft', 'prop', 0.018)
    near_cap = cap1 if dot((0, 0, 1), cam.toward) > 0 else cap0
    poly3(s, cam, 'towel roll end', near_cap, 'prop-soft', 'prop', 0.018)
    # rolled-towel spiral on the end, so it reads as a towel and not a tube
    spiral = [(cx + r * (0.25 + 0.5 * a / (4 * math.pi)) * math.cos(a), cy + r * (0.25 + 0.5 * a / (4 * math.pi)) * math.sin(a),
               near_cap[0][2]) for a in (4 * math.pi * i / 40 for i in range(41))]
    from figure3d import line3
    line3(s, cam, 'towel roll spiral', spiral, 'prop', 0.01)
    return (cx, cy)


def seg_dist(c, a, b):
    """2D distance (x, y) from point c to segment ab."""
    ax, ay, bx, by, cx, cy = a[0], a[1], b[0], b[1], c[0], c[1]
    dx, dy = bx - ax, by - ay
    u = max(0.0, min(1.0, ((cx - ax) * dx + (cy - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(ax + u * dx - cx, ay + u * dy - cy)


def short_arc_quad():
    """Both legs straight, a towel roll under the near knee. The heel lifts
    until the knee is straight, holds, and lowers; the back of the knee
    stays on the roll."""
    # The knee sits on the roll, 1 cm into the soft towel's silhouette margin.
    knee_y = MAT + 2 * ROLL_R + W_LEG / 2 + 0.01
    plantar = 18
    thigh = bisect(lambda h: geometry(hook_lying(legs={'near': leg_fk(h, 0, plantar, 2)}))['near leg'][1][1] - knee_y,
                   0.0, 40.0)

    def heel_gap(k):
        g = geometry(hook_lying(legs={'near': leg_fk(thigh, k, plantar, 2)}))
        return foot_bottom(g, 'near') - (MAT + 0.002)

    k_rest = bisect(heel_gap, 5.0, 70.0)
    far = rest_fk_leg(abd=2)
    down = hook_lying(legs={'near': leg_fk(thigh, k_rest, plantar, 2), 'far': far})
    up = hook_lying(legs={'near': leg_fk(thigh, 0.0, plantar, 2), 'far': far})
    tr = Track()
    t = chain(tr, [(down, 0.8), (up, 1.5), (up, 1.2), (down, 1.9), (down, 0.7)])
    cam = Camera(yaw=22, pitch=26)
    s = supine_scene('Extensão de joelho sobre rolo', cam, tr, mat_x1=LONG_MAT)
    knee0 = geometry(down)['near leg'][1]
    centre = roll(s, cam, knee0[0], 0.0, 0.24)
    samples = add_figure(s, cam, tr, shadow=False)
    markers(s, ['start', 'straighten_knee', 'hold', 'lower_heel', 'rest'], t)
    check3d(s, cam, tr, samples, floor=False,
            planted=[planted('far leg', geometry(down)['far leg'][2]),
                     ('near knee', lambda g: g['near leg'][1], knee0)])
    common_checks(samples)
    clear = ROLL_R + W_LEG / 2 - 0.003
    for fr, g in samples:
        hip, knee, ankle = g['near leg']
        assert seg_dist(centre, hip, knee) > clear and seg_dist(centre, knee, ankle) > clear, ('leg in roll', fr)
        assert length(sub(ankle, hip)) <= 0.89 + 1e-9, ('knee hyperextended', fr)
    return s, k_rest


SCENES = {
    'bridge': bridge,
    'heel_slides': heel_slides,
    'straight_leg_raise': straight_leg_raise,
    'supine_hip_abduction': supine_hip_abduction,
    'single_knee_to_chest': single_knee_to_chest,
    'short_arc_quad': lambda: short_arc_quad()[0],
}
