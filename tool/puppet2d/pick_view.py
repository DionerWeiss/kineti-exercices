"""Which puppet view shows an exercise: the side (drive_puppet.py) or the front (drive_front.py).

    python3 pick_view.py <joints.json> <action> [<action>...] [--json]

For each action the body's own axes are taken from its median pose: up = hip joints -> neck, left = shoulders and hips
(left minus right), forward = left x up. Every moving end (elbows, hands, knees, feet, head) is measured relative to
the pelvis over the move; its spread (standard deviation) along `left` is motion in the frontal plane only, along
`forward` motion in the sagittal plane only (the `up` part shows in both views and decides nothing). A spine that
bends sideways counts as frontal, one that bends forward as sagittal.

    front  when frontal >= 1.15 x sagittal (and at least 1.5 cm), or when the base moves sideways: spread of the
           stance width plus spread of the pelvis' sideways shift over the feet >= 6 cm (jacks, side steps, lateral
           lunges, weight shifts); else side.

Because the axes are the body's, a side-lying move (side plank: the hips rise along the body's left/right axis) comes
out front, and a bridge or a push-up (motion along the body's forward axis, which points at the sky / the floor) side.
"""
import json
import sys

import numpy as np

RATIO, MIN_M, BASE_M = 1.15, 0.015, 0.06
ENDS = [('elbowL', 0), ('elbowR', 0), ('handL', 0), ('handR', 0), ('kneeL', 0), ('kneeR', 0), ('footL', 0),
        ('footR', 0), ('neck', 1)]


def jp(fr, b, tail=0):
    return np.array(fr[b][tail], float)


def axes(fr):
    hc = (jp(fr, 'legL') + jp(fr, 'legR')) / 2
    up = jp(fr, 'neck') - hc
    up /= np.linalg.norm(up)
    lat = (jp(fr, 'armL') - jp(fr, 'armR')) + 2 * (jp(fr, 'legL') - jp(fr, 'legR'))
    lat -= up * np.dot(lat, up)
    lat /= np.linalg.norm(lat)
    return lat, np.cross(lat, up), up, hc


def pick(frames):
    A = [axes(fr) for fr in frames]
    lat = np.median([a[0] for a in A], 0)
    up = np.median([a[2] for a in A], 0)
    up /= np.linalg.norm(up)
    lat -= up * np.dot(lat, up)
    lat /= np.linalg.norm(lat)
    fwd = np.cross(lat, up)
    front = side = 0.0
    for b, t in ENDS:
        rel = np.array([jp(fr, b, t) - a[3] for fr, a in zip(frames, A)])
        front += float(np.std(rel @ lat))
        side += float(np.std(rel @ fwd))
    # the base: the stance widening / narrowing and the pelvis shifting sideways over the feet (side steps, jacks,
    # lateral lunges, weight shifts). From the side that is invisible however large the sagittal motion is (lateral lunge, side squats).
    width = [float(np.dot(jp(fr, 'footL') - jp(fr, 'footR'), lat)) for fr in frames]
    shift = [float(np.dot(a[3] - (jp(fr, 'footL') + jp(fr, 'footR')) / 2, lat)) for fr, a in zip(frames, A)]
    base = float(np.std(width) + np.std(shift))
    view = 'front' if (front >= RATIO * side and front >= MIN_M) or base >= BASE_M else 'side'
    return view, front, side, base


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    J = json.load(open(args[0]))
    out = {}
    for act in args[1:]:
        if act not in J:
            print(act, 'MISSING')
            continue
        view, f, s, b = pick(J[act])
        out[act] = view
        if '--json' not in sys.argv:
            print(f'{view:5s}  {act:45s} frontal {f * 100:5.1f} cm  sagittal {s * 100:5.1f} cm  base sideways {b * 100:5.1f} cm')
    if '--json' in sys.argv:
        print(json.dumps(out))


if __name__ == '__main__':
    main()
