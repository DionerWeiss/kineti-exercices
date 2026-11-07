"""MediaPipe landmarks -> scene JSON for tool/blender/render_scene.py.

    python3 tool/mocap/to_scene.py landmarks.json scene.json [--seconds 6] [--camera 22,14] [--ball]

- Axes: MediaPipe world (x right, y down, z away from the camera) becomes
  the rig's (Y up, near side +Z towards the camera).
- Size: the person is scaled so the legs match the character's; the
  character's arm factor is set so the arms match too, so straight limbs
  stay straight.
- Time: Gaussian smoothing, resampled to 30 fps; the window whose ends
  match best becomes the loop, and its last half second blends into the start.
- Ground: the lowest support point (hands or feet) is put on the mat.
"""

import argparse
import json
import math
from pathlib import Path

import numpy as np

CHAR_LEG = 0.437 + 0.46        # character thigh + calf (Kineti_Rig)
CHAR_ARM = 0.261 + 0.269       # character upper arm + forearm
FPS = 30
MAT_TOP = 0.02
L = {'nose': 0, 'ear_l': 7, 'ear_r': 8, 'sh_l': 11, 'sh_r': 12, 'el_l': 13, 'el_r': 14, 'wr_l': 15, 'wr_r': 16,
     'hip_l': 23, 'hip_r': 24, 'kn_l': 25, 'kn_r': 26, 'an_l': 27, 'an_r': 28, 'heel_l': 29, 'heel_r': 30,
     'toe_l': 31, 'toe_r': 32}


def unit(v):
    return v / (np.linalg.norm(v) + 1e-9)


def smooth(x, sigma):
    """Gaussian smoothing along time (axis 0), edges padded by reflection."""
    r = int(3 * sigma)
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    pad = np.pad(x, [(r, r)] + [(0, 0)] * (x.ndim - 1), mode='reflect')
    return np.stack([np.tensordot(k, pad[i:i + 2 * r + 1], axes=(0, 0)) for i in range(len(x))])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('landmarks')
    ap.add_argument('out')
    ap.add_argument('--seconds', type=float, default=6.0)
    ap.add_argument('--camera', default='22,14')
    ap.add_argument('--ball', action='store_true', help='shins rest on a gym ball')
    a = ap.parse_args()
    src = json.loads(Path(a.landmarks).read_text())
    fps_in = src['fps']
    W = np.array([f['world'] for f in src['frames'] if f['world']], dtype=float)  # (T, 33, 3)
    W = W * np.array([1.0, -1.0, -1.0])  # rig axes: Y up, +Z towards the camera
    W = smooth(W, sigma=2.0)

    # scale to the character
    leg = np.mean([np.linalg.norm(W[:, L[f'kn_{s}']] - W[:, L[f'hip_{s}']], axis=1).mean() +
                   np.linalg.norm(W[:, L[f'an_{s}']] - W[:, L[f'kn_{s}']], axis=1).mean() for s in 'lr'])
    scale = CHAR_LEG / leg
    W *= scale
    arm = np.mean([np.linalg.norm(W[:, L[f'el_{s}']] - W[:, L[f'sh_{s}']], axis=1).mean() +
                   np.linalg.norm(W[:, L[f'wr_{s}']] - W[:, L[f'el_{s}']], axis=1).mean() for s in 'lr'])
    arm_factor = float(min(max(arm / CHAR_ARM, 0.8), 1.05))

    # resample to 30 fps
    t_in = np.arange(len(W)) / fps_in
    t_out = np.arange(0, t_in[-1], 1 / FPS)
    W = np.stack([np.stack([np.interp(t_out, t_in, W[:, j, c]) for c in range(3)], axis=1) for j in range(33)], axis=1)

    # loop window: ends that match best
    n = int(round(a.seconds * FPS))
    if len(W) > n:
        costs = [np.abs(W[i] - W[i + n - 1]).mean() for i in range(len(W) - n)]
        i0 = int(np.argmin(costs))
        W = W[i0:i0 + n].copy()
    blend = min(int(0.5 * FPS), len(W) // 4)
    for k in range(blend):  # last half second eases into the first frame
        w = 0.5 - 0.5 * math.cos(math.pi * (k + 1) / blend)
        W[len(W) - blend + k] = (1 - w) * W[len(W) - blend + k] + w * W[0]

    # near side: the one closer to the camera (larger Z)
    near = 'r' if W[:, L['hip_r'], 2].mean() > W[:, L['hip_l'], 2].mean() else 'l'
    far = 'l' if near == 'r' else 'r'

    # ground: the lowest support point (wrists or ankles/toes) rests on the mat
    supports = [L[f'wr_{s}'] for s in 'lr'] + [L[f'toe_{s}'] for s in 'lr'] + [L[f'heel_{s}'] for s in 'lr']
    low = W[:, supports, 1].min(axis=1).mean()
    W[:, :, 1] += MAT_TOP + 0.03 - low

    samples = []
    for fr, P in enumerate(W):
        hip = (P[L['hip_l']] + P[L['hip_r']]) / 2
        sh = (P[L['sh_l']] + P[L['sh_r']]) / 2
        Ut = unit(sh - hip)
        Lp = unit(P[L[f'hip_{near}']] - P[L[f'hip_{far}']])
        Lp = unit(Lp - Ut * Lp.dot(Ut))
        Lt = unit(P[L[f'sh_{near}']] - P[L[f'sh_{far}']])
        Lt = unit(Lt - Ut * Lt.dot(Ut))
        Ap, At = np.cross(Ut, Lp), np.cross(Ut, Lt)  # rig frames: A = U x L
        head = (P[L['ear_l']] + P[L['ear_r']]) / 2
        h = head - sh
        nod = math.degrees(math.atan2(h.dot(At), h.dot(Ut)))
        side = lambda s: {'leg': [P[L[f'hip_{s}']], P[L[f'kn_{s}']], P[L[f'an_{s}']]],
                          'arm': [P[L[f'sh_{s}']], P[L[f'el_{s}']], P[L[f'wr_{s}']]],
                          'foot': [P[L[f'heel_{s}']], P[L[f'toe_{s}']]]}
        sn, sf = side(near), side(far)
        tl = lambda v: [float(x) for x in v]
        samples.append({'fr': fr, 'pelvis_frame': [tl(Ut), tl(Ap), tl(Lp)], 'thorax_frame': [tl(Ut), tl(At), tl(Lt)],
                        'nod': nod, 'torso': [tl(hip), tl(hip + 0.42 * (sh - hip)), tl(sh)], 'head': tl(head),
                        **{f'near {k}': [tl(q) for q in v] for k, v in sn.items()},
                        **{f'far {k}': [tl(q) for q in v] for k, v in sf.items()}})

    props = []
    xs = W[:, :, 0]
    props.append({'type': 'box', 'name': 'mat', 'min': [float(xs.min()) - 0.35, 0.0, -0.45],
                  'max': [float(xs.max()) + 0.35, MAT_TOP, 0.45], 'role': 'prop-soft'})
    if a.ball:  # shins rest on the top of a ball standing on the mat
        an = (W[:, L['an_l']] + W[:, L['an_r']]).mean(axis=0) / 2
        kn = (W[:, L['kn_l']] + W[:, L['kn_r']]).mean(axis=0) / 2
        contact = an + 0.3 * (kn - an)
        r = (contact[1] - 0.055 - MAT_TOP) / 2
        props.append({'type': 'sphere', 'name': 'ball', 'center': [float(contact[0]), MAT_TOP + r, 0.0], 'radius': float(r)})

    yaw, pitch = (float(v) for v in a.camera.split(','))
    y, p = math.radians(yaw), math.radians(pitch)
    right = np.array([math.cos(y), 0.0, -math.sin(y)])
    up = np.array([-math.sin(y) * math.sin(p), math.cos(p), -math.cos(y) * math.sin(p)])
    pts = np.concatenate([W.reshape(-1, 3)] + [np.array([[pr['min'][0], 0, 0], [pr['max'][0], 0, 0]]) for pr in props if pr['type'] == 'box'])
    sx, sy = pts @ right, pts @ up
    pad = 0.25
    left, rgt, bot, top = sx.min() - pad, sx.max() + pad, sy.min() - pad, sy.max() + pad
    if (rgt - left) / (top - bot) < 1.6:  # 16:10 frame
        c, half = (left + rgt) / 2, (top - bot) * 1.6 / 2
        left, rgt = c - half, c + half
    else:
        c, half = (bot + top) / 2, (rgt - left) / 1.6 / 2
        bot, top = c - half, c + half

    out = {'slug': Path(a.out).stem, 'fps': FPS, 'frames_total': len(samples), 'kind': 'mocap', 'camera': [yaw, pitch],
           'scene_bounds': [float(left), float(rgt), float(bot), float(top)], 'props': props, 'bands': {},
           'samples': samples, 'arm': arm_factor, 'lift': False}
    Path(a.out).write_text(json.dumps(out))
    print(f'{len(samples)} frames, scale {scale:.2f}, arm factor {arm_factor:.2f}, near side {near}, props {[p["name"] for p in props]}')


if __name__ == '__main__':
    main()
