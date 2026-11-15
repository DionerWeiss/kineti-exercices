"""Top view of a lying move for drive_front.py: rotates the action's 3D joints so the body stands up facing the
front puppet's camera, then drive_front --top lays the drawing back down (head to the left) without a floor.

    python3 top_view.py <joints.json> <action> <out joints.json> [--side]

--side (a side-lying move, for drive_puppet.py --top): the side the body lies on faces away from the camera; the up
side of the body (sky) is mapped to the side puppet's camera axis (+x), so its sagittal motion (a side-lying shoulder
flexion, a quad stretch, a heel slide) is drawn in profile, seen from above.

A supine (or prone) body seen by drive_front's camera, which stays horizontal, points at the lens: a hip abduction,
a knee fall-out or a snow angel then show as a head drawn under the mat. Seen from above they read like PocketPhysio's
top shots. The rotation maps the body's head direction (median, horizontal) to +z and the side the chest faces (sky
for supine, floor for prone) to the camera (-y); the frame is shifted so the lowest foot end sits at z = 0. Per frame
`_low` becomes the foot/hand bone end nearest the feet (the mesh's lowest point means nothing once rotated), `_palm`
and `_tip` are rotated; `_ground` is dropped (in the top view nothing rests on a floor line). `rest` is kept as is.
"""
import json
import sys

import numpy as np

src, act, out = sys.argv[1:4]
J = json.load(open(src))
frames = J[act]


def jp(fr, b, t=0):
    return np.array(fr[b][t], float)


heads, faces = [], []
for fr in frames:
    hc = (jp(fr, 'legL') + jp(fr, 'legR')) / 2
    up = jp(fr, 'neck') - hc
    lat = (jp(fr, 'armL') - jp(fr, 'armR')) + 2 * (jp(fr, 'legL') - jp(fr, 'legR'))
    heads.append(up / np.linalg.norm(up))
    fw = np.cross(lat, up)
    faces.append(fw / np.linalg.norm(fw))
a = np.median(heads, 0)
a[2] = 0
a /= np.linalg.norm(a)
sky = 1.0 if np.median([f[2] for f in faces]) >= 0 else -1.0
c = np.array([0.0, 0.0, sky])
b = np.cross(a, c)
SIDE = '--side' in sys.argv
if SIDE:
    c = np.array([0.0, 0.0, 1.0])
    R = np.array([c, np.cross(a, c), a])   # R a = +z, R c = +x (sky -> the side camera's axis)
else:
    R = np.array([b, -c, a])          # R a = +z, R c = -y, R (a x c) = +x


def rot(v):
    return (R @ np.asarray(v, float)).tolist()


new = []
for fr in frames:
    nf = {}
    for k, v in fr.items():
        if k.startswith('_'):
            continue
        nf[k] = [rot(v[0]), rot(v[1])]
    low = {}
    for e in ('footL', 'footR', 'handL', 'handR'):
        h, t = nf[e]
        low[e] = min((h, t), key=lambda p: p[2])
    nf['_low'] = low
    nf['_palm'] = {s: rot(p) for s, p in fr.get('_palm', {}).items()}
    nf['_tip'] = {s: rot(p) for s, p in fr.get('_tip', {}).items()}
    new.append(nf)
z0 = min(min(fr['_low']['footL'][2], fr['_low']['footR'][2]) for fr in new)
y0 = float(np.median([(fr['hips'][0][1]) for fr in new]))
for fr in new:
    for k, v in fr.items():
        if k in ('_low', '_palm', '_tip'):
            for e in v:
                v[e] = [v[e][0], v[e][1] - y0, v[e][2] - z0]
        else:
            fr[k] = [[p[0], p[1] - y0, p[2] - z0] for p in v]
res = {k: J[k] for k in ('bones', 'parents', 'rest') if k in J}
res[act] = new
res['_top'] = {act: {'sky': 1.0 if SIDE else sky, 'side': SIDE}}
json.dump(res, open(out, 'w'))
print('TOP', act, 'side-lying' if SIDE else 'supine' if sky > 0 else 'prone', 'frames', len(new))
