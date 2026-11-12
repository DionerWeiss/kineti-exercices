#!/usr/bin/env python3
"""Sample physiotherapy loops drawn as a flat illustration.

Side-view figure: coral tank, charcoal shorts, teal-soled shoes, blank face,
soft ground shadow. Original drawing; the pose language follows the library
exercises, not any third-party file.
"""

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "examples" / "estilo"

W, H = 640, 640
FPS = 30
N = 180  # 6 s, looped
GROUND = 518

SKIN = [0.973, 0.800, 0.675, 1]
SKIN_FAR = [0.902, 0.706, 0.576, 1]
HAIR = [0.165, 0.145, 0.125, 1]
TANK = [0.945, 0.455, 0.333, 1]
TANK_SIDE = [0.816, 0.345, 0.251, 1]
TANK_FAR = [0.969, 0.647, 0.576, 1]
SHORTS = [0.176, 0.192, 0.216, 1]
SHORTS_FAR = [0.361, 0.384, 0.420, 1]
SHOE = [0.216, 0.235, 0.267, 1]
SOLE = [0.180, 0.710, 0.640, 1]
MAT = [0.902, 0.929, 0.949, 1]
MAT_EDGE = [0.820, 0.863, 0.898, 1]
SHADOW = [0.620, 0.670, 0.720, 1]
CHAIR = [0.816, 0.839, 0.867, 1]
CHAIR_DK = [0.655, 0.690, 0.725, 1]
BED = [0.925, 0.945, 0.960, 1]
BED_DK = [0.780, 0.820, 0.855, 1]
PILLOW = [0.965, 0.972, 0.980, 1]
BENCH = [0.835, 0.855, 0.875, 1]

THIGH, SHIN, FOOT = 86, 82, 34
UARM, FARM = 58, 52
TORSO, NECK, HEAD = 108, 16, 28


def polar(o, length, ang):
    return (o[0] + length * math.cos(ang), o[1] + length * math.sin(ang))


def lerp(a, b, u):
    return (a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u)


def ang(a, b):
    return math.atan2(b[1] - a[1], b[0] - a[0])


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def env(t, spans):
    """Piecewise smoothstep. spans are (duration, value) and sum to 1."""
    x = t % 1.0
    acc = 0.0
    prev = spans[-1][1]
    for dur, val in spans:
        if x <= acc + dur + 1e-9:
            local = 0 if dur <= 0 else (x - acc) / dur
            return prev + (val - prev) * ease(local)
        acc += dur
        prev = val
    return prev


def ik(hip, foot, l1, l2, up=True):
    dx, dy = foot[0] - hip[0], foot[1] - hip[1]
    d = math.hypot(dx, dy)
    d = min(max(d, abs(l1 - l2) + 1), l1 + l2 - 1)
    a = (l1 * l1 - l2 * l2 + d * d) / (2 * d)
    h = math.sqrt(max(l1 * l1 - a * a, 0))
    ux, uy = dx / d, dy / d
    px, py = -uy, ux
    if (py > 0) == up:
        px, py = -px, -py
    return (hip[0] + a * ux + h * px, hip[1] + a * uy + h * py)


def capsule(a, b, ra, rb, segs=7):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy) or 1.0
    px, py = -dy / L, dx / L
    ang0 = math.atan2(py, px)
    pts = []
    for i in range(segs + 1):
        t = ang0 + math.pi * i / segs
        pts.append((b[0] + rb * math.cos(t), b[1] + rb * math.sin(t)))
    for i in range(segs + 1):
        t = ang0 + math.pi + math.pi * i / segs
        pts.append((a[0] + ra * math.cos(t), a[1] + ra * math.sin(t)))
    return pts


def ribbon(pts, radii, segs=6):
    left, right = [], []
    for i, p in enumerate(pts):
        if i == 0:
            d = (pts[1][0] - p[0], pts[1][1] - p[1])
        elif i == len(pts) - 1:
            d = (p[0] - pts[i - 1][0], p[1] - pts[i - 1][1])
        else:
            d = (pts[i + 1][0] - pts[i - 1][0], pts[i + 1][1] - pts[i - 1][1])
        L = math.hypot(d[0], d[1]) or 1.0
        px, py = -d[1] / L, d[0] / L
        r = radii[i]
        left.append((p[0] + px * r, p[1] + py * r))
        right.append((p[0] - px * r, p[1] - py * r))
    start, end = pts[0], pts[-1]
    d0 = (pts[1][0] - start[0], pts[1][1] - start[1])
    L0 = math.hypot(*d0) or 1.0
    back = math.atan2(-d0[1] / L0, -d0[0] / L0)
    d1 = (end[0] - pts[-2][0], end[1] - pts[-2][1])
    L1 = math.hypot(*d1) or 1.0
    fwd = math.atan2(d1[1] / L1, d1[0] / L1)
    cap_b, cap_a = [], []
    for i in range(1, segs):
        t = fwd - math.pi / 2 + math.pi * i / segs
        cap_b.append((end[0] + radii[-1] * math.cos(t), end[1] + radii[-1] * math.sin(t)))
    for i in range(1, segs):
        t = back - math.pi / 2 + math.pi * i / segs
        cap_a.append((start[0] + radii[0] * math.cos(t), start[1] + radii[0] * math.sin(t)))
    return left + cap_b + right[::-1] + cap_a


def tube(pts, radii, cap0=True, cap1=True, join_n=4, cap_n=5):
    """One filled limb. Vertex count stays fixed for a given point count,
    so the shape can be keyframed."""
    pts = [(float(p[0]), float(p[1])) for p in pts]
    radii = [float(r) for r in radii]
    prev = (1.0, 0.0)
    dirs = []
    for i in range(len(pts) - 1):
        dx = pts[i + 1][0] - pts[i][0]
        dy = pts[i + 1][1] - pts[i][1]
        length = math.hypot(dx, dy)
        if length < 0.75:
            dirs.append(prev)
        else:
            prev = (dx / length, dy / length)
            dirs.append(prev)
    if not dirs:
        dirs = [(1.0, 0.0)]

    def left_normal(d):
        return (-d[1], d[0])

    def sweep_to(a0, a1):
        return (a1 - a0 + math.pi) % (2 * math.pi) - math.pi

    left, right = [], []
    for i, p in enumerate(pts):
        r = radii[i]
        if i == 0:
            nrm = left_normal(dirs[0])
        elif i == len(pts) - 1:
            nrm = left_normal(dirs[-1])
        else:
            n0 = left_normal(dirs[i - 1])
            n1 = left_normal(dirs[i])
            a0 = math.atan2(n0[1], n0[0])
            sw = sweep_to(a0, math.atan2(n1[1], n1[0]))
            for k in range(1, join_n + 1):
                t = a0 + sw * (k / (join_n + 1))
                left.append((p[0] + r * math.cos(t), p[1] + r * math.sin(t)))
                right.append((p[0] + r * math.cos(t + math.pi), p[1] + r * math.sin(t + math.pi)))
            nrm = n1
        left.append((p[0] + nrm[0] * r, p[1] + nrm[1] * r))
        right.append((p[0] - nrm[0] * r, p[1] - nrm[1] * r))

    def cap(center, r, a_from, a_to):
        out = []
        for k in range(1, cap_n + 1):
            t = a_from + (a_to - a_from) * (k / (cap_n + 1))
            out.append((center[0] + r * math.cos(t), center[1] + r * math.sin(t)))
        return out

    a0 = math.atan2(left_normal(dirs[0])[1], left_normal(dirs[0])[0])
    a1 = math.atan2(left_normal(dirs[-1])[1], left_normal(dirs[-1])[0])
    # End cap passes through the forward direction; start cap through the back.
    end_cap = cap(pts[-1], radii[-1], a1, a1 - math.pi) if cap1 else []
    start_cap = cap(pts[0], radii[0], a0 + math.pi, a0) if cap0 else []
    return left + end_cap + right[::-1] + start_cap


def spine(hip, torso, bend):
    end = polar(hip, TORSO, torso)
    mid = lerp(hip, end, 0.5)
    px, py = -math.sin(torso), math.cos(torso)
    mid = (mid[0] + px * bend, mid[1] + py * bend)
    pts = []
    for i in range(5):
        t = i / 4
        u = 1 - t
        pts.append((
            u * u * hip[0] + 2 * u * t * mid[0] + t * t * end[0],
            u * u * hip[1] + 2 * u * t * mid[1] + t * t * end[1],
        ))
    return end, pts


def limb(hip, thigh_a, shin_a, foot_a):
    knee = polar(hip, THIGH, thigh_a)
    ankle = polar(knee, SHIN, shin_a)
    toe = polar(ankle, FOOT, foot_a)
    return knee, ankle, toe


def arm(sh, a, e):
    elbow = polar(sh, UARM, a)
    wrist = polar(elbow, FARM, e)
    return elbow, wrist


class Fig:
    def __init__(self, hip, torso, nose, bend, near, far, narm, farm, end=None, far_hip=None, front=1):
        self.hip = hip
        self.torso = torso
        self.nose = nose
        self.bend = bend
        self.front = front
        self.near = near  # knee ankle toe
        self.far = far
        self.narm = narm
        self.farm = farm
        if end is None:
            self.shoulder, self.back = spine(hip, torso, bend)
        else:
            self.shoulder = end
            mid = lerp(hip, end, 0.5)
            px, py = -math.sin(torso), math.cos(torso)
            mid = (mid[0] + px * bend, mid[1] + py * bend)
            self.back = []
            for i in range(5):
                t = i / 4
                u = 1 - t
                self.back.append((
                    u * u * hip[0] + 2 * u * t * mid[0] + t * t * end[0],
                    u * u * hip[1] + 2 * u * t * mid[1] + t * t * end[1],
                ))
        neck = ang(self.back[-2], self.shoulder)
        self.head = polar(self.shoulder, NECK + HEAD * 0.42, neck)
        self.far_hip = far_hip or (hip[0] - 5, hip[1] - 7)


def shift(p, ox=-7, oy=-12):
    return (p[0] + ox, p[1] + oy)


# --- exercises -----------------------------------------------------------

LY = 478  # back rests on the mat


def heel_slides(t):
    u = env(t, [(0.14, 0), (0.28, 1), (0.16, 1), (0.28, 0), (0.14, 0)])
    hip = (340, LY)
    reach = THIGH + SHIN - 8
    foot = (hip[0] + reach * (1 - 0.55 * u), LY + 4)
    knee = ik(hip, foot, THIGH, SHIN, up=True)
    far_hip = (hip[0] - 4, hip[1] - 8)
    far_foot = (far_hip[0] + reach, far_hip[1] + 4)
    far_knee = ik(far_hip, far_foot, THIGH, SHIN, up=True)
    fig = Fig(
        hip, math.pi, -math.pi / 2, 2,
        (knee, foot, polar(foot, FOOT, -0.35)),
        (far_knee, far_foot, polar(far_foot, FOOT, -0.3)),
        (0, 0), (0, 0), far_hip=far_hip,
    )
    fig.narm = arm(fig.shoulder, 0.25, 0.15)
    fig.farm = arm(shift(fig.shoulder, -4, -6), 0.18, 0.1)
    return fig


def bridge(t):
    u = env(t, [(0.12, 0), (0.26, 1), (0.20, 1), (0.28, 0), (0.14, 0)])
    shoulder = (214, LY)
    # Hip rises and shifts toward the shoulders so the torso length stays put
    # and the knees stay bent instead of locking into a straight slope.
    hip = (322 - 46 * u, LY - 88 * u)
    torso = ang(hip, shoulder)
    foot = (392, LY + 6)
    knee = ik(hip, foot, THIGH, SHIN, up=True)
    far_hip = (hip[0] - 6, hip[1] - 6)
    far_foot = (386, LY + 2)
    far_knee = ik(far_hip, far_foot, THIGH, SHIN, up=True)
    fig = Fig(hip, torso, -math.pi / 2, 6 * u, (knee, foot, polar(foot, FOOT, -0.9)),
              (far_knee, far_foot, polar(far_foot, FOOT, -0.85)), (0, 0), (0, 0),
              end=shoulder, far_hip=far_hip)
    fig.narm = arm(fig.shoulder, 0.7, 0.35)
    fig.farm = arm(shift(fig.shoulder, -4, -6), 0.5, 0.25)
    return fig


def clamshell(t):
    u = env(t, [(0.12, 0), (0.26, 1), (0.18, 1), (0.28, 0), (0.16, 0)])
    hip = (340, LY - 4)
    # Top knee swings from the mat up toward the ceiling. Foot stays tucked.
    thigh_a = 0.22 * (1 - u) + (-1.2) * u
    knee = polar(hip, 80, thigh_a)
    foot = (hip[0] + 22, LY + 16)
    toe = (foot[0] + 26, foot[1] + 2)
    far_hip = (hip[0] - 2, hip[1] + 8)
    far_knee = polar(far_hip, 76, 0.28)
    far_foot = (far_hip[0] + 18, far_hip[1] + 14)
    fig = Fig(hip, math.pi, -math.pi / 2, 0,
              (knee, foot, toe),
              (far_knee, far_foot, (far_foot[0] + 20, far_foot[1] + 3)),
              (0, 0), (0, 0), far_hip=far_hip)
    # Both arms rest along the side, on the mat.
    fig.narm = arm(fig.shoulder, 0.1, 0.35)
    fig.farm = arm((fig.shoulder[0] - 2, fig.shoulder[1] - 4), 0.02, 0.22)
    return fig


def knee_extension(t):
    u = env(t, [(0.14, 0), (0.28, 1), (0.16, 1), (0.28, 0), (0.14, 0)])
    hip = (300, 400)
    thigh = 0.12
    shin = (math.pi / 2 + 0.06) * (1 - u) + 0.18 * u
    foot_a = shin - 1.15
    knee, ankle, toe = limb(hip, thigh, shin, foot_a)
    far_hip = (hip[0] - 6, hip[1] - 6)
    fk, fa, ft = limb(far_hip, 0.16, math.pi / 2 + 0.04, -0.2)
    fig = Fig(hip, -math.pi / 2 + 0.04, 0.0, 0,
              (knee, ankle, toe), (fk, fa, ft), (0, 0), (0, 0), far_hip=far_hip)
    fig.narm = arm(fig.shoulder, 1.15, 1.35)
    fig.farm = arm((fig.shoulder[0] - 6, fig.shoulder[1] - 4), 1.25, 1.45)
    return fig


def ankle_pumps(t):
    lift = math.sin(t * 2 * math.pi) * 0.5 + 0.5  # 0 toes away, 1 toes toward the head
    hip = (328, 452)
    knee, ankle, _ = limb(hip, 0.02, 0.03, 0)
    toe = polar(ankle, FOOT, 0.35 - 1.15 * lift)
    far_hip = (hip[0] - 4, hip[1] - 7)
    fk, fa, _ = limb(far_hip, 0.0, 0.02, 0)
    ft = polar(fa, FOOT, 0.3 - 1.05 * lift)
    fig = Fig(hip, math.pi, -math.pi / 2, 0,
              (knee, ankle, toe), (fk, fa, ft), (0, 0), (0, 0), far_hip=far_hip)
    fig.narm = arm(fig.shoulder, 0.35, 0.2)
    fig.farm = arm((fig.shoulder[0] - 4, fig.shoulder[1] - 6), 0.22, 0.12)
    return fig


def cat_camel(t):
    u = math.sin(t * 2 * math.pi)  # +1 cat (back up), -1 camel
    hip = (400, 424)
    shoulder = (230, 418 - 10 * u)
    hand = (214, 512)
    knee_p = (412, 510)
    bend = 92 * u
    torso = ang(hip, shoulder)
    far_hip = (hip[0] - 8, hip[1] - 6)
    far_knee = (knee_p[0] - 14, knee_p[1] - 6)
    fig = Fig(hip, torso, math.pi + 0.45 * u, bend,
              (knee_p, (knee_p[0] - 6, knee_p[1] + 2), (knee_p[0] + 22, knee_p[1] + 2)),
              (far_knee, (far_knee[0] - 6, far_knee[1] + 2), (far_knee[0] + 18, far_knee[1] + 2)),
              (0, 0), (0, 0), end=shoulder, far_hip=far_hip, front=-1)
    elbow = lerp(shoulder, hand, 0.5)
    elbow = (elbow[0] + 6, elbow[1] - 6)
    fig.narm = (elbow, hand)
    fig.farm = ((elbow[0] - 10, elbow[1] - 6), (hand[0] - 12, hand[1] - 6))
    return fig


def single_leg(t):
    u = env(t, [(0.16, 0), (0.24, 1), (0.22, 1), (0.22, 0), (0.16, 0)])
    hip = (250, GROUND - 20 - SHIN - THIGH)
    thigh = math.pi / 2 * (1 - u) + 0.35 * u
    shin = math.pi / 2 * (1 - u) + 1.2 * u
    knee, ankle, toe = limb(hip, thigh, shin, 0.05 if u < 0.5 else -0.4)
    far_hip = (hip[0] - 8, hip[1] - 4)
    fk, fa, ft = limb(far_hip, math.pi / 2, math.pi / 2, 0.0)
    fig = Fig(hip, -math.pi / 2, 0.0, 0,
              (knee, ankle, toe), (fk, fa, ft), (0, 0), (0, 0), far_hip=far_hip)
    # Hand reaches a counter that stays clear of the lifted knee.
    fig.narm = arm(fig.shoulder, 1.35 * (1 - u) + 0.22 * u, 1.55 * (1 - u) + 0.38 * u)
    fig.farm = arm((fig.shoulder[0] - 8, fig.shoulder[1] - 2), 1.45, 1.7)
    return fig


def sit_stand(t):
    u = env(t, [(0.12, 0), (0.16, 0.25), (0.18, 1), (0.16, 1), (0.16, 0.25), (0.12, 0), (0.10, 0)])
    sit = (300, 404)
    stand = (324, GROUND - 18 - SHIN - THIGH)
    hip = lerp(sit, stand, ease(u))
    torso = (-1.42) * (1 - u) + (-math.pi / 2) * u
    thigh = 0.08 * (1 - u) + (math.pi / 2) * u
    shin = (math.pi / 2) * (1 - u) + (math.pi / 2) * u
    knee, ankle, toe = limb(hip, thigh, shin, -0.15)
    far_hip = (hip[0] - 6, hip[1] - 5)
    fk, fa, ft = limb(far_hip, thigh + 0.03, shin, -0.1)
    fig = Fig(hip, torso, 0.0, 0,
              (knee, ankle, toe), (fk, fa, ft), (0, 0), (0, 0), far_hip=far_hip)
    # Hands rest on the thighs while seated and hang at the sides when standing.
    fig.narm = arm(fig.shoulder, 0.95 * (1 - u) + 1.55 * u, 0.7 * (1 - u) + 1.7 * u)
    fig.farm = arm((fig.shoulder[0] - 5, fig.shoulder[1] - 4), 1.15 * (1 - u) + 1.65 * u, 0.85 * (1 - u) + 1.8 * u)
    return fig


EXERCISES = [
    ("heel_slides", "Deslizamento do calcanhar", "mat", heel_slides),
    ("bridge", "Ponte", "mat", bridge),
    ("side_lying_clamshell", "Concha deitado de lado", "mat", clamshell),
    ("seated_knee_extension", "Extensão de joelho sentado", "chair", knee_extension),
    ("ankle_pumps", "Bombeamento de tornozelos", "bed", ankle_pumps),
    ("cat_camel", "Gato-camelo", "mat", cat_camel),
    ("single_leg_stance", "Apoio unipodal", "bench", single_leg),
    ("sit_to_stand_exercise", "Sentar e levantar", "chair", sit_stand),
]


# --- lottie --------------------------------------------------------------

def rnd(pts):
    return [[round(x, 1), round(y, 1)] for x, y in pts]


def smooth_handles(pts, tension=0.18):
    """Closed-curve handles so the outline reads as a vector shape, not a polygon."""
    n = len(pts)
    inn, out = [], []
    for i in range(n):
        prev, nxt = pts[(i - 1) % n], pts[(i + 1) % n]
        ox = (nxt[0] - prev[0]) * tension
        oy = (nxt[1] - prev[1]) * tension
        out.append([round(ox, 2), round(oy, 2)])
        inn.append([round(-ox, 2), round(-oy, 2)])
    return inn, out


def path_keys(samples):
    keys = []
    for i, (fr, pts) in enumerate(samples):
        inn, out = smooth_handles(pts)
        key = {"t": fr, "s": [{"i": inn, "o": out, "v": rnd(pts), "c": True}]}
        if i < len(samples) - 1:
            key["i"] = {"x": 1, "y": 1}
            key["o"] = {"x": 0, "y": 0}
        keys.append(key)
    return keys


def point_keys(samples):
    keys = []
    for i, (fr, p) in enumerate(samples):
        key = {"t": fr, "s": [round(p[0], 1), round(p[1], 1)]}
        if i < len(samples) - 1:
            key["i"] = {"x": 1, "y": 1}
            key["o"] = {"x": 0, "y": 0}
        keys.append(key)
    return keys


def group_path(name, keys, color, opacity=100):
    return {
        "ty": "gr", "nm": name,
        "it": [
            {"ty": "sh", "nm": "path", "ks": {"a": 1, "k": keys}},
            {"ty": "fl", "nm": "fill", "c": {"a": 0, "k": color}, "o": {"a": 0, "k": opacity}, "r": 1},
            tr(),
        ],
    }


def group_static(name, pts, color, opacity=100):
    return {
        "ty": "gr", "nm": name,
        "it": [
            {"ty": "sh", "nm": "path", "ks": {"a": 0, "k": {
                "i": smooth_handles(pts)[0], "o": smooth_handles(pts)[1], "v": rnd(pts), "c": True}}},
            {"ty": "fl", "nm": "fill", "c": {"a": 0, "k": color}, "o": {"a": 0, "k": opacity}, "r": 1},
            tr(),
        ],
    }


def group_ellipse(name, keys, size, color, opacity=100):
    return {
        "ty": "gr", "nm": name,
        "it": [
            {"ty": "el", "nm": "ellipse", "p": {"a": 1, "k": keys}, "s": {"a": 0, "k": size}},
            {"ty": "fl", "nm": "fill", "c": {"a": 0, "k": color}, "o": {"a": 0, "k": opacity}, "r": 1},
            tr(),
        ],
    }


def tr():
    return {"ty": "tr", "nm": "tr", "p": {"a": 0, "k": [0, 0]}, "a": {"a": 0, "k": [0, 0]},
            "s": {"a": 0, "k": [100, 100]}, "r": {"a": 0, "k": 0}, "o": {"a": 0, "k": 100},
            "sk": {"a": 0, "k": 0}, "sa": {"a": 0, "k": 0}}


def layer(name, shapes, ind):
    return {
        "ddd": 0, "ty": 4, "nm": name, "sr": 1,
        "ks": {"o": {"a": 0, "k": 100}, "r": {"a": 0, "k": 0}, "p": {"a": 0, "k": [0, 0, 0]},
               "a": {"a": 0, "k": [0, 0, 0]}, "s": {"a": 0, "k": [100, 100, 100]}},
        "ao": 0, "shapes": shapes, "ip": 0, "op": N, "st": 0, "bm": 0, "ind": ind,
    }


def shorts_end(hip, knee):
    return lerp(hip, knee, 0.58)


def samples(fn, step=3):
    frames = list(range(0, N, step)) + [N]
    return [(fr, fn(fr / N)) for fr in frames]


def hair_center(head, neck_dir):
    # Cap sits on the skull, mostly covered by the face circle.
    top = (math.cos(neck_dir), math.sin(neck_dir))
    return (head[0] + top[0] * 13, head[1] + top[1] * 13)


def rounded_rect(cx, cy, w, h, r, segs=4):
    x0, y0, x1, y1 = cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2
    r = min(r, w / 2, h / 2)
    corners = [
        ((x1 - r, y0 + r), -math.pi / 2),
        ((x1 - r, y1 - r), 0),
        ((x0 + r, y1 - r), math.pi / 2),
        ((x0 + r, y0 + r), math.pi),
    ]
    pts = []
    for (c, a0) in corners:
        for i in range(segs + 1):
            t = a0 + (math.pi / 2) * i / segs
            pts.append((c[0] + r * math.cos(t), c[1] + r * math.sin(t)))
    return pts


def prop_shapes(kind, fig0):
    hip = fig0.hip
    if kind == "mat":
        return [
            group_static("mat", rounded_rect(320, GROUND - 8, 470, 22, 8), MAT),
            group_static("mat-edge", rounded_rect(320, GROUND + 6, 470, 14, 6), MAT_EDGE),
        ]
    if kind == "bed":
        return [
            group_static("bed-leg", rounded_rect(220, GROUND + 8, 10, 36, 2), BED_DK),
            group_static("bed-leg-2", rounded_rect(470, GROUND + 8, 10, 36, 2), BED_DK),
            group_static("bed", rounded_rect(330, GROUND - 28, 520, 28, 8), BED),
            group_static("mattress", rounded_rect(330, GROUND - 46, 500, 16, 7), MAT),
            group_static("pillow", rounded_rect(fig0.head[0] - 4, fig0.head[1] + 18, 78, 28, 12), PILLOW),
        ]
    if kind == "chair":
        seat_y = hip[1] + 18
        seat_x = hip[0] + 6
        return [
            group_static("chair-leg", rounded_rect(seat_x - 36, seat_y + 52, 10, 78, 2), CHAIR_DK),
            group_static("chair-leg-2", rounded_rect(seat_x + 42, seat_y + 52, 10, 78, 2), CHAIR_DK),
            group_static("chair-back", rounded_rect(seat_x - 58, seat_y - 48, 12, 108, 4), CHAIR),
            group_static("chair-seat", rounded_rect(seat_x, seat_y, 128, 16, 4), CHAIR),
        ]
    if kind == "bench":
        return [
            group_static("bench-leg", rounded_rect(500, 390, 14, 250, 3), CHAIR_DK),
            group_static("bench-top", rounded_rect(445, 258, 150, 16, 4), BENCH),
        ]
    return []


def belly(fig):
    """Screen direction of the front of the body (the chest faces this way)."""
    s = fig.front
    return (-math.sin(fig.torso) * s, math.cos(fig.torso) * s)


def crown(fig):
    return (
        math.cos(ang(fig.shoulder, fig.head)),
        math.sin(ang(fig.shoulder, fig.head)),
    )


def build(fn):
    step = 3
    frames = list(range(0, N, step)) + [N]
    figs = [(fr, fn(fr / N)) for fr in frames]

    def seq(getter):
        paths = [getter(fig) for _, fig in figs]
        n0 = len(paths[0])
        for i, path in enumerate(paths):
            if len(path) != n0:
                raise RuntimeError(f"vertex count changed {n0} -> {len(path)} at sample {i}")
        return path_keys([(fr, path) for (fr, _), path in zip(figs, paths)])

    def pts(getter):
        return point_keys([(fr, getter(fig)) for fr, fig in figs])

    def buried(origin, outer):
        # Pull the start of a limb back under the torso so the joint disappears.
        return lerp(outer, origin, 1.08)

    def arm_path(fig, which):
        if which == "near":
            shoulder, (elbow, wrist) = fig.shoulder, fig.narm
            radii = (9, 7, 7.5, 10)
        else:
            shoulder, (elbow, wrist) = shift(fig.shoulder, -8, -10), fig.farm
            radii = (7.5, 6, 6.5, 10)
        hand = lerp(elbow, wrist, 1.28)
        return tube([buried(shoulder, elbow), elbow, wrist, hand], radii, cap0=False, cap1=True)

    def leg_path(fig, which):
        if which == "near":
            hip, (knee, ankle, _toe) = fig.hip, fig.near
            radii = (16, 13, 10)
        else:
            hip, (knee, ankle, _toe) = fig.far_hip, fig.far
            radii = (13, 11, 8.5)
        return tube([hip, knee, ankle], radii, cap0=False, cap1=True)

    def shorts_path(fig, which):
        if which == "near":
            hip, knee = fig.hip, fig.near[0]
            radii = (18, 13)
        else:
            hip, knee = fig.far_hip, fig.far[0]
            radii = (14, 10)
        hem = lerp(hip, knee, 0.64)
        waist = lerp(knee, hip, 1.1)
        return tube([waist, hip, hem], [radii[0] + 2, radii[0], radii[1]], cap0=True, cap1=True)

    def shoe_upper(ankle, toe):
        mid = lerp(ankle, toe, 0.45)
        return tube([ankle, mid, toe], (13, 14, 11), cap0=True, cap1=True)

    def shoe_sole(ankle, toe):
        dx, dy = toe[0] - ankle[0], toe[1] - ankle[1]
        length = math.hypot(dx, dy) or 1.0
        px, py = -dy / length, dx / length
        if py < 0:
            px, py = -px, -py

        def drop(p, k):
            return (p[0] + px * k, p[1] + py * k)

        mid = lerp(ankle, toe, 0.5)
        return tube([drop(ankle, 8), drop(mid, 9), drop(toe, 7)], (6, 6.5, 5.5), cap0=True, cap1=True)

    def torso_path(fig, radii, shift_px):
        bx, by = belly(fig)
        pts = [(p[0] + bx * shift_px, p[1] + by * shift_px) for p in fig.back]
        return tube(pts, radii, cap0=True, cap1=True)

    def hair_place(fig):
        bx, by = belly(fig)
        cx, cy = crown(fig)
        # Skull sits toward the back and the crown; the face covers the front.
        return (fig.head[0] - bx * 8 + cx * 5, fig.head[1] - by * 8 + cy * 5)

    def face_place(fig):
        bx, by = belly(fig)
        cx, cy = crown(fig)
        return (fig.head[0] + bx * 13 - cx * 3, fig.head[1] + by * 13 - cy * 3)

    # Lottie paints the first shape in a layer on top.
    near = [
        group_ellipse("face", pts(face_place), [68, 64], SKIN),
        group_ellipse("hair", pts(hair_place), [86, 80], HAIR),
        group_path("neck", seq(lambda f: tube(
            [f.shoulder, lerp(f.shoulder, f.head, 0.62)], [10, 11], cap0=True, cap1=True)), SKIN),
        group_path("sole", seq(lambda f: shoe_sole(f.near[1], f.near[2])), SOLE),
        group_path("shoe", seq(lambda f: shoe_upper(f.near[1], f.near[2])), SHOE),
        group_path("arm", seq(lambda f: arm_path(f, "near")), SKIN),
        group_path("shorts", seq(lambda f: shorts_path(f, "near")), SHORTS),
        group_path("torso", seq(lambda f: torso_path(f, [22, 17, 26, 20, 11], 16)), TANK),
        group_path("torso-side", seq(lambda f: torso_path(f, [34, 28, 38, 32, 18], 0)), TANK_SIDE),
        group_path("leg", seq(lambda f: leg_path(f, "near")), SKIN),
    ]
    far = [
        group_path("sole", seq(lambda f: shoe_sole(f.far[1], f.far[2])), SOLE),
        group_path("shoe", seq(lambda f: shoe_upper(f.far[1], f.far[2])), SHOE),
        group_path("shorts", seq(lambda f: shorts_path(f, "far")), SHORTS_FAR),
        group_path("arm", seq(lambda f: arm_path(f, "far")), SKIN_FAR),
        group_path("leg", seq(lambda f: leg_path(f, "far")), SKIN_FAR),
    ]

    prop = prop_shapes(PROP, figs[0][1])
    shadow = group_ellipse(
        "shadow",
        pts(lambda f: ((f.hip[0] + f.near[2][0]) / 2, GROUND + 8)),
        [170, 26], SHADOW, opacity=40)

    layers = [
        layer("near", near, 1),
        layer("far", far, 2),
        layer("prop", prop, 3),
        layer("shadow", [shadow], 4),
    ]
    return {
        "v": "5.7.4", "fr": FPS, "ip": 0, "op": N, "w": W, "h": H,
        "nm": NAME, "ddd": 0, "assets": [], "layers": layers,
    }


PROP = "mat"
NAME = ""


def main():
    global PROP, NAME
    OUT.mkdir(parents=True, exist_ok=True)
    for slug, name, kind, fn in EXERCISES:
        PROP, NAME = kind, name
        data = build(fn)
        path = OUT / f"{slug}.json"
        path.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
        print(f"{slug:28} {path.stat().st_size/1024:7.1f} KB")


if __name__ == "__main__":
    main()
