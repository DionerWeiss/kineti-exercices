"""Lote 2 of the expanded exercise library: exercises with an elastic band or
a ball, on the same rig as the home exercises.

Built by tool/build_catalog.py (see its docstring).

Prop conventions:
- Elastic band: a 'marker' stroke (tertiary orange) about 2 cm wide between
  its anchor and the hands, redrawn every frame; it thins a little as it
  stretches. Anchors (door, door frame) use 'prop' and 'prop-soft'.
- Balls: 'prop-soft' fill with a 'prop' outline.

Every scene is one slow repetition per loop (start -> execution -> return),
has named step markers and passes the rig's geometric checks plus its own.
"""

import _rig  # noqa: F401  (puts the Kineti rig on sys.path)
import math

from build_home_exercise_animations import chain, check2d, markers, scene3d, seated3d
from build_library_seated_animations import SIDE_ARMS
from build_library_standing_animations import PEL_Y, every_frame, repeat, stand3d
from figure3d import (HALF_SHOULDERS, Camera, add, add_figure, arm_fk, arm_ik, chair, check as check3d,
                      dot, floor_patch, geometry, leg_ik, length, line3, mul, poly3, sample, sub, two_bone,
                      unit, with_body)
from kineti_lottie import (ANKLE, FPS, L_FORE, L_UP, W_LEG, W_TORSO, Scene, Track,
                           animated, dedupe, ellipse, figure_geometry, fill, group, path, planted, pose, stroke,
                           with_)

BAND_W = 0.02   # elastic band width (m) at rest length
BAND_HALO = 0.008


# ------------------------------------------------------------------ prop drawing
def band(scene, cam, samples, name, points_of, rest_length):
    """Band polyline through points_of(g) (world points) on every sampled
    frame. Width thins with stretch (volume kept: w ~ 1/sqrt(stretch))."""
    keys, widths = [], []
    for fr, g in samples:
        pts = points_of(g)
        stretched = sum(length(sub(b, a)) for a, b in zip(pts, pts[1:]))
        w = BAND_W * min(1.0, max(0.6, math.sqrt(rest_length / stretched)))
        keys.append((fr, [cam.px(scene, q) for q in pts]))
        widths.append((fr, round(scene.m(w), 2)))
    halo = stroke('stage', scene.m(BAND_W + 2 * BAND_HALO), scene.palette)
    halo['w'] = animated(dedupe([(fr, round(w + scene.m(2 * BAND_HALO), 2)) for fr, w in widths]))
    line = stroke('marker', scene.m(BAND_W), scene.palette)
    line['w'] = animated(dedupe(widths))
    scene.layer(f'{name} halo', [group(f'{name} halo', [path(keys=keys), halo])])
    scene.layer(name, [group(name, [path(keys=keys), line])])


def ball_layer(scene, name, centers_px, sizes_px, seam=None):
    """Ball as an ellipse (fill prop-soft, outline prop). centers_px and
    sizes_px: [(frame, [x, y])]. seam: optional [(frame, [p0, p1])] chord."""
    el = ellipse(keys=centers_px)
    sizes = dedupe(sizes_px)
    el['s'] = animated(sizes) if len(sizes) > 1 else {'a': 0, 'k': sizes[0][1]}
    items = [el, fill('prop-soft', scene.palette), stroke('prop', scene.m(0.014), scene.palette)]
    scene.layer(name, [group(name, items)])
    if seam:
        scene.layer(f'{name} seam', [group('seam', [path(keys=seam), stroke('prop', scene.m(0.01), scene.palette)])])


# ------------------------------------------------------------------ 1. seated row
DOOR_X = 1.22                    # door face, in front of the patient
ROW_ANCHOR = (DOOR_X, 0.88, 0.0)  # band anchored at chest height


def row_arms(pull):
    """Hands in the thorax frame: reaching forward (pull 0) to beside the
    ribs (pull 1), elbows close to the body and travelling back."""
    out = {}
    for side, sign in (('near', 1), ('far', -1)):
        reach = (-0.12, 0.5, sign * 0.1)
        ribs = (-0.2, 0.06, sign * 0.2)
        hand = tuple(a + (b - a) * pull for a, b in zip(reach, ribs))
        out[side] = arm_ik(hand, (-0.35, -1.0, sign * 0.35))
    return out


def seated_band_row():
    """Sitting tall on a stool facing a door, the band anchored to the door
    at chest height. Both hands pull the band toward the ribs, elbows close
    to the body and the shoulder blades drawn together, then return."""
    cam = Camera(yaw=-38, pitch=12)  # behind and to the side: back and blades in view
    rest = seated3d(trunk=0, arms=row_arms(0.0))
    pulled = with_body(rest, arms=row_arms(1.0), retract=0.035)
    tr = Track()
    t = chain(tr, [(rest, 0.8), (pulled, 1.5), (pulled, 0.8), (rest, 1.9), (rest, 0.8)])
    door = [(DOOR_X, y, z) for y in (0.0, 1.25) for z in (-0.45, 0.45)]
    s = scene3d('Remada sentada com faixa', cam, tr, door, width=3.3)
    floor_patch(s, cam, -0.75, DOOR_X + 0.2, -0.7, 0.7)
    poly3(s, cam, 'door', [(DOOR_X, 0, -0.45), (DOOR_X, 2.3, -0.45), (DOOR_X, 2.3, 0.45), (DOOR_X, 0, 0.45)],
          'prop-soft', 'prop', 0.02)
    line3(s, cam, 'door anchor', [(DOOR_X, ROW_ANCHOR[1] - 0.04, 0), (DOOR_X, ROW_ANCHOR[1] + 0.04, 0)], 'prop', 0.04)
    chair(s, cam, backrest=False)
    samples = sample(s, tr)
    band(s, cam, samples, 'band', lambda g: [g['near arm'][2], ROW_ANCHOR, g['far arm'][2]],
         2 * length(sub(geometry(rest)['near arm'][2], ROW_ANCHOR)))

    def blades(smp):
        for side in ('far', 'near'):
            keys = [(fr, [cam.px(s, q) for q in g[f'{side} scapula']]) for fr, g in smp]
            s.layer('scapula', [group('scapula', [path(keys=keys), stroke('stage', s.m(0.022), s.palette)])])

    samples = add_figure(s, cam, tr, front=('near', 'far'), girdle=True, after_legs=blades)
    markers(s, ['start', 'pull', 'hold', 'release', 'rest'], t)
    check3d(s, cam, tr, samples)
    g_rest, g_pull = geometry(rest), geometry(pulled)
    for side in ('near', 'far'):
        sh, elbow, hand = g_pull[f'{side} arm']
        assert elbow[0] < sh[0] - 0.05, ('elbow not behind the trunk', side)
        assert hand[0] > -0.05, ('hand behind the back', side)
        assert abs(elbow[2]) < 0.36, ('elbow flared out', side)
    for fr, g in samples:  # band stays taut and in front of the body
        for side in ('near', 'far'):
            hand = g[f'{side} arm'][2]
            assert hand[0] < ROW_ANCHOR[0] - 0.4, ('hand at the door', fr)
            assert length(sub(hand, ROW_ANCHOR)) >= length(sub(g_rest[f'{side} arm'][2], ROW_ANCHOR)) - 1e-6
    return s


# ------------------------------------------------------------------ 2. band pull-apart
REACH = 0.53


def pull_apart_arms(u):
    """Arms straight at shoulder height; u 0: in front, hands about 25 cm
    apart; u 1: out to the sides, a little in front of the body."""
    a = math.radians(4 + 78 * u)
    out = {}
    for side, sign in (('near', 1), ('far', -1)):
        hand =(0.0, REACH * math.cos(a), sign * (HALF_SHOULDERS + REACH * math.sin(a) - 0.035 * (1 - u)))
        out[side] = arm_ik(hand, (-1.0, -0.15, sign * 0.1))
    return out


def band_pull_apart():
    """Standing, arms straight in front at shoulder height holding the band.
    The arms open out to the sides, stretching the band across the chest,
    and come back slowly."""
    cam = Camera(yaw=64, pitch=10)
    feet = ((0.0, ANKLE, 0.1), (0.0, ANKLE, -0.1))
    at = lambda u: stand3d((0.0, PEL_Y, 0.0), *feet, arms=pull_apart_arms(u), trunk=1)
    tr = Track()
    t = repeat(tr, at, (0.8, 1.6, 0.8, 1.8, 0.8))
    s = scene3d('Abertura de braços com faixa', cam, tr, width=3.0)
    floor_patch(s, cam, -0.7, 0.8, -0.9, 0.9)
    rest_len = length(sub(geometry(at(0))['near arm'][2], geometry(at(0))['far arm'][2]))
    samples = add_figure(s, cam, tr, girdle=True, after_arms=lambda smp: band(
        s, cam, smp, 'band', lambda g: [g['far arm'][2], g['near arm'][2]], rest_len))
    markers(s, ['start', 'open_arms', 'hold', 'close_arms', 'rest'], t)
    planted = [(f'{k} ankle', lambda g, k=k: g[f'{k} leg'][2], a) for k, a in zip(('near', 'far'), feet)]
    check3d(s, cam, tr, samples, planted=planted)
    for fr, g in samples:
        for side in ('near', 'far'):
            sh, _, hand = g[f'{side} arm']
            assert length(sub(hand, sh)) > 0.5, ('elbow bent', fr, side)
            assert abs(hand[1] - sh[1]) < 0.03, ('hand off shoulder height', fr, side)
    g1 = geometry(at(1))
    assert length(sub(g1['near arm'][2], g1['far arm'][2])) > 3 * rest_len, 'band barely stretched'
    return s


# ------------------------------------------------------------------ 3. external rotation
ER_SHOULDER = (0.0, 0.0, HALF_SHOULDERS)  # near shoulder joint in the thorax frame
ER_ELBOW = (-L_UP + 0.004, 0.0, HALF_SHOULDERS + 0.03)  # elbow tucked at the side


def er_arm(angle):
    """Near arm: elbow fixed at the side, bent 90 degrees; the forearm swings
    from pointing forward (0) outward by `angle` degrees about the upper arm."""
    a = math.radians(angle)
    up = unit(sub(ER_ELBOW, ER_SHOULDER))
    elbow = add(ER_SHOULDER, mul(up, L_UP))
    lateral = unit((up[2], 0.0, -up[0]))  # perpendicular to the upper arm, outward
    fore = add(mul((0.0, 1.0, 0.0), math.cos(a)), mul(lateral, math.sin(a)))
    hand = add(elbow, mul(fore, L_FORE))
    return arm_ik(hand, sub(elbow, ER_SHOULDER))


POST = (0.32, -0.78)  # door frame post (x, z) on the far side


def band_shoulder_external_rotation():
    """Standing side-on to a door frame, the band anchored at elbow height on
    the far side. With the near elbow tucked at the side and bent to 90
    degrees, the forearm turns outward against the band and back."""
    cam = Camera(yaw=58, pitch=34)  # front and above: the forearm sweeps in a horizontal arc
    feet = ((0.0, ANKLE, 0.1), (0.0, ANKLE, -0.1))
    far_arm = arm_fk(2, 9, abd=6)

    def at(u):
        return stand3d((0.0, PEL_Y, 0.0), *feet, arms={'near': er_arm(-8 + 68 * u), 'far': far_arm}, trunk=0)

    tr = Track()
    t = repeat(tr, at, (0.8, 1.6, 0.7, 1.9, 0.8))
    anchor_y = geometry(at(0))['near arm'][1][1]
    anchor = (POST[0], anchor_y, POST[1] + 0.03)
    post = [(POST[0], y, POST[1]) for y in (0.0, 1.9)]
    s = scene3d('Rotação externa de ombro com faixa', cam, tr, post, width=3.0)
    floor_patch(s, cam, -0.7, 0.9, -1.0, 0.9)
    line3(s, cam, 'door frame', post, 'prop', 0.06)
    line3(s, cam, 'door anchor', [(POST[0], anchor_y - 0.035, POST[1] + 0.03), (POST[0], anchor_y + 0.035,
                                                                                 POST[1] + 0.03)], 'prop', 0.04)
    rest_len = length(sub(geometry(at(0))['near arm'][2], anchor))
    samples = add_figure(s, cam, tr, after_arms=lambda smp: band(
        s, cam, smp, 'band', lambda g: [anchor, g['near arm'][2]], rest_len))
    markers(s, ['start', 'rotate_out', 'hold', 'return', 'rest'], t)
    planted = [(f'{k} ankle', lambda g, k=k: g[f'{k} leg'][2], a) for k, a in zip(('near', 'far'), feet)]
    elbow0 = geometry(at(0))['near arm'][1]
    planted.append(('near elbow', lambda g: g['near arm'][1], elbow0))
    check3d(s, cam, tr, samples, planted=planted)
    for fr, g in samples:
        sh, elbow, hand = g['near arm']
        fore = sub(hand, elbow)
        assert abs(fore[1]) < 0.04, ('forearm not level', fr)
        upper = unit(sub(elbow, sh))
        assert abs(dot(upper, unit(fore))) < 0.02, ('elbow not at 90 degrees', fr)
        assert hand[0] > W_TORSO / 2, ('hand in the trunk', fr)
    g1 = geometry(at(1))
    assert g1['near arm'][2][2] > g1['near arm'][1][2] + 0.2, 'forearm did not turn out'
    return s


# ------------------------------------------------------------------ 4/5. seated knees
def knee_target_leg(g_ref, side, knee_z, ankle):
    """Leg IK with the ankle planted and the knee placed at lateral position
    knee_z (bisection on the knee-direction hint)."""
    sign = 1 if side == 'near' else -1
    lo, hi = -1.5, 1.5
    hip = g_ref[f'{side} leg'][0]
    for _ in range(50):
        k = (lo + hi) / 2
        leg = leg_ik(ankle, (1.0, 0.0, sign * 0.04), (1.0, 0.0, k))
        knee, _ = two_bone(hip, ankle, 0.44, 0.45, (1.0, 0.0, k))
        if knee[2] < knee_z:
            lo = k
        else:
            hi = k
    return leg


def seated_knees(knee_half_gap, ankle_half_gap, arms=SIDE_ARMS):
    """Seated pose with feet planted at ±ankle_half_gap and knees at
    ±knee_half_gap."""
    base = seated3d(trunk=0, arms=arms)
    g = geometry(base)
    legs = {}
    for side, sign in (('near', 1), ('far', -1)):
        a = g[f'{side} leg'][2]
        ankle = (a[0], a[1], sign * ankle_half_gap)
        legs[side] = knee_target_leg(g, side, sign * knee_half_gap, ankle)
    return with_body(base, legs=legs)


SEAT_TOP, SEAT_FRONT = 0.46, 0.23

# Arms crossed on the chest, each hand on the opposite shoulder: keeps the
# arms clear of the thighs, which carry the movement in the knee scenes.
CROSSED_ARMS = {side: arm_ik((-0.06, 0.13, -sign * 0.1), (-0.5, 0.35, sign * 1.0))
                for side, sign in (('near', 1), ('far', -1))}


def thighs_on_seat(samples):
    for fr, g in samples:
        for side in ('near', 'far'):
            hip, knee, _ = g[f'{side} leg']
            for i in range(11):
                q = add(hip, mul(sub(knee, hip), i / 10))
                if q[0] < SEAT_FRONT:
                    assert q[1] - W_LEG / 2 > SEAT_TOP - 0.012, ('thigh in seat', fr, side)


def seated_band_hip_abduction():
    """Seated, a band looped around both thighs just above the knees. The
    knees open apart against the band, feet planted, and close slowly."""
    cam = Camera(yaw=42, pitch=36)  # front, three-quarter and above: the thighs read on the seat
    closed, opened = seated_knees(0.12, 0.13, CROSSED_ARMS), seated_knees(0.27, 0.13, CROSSED_ARMS)
    tr = Track()
    t = chain(tr, [(closed, 0.8), (opened, 1.5), (opened, 0.8), (closed, 1.9), (closed, 0.8)])
    extra = [(x, y, z) for x in (-0.3, 0.6) for y in (0.0, 1.0) for z in (-0.3, 0.3)]
    s = scene3d('Abdução de quadril sentado com faixa', cam, tr, extra)
    floor_patch(s, cam, -0.75, 1.0, -0.6, 0.6)
    chair(s, cam)

    def loop_points(g):
        """Across the top of both thighs, outer edge to outer edge: the strap
        over each thigh and the stretched span between the knees."""
        pts = []
        for side, sign in (('far', -1), ('near', 1)):
            hip, knee, _ = g[f'{side} leg']
            c = add(hip, mul(sub(knee, hip), 0.82), (0.0, 0.012, 0.0))
            edges = [add(c, (0.0, 0.0, -sign * W_LEG / 2)), add(c, (0.0, 0.0, sign * W_LEG / 2))]
            pts += edges if side == 'near' else edges[::-1]
        return pts

    def straps(smp):
        pts = loop_points(geometry(closed))
        rest = sum(length(sub(b, a)) for a, b in zip(pts, pts[1:]))
        band(s, cam, smp, 'band', loop_points, rest)

    samples = add_figure(s, cam, tr, front=('near', 'far'), after_legs=straps)
    markers(s, ['start', 'open_knees', 'hold', 'close_knees', 'rest'], t)
    ankles = {side: geometry(closed)[f'{side} leg'][2] for side in ('near', 'far')}
    planted = [(f'{k} ankle', lambda g, k=k: g[f'{k} leg'][2], a) for k, a in ankles.items()]
    check3d(s, cam, tr, samples, planted=planted)
    thighs_on_seat(samples)
    g1 = geometry(opened)
    assert g1['near leg'][1][2] - g1['far leg'][1][2] > 0.5, 'knees did not open'
    return s


BALL_D = 0.2  # soft ball between the knees


def adductor_ball_squeeze():
    """Seated, a soft ball between the knees. The knees squeeze the ball,
    which flattens a little, hold, then release."""
    cam = Camera(yaw=42, pitch=36)  # front, three-quarter and above: the ball reads between the thighs
    gap = lambda d: (d + W_LEG) / 2  # knee centre half-gap for a ball of width d
    # A soft ball can flatten well past a timid 5 cm; the squash has to read
    # between the knees in a full-body frame.
    squeeze_m = 0.11
    rest = seated_knees(gap(BALL_D), gap(BALL_D), CROSSED_ARMS)
    squeeze = seated_knees(gap(BALL_D - squeeze_m), gap(BALL_D), CROSSED_ARMS)
    tr = Track()
    t = chain(tr, [(rest, 0.8), (squeeze, 1.0), (squeeze, 2.2), (rest, 1.2), (rest, 0.8)])
    extra = [(x, y, z) for x in (-0.3, 0.6) for y in (0.0, 1.0) for z in (-0.3, 0.3)]
    s = scene3d('Adução com bola entre os joelhos', cam, tr, extra, width=2.4)
    floor_patch(s, cam, -0.75, 1.0, -0.6, 0.6)
    chair(s, cam)
    yaw, pitch = math.radians(42), math.radians(36)

    def ball(smp):
        centers, sizes = [], []
        for fr, g in smp:
            kn, kf = g['near leg'][1], g['far leg'][1]
            c = mul(add(kn, kf), 0.5)
            width = kn[2] - kf[2] - W_LEG  # z extent of the squeezed ball
            depth = BALL_D + (BALL_D - width) * 0.85  # bulges as the knees flatten it
            sx = 2 * math.hypot(depth / 2 * math.cos(yaw), width / 2 * math.sin(yaw))
            sy = 2 * math.hypot(depth / 2 * math.sin(pitch), depth / 2 * math.cos(pitch))
            centers.append((fr, cam.px(s, c)))
            sizes.append((fr, [round(s.m(sx), 1), round(s.m(sy), 1)]))
        ball_layer(s, 'ball', centers, sizes)

    samples = add_figure(s, cam, tr, front=('near', 'far'), after_legs=ball)
    markers(s, ['start', 'squeeze', 'hold', 'release', 'rest'], t)
    ankles = {side: geometry(rest)[f'{side} leg'][2] for side in ('near', 'far')}
    planted = [(f'{k} ankle', lambda g, k=k: g[f'{k} leg'][2], a) for k, a in ankles.items()]
    check3d(s, cam, tr, samples, planted=planted)
    thighs_on_seat(samples)
    for fr, g in samples:
        width = g['near leg'][1][2] - g['far leg'][1][2] - W_LEG
        assert BALL_D - 0.12 < width < BALL_D + 1e-3, ('ball squeezed out of range', fr, width)
    return s


# ------------------------------------------------------------------ 6. wall ball squat
WB_HIP_X = 0.25        # hips stay over this x: the back rides the ball straight down
WB_R = 0.275           # gym ball radius
WB_FEET_X = WB_HIP_X + 0.36
WB_BALL_X = WB_HIP_X - W_TORSO / 2 - WB_R
WB_WALL_X = WB_BALL_X - WB_R
WB_TOP_Y, WB_DROP = 0.87, 0.21
WB_BALL_Y0 = WB_TOP_Y + 0.17  # ball at the lower back when standing


def wall_ball_pose(u):
    hy = WB_TOP_Y - WB_DROP * u
    p = pose(WB_HIP_X, hy, 0.0, 0.0, aa=(84, 84), ab=(84, 84))
    return with_(p, fa=planted(p, WB_FEET_X), fb=planted(p, WB_FEET_X))


def wall_ball_squat():
    """Profile, a gym ball between the lower back and a wall, feet a step in
    front. The hips sink into a partial squat while the ball rolls down the
    wall at half the speed, then the body rises back up."""
    s = Scene('Agachamento com bola na parede', -1.45, 1.95, -0.25, 6.2)
    tr = Track()
    t = repeat(tr, wall_ball_pose, (0.8, 1.8, 0.8, 2.0, 0.8))
    top = s.top
    s.polygon('wall face', [(s.left, -0.09), (WB_WALL_X - 0.02, -0.09), (WB_WALL_X - 0.02, top), (s.left, top)],
              'prop-soft')
    s.floor(x0=WB_WALL_X - 0.02)
    s.line('wall', [(WB_WALL_X - 0.02, -0.09), (WB_WALL_X - 0.02, top)], 'prop', 0.03)

    def drop_at(fr):
        return WB_TOP_Y - tr.at(fr / FPS)['hy']

    frames_ = list(range(0, s.frames, 2)) + [s.frames]
    centers, seams = [], []
    for fr in frames_:
        cy = WB_BALL_Y0 - drop_at(fr) / 2  # rolls without slipping between wall and back
        a = -(drop_at(fr) / 2) / WB_R + 0.7
        d = (WB_R * 0.82 * math.cos(a), WB_R * 0.82 * math.sin(a))
        centers.append((fr, s.px(WB_BALL_X, cy)))
        seams.append((fr, [s.px(WB_BALL_X - d[0], cy - d[1]), s.px(WB_BALL_X + d[0], cy + d[1])]))
    dpx = round(s.m(2 * WB_R), 1)
    ball_layer(s, 'ball', centers, [(0, [dpx, dpx])], seam=seams)
    s.figure(tr)
    markers(s, ['start', 'squat_down', 'hold', 'stand_up', 'rest'], t)
    check2d(s, tr)
    for fr, g in every_frame(s, tr):
        (hx, hy), (sx, sy) = g['torso']
        cy = WB_BALL_Y0 - (WB_TOP_Y - hy) / 2
        assert hy - 0.02 < cy < sy, ('ball not against the back', fr)
        assert abs(hx - W_TORSO / 2 - (WB_BALL_X + WB_R)) < 1e-6, ('back left the ball', fr)
        ax = g['front_leg']['leg'][2][0]
        assert abs(ax - WB_FEET_X) < 1e-6, ('foot slid', fr)
        knee = g['front_leg']['leg'][1]
        assert knee[0] < ax + 0.2, ('knee far past the toes', fr)
    g1 = figure_geometry(wall_ball_pose(1.0))
    hip, knee, ankle = g1['front_leg']['leg']
    v1, v2 = sub2(hip, knee), sub2(ankle, knee)
    angle = math.degrees(math.acos((v1[0] * v2[0] + v1[1] * v2[1]) / math.hypot(*v1) / math.hypot(*v2)))
    assert 95 < angle < 140, ('partial squat knee angle', angle)
    return s


def sub2(a, b):
    return (a[0] - b[0], a[1] - b[1])


SCENES = {
    'seated_band_row': seated_band_row,
    'band_pull_apart': band_pull_apart,
    'band_shoulder_external_rotation': band_shoulder_external_rotation,
    'seated_band_hip_abduction': seated_band_hip_abduction,
    'adductor_ball_squeeze': adductor_ball_squeeze,
    'wall_ball_squat': wall_ball_squat,
}
