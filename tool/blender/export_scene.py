"""Exports one library exercise for the Blender renderer: the motion of the
figure on every sampled frame, the camera, and the props the scene draws.

    python3 tool/blender/export_scene.py <slug> <out.json>

The scene is built exactly as for the Lottie (same builder, same checks).
While it builds, the figure painters and the prop primitives are wrapped to
record world-space data instead of only pixels:

- 3D scenes (figure3d): joints straight from figure3d.geometry; boxes,
  bars (line3) and panels (poly3) as drawn by the builders.
- Profile scenes (kineti_lottie.Scene.figure): the 2D rig places each side
  at a fixed depth, so the 3D joints are rebuilt from the pose; profile
  lines and polygons are recorded with their names and rebuilt as 3D props
  in Blender (a chair becomes a chair, a wall or step a block).
- Elastic bands (build_library_props_animations.band): world points per frame.

Coordinates are the rig's: metres, Y up; a body facing +X has its near
(right) side towards +Z.
"""

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _rig  # noqa: E402,F401
import build_catalog as bc  # noqa: E402
import figure3d  # noqa: E402
import figure_style  # noqa: E402
import kineti_lottie as kl  # noqa: E402

FPS = kl.FPS


# ------------------------------------------------------------------ profile rig in 3D
def profile_geometry3d(p):
    """kineti_lottie.figure_geometry, keeping depth: same joints, as 3D points."""
    g2 = kl.figure_geometry(p)
    th, hx = p['th'], p['hx']
    c, s = math.cos(th), math.sin(th)
    sign = 1 if c >= 0 else -1  # which local side is drawn in front

    def lift(pt2, z):
        """Screen x of the 2D rig is hx + c*x + s*z; recover x, rebuild world."""
        x = (pt2[0] - hx - s * z) / c if abs(c) > 1e-6 else 0.0
        return (hx + c * x + s * z, pt2[1], -s * x + c * z)

    za, zb = kl.HIP_Z, -kl.HIP_Z
    sa, sb = kl.SHOULDER_Z, -kl.SHOULDER_Z
    legs = {'near': (g2['front_leg'], za if sign > 0 else zb), 'far': (g2['back_leg'], zb if sign > 0 else za)}
    arms = {'near': (g2['front_arm'], sa if sign > 0 else sb), 'far': (g2['back_arm'], sb if sign > 0 else sa)}
    hip2, sh2 = g2['torso']
    hip, shoulder = lift(hip2, 0.0), lift(sh2, 0.0)
    out = {'torso': [hip, tuple((a + b) / 2 for a, b in zip(hip, shoulder)), shoulder], 'head': lift(g2['head'], 0.0)}
    for side, (leg, z) in legs.items():
        out[f'{side} leg'] = [lift(q, z) for q in leg['leg']]
        out[f'{side} foot'] = [lift(q, z) for q in leg['foot']]
    for side, (arm, z) in arms.items():
        out[f'{side} arm'] = [lift(q, z) for q in arm['arm']]
    up = (0.0, 1.0, 0.0)
    ant = (c, 0.0, -s)
    lat = (s, 0.0, c)
    tr = math.radians(p['trunk'])
    ut = tuple(math.sin(tr) * a + math.cos(tr) * u for a, u in zip(ant, up))
    at = tuple(math.cos(tr) * a - math.sin(tr) * u for a, u in zip(ant, up))
    out['frames'] = ((up, ant, lat), (ut, at, lat))
    return out


# ------------------------------------------------------------------ recording
def export(slug):
    found = bc.scenes()
    mod_name, fn = found[slug]
    rec = {'samples': None, 'track': None, 'kind': None, 'props': [], 'bands': {}, 'cams': []}
    depth = [0]

    # figure painters
    orig_sample = figure_style.sample

    def sample3d(scene, track):
        s = orig_sample(scene, track)
        rec.update(samples=s, track=track, kind='3d')
        return s
    figure_style.sample = sample3d
    orig_fig2d = kl.Scene.figure

    def figure2d(self, track, *a, **k):
        frames = list(range(0, self.frames, kl.STEP)) + [self.frames]
        rec.update(samples=[(fr, profile_geometry3d(track.at(fr / FPS))) for fr in frames], track=track, kind='2d')
        return orig_fig2d(self, track, *a, **k)
    kl.Scene.figure = figure2d

    # 3D primitives, wherever the builders imported them from
    originals = {n: getattr(figure3d, n) for n in ('box', 'line3', 'poly3')}

    def box(scene, cam, name, x0, x1, y0, y1, z0, z1, top='prop-soft', side='floor', outline='prop'):
        if not depth[0]:
            rec['props'].append({'type': 'box', 'name': name, 'min': [x0, y0, z0], 'max': [x1, y1, z1], 'role': top})
        depth[0] += 1
        try:
            return originals['box'](scene, cam, name, x0, x1, y0, y1, z0, z1, top, side, outline)
        finally:
            depth[0] -= 1

    def line3(scene, cam, name, points, role, width):
        if not depth[0]:
            rec['props'].append({'type': 'bar', 'name': name, 'points': [list(q) for q in points], 'width': width, 'role': role})
        return originals['line3'](scene, cam, name, points, role, width)

    def poly3(scene, cam, name, points, role, outline=None, width=0.02):
        if not depth[0] and name != 'floor plane':
            rec['props'].append({'type': 'panel', 'name': name, 'points': [list(q) for q in points], 'role': role})
        return originals['poly3'](scene, cam, name, points, role, outline, width)
    wrappers = {'box': box, 'line3': line3, 'poly3': poly3}
    for mod in list(sys.modules.values()):
        for n, f in originals.items():
            if getattr(mod, n, None) is f:
                setattr(mod, n, wrappers[n])

    # profile primitives
    orig_line, orig_poly = kl.Scene.line, kl.Scene.polygon

    def sline(self, name, points, role, width_m, *a, **k):
        if rec['kind'] is None or not name.startswith('figure'):
            rec['props'].append({'type': 'line2d', 'name': name, 'points': [list(q) for q in points], 'width': width_m, 'role': role})
        return orig_line(self, name, points, role, width_m, *a, **k)

    def spoly(self, name, points, role, *a, **k):
        rec['props'].append({'type': 'poly2d', 'name': name, 'points': [list(q) for q in points], 'role': role})
        return orig_poly(self, name, points, role, *a, **k)
    kl.Scene.line, kl.Scene.polygon = sline, spoly

    # elastic bands
    try:
        import build_library_props_animations as bp
        orig_band = bp.band

        def band(scene, cam, samples, name, points_of, rest_length):
            rec['bands'][name] = [[fr, [list(q) for q in points_of(g)]] for fr, g in samples]
            return orig_band(scene, cam, samples, name, points_of, rest_length)
        bp.band = band
    except ModuleNotFoundError:
        pass

    # camera: whichever Camera projects the scene (some builders create it at import time)
    orig_screen = figure3d.Camera.screen

    def screen(self, point):
        rec['cam_obj'] = self
        return orig_screen(self, point)
    figure3d.Camera.screen = screen

    with figure_style.style(slug):
        data = bc.build(fn)  # same builder and checks as the Lottie
    return rec, data


# Working-part highlight. Same map as figure_style.STYLE; near is the character's right.
_SEG = {
    'leg': ('thigh_', 'calf_', 'foot_'), 'thigh': ('thigh_',), 'shin': ('calf_',), 'foot': ('foot_',),
    'arm': ('upperarm_', 'lowerarm_', 'hand_'), 'upper': ('upperarm_',), 'fore': ('lowerarm_', 'hand_'),
}
_TORSO = {
    'pelvis': ('pelvis', 'spine_01'), 'abdomen': ('spine_01', 'spine_02'),
    'thorax': ('spine_02', 'spine_03'), 'upper_back': ('spine_03', 'clavicle_l', 'clavicle_r'),
    'trunk': ('pelvis', 'spine_01', 'spine_02', 'spine_03'),
}
_DIGITS = ('index', 'middle', 'ring', 'pinky', 'thumb')


def accent_bones(slug):
    cfg = figure_style.STYLE.get(slug, {})
    names = []
    for part in cfg.get('parts', ()):
        side, seg = part.split()
        for sd in (('near', 'far') if side == 'both' else (side,)):
            sfx = 'r' if sd == 'near' else 'l'
            names.extend(pfx + sfx for pfx in _SEG[seg])
            if seg in ('arm', 'fore'):
                names.extend(f'{digit}_{i:02d}_{sfx}' for digit in _DIGITS for i in (1, 2, 3))
    for region in cfg.get('torso', ()):
        names.extend(_TORSO[region])
    return list(dict.fromkeys(names))


def _add(a, b, scale=1.0):
    return [a[i] + scale * b[i] for i in range(3)]


def _mid(a, b):
    return [(a[i] + b[i]) * 0.5 for i in range(3)]


def gadgets(slug, samples):
    """Props the Lottie draws as screen shapes, rebuilt from the same joints."""
    items = []

    def dumbbell(side, half):
        keys = []
        for s in samples:
            elbow, hand = s[f'{side} arm'][1], s[f'{side} arm'][2]
            reach = _add(hand, elbow, -1.0)
            span = math.sqrt(sum(v * v for v in reach)) or 1.0
            palm = _add(hand, reach, 0.065 / span)  # the rig point is the wrist; the grip is in the palm
            lateral = s['thorax_frame'][2]
            keys.append({'fr': s['fr'], 'a': _add(palm, lateral, -half), 'b': _add(palm, lateral, half)})
        items.append({'type': 'dumbbell', 'name': f'dumbbell {side}', 'keys': keys})

    if slug == 'adductor_ball_squeeze':
        import build_library_props_animations as props
        keys = []
        for s in samples:
            kn, kf = s['near leg'][1], s['far leg'][1]
            center = _mid(kn, kf)
            center[1] -= 0.015  # just under the knee joint, in the gap
            width = max(kn[2] - kf[2] - kl.W_LEG, 0.05)
            depth = props.BALL_D + (props.BALL_D - width) * 0.4
            keys.append({'fr': s['fr'], 'center': center, 'scale': [depth, depth * 0.95, width]})
        items.append({'type': 'ball', 'name': 'ball', 'color': [0.74, 0.16, 0.13], 'keys': keys})
    elif slug == 'wall_ball_squat':
        import build_library_props_animations as props
        keys = []
        for s in samples:
            hy = s['torso'][0][1]
            cy = props.WB_BALL_Y0 - (props.WB_TOP_Y - hy) / 2
            d = props.WB_R * 2
            keys.append({'fr': s['fr'], 'center': [props.WB_BALL_X, cy, 0.0], 'scale': [d, d, d]})
        items.append({'type': 'ball', 'name': 'gym ball', 'color': [0.62, 0.70, 0.76], 'keys': keys})
    elif slug in ('seated_overhead_press', 'elbow_flexion_dumbbell'):
        import build_library_seated_animations as seated
        sides = ('near', 'far') if slug == 'seated_overhead_press' else ('near',)
        for side in sides:
            dumbbell(side, seated.DUMBBELL_HALF)
    elif slug == 'seated_knee_extension_ankle_weight':
        keys = []
        for s in samples:
            knee, ankle = s['near leg'][1], s['near leg'][2]
            d = _add(knee, ankle, -1.0)
            keys.append({'fr': s['fr'], 'a': _add(ankle, d, 0.10), 'b': _add(ankle, d, 0.17)})
        items.append({'type': 'cuff', 'name': 'ankle weight', 'keys': keys})
    return items


def main(slug, out):
    rec, data = export(slug)
    samples = []
    for fr, g in rec['samples']:
        p = rec['track'].at(fr / FPS)
        samples.append({'fr': fr, 'pelvis_frame': g['frames'][0], 'thorax_frame': g['frames'][1],
                        'nod': p.get('nod', 0.0), 'torso': g['torso'], 'head': g['head'],
                        **{f'{s} {k}': g[f'{s} {k}'] for s in ('near', 'far') for k in ('leg', 'arm', 'foot')}})
    cam = (0.0, 0.0)
    if rec['kind'] == '3d' and rec.get('cam_obj'):
        t = rec['cam_obj'].toward
        cam = (math.degrees(math.atan2(t[0], t[2])), math.degrees(math.asin(max(-1.0, min(1.0, t[1])))))
    accent = accent_bones(slug)
    gear = gadgets(slug, samples)
    out_data = {'slug': slug, 'fps': FPS, 'frames_total': data['op'], 'kind': rec['kind'], 'camera': cam,
                'scene_bounds': SCENE_BOUNDS[0], 'props': rec['props'], 'bands': rec['bands'],
                'accent': accent, 'gadgets': gear, 'samples': samples}
    Path(out).write_text(json.dumps(out_data, separators=(',', ':')))
    print(f'{slug}: {rec["kind"]} rig, {len(samples)} samples, {len(rec["props"])} props, '
          f'{len(rec["bands"])} bands, {len(gear)} gadgets, {len(accent)} accent bones, '
          f'camera ({cam[0]:.0f}, {cam[1]:.0f})')


# Scene bounds: captured from the Scene object as it is created.
SCENE_BOUNDS = []
_orig_init = kl.Scene.__init__


def _scene_init(self, name, left, right, bottom, duration, *a, **k):
    _orig_init(self, name, left, right, bottom, duration, *a, **k)
    SCENE_BOUNDS.insert(0, [self.left, self.right, self.bottom, self.top])


kl.Scene.__init__ = _scene_init

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
