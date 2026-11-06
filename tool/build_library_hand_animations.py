"""Hand and wrist exercises (lote 4) as close-up detail scenes.

At full-body scale a finger is a few pixels wide, so these scenes frame only
the forearm resting on a table and the hand. They keep the body rig's visual
language: round-capped strokes, colour roles, 'stage' halos that separate a
segment from what is painted under it, no text or arrows, one slow
repetition per loop with named step markers.

The hand is a small 3D model local to this module: a palm plate, four
fingers with three phalanges each and a thumb (metacarpal + two phalanges,
solved with two-bone IK towards a tip target). It is posed in a hand frame
(d distal, r radial, p palmar) and projected by figure3d's orthographic
camera. The forearm lies along -X on a table whose top is y = 0.

Built by tool/build_catalog.py (see its docstring).
"""

import _rig  # noqa: F401  (puts the Kineti rig on sys.path)
import math

from build_home_exercise_animations import chain, markers
from figure3d import (IK_ERRORS, Camera, add, blend, box, cross, dot, length, mul, rotate, sub, two_bone,
                      unit)
from kineti_lottie import FPS, STEP, Scene, Track, animated, fill, group, path, smooth, stroke

# ------------------------------------------------------------------ hand model (metres)
FORE_W = 0.06      # forearm stroke: about the wrist's thickness
PALM_W = 0.026     # palm plate stroke: gives the plate its thickness and round edge
HALO = 0.004       # stage outline around front segments (close-up scale)
FORE_LEN = 0.30

# Palm plate, inset by PALM_W / 2 from the visible outline (d, r).
PALM = [(0.008, 0.016), (0.034, 0.030), (0.078, 0.026), (0.083, 0.008), (0.081, -0.009), (0.073, -0.024),
        (0.008, -0.018)]  # the bulge at (0.034, 0.030) is the thenar eminence over the thumb metacarpal
# name: (MCP (d, r), phalanges (m), stroke width (m))
FINGERS = {
    'index': ((0.086, 0.026), (0.040, 0.025, 0.020), 0.0175),
    'middle': ((0.090, 0.008), (0.045, 0.028, 0.021), 0.018),
    'ring': ((0.087, -0.009), (0.042, 0.026, 0.020), 0.017),
    'little': ((0.078, -0.025), (0.032, 0.020, 0.018), 0.015),
}
ORDER = ('index', 'middle', 'ring', 'little')
FAR_FIRST = ('little', 'ring', 'middle', 'index')  # paint order when the camera is on the thumb side
CMC = (0.016, 0.022, 0.008)        # thumb base in the hand frame, under the thenar bulge
THUMB = (0.046, 0.030, 0.026)      # metacarpal, proximal, distal
THUMB_W = 0.019


def finger(mcp=10.0, pip=15.0, dip=8.0, abd=0.0):
    """Flexion of each joint towards the palm and spread towards the thumb (deg)."""
    return {'mcp': mcp, 'pip': pip, 'dip': dip, 'abd': abd}


def thumb(meta, tip, bend=(-0.2, 0.4, -1.0)):
    """Metacarpal direction, tip target and IP-knuckle hint, all in the hand
    frame (d, r, p)."""
    return {'meta': tuple(meta), 'tip': tuple(tip), 'bend': tuple(bend)}


def hand(sup=0.0, flex=0.0, wrist=(0.0, 0.03, 0.0), fingers=None, thumb_=None):
    """sup: forearm rotation, 0 palm down, 90 thumb up, 180 palm up.
    flex: wrist flexion towards the palm (+) or extension (-)."""
    return {'sup': sup, 'flex': flex, 'wrist': tuple(wrist),
            'fingers': fingers or {n: finger() for n in ORDER},
            'thumb': thumb_ or REST_THUMB}


def finger_chain(name, f):
    """Joint points of one finger in the hand frame."""
    (d, r), bones, _ = FINGERS[name]
    a = math.radians(f['abd'])
    dir0 = (math.cos(a), math.sin(a), 0.0)
    axis = unit(cross(dir0, (0.0, 0.0, 1.0)))  # rotating about it bends towards +p
    pts, q, bend = [(d, r, 0.0)], (d, r, 0.0), 0.0
    for joint, bone in zip(('mcp', 'pip', 'dip'), bones):
        bend += f[joint]
        q = add(q, mul(rotate(dir0, axis, bend), bone))
        pts.append(q)
    return pts


def thumb_chain(t):
    mcp = add(CMC, mul(unit(t['meta']), THUMB[0]))
    ip, tip = two_bone(mcp, t['tip'], THUMB[1], THUMB[2], t['bend'])
    return [CMC, mcp, ip, tip]


def straight_thumb_tip(meta, direction, reach=0.057):
    return add(CMC, mul(unit(meta), THUMB[0]), mul(unit(direction), reach))


REST_META = (0.8, 0.5, 0.25)
REST_THUMB = thumb(REST_META, straight_thumb_tip(REST_META, (0.9, 0.3, 0.3), reach=0.053))


def frame(p):
    """World hand frame (origin, d, r, p) after forearm rotation and wrist flexion."""
    D, R, P = (1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, -1.0, 0.0)  # palm down
    R, P = rotate(R, D, -p['sup']), rotate(P, D, -p['sup'])
    D, P = rotate(D, R, -p['flex']), rotate(P, R, -p['flex'])
    return p['wrist'], D, R, P


def geometry(p):
    o, D, R, P = frame(p)
    world = lambda q: add(o, mul(D, q[0]), mul(R, q[1]), mul(P, q[2]))
    g = {
        'forearm': [add(p['wrist'], (-FORE_LEN, 0.0, 0.0)), p['wrist']],
        'palm': [world((d, r, 0.0)) for d, r in PALM],
        'thumb': [world(q) for q in thumb_chain(p['thumb'])],
        'local': {n: finger_chain(n, p['fingers'][n]) for n in ORDER},
        'frame': (o, D, R, P),
    }
    for n in ORDER:
        g[n] = [world(q) for q in g['local'][n]]
    g['local']['thumb'] = thumb_chain(p['thumb'])
    return g


def to_local(p, q):
    o, D, R, P = frame(p)
    v = sub(q, o)
    return (dot(v, D), dot(v, R), dot(v, P))


# ------------------------------------------------------------------ shared poses
def fist_fingers():
    return {'index': finger(82, 98, 50, -3), 'middle': finger(84, 100, 52, 0),
            'ring': finger(84, 100, 52, 3), 'little': finger(82, 98, 50, 6)}


def open_fingers():
    return {'index': finger(0, 3, 2, 13), 'middle': finger(0, 3, 2, 3),
            'ring': finger(0, 3, 2, -7), 'little': finger(0, 3, 2, -18)}


def fist_thumb(fingers):
    """Thumb tip resting over the middle phalanges of index and middle."""
    a, b = finger_chain('index', fingers['index']), finger_chain('middle', fingers['middle'])
    mid = mul(add(a[2], a[3], b[2]), 1 / 3)
    tip = add(mid, (0.0, 0.0, 0.018))
    return thumb((0.75, 0.25, 0.6), tip, bend=(0.1, 0.6, -0.6))


OPEN_META = (0.55, 0.75, 0.3)
OPEN_THUMB = thumb(OPEN_META, straight_thumb_tip(OPEN_META, (0.6, 0.75, 0.25), reach=0.054))


# ------------------------------------------------------------------ drawing
def samples(scene, track):
    return [(fr, geometry(track.at(fr / FPS))) for fr in list(range(0, scene.frames, STEP)) + [scene.frames]]


def chain_layer(scene, cam, smp, name, get, role, width, closed=False, filled=False):
    keys = [(fr, [cam.px(scene, q) for q in get(g)]) for fr, g in smp]
    items = [path(keys=keys, closed=closed)]
    if filled:
        items.append(fill(role, scene.palette))
    items.append(stroke(role, scene.m(width), scene.palette))
    scene.layer(name, [group(name, items)])


def segment(scene, cam, smp, name, get, width, role='figure', halo=True):
    if halo:
        chain_layer(scene, cam, smp, f'{name} halo', get, 'stage', width + 2 * HALO)
    chain_layer(scene, cam, smp, name, get, role, width)


def draw_hand(scene, cam, smp, order=FAR_FIRST, back=(), thumb_last=True, palm_halo=True, between=None):
    """Forearm, palm plate, fingers in `order` (painted first = farthest),
    thumb. Fingers in `back` use the far-limb colour. `between` is called
    after the fingers and before the thumb (props held in the hand)."""
    segment(scene, cam, smp, 'hand forearm', lambda g: g['forearm'], FORE_W, halo=False)
    if palm_halo:
        chain_layer(scene, cam, smp, 'hand palm halo', lambda g: g['palm'], 'stage', PALM_W + 2 * HALO, closed=True)
    chain_layer(scene, cam, smp, 'hand palm', lambda g: g['palm'], 'figure', PALM_W, closed=True, filled=True)
    if not thumb_last:
        segment(scene, cam, smp, 'hand thumb', lambda g: g['thumb'], THUMB_W)
    for n in order:
        segment(scene, cam, smp, f'hand {n}', lambda g, n=n: g[n], FINGERS[n][2],
                role='figure-back' if n in back else 'figure')
    if between:
        between()
    if thumb_last:
        segment(scene, cam, smp, 'hand thumb', lambda g: g['thumb'], THUMB_W)


def table(scene, cam, edge):
    box(scene, cam, 'table', -1.2, edge, -0.06, 0.0, -0.45, 0.45, top='prop-soft', side='floor', outline='prop')


def hand_points(g):
    return g['palm'] + g['thumb'] + [q for n in ORDER for q in g[n]] + [g['forearm'][1]]


def fit_scene(title, cam, track, width=0.42, pad=0.03, extra=()):
    """Scene of the given width (m) centred on the hand over the whole loop."""
    probe = Scene(title, 0, 1, 0, track.duration)
    pts = [cam.screen(q) for _, g in samples(probe, track) for q in hand_points(g)]
    pts += [cam.screen(q) for q in extra]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    aspect = 720 / 450
    w = max(width, max(xs) - min(xs) + 2 * pad, (max(ys) - min(ys) + 2 * pad) * aspect)
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    return Scene(title, cx - w / 2, cx + w / 2, cy - w / aspect / 2, track.duration)


def check(scene, cam, track, smp, margin_px=6):
    """Loop closes, thumb IK reached, the hand stays inside the frame and the
    forearm stays on the table (it never moves)."""
    assert geometry(track.at(0)) == geometry(track.at(track.duration)), 'open loop'
    assert not IK_ERRORS, f'thumb out of reach: {IK_ERRORS[:3]}'
    fore0 = smp[0][1]['forearm']
    for fr, g in smp:
        assert g['forearm'] == fore0, ('forearm moved', fr)
        assert abs(g['forearm'][0][1] - FORE_W / 2) < 1e-9, ('forearm off the table', fr)
        for q in hand_points(g):
            x, y = cam.px(scene, q)
            assert margin_px < x < scene.w - margin_px and margin_px < y < scene.h - margin_px, ('out of frame', fr, q)


def above_table(smp, edge, tol=0.002):
    """Nothing over the table top sinks into it (segments are tubes)."""
    for fr, g in smp:
        tubes = [(g['palm'], PALM_W), (g['thumb'], THUMB_W)] + [(g[n], FINGERS[n][2]) for n in ORDER]
        for pts, w in tubes:
            for a, b in zip(pts, pts[1:]):
                for k in range(5):
                    q = add(a, mul(sub(b, a), k / 4))
                    if q[0] < edge:
                        assert q[1] - w / 2 > -tol, ('through the table', fr, q)


# ------------------------------------------------------------------ Ex. wrist flexion / extension
EDGE = -0.03  # table edge, just behind the wrist


def wrist_flexion_extension():
    """Forearm on the table, palm down, the hand beyond the edge. The wrist
    bends down slowly, back to neutral, up, and back; fingers stay relaxed."""
    cam = Camera(yaw=25, pitch=38)
    neutral = hand(flex=0.0)
    down, up = hand(flex=58.0), hand(flex=-48.0)
    tr = Track()
    t = chain(tr, [(neutral, 0.6), (down, 1.5), (down, 0.6), (neutral, 1.1), (up, 1.3), (up, 0.6),
                   (neutral, 1.1), (neutral, 0.4)])
    s = fit_scene('Flexão e extensão de punho', cam, tr, width=0.5)
    table(s, cam, EDGE)
    smp = samples(s, tr)
    draw_hand(s, cam, smp)
    markers(s, ['start', 'flex_wrist', 'hold_down', 'back_to_neutral', 'extend_wrist', 'hold_up', 'return', 'rest'], t)
    check(s, cam, tr, smp)
    above_table(smp, EDGE)
    return s


def forearm_pronation_supination():
    """Forearm on the table with the hand beyond the edge, thumb up. The
    forearm turns the palm down, back through thumb up to palm up, and back."""
    cam = Camera(yaw=40, pitch=34)
    relaxed = {n: finger(12, 18, 10) for n in ORDER}
    mid, down, up = (hand(sup=a, fingers=relaxed) for a in (90.0, 0.0, 180.0))
    tr = Track()
    t = chain(tr, [(mid, 0.6), (down, 1.4), (down, 0.6), (mid, 1.1), (up, 1.4), (up, 0.6), (mid, 1.2),
                   (mid, 0.4)])
    s = fit_scene('Pronação e supinação', cam, tr, width=0.4)
    table(s, cam, EDGE)
    smp = samples(s, tr)
    draw_hand(s, cam, smp)
    markers(s, ['start', 'palm_down', 'hold_down', 'thumb_up', 'palm_up', 'hold_up', 'return', 'rest'], t)
    check(s, cam, tr, smp)
    above_table(smp, EDGE)
    return s


# ------------------------------------------------------------------ palm-up scenes
ON_TABLE = 0.35   # table edge beyond the fingertips: the whole hand rests on it
PALM_UP_CAM = (20, 55)


def palm_up(fingers, thumb_, flex=-4.0):
    return hand(sup=180.0, flex=flex, fingers=fingers, thumb_=thumb_)


def relaxed_fingers():
    return {'index': finger(14, 20, 10, 5), 'middle': finger(14, 20, 10, 1),
            'ring': finger(15, 21, 10, -3), 'little': finger(16, 22, 11, -7)}


def palm_up_scene(title, tr, width=0.42, extra=(), view=PALM_UP_CAM):
    cam = Camera(yaw=view[0], pitch=view[1])
    s = fit_scene(title, cam, tr, width=width, extra=extra)
    table(s, cam, ON_TABLE)
    return s, cam


def open_close_hand():
    """Palm up on the table. The hand opens with the fingers spread, closes
    into a gentle fist with the thumb over the fingers, and opens again."""
    rest = palm_up(relaxed_fingers(), REST_THUMB)
    opened = palm_up(open_fingers(), OPEN_THUMB)
    fist = palm_up(fist_fingers(), fist_thumb(fist_fingers()))
    tr = Track()
    t = chain(tr, [(rest, 0.5), (opened, 1.0), (opened, 0.6), (fist, 1.4), (fist, 0.8), (opened, 1.2),
                   (opened, 0.4), (rest, 0.8), (rest, 0.4)])
    s, cam = palm_up_scene('Abrir e fechar a mão', tr)
    smp = samples(s, tr)
    draw_hand(s, cam, smp, order=ORDER)
    markers(s, ['start', 'open', 'hold_open', 'close_fist', 'hold_fist', 'open_again', 'hold_open_again', 'relax',
                'rest'], t)
    check(s, cam, tr, smp)
    above_table(smp, ON_TABLE)
    return s


# Grip: a soft ball rests in the palm; squeezing flattens it against the palm.
BALL_R = 0.031
SQUASH = 0.28   # flattening at full squeeze


def ball(squeeze):
    """Ball semi-axes (d, r, p) and centre in the hand frame. Volume is kept:
    it flattens along p and bulges along d and r."""
    k = 1 - SQUASH * squeeze
    radii = (BALL_R / math.sqrt(k), BALL_R / math.sqrt(k), BALL_R * k)
    return radii, (0.052, 0.0, PALM_W / 2 + radii[2] + 0.001)


def clearance(pts, w, radii, c, skip_start=False):
    """Smallest distance of a tube polyline to the ball centre, in units of
    the ball inflated by the tube radius (1.0 = touching)."""
    best = 9.0
    for a, b in zip(pts, pts[1:]):
        for k in range(1 if skip_start else 0, 5):
            q = add(a, mul(sub(b, a), k / 4))
            best = min(best, math.sqrt(sum(((q[i] - c[i]) / (radii[i] + w / 2)) ** 2 for i in range(3))))
    return best


CURL = (0.9, 1.0, 0.6)  # MCP : PIP : DIP share of a natural finger curl


def wrap(name, radii, c, abd, contact=1.0, limit=110.0):
    """Curls the finger (joints in the CURL proportion) until it reaches the
    ball surface: the largest curl whose phalanges all stay outside."""
    w = FINGERS[name][2]
    curl = lambda th: finger(CURL[0] * th, CURL[1] * th, CURL[2] * th, abd)
    ok = lambda th: clearance(finger_chain(name, curl(th)), w, radii, c) >= contact
    lo, hi = 0.0, limit
    if ok(hi):
        return curl(hi)
    for _ in range(30):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if ok(mid) else (lo, mid)
    return curl(lo)


def grip(squeeze):
    radii, c = ball(squeeze)
    contact = 1.0 - 0.08 * squeeze  # the fingers press slightly into the soft ball
    f = {n: wrap(n, radii, c, a, contact) for n, a in zip(ORDER, (-2, 0, 2, 5))}
    tip = add(c, (0.0, 0.024, radii[2] * 0.75 + THUMB_W / 2 + 0.002))  # thumb pad on the ball's radial top
    return palm_up(f, thumb((0.6, 0.45, 0.65), tip, bend=(0.2, 0.7, -0.4)), flex=-2.0)


def ellipsoid_outline(cam, scene, centre, axes, n=36):
    """Exact orthographic silhouette of an ellipsoid with world semi-axis
    vectors `axes`, via its support points."""
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        w = add(mul(cam.right, math.cos(a)), mul(cam.up, math.sin(a)))
        mt = [dot(v, w) for v in axes]
        norm = math.sqrt(sum(x * x for x in mt))
        q = add(centre, *[mul(v, x / norm) for v, x in zip(axes, mt)])
        pts.append(cam.px(scene, q))
    return pts


def grip_ball_squeeze():
    """Palm up, a soft ball held in the hand. The fingers and thumb squeeze
    it slowly, it flattens, they hold and release."""
    rest_s, squeeze_s, hold_s, release_s, tail = 0.8, 1.2, 1.4, 1.6, 0.8
    t1, t2 = rest_s + squeeze_s, rest_s + squeeze_s + hold_s
    t3, duration = t2 + release_s, t2 + release_s + tail
    level = lambda t: smooth(min(max((t - rest_s) / squeeze_s, 0), 1)) - smooth(min(max((t - t2) / release_s, 0), 1))
    tr = Track()
    tr.add(0, duration, lambda t: grip(level(t)))

    def ball_world(fr):
        t = fr / FPS
        p = tr.at(t)
        o, D, R, P = frame(p)
        radii, c = ball(level(t))
        centre = add(o, mul(D, c[0]), mul(R, c[1]), mul(P, c[2]))
        return centre, (mul(D, radii[0]), mul(R, radii[1]), mul(P, radii[2]))

    view = (25, 25)  # low, from the little-finger side: the ball shows between thumb and fingers
    probe_cam = Camera(yaw=view[0], pitch=view[1])
    extra = [add(ball_world(0)[0], mul(probe_cam.up, BALL_R * 1.2))]
    s, cam = palm_up_scene('Apertar bola', tr, width=0.27, extra=extra, view=view)
    smp = samples(s, tr)

    def draw_ball():
        keys = [(fr, ellipsoid_outline(cam, s, *ball_world(fr))) for fr, _ in smp]
        # 'marker' fill: a 'prop-soft' ball would vanish against the table top
        s.layer('ball', [group('ball', [path(keys=keys, closed=True), fill('marker', s.palette),
                                        stroke('prop', s.m(0.003), s.palette)])])
        for n in ('ring', 'little'):  # the near fingers wrap in front of the ball
            segment(s, cam, smp, f'hand {n}', lambda g, n=n: g[n], FINGERS[n][2])

    draw_hand(s, cam, smp, order=('index', 'middle'), between=draw_ball)
    markers(s, ['start', 'squeeze', 'hold', 'release', 'rest'], [0, rest_s, t1, t2, t3, duration])
    check(s, cam, tr, smp)
    above_table(smp, ON_TABLE)
    for fr, g in smp:  # fingers and thumb never cut deep into the ball
        p = tr.at(fr / FPS)
        radii, c = ball(level(fr / FPS))
        tubes = [(g['local']['thumb'][1:], THUMB_W)] + [(g['local'][n], FINGERS[n][2]) for n in ORDER]
        for pts, w in tubes:
            assert clearance(pts, w, radii, c) > 0.9, ('into the ball', fr)
    return s


# Opposition: the thumb pad meets each fingertip pad in turn.
TOUCH_FLEX = {'index': (55, 50, 20), 'middle': (55, 52, 22), 'ring': (57, 54, 24), 'little': (60, 56, 26)}
PAD_GAP = 0.016  # thumb tip centre to fingertip centre when the pads touch


def pad_point(name, f):
    """Fingertip centre and its pad normal (palmar side of the last phalanx)."""
    pts = finger_chain(name, f)
    a = math.radians(f['abd'])
    dir0 = (math.cos(a), math.sin(a), 0.0)
    axis = unit(cross(dir0, (0.0, 0.0, 1.0)))
    normal = rotate((0.0, 0.0, 1.0), axis, f['mcp'] + f['pip'] + f['dip'])
    return pts[-1], normal


def touch(name):
    f = {n: finger(6, 8, 4, a) for n, a in zip(ORDER, (6, 1, -3, -8))}
    f[name] = finger(*TOUCH_FLEX[name], f[name]['abd'])
    tip, normal = pad_point(name, f[name])
    target = add(tip, mul(normal, PAD_GAP))
    meta = unit(add(unit(sub(target, CMC)), (0.0, 0.25, 0.35)))
    return palm_up(f, thumb(meta, target, bend=(0.2, 0.8, -0.3)))


def thumb_opposition():
    """Palm up. The thumb tip touches the tip of the index, middle, ring and
    little fingers in turn, then the hand opens back to rest."""
    rest = palm_up({n: finger(6, 8, 4, a) for n, a in zip(ORDER, (6, 1, -3, -8))}, OPEN_THUMB)
    poses = [touch(n) for n in ORDER]
    steps = [(rest, 0.5)]
    for p in poses:
        steps += [(p, 0.7), (p, 0.45)]
    steps += [(rest, 1.0), (rest, 0.5)]
    tr = Track()
    t = chain(tr, steps)
    s, cam = palm_up_scene('Oposição do polegar', tr)
    smp = samples(s, tr)
    draw_hand(s, cam, smp, order=ORDER)
    names = ['start']
    for n in ORDER:
        names += [f'to_{n}', f'touch_{n}']
    markers(s, names + ['open', 'rest'], t)
    check(s, cam, tr, smp)
    above_table(smp, ON_TABLE)
    holds = [(n, t[2 + 2 * i], t[3 + 2 * i]) for i, n in enumerate(ORDER)]
    for n, a, b in holds:  # pads meet during each hold
        for fr in range(int(a * FPS) + 1, int(b * FPS)):
            g = geometry(tr.at(fr / FPS))
            d = length(sub(g['thumb'][-1], g[n][-1]))
            assert abs(d - PAD_GAP) < 0.003, ('pads apart', n, fr, round(d, 4))
    for fr, g in smp:  # the thumb crosses in front of the palm, never through it
        for q in g['local']['thumb'][2:]:
            if q[0] > 0.02 and abs(q[1]) < 0.035:  # over the palm plate
                assert q[2] > PALM_W / 2 + THUMB_W / 2 - 0.004, ('thumb through the palm', fr, q)
    return s


SCENES = {
    'wrist_flexion_extension': wrist_flexion_extension,
    'forearm_pronation_supination': forearm_pronation_supination,
    'grip_ball_squeeze': grip_ball_squeeze,
    'open_close_hand': open_close_hand,
    'thumb_opposition': thumb_opposition,
}
