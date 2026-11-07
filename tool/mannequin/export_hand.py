"""Exports the hand close-up scenes (tool/build_library_hand_animations.py) frame by frame, for the
mannequin-style hand render (render_hand.py). Same kinematics and checks as the Lottie version.

    python3 tool/mannequin/export_hand.py <out_dir> [slugs...]     # <out_dir>/<slug>.json

World axes of the builder: x along the forearm (hand at +x), y up (table top at y = 0), z towards the camera
side. Each frame stores the forearm, palm outline, the four fingers and the thumb (joint points, metres).
"""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_library_hand_animations as H  # noqa: E402
from kineti_lottie import FPS  # noqa: E402

import math  # noqa: E402

SLUGS = ['wrist_flexion_extension', 'forearm_pronation_supination', 'open_close_hand', 'thumb_opposition',
         'grip_ball_squeeze', 'mcp_flexion', 'thumb_flexion', 'thumb_abduction', 'wrist_deviation']
EDGES = {'wrist_flexion_extension': H.EDGE, 'forearm_pronation_supination': H.EDGE}


# ---- scenes of our own, built with the same hand model (palm up on the table unless noted)
def _scene(steps, view=H.PALM_UP_CAM):
    tr = H.Track()
    H.chain(tr, steps)
    cam = H.Camera(yaw=view[0], pitch=view[1])
    return cam, tr


def mcp_flexion():
    """'L' hand: the fingers bend only at the knuckles, the finger joints stay straight."""
    rest = H.palm_up(H.relaxed_fingers(), H.REST_THUMB)
    flat = H.palm_up({n: H.finger(0, 3, 2, a) for n, a in zip(H.ORDER, (5, 1, -3, -7))}, H.REST_THUMB)
    ell = H.palm_up({n: H.finger(85, 2, 2, a) for n, a in zip(H.ORDER, (3, 0, -2, -4))}, H.REST_THUMB)
    return _scene([(rest, 0.5), (flat, 0.9), (flat, 0.4), (ell, 1.2), (ell, 0.8), (flat, 1.1), (flat, 0.4), (rest, 0.8),
                   (rest, 0.4)], view=(70, 30))


def thumb_flexion():
    """The thumb tip slides across the palm towards the base of the little finger and back."""
    f = {n: H.finger(6, 8, 4, a) for n, a in zip(H.ORDER, (6, 1, -3, -8))}
    rest = H.palm_up(f, H.OPEN_THUMB)
    tip = (0.07, -0.022, H.PALM_W / 2 + H.THUMB_W / 2 + 0.002)
    meta = H.unit(H.add(H.unit(H.sub(tip, H.CMC)), (0.0, 0.3, 0.45)))
    flex = H.palm_up(f, H.thumb(meta, tip, bend=(0.2, 0.8, -0.3)))
    return _scene([(rest, 0.5), (flex, 1.2), (flex, 0.7), (rest, 1.2), (rest, 0.5)])


def thumb_abduction():
    """The thumb opens away from the index finger and closes back beside it."""
    f = {n: H.finger(4, 6, 3, a) for n, a in zip(H.ORDER, (4, 1, -2, -6))}
    close_meta = (0.85, 0.35, 0.15)
    closed = H.palm_up(f, H.thumb(close_meta, H.straight_thumb_tip(close_meta, (0.95, 0.2, 0.1), reach=0.054)))
    opened = H.palm_up(f, H.OPEN_THUMB)
    return _scene([(closed, 0.5), (opened, 1.1), (opened, 0.6), (closed, 1.1), (closed, 0.5)])


WRIST_DEV = {}


def wrist_deviation():
    """Palm down on the table: the hand swings towards the thumb, back, towards the little finger."""
    f = {n: H.finger(0, 3, 2, a) for n, a in zip(H.ORDER, (5, 1, -3, -7))}
    flat = H.hand(sup=0.0, fingers=f, thumb_=H.REST_THUMB)
    tr = H.Track()
    t = H.chain(tr, [(flat, 0.5), (flat, 1.1), (flat, 0.6), (flat, 1.1), (flat, 1.1), (flat, 0.6), (flat, 1.1), (flat, 0.4)])
    # radial 20 deg, ulnar 30 deg, eased between the chain's step times
    targets = [0, 20, 20, 0, -30, -30, 0, 0, 0]
    WRIST_DEV['curve'] = (list(t), targets)
    return H.Camera(yaw=15, pitch=72), tr


def deviation_at(time):
    ts, vs = WRIST_DEV['curve']
    for a, b, va, vb in zip(ts, ts[1:], vs, vs[1:]):
        if a <= time <= b:
            u = (time - a) / (b - a) if b > a else 0
            return va + (vb - va) * H.smooth(u)
    return vs[-1]


def rotate_about(q, o, axis, deg):
    return H.add(o, H.rotate(H.sub(q, o), axis, deg))


GRIP = (0.8, 1.2, 1.4, 1.6, 0.8)  # rest, squeeze, hold, release, tail (the builder's grip_ball_squeeze)


def grip_level(t):
    rest_s, squeeze_s, hold_s, release_s, _ = GRIP
    t2 = rest_s + squeeze_s + hold_s
    c = lambda u: H.smooth(min(max(u, 0), 1))
    return c((t - rest_s) / squeeze_s) - c((t - t2) / release_s)


OWN = {'mcp_flexion': mcp_flexion, 'thumb_flexion': thumb_flexion, 'thumb_abduction': thumb_abduction,
       'wrist_deviation': wrist_deviation}


def main():
    out, slugs = Path(sys.argv[1]), sys.argv[2:] or SLUGS
    out.mkdir(parents=True, exist_ok=True)
    seen = {}
    orig = H.fit_scene

    def spy(title, cam, track, *a, **kw):
        seen.update(cam=cam, track=track)
        return orig(title, cam, track, *a, **kw)

    H.fit_scene = spy
    for slug in slugs:
        if slug in OWN:
            cam, tr = OWN[slug]()
        else:
            H.SCENES[slug]()  # builds and checks the Lottie scene, and records its camera and track
            cam, tr = seen['cam'], seen['track']
        n = int(round(tr.duration * FPS))
        frames = []
        for f in range(n):
            p = tr.at(f / FPS)
            g = H.geometry(p)
            fr = {k: g[k] for k in ('forearm', 'palm', 'thumb', *H.ORDER)}
            if slug == 'wrist_deviation':  # turn the hand about the palm normal at the wrist
                o, D, R, P = g['frame']
                a = deviation_at(f / FPS)
                for k in ('palm', 'thumb', *H.ORDER):
                    fr[k] = [rotate_about(q, o, P, a) for q in fr[k]]
            if slug == 'grip_ball_squeeze':
                o, D, R, P = H.frame(p)
                radii, c = H.ball(grip_level(f / FPS))
                fr['ball'] = {'c': H.add(o, H.mul(D, c[0]), H.mul(R, c[1]), H.mul(P, c[2])),
                              'axes': [H.mul(D, radii[0]), H.mul(R, radii[1]), H.mul(P, radii[2])]}
            frames.append(fr)
        data = {'slug': slug, 'fps': FPS, 'edge': EDGES.get(slug, H.ON_TABLE), 'cam_right': list(cam.right), 'cam_up': list(cam.up),
                'widths': {'forearm': H.FORE_W, 'palm': H.PALM_W, 'thumb': H.THUMB_W,
                           **{k: H.FINGERS[k][2] for k in H.ORDER}}, 'frames': frames}
        json.dump(data, open(out / f'{slug}.json', 'w'))
        print(slug, n, 'frames')


if __name__ == '__main__':
    main()
