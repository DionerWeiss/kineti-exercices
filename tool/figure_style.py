"""Library figure style: the rig's figure, redrawn for patients.

Same skeleton and motion as the clinical rig; only the painting changes:
  - shaped feet (heel, sole, toes, instep) instead of a short stroke;
  - a torso with volume (pelvis, waist, chest, shoulders) built from
    cross-sections, so belly, chest and lordosis read as a change of shape;
  - a neck and a nose, so the facing direction reads;
  - the working segments of each exercise in `figure-active`
    (colorScheme.tertiary), the far side in `figure-active-back`.

The rig lives in the app repository and also draws the app's clinical tests,
so this module does not edit it: importing it (through `_rig`) swaps
figure3d.add_figure and kineti_lottie.Scene.figure for painters that fall
back to the originals unless a library exercise is being built.
`use(slug)` selects the style for one build; `use(None)` restores the rig's
own figure (the clinical-test references keep it, to match the app).
"""

import math
from contextlib import contextmanager

import figure3d
import kineti_lottie as kl
from figure3d import sample
from kineti_lottie import FPS, HALO, HEAD_R, SHOULDER, STEP, W_ARM, W_FOOT, W_LEG, ellipse, fill, group, path, stroke

for _pal, _act, _act_back in ((kl.LIGHT, '#FF6D00', '#FFC08F'), (kl.DARK, '#FF8A3D', '#8A4A22')):
    _pal.setdefault('figure-active', _act)          # colorScheme.tertiary
    _pal.setdefault('figure-active-back', _act_back)  # tertiary blended over surface

# ------------------------------------------------------------------ working segments per exercise
# Parts: '<side> <segment>' with side near/far (near = the side towards the
# camera; the profile rig calls it front/back) and segment leg, thigh, shin,
# foot, arm, upper, fore. 'both <segment>' expands to the two sides.
# Torso regions: pelvis, abdomen, thorax, upper_back, trunk.
# Exercises left out show the whole body working (gait, bird dog with
# alternating limbs) or a cue the figure cannot carry (pursed lips): no accent.
STYLE = {
    # mobilidade e transferências
    'sit_to_stand_exercise': dict(parts=['both thigh']),
    # quadril e glúteos
    'standing_hip_flexion': dict(parts=['near leg']),
    'standing_hip_extension': dict(parts=['near leg']),
    'standing_hip_abduction': dict(parts=['near leg']),
    'bridge': dict(torso=['pelvis']),
    'straight_leg_raise': dict(parts=['near leg']),
    'supine_hip_abduction': dict(parts=['near leg']),
    'seated_band_hip_abduction': dict(parts=['both thigh']),
    'adductor_ball_squeeze': dict(parts=['both thigh']),
    'prone_hip_extension': dict(parts=['near leg']),
    'side_lying_clamshell': dict(parts=['far thigh']),      # lying on the near side: the top leg is 'far'
    'side_lying_hip_abduction': dict(parts=['far leg']),
    # joelhos
    'seated_knee_extension': dict(parts=['near shin']),
    'seated_knee_extension_ankle_weight': dict(parts=['near shin']),
    'standing_knee_flexion': dict(parts=['near shin']),
    'mini_squat': dict(parts=['both thigh']),
    'heel_slides': dict(parts=['near leg']),
    'short_arc_quad': dict(parts=['near shin']),
    'wall_ball_squat': dict(parts=['both thigh']),
    # tornozelos e pés
    'ankle_pumps': dict(parts=['both foot']),
    'standing_heel_raise': dict(parts=['both foot']),
    'ankle_circles': dict(parts=['near foot']),
    'seated_heel_toe_raises': dict(parts=['both foot']),
    # equilíbrio: the base of support is the instruction
    'feet_together_stance': dict(parts=['both foot']),
    'semi_tandem_stance': dict(parts=['both foot']),
    'lateral_weight_shift': dict(parts=['both foot']),
    'single_leg_stance': dict(parts=['far foot']),  # the standing foot; the near leg lifts
    # marcha
    'seated_marching': dict(parts=['both thigh']),
    'standing_marching': dict(parts=['both thigh']),
    'step_up': dict(parts=['both thigh']),
    # tronco e coluna
    'supine_pelvic_tilt': dict(torso=['pelvis']),
    'seated_trunk_rotation': dict(torso=['thorax']),
    'abdominal_crunches': dict(torso=['abdomen']),
    'single_knee_to_chest': dict(parts=['near leg']),
    'prone_press_up_on_elbows': dict(torso=['thorax']),
    'cat_camel': dict(torso=['trunk']),
    # ombros e escápulas
    'shoulder_shrugs': dict(torso=['upper_back']),
    'scapular_retraction': dict(torso=['upper_back']),
    'arm_circles': dict(parts=['both arm']),
    'seated_shoulder_flexion': dict(parts=['both arm']),
    'seated_shoulder_abduction': dict(parts=['both arm']),
    'seated_overhead_press': dict(parts=['both arm']),
    'wall_push_up': dict(parts=['both arm']),
    # the elastic band is drawn in 'marker' (same orange): accent the upper arms only, so it stays visible
    'seated_band_row': dict(parts=['both upper']),
    'band_pull_apart': dict(parts=['both upper']),
    'band_shoulder_external_rotation': dict(parts=['near fore']),
    # cotovelos, punhos e mãos
    'elbow_flexion': dict(parts=['near fore']),
    'elbow_flexion_dumbbell': dict(parts=['near fore']),
    # respiração
    'diaphragmatic_breathing': dict(torso=['trunk']),  # the hands lie on chest and belly; a belly-only accent hides under them
}

# Fractions along hip -> shoulder (0 hip, 1 shoulder line).
REGIONS = {'pelvis': (-0.16, 0.42), 'abdomen': (0.12, 0.62), 'thorax': (0.42, 1.14), 'upper_back': (0.6, 1.1),
           'trunk': (-0.16, 1.14)}

_STATE = {'enabled': False, 'parts': set(), 'torso': []}


def use(slug):
    """Selects the library style for `slug` (None: the rig's own figure)."""
    cfg = STYLE.get(slug, {}) if slug else {}
    parts = set()
    for p in cfg.get('parts', ()):
        side, seg = p.split()
        assert seg in ('leg', 'thigh', 'shin', 'foot', 'arm', 'upper', 'fore'), p
        parts |= {f'{s} {seg}' for s in (('near', 'far') if side == 'both' else (side,))}
    for r in cfg.get('torso', ()):
        assert r in REGIONS, r
    _STATE.update(enabled=slug is not None, parts=parts, torso=[REGIONS[r] for r in cfg.get('torso', ())])


@contextmanager
def style(slug):
    use(slug)
    try:
        yield
    finally:
        use(None)


# ------------------------------------------------------------------ shapes
def add(*vs):
    return tuple(sum(c) for c in zip(*vs))


def sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def mul(v, k):
    return tuple(x * k for x in v)


def lerp(a, b, u):
    return tuple(x + (y - x) * u for x, y in zip(a, b))


def norm2(v):
    n = math.hypot(*v)
    return (v[0] / n, v[1] / n) if n > 1e-9 else (0.0, 1.0)


# Torso cross-sections: (fraction along hip->shoulder, half depth, anterior
# offset, half width, belly weight, chest weight), metres.
LEVELS = [(-0.16, 0.085, -0.012, 0.135, 0.0, 0.0),
          (0.00, 0.112, 0.000, 0.158, 0.0, 0.0),
          (0.22, 0.104, 0.008, 0.145, 1.8, 0.0),  # belly weights > 1: the rig's few centimetres
          (0.42, 0.100, 0.008, 0.138, 1.2, 0.0),  # of expansion must read as breathing
          (0.62, 0.112, 0.014, 0.155, 0.0, 0.7),
          (0.82, 0.116, 0.012, 0.170, 0.0, 1.0),
          (0.97, 0.104, 0.000, 0.176, 0.0, 0.2),
          (1.06, 0.082, -0.006, 0.152, 0.0, 0.0),
          (1.14, 0.056, -0.010, 0.100, 0.0, 0.0)]
W_NECK = 0.13
NOSE_R = 0.034
FOOT_OUTLINE_W = 0.016

# Foot outline in the foot frame: t towards the toes, n towards the sole.
FOOT = [(-0.030, -0.025), (-0.062, 0.015), (-0.060, 0.055), (-0.038, 0.072), (0.120, 0.072), (0.165, 0.066),
        (0.180, 0.050), (0.165, 0.030), (0.080, 0.006), (0.025, -0.028)]


def foot_outline(ankle, heel, toe):
    """Both rigs place the foot stroke at heel = A - 0.035 t + 0.03 n and
    toe = A + 0.14 t + 0.04 n; solving for t and n is linear, so it works on
    3D points and on the profile rig's projected 2D points alike."""
    h, q = sub(heel, ankle), sub(toe, ankle)
    t = mul(sub(mul(q, 3), mul(h, 4)), 1 / 0.56)
    n = mul(add(h, mul(t, 0.035)), 1 / 0.03)
    return [add(ankle, mul(t, a), mul(n, b)) for a, b in FOOT]


def levels(span=None):
    if span is None:
        return LEVELS
    f0, f1 = span

    def at(f):
        for (fa, *a), (fb, *b) in zip(LEVELS, LEVELS[1:]):
            if fa <= f <= fb:
                u = (f - fa) / (fb - fa)
                return (f, *[x + (y - x) * u for x, y in zip(a, b)])
        raise ValueError(f)
    return [at(f0)] + [lv for lv in LEVELS if f0 < lv[0] < f1] + [at(f1)]


def outline(rows):
    """rows: (centre, perpendicular, extent) per level -> closed polygon."""
    left = [add(c, mul(p, e)) for c, p, e in rows]
    right = [sub(c, mul(p, e)) for c, p, e in rows]
    return left + right[::-1]


# 3D torso: spine through hip, lumbar and shoulder; frames blend pelvis -> thorax.
def spine3(g, f):
    hip, lumbar, shoulder = g['torso']
    (Up, _, _), (Ut, _, _) = g['frames']
    if f <= 0:
        return add(hip, mul(Up, f * SHOULDER))
    if f <= 0.42:
        return lerp(hip, lumbar, f / 0.42)
    if f <= 1:
        return lerp(lumbar, shoulder, (f - 0.42) / 0.58)
    return add(shoulder, mul(Ut, (f - 1) * SHOULDER))


def torso3(cam, g, p, span=None):
    (_, Ap, Lp), (_, At, Lt) = g['frames']
    rows = []
    for f, d, o, w, kb, kc in levels(span):
        u = min(max((f - 0.2) / 0.5, 0.0), 1.0)
        A, L = lerp(Ap, At, u), lerp(Lp, Lt, u)
        c = add(spine3(g, f), mul(A, o + kb * p.get('belly', 0.0) + kc * p.get('chest', 0.0)))
        s = norm2(sub(cam.screen(spine3(g, f + 0.04)), cam.screen(spine3(g, f - 0.04))))
        perp = (-s[1], s[0])
        a2, l2 = cam.screen(A), cam.screen(L)
        ext = math.hypot(d * (a2[0] * perp[0] + a2[1] * perp[1]), w * (l2[0] * perp[0] + l2[1] * perp[1]))
        rows.append((cam.screen(c), perp, ext))
    return outline(rows)


# 2D torso (profile rig): straight spine; turning about Y shows the width.
def anterior2(g, p):
    (hx, hy), (sx, sy) = g['torso']
    u = norm2((sx - hx, sy - hy))
    k = 1 if math.cos(p['th']) >= 0 else -1
    return u, (u[1] * k, -u[0] * k)


def torso2(g, p, span=None):
    (hx, hy), (sx, sy) = g['torso']
    c, s = math.cos(p['th']), math.sin(p['th'])
    u, a = anterior2(g, p)
    perp = (-u[1], u[0])
    rows = []
    for f, d, o, w, kb, kc in levels(span):
        centre = (hx + (sx - hx) * f + a[0] * o * abs(c), hy + (sy - hy) * f + a[1] * o)
        rows.append((centre, perp, math.hypot(d * c, w * s)))
    return outline(rows)


# ------------------------------------------------------------------ painting
class Painter:
    """Rig-neutral painter: `limbs(g)` maps 'near'/'far' to leg, foot and arm
    polylines in picture metres; `to_px` turns them into pixels."""

    def __init__(self, scene, frames, to_px, opacity=None):
        self.s, self.frames, self.to_px, self.opacity = scene, frames, to_px, opacity

    def keys(self, get):
        return [(fr, [self.to_px(q) for q in get(g, p)]) for fr, p, g in self.frames]

    def line(self, name, get, role, width):
        self.s.layer(f'figure {name}', [group(name, [path(keys=self.keys(get)), stroke(role, self.s.m(width), self.s.palette)])],
                     self.opacity)

    def poly(self, name, get, role, outline_w=0.0):
        items = [path(keys=self.keys(get), closed=True), fill(role, self.s.palette)]
        if outline_w:
            items.append(stroke(role, self.s.m(outline_w), self.s.palette))
        self.s.layer(f'figure {name}', [group(name, items)], self.opacity)

    def dot(self, name, get, radius, role='figure'):
        d = round(self.s.m(radius * 2), 1)
        keys = [(fr, self.to_px(get(g, p))) for fr, p, g in self.frames]
        self.s.layer(f'figure {name}', [group(name, [ellipse(size=(d, d), keys=keys), fill(role, self.s.palette)])],
                     self.opacity)

    # limbs ---------------------------------------------------------------
    def limb(self, side, kind, get, back):
        """Leg or arm in its base role, then active segments over it."""
        whole, segs = ('leg', ('thigh', 'shin')) if kind == 'leg' else ('arm', ('upper', 'fore'))
        parts = _STATE['parts']
        active = 'figure-active-back' if back else 'figure-active'
        base = 'figure-back' if back else 'figure'
        on = {sg for sg in segs if f'{side} {sg}' in parts or f'{side} {whole}' in parts}
        width = W_LEG if kind == 'leg' else W_ARM
        self.line(f'{side} {kind}', get, active if len(on) == 2 else base, width)
        if len(on) == 1:
            i = segs.index(on.pop())
            self.line(f'{side} {segs[i]} active', lambda g, p: get(g, p)[i:i + 2], active, width)

    def foot(self, side, get_ankle_heel_toe, back, halo=False):
        role = ('figure-active-back' if back else 'figure-active') if f'{side} foot' in _STATE['parts'] else \
            ('figure-back' if back else 'figure')
        # The rig's heel-toe stroke stays under the outline: seen toe-on the
        # outline is edge-on, and the stroke keeps the foot its usual width.
        get = lambda g, p: foot_outline(*get_ankle_heel_toe(g, p))
        stroke_pts = lambda g, p: get_ankle_heel_toe(g, p)[1:]
        if halo:
            self.line(f'{side} foot halo stroke', stroke_pts, 'stage', W_FOOT + 2 * HALO)
            self.poly(f'{side} foot halo', get, 'stage', FOOT_OUTLINE_W + 2 * HALO)
        else:
            self.line(f'{side} foot stroke', stroke_pts, role, W_FOOT)
            self.poly(f'{side} foot', get, role, FOOT_OUTLINE_W)

    def torso(self, get_outline):
        self.poly('torso', lambda g, p: get_outline(g, p, None), 'figure')
        for i, span in enumerate(_STATE['torso']):
            self.poly(f'torso active {i}', lambda g, p, span=span: get_outline(g, p, span), 'figure-active')


ORIGINAL_ADD_FIGURE = figure3d.add_figure
ORIGINAL_SCENE_FIGURE = kl.Scene.figure


def add_figure(scene, cam, track, front=('near',), shadow=True, girdle=False, belly=False, chest=False,
               far_fore_over_chest=False, after_legs=None, after_arms=None):
    """figure3d.add_figure with the library style; same paint order and hooks."""
    if not _STATE['enabled']:
        return ORIGINAL_ADD_FIGURE(scene, cam, track, front, shadow, girdle, belly, chest, far_fore_over_chest,
                                   after_legs, after_arms)
    samples = sample(scene, track)
    frames = [(fr, track.at(fr / FPS), g) for fr, g in samples]
    pt = Painter(scene, frames, lambda q: scene.px(*(cam.screen(q) if len(q) == 3 else q)))
    m, pal = scene.m, scene.palette
    leg = lambda s: (lambda g, p: g[f'{s} leg'])
    aht = lambda s: (lambda g, p: (g[f'{s} leg'][2], *g[f'{s} foot']))
    if shadow:
        keys = [(fr, cam.px(scene, (g['pelvis'][0], 0.0, g['pelvis'][2]))) for fr, g in samples]
        scene.layer('figure shadow', [group('shadow', [ellipse(size=(round(m(0.56), 1), round(m(0.06), 1)), keys=keys),
                                                       fill('shadow', pal, 7)])])
    for s in [s for s in ('far', 'near') if s not in front]:
        pt.limb(s, 'leg', leg(s), back=True)
        pt.foot(s, aht(s), back=True)
        pt.limb(s, 'arm', lambda g, p, s=s: g[f'{s} arm'], back=True)
    pt.line('neck', lambda g, p: [spine3(g, 0.98), g['head']], 'figure', W_NECK)
    pt.torso(lambda g, p, span: torso3(cam, g, p, span))
    if girdle:
        pt.line('girdle', lambda g, p: g['girdle'], 'figure', W_ARM)

    def nose(g, p):
        _, (Ut, At, _) = g['frames']
        a = math.radians(p.get('nod', 0.0))
        return add(g['head'], mul(add(mul(At, math.cos(a)), mul(Ut, -math.sin(a))), HEAD_R * 0.93), mul(Ut, -0.012))
    pt.dot('nose', nose, NOSE_R)
    pt.dot('head', lambda g, p: g['head'], HEAD_R)
    if far_fore_over_chest:
        pt.line('far fore halo', lambda g, p: g['far fore'], 'stage', W_ARM + 2 * HALO)
        pt.line('far fore', lambda g, p: g['far fore'], 'figure-back', W_ARM)
    for s in [s for s in ('far', 'near') if s in front]:
        pt.line(f'{s} leg halo', lambda g, p, s=s: g[f'{s} leg halo'], 'stage', W_LEG + 2 * HALO)
        pt.foot(s, aht(s), back=False, halo=True)
        pt.limb(s, 'leg', leg(s), back=False)
        pt.foot(s, aht(s), back=False)
    if after_legs:
        after_legs(samples)
    for s in [s for s in ('far', 'near') if s in front]:
        pt.line(f'{s} arm halo', lambda g, p, s=s: g[f'{s} arm halo'], 'stage', W_ARM + 2 * HALO)
        pt.limb(s, 'arm', lambda g, p, s=s: g[f'{s} arm'], back=False)
    if after_arms:
        after_arms(samples)
    return samples


def scene_figure(self, track, layer_opacity=None, on_frame=None, before_front_arm=None):
    """kineti_lottie.Scene.figure (profile rig) with the library style."""
    if not _STATE['enabled']:
        return ORIGINAL_SCENE_FIGURE(self, track, layer_opacity, on_frame, before_front_arm)
    frames = []
    for fr in list(range(0, self.frames, STEP)) + [self.frames]:
        p = track.at(fr / FPS)
        g = kl.figure_geometry(p)
        if on_frame:
            on_frame(fr, g)
        frames.append((fr, p, g))
    pt = Painter(self, frames, lambda q: self.px(*q), layer_opacity)
    side = {'near': 'front', 'far': 'back'}
    leg = lambda s: (lambda g, p: g[f'{side[s]}_leg']['leg'])
    aht = lambda s: (lambda g, p: (g[f'{side[s]}_leg']['leg'][2], *g[f'{side[s]}_leg']['foot']))
    m = self.m
    self.layer('figure shadow', [group('shadow', [ellipse(size=(round(m(0.56), 1), round(m(0.06), 1)),
                                                          keys=[(fr, self.px(g['hip_x'], 0.0)) for fr, p, g in frames]),
                                                  fill('shadow', self.palette, 7)])], layer_opacity)
    pt.limb('far', 'leg', leg('far'), back=True)
    pt.foot('far', aht('far'), back=True)
    pt.limb('far', 'arm', lambda g, p: g['back_arm']['arm'], back=True)
    pt.line('neck', lambda g, p: [lerp(g['torso'][0], g['torso'][1], 0.98), g['head']], 'figure', W_NECK)
    pt.torso(lambda g, p, span: torso2(g, p, span))

    def nose(g, p):
        _, a = anterior2(g, p)
        hx, hy = g['head']
        return (hx + a[0] * HEAD_R * 0.93 * abs(math.cos(p['th'])), hy + a[1] * HEAD_R * 0.93 - 0.012)
    pt.dot('nose', nose, NOSE_R)
    pt.dot('head', lambda g, p: g['head'], HEAD_R)
    pt.line('front leg halo', lambda g, p: g['front_leg']['leg_halo'], 'stage', W_LEG + 2 * HALO)
    pt.foot('near', aht('near'), back=False, halo=True)
    pt.limb('near', 'leg', leg('near'), back=False)
    pt.foot('near', aht('near'), back=False)
    if before_front_arm:
        before_front_arm()
    pt.line('front arm halo', lambda g, p: g['front_arm']['arm_halo'], 'stage', W_ARM + 2 * HALO)
    pt.limb('near', 'arm', lambda g, p: g['front_arm']['arm'], back=False)


figure3d.add_figure = add_figure
kl.Scene.figure = scene_figure
