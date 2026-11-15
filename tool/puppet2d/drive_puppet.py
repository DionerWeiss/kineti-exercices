"""Drives the LottieFiles "Split Jump" cut-out man (Dinh) with the mannequin's 3D joints, seen from the side.

    python3 drive_puppet.py <split-jump.json> <joints.json> <action> <out.json> [--kineti] [--walk]
            [--props=a,b,...] [--hands=auto|open|fist] [--nosmooth] [--debugfeet] [--debughands]

The puppet is frozen on frame T0 (its legs form a plain hip->knee->ankle chain there); every piece then gets,
per frame, the 2D angle of its 3D segment projected on the sagittal plane (screen x = forward = -Y, y = -Z).
Lengths stay the puppet's. The body is placed so the lowest shoe touches the ground (lifted by the 3D feet's
height in jumps). --kineti recolours the orange tank top in the Kineti blue.

Supports: the floor and the move's ground boxes (joints.json `_ground`, exported by export_joints.py: a step, a
chair seat, a bench, a balance disc, a walker's handles) are what feet, knees and hands rest on. A foot is
planted against the support under it; a kneeling or lying body is settled on the floor by its shoes, knees or
seat. Hands: an open hand (palm, finger block with separation lines, thumb) or the drawing's fist (running,
holding a prop); a hand that rests on a support in 3D lies flat on it (palm down, fingers forward, or flat
against a wall) and the arm reaches for it by IK, its palm pinned while it stays there. A support only the
hands touch is drawn where the drawn arms reach it (the puppet's arms are shorter than the rig's).
Props: the jobs.json names of render_mannequin.py, drawn flat from the drawn body (see the equipment section).
"""
import copy
import json
import math
import sys

import numpy as np

SRC, JOINTS, ACT, OUT = sys.argv[1:5]
KINETI = '--kineti' in sys.argv
PROPS = set()
for _a in sys.argv:
    if _a.startswith('--props='):
        PROPS |= set(_a.split('=', 1)[1].replace('+', ',').split(','))
PROPS.discard('')
T0 = 15

d = json.load(open(SRC))
comp = d['assets'][0]
L = {l['ind']: l for l in comp['layers']}
name = {l['nm']: l['ind'] for l in comp['layers']}


# ---------- property evaluation and freezing
def lerp(a, b, u):
    if isinstance(a, dict):  # bezier path
        return {**a, **{k: lerp(a[k], b[k], u) for k in ('i', 'o', 'v')}}
    if isinstance(a, list):
        return [lerp(x, y, u) for x, y in zip(a, b)]
    return a + (b - a) * u


def at(prop, t):
    if prop.get('a') != 1:
        return prop['k']
    ks = prop['k']
    if t <= ks[0]['t']:
        return ks[0]['s']
    for i in range(len(ks) - 1):
        a, b = ks[i], ks[i + 1]
        if a['t'] <= t < b['t']:
            end = b.get('s', a.get('e'))
            if a.get('h') == 1 or end is None:
                return a['s']
            return lerp(a['s'], end, (t - a['t']) / (b['t'] - a['t']))
    last = ks[-1]
    return last.get('s', ks[-2].get('e'))


def freeze(o, t):
    if isinstance(o, dict):
        if o.get('a') == 1 and isinstance(o.get('k'), list) and o['k'] and isinstance(o['k'][0], dict) and 't' in o['k'][0]:
            v = at(o, t)
            o['a'] = 0
            o['k'] = v[0] if isinstance(v, list) and len(v) == 1 and isinstance(v[0], dict) else v
            if isinstance(o['k'], list) and len(o['k']) == 1 and not isinstance(o['k'][0], dict):
                o['k'] = o['k'][0]
            return
        for v in o.values():
            freeze(v, t)
    elif isinstance(o, list):
        for v in o:
            freeze(v, t)


# keep the FK chain of frames 8..23 and everything always visible; drop the other leg variants
KEEP_LEGS = {'dui R 2', 'chan R 2', 'giay R 2', 'dui L 2', 'chan L 2', 'giay L 2'}
drop = []
for l in comp['layers']:
    if l['nm'] in KEEP_LEGS or (l.get('ip', 0) <= 0 and l.get('op', 0) >= 300):
        continue
    drop.append(l['nm'])
byind = {l['ind']: l for l in comp['layers']}
changed = True
while changed:
    changed = False
    for l in comp['layers']:
        par = l.get('parent')
        if par and byind[par]['nm'] in drop and l['nm'] not in drop:
            drop.append(l['nm'])
            changed = True
comp['layers'] = [l for l in comp['layers'] if l['nm'] not in drop]
print('DROP', drop)
for l in comp['layers']:
    freeze(l, T0)
L = {l['ind']: l for l in comp['layers']}
name = {l['nm']: l['ind'] for l in comp['layers']}


def tr(ks):
    def g(k, dflt):
        v = ks.get(k)
        if v is None:
            return dflt
        v = v['k']
        if isinstance(v, list) and v and isinstance(v[0], dict):   # keyed (a flipped flat hand): its first key
            v = v[0]['s']
        return v
    p = g('p', [0, 0])
    a = g('a', [0, 0])
    s = g('s', [100, 100])
    r = g('r', 0)
    r = r[0] if isinstance(r, list) else r
    return np.array(p[:2], float), np.array(a[:2], float), np.array(s[:2], float) / 100, float(r)


def mat(p, a, s, r):
    c, sn = math.cos(math.radians(r)), math.sin(math.radians(r))
    R = np.array([[c, -sn, 0], [sn, c, 0], [0, 0, 1]])  # y down: positive r turns clockwise on screen
    S = np.diag([s[0], s[1], 1])
    T = np.array([[1, 0, p[0]], [0, 1, p[1]], [0, 0, 1]])
    A = np.array([[1, 0, -a[0]], [0, 1, -a[1]], [0, 0, 1]])
    return T @ R @ S @ A


REST = {i: tr(l['ks']) for i, l in L.items()}


SCL = {}   # per-frame scale of a layer (a planted leg stretched a little to reach its floor line)


def world(i, rot=None, pos=None):
    p, a, s, r = REST[i]
    if i in SCL:
        s = s * SCL[i]
    if rot is not None and i in rot:
        r = rot[i]
    if pos is not None and i in pos:
        p = pos[i]
    M = mat(p, a, s, r)
    par = L[i].get('parent')
    return world(par, rot, pos) @ M if par else M


def pivot(i, rot=None, pos=None):
    return (world(i, rot, pos) @ np.array([*REST[i][1], 1]))[:2]


def shape_points(o, M):
    """All path vertices of a layer's shapes (with group transforms), in world space."""
    out = []
    for s in o:
        if s.get('ty') == 'gr':
            items = s.get('it', [])
            t = next((x for x in items if x.get('ty') == 'tr'), None)
            G = M
            if t is not None:
                G = M @ mat(*tr(t))
            out += shape_points(items, G)
        elif s.get('ty') == 'sh':
            k = s['ks']['k']
            k = k[0] if isinstance(k, list) else k
            for v in k['v']:
                out.append((M @ np.array([v[0], v[1], 1]))[:2])
    return out


def ang(v):
    return math.degrees(math.atan2(v[1], v[0]))


I = name
# segments: piece -> (distal point in the puppet, 3D joints (from, to))
SEG = {
    'than': (lambda: pivot(I['co']), ('hips', 'neck')),
    'dui R 2': (lambda: pivot(I['chan R 2']), ('legR', 'kneeR')),
    'chan R 2': (lambda: pivot(I['giay R 2']), ('kneeR', 'footR')),
    'dui L 2': (lambda: pivot(I['chan L 2']), ('legL', 'kneeL')),
    'chan L 2': (lambda: pivot(I['giay L 2']), ('kneeL', 'footL')),
    'canh tay R': (lambda: pivot(I['cang tay R']), ('armR', 'elbowR')),
    'cang tay R': (lambda: pivot(I['ban tay R']), ('elbowR', 'handR')),
    'canh tay L': (lambda: pivot(I['cang tay L']), ('armL', 'elbowL')),
    'cang tay L': (lambda: pivot(I['ban tay L']), ('elbowL', 'handL')),
}
PROX = {'than': lambda: pivot(I['mong'])}  # the torso's direction runs from the pelvis to the neck
PHI = {}
for nm, (dist, _) in SEG.items():
    prox = PROX.get(nm, lambda nm=nm: pivot(I[nm]))()
    PHI[nm] = ang(dist() - prox)
print('PUPPET ANGLES', {k: round(v, 1) for k, v in PHI.items()})


def hull(P_):
    P_ = sorted(map(tuple, P_))
    cross = lambda o, a, b: (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p_ in P_:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p_) <= 0:
            lo.pop()
        lo.append(p_)
    for p_ in reversed(P_):
        while len(up) >= 2 and cross(up[-2], up[-1], p_) <= 0:
            up.pop()
        up.append(p_)
    return [np.array(p_) for p_ in lo[:-1] + up[:-1]]


def sole(s):
    """The drawn shoe's sole: the longest bottom edge of its outline (screen angle, heel->toe), and how far the
    ankle sits above that line."""
    i = I['giay %s 2' % s]
    H = hull(shape_points(L[i]['shapes'], world(i)))
    best = None
    for a_, b_ in zip(H, H[1:] + H[:1]):
        e = b_ - a_
        n = np.array([e[1], -e[0]]) / (np.linalg.norm(e) + 1e-9)       # outward normal (hull is CCW in y-down)
        if n[1] > 0.5 and (best is None or np.linalg.norm(e) > np.linalg.norm(best[1] - best[0])):
            best = (a_, b_)
    a_, b_ = best
    if b_[0] < a_[0]:
        a_, b_ = b_, a_
    e = (b_ - a_) / np.linalg.norm(b_ - a_)
    an = pivot(i)
    h = abs((an - a_)[0] * e[1] - (an - a_)[1] * e[0])
    return ang(b_ - a_), h


# The far (L) leg is drawn shorter and its foot sits higher on the page (the artist's perspective). Keep the art,
# and give each foot its own floor line: the far one OFF px above the near one, measured with both legs straight
# down and the soles flat. A single floor line made the body sink whenever it stood on the far leg alone.
def leg_reach(s):
    l1 = np.linalg.norm(pivot(I['chan %s 2' % s]) - pivot(I['dui %s 2' % s]))
    l2 = np.linalg.norm(pivot(I['giay %s 2' % s]) - pivot(I['chan %s 2' % s]))
    return l1 + l2 + sole(s)[1]


OFF = {'R': 0.0, 'L': float((pivot(I['dui R 2'])[1] + leg_reach('R')) - (pivot(I['dui L 2'])[1] + leg_reach('L')))}
SOLE = {s: sole(s)[0] for s in 'LR'}
print('FLOOR OFF', {k: round(v, 1) for k, v in OFF.items()}, 'sole angles', {k: round(v, 1) for k, v in SOLE.items()})

# ---------- the 3D motion
J = json.load(open(JOINTS))
frames = J[ACT]


def smooth_frames(frames, sigma=1.2):
    """Light Gaussian smoothing of every joint over time, wrapping around (the moves loop): the 3D builder
    has single-frame pops where a foot is planted or let go; spread over a few frames they read as motion."""
    names = [b for b in frames[0] if not b.startswith('_')]
    A_ = np.array([[frames[f][b] for b in names] for f in range(len(frames))], float)   # F x B x 2 x 3
    r = int(3 * sigma) + 1
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    out = np.zeros_like(A_)
    for j, w in zip(range(-r, r + 1), k):
        out += w * np.roll(A_, -j, axis=0)
    return [{**{b: out[f, i].tolist() for i, b in enumerate(names)}, **{b: frames[f][b] for b in frames[f] if b.startswith('_')}}
            for f in range(len(frames))]


def despike_frames(frames, min_m=0.003, ratio=1.5):
    """One-frame pops of the whole 3D pose (the builder joins a move's two halves with a frame that jumps out and back,
    up to 15 mm): a frame whose joints sit away from both neighbours while the neighbours agree is replaced by their
    mean (contacts, _low, _palm, _tip included). Every other frame is left as built: not a smoothing."""
    names = [b for b in frames[0] if not b.startswith('_')]
    A_ = np.array([[frames[f][b] for b in names] for f in range(len(frames))], float).reshape(len(frames), -1, 3)
    n_ = len(frames)
    out = list(frames)
    fixed = []
    for f in range(n_):
        a_, b_, c_ = A_[f - 1], A_[f], A_[(f + 1) % n_]
        s = float(np.median(np.minimum(np.linalg.norm(b_ - a_, axis=1), np.linalg.norm(b_ - c_, axis=1))))
        s0 = float(np.median(np.linalg.norm(c_ - a_, axis=1)))
        # a turning point (the bottom of a squat) also sits away from two neighbours that agree; a pop does not
        # come from motion: the steps just outside it are small
        outer = float(np.median(np.maximum(np.linalg.norm(A_[f - 1] - A_[f - 2], axis=1),
                                           np.linalg.norm(A_[(f + 2) % n_] - A_[(f + 1) % n_], axis=1))))
        if s > min_m and s > ratio * s0 and outer < 0.5 * s:
            fa, fc = frames[f - 1], frames[(f + 1) % n_]
            def mean(x, y):
                if isinstance(x, dict):
                    return {k: mean(x[k], y[k]) for k in x}
                if isinstance(x, list):
                    return [mean(u, v) for u, v in zip(x, y)]
                return (x + y) / 2 if isinstance(x, (int, float)) else x
            out[f] = {k: (mean(fa[k], fc[k]) if k in fc else v) for k, v in frames[f].items()}
            fixed.append(f)
    if fixed:
        print('DESPIKE 3D frames', fixed)
    return out


frames = despike_frames(frames)
if '--nosmooth' not in sys.argv:
    frames = smooth_frames(frames)


WALK = '--walk' in sys.argv
# a side-lying move rotated upright by top_view.py --side: drawn in profile as seen from above, laid down at the end
TOP = (J.get('_top') or {}).get(ACT)
if TOP:
    print('TOP VIEW side-lying')
_f0 = J[ACT][0]
_lat = (np.array(_f0['armL'][0]) - np.array(_f0['armR'][0])) + 2 * (np.array(_f0['legL'][0]) - np.array(_f0['legR'][0]))
_lat[2] = 0
FWD = np.cross(_lat / np.linalg.norm(_lat), [0, 0, 1])
FWD /= np.linalg.norm(FWD)
FWD_REST = np.array([0.0, -1.0, 0.0])          # the rig's rest pose faces -Y
print('FACING', np.round(FWD, 2))


def P(v, fwd=None):  # sagittal projection, screen coords (x forward, y down), metres; the action's own facing
    f = FWD if fwd is None else fwd
    return np.array([float(np.dot(v, f)), -float(v[2])])


def jp(fr, b, tail=False):
    return np.array(fr[b][1 if tail else 0])


def a3(fr, b0, b1, fwd=None):
    return ang(P(jp(fr, b1), fwd) - P(jp(fr, b0), fwd))


def ankle(fr, s):
    """Foot angle relative to the shin in the sagittal plane (90 = neutral)."""
    shin = a3(fr, 'knee' + s, 'foot' + s)
    foot = ang(P(jp(fr, 'foot' + s, True)) - P(jp(fr, 'foot' + s)))
    return foot - shin


# pixels per metre from the leg length
pl = np.linalg.norm(pivot(I['chan R 2']) - pivot(I['dui R 2'])) + np.linalg.norm(pivot(I['giay R 2']) - pivot(I['chan R 2']))
f0 = frames[0]
l3 = np.linalg.norm(jp(f0, 'kneeR') - jp(f0, 'legR')) + np.linalg.norm(jp(f0, 'footR') - jp(f0, 'kneeR'))
K = pl / l3
ANK0 = {s: ankle(f0, s) for s in 'LR'}
LEG_LEN = {s: (float(np.linalg.norm(pivot(I['chan %s 2' % s]) - pivot(I['dui %s 2' % s]))),
               float(np.linalg.norm(pivot(I['giay %s 2' % s]) - pivot(I['chan %s 2' % s])))) for s in 'LR'}
LEG3 = {s: float(np.linalg.norm(jp(J['rest'], 'knee' + s) - jp(J['rest'], 'leg' + s))
                 + np.linalg.norm(jp(J['rest'], 'foot' + s) - jp(J['rest'], 'knee' + s))) for s in 'LR'}
print('LEGS puppet', {s: tuple(round(x, 1) for x in v) for s, v in LEG_LEN.items()}, '3D', {s: round(v, 3) for s, v in LEG3.items()})
HAS_LOW = '_low' in frames[0]
# the supports the move was built on: the floor (FLOOR_Z) and the raised boxes of kineti_builder's "ground"
# (a step, a chair seat under the hands, a bench, a balance disc...), in world metres
GROUND = (J.get('_ground') or {}).get(ACT) or {}
FLOOR_Z = float(GROUND.get('base', 0.0))
BOXES = [b for b in GROUND.get('boxes', []) if b[4] > FLOOR_Z + 0.03]


def sup_h(p, margin=0.04):
    """Height of the support under the world point p: the floor, or the highest ground box there that is not
    above p (a foot beside a step's edge, at floor level, is on the floor)."""
    h = FLOOR_Z
    for x0, x1, y0, y1, hb in BOXES:
        if x0 - margin <= p[0] <= x1 + margin and y0 - margin <= p[1] <= y1 + margin and hb <= p[2] + 0.05:
            h = max(h, hb)
    return h


def _rest_gap(e):
    """How far a foot's lowest point stays above the support under it over the move. Near zero (or a little
    below: the builder lets a sole sink) when the foot rests; large when it never touches (a knee push-up)."""
    return sorted(fr['_low'][e][2] - sup_h(fr['_low'][e]) for fr in frames)[min(2, len(frames) - 1)]   # not a 1-2 frame dip


LOW0 = {}
if HAS_LOW:
    for _e in ('footL', 'footR'):
        _g = _rest_gap(_e)
        LOW0[_e] = _g if _g < 0.06 else 0.0
# the feet that never rest on anything do not set the floor line (a knee push-up: the feet are in the air)
_resting = [s_ for s_ in 'LR' if not HAS_LOW or _rest_gap('foot' + s_) < 0.06]
foot_floor = min(min(fr['foot' + s_][0][2] for s_ in (_resting or 'LR')) for fr in frames)
if HAS_LOW and not _resting:
    foot_floor = min(min(fr['footL'][0][2], fr['footR'][0][2]) for fr in frames) - min(
        min(fr['_low']['footL'][2], fr['_low']['footR'][2]) for fr in frames) + FLOOR_Z


def low_z(fr, e):
    """Height of the lowest point of a foot's 3D mesh above the support under it (the floor or a box), less the
    little it always sinks there (toes on tiptoe give a positive value)."""
    if HAS_LOW:
        return fr['_low'][e][2] - sup_h(fr['_low'][e]) - LOW0[e]
    return fr[e][0][2] - foot_floor


def foot_sup(fr, s):
    """Support height under a foot, metres above the floor."""
    return (sup_h(fr['_low']['foot' + s]) if HAS_LOW else FLOOR_Z) - FLOOR_Z


# where the resting feet stand (0 on the floor, the box top on a balance disc): the drawing's ground line is there
_hf = [foot_sup(fr, s_) for fr in frames for s_ in _resting if low_z(fr, 'foot' + s_) < 0.012]
H_FEET = float(min(_hf)) if _hf else 0.0          # the lowest support the feet rest on: foot_floor's
print('SUPPORTS floor', FLOOR_Z, 'boxes', BOXES, 'feet rest', _resting, 'on', round(H_FEET, 3))


def contact(fr, s, near=0.01, far=0.035):
    """1 when the 3D foot rests on the floor, 0 once it is `far` above it, smooth in between."""
    w = float(np.clip((far - low_z(fr, 'foot' + s)) / (far - near), 0, 1))
    return w * w * (3 - 2 * w)
print(f'K {K:.1f} px/m, ankle at frame 0 {ANK0}')

PARENT_SEG = {'than': None, 'dui R 2': 'than', 'dui L 2': 'than', 'canh tay R': 'than', 'canh tay L': 'than',
              'chan R 2': 'dui R 2', 'chan L 2': 'dui L 2', 'cang tay R': 'canh tay R', 'cang tay L': 'canh tay L',
              'giay R 2': 'chan R 2', 'giay L 2': 'chan L 2'}
shoe_pts = {s: [] for s in 'LR'}
ground = max(p[1] for s in 'LR' for p in shape_points(L[I['giay %s 2' % s]]['shapes'], world(I['giay %s 2' % s])))

keys = {nm: [] for nm in PARENT_SEG}
keys.update({'ban tay L': [], 'ban tay R': []})


def wrist(fr, s, fwd=None):
    """Sagittal angle of the 3D hand bone against the forearm (degrees, wrapped to -180..180)."""
    a = ang(P(jp(fr, 'hand' + s, True), fwd) - P(jp(fr, 'hand' + s), fwd)) - a3(fr, 'elbow' + s, 'hand' + s, fwd)
    return (a + 180) % 360 - 180


def neck(fr, fwd=None):
    """Sagittal angle of the 3D neck bone (head direction) against the trunk."""
    a = ang(P(jp(fr, 'neck', True), fwd) - P(jp(fr, 'neck'), fwd)) - a3(fr, 'hips', 'neck', fwd)
    return (a + 180) % 360 - 180


WRIST0 = {s: wrist(J['rest'], s, FWD_REST) for s in 'LR'}
NECK0 = neck(J['rest'], FWD_REST)
ARM_LEN = {s: (float(np.linalg.norm(pivot(I['cang tay ' + s]) - pivot(I['canh tay ' + s]))),
               float(np.linalg.norm(pivot(I['ban tay ' + s]) - pivot(I['cang tay ' + s])))) for s in 'LR'}
ARM3 = {s: float(np.linalg.norm(jp(J['rest'], 'elbow' + s) - jp(J['rest'], 'arm' + s))
                 + np.linalg.norm(jp(J['rest'], 'hand' + s) - jp(J['rest'], 'elbow' + s))) for s in 'LR'}
keys['co'] = []


def _knee_r(s):
    """Half the drawn leg's thickness at the knee: how far the kneecap's outline sits below the knee pivot."""
    kp = pivot(I['chan %s 2' % s])
    ax = pivot(I['giay %s 2' % s]) - kp
    ax /= np.linalg.norm(ax)
    pts = bez_points(L[I['chan %s 2' % s]]['shapes'], world(I['chan %s 2' % s]))
    near = np.abs((pts - kp) @ ax) < 14
    return float(np.abs((pts[near] - kp) @ np.array([ax[1], -ax[0]])).max()) if near.sum() else 18.0




def solve2(H, T, l1, l2, guide):
    """2-bone IK in the drawing: world angles of both pieces reaching T from H; of the two knee/elbow
    solutions, the one nearer `guide` (continuous; no flipping when the limb is almost straight)."""
    d_ = min(max(np.linalg.norm(T - H), abs(l1 - l2) + 1e-3), l1 + l2 - 1e-3)
    base = ang(T - H)
    al = math.degrees(math.acos(max(-1.0, min(1.0, (l1 * l1 + d_ * d_ - l2 * l2) / (2 * l1 * d_)))))
    Tn = H + (T - H) / max(np.linalg.norm(T - H), 1e-6) * d_
    best = None
    for sg in (1, -1):
        a_ = math.radians(base + sg * al)
        Kp = H + l1 * np.array([math.cos(a_), math.sin(a_)])
        dist = np.linalg.norm(Kp - guide)
        if best is None or dist < best[0]:
            best = (dist, base + sg * al, Kp)
    return best[1], ang(Tn - best[2])


def ik2(fr, prox, mid, lens, l3, b0, b1, b2, rot_t):
    """The end goes where the 3D end is relative to the root, scaled to the drawn limb; the middle joint
    follows the 3D one (scaled the same way)."""
    l1, l2 = lens
    H = pivot(I[prox], rot_t)
    sc = (l1 + l2) / l3
    T = H + (P(jp(fr, b2)) - P(jp(fr, b0))) * sc
    guide = H + (P(jp(fr, b1)) - P(jp(fr, b0))) * sc
    return solve2(H, T, l1, l2, guide)


def wdelta(v):
    return (v + 180) % 360 - 180
# ---------- hands: the drawing's running fist, or a relaxed open hand drawn along the forearm
RUN = ('jog', 'run', 'sprint', 'march', 'high-knee', 'butt-kick', 'skater', 'punch', 'box')
HANDS = next((a.split('=')[1] for a in sys.argv if a.startswith('--hands=')), 'auto')
_open_props = any(p_ in ('heldball', 'waistball') or p_.startswith(('pball-v-h', 'wallpress-h', 'tableball', 'wallat-h'))
                  for p_ in PROPS)
if HANDS == 'auto' and any(w in ACT for w in RUN) and not _open_props:     # palms on a ball stay open
    HANDS = 'fist'


def hexc(h):
    return [round(int(h[i:i + 2], 16) / 255, 4) for i in (1, 3, 5)] + [1]


def smooth_path(pts, closed=True):
    """Catmull-Rom through the points, as a Lottie bezier path."""
    pts = [np.array(p, float) for p in pts]
    n = len(pts)
    v, ii, oo = [], [], []
    for k in range(n):
        a = pts[(k - 1) % n] if closed or k > 0 else pts[k]
        b = pts[(k + 1) % n] if closed or k < n - 1 else pts[k]
        t = (b - a) / 6
        v.append([round(x, 2) for x in pts[k]])
        oo.append([round(x, 2) for x in t])
        ii.append([round(-x, 2) for x in t])
    return {'c': closed, 'v': v, 'i': ii, 'o': oo}


def first_fill(nm):
    """Solid fill of a layer, so the drawn hand can use the forearm's own skin."""
    def walk(shapes):
        for s in shapes or []:
            if s.get('ty') == 'fl':
                k = s.get('c', {}).get('k')
                if isinstance(k, list) and k and not isinstance(k[0], dict):
                    return list(k)
            elif s.get('ty') == 'gr':
                c = walk(s.get('it'))
                if c:
                    return c
    return walk(L[I[nm]]['shapes'])


def group(name, path, fill=None, stroke=None, width=1.6):
    it = [{'ty': 'sh', 'nm': 'path', 'ks': {'a': 0, 'k': path}}]
    if fill:
        it.append({'ty': 'fl', 'c': {'a': 0, 'k': fill if isinstance(fill, list) else hexc(fill)},
                   'o': {'a': 0, 'k': 100}, 'r': 1, 'nm': 'fill'})
    if stroke:
        it.append({'ty': 'st', 'c': {'a': 0, 'k': hexc(stroke)}, 'o': {'a': 0, 'k': 100}, 'w': {'a': 0, 'k': width},
                   'lc': 2, 'lj': 2, 'nm': 'stroke'})
    it.append({'ty': 'tr', 'p': {'a': 0, 'k': [0, 0]}, 'a': {'a': 0, 'k': [0, 0]}, 's': {'a': 0, 'k': [100, 100]},
               'r': {'a': 0, 'k': 0}, 'o': {'a': 0, 'k': 100}, 'sk': {'a': 0, 'k': 0}, 'sa': {'a': 0, 'k': 0}})
    return {'ty': 'gr', 'nm': name, 'it': it}


def hand_geom(s):
    """The wrist frame of a hand, from the drawn forearm: the wrist pivot W, the forearm direction u and the thumb
    side t (world and hand-layer space), the forearm's half width hw at the wrist (and its centre offset mid
    along t), and the hand length Lh. Every hand drawing is laid out in (along u, across t) pixels from W."""
    hand, fore = I['ban tay ' + s], I['cang tay ' + s]
    W = pivot(hand)
    u = W - pivot(fore)
    flen = float(np.linalg.norm(u))
    u /= flen
    t = np.array([u[1], -u[0]])                       # thumb side: up when the forearm points forward
    Minv = np.linalg.inv(world(hand))[:2, :2]
    ul, tl = Minv @ u, Minv @ t
    ul, tl = ul / np.linalg.norm(ul), tl / np.linalg.norm(tl)
    pts = bez_points(L[fore]['shapes'], world(fore))
    along, across = (pts - W) @ u, (pts - W) @ t
    near = np.abs(along + 6) < 8                       # the forearm's outline just short of the wrist
    if near.sum() > 4:
        lo, hi = float(across[near].min()), float(across[near].max())
    else:
        lo, hi = -7.0, 7.0
    mid, hw = (lo + hi) / 2, max(5.0, min(11.0, (hi - lo) / 2))
    ext = float(max(0.0, along.max()))                 # how far the forearm's rounded end runs past the wrist
    return dict(W=W, u=u, t=t, A=np.array(REST[hand][1], float), ul=ul, tl=tl, mid=mid, hw=hw,
                Lh=0.76 * flen, flen=flen, ext=ext)


def skin_shade(c, k=0.9):
    return [round(c[0] * k, 4), round(c[1] * k * 0.97, 4), round(c[2] * k * 0.97, 4), 1]


def line_group(name, path, color, width):
    it = [{'ty': 'sh', 'nm': 'path', 'ks': {'a': 0, 'k': path}},
          {'ty': 'st', 'c': {'a': 0, 'k': color}, 'o': {'a': 0, 'k': 100}, 'w': {'a': 0, 'k': width},
           'lc': 2, 'lj': 2, 'nm': 'stroke'}]
    it.append({'ty': 'tr', 'p': {'a': 0, 'k': [0, 0]}, 'a': {'a': 0, 'k': [0, 0]}, 's': {'a': 0, 'k': [100, 100]},
               'r': {'a': 0, 'k': 0}, 'o': {'a': 0, 'k': 100}, 'sk': {'a': 0, 'k': 0}, 'sa': {'a': 0, 'k': 0}})
    return {'ty': 'gr', 'nm': name, 'it': it}


def wrap(name, items, A):
    """A group whose transform (opacity, mirror) can be animated, pivoting on the wrist A (layer space)."""
    return {'ty': 'gr', 'nm': name, 'it': items + [
        {'ty': 'tr', 'p': {'a': 0, 'k': [float(A[0]), float(A[1])]}, 'a': {'a': 0, 'k': [float(A[0]), float(A[1])]},
         's': {'a': 0, 'k': [100, 100]}, 'r': {'a': 0, 'k': 0}, 'o': {'a': 0, 'k': 100},
         'sk': {'a': 0, 'k': 0}, 'sa': {'a': 0, 'k': 0}}]}


def hand_shapes(s):
    """Two drawings of the hand in the flat Dinh style, in the hand layer's space, both joined to the forearm by
    a round wrist cap centred on the wrist pivot (so the joint stays closed at any wrist angle):
      open:  the relaxed hand seen from the side - a palm a little wider than the wrist, the four fingers as one
             rounded block with thin separation lines, the thumb on the thumb side;
      flat:  the hand lying palm down on a support, fingers forward along the support (planted hands).
    The skin is the forearm's own fill; lines use a darker shade of it (near and far arm keep their tones)."""
    g = HG[s]
    hw, mid, Lh = g['hw'], g['mid'], g['Lh']
    Q = lambda sv, wv: g['A'] + sv * g['ul'] + (mid + wv) * g['tl']
    base = first_fill('cang tay ' + s)
    shade = skin_shade(base, 0.9)
    shade = skin_shade(base, 0.86)
    cap = [(-hw * math.cos(math.radians(a_)) * 0.98, hw * math.sin(math.radians(a_)) * 0.98)
           for a_ in (-90, -135, 180, 135, 90)]
    # open hand: wrist cap, the back of the hand rising to the knuckles (a little wider than the wrist), the
    # fingers as one block to a rounded tip, the little-finger edge back to the wrist with the palm's soft bulge
    open_pts = cap + [(0.14 * Lh, 1.2 * hw), (0.32 * Lh, 1.44 * hw), (0.48 * Lh, 1.42 * hw), (0.7 * Lh, 1.2 * hw),
                      (0.88 * Lh, 0.94 * hw), (0.99 * Lh, 0.46 * hw), (1.0 * Lh, -0.08 * hw), (0.9 * Lh, -0.48 * hw),
                      (0.72 * Lh, -0.74 * hw), (0.52 * Lh, -1.02 * hw), (0.32 * Lh, -1.3 * hw), (0.12 * Lh, -1.2 * hw)]
    palm = smooth_path([Q(*p_) for p_ in open_pts])
    # the thumb lies along the index finger, its tip a little above the back of the hand
    thumb = smooth_path([Q(*p_) for p_ in (
        (0.02 * Lh, 0.95 * hw), (0.12 * Lh, 1.6 * hw), (0.28 * Lh, 2.05 * hw), (0.44 * Lh, 2.2 * hw),
        (0.55 * Lh, 2.0 * hw), (0.52 * Lh, 1.66 * hw), (0.36 * Lh, 1.36 * hw))])
    crease = smooth_path([Q(*p_) for p_ in ((0.22 * Lh, 1.34 * hw), (0.36 * Lh, 1.5 * hw), (0.5 * Lh, 1.7 * hw))],
                         closed=False)
    fingers = []
    for w0, w1 in ((0.7, 0.52), (0.16, 0.1), (-0.36, -0.28)):
        fingers.append(line_group('dedo', smooth_path([Q(0.62 * Lh, w0 * hw), Q(0.76 * Lh, (w0 + w1) / 2 * hw),
                                                        Q(0.88 * Lh, w1 * hw)], closed=False), shade, 1.2))
    # (a Lottie group draws its first item on top)
    open_g = [line_group('dobra', crease, shade, 1.4), group('polegar', thumb, fill=base)] + fingers + [
        group('palma', palm, fill=base)]
    # flat hand, palm down on the support (the -t side), fingers forward. Its heel reaches as low as the
    # forearm's rounded end, so the wrist does not poke through the support.
    Dn = max(1.04 * hw - mid, g['ext'] - 1.0)
    wb = -Dn - mid
    flat_pts = [(-0.55 * hw, wb + 0.25 * hw), (-hw, 0.0), (-0.7 * hw, 0.7 * hw), (0.0, hw),
                (0.2 * Lh, 0.96 * hw), (0.4 * Lh, 0.66 * hw), (0.55 * Lh, 0.56 * hw), (0.74 * Lh, 0.22 * hw),
                (0.92 * Lh, wb + 0.95 * hw), (1.03 * Lh, wb + 0.48 * hw), (1.0 * Lh, wb + 0.04 * hw),
                (0.62 * Lh, wb), (0.25 * Lh, wb), (0.05 * Lh, wb)]
    flat = smooth_path([Q(*p_) for p_ in flat_pts])
    flat_l = [line_group('dedo', smooth_path([Q(0.6 * Lh, 0.3 * hw), Q(0.78 * Lh, wb + 1.02 * hw),
                                              Q(0.94 * Lh, wb + 0.62 * hw)], closed=False), shade, 1.4),
              line_group('dedo', smooth_path([Q(0.6 * Lh, wb + 0.55 * hw), Q(0.8 * Lh, wb + 0.5 * hw),
                                              Q(0.95 * Lh, wb + 0.36 * hw)], closed=False), shade, 1.3),
              line_group('polegar', smooth_path([Q(0.12 * Lh, 0.55 * hw), Q(0.3 * Lh, 0.38 * hw),
                                                 Q(0.46 * Lh, 0.12 * hw)], closed=False), shade, 1.3)]
    flat_g = flat_l + [group('palma', flat, fill=base)]
    g['floor_drop'] = {1: Dn, -1: Dn + 2 * mid}          # wrist pivot above the support (fingers fwd/back)
    g['reach'] = 1.0 * Lh
    return [wrap('mao aberta', open_g, g['A']), wrap('mao apoiada', flat_g, g['A'])]


def bez_points(shapes, M, n=16):
    """Points along every bezier path of a layer's shapes (group transforms applied), world space."""
    out = []
    for sh in shapes:
        if sh.get('ty') == 'gr':
            t_ = next((x for x in sh['it'] if x.get('ty') == 'tr'), None)
            out += list(bez_points(sh['it'], M @ mat(*tr(t_)) if t_ else M, n))
        elif sh.get('ty') == 'sh':
            k = sh['ks']['k']
            k = k[0] if isinstance(k, list) else k
            v, ii, oo = np.array(k['v']), np.array(k['i']), np.array(k['o'])
            m = len(v)
            for j in range(m if k.get('c') else m - 1):
                p0, p3 = v[j], v[(j + 1) % m]
                p1, p2 = p0 + oo[j], p3 + ii[(j + 1) % m]
                for q in np.linspace(0, 1, n):
                    p = (1 - q) ** 3 * p0 + 3 * (1 - q) ** 2 * q * p1 + 3 * (1 - q) * q * q * p2 + q ** 3 * p3
                    out.append((M @ np.array([p[0], p[1], 1]))[:2])
    return np.array(out)


HG = {s_: hand_geom(s_) for s_ in 'LR'}
FIST_SHAPES = {s_: L[I['ban tay ' + s_]]['shapes'] for s_ in 'LR'}
_fist_pts = {s_: np.array(shape_points(FIST_SHAPES[s_], np.eye(3))) for s_ in 'LR'}
FIST_C = {s_: (_fist_pts[s_].min(0) + _fist_pts[s_].max(0)) / 2 for s_ in 'LR'}
HELD = {'dumbbell', 'bandhands', 'bandanchor', 'bandanchor1', 'bandfeet', 'stick', 'walker', 'walkergo', 'pulley'}


def grips(s_):
    """Hand s_ holds something (render_mannequin.grips): a handle prop, a cane on that side, a band/towel/stick end."""
    if PROPS & HELD or 'cane' + s_ in PROPS:
        return True
    return any(p_.startswith(('band-', 'towel-', 'stick-', 'stickend-', 'stickfloor-')) and 'h' + s_ in p_.split('-')[1:]
               for p_ in PROPS)


FIST = {s_: HANDS == 'fist' or (HANDS == 'auto' and grips(s_)) for s_ in 'LR'}
for s_ in 'LR':
    shp = hand_shapes(s_)
    if FIST[s_]:                              # the drawing's own fist (running, holding), plus the flat hand
        shp = [wrap('punho', FIST_SHAPES[s_], HG[s_]['A']), shp[1]]
    L[I['ban tay ' + s_]]['shapes'] = shp
print('HAND GEOM', {s_: {k: round(float(HG[s_][k]), 1) for k in ('hw', 'mid', 'Lh', 'flen', 'ext')} for s_ in 'LR'})
print('HANDS', HANDS)

# pull each shoe a little up the shin so the ankle of the drawing meets the leg (the sneaker's pivot sits
# a few pixels short of the shin outline)
for s in 'LR':
    sho, shin = I['giay %s 2' % s], I['chan %s 2' % s]
    delta = pivot(shin) - pivot(sho)
    delta = delta / max(np.linalg.norm(delta), 1e-6) * 26.0
    Wp = world(L[sho]['parent'])[:2, :2]
    p, a, sc, r = REST[sho]
    newp = p + np.linalg.inv(Wp) @ delta
    REST[sho] = (newp, a, sc, r)
    pk = L[sho]['ks']['p']['k']
    pk[0], pk[1] = float(newp[0]), float(newp[1])
# the shoe moved, so the drawn shin is shorter than the length IK and the metre scale were given.
# leaving the old length makes a straight leg look short, and the floor reach folds the knee to fit.
LEG_LEN = {s: (float(np.linalg.norm(pivot(I['chan %s 2' % s]) - pivot(I['dui %s 2' % s]))),
               float(np.linalg.norm(pivot(I['giay %s 2' % s]) - pivot(I['chan %s 2' % s])))) for s in 'LR'}
pl = LEG_LEN['R'][0] + LEG_LEN['R'][1]
K = pl / l3
OFF = {'R': 0.0, 'L': float((pivot(I['dui R 2'])[1] + leg_reach('R')) - (pivot(I['dui L 2'])[1] + leg_reach('L')))}
KNEE_R = {s_: _knee_r(s_) for s_ in 'LR'}
print('LEGS drawn', {s: tuple(round(x, 1) for x in v) for s, v in LEG_LEN.items()}, 'K', round(K, 1))

def foot_pitch(fr, s, fwd=None):
    return ang(P(jp(fr, 'foot' + s, True), fwd) - P(jp(fr, 'foot' + s), fwd))


FOOT0 = {s: foot_pitch(J['rest'], s, FWD_REST) for s in 'LR'}
_fp = foot_pitch
foot_pitch = lambda fr, s: wdelta(_fp(fr, s) - FOOT0[s])
# standing straight: the near hip right above a flat sole on the floor line
_hipR, _mong = pivot(I['dui R 2']), pivot(I['mong'])
C_HIP = (ground - leg_reach('R') - _hipR[1] + _mong[1]) + K * J['rest']['hips'][0][2] - K * (J['rest']['footR'][0][2] - foot_floor)
def ankle_rel(fr, s, fwd=None):
    return ang(P(jp(fr, 'foot' + s, True), fwd) - P(jp(fr, 'foot' + s), fwd)) - a3(fr, 'knee' + s, 'foot' + s, fwd)


ANKLE0 = {s: ankle_rel(J['rest'], s, FWD_REST) for s in 'LR'}
ankle_delta = lambda fr, s: max(-70.0, min(70.0, wdelta(ankle_rel(fr, s) - ANKLE0[s])))
def smooth_cyclic(v, sigma=2.0):
    v = np.array(v, float)
    r = int(3 * sigma) + 1
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    return sum(w * np.roll(v, -j) for j, w in zip(range(-r, r + 1), k))


# contact weights, smoothed over time: a fast take-off lifts a foot several cm in one frame, and the blends
# that hang on them (shoe flat/pointed, IK/FK, floor reach) would snap
CW = {key: {s: smooth_cyclic([contact(fr_, s, a_, b_) for fr_ in frames]) for s in 'LR'}
      for key, (a_, b_) in {'leg': (0.02, 0.10), 'shoe': (0.015, 0.06), 'floor': (0.01, 0.06)}.items()}
# how much the rig's foot bone actually bends against the shin over the move. A wide range is a real ankle
# (pumps, raises); a few degrees is the bone riding along with the shin, which must not spin the shoe.
ANK_RANGE = {}
for s in 'LR':
    _ad = [ankle_delta(fr_, s) for fr_ in frames]
    ANK_RANGE[s] = max(_ad) - min(_ad)
print('ANKLE RANGE', {k: round(v, 1) for k, v in ANK_RANGE.items()})
# A seated heel-toe rock keeps the sole on the floor while the ankle rises a few centimetres.
# The rig angle is too small to see, so that pattern is allowed to tip the shoe.
ROCK = {}
for s in 'LR':
    zs = [float(fr_['foot' + s][0][2]) for fr_ in frames]
    lows = [float(fr_['_low']['foot' + s][2]) for fr_ in frames]
    ROCK[s] = (max(zs) - min(zs) > 0.025) and (max(lows) < 0.025)
# Lying, kneeling, all fours: the spine is far from upright. The standing foot-lock and the leg IK
# rebuild the knee to keep a shoe on a line, which is the wrong gesture (a heel slide must slide).
_spine = [a3(fr_, 'hips', 'neck') for fr_ in frames]
_off = float(np.median([abs(wdelta(a + 90.0)) for a in _spine]))
_hip = float(np.median([fr_['hips'][0][2] for fr_ in frames]))
# also a low pelvis with an upright trunk: long sitting. The feet are out in front, not under the body.
FLOOR = _off > 50 or _hip < 0.40
# but a standing body bent over at the hips (pendulum, windmill, hinge, forward fold): pelvis high, both feet resting,
# the hands never on the floor, the knees straight - the standing foot-lock and floor reach keep its shoes on their lines
_hands_floor = HAS_LOW and min(min(fr_['_low']['handL'][2], fr_['_low']['handR'][2]) for fr_ in frames) < FLOOR_Z + 0.05
_knees_low = min(min(fr_['kneeL'][0][2], fr_['kneeR'][0][2]) for fr_ in frames) < FLOOR_Z + 0.25
_legs_straight = min(float(np.median([np.linalg.norm(jp(fr_, 'foot' + s_) - jp(fr_, 'leg' + s_)) for fr_ in frames])) / LEG3[s_]
                     for s_ in 'LR') > 0.95
_lat_u = np.cross(FWD, [0, 0, 1])
_stance = float(np.median([abs(np.dot(jp(fr_, 'footL') - jp(fr_, 'footR'), _lat_u)) for fr_ in frames]))
_legs_straight = _legs_straight and _stance < 0.3        # a wide stance foreshortens the legs in profile
if FLOOR and _hip > 0.62 and len(_resting) == 2 and not _hands_floor and not _knees_low and _legs_straight:
    FLOOR = False
    print('POSE standing bent over')
print('POSE', 'chao' if FLOOR else 'em pe', 'spine off vertical', round(_off, 1), 'hip', round(_hip, 2))


def shoe_bend(fr, s, shin_w, planted):
    """Extra shoe rotation on top of the drawn ankle, in degrees. Kept small enough that the sneaker stays
    on the shin: the old sole-to-the-ground aim twisted it off whenever the leg was not standing straight.
    The branches below switch on the contact weight (0.45) and on the shin's tilt (35 deg): a hard switch flipped the
    shoe 50-60 deg in one frame (chair-hamstring-stretch: sole flat -> the 3D toes-up stretch as the shin passed 35 deg).
    Across each switch the two answers are blended (contact 0.2..0.7, tilt 28..42 deg); outside it nothing changes."""
    if FLOOR:
        return _shoe_bend(fr, s, shin_w, planted, 35.0)
    def ss(x):
        x = max(0.0, min(1.0, x))
        return x * x * (3.0 - 2.0 * x)
    def mix(a, b, t):
        return a + wdelta(b - a) * t
    a_ = ss((abs(wdelta(shin_w - 90.0)) - 28.0) / 14.0)
    def by_tilt(p):
        return mix(_shoe_bend(fr, s, shin_w, p, 180.0), _shoe_bend(fr, s, shin_w, p, 0.0), a_)
    t_ = ss((planted - 0.2) / 0.5)
    return mix(by_tilt(0.0), by_tilt(1.0), t_)


def _shoe_bend(fr, s, shin_w, planted, tilt_lim):
    ad = ankle_delta(fr, s)
    if FLOOR:
        # the foot follows the leg. Forcing the sole level rewrites the knee every frame.
        # a real ankle (pumps) still bends; a rig offset that never moves stays near the shin.
        lim = 50.0 if ANK_RANGE[s] >= 22 else 20.0
        return max(-lim, min(lim, ad))
    if planted > 0.45 and ROCK[s]:
        span = max(ANK_RANGE[s], 1.0)
        return max(-36.0, min(36.0, ad / span * 32.0))
    if planted > 0.45 and abs(wdelta(shin_w - 90.0)) < tilt_lim:
        rise = max(0.0, fr['foot' + s][0][2] - foot_floor)          # standing heel raise: tip onto the toes
        # from a sole level on the floor whatever the shin's lean (a bend of 0 tilted the shoe with the shin, up to
        # 35 deg at a squat's bottom, and the floor reach then flipped between this branch and the next every pass)
        return math.degrees(math.asin(min(1.0, rise / 0.16))) - wdelta(shin_w - 90.0)
    if ANK_RANGE[s] >= 22:
        return max(-40.0, min(50.0, ad))
    if planted > 0.45:
        # toes point forward when the foot is in front of the hips, back when it is behind (kneeling).
        # knee-to-foot flips sign whenever the shin passes vertical and spun the shoe a quarter turn.
        ground_sole = 0.0 if P(jp(fr, 'foot' + s))[0] >= P(jp(fr, 'hips'))[0] - 0.02 else 180.0
        return max(-50.0, min(50.0, wdelta(ground_sole - (shin_w - 90.0))))
    return max(-35.0, min(40.0, ad))
QA = []
scl_keys = []
anchor = {}
hold = {}
primary = None
SWITCH = [0.0, 0.0, 0.0]     # body offset carried over a support-foot switch, its weight (eases out), last correction
# how many frames ahead each foot stays planted and still in 3D (the support foot is the one that stays)
_pl = {s: [low_z(fr_, 'foot' + s) < 0.012 and (k_ == 0 or abs(P(jp(fr_, 'foot' + s))[0] - P(jp(frames[k_ - 1], 'foot' + s))[0]) < 0.006)
           for k_, fr_ in enumerate(frames)] for s in 'LR'}
STAY = {}
for s_ in 'LR':
    run, out_ = 0, [0] * len(frames)
    for k_ in range(len(frames) - 1, -1, -1):
        run = run + 1 if _pl[s_][k_] else 0
        out_[k_] = run
    STAY[s_] = out_
hand_floor = min(min(fr['handL'][0][2], fr['handR'][0][2]) for fr in frames)
pos_keys = []
# Sit-to-stand: the 3D hips rise in place, so a fixed chair stays inside the standing body.
# Step the whole figure forward as it stands. The step is spread over several frames.
# Only for a real sit-to-stand (the hips go down to seat height) whose 3D hips stay in place: a move that already
# carries the hips forward over the feet (kineti-walker-sit-to-stand-arms-v2: 0.40 m) or a walker mini-squat would
# slide its planted feet by the step.
SHIFTS = [0.0] * len(frames)
if PROPS & {'chairfit', 'walker', 'walkergo'}:
    _zs = [fr_['hips'][0][2] for fr_ in frames]
    _lo, _hi = min(_zs), max(_zs)
    _travel = abs(float(P(jp(frames[int(np.argmax(_zs))], 'hips'))[0] - P(jp(frames[int(np.argmin(_zs))], 'hips'))[0]))
    print('SIT-TO-STAND hips z %.2f..%.2f, forward travel %.2f m' % (_lo, _hi, _travel))
    if _hi - _lo > 0.15 and _lo - FLOOR_Z < 0.65 and _travel < 0.15:
        _raw = []
        for _z in _zs:
            _t = max(0.0, min(1.0, (_z - _lo) / (_hi - _lo)))
            _t = _t * _t * (3.0 - 2.0 * _t)
            _raw.append(_t * 0.28 * K)
        _cap = 8.0
        for _i in range(1, len(_raw)):
            _raw[_i] = min(_raw[_i], _raw[_i - 1] + _cap)
        for _i in range(len(_raw) - 2, -1, -1):
            _raw[_i] = min(_raw[_i], _raw[_i + 1] + _cap)
        SHIFTS = _raw
hand_scl_keys = []
arm_scl_keys = []
shadow_keys = []          # center x, center y, scale x, scale y — same space as the torso, before the final shifts
x0 = None
_sp = np.array(shape_points(L[I['shadow']]['shapes'], np.eye(3)))
if len(_sp) == 0:                                 # the shadow is an ellipse, not a path
    SHADOW_C, SHADOW_SIZE = np.array([72.6, 0.0]), np.array([623.5, 141.3])
else:
    SHADOW_C, SHADOW_SIZE = (_sp.min(0) + _sp.max(0)) / 2, _sp.max(0) - _sp.min(0)
L[I['shadow']]['ks']['a'] = {'a': 0, 'k': [round(float(SHADOW_C[0]), 2), round(float(SHADOW_C[1]), 2), 0]}
# A straight knee is not folded to chase the sole. Measure how far that sole sticks through the floor
# on the straightest frame and lift the body by that once, so the feet stay down without a hop.
if not FLOOR:
    def _ext(fr_, s_):
        return float(np.linalg.norm(P(jp(fr_, 'foot' + s_)) - P(jp(fr_, 'leg' + s_))) / LEG3[s_])
    _fi = max(range(len(frames)), key=lambda i: min(_ext(frames[i], s_) for s_ in 'LR'))
    _fr = frames[_fi]
    if min(_ext(_fr, s_) for s_ in 'LR') > 0.96:
        _D = {nm: a3(_fr, b0, b1) - PHI[nm] for nm, (_, (b0, b1)) in SEG.items()}
        for s_ in 'LR':
            _ch = 'chan %s 2' % s_
            _D['giay %s 2' % s_] = _D[_ch] + shoe_bend(_fr, s_, PHI[_ch] + _D[_ch], float(CW['shoe'][s_][_fi]))
        _rot = {I[nm]: REST[I[nm]][3] + _D[nm] - (_D[par] if par else 0.0) for nm, par in PARENT_SEG.items()}
        _pos = {I['than']: np.array([float(REST[I['than']][0][0]), 0.0])}
        _pos[I['than']][1] += (C_HIP - K * _fr['hips'][0][2]) - pivot(I['mong'], _rot, _pos)[1]
        _pen = max(max(p[1] for p in shape_points(L[I['giay %s 2' % s_]]['shapes'],
                     world(I['giay %s 2' % s_], _rot, _pos))) - (ground - OFF[s_] - K * (foot_sup(_fr, s_) - H_FEET)) for s_ in 'LR')   # on a step: its top
        C_HIP -= _pen
        print('SOLE FIX', round(_pen, 1), 'frame', _fi)
for f, fr in enumerate(frames):
    D = {}
    for nm, (_, (b0, b1)) in SEG.items():
        D[nm] = a3(fr, b0, b1) - PHI[nm]
    # legs by 2-bone IK: the ankle goes where the 3D ankle is relative to the hip, scaled to the drawn leg, so
    # a lifted foot keeps its height (copying the two angles alone would not: the drawn thigh/shin ratio differs)
    SCL.clear()
    rot_t = {I['than']: REST[I['than']][3] + D['than']}
    # On the floor the bone angles are the gesture. IK and the floor reach rebuild the knee so a shoe
    # hits a line, and a heel slide stops sliding.
    if not FLOOR:
        for s in 'LR':
            th, sh = 'dui %s 2' % s, 'chan %s 2' % s
            a1, a2 = ik2(fr, th, sh, LEG_LEN[s], LEG3[s], 'leg' + s, 'knee' + s, 'foot' + s, rot_t)
            # On the floor the bone angles are pinned by the settle below. In the air those angles
            # drop the shoe through the floor, and the settle then folds the knee backwards to park it.
            # Follow the 3D ankle and the 3D knee for the whole time the foot is off the ground.
            air = 1.0 - float(CW['leg'][s][f])
            D[th] += air * wdelta(a1 - PHI[th] - D[th])
            D[sh] += air * wdelta(a2 - PHI[sh] - D[sh])
        for s in 'LR':
            ua, fa = 'canh tay ' + s, 'cang tay ' + s
            a1, a2 = ik2(fr, ua, fa, ARM_LEN[s], ARM3[s], 'arm' + s, 'elbow' + s, 'hand' + s, rot_t)
            D[ua] = a1 - PHI[ua]
            D[fa] = a2 - PHI[fa]
    for s in 'LR':
        ch = 'chan %s 2' % s
        D['giay %s 2' % s] = D[ch] + shoe_bend(fr, s, PHI[ch] + D[ch], float(CW['shoe'][s][f]))
    rot = {}
    for nm, par in PARENT_SEG.items():
        i = I[nm]
        rot[i] = REST[i][3] + D[nm] - (D[par] if par else 0.0)
    # place the torso: x follows the 3D hips, y puts the lowest shoe on the ground (lifted in jumps)
    hx = 0.0 if WALK else P(jp(fr, 'hips'))[0] * K       # walks: in place, like on a treadmill
    if x0 is None:
        x0 = REST[I['than']][0][0] - hx
    pos = {I['than']: np.array([x0 + hx, REST[I['than']][0][1]])}
    rot[I['co']] = REST[I['co']][3] + max(-60.0, min(60.0, wdelta(neck(fr) - NECK0)))
    for s in 'LR':
        fa = 'cang tay ' + s
        fore_w = PHI[fa] + D[fa]
        extra = 0.0 if FLOOR else wdelta(wrist(fr, s) - WRIST0[s])
        rot[I['ban tay ' + s]] = REST[I['ban tay ' + s]][3] + max(-30.0, min(30.0, extra))
    # contacts: only what rests on the floor in 3D (a reaching hand that stops short of the floor must not lift
    # the body); each shoe against its own floor line
    def lowest(nm):
        return max(p[1] for p in shape_points(L[I[nm]]['shapes'], world(I[nm], rot, pos)))
    # the body height follows the 3D hips (as the 3D builder does); the legs on the floor then reach for it below
    pos[I['than']][1] += (C_HIP - K * fr['hips'][0][2]) - pivot(I['mong'], rot, pos)[1]
    def still(s):
        if f == 0:
            return True
        # the ankle still, or (rolling onto the toes) the contact point still. On a flat sole the lowest vertex
        # hops between heel and toe, so the contact point alone is no guide
        if abs(P(jp(fr, 'foot' + s))[0] - P(jp(frames[f - 1], 'foot' + s))[0]) < 0.006:
            return True
        return HAS_LOW and abs(P(np.array(fr['_low']['foot' + s]))[0] - P(np.array(frames[f - 1]['_low']['foot' + s]))[0]) < 0.004
    planted = [] if FLOOR else [s for s in 'LR' if low_z(fr, 'foot' + s) < 0.012 and still(s)]
    # one foot carries the body: it keeps its spot while it stays planted (a toe sliding along the floor in 3D,
    # or a second foot resting lightly, must not drag it); when it lifts, the stillest planted foot takes over
    # from where it stands, so the body never jumps. Not on the floor: a heel slide has to slide.
    if primary not in planted:
        _old_off = SWITCH[2] if primary is not None else None    # the body correction applied last frame
        primary = max(planted, key=lambda s: STAY[s][f]) if planted else None
        if primary is not None:
            anchor.clear()
            # a foot that was held on its spot takes over from that spot (its drawn FK place can be far from it)
            anchor[primary] = hold[primary][0] if primary in hold else pivot(I['giay %s 2' % primary], rot, pos)[0]
            if _old_off is not None:
                # the body was placed by the old support foot and the new one reached its spot by IK; placed by the
                # new foot's FK the body would step 2-3 px in one frame (a blink at 60 fps). Keep the old placement
                # and ease into the new one over 6 frames (the support foot drifts < 0.5 px/frame instead).
                # Only a small offset (<= 6 px); a larger one is a real re-placement and stays as it was.
                _c = _old_off - (anchor[primary] - pivot(I['giay %s 2' % primary], rot, pos)[0])
                if abs(_c) <= 6.0:
                    SWITCH[0], SWITCH[1] = _c, 1.0
    if primary is not None:
        SWITCH[2] = anchor[primary] - pivot(I['giay %s 2' % primary], rot, pos)[0]
        pos[I['than']][0] += SWITCH[2]
    _easing = SWITCH[1] > 0
    if _easing:
        pos[I['than']][0] += SWITCH[0] * SWITCH[1]
        SWITCH[1] -= 1 / 6
    pos[I['than']][0] += SHIFTS[f]
    # the other planted foot keeps its spot too (its leg reaches for it below)
    for s in 'LR':
        if s == primary:                                        # the support foot is anchored by the body itself;
            if not (_easing and s in hold):                     # (while the body eases after a switch its leg keeps
                hold.pop(s, None)                               # reaching its spot) an old held spot would drag it back
        elif _pl[s][f]:                                         # resting and still (strict): keep its spot
            if s not in hold:
                hold[s] = [pivot(I['giay %s 2' % s], rot, pos)[0] - SHIFTS[f], 1.0]   # in unshifted x: a sit-to-stand step carries it
            hold[s][1] = 1.0
        elif s in hold:                                         # let go over 6 frames
            hold[s][1] -= 1 / 6
            if hold[s][1] <= 0:
                hold.pop(s)
    # every planted foot rests on its own floor line: the legs reach for it (like settle() in the 3D builder).
    # twice, because laying the sole on changes which point of the shoe is lowest.
    def leg_ext(s):
        return float(np.linalg.norm(P(jp(fr, 'foot' + s)) - P(jp(fr, 'leg' + s))) / LEG3[s])
    for _settle in range(0 if FLOOR else 2):
        for s in 'LR':
            if low_z(fr, 'foot' + s) > 0.06:                     # airborne: leave the IK pose alone
                continue
            w_ = float(CW['floor'][s][f])                       # eases in/out near the floor
            line_ = ground - OFF[s] - K * (foot_sup(fr, s) - H_FEET)    # its floor line, or the top of the box under it
            if leg_ext(s) > 0.96 and not (_pl[s][f] and line_ - lowest('giay %s 2' % s) > 0.5) \
                    and not (s in hold and abs(hold[s][0] + SHIFTS[f] - pivot(I['giay %s 2' % s], rot, pos)[0]) > 0.5):
                # a straight knee must not fold to chase the sole; a planted straight leg whose sole hangs above its
                # line (the drawn legs differ in length: a lean, a wall push-up) reaches it by the thigh's stretch.
                # A held foot off its spot is still pinned (else it hops back to its FK place once the sole touches)
                continue
            through = lowest('giay %s 2' % s) - line_ > 0.5
            if w_ > 0 or through or s in hold:          # a held foot keeps its spot up to take-off
                w_ = max(w_, 1.0 if through else 0.0)
                th, sh_, sho = 'dui %s 2' % s, 'chan %s 2' % s, 'giay %s 2' % s
                dy = (line_ - lowest(sho)) * w_
                if through and w_ == 1.0 and contact(fr, s, 0.01, 0.06) == 0:
                    dy = min(dy, 0.0)                             # in the air: only push it up out of the floor
                if abs(dy) > 0.5 or s in hold:
                    H = pivot(I[th], rot, pos)
                    A_ = pivot(I[sho], rot, pos) + np.array([0.0, dy])
                    if s in hold:
                        A_[0] += (hold[s][0] + SHIFTS[f] - A_[0]) * hold[s][1]   # x pinned in full while it rests (y eases in with w_)
                        R_ = 1.15 * 0.995 * sum(LEG_LEN[s])      # out of reach: the floor wins, the spot gives way
                        if np.linalg.norm(A_ - H) > R_ and abs(A_[1] - H[1]) < R_:
                            A_[0] = H[0] + np.sign(A_[0] - H[0]) * math.sqrt(R_ ** 2 - (A_[1] - H[1]) ** 2)
                    # the 3D knee, not the drawing: the drawn knee walks off to the wrong side and the next
                    # pass follows it, so a flexion ends up kicked out behind the body
                    l1_, l2_ = LEG_LEN[s]
                    sc_ = (l1_ + l2_) / LEG3[s]
                    Kn = H + (P(jp(fr, 'knee' + s)) - P(jp(fr, 'leg' + s))) * sc_
                    need = np.linalg.norm(A_ - H) / (0.995 * (l1_ + l2_))
                    SCL[I[th]] = float(np.clip(need, 1.0, 1.15))
                    a1, a2 = solve2(H, A_, l1_ * SCL[I[th]], l2_ * SCL[I[th]], Kn)
                    D[th], D[sh_] = a1 - PHI[th], a2 - PHI[sh_]
                    D[sho] = D[sh_] + shoe_bend(fr, s, PHI[sh_] + D[sh_], float(CW['shoe'][s][f]))
                    for nm in (th, sh_, sho):
                        par = PARENT_SEG[nm]
                        rot[I[nm]] = REST[I[nm]][3] + D[nm] - (D[par] if par else 0.0)
    mong = pivot(I['mong'], rot, pos)
    lows = [lowest('giay %s 2' % s) for s in 'LR' if low_z(fr, 'foot' + s) < 0.04]
    floor_y = min(lows) if lows else ground
    # shadow: a flat ellipse on the floor, spanning whatever is actually supporting the body
    xs = []
    for nm in ('giay R 2', 'giay L 2', 'ban tay R', 'ban tay L', 'chan R 2', 'chan L 2', 'dui R 2', 'dui L 2'):
        pts = np.array(shape_points(L[I[nm]]['shapes'], world(I[nm], rot, pos)))
        if len(pts) == 0:
            continue
        on = pts[np.abs(pts[:, 1] - floor_y) < 80]
        if len(on):
            xs += [float(on[:, 0].min()), float(on[:, 0].max())]
    if xs:
        pad = 28.0
        x0s, x1s = min(xs) - pad, max(xs) + pad
        vis_h = 52.0
        sy = vis_h / SHADOW_SIZE[1] * 100             # a low ellipse on the floor, not the tall jump blob
        shadow_keys.append([(x0s + x1s) / 2, floor_y + vis_h * 0.32, (x1s - x0s) / SHADOW_SIZE[0] * 100, sy])
    else:
        shadow_keys.append([float(mong[0]), float(floor_y), 18.0, 16.0])
    # a planted foot stays put: slide the body so planted shoes keep their spot (no skating)
    for nm in PARENT_SEG:
        keys[nm].append(rot[I[nm]])
    keys['co'].append(rot[I['co']])
    scl_keys.append({s: SCL.get(I['dui %s 2' % s], 1.0) for s in 'LR'})
    hand_scl_keys.append({s: SCL.get(I['ban tay ' + s], 1.0) for s in 'LR'})
    arm_scl_keys.append({nm: SCL.get(I[nm], 1.0) for nm in ('canh tay R', 'canh tay L')})
    for s in 'LR':
        keys['ban tay ' + s].append(rot[I['ban tay ' + s]])
    pos_keys.append(pos[I['than']].tolist())
    sh = {}
    for s in 'LR':
        pts = np.array(shape_points(L[I['giay %s 2' % s]]['shapes'], world(I['giay %s 2' % s], rot, pos)))
        sh[s] = (float(pts[:, 1].max()), float(pts[pts[:, 1].argmax(), 0]), pivot(I['giay %s 2' % s], rot, pos))
    if "--debugskate" in sys.argv:
        print("SK", f, primary, sorted(hold), {s_: (bool(_pl[s_][f]), round(float(CW["floor"][s_][f]), 2), round(float(sh[s_][2][0]), 1), round(float(P(jp(fr, "foot" + s_))[0]) * 1000, 1), round(low_z(fr, "foot" + s_), 3)) for s_ in "LR"})
    QA.append(dict(hip=pivot(I['mong'], rot, pos), hz=fr['hips'][0][2], sh=sh,
                   fz={s: low_z(fr, 'foot' + s) for s in 'LR'}, fs={s: foot_sup(fr, s) - H_FEET for s in 'LR'}, fx={s: P(jp(fr, 'foot' + s))[0] for s in 'LR'},
                   rot=dict(rot),
                   knee={s: (float(pivot(I['chan %s 2' % s], rot, pos)[1]) + KNEE_R[s],
                             float(fr['knee' + s][0][2] - sup_h(fr['knee' + s][0]) < 0.075), sup_h(fr['knee' + s][0]) - FLOOR_Z)
                         for s in 'LR'},
                   seat=(lowest('mong'), float(fr['hips'][0][2] - FLOOR_Z < 0.16))))

floor_dy = 0.0
if FLOOR and QA:
    # one vertical shift for the whole move, so the feet that are on the floor in 3D sit on the line.
    # The same shift every frame: the gesture, including a hip that rises, stays as it was.
    # what touches a support in 3D: shoes, knees (kneeling), else the seat (sitting or lying on the floor)
    FL = ground + K * H_FEET                    # the floor line (FLOOR_Z) before the shift
    gaps = []
    for q in QA:
        g_ = [FL - OFF[s] - K * (q['fs'][s] + H_FEET) - q['sh'][s][0] for s in 'LR' if q['fz'][s] < 0.03]
        g_ += [FL - OFF[s] - K * q['knee'][s][2] - q['knee'][s][0] for s in 'LR' if q['knee'][s][1]]
        if not g_ and q['seat'][1]:
            g_ = [FL - q['seat'][0]]
        gaps += g_
    if gaps:
        floor_dy = float(np.median(gaps))
        print('FLOOR SHIFT', round(floor_dy, 1), 'from', len(gaps), 'contacts')
        for p in pos_keys:
            p[1] += floor_dy
        for s in shadow_keys:
            s[1] += floor_dy
        for q in QA:
            q['hip'] = q['hip'] + np.array([0.0, floor_dy])
            q['sh'] = {s: (v[0] + floor_dy, v[1], v[2] + np.array([0.0, floor_dy])) for s, v in q['sh'].items()}
            q['knee'] = {s: (v[0] + floor_dy, v[1], v[2]) for s, v in q['knee'].items()}
FLOOR_LINE = ground + K * H_FEET               # screen y of the 3D floor (near side), in the body's final coordinates


SUPY = {}       # near-line y of a support that only hands rest on, set where the drawn arms reach it (below)


def sup_line(h, s='R'):
    """Screen y of a horizontal support h metres above the floor, on the near (R) or far (L) side: the far side
    sits OFF px higher, like the far foot (the drawing is seen from a little above)."""
    base = SUPY.get(round(float(h), 3), FLOOR_LINE - K * h)
    return base - (OFF['L'] if s == 'L' else 0.0)


# ---------- planted hands: a hand that rests on a support in 3D (floor, box, chair seat, backrest, table, wall)
# lies flat on that support in the drawing: palm down (or against the wall), fingers forward, wrist bent; the arm
# reaches for it by IK, the way the legs reach for the floor.
def frame_pose(f):
    rot_ = dict(QA[f]['rot'])
    pos_ = {I['than']: np.array(pos_keys[f][:2], float)}
    SCL.clear()
    for s in 'LR':
        if scl_keys[f][s] != 1.0:
            SCL[I['dui %s 2' % s]] = scl_keys[f][s]
        if arm_scl_keys[f]['canh tay ' + s] != 1.0:
            SCL[I['canh tay ' + s]] = arm_scl_keys[f]['canh tay ' + s]
    return rot_, pos_


def px_of(f, w3, rot_, pos_, s=None):
    """A 3D point in the drawing's pixels, relative to the drawn near hip joint, or to the drawn shoulder of
    side s (for what the hands touch), 1 m = K px."""
    if s:
        return pivot(I['canh tay ' + s], rot_, pos_) + (P(np.array(w3, float)) - P(jp(frames[f], 'arm' + s))) * K
    return pivot(I['dui R 2'], rot_, pos_) + (P(np.array(w3, float)) - P(jp(frames[f], 'legR'))) * K


def palm3(fr, s):
    return np.array(fr['_palm'][s] if '_palm' in fr else fr['_low']['hand' + s], float)


def tip3(fr, s):
    return np.array(fr['_tip'][s] if '_tip' in fr else fr['hand' + s][1], float)


def smoothstep(x):
    x = float(np.clip(x, 0.0, 1.0))
    return x * x * (3 - 2 * x)


PLANT = {s: np.zeros(len(frames)) for s in 'LR'}       # weight of the planted pose
PDIR = {s: np.ones(len(frames)) for s in 'LR'}          # fingers forward (+1) or back (-1) along the support
PKIND = {s: [None] * len(frames) for s in 'LR'}         # ('h', height) horizontal support or ('w', x) the wall
VIRT = {}                                                # props drawn under the hands: side -> top height
if PROPS & {'support', 'side'} or ('table' in PROPS and not BOXES):
    sides = 'LR'
    if 'side' in PROPS and 'support' not in PROPS:      # the hand furthest out to the side holds the backrest
        hxm = np.mean([fr['hips'][0][0] for fr in frames])
        sides = max('LR', key=lambda s_: np.mean([abs(fr['_palm'][s_][0] - hxm) if '_palm' in fr else 0 for fr in frames]))
    if 'table' in PROPS and not BOXES:                  # the hand(s) that stay put
        trav = {s_: max(np.linalg.norm(palm3(fr, s_) - palm3(frames[0], s_)) for fr in frames) for s_ in 'LR'}
        sides = [s_ for s_ in 'LR' if trav[s_] < 0.05] or [min(trav, key=trav.get)]
        sides = [s_ for s_ in 'LR' if 'table' + s_ in PROPS] or sides
    for s_ in sides:
        VIRT[s_] = min(palm3(fr, s_)[2] for fr in frames) - 0.035 - FLOOR_Z
WALL_A = None
if 'wall' in PROPS:
    WALL_A = max(max(float(np.dot(palm3(fr, s_), FWD)) for s_ in 'LR') for fr in frames) + 0.035
_wp = [p_ for p_ in PROPS if p_.startswith('wallpress-h') and p_.endswith('-F')]
if _wp and WALL_A is None:
    # a ball pressed on the wall in front: the hand rests on the ball's near side, a plane like a wall; planted on it,
    # the drawn (shorter) arm reaches it by IK and the ball, carried by the hand, stays on the wall
    _s = _wp[0].split('-')[1][1]
    WALL_A = max(float(np.dot(palm3(fr, _s), FWD)) for fr in frames) + 0.035
GRIPPED = set()      # fists that rest on a handle the move was built on (a walker): planted, but kept closed
for s in 'LR':
    if FIST[s] and grips(s):
        if not (BOXES and PROPS & {'walker'}):
            continue
        GRIPPED.add(s)
    w_raw, kind = [], []
    for f, fr in enumerate(frames):
        lo, pm = np.array(fr['_low']['hand' + s], float), palm3(fr, s)
        sh_z = fr['arm' + s][0][2]
        cand = []
        if s in GRIPPED:
            hs = sup_h(pm + np.array([0, 0, 0.05]))
            cand = [(abs(pm[2] - hs) - 0.02, ('g', hs - FLOOR_Z))] if hs > FLOOR_Z else []
            gap, k_ = min(cand, key=lambda c: c[0]) if cand else (1.0, None)
            w_raw.append(smoothstep((0.08 - gap) / 0.05))
            kind.append(k_)
            continue
        if WALL_A is not None:
            cand.append((WALL_A - 0.035 - float(np.dot(pm, FWD)), ('w', WALL_A)))
        if s in VIRT:                                     # held on the backrest / table the whole time
            cand.append((0.0, ('h', VIRT[s])))
        hs = sup_h(lo)
        if sh_z - lo[2] > 0.12:
            cand.append((lo[2] - hs, ('h', hs - FLOOR_Z)))
        gap, k_ = min(cand, key=lambda c: c[0]) if cand else (1.0, None)
        if k_ is not None and k_[0] == 'h' and sh_z - lo[2] > 0.3:
            # a hand under a raised shoulder (all fours, a plank) carries weight: the rig leaves some 4-6 cm above
            # the floor, which drawn reads as a hand floating under the body; up to 9 cm it is planted
            w_raw.append(smoothstep((0.13 - gap) / 0.05))
        else:
            w_raw.append(smoothstep((0.06 - gap) / 0.04))
        kind.append(k_)
    w_s = np.clip(smooth_cyclic(w_raw, 1.5), 0, 1)
    w_s[w_s < 0.02] = 0.0
    PLANT[s] = w_s
    last = None
    for f in range(len(frames)):                         # the support a hand is on holds while it eases off
        if kind[f] is not None and w_raw[f] > 0.3:
            last = kind[f]
        PKIND[s][f] = kind[f] if w_raw[f] > 0.3 or last is None else last
upright_f = [abs(wdelta(a3(fr, 'hips', 'neck') + 90.0)) < 35 for fr in frames]
# A raised support that only the hands touch (a walker's handles, a table, a chair under the hands, a backrest)
# goes where the drawn arms reach it: the puppet's arms are shorter than the rig's, so its 3D height would leave
# the hands hanging above it or the arms stretched. Supports the feet stand on keep their measured height.
ARM_SC = {s: (ARM_LEN[s][0] + ARM_LEN[s][1]) / ARM3[s] for s in 'LR'}
FOOT_HS = {round(float(q['fs'][s_] + H_FEET), 3) for q in QA for s_ in 'LR' if q['fz'][s_] < 0.012}


def natural_palm(f, fr, s, rot_, pos_):
    """Where the drawn arm puts the palm: the 3D wrist relative to the shoulder at the drawn arm's scale, then the
    drawn hand's own length forward (a hand flat on a support, fingers forward)."""
    w = pivot(I['canh tay ' + s], rot_, pos_) + (P(jp(fr, 'hand' + s)) - P(jp(fr, 'arm' + s))) * ARM_SC[s]
    if s in GRIPPED:
        fc = FIST_C[s] - HG[s]['A']
        return w + np.array([float(fc @ HG[s]['ul']), -float(fc @ HG[s]['tl'])])
    return w + np.array([0.4 * HG[s]['Lh'], 0.0])


_sy = {}
for f, fr in enumerate(frames):
    for s in 'LR':
        k_ = PKIND[s][f]
        if PLANT[s][f] < 0.5 or k_ is None or k_[0] not in 'hg' or k_[1] < 0.03 or round(float(k_[1]), 3) in FOOT_HS:
            continue
        rot_, pos_ = frame_pose(f)
        pm = natural_palm(f, fr, s, rot_, pos_)
        if k_[0] == 'g':
            fpts = np.array(shape_points(FIST_SHAPES[s], np.eye(3)))
            y = pm[1] + float(max(-(fpts - FIST_C[s]) @ HG[s]['tl']))
        else:
            y = pm[1] + 0.5 * HG[s]['hw']
        _sy.setdefault(round(float(k_[1]), 3), []).append(y + (OFF['L'] if s == 'L' else 0.0))
SCL.clear()
for h_, ys in _sy.items():
    SUPY[h_] = float(np.median(ys))
    print('HAND SUPPORT', h_, 'at', round(SUPY[h_], 1), 'px (3D height gives', round(FLOOR_LINE - K * h_, 1), ')')
PIN = {}                                                 # a planted palm keeps its spot (no skating), like a foot
LAST_UA = {}                                             # the upper arm's last planted angle: keeps the elbow side
for f, fr in enumerate(frames):
    if not any(PLANT[s][f] > 0 for s in 'LR'):
        continue
    rot_, pos_ = frame_pose(f)
    face = 1.0 if P(jp(fr, 'neck'))[0] >= P(jp(fr, 'hips'))[0] else -1.0
    for s in 'LR':
        w_ = float(PLANT[s][f])
        if w_ <= 0 or PKIND[s][f] is None:
            continue
        g = HG[s]
        ua, fa, hd = 'canh tay ' + s, 'cang tay ' + s, 'ban tay ' + s
        H = pivot(I[ua], rot_, pos_)
        l1, l2 = ARM_LEN[s]
        kind_, val = PKIND[s][f]
        pm = natural_palm(f, fr, s, rot_, pos_) if round(float(val), 3) in SUPY else px_of(f, palm3(fr, s), rot_, pos_, s)
        if kind_ in 'hg' and w_ > 0.5:
            if s not in PIN or PIN[s][1] != PKIND[s][f]:
                PIN[s] = (float(pm[0]), PKIND[s][f])
            pm = np.array([PIN[s][0], pm[1]])
        elif w_ <= 0.5:
            PIN.pop(s, None)
        if kind_ == 'g':                                  # a fist on a handle: the fist sits on its top
            dirn, want = 1.0, 0.0
            fc = FIST_C[s] - g['A']
            sv, wv = float(fc @ g['ul']), float(fc @ g['tl'])
            fpts = np.array(shape_points(FIST_SHAPES[s], np.eye(3)))
            hf = float(max(-(fpts - FIST_C[s]) @ g['tl']))
            T = np.array([pm[0] - sv, sup_line(val, s) - hf + wv])
        elif kind_ == 'w':                                # against the wall: fingers up, palm facing it
            wall_x = float(px_of(f, jp(fr, 'arm' + s) + FWD * (val - float(np.dot(jp(fr, 'arm' + s), FWD))), rot_, pos_, s)[0])
            dirn, want = 1.0, -90.0
            T = np.array([wall_x - g['floor_drop'][1], pm[1] + 0.4 * g['Lh']])
        else:
            tv = P(tip3(fr, s)) - P(palm3(fr, s))
            if upright_f[f]:
                dirn = float(np.sign(tv[0])) if abs(tv[0]) > 0.03 else 1.0
            else:
                dirn = face
            want = 0.0 if dirn > 0 else 180.0
            T = np.array([pm[0] - dirn * 0.4 * g['Lh'], sup_line(val, s) - g['floor_drop'][int(dirn)]])
        R = 0.995 * (l1 + l2)
        dv_ = T - H
        stretch = 1.0
        if np.linalg.norm(dv_) > R:
            if kind_ == 'w' and abs(dv_[0]) < R:           # slide along the wall
                T[1] = H[1] + np.sign(dv_[1]) * math.sqrt(R * R - dv_[0] ** 2)
            elif kind_ != 'w' and abs(dv_[1]) < R:          # slide along the support
                T[0] = H[0] + np.sign(dv_[0]) * math.sqrt(R * R - dv_[1] ** 2)
            else:
                stretch = float(min(1.12, np.linalg.norm(dv_) / R))
        guide = pivot(I[fa], rot_, pos_)
        if s in LAST_UA and LAST_UA[s][0] == f - 1:        # continuous: the elbow stays on the side it was
            guide = H + l1 * stretch * np.array([math.cos(math.radians(LAST_UA[s][1])), math.sin(math.radians(LAST_UA[s][1]))])
        a1, a2 = solve2(H, T, l1 * stretch, l2 * stretch, guide)
        LAST_UA[s] = (f, a1)
        D_ua, D_fa = a1 - PHI[ua], a2 - PHI[fa]
        D_than = rot_[I['than']] - REST[I['than']][3]
        new_ua = REST[I[ua]][3] + D_ua - D_than
        new_fa = REST[I[fa]][3] + D_fa - D_ua
        fore_w = PHI[fa] + D_fa
        new_hd = REST[I[hd]][3] + wdelta(want - fore_w)
        for idx, nv in ((I[ua], new_ua), (I[fa], new_fa), (I[hd], new_hd)):
            ov = QA[f]['rot'][idx]
            QA[f]['rot'][idx] = ov + w_ * wdelta(nv - ov)
        if stretch > 1.0:
            arm_scl_keys[f][ua] = 1.0 + w_ * (stretch - 1.0)
        PDIR[s][f] = dirn
        if '--debughands' in sys.argv and f % 10 == 0:
            print('HANDDBG', f, s, kind_, 'H', np.round(H, 1), 'T', np.round(T, 1), 'w', round(w_, 2), 'supl', round(sup_line(val, s), 1))
        for nm in (ua, fa, hd):
            keys[nm][f] = QA[f]['rot'][I[nm]]
SCL.clear()
for s in 'LR':
    if PLANT[s].max() > 0:
        print('PLANT', s, 'frames', int((PLANT[s] > 0.5).sum()), 'kinds', sorted({str(k) for k in PKIND[s] if k}))
# the hand drawing: open (or the fist) in the air, flat while planted; mirrored when the fingers point back
def hold_track(vals):
    ks, prev = [], None
    for t, v in enumerate(vals):
        if v != prev:
            ks.append({'t': t, 's': v if isinstance(v, list) else [v], 'h': 1})
            prev = v
    return {'a': 0, 'k': vals[0]} if len(ks) == 1 else {'a': 1, 'k': ks}


for s in 'LR':
    on = [bool(PLANT[s][f] > 0.5) and s not in GRIPPED for f in range(len(frames))]
    grs = L[I['ban tay ' + s]]['shapes']
    trs = {gr_['nm']: gr_['it'][-1] for gr_ in grs}
    for nm_, tr_ in trs.items():
        if nm_ == 'mao apoiada':
            tr_['o'] = hold_track([100 if o_ else 0 for o_ in on])
            g = HG[s]
            c_ = g['A'] + g['mid'] * g['tl']
            th = math.degrees(math.atan2(g['ul'][1], g['ul'][0]))
            mir = [bool(o_ and PDIR[s][f] < 0) for f, o_ in enumerate(on)]
            if any(mir):
                tr_['p'] = {'a': 0, 'k': [float(c_[0]), float(c_[1])]}
                tr_['a'] = {'a': 0, 'k': [float(c_[0]), float(c_[1])]}
                tr_['r'] = hold_track([round(2 * th, 3) if m_ else 0.0 for m_ in mir])
                tr_['s'] = hold_track([[100, -100] if m_ else [100, 100] for m_ in mir])
        else:
            tr_['o'] = hold_track([0 if o_ else 100 for o_ in on])

# ---------- QA: what a viewer would notice
def qa():
    out = {}
    hip_h = np.array([ground - q['hip'][1] for q in QA])
    hz = np.array([q['hz'] for q in QA]) * K
    out['bob_px'] = round(float(np.ptp(hip_h - hz)), 1)         # the body rising/sinking where the 3D hips do not
    fl, sk, sk_at = 0.0, 0.0, ''
    for s in 'LR':
        on = [i for i, q in enumerate(QA) if q['fz'][s] < 0.012]
        fl = max([fl] + [abs(QA[i]['sh'][s][0] + OFF[s] - ground + K * QA[i]['fs'][s]) for i in on])   # planted 3D foot: shoe above/below ground
        for a_, b_ in zip(on, on[1:]):
            if b_ == a_ + 1 and abs(QA[b_]['fx'][s] - QA[a_]['fx'][s]) < 0.002:  # planted and still in 3D
                d_ = abs(QA[b_]['sh'][s][2][0] - QA[a_]['sh'][s][2][0])
                if d_ > sk:
                    sk, sk_at = d_, f'{s}@{b_}'
    out['float_px'], out['skate_px_per_frame'], out['skate_at'] = round(fl, 1), round(sk, 2), sk_at
    jump, who = 0.0, ''
    for f_, (a_, b_) in enumerate(zip(QA, QA[1:])):
        for k in a_['rot']:
            d_ = abs(wdelta(b_['rot'][k] - a_['rot'][k]))
            if d_ > jump:
                jump, who = d_, f"{L[k]['nm']}@{f_ + 1}"
    out['max_turn_deg_per_frame'] = round(jump, 1)
    out['max_turn_at'] = who
    hy = np.array([q['hip'][1] for q in QA]); hz3 = np.array([q['hz'] for q in QA]) * K
    out['max_body_step_px'] = round(float(np.abs(np.diff(hy) + np.diff(hz3)).max()), 1) if len(QA) > 1 else 0
    return out


print('QA', json.dumps(qa()))
if '--debugfeet' in sys.argv:
    for i_, q_ in enumerate(QA):
        print('FEET', i_, {s_: (round(q_['fz'][s_], 3), round(q_['fs'][s_], 3), round(q_['sh'][s_][0] + OFF[s_] - ground + K * q_['fs'][s_], 1)) for s_ in 'LR'})

# close the loop: spread whatever x drift the anchoring left over the cycle
drift = pos_keys[-1][0] - pos_keys[0][0] - (0.0 if WALK else (P(jp(frames[-1], 'hips'))[0] - P(jp(frames[0], 'hips'))[0]) * K)
for k_, p_ in enumerate(pos_keys):
    p_[0] -= drift * k_ / max(len(pos_keys) - 1, 1)
for k_, s_ in enumerate(shadow_keys):             # the shadow moves with the body it lies under
    s_[0] -= drift * k_ / max(len(shadow_keys) - 1, 1)

# centre the motion horizontally in the comp
xs = [p[0] for p in pos_keys]
center_dx = REST[I['than']][0][0] - (max(xs) + min(xs)) / 2
for p in pos_keys:
    p[0] += center_dx
for s in shadow_keys:
    s[0] += center_dx

N = len(frames)


def smooth_ang(vals, sigma=1.3):
    """Cyclic smoothing of an angle track, so a one-frame twist of the shoe or the hand does not pop."""
    v = np.unwrap(np.deg2rad(np.array(vals, float)))
    r = int(3 * sigma) + 1
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    return list(np.rad2deg(sum(w * np.roll(v, -j) for j, w in zip(range(-r, r + 1), k))))


for nm in ('giay R 2', 'giay L 2', 'ban tay R', 'ban tay L'):
    keys[nm] = smooth_ang(keys[nm])


def anim(vals, dims):
    ks = []
    for t, v in enumerate(vals):
        k = {'t': t, 's': (v if dims > 1 else [v]), 'i': {'x': 0.5, 'y': 0.5}, 'o': {'x': 0.5, 'y': 0.5}}
        if dims > 1:
            k['ti'], k['to'] = [0] * dims, [0] * dims
        ks.append(k)
    return {'a': 1, 'k': ks}


# unwrap every angle track: lottie interpolates between keys (and the player renders in-betweens), so a step
# from +179 to -179 would spin the piece a full turn inside one frame - the "blink"
for nm in keys:
    keys[nm] = list(np.rad2deg(np.unwrap(np.deg2rad(np.array(keys[nm], float)))))
# one-frame reversals (a key that jumps out and straight back, from a contact switching on for a single frame)
# flash in the rendered in-betweens; replace just those keys by their neighbours' mean. Not a smoothing: every
# other key, and so every contact, stays as solved.
_despiked = 0
for nm in keys:
    v = keys[nm]
    for i_ in range(1, len(v) - 1):
        a_, b_ = v[i_] - v[i_ - 1], v[i_ + 1] - v[i_]
        if a_ * b_ < 0 and min(abs(a_), abs(b_)) > 1.0:
            v[i_] = (v[i_ - 1] + v[i_ + 1]) / 2
            _despiked += 1
# smaller one-frame twitches (a 0.5 deg out-and-back of a still arm moves the hand 3 px for one frame, a flicker in the
# 60 fps video): a key that steps out and back while the keys around it barely move is replaced the same way; at a
# real turning point the motion slows into it, so the steps around it are larger than the steps at it
for nm in keys:
    v = keys[nm]
    for i_ in range(2, len(v) - 2):
        a_, b_ = v[i_] - v[i_ - 1], v[i_ + 1] - v[i_]
        if a_ * b_ < 0 and min(abs(a_), abs(b_)) > 0.2:
            outer = max(abs(v[i_ - 1] - v[i_ - 2]), abs(v[i_ + 2] - v[i_ + 1]))
            if outer < 0.5 * min(abs(a_), abs(b_)):
                v[i_] = (v[i_ - 1] + v[i_ + 1]) / 2
                _despiked += 1
if _despiked:
    print('DESPIKE', _despiked, 'keys')
# a free arm whose upper arm or forearm points straight out sideways has no direction in profile: its projected angle
# snaps by up to 180 deg in one frame (an arm swung out and over, a hand brought to the shoulder through abduction).
# Such a snap (> 45 deg in a frame, the hand not planted) is spread over the frames around it as a quick swing of both
# arm pieces; the keys outside that window, and every planted hand, stay as solved.
_eased = 0
for s in 'LR':
    ua, fa = 'canh tay ' + s, 'cang tay ' + s
    n_ = len(keys[ua])
    snaps = [i_ for i_ in range(1, n_) if max(abs(keys[ua][i_] - keys[ua][i_ - 1]), abs(keys[fa][i_] - keys[fa][i_ - 1])) > 45
             and PLANT[s][max(0, i_ - 6):i_ + 6].max() < 0.05]
    for i_ in snaps:
        w = 5
        a_, b_ = max(0, i_ - w - 1), min(n_ - 1, i_ + w)
        if b_ - a_ < 2:
            continue
        for nm in (ua, fa):
            va, vb = keys[nm][a_], keys[nm][b_]
            for k_ in range(a_ + 1, b_):
                u = (k_ - a_) / (b_ - a_)
                keys[nm][k_] = va + (vb - va) * u * u * (3 - 2 * u)
        _eased += 1
if _eased:
    print('EASED arm snaps', _eased)
_flips =[(nm, i_) for nm in keys for i_ in range(1, len(keys[nm])) if abs(keys[nm][i_] - keys[nm][i_ - 1]) > 45]
print('FLIPS', len(_flips), _flips[:6])               # a piece turning > 45 deg in one frame: a visible snap
for nm, vals in keys.items():
    L[I[nm]]['ks']['r'] = anim([round(v, 3) for v in vals], 1)
for s in 'LR':
    vals = [k_[s] for k_ in scl_keys]
    if max(vals) > 1.001:
        s0 = REST[I['dui %s 2' % s]][2] * 100
        L[I['dui %s 2' % s]]['ks']['s'] = anim([[round(float(s0[0] * v), 3), round(float(s0[1] * v), 3), 100] for v in vals], 3)
        print('STRETCH', s, round(max(vals), 3))
# the forearm's twin is the matte of the upper arm's shadow: it turns with the forearm
L[I['cang tay R 2']]['ks']['r'] = anim([round(v, 3) for v in keys['cang tay R']], 1)
for s in 'LR':
    vals = [k_[s] for k_ in hand_scl_keys]
    if max(vals) > 1.02 or min(vals) < 0.98:
        s0 = REST[I['ban tay ' + s]][2] * 100
        L[I['ban tay ' + s]]['ks']['s'] = anim([[round(float(s0[0] * v), 2), round(float(s0[1] * v), 2), 100] for v in vals], 3)
for nm in ('canh tay R', 'canh tay L'):
    vals = [k_[nm] for k_ in arm_scl_keys]
    if max(vals) > 1.02:
        s0 = REST[I[nm]][2] * 100
        L[I[nm]]['ks']['s'] = anim([[round(float(s0[0] * v), 2), round(float(s0[1] * v), 2), 100] for v in vals], 3)
for f_, sk_ in enumerate(shadow_keys):          # the shadow lies on the 3D floor (under a disc, a box...)
    sk_[1] = FLOOR_LINE + 52.0 * 0.32
    if not FLOOR and not BOXES and f_ < len(frames):
        # standing on the far foot alone: that sole sits OFF px higher (the art's perspective), and a shadow left on
        # the near line read as the figure floating; it moves up to the far line while the near foot is lifted
        sk_[1] -= OFF['L'] * float(CW['floor']['L'][f_]) * (1.0 - float(CW['floor']['R'][f_]))
if shadow_keys:
    L[I['shadow']]['ks']['p'] = anim([[round(x, 2), round(y, 2), 0] for x, y, _, _ in shadow_keys], 3)
    L[I['shadow']]['ks']['s'] = anim([[round(sx, 2), round(sy, 2), 100] for _, _, sx, sy in shadow_keys], 3)
p_old = L[I['than']]['ks']['p']['k']
L[I['than']]['ks']['p'] = anim([[round(x, 2), round(y, 2), 0] for x, y in pos_keys], 3)

# ---------- equipment, in the same sagittal pixels as the body
# Every prop is placed from the DRAWN body (hands, feet, knees, pelvis on the final keys), so held things stay in
# the hand and supports stay under what rests on them; 3D positions only say where along the floor a fixed prop
# stands. Flat style: muted greys/blues; a support's top is a lighter band from the far line to the near line
# (the drawing is seen from a little above, like the far foot that sits OFF px higher).
PROP_PTS = []
NEAR_TOP = 'giay R 2'      # layers: inserting before this sits above the near arm (held in front of the body)


def pose_at(f):
    """Final rotations (smoothed, unwrapped keys) and pelvis position of frame f; sets SCL for the stretched limbs."""
    rot_ = {I[nm]: keys[nm][f] for nm in keys}
    SCL.clear()
    for s in 'LR':
        if scl_keys[f][s] != 1.0:
            SCL[I['dui %s 2' % s]] = scl_keys[f][s]
        if arm_scl_keys[f]['canh tay ' + s] != 1.0:
            SCL[I['canh tay ' + s]] = arm_scl_keys[f]['canh tay ' + s]
    return rot_, {I['than']: np.array(pos_keys[f][:2], float)}


POSES = [pose_at(f) for f in range(N)]
SCL_F = []
for f in range(N):
    pose_at(f)
    SCL_F.append(dict(SCL))
SCL.clear()


def W_(f, nm):
    """World matrix of a drawn layer at frame f."""
    SCL.clear()
    SCL.update(SCL_F[f])
    m = world(I[nm], *POSES[f])
    SCL.clear()
    return m


def drawn(f, nm):
    """Pivot of a drawn part at frame f."""
    return (W_(f, nm) @ np.array([*REST[I[nm]][1], 1]))[:2]


def lay_pt(f, nm, p):
    return (W_(f, nm) @ np.array([p[0], p[1], 1]))[:2]


def hip_px(f):
    return drawn(f, 'mong')


def to_px(f, w3):
    """A 3D point in the puppet's pixels, relative to the drawn near hip joint (1 m = K px)."""
    return drawn(f, 'dui R 2') + (P(np.array(w3, float)) - P(jp(frames[f], 'legR'))) * K


def along_pt(f, along, z):
    """`along` metres in front of the hips (negative is behind), at absolute height z."""
    w = np.array(jp(frames[f], 'hips'), float) + FWD * along
    w[2] = z
    return to_px(f, w)




def grip(f, s):
    """Where the drawn hand holds something: the fist's centre, or the middle of the open palm."""
    g = HG[s]
    if FIST[s]:
        return lay_pt(f, 'ban tay ' + s, FIST_C[s])
    return lay_pt(f, 'ban tay ' + s, g['A'] + 0.42 * g['Lh'] * g['ul'] + g['mid'] * g['tl'])


def hand_axes(f, s):
    """World unit vectors of the drawn hand at frame f: u (wrist -> fingers) and t (thumb side)."""
    g = HG[s]
    M = W_(f, 'ban tay ' + s)[:2, :2]
    u = M @ g['ul']
    t = M @ g['tl']
    return u / np.linalg.norm(u), t / np.linalg.norm(t)


def foot_pt(f, s, where='ball'):
    """A point of the drawn foot: the ankle pivot, or the ball of the foot (the sole, 3/4 towards the toe)."""
    an = drawn(f, 'giay %s 2' % s)
    if where == 'ankle':
        return an
    pts = np.array(shape_points(L[I['giay %s 2' % s]]['shapes'], W_(f, 'giay %s 2' % s)))
    toe = pts[np.argmax((pts - an) @ np.array([math.cos(math.radians(keys['giay %s 2' % s][f] - REST[I['giay %s 2' % s]][3] + SOLE[s])),
                                               math.sin(math.radians(keys['giay %s 2' % s][f] - REST[I['giay %s 2' % s]][3] + SOLE[s]))]))]
    return an + (toe - an) * 0.7


def knee_pt(f, s):
    return drawn(f, 'chan %s 2' % s)


def shin_pt(f, s, up):
    """A point on the drawn shin `up` metres above the ankle."""
    a, k = drawn(f, 'giay %s 2' % s), drawn(f, 'chan %s 2' % s)
    v = k - a
    return a + v / np.linalg.norm(v) * up * K


def thigh_pt(f, s, up):
    k, h = drawn(f, 'chan %s 2' % s), drawn(f, 'dui %s 2' % s)
    v = h - k
    return k + v / np.linalg.norm(v) * up * K


def end_pt(f, code):
    """band_end codes of render_mannequin: hL/hR grip, fL/fR ball of the foot, aL/aR ankle, kL/kR knee,
    sL/sR behind the shoulder, eL/eR just behind the elbow."""
    k, s = code[0], code[1]
    if k == 'h':
        return grip(f, s)
    if k == 'f':
        return foot_pt(f, s)
    if k == 'a':
        return shin_pt(f, s, 0.07)
    if k == 'k':
        return knee_pt(f, s)
    if k == 's':
        return drawn(f, 'canh tay ' + s) + np.array([-0.1 * K, 0.0])
    if k == 'e':
        return drawn(f, 'cang tay ' + s) + np.array([-0.04 * K, 0.0])
    raise KeyError(code)


def end3(fr, code):
    k, s = code[0], code[1]
    b = {'h': 'hand', 'f': 'foot', 'a': 'foot', 'k': 'knee', 's': 'arm', 'e': 'elbow'}[k] + s
    return jp(fr, b)


def path_of(pts, closed=True):
    return {'c': closed, 'v': [[round(float(x), 2), round(float(y), 2)] for x, y in pts],
            'i': [[0, 0]] * len(pts), 'o': [[0, 0]] * len(pts)}


def rect(x0, y0, x1, y1, fill, track=True, nm='box'):
    x0, x1 = (x0, x1) if x0 <= x1 else (x1, x0)
    y0, y1 = (y0, y1) if y0 <= y1 else (y1, y0)
    if track:
        PROP_PTS.extend([[x0, y0], [x1, y1]])
    return group(nm, path_of([(x0, y0), (x1, y0), (x1, y1), (x0, y1)]), fill=fill)


def rrect(x0, y0, x1, y1, r, fill, track=True, nm='box', stroke=None):
    """Rounded rectangle (corner radius r)."""
    x0, x1 = (x0, x1) if x0 <= x1 else (x1, x0)
    y0, y1 = (y0, y1) if y0 <= y1 else (y1, y0)
    r = max(0.0, min(r, (x1 - x0) / 2, (y1 - y0) / 2))
    if track:
        PROP_PTS.extend([[x0, y0], [x1, y1]])
    k = 0.5523 * r
    v = [(x0 + r, y0), (x1 - r, y0), (x1, y0 + r), (x1, y1 - r), (x1 - r, y1), (x0 + r, y1), (x0, y1 - r), (x0, y0 + r)]
    ii = [(-k, 0), (0, 0), (0, -k), (0, 0), (k, 0), (0, 0), (0, k), (0, 0)]
    oo = [(0, 0), (k, 0), (0, 0), (0, k), (0, 0), (-k, 0), (0, 0), (0, -k)]
    pth = {'c': True, 'v': [[round(a, 2), round(b, 2)] for a, b in v], 'i': [list(p) for p in ii], 'o': [list(p) for p in oo]}
    return group(nm, pth, fill=fill, stroke=stroke, width=1.2)


def ellipse(cx, cy, rx, ry, fill, track=True, nm='elipse', n=12, stroke=None):
    if track:
        PROP_PTS.extend([[cx - rx, cy - ry], [cx + rx, cy + ry]])
    return group(nm, smooth_path([[cx + rx * math.cos(a), cy + ry * math.sin(a)]
                                  for a in np.linspace(0, 2 * math.pi, n, endpoint=False)]), fill=fill, stroke=stroke, width=1.2)


def prop_layer(nm, shapes, behind=True, at=None):
    """A shape layer for a prop: behind the whole body, on top of it, or inserted just above layer `at`."""
    ind = max(l['ind'] for l in comp['layers']) + 1
    lay = {'ddd': 0, 'ind': ind, 'ty': 4, 'nm': nm, 'sr': 1,
           'ks': {'o': {'a': 0, 'k': 100}, 'r': {'a': 0, 'k': 0}, 'p': {'a': 0, 'k': [0, 0, 0]},
                  'a': {'a': 0, 'k': [0, 0, 0]}, 's': {'a': 0, 'k': [100, 100, 100]}},
           'ao': 0, 'shapes': shapes, 'ip': 0, 'op': N, 'st': 0, 'bm': 0}
    if at is not None:
        k = next(i for i, l in enumerate(comp['layers']) if l['nm'] == at)
        comp['layers'].insert(k, lay)
    elif behind:
        k = next(i for i, l in enumerate(comp['layers']) if l['nm'] == 'shadow')
        comp['layers'].insert(k, lay)              # behind the body, in front of its floor shadow
    else:
        comp['layers'].insert(0, lay)
    return lay


def solid_layer(nm, shapes, behind=True, at=None):
    if shapes:
        return prop_layer(nm, shapes, behind, at)


def moving_layer(nm, shapes, ps, rs=None, behind=False, at=None, r_track=0.0):
    """A prop drawn around its own origin, carried every frame to ps[f] (and turned rs[f] degrees)."""
    lay = prop_layer(nm, shapes, behind, at)
    lay['ks']['p'] = anim([[round(float(p[0]), 2), round(float(p[1]), 2), 0] for p in ps], 3)
    if rs is not None:
        lay['ks']['r'] = anim(list(np.round(np.rad2deg(np.unwrap(np.deg2rad(np.array(rs, float)))), 3)), 1)
    for p in ps[::2]:
        PROP_PTS.extend([[p[0] - r_track, p[1] - r_track], [p[0] + r_track, p[1] + r_track]])
    return lay


CHAIR, CHAIR_DK, CHAIR_TOP = '#C5D0DC', '#8E9AAB', '#DCE3EB'
WALL_C, STEP_C, STEP_TOP = '#E7EDF4', '#9AA8BA', '#5E6B7D'
BALL_C, DB_C, DB_HI, BAND_C = '#F2A65A', '#3D4654', '#5A6577', '#F57C1F'
MAT_C, MAT_TOP, ROLL_C, BED_C = '#C9D5E2', '#DCE5EE', '#7FB7AE', '#F4F6F9'
BED_BASE, PILLOW_C, PILLOW_LN = '#C5D0DC', '#F4F1EC', '#DDD6CB'
SWISS_C, SWISS_HI, WOBBLE_C, BOSU_C = '#5B8DEF', '#7FA6F3', '#7C6FD6', '#2F80ED'
STICK_C, WALKER_C, GRIP_C, LADDER_C = '#3F6E8C', '#AEB8C6', '#3D4A5C', '#E2B43A'
TOWEL_C, TOWEL_LN, MARK_C, TAPE_C = '#E6DCC6', '#CFC6B3', '#F5593D', '#3D4A5C'
FL = FLOOR_LINE                                   # near floor line (FLOOR_Z), final coordinates
FAR = OFF['L']


def top_band(x0, x1, h, front, top, track=True, nm='tampo'):
    """A support seen from a little above: its top face (far line to near line) and its front face below."""
    yn, yf = sup_line(h), sup_line(h, 'L')
    out = [rect(x0, yf - 2, x1, yn, top, track, nm)]
    if front:
        out.insert(0, rect(x0, yn, x1, yn + front, CHAIR_DK if top == CHAIR_TOP else STEP_TOP, track, nm + ' frente'))
    return out


def chair_px(front_x, back_x, seat_y, floor_y, back_h, seat_far=None):
    """Chair in screen pixels: seat (its top face up to seat_far), two legs, backrest at back_x."""
    thick = max(8.0, 0.04 * K)
    x0, x1 = sorted((front_x, back_x))
    shapes = []
    if back_h > 4:
        shapes.append(rrect(back_x - thick * 0.45, seat_y - back_h, back_x + thick * 0.45, seat_y + thick, 3, CHAIR))
    if seat_far is not None and seat_far < seat_y - 2:
        shapes.append(rect(x0, seat_far, x1, seat_y, CHAIR_TOP))
    shapes.append(rrect(x0, seat_y, x1, seat_y + thick, 2, CHAIR))
    span = x1 - x0
    for x in (x0 + span * 0.08, x1 - span * 0.08 - thick * 0.7):
        shapes.append(rect(x, seat_y + thick * 0.3, x + thick * 0.7, floor_y, CHAIR_DK))
    return shapes


def box_along(b, f=0):
    """Range of a ground box along the facing, metres from the hips of frame f."""
    hp = jp(frames[f], 'hips')
    al = [float(np.dot(np.array([x, y, 0.0]) - np.array([hp[0], hp[1], 0.0]), FWD)) for x in b[:2] for y in b[2:4]]
    return min(al), max(al)


def box_x(b, f=0):
    a0, a1 = box_along(b, f)
    return float(along_pt(f, a0, FLOOR_Z)[0]), float(along_pt(f, a1, FLOOR_Z)[0])


hz0 = float(jp(frames[0], 'hips')[2])
floor_z = FLOOR_Z
floor_y = FL
seated = bool(PROPS & {'chair', 'stool'} or ('ball' in PROPS and not PROPS & {'wallball', 'wallback'} and 0.38 < hz0 < 0.68))
DONE = set()

# --- seats
if 'swissseat' in PROPS:
    # an exercise ball as the seat (55 cm, squashed a little under the pelvis)
    seat_f = min(range(N), key=lambda i: frames[i]['hips'][0][2])
    rot_, pos_ = POSES[seat_f]
    SCL.update(SCL_F[seat_f])
    bottom = max(p[1] for p in shape_points(L[I['mong']]['shapes'], world(I['mong'], rot_, pos_)))
    SCL.clear()
    hip = hip_px(seat_f)
    ry = (FL - bottom + 4) / 2
    rx = 0.29 * K
    cx = hip[0] + 0.03 * K
    solid_layer('bola suica', [ellipse(cx - rx * 0.35, FL - ry * 1.35, rx * 0.22, ry * 0.12, SWISS_HI, nm='brilho'),
                               ellipse(cx, FL - ry, rx, ry, SWISS_C, n=16)])
    DONE.add('swissseat')
elif seated or PROPS & {'chairfit'}:
    # fit the seat to the drawn pelvis at the lowest (most seated) frame
    seat_f = min(range(N), key=lambda i: frames[i]['hips'][0][2])
    hip = hip_px(seat_f)
    back_h = 0.0 if 'stool' in PROPS else 0.46 * K
    sy = hip[1] + 0.04 * K
    solid_layer('cadeira', chair_px(hip[0] + 0.22 * K, hip[0] - 0.18 * K, sy, FL, back_h, sy - FAR * 0.6))
if 'chairbehind' in PROPS:
    low = max(range(N), key=lambda i: float(hip_px(i)[1]))
    hip = hip_px(low)
    solid_layer('cadeira', chair_px(hip[0] - 0.05 * K, hip[0] - 0.43 * K, FL - 0.45 * K, FL, 0.42 * K, FL - 0.45 * K - FAR * 0.6))
if 'bedfit' in PROPS:
    hip = hip_px(0)
    top = hip[1] + 0.075 * K
    solid_layer('cama', [rect(hip[0] - 0.95 * K, top, hip[0] + 0.12 * K, top + 0.18 * K, BED_C),
                         rect(hip[0] - 0.97 * K, top + 0.18 * K, hip[0] + 0.14 * K, FL, BED_BASE)])

# --- the ground boxes the move was built on (kineti_builder "ground"): what each one is depends on the props
if BOXES and not PROPS & {'walker', 'walkergo', 'swissseat'} and not any(p.startswith(('ballfeet', 'ballarms', 'ballhands', 'ballback')) for p in PROPS):
    for b in BOXES:
        h = b[4] - FLOOR_Z
        x0, x1 = box_x(b)
        yn, yf = sup_line(h), sup_line(h, 'L')
        if 'chairbox' in PROPS:
            # a chair seat; its backrest on the side away from the pelvis
            a0, a1 = box_along(b)
            back_x = x1 if (a0 + a1) / 2 > 0 else x0
            solid_layer('cadeira', chair_px(x1 if back_x == x0 else x0, back_x, yn, FL, 0.5 * K, yf))
        elif 'table' in PROPS or any(p.startswith('table') for p in PROPS):
            th = max(8.0, 0.04 * K)
            bits = [rect(x0, yf, x1, yn, CHAIR_TOP), rrect(x0 - 4, yn, x1 + 4, yn + th, 2, CHAIR)]
            for x in (x0 + 0.05 * K, x1 - 0.05 * K - th * 0.7):
                bits.append(rect(x, yn + th, x + th * 0.7, FL, CHAIR_DK))
            solid_layer('mesa', bits)
        elif 'pillow' in PROPS:
            z = 0.0
            bits = []
            if h > 0.45:                                    # a small table under one pillow
                th = max(8.0, 0.04 * K)
                yt = sup_line(h - 0.1)
                bits += [rect(x0 - 0.05 * K, yt, x1 + 0.05 * K, yt + th, CHAIR)]
                for x in (x0, x1 - th * 0.7):
                    bits.append(rect(x, yt + th, x + th * 0.7, FL, CHAIR_DK))
                z = h - 0.1
            n = max(1, round((h - z) / 0.12))
            tk = (h - z) / n
            for i_ in range(n):
                ya, yb = sup_line(z + tk * (i_ + 1)), sup_line(z + tk * i_)
                bits.insert(0, rrect(x0 + 0.01 * K * (i_ % 2), ya - (FAR * 0.5 if i_ == n - 1 else 0), x1, yb, tk * K * 0.45,
                                     PILLOW_C, stroke=PILLOW_LN))
            solid_layer('travesseiro', bits)
        elif PROPS & {'wobble', 'board', 'bosu', 'bosuflat'}:
            c, r = (x0 + x1) / 2, (x1 - x0) / 2
            if 'wobble' in PROPS:                           # an air cushion
                bits = [rrect(c - r, yf, c + r, FL, (FL - yf) * 0.45, WOBBLE_C)]
            elif 'board' in PROPS:                          # a round board on a half-sphere pivot
                bits = [rrect(c - r, yf, c + r, yn + 0.025 * K, 3, STEP_TOP),
                        ellipse(c, FL, (h - 0.025) * K, (h - 0.025) * K, STEP_C, n=14)]
            elif 'bosuflat' in PROPS:                       # dome down, the flat platform on top
                bits = [rrect(c - r, yf, c + r, yn + 0.03 * K, 3, STEP_TOP),
                        group('cupula', path_of([(c - r, yn + 0.03 * K), (c + r, yn + 0.03 * K), (c + 0.1 * K, FL), (c - 0.1 * K, FL)]), fill=BOSU_C)]
                PROP_PTS.extend([[c - r, yf], [c + r, FL]])
            else:                                           # BOSU: a dome on a dark ring
                dome = [[c + r * math.cos(a), FL - (FL - yf + 4) * math.sin(a)] for a in np.linspace(0, math.pi, 9)]
                bits = [rect(c - r - 4, FL - 0.03 * K, c + r + 4, FL, STEP_TOP),
                        group('cupula', smooth_path(dome, closed=True), fill=BOSU_C)]
                PROP_PTS.extend([[c - r, yf], [c + r, FL]])
            solid_layer('disco', bits)
        elif 'bed' in PROPS:
            solid_layer('cama', [rect(x0, yf, x1, yn, BED_C), rect(x0, yn, x1, yn + 0.12 * K, BED_C),
                                 rect(x0 - 3, yn + 0.12 * K, x1 + 3, FL, BED_BASE)])
        else:                                               # an aerobic step: grey block, dark rubber top
            solid_layer('degrau', [rect(x0, yf, x1, yn + 0.02 * K, STEP_TOP), rect(x0, yn, x1, FL, STEP_C)])
    DONE |= {'chairbox', 'pillow', 'wobble', 'board', 'bosu', 'bosuflat', 'step'}
    if 'bed' in PROPS:
        DONE.add('bed')

# --- supports under planted hands (no ground box): a chair backrest, a side chair, a table
if PROPS & {'support', 'side'}:
    for s, h in VIRT.items():
        fs = [f for f in range(N) if PLANT[s][f] > 0.5] or list(range(N))
        hx = float(np.median([grip(f, s)[0] for f in fs]))
        thick = max(8.0, 0.04 * K)
        yn, yf = sup_line(h), sup_line(h, 'L')
        # the backrest: its top rail under the palm, the seat behind it (away from the body), legs to the floor
        back_x0, back_x1 = hx - 0.05 * K, hx + 0.05 * K
        seat_y = FL - 0.45 * K
        bits = [rect(back_x0, yf, back_x1, yn, CHAIR_TOP), rrect(back_x0, yn, back_x1, yn + thick, 3, CHAIR),
                rect(hx - thick * 0.45, yn, hx + thick * 0.45, seat_y, CHAIR)]
        bits += chair_px(hx + 0.44 * K, hx, seat_y, FL, 0.0, seat_y - FAR * 0.6)
        solid_layer('cadeira', bits)
    DONE |= {'support', 'side'}
if 'table' in PROPS and not BOXES and VIRT:
    h = min(VIRT.values())
    hx = float(np.median([grip(f, s)[0] for s in VIRT for f in range(N)]))
    x0, x1 = hx - 0.12 * K, hx + (0.35 if len(VIRT) == 1 else 0.6) * K
    th = max(8.0, 0.04 * K)
    yn, yf = sup_line(h), sup_line(h, 'L')
    bits = [rect(x0, yf, x1, yn, CHAIR_TOP), rrect(x0, yn, x1, yn + th, 2, CHAIR)]
    for x in (x0 + 0.04 * K, x1 - 0.04 * K - th * 0.7):
        bits.append(rect(x, yn + th, x + th * 0.7, FL, CHAIR_DK))
    solid_layer('mesa', bits)
    DONE.add('table')

# --- walls
WALL_X = None
if WALL_A is not None:
    WALL_X = float(drawn(0, 'canh tay R')[0] + (WALL_A - float(np.dot(jp(frames[0], 'armR'), FWD))) * K)
    top = min(min(grip(f, s)[1] for s in 'LR') for f in range(N)) - 0.9 * K
    if not _wp:                     # a pressed ball's wall is drawn past the ball (below)
        solid_layer('parede', [rect(WALL_X, top, WALL_X + 14, FL, WALL_C)])
    DONE.add('wall')
if PROPS & {'wallback', 'wallball'}:
    # the wall touches the back over the whole motion (wall squat); with wallball an exercise ball sits between the
    # lower back and the wall
    back = []
    for f in range(N):
        pts = []
        for nm in ('than', 'mong', 'dau'):
            SCL.update(SCL_F[f])
            pts += shape_points(L[I[nm]]['shapes'], world(I[nm], *POSES[f]))
            SCL.clear()
        back.append(min(p[0] for p in pts))
    bx = min(back)
    if 'wallball' in PROPS:
        BR = 0.3 * K
        wx = bx - 2 * BR + 0.05 * K
        ps = []
        for f in range(N):
            sp = drawn(f, 'than')
            ps.append([wx + BR, (sp[1] + hip_px(f)[1]) / 2 - 0.08 * K])
        moving_layer('bola', [ellipse(-BR * 0.35, -BR * 0.4, BR * 0.22, BR * 0.13, '#F6BC82', False, 'brilho'),
                              ellipse(0, 0, BR, BR, BALL_C, False, n=16)], ps, behind=True, r_track=BR)
    else:
        wx = bx - 2
    solid_layer('parede', [rect(wx - 16, FL - 2.1 * K, wx, FL, WALL_C)])
    DONE |= {'wallback', 'wallball'}

# --- top view (top_view.py --side): the floor is the page; a mat (or the bed's top) under the body, a pillow under
# the head, behind the figure
if TOP:
    xs, ys = [], []
    for f in range(0, N, 3):
        for nm in ('mong', 'dau', 'giay R 2', 'giay L 2', 'ban tay R', 'ban tay L', 'chan R 2', 'chan L 2'):
            p_ = drawn(f, nm)
            xs.append(float(p_[0])); ys.append(float(p_[1]))
    cx = (min(xs) + max(xs)) / 2
    hw = max(0.36 * K, (max(xs) - min(xs)) / 2 + 0.15 * K)
    y0, y1 = min(ys) - 0.25 * K, max(ys) + 0.12 * K
    if 'bed' in PROPS:
        solid_layer('cama', [rrect(cx - hw - 0.1 * K, y0 - 0.05 * K, cx + hw + 0.1 * K, y1 + 0.05 * K, 0.03 * K, BED_C, stroke=BED_BASE)])
    else:
        solid_layer('colchonete', [rrect(cx - hw, y0, cx + hw, y1, 0.04 * K, MAT_TOP, stroke=MAT_C)])
    if 'pillow' in PROPS:
        hd = drawn(0, 'dau')
        solid_layer('travesseiro', [rrect(hd[0] - 0.2 * K, hd[1] - 0.22 * K, hd[0] + 0.2 * K, hd[1] + 0.08 * K, 0.05 * K,
                                          PILLOW_C, stroke=PILLOW_LN)])
    DONE |= {'bed', 'mat', 'pillow'}
# --- floor things
if 'roll' in PROPS:
    best = max(range(N), key=lambda f: max(frames[f]['foot' + s][0][2] for s in 'LR'))
    kn = knee_pt(best, 'R')
    r = 0.07 * K
    solid_layer('rolo', [ellipse(kn[0], FL - r, r * 1.05, r, ROLL_C, n=12)])
    DONE.add('roll')
if 'bed' in PROPS and 'bed' not in DONE:
    xs = [p for f in range(0, N, 3) for p in (hip_px(f)[0], foot_pt(f, 'R')[0], drawn(f, 'dau')[0], foot_pt(f, 'L')[0])]
    x0, x1 = min(xs) - 0.3 * K, max(xs) + 0.3 * K
    drop = 0.5 * K
    solid_layer('cama', [rect(x0, FL - FAR - 6, x1, FL + 0.16 * K, BED_C),
                         rect(x0 - 3, FL + 0.16 * K, x1 + 3, FL + drop - 0.08 * K, BED_BASE),
                         rect(x0 + 0.04 * K, FL + drop - 0.08 * K, x0 + 0.08 * K, FL + drop, CHAIR_DK),
                         rect(x1 - 0.08 * K, FL + drop - 0.08 * K, x1 - 0.04 * K, FL + drop, CHAIR_DK)])
    DONE.add('bed')
elif not TOP and ('mat' in PROPS or (FLOOR and not PROPS & {'chair', 'chairfit', 'bed', 'swissseat'})):
    xs = []
    for f in range(0, N, 3):
        for nm in ('mong', 'dau', 'giay R 2', 'giay L 2', 'ban tay R', 'ban tay L', 'chan R 2'):
            xs.append(drawn(f, nm)[0])
    x0, x1 = min(xs) - 0.2 * K, max(xs) + 0.2 * K
    solid_layer('colchonete', [rect(x0, FL - FAR - 8, x1, FL + 2, MAT_TOP), rect(x0, FL + 2, x1, FL + max(8, 0.02 * K), MAT_C)])
if 'pillow' in PROPS and 'pillow' not in DONE:
    # a pillow under the head (lying) or behind the back
    f0_ = 0
    hd = drawn(f0_, 'dau')
    solid_layer('travesseiro', [rrect(hd[0] - 0.22 * K, FL - 0.09 * K - FAR * 0.5, hd[0] + 0.18 * K, FL, 0.04 * K, PILLOW_C, stroke=PILLOW_LN)])
if 'step' in PROPS and 'step' not in DONE:
    # no ground box: a 20 cm step under the soles that are highest in 3D, both feet up (a heel drop)
    hi_f = min(range(N), key=lambda f: min(QA[f]['sh'][s][0] for s in 'LR'))
    ank = foot_pt(hi_f, 'R', 'ankle')
    x0, x1 = ank[0] - 0.08 * K, ank[0] + 0.3 * K
    solid_layer('degrau', [rect(x0, FL - 0.2 * K - FAR, x1, FL - 0.18 * K, STEP_TOP), rect(x0, FL - 0.2 * K, x1, FL, STEP_C)])
if 'marks' in PROPS:
    bits = []
    for s in 'LR':
        p0 = foot_pt(0, s)
        spots = []
        for f in range(N):
            q = foot_pt(f, s)
            if QA[f]['fz'][s] < 0.015 and abs(q[0] - p0[0]) > 0.15 * K:
                if spots and abs(spots[-1][-1] - q[0]) < 0.08 * K:
                    spots[-1].append(q[0])
                else:
                    spots.append([q[0]])
        for sp_ in spots:
            c = float(np.mean(sp_))
            yb = FL - (FAR if s == 'L' else 0)
            bits.append(ellipse(c, yb - 2, 0.075 * K, 0.022 * K, MARK_C))
    solid_layer('marcas', bits)
if 'line' in PROPS:
    xs = [hip_px(f)[0] for f in range(N)]
    c = (max(xs) + min(xs)) / 2
    solid_layer('fita', [rect(c - 0.02 * K, FL - FAR - 4, c + 0.02 * K, FL + 2, TAPE_C)])
ladders = [p for p in PROPS if p.startswith('ladder-')]
if ladders:
    step_m = int(ladders[0].split('-')[1]) / 100
    xs = [foot_pt(f, s)[0] for f in range(N) for s in 'LR']
    x0, x1 = min(xs) - 0.6 * K, max(xs) + 0.6 * K
    rail = max(5.0, 0.015 * K)
    bits = [rect(x0, FL - FAR - 2, x1, FL - FAR - 2 + rail * 0.8, LADDER_C), rect(x0, FL - rail * 0.8, x1, FL, LADDER_C)]
    x = x0
    while x < x1:
        bits.append(group('degrau', path_of([(x, FL - FAR - 2), (x + rail, FL - FAR - 2), (x + rail, FL), (x, FL)]), fill=LADDER_C))
        x += step_m * K
    solid_layer('escada', bits)

# --- held and worn things (follow the drawn body every frame)
if 'ball' in PROPS:
    # squeezed between the knees: just in front of the far knee, behind the near leg
    r = 0.1 * K
    ps = [(knee_pt(f, 'R') + knee_pt(f, 'L')) / 2 + np.array([0.05 * K, -0.01 * K]) for f in range(N)]
    moving_layer('bola', [ellipse(-r * 0.35, -r * 0.4, r * 0.22, r * 0.13, '#F6BC82', False, 'brilho'),
                          ellipse(0, 0, r, r, BALL_C, False)], ps, at='giay L 2', r_track=r)
if 'kneepillow' in PROPS:
    ps = [(knee_pt(f, 'R') + knee_pt(f, 'L')) / 2 + np.array([0.03 * K, 0.0]) for f in range(N)]
    moving_layer('travesseiro', [rrect(-0.13 * K, -0.06 * K, 0.13 * K, 0.06 * K, 0.04 * K, PILLOW_C, False, stroke=PILLOW_LN)],
                 ps, at='giay L 2', r_track=0.13 * K)
for ap in [p for p in PROPS if p.startswith('armpillow')]:
    s = ap[-1]
    ps = [drawn(f, 'cang tay ' + s) + np.array([0.0, -0.05 * K]) for f in range(N)]
    moving_layer('travesseiro', [rrect(-0.06 * K, -0.12 * K, 0.06 * K, 0.12 * K, 0.04 * K, PILLOW_C, False, stroke=PILLOW_LN)],
                 ps, at=NEAR_TOP if s == 'R' else 'cang tay L', r_track=0.12 * K)
if 'heldball' in PROPS:
    # a ball held between the palms: radius from the palms' 3D distance (render_mannequin)
    pl3 = np.linalg.norm(palm3(frames[0], 'L') - palm3(frames[0], 'R'))
    rb = min(max(pl3 / 2 - 0.035, 0.08), 0.3) * K
    ps = []
    for f in range(N):
        a_, b_ = grip(f, 'R'), grip(f, 'L')
        u, t = hand_axes(f, 'R')
        ps.append((a_ + b_) / 2 + u * 0.1 * HG['R']['Lh'])
    moving_layer('bola', [ellipse(-rb * 0.35, -rb * 0.4, rb * 0.22, rb * 0.13, '#F6BC82', False, 'brilho'),
                          ellipse(0, 0, rb, rb, BALL_C, False, n=14)], ps, at=NEAR_TOP, r_track=rb)
if 'waistball' in PROPS:
    rb = 0.1 * K
    ps = [grip(f, 'R' if f < N / 2 else 'L') for f in range(N)]
    moving_layer('bola', [ellipse(0, 0, rb, rb, BALL_C, False)], ps, at=NEAR_TOP, r_track=rb)
if 'dumbbell' in PROPS:
    # a hammer-grip dumbbell: the bar runs thumb-to-little-finger through the fist, a plate on each side
    for s in 'LR':
        pts = _fist_pts[s]
        g = HG[s]
        half = float(np.abs((pts - FIST_C[s]) @ g['tl']).max())
        pr, pw, bt = 0.042 * K, 0.042 * K, 0.012 * K
        off = half + pw * 0.5 + 1
        shapes = [rrect(-pr, -off - pw / 2, pr, -off + pw / 2, 5, DB_C, False, 'anilha'),
                  rrect(-pr, off - pw / 2, pr, off + pw / 2, 4, DB_C, False, 'anilha'),
                  rect(-bt, -off, bt, off, DB_HI, False, 'barra')]
        # local frame: x along the hand's u, y across it (the bar runs along y)
        ps = [grip(f, s) for f in range(N)]
        rs = [math.degrees(math.atan2(hand_axes(f, s)[0][1], hand_axes(f, s)[0][0])) for f in range(N)]
        moving_layer('halter ' + s, shapes, ps, rs, at=NEAR_TOP if s == 'R' else 'ban tay L', r_track=off + pw)
        if s == 'L':          # above the far hand: move the layer just above it
            k_h = next(i for i, l in enumerate(comp['layers']) if l['nm'] == 'ban tay L')
            k_d = next(i for i, l in enumerate(comp['layers']) if l['nm'] == 'halter L')
            if k_d > k_h:
                comp['layers'].insert(k_h, comp['layers'].pop(k_d))
if 'cuff' in PROPS:
    for s in 'LR':
        ps, rs = [], []
        for f in range(N):
            a = shin_pt(f, s, 0.06)
            k = knee_pt(f, s)
            ps.append(a)
            rs.append(math.degrees(math.atan2(k[1] - a[1], k[0] - a[0])))
        cw = 0.065 * K
        moving_layer('caneleira ' + s, [rrect(-0.035 * K, -cw / 2 - 4, 0.035 * K, cw / 2 + 4, 6, '#334155', False)], ps, rs,
                     at='giay R 2' if s == 'R' else 'giay L 2', r_track=cw)


def bar_between(pa, pb, nm, fill, thick, min_len=1.0, at=None, behind=False, stroke=None, center_len=None):
    """A straight bar (band, rope, stick, towel) between two moving points, as a unit rectangle stretched,
    turned and carried every frame. center_len: a fixed-length bar centred between the points instead."""
    ks_p, ks_r, ks_s = [], [], []
    for a, b in zip(pa, pb):
        dv = b - a
        dist = float(np.linalg.norm(dv))
        mid = (a + b) / 2
        an = math.degrees(math.atan2(dv[1], dv[0])) if dist > 8 else (ks_r[-1] if ks_r else 0.0)
        if center_len is not None:
            dist = max(center_len(a, b), min_len)
        dist = max(dist, min_len)
        ks_p.append([round(float(mid[0]), 2), round(float(mid[1]), 2), 0])
        ks_r.append(an)
        ks_s.append([round(dist * 100, 2), 100, 100])
        PROP_PTS.extend([(mid + (dv / max(np.linalg.norm(dv), 1e-6)) * dist / 2).tolist(),
                         (mid - (dv / max(np.linalg.norm(dv), 1e-6)) * dist / 2).tolist()])
    bar = {'ty': 'gr', 'nm': 'barra', 'it': [
        {'ty': 'rc', 'nm': 'rc', 'p': {'a': 0, 'k': [0, 0]}, 's': {'a': 0, 'k': [1, thick * 2]}, 'r': {'a': 0, 'k': 0}},
        {'ty': 'fl', 'c': {'a': 0, 'k': hexc(fill)}, 'o': {'a': 0, 'k': 100}, 'r': 1, 'nm': 'fill'},
        {'ty': 'tr', 'p': {'a': 0, 'k': [0, 0]}, 'a': {'a': 0, 'k': [0, 0]}, 's': {'a': 0, 'k': [100, 100]},
         'r': {'a': 0, 'k': 0}, 'o': {'a': 0, 'k': 100}, 'sk': {'a': 0, 'k': 0}, 'sa': {'a': 0, 'k': 0}}]}
    if stroke:
        bar['it'].insert(1, {'ty': 'st', 'c': {'a': 0, 'k': hexc(stroke)}, 'o': {'a': 0, 'k': 100}, 'w': {'a': 0, 'k': 0.012},
                             'lc': 2, 'lj': 2, 'nm': 'stroke'})
    lay = prop_layer(nm, [bar], behind, at)
    lay['ks']['p'] = anim(ks_p, 3)
    lay['ks']['r'] = anim(list(np.round(np.rad2deg(np.unwrap(np.deg2rad(np.array(ks_r)))), 3)), 1)
    lay['ks']['s'] = anim(ks_s, 3)
    return lay


def post_at(x, top_y, nm='batente'):
    solid_layer(nm, [rect(x - 0.025 * K, top_y, x + 0.025 * K, FL, CHAIR)], behind=True)


BT = max(2.4, 0.008 * K)                       # band half thickness
# --- elastic bands
if 'bandhands' in PROPS:
    bar_between([grip(f, 'L') for f in range(N)], [grip(f, 'R') for f in range(N)], 'faixa', BAND_C, BT, at=NEAR_TOP)
if PROPS & {'bandanchor', 'bandanchor1'}:
    sides = ['L', 'R']
    if 'bandanchor1' in PROPS:
        trav = {s: max(np.linalg.norm(palm3(fr, s) - palm3(frames[0], s)) for fr in frames) for s in 'LR'}
        sides = [max(trav, key=trav.get)]
    p0 = np.mean([palm3(frames[0], s) for s in sides], axis=0)
    sh0 = np.mean([jp(frames[0], 'arm' + s) for s in sides], axis=0)
    dv = p0 - sh0
    dv[2] = 0
    dv = dv / np.linalg.norm(dv) if np.linalg.norm(dv) > 0.05 else FWD
    anc3 = p0 + dv * 0.55
    anc = np.mean([grip(0, s) for s in sides], axis=0) + P(dv) * 0.55 * K
    post_at(anc[0], FL - 2.0 * K)
    for s in sides:
        bar_between([grip(f, s) for f in range(N)], [anc] * N, 'faixa ' + s, BAND_C, BT,
                    at=NEAR_TOP if s == 'R' else 'cang tay L')
if 'bandfeet' in PROPS:
    for s in 'LR':
        bar_between([grip(f, s) for f in range(N)], [(foot_pt(f, 'L') + foot_pt(f, 'R')) / 2 for f in range(N)],
                    'faixa ' + s, BAND_C, BT, at=NEAR_TOP if s == 'R' else 'cang tay L')
if PROPS & {'bandknees', 'bandankles'}:
    # a loop round both thighs above the knees (or both shins above the ankles): seen from the side, a strip
    # across each drawn limb, the near one on top of the near leg, the far one on the far leg
    for s in 'LR':
        for kind in [k for k in ('bandknees', 'bandankles') if k in PROPS]:
            ps, rs = [], []
            for f in range(N):
                if kind == 'bandknees':
                    c, a = thigh_pt(f, s, 0.09), knee_pt(f, s)
                else:
                    c, a = shin_pt(f, s, 0.07), drawn(f, 'giay %s 2' % s)
                ps.append(c)
                rs.append(math.degrees(math.atan2(c[1] - a[1], c[0] - a[0])))
            w_ = 0.075 * K if kind == 'bandknees' else 0.06 * K
            moving_layer('faixa ' + s, [rrect(-BT * 1.6, -w_, BT * 1.6, w_, BT, BAND_C, False)], ps, rs,
                         at=('dui R 2' if kind == 'bandknees' else 'giay R 2') if s == 'R' else ('dui L 2' if kind == 'bandknees' else 'giay L 2'),
                         r_track=w_)
# band-<end>-<end> and towel-<end>-<end> (render_mannequin): ends are body points or a post F/B/L/R 0.6 m from
# the other end's start, at its height (lo/hi: 12 cm / 1.95 m). L/R posts stand beside the body: in a side
# view they are behind it, so the band runs to the body's own x there.
for bp in sorted(p for p in PROPS if p.startswith(('band-', 'towel-'))):
    ends = bp.split('-')[1:]
    towel = bp.startswith('towel-')
    tracks = []
    for i_, e_ in enumerate(ends):
        if e_[0] in 'FBLR' and (len(e_) == 1 or e_[1:] in ('lo', 'hi')):
            other = ends[1 - i_]
            o2 = end_pt(0, other)
            o3 = end3(frames[0], other)
            dx = {'F': 0.6, 'B': -0.6, 'L': 0.0, 'R': 0.0}[e_[0]] * K
            if e_[0] in 'FB' and abs(float(np.dot(o3 - jp(frames[0], 'hips'), FWD))) > 0.05:
                dx += np.sign(dx) * 0.12 * K
            zy = {'lo': FL - 0.12 * K, 'hi': FL - 1.95 * K}.get(e_[1:], o2[1])
            anc = np.array([o2[0] + dx, zy])
            if e_[0] in 'FB':
                post_at(anc[0], min(FL - 2.0 * K, zy - 0.1 * K))
            else:
                anc[0] = o2[0] - 0.02 * K
            tracks.append([anc] * N)
        else:
            tracks.append([end_pt(f, e_) for f in range(N)])
    near = any(e_ in ('hR', 'fR', 'aR', 'kR', 'sR') for e_ in ends)
    if towel:
        bar_between(tracks[0], tracks[1], 'toalha', TOWEL_C, max(6.0, 0.02 * K), at=NEAR_TOP if near else 'cang tay L')
    else:
        bar_between(tracks[0], tracks[1], 'faixa', BAND_C, BT, at=NEAR_TOP if near else 'cang tay L')

# --- sticks, canes, walkers
STICK_L = 1.05
for sp in sorted(p for p in PROPS if p == 'stick' or p.startswith(('stick-', 'stickend-', 'stickfloor-'))):
    kind, *ends = sp.split('-')
    ends = ends or ['hL', 'hR']
    A_ = [end_pt(f, ends[0]) for f in range(N)]
    B_ = [end_pt(f, ends[-1]) for f in range(N)]
    if kind == 'stickfloor':
        top0 = (A_[0] + B_[0]) / 2
        tip = np.array([top0[0] + 0.02 * K, FL])
        L0 = float(np.linalg.norm(top0 - tip)) + 0.06 * K
        tops = []
        for f in range(N):
            top = (A_[f] + B_[f]) / 2
            dv = top - tip
            tops.append(tip + dv / np.linalg.norm(dv) * max(L0, np.linalg.norm(dv) + 0.04 * K))
        bar_between([tip] * N, tops, 'bastao', STICK_C, max(3.5, 0.013 * K))
        continue
    # the stick's own 3D length and direction, projected: across the body it is seen end-on, a short stub
    pa3 = [end3(fr, ends[0]) for fr in frames]
    pb3 = [end3(fr, ends[-1]) for fr in frames]
    proj = [float(np.linalg.norm(P(b) - P(a))) for a, b in zip(pa3, pb3)]
    full = [max(STICK_L, float(np.linalg.norm(b - a)) + 0.2) for a, b in zip(pa3, pb3)]
    E0, E1 = [], []
    for f in range(N):
        c3 = float(np.linalg.norm(pb3[f] - pa3[f]))
        ln = full[f] * (proj[f] / c3 if c3 > 1e-3 else 0.0) * K
        c = (A_[f] + B_[f]) / 2
        dv = B_[f] - A_[f]
        if kind == 'stickend':
            c = A_[f] + dv * 0.0
        if ln < 0.26 * K or np.linalg.norm(dv) < 8:
            # across the body: seen almost end-on. A short, slightly turned stick through the fists reads as one.
            u, t = hand_axes(f, 'R')
            dv, ln = t, 0.26 * K
        dv = dv / np.linalg.norm(dv)
        if kind == 'stickend':
            E0.append(A_[f] - dv * 0.05 * K)
            E1.append(A_[f] + dv * (ln - 0.05 * K))
        else:
            E0.append(c - dv * ln / 2)
            E1.append(c + dv * ln / 2)
    bar_between(E0, E1, 'bastao', STICK_C, max(3.5, 0.013 * K), at=NEAR_TOP)
for cp in [p for p in PROPS if p in ('caneL', 'caneR')]:
    s = cp[-1]
    tops = [grip(f, s) for f in range(N)]
    bots = [np.array([t[0] + 0.03 * K, FL - (FAR if s == 'L' else 0)]) for t in tops]
    bar_between(bots, tops, 'bengala', STICK_C, max(3.5, 0.012 * K), at=NEAR_TOP if s == 'R' else 'ban tay L')
    bar_between([t + np.array([-0.03 * K, -0.02 * K]) for t in tops], [t + np.array([0.09 * K, -0.02 * K]) for t in tops],
                'bengala cabo', GRIP_C, max(4.0, 0.015 * K), at=NEAR_TOP if s == 'R' else 'ban tay L')
if PROPS & {'walker', 'walkergo'}:
    # a rolling walker seen from the side: the handles at the drawn hands, a front and a back leg, wheels in front
    if 'walkergo' in PROPS:
        fs = list(range(N))
    else:
        best = max(range(N), key=lambda i: float(grip(i, 'L')[0] + grip(i, 'R')[0]))
        fs = [best] * N
    hz_ = float(np.mean([(grip(f, 'L')[1] + grip(f, 'R')[1]) / 2 for f in fs]))
    if GRIPPED and BOXES:                            # the handles the move was built on
        hz_ = sup_line(max(b[4] for b in BOXES) - FLOOR_Z) + max(6.0, 0.016 * K) * 0.5
    hgt = FL - hz_
    thick = max(6.0, 0.016 * K)
    shapes = [rrect(-0.06 * K, -thick, 0.08 * K, thick, thick, GRIP_C, False, 'pega'),
              rect(-0.12 * K, -thick * 0.5, 0.32 * K, thick * 0.5, WALKER_C, False, 'trilho'),
              rect(0.3 * K - thick * 0.45, 0, 0.3 * K + thick * 0.45, hgt - 0.05 * K, WALKER_C, False, 'perna'),
              rect(-0.12 * K - thick * 0.45, 0, -0.12 * K + thick * 0.45, hgt, WALKER_C, False, 'perna'),
              rect(-0.12 * K, hgt * 0.55 - thick * 0.4, 0.3 * K, hgt * 0.55 + thick * 0.4, WALKER_C, False, 'travessa'),
              ellipse(0.3 * K, hgt - 0.045 * K, 0.045 * K, 0.045 * K, GRIP_C, False, 'roda')]
    ps = [np.array([(grip(f, 'L')[0] + grip(f, 'R')[0]) / 2, hz_]) for f in fs]
    if GRIPPED and 'walkergo' not in PROPS:          # fixed walker: the frame from its front legs, the grips slide
        gx = [min(grip(f, 'L')[0], grip(f, 'R')[0]) for f in range(N)]
        x_front = max(grip(f, 'R')[0] for f in range(N)) + 0.26 * K
        x_back = min(gx) - 0.04 * K
        shapes[1] = rect(x_back - ps[0][0], -thick * 0.5, x_front - ps[0][0], thick * 0.5, WALKER_C, False, 'trilho')
        shapes[2] = rect(x_front - ps[0][0] - thick * 0.9, 0, x_front - ps[0][0], hgt - 0.05 * K, WALKER_C, False, 'perna')
        shapes[5] = ellipse(x_front - ps[0][0] - thick * 0.45, hgt - 0.045 * K, 0.045 * K, 0.045 * K, GRIP_C, False, 'roda')
        shapes[4] = rect(-0.12 * K, hgt * 0.55 - thick * 0.4, x_front - ps[0][0], hgt * 0.55 + thick * 0.4, WALKER_C, False, 'travessa')
        gxr = float(np.median([grip(f, 'R')[0] for f in range(N)])) - ps[0][0]
        shapes[0] = rrect(gxr - 0.06 * K, -thick * 0.6, gxr + 0.06 * K, thick * 0.6, thick * 0.6, GRIP_C, False, 'pega')
        # the far side's frame, a little higher (the drawing is seen from slightly above)
        shapes.append(rect(x_back - ps[0][0], -FAR - thick * 0.5, x_front - ps[0][0], -FAR + thick * 0.5, '#C9D1DC', False, 'trilho longe'))
        shapes.append(rect(x_front - ps[0][0] - thick * 0.9, -FAR, x_front - ps[0][0], hgt - FAR - 0.05 * K, '#C9D1DC', False, 'perna longe'))
        shapes.append(rect(-0.12 * K - thick * 0.45, -FAR, -0.12 * K + thick * 0.45, hgt - FAR, '#C9D1DC', False, 'perna longe'))
    lay = moving_layer('andador', shapes, ps, behind=True)
    for p in ps[::3]:
        PROP_PTS.extend([[p[0] - 0.14 * K, p[1] - thick], [p[0] + 0.34 * K, FL]])
if 'pulley' in PROPS:
    nk = drawn(0, 'co')
    c = nk + np.array([-0.25 * K, -0.75 * K])
    r = max(10.0, 0.05 * K)
    solid_layer('roldana', [rect(c[0] - 3, c[1] - 0.6 * K, c[0] + 3, c[1], CHAIR_DK), ellipse(c[0], c[1], r, r, GRIP_C)])
    for s in 'LR':
        bar_between([grip(f, s) for f in range(N)], [c] * N, 'corda ' + s, BAND_C, max(1.8, 0.006 * K),
                    at=NEAR_TOP if s == 'R' else 'cang tay L')

# --- exercise balls under a part (render_mannequin.support_ball): on the floor, under the drawn part
for kind in sorted(p for p in PROPS if p.startswith(('ballfeet', 'ballhands', 'ballarms', 'ballback'))):
    part, side = (kind[:-1], kind[-1]) if kind[-1] in 'LR' else (kind, None)
    ss = [side] if side else ['L', 'R']
    ps, rr = [], []
    for f in range(N):
        if part == 'ballfeet':
            pts = [drawn(f, 'giay %s 2' % s) for s in ss]
            low = max(QA[f]['sh'][s][0] for s in ss)
        elif part == 'ballarms':
            pts = [(drawn(f, 'cang tay ' + s) + drawn(f, 'ban tay ' + s)) / 2 for s in ss]
            low = max(p[1] for p in pts) + HG['R']['hw']
        elif part == 'ballhands':
            pts = [grip(f, s) for s in ss]
            low = max(p[1] for p in pts) + HG['R']['hw']
        else:
            pts = [(drawn(f, 'co') * 0.7 + hip_px(f) * 0.3)]
            low = pts[0][1] + 0.12 * K
        x = float(np.mean([p[0] for p in pts]))
        r = float(np.clip((FL - low) / 2, 0.18 * K, 0.33 * K))
        ps.append([x, FL - r])
        rr.append(r)
    r = float(np.median(rr))
    if part == 'ballhands':
        ps = [ps[0]] * N
    ps = [[p[0], FL - r] for p in ps]
    moving_layer('bola suica', [ellipse(-r * 0.35, -r * 0.42, r * 0.2, r * 0.12, SWISS_HI, False, 'brilho'),
                                ellipse(0, 0, r, r, SWISS_C, False, n=16)], ps, behind=True, r_track=r)
    if 'ballwall' in PROPS:
        wx = ps[0][0] + r + 2
        solid_layer('parede', [rect(wx, FL - 2.0 * K, wx + 14, FL, WALL_C)])
for pp in [p for p in PROPS if p.startswith('pball-')]:
    _, size, part = pp.split('-')
    static = part.endswith('0')
    part = part[:2]
    r = {'v': 0.11, 't': 0.034}[size] * K
    col = BALL_C if size == 'v' else '#C8E64A'
    s = part[1]
    pts = []
    for f in range(N):
        if part[0] == 'h':
            q = grip(f, s)
        elif part[0] == 'f':
            q = foot_pt(f, s)
        elif part[0] == 'c':
            q = (drawn(f, 'giay %s 2' % s) + knee_pt(f, s)) / 2
        else:
            q = knee_pt(f, s)
        # top view: no floor line, the ball sits under the hand / foot / knee where it is drawn
        pts.append([q[0], q[1]] if TOP else [q[0], FL - r - (FAR if s == 'L' else 0)])
    if static:
        pts = [pts[0]] * N
    moving_layer('bola', [ellipse(0, 0, r, r, col, False)], pts, at=NEAR_TOP if s == 'R' else 'giay L 2', r_track=r)
for wp in [p for p in PROPS if p.startswith('wallpress-')]:
    _, end, dr = wp.split('-')
    rb = 0.11 * K
    sgn = {'F': 1, 'B': -1}.get(dr, 0)
    pts = [end_pt(f, end) for f in range(N)]
    ps = [p + np.array([sgn * rb, 0.0]) for p in pts]
    if sgn:
        # the wall touches the ball where the hand presses it most of the time (a planted hand holds one line; the
        # odd frame reaching past it must not push the wall away from the ball)
        far_x = float(np.percentile([p[0] * sgn for p in pts], 75)) * sgn
        wx = far_x + sgn * 2 * rb
        solid_layer('parede', [rect(wx, FL - 2.2 * K, wx + sgn * 14, FL, WALL_C)])
    moving_layer('bola', [ellipse(0, 0, rb, rb, BALL_C, False)], ps, at=NEAR_TOP if end[1] == 'R' else 'giay L 2', r_track=rb)
for wa in [p for p in PROPS if p.startswith('wallat-')]:
    _, end, dr = wa.split('-')
    if dr[0] not in 'FB':
        continue                                    # a wall beside the body: not visible from the side
    sgn = 1 if dr[0] == 'F' else -1
    pts = [end_pt(f, end) for f in range(N)]
    far_x = max(p[0] * sgn for p in pts) * sgn + sgn * 0.03 * K
    if dr.endswith('p'):
        solid_layer('batente', [rect(far_x, FL - 2.2 * K, far_x + sgn * 0.12 * K, FL, CHAIR)])
    else:
        solid_layer('parede', [rect(far_x, FL - 2.4 * K, far_x + sgn * 14, FL, WALL_C)])
tbp = next((p for p in PROPS if p.startswith('tableball')), None)
if tbp:
    s = tbp[-1] if tbp[-1] in 'LR' else 'R'
    RB = 0.2 * K
    gs = [grip(f, s) for f in range(N)]
    top = max(g_[1] for g_ in gs) + HG[s]['hw'] + 2 * RB
    x0 = gs[0][0] - 0.3 * K
    th = max(8.0, 0.04 * K)
    solid_layer('mesa', [rect(x0, top - FAR * 0.6, x0 + 0.8 * K, top, CHAIR_TOP), rect(x0, top, x0 + 0.8 * K, top + th, CHAIR),
                         rect(x0 + 0.05 * K, top + th, x0 + 0.05 * K + th * 0.7, FL, CHAIR_DK),
                         rect(x0 + 0.75 * K - th * 0.7, top + th, x0 + 0.75 * K, FL, CHAIR_DK)])
    moving_layer('bola', [ellipse(0, 0, RB, RB, SWISS_C, False, n=14)], [[g_[0], top - RB] for g_ in gs], at=NEAR_TOP, r_track=RB)
if PROPS:
    print('PROPS', sorted(PROPS), 'not drawn:', sorted(p for p in PROPS if p in {'throw'} or p.startswith('throw-')))

for l in comp['layers']:
    l['ip'], l['op'] = 0, N
d['ip'], d['op'] = 0, N
d['fr'] = 30
for l in d['layers']:
    l['ip'], l['op'] = 0, N
    l.pop('tm', None)  # the root's time remap would hold the comp on one frame
    freeze(l, T0)

# ---------- framing: the whole motion (arms overhead included) fits the canvas with a margin; the figure is
# never enlarged past the drawing's own size, so most moves keep the same scale
pts = []
for f in range(0, N, 2):
    SCL.clear()
    for s in 'LR':
        if scl_keys[f][s] != 1.0:
            SCL[I['dui %s 2' % s]] = scl_keys[f][s]
        if arm_scl_keys[f]['canh tay ' + s] != 1.0:
            SCL[I['canh tay ' + s]] = arm_scl_keys[f]['canh tay ' + s]
        if hand_scl_keys[f][s] != 1.0:
            SCL[I['ban tay ' + s]] = hand_scl_keys[f][s]
    pos_f = {I['than']: np.array(pos_keys[f][:2])}
    for i, l in L.items():
        if l.get('shapes') and not l.get('td'):
            pts += shape_points(l['shapes'], world(i, QA[f]['rot'], pos_f))
SCL.clear()
if PROP_PTS:
    pts = list(pts) + PROP_PTS
pts = np.array(pts)
x0_, y0_ = pts.min(0)
x1_, y1_ = pts.max(0)
root = next(l for l in d['layers'] if l.get('refId') == comp['id'])
rp = root['ks']['p']['k']; ra = root['ks']['a']['k']
W_, H_ = d['w'], d['h']
MT, MB, MS = 0.06 * H_, 0.05 * H_, 0.06 * W_
sc = min(1.0, (H_ - MT - MB) / (y1_ - y0_), (W_ - 2 * MS) / (x1_ - x0_))
# keep the drawing's own ground line where it was when the motion fits; otherwise anchor the bottom margin
base_y = rp[1] + (y1_ - ra[1])
py = min(base_y, H_ - MB) if sc >= 1.0 else H_ - MB
root['ks']['s'] = {'a': 0, 'k': [round(sc * 100, 3), round(sc * 100, 3), 100]}
root['ks']['a'] = {'a': 0, 'k': [round(float((x0_ + x1_) / 2), 2), round(float(y1_), 2), 0]}
root['ks']['p'] = {'a': 0, 'k': [W_ / 2, round(float(py), 2), 0]}
if TOP:
    # laid down: turned 90 deg counter-clockwise (head to the left), fitted to the canvas; no floor shadow
    sc = min(1.0, (W_ - 2 * MS) / (y1_ - y0_), (H_ - MT - MB) / (x1_ - x0_))
    root['ks']['s'] = {'a': 0, 'k': [round(sc * 100, 3), round(sc * 100, 3), 100]}
    root['ks']['a'] = {'a': 0, 'k': [round(float((x0_ + x1_) / 2), 2), round(float((y0_ + y1_) / 2), 2), 0]}
    root['ks']['p'] = {'a': 0, 'k': [W_ / 2, round(H_ * 0.52, 2), 0]}
    root['ks']['r'] = {'a': 0, 'k': -90}
    L[I['shadow']]['ks']['o'] = {'a': 0, 'k': 0}
print('FRAME scale', round(sc, 3), 'bbox', [round(float(v)) for v in (x0_, y0_, x1_, y1_)])


if KINETI:
    s = json.dumps(d)
    def c(h):
        return [round(int(h[i:i + 2], 16) / 255, 4) for i in (1, 3, 5)]

    def rec(o):
        if isinstance(o, dict):
            if o.get('ty') == 'fl' and isinstance(o.get('c', {}).get('k'), list) and not isinstance(o['c']['k'][0], dict):
                k = o['c']['k']
                hx = '#%02X%02X%02X' % tuple(round(v * 255) for v in k[:3])
                if hx in MAP:
                    o['c']['k'] = c(MAP[hx]) + k[3:]
            for v in o.values():
                rec(v)
        elif isinstance(o, list):
            for v in o:
                rec(v)
    MAP = {'#E96A2A': '#2563EB', '#CC5E28': '#1D4ED8'}
    rec(d)
json.dump(d, open(OUT, 'w'))
print('WROTE', OUT, N, 'frames')
