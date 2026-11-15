"""Front-view companion of drive_puppet.py: the same exercise seen from the front, by the same man.

    python3 drive_front.py <front_puppet.json> <joints.json> <action> <out.json> --kineti [--hands=auto|open|fist]
                           [--walk] [--props=a,b,...] [--match=<side lottie of the same move>] [--nothin] [--debughands]
    python3 drive_front.py --build-puppet <dinh jumping_jack.json> <front_puppet.json> [--height=711]

The puppet (front_puppet.json) is built once from Dinh Bui Xuan's "Jumping Jack" front-facing man (LottieFiles, Lottie
Simple License) and restyled as the side puppet's man (split-jump-dinh.json + drive_puppet --kineti): Kineti blue tank,
grey hair, the side puppet's skin tones, black shorts, dark sneakers with the orange sole line, and a hint of a face (two
brows, a nose shadow). Dinh drew the arm in one piece and the shoe as a missing bitmap: the arm is cut at the elbow
along its own outline, and the shoes are drawn here.

Every piece is a flat layer whose local +y runs from its proximal joint to its distal joint; each frame gets its
position, rotation and scale from a 2D forward chain:
  * projection on the frontal plane of the action: the camera looks along the figure's facing (median over the move),
    screen x = the figure's left (seen on the right), y = height;
  * angle of each piece = angle of its projected 3D segment; its length is scaled by projected/true 3D length
    (foreshortening), clamped, and the angle is held when the projection is too short to give a stable direction;
  * legs: FK in the air, near the floor the hip->ankle chain is rotated/scaled so the ankle lands on its support (the
    floor or a ground box of joints.json `_ground`) and a planted foot keeps its spot; on tiptoe the shoe is drawn
    taller down to the floor; body height follows the 3D hip joints;
  * hands (as drive_puppet): Dinh's relaxed open hand, a fist (running, --hands=fist, a held prop), or - when the 3D
    hand rests on a support (floor, ground box, a chair beside / in front, a table) - the palm flat on it, fingers along
    the support pointing away from the body, the arm reaching for it by 2-bone IK and the wrist pinned. A lying body
    with a planted hand (side plank) is turned a few degrees about its feet so the drawn arm reaches the floor;
  * layer order: arms behind the torso, or a copy in front of it while the hand/elbow is in front of the chest; the
    hand (and its forearm) over the head while in front of the face; the right leg over the left while it is nearer
    the camera (curtsy, crossover). Copies switch by hold keys with hysteresis; copies never drawn are left out;
  * lying moves (side plank, side-lying): one vertical shift puts what rests on the floor on it.
Props (the jobs.json names of render_mannequin.py, drive_puppet's code ported to the front view): see the equipment
section. All angle tracks are unwrapped (no blink) and single-frame reversals removed. Keys are thinned: a key that
linear interpolation reproduces within 0.3 px / 0.3 deg / 0.3 % is dropped (planted contacts within 0.1 px; --nothin
keeps every key); the pieces are parented to a null carrying the pelvis when that takes fewer keys. Auto-framing and
the QA line follow drive_puppet.
"""
import copy
import json
import math
import sys

import numpy as np

KIN_BLUE, KIN_BLUE_DK = '#2563EB', '#1D4ED8'   # drive_puppet --kineti


# ---------- Lottie helpers (as drive_puppet)
def lerp(a, b, u):
    if isinstance(a, dict):
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


def tr(ks):
    def g(k, dflt):
        v = ks.get(k)
        return dflt if v is None else v['k']
    p, a, s, r = g('p', [0, 0]), g('a', [0, 0]), g('s', [100, 100]), g('r', 0)
    r = r[0] if isinstance(r, list) else r
    return np.array(p[:2], float), np.array(a[:2], float), np.array(s[:2], float) / 100, float(r)


def mat(p, a, s, r):
    c, sn = math.cos(math.radians(r)), math.sin(math.radians(r))
    R = np.array([[c, -sn, 0], [sn, c, 0], [0, 0, 1]])  # y down: positive r turns clockwise on screen
    S = np.diag([s[0], s[1], 1])
    T = np.array([[1, 0, p[0]], [0, 1, p[1]], [0, 0, 1]])
    A = np.array([[1, 0, -a[0]], [0, 1, -a[1]], [0, 0, 1]])
    return T @ R @ S @ A


def ang(v):
    return math.degrees(math.atan2(v[1], v[0]))


def wdelta(v):
    return (v + 180) % 360 - 180


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


IDENT_TR = {'ty': 'tr', 'p': {'a': 0, 'k': [0, 0]}, 'a': {'a': 0, 'k': [0, 0]}, 's': {'a': 0, 'k': [100, 100]},
            'r': {'a': 0, 'k': 0}, 'o': {'a': 0, 'k': 100}, 'sk': {'a': 0, 'k': 0}, 'sa': {'a': 0, 'k': 0}}


def group(name, path, fill=None, stroke=None, width=1.6):
    it = [{'ty': 'sh', 'nm': 'path', 'ks': {'a': 0, 'k': path}}]
    if fill:
        it.append({'ty': 'fl', 'c': {'a': 0, 'k': fill if isinstance(fill, list) else hexc(fill)},
                   'o': {'a': 0, 'k': 100}, 'r': 1, 'nm': 'fill'})
    if stroke:
        it.append({'ty': 'st', 'c': {'a': 0, 'k': hexc(stroke)}, 'o': {'a': 0, 'k': 100}, 'w': {'a': 0, 'k': width},
                   'lc': 2, 'lj': 2, 'nm': 'stroke'})
    it.append(copy.deepcopy(IDENT_TR))
    return {'ty': 'gr', 'nm': name, 'it': it}


def bake(items, M):
    """Copy of a shape list with every group transform (and M) applied to the path vertices; group transforms reset."""
    out = []
    t = next((x for x in items if x.get('ty') == 'tr'), None)
    G = M @ mat(*tr(t)) if t is not None else M
    lin = G[:2, :2]
    flip = np.linalg.det(lin) < 0
    for x in items:
        ty = x.get('ty')
        if ty == 'gr':
            g = {k: v for k, v in x.items() if k != 'it'}
            g['it'] = bake(x['it'], G)
            out.append(g)
        elif ty == 'sh':
            k = x['ks']['k']
            k = k[0] if isinstance(k, list) else k
            v = [(G @ np.array([p[0], p[1], 1]))[:2] for p in k['v']]
            ii = [lin @ np.array(p[:2]) for p in k['i']]
            oo = [lin @ np.array(p[:2]) for p in k['o']]
            y = copy.deepcopy(x)
            y['ks'] = {'a': 0, 'k': {'c': k.get('c', True), 'v': [[round(float(a), 3) for a in p] for p in v],
                                     'i': [[round(float(a), 3) for a in p] for p in ii],
                                     'o': [[round(float(a), 3) for a in p] for p in oo]}}
            if flip:
                y['d'] = 3 if x.get('d', 1) != 3 else 1
            out.append(y)
        elif ty == 'tr':
            out.append(copy.deepcopy(IDENT_TR))
        else:
            out.append(copy.deepcopy(x))
    return out


def bez_points(shapes, M=np.eye(3), n=16):
    """Points along every bezier path of a shape list (group transforms applied)."""
    out = []
    t_ = next((x for x in shapes if x.get('ty') == 'tr'), None)
    G = M @ mat(*tr(t_)) if t_ is not None else M
    for sh in shapes:
        if sh.get('ty') == 'gr':
            out += list(bez_points(sh['it'], G, n))
        elif sh.get('ty') == 'sh':
            k = sh['ks']['k']
            k = k[0] if isinstance(k, list) else k
            v, ii, oo = np.array(k['v'], float), np.array(k['i'], float), np.array(k['o'], float)
            m = len(v)
            for j in range(m if k.get('c') else m - 1):
                p0, p3 = v[j], v[(j + 1) % m]
                p1, p2 = p0 + oo[j], p3 + ii[(j + 1) % m]
                for q in np.linspace(0, 1, n):
                    p = (1 - q) ** 3 * p0 + 3 * (1 - q) ** 2 * q * p1 + 3 * (1 - q) * q * q * p2 + q ** 3 * p3
                    out.append((G @ np.array([p[0], p[1], 1]))[:2])
    return np.array(out).reshape(-1, 2)


def scan(P, y):
    """Left/right x where the horizontal line y crosses the closed outline P (points in path order)."""
    a, b = P, np.roll(P, -1, axis=0)
    m = ((a[:, 1] - y) * (b[:, 1] - y) <= 0) & (np.abs(b[:, 1] - a[:, 1]) > 1e-9)
    if not m.any():
        return None
    t = (y - a[m, 1]) / (b[m, 1] - a[m, 1])
    xs = a[m, 0] + t * (b[m, 0] - a[m, 0])
    return float(xs.min()), float(xs.max())


def recolor(o, MAP):
    if isinstance(o, dict):
        if o.get('ty') in ('fl', 'st') and isinstance(o.get('c', {}).get('k'), list) and not isinstance(o['c']['k'][0], dict):
            k = o['c']['k']
            hx = '#%02X%02X%02X' % tuple(round(v * 255) for v in k[:3])
            if hx in MAP:
                o['c']['k'] = hexc(MAP[hx])[:3] + k[3:]
        for v in o.values():
            recolor(v, MAP)
    elif isinstance(o, list):
        for v in o:
            recolor(v, MAP)


def shape_layer(ind, nm, shapes, n_frames=1):
    return {'ddd': 0, 'ind': ind, 'ty': 4, 'nm': nm, 'sr': 1,
            'ks': {'o': {'a': 0, 'k': 100}, 'r': {'a': 0, 'k': 0}, 'p': {'a': 0, 'k': [0, 0, 0]},
                   'a': {'a': 0, 'k': [0, 0, 0]}, 's': {'a': 0, 'k': [100, 100, 100]}},
            'ao': 0, 'shapes': shapes, 'ip': 0, 'op': n_frames, 'st': 0, 'bm': 0}


# ======================================================================================================
# puppet build: Dinh's Jumping Jack man (frame 0, standing, arms down) -> front_puppet.json
# ======================================================================================================
SKIN, SKIN_DK, SKIN_SH = '#F7B29F', '#F29C91', '#E1918A'      # the side puppet's near skin, far skin, shading
HAIR = '#5A595E'
SHORTS, SHORTS_HI = '#161616', '#2A2B2A'
SHOE_UP, SHOE_SOLE, SHOE_LINE, SHOE_TONGUE = '#3A3C3B', '#262626', '#E26927', '#4A4C4B'
RESTYLE = {
    '#E1BD9E': SKIN, '#E2BD9F': SKIN, '#E2B48E': '#F4A796', '#D5A074': SKIN_SH, '#DDB28D': SKIN_DK,
    '#4A230F': HAIR, '#161213': SHORTS, '#BBBBBB': '#F1F2F2',
    '#D66227': KIN_BLUE, '#D66228': KIN_BLUE, '#C95728': '#2159E0', '#B43D26': KIN_BLUE_DK,
}
# the side figure, standing (split-jump frame 15, drawn size): head top to sole, px. The front man is scaled to it.
CX, FLOOR_Y = 1200.0, 1400.0


def build_puppet(src, out, side_height):
    d = json.load(open(src))
    A = {a['id']: a for a in d['assets'] if 'layers' in a}
    c0, c1 = A['comp_0'], A['comp_1']
    for c in (c0, c1):
        for l in c['layers']:
            freeze(l, 0)

    def world(comp, ind):
        Ls = {l['ind']: l for l in comp['layers']}
        l = Ls[ind]
        M = mat(*tr(l['ks']))
        return world(comp, l['parent']) @ M if l.get('parent') else M

    def pivot(M, l):
        return (M @ np.array([*tr(l['ks'])[1], 1]))[:2]

    L0 = {l['ind']: l for l in c0['layers']}
    L1 = {l['ind']: l for l in c1['layers']}
    torso = L0[1]
    Mt = world(c0, 1)
    tg = {g['nm']: g for g in torso['shapes'] if g.get('ty') == 'gr'}
    J = {}
    parts = {}          # piece -> list of baked groups (world coords)
    # legs: the mirrored precomp (2) is the figure's right leg (left on screen), precomp 3 its left
    for pre, s in ((2, 'R'), (3, 'L')):
        Mp = world(c0, pre)
        Mthigh = Mp @ world(c1, 1)
        Mshin = Mp @ world(c1, 3)
        Mshoe = Mp @ world(c1, 2)
        J['hip' + s] = pivot(Mthigh, L1[1])
        sg = {g['nm']: g for g in L1[3]['shapes'] if g.get('ty') == 'gr'}
        thigh_skin = bake([sg['Group 3']], Mshin)
        shin = bake([sg['Group 1']], Mshin)
        shorts_leg = bake(L1[1]['shapes'], Mthigh)
        P3, P1 = bez_points(thigh_skin), bez_points(shin)
        ky = (P3[:, 1].max() + P1[:, 1].min()) / 2 + 6
        row = P1[np.abs(P1[:, 1] - ky) < 8]
        J['knee' + s] = np.array([(row[:, 0].min() + row[:, 0].max()) / 2, ky])
        J['kneeW' + s] = float(row[:, 0].max() - row[:, 0].min())
        # the missing shoe bitmap: 32 x 50 around its anchor; the ankle a quarter down from its top
        c = (Mshoe @ np.array([16, 25, 1]))[:2]
        J['ankle' + s] = c + np.array([0.0, -50 * 0.22])
        yb = min(float(P1[:, 1].max()) - 6, float(J['ankle' + s][1]))
        bot = P1[np.abs(P1[:, 1] - yb) < 4]
        J['ankleW' + s] = float(bot[:, 0].max() - bot[:, 0].min())
        J['ankle' + s][0] = float(bot[:, 0].max() + bot[:, 0].min()) / 2      # the shoe centred under the shin
        parts['coxa ' + s] = thigh_skin
        parts['_shorts ' + s] = shorts_leg
        parts['perna ' + s] = shin
    # arms: one Dinh piece from shoulder to wrist, cut at the elbow below
    for ia, ih, s in ((6, 7, 'L'), (8, 9, 'R')):
        Ma, Mh = world(c0, ia), world(c0, ih)
        J['shoulder' + s] = pivot(Ma, L0[ia])
        J['wrist' + s] = pivot(Mh, L0[ih])
        parts['_arm ' + s] = bake(L0[ia]['shapes'], Ma)
        parts['mao ' + s] = bake(L0[ih]['shapes'], Mh)
    head_g = ['Group %d' % i for i in range(10, 18)]
    parts['quadril'] = bake([tg['Group 1']], Mt)
    parts['tronco'] = bake([g for nm, g in tg.items() if nm not in head_g and nm != 'Group 1'], Mt)
    parts['cabeca'] = bake([tg[nm] for nm in head_g], Mt)
    Ph = bez_points(parts['cabeca'])
    J['pelvis'] = (J['hipL'] + J['hipR']) / 2
    J['headpivot'] = np.array([float(Ph[:, 0].mean()), float(Ph[:, 1].max()) - 4])
    J['headtop'] = np.array([float(Ph[:, 0].mean()), float(Ph[:, 1].min())])
    J['neck'] = np.array([float(J['pelvis'][0]), (J['shoulderL'][1] + J['shoulderR'][1]) / 2 - 6])
    # the elbow sits where the 3D rig has it along the arm (upper arm 0.29 m, forearm 0.25 m)
    for s in 'LR':
        J['elbow' + s] = J['shoulder' + s] + (J['wrist' + s] - J['shoulder' + s]) * (0.29 / 0.54)

    # scale everything to the side figure's height
    allp = np.vstack([bez_points(v) for v in parts.values()])
    top = float(allp[:, 1].min())
    sole = float(max(J['ankleL'][1], J['ankleR'][1])) + 50 * 0.78
    sc = side_height / (sole - top)
    # comp coordinates: the floor at y = FLOOR_Y, the pelvis at x = CX (a large precomp, so nothing is clipped)
    off = np.array([CX - J['pelvis'][0] * sc, FLOOR_Y - sole * sc])
    S = np.array([[sc, 0, off[0]], [0, sc, off[1]], [0, 0, 1.0]])
    parts = {k: bake(v, S) for k, v in parts.items()}
    J = {k: (v * sc + off if isinstance(v, np.ndarray) and v.shape == (2,) else v * sc) for k, v in J.items()}
    # hair: the side man's hair has volume on top (a quiff); Dinh's front cap is thin. A grey dome behind the head,
    # rising above the scalp, keeps Dinh's hairline and gives the side figure's silhouette.
    Ph = bez_points(parts['cabeca'])
    hx0, hx1, hy0 = float(Ph[:, 0].min()), float(Ph[:, 0].max()), float(Ph[:, 1].min())
    hh = float(Ph[:, 1].max() - hy0)
    hc = (hx0 + hx1) / 2
    hw = (hx1 - hx0) / 2
    ear = hy0 + 0.42 * hh
    dome = []
    for t in np.linspace(180, 360, 15):            # a round, full crown above the scalp (superellipse)
        c_, s_ = math.cos(math.radians(t)), math.sin(math.radians(t))
        x_ = math.copysign(abs(c_) ** (2 / 2.8), c_)
        y_ = -abs(s_) ** (2 / 2.8)
        lift = 0.04 * math.exp(-((t - 300) / 22) ** 2)             # the quiff, a little off centre like the side's
        dome.append((hc + hw * 1.03 * x_, hy0 + 0.34 * hh + (0.50 + lift) * hh * y_))
    dome = [(hc - hw * 0.95, ear)] + dome[1:-1] + [(hc + hw * 0.95, ear), (hc, hy0 + 0.30 * hh)]
    parts['cabeca'] = parts['cabeca'] + [group('cabelo', smooth_path(dome), fill=hexc('#4A230F'))]
    # a hint of a face, as little as the side puppet shows (its nose line and brow): two short brows in the hair
    # colour and a soft nose shadow in the shading tone. Units: u down from Dinh's head top in head heights (hh),
    # v across from the centre in half widths (hw, ears included).
    fy = lambda u: hy0 + u * hh
    face = []
    for sd in (-1.0, 1.0):
        brow = [(hc + sd * hw * v, fy(u)) for v, u in ((0.17, 0.392), (0.30, 0.362), (0.46, 0.358), (0.57, 0.382),
                                                       (0.46, 0.392), (0.30, 0.400))]
        face.append(group('sobrancelha', smooth_path(brow), fill=hexc('#4A230F')))
    nose = [(hc + hw * v, fy(u)) for v, u in ((0.03, 0.43), (0.07, 0.56), (0.095, 0.635), (0.0, 0.66), (-0.095, 0.635),
                                              (-0.05, 0.615), (0.015, 0.56), (-0.005, 0.45))]
    face.append(group('nariz', smooth_path(nose), fill=hexc('#D5A074')))
    parts['cabeca'] = face + parts['cabeca']
    print('BUILD scale', round(sc, 3), 'height', round(side_height, 1))

    pieces = {}

    def put(nm, origin, axis, groups, length):
        """Groups (world px) -> piece-local coords: origin at the joint, local +y along `axis` (degrees)."""
        r = axis - 90.0
        M = mat(np.zeros(2), np.zeros(2), np.ones(2), -r) @ np.array([[1, 0, -origin[0]], [0, 1, -origin[1]], [0, 0, 1]])
        pieces[nm] = {'origin': [float(origin[0]), float(origin[1])], 'axis': float(axis), 'len': float(length),
                      'shapes': bake(groups, M)}

    def seg(a, b):
        return ang(J[b] - J[a]), float(np.linalg.norm(J[b] - J[a]))

    # the seat ends at the crotch: Dinh's two lobes below it hang under the thighs once they splay (squat, jacks);
    # the shorts' legs (on the thighs) draw that part instead
    Pq = bez_points(parts['quadril'], np.eye(3), 24)
    cxq = float(J['pelvis'][0])
    yc = scan(Pq[:, ::-1], cxq)                  # vertical line through the centre: (top y, bottom y)
    apex = yc[1] if yc else float(J['pelvis'][1]) + 20
    Pq = Pq[::3].copy()
    Pq[:, 1] = np.minimum(Pq[:, 1], apex + 2.0)
    keep = [Pq[0]] + [p_ for i_, p_ in enumerate(Pq[1:]) if np.linalg.norm(p_ - Pq[i_]) > 1.0]
    parts['quadril'] = [group('calcao', smooth_path(keep), fill=hexc('#161213'))]
    put('quadril', J['pelvis'], 0.0, parts['quadril'], float(np.linalg.norm(J['hipL'] - J['hipR'])))
    a_, l_ = seg('pelvis', 'neck')
    put('tronco', J['pelvis'], a_, parts['tronco'], l_)
    put('cabeca', J['headpivot'], -90.0, parts['cabeca'], float(J['headpivot'][1] - J['headtop'][1]))
    for s in 'LR':
        a_, l_ = seg('hip' + s, 'knee' + s)
        # the shorts' leg: Dinh's piece rises above the hip joint and, once the thigh turns out (squat, jacks), that
        # part swings in under the crotch. Redrawn from its own outline below the joint, with a round top centred
        # on the joint (it then stays put however the thigh turns).
        r_ = a_ - 90.0
        Mh = mat(np.zeros(2), np.zeros(2), np.ones(2), -r_) @ np.array([[1, 0, -J['hip' + s][0]], [0, 1, -J['hip' + s][1]], [0, 0, 1]])
        Ps = bez_points(parts['_shorts ' + s], Mh, 40)
        ys1 = float(Ps[:, 1].max())
        Ls_, Rs_ = [], []
        for y in np.linspace(0.0, ys1 - 1.0, 14):
            sc_ = scan(Ps, y)
            if sc_:                                  # 2.5 px wider each side: the two legs overlap at the seam
                Ls_.append([sc_[0] - 2.5, float(y)])
                Rs_.append([sc_[1] + 2.5, float(y)])
        hw_, hc_ = (Rs_[0][0] - Ls_[0][0]) / 2, (Rs_[0][0] + Ls_[0][0]) / 2
        top = [[hc_ + hw_ * math.cos(math.radians(t)), hw_ * math.sin(math.radians(t))] for t in np.linspace(180, 360, 9)][1:-1]
        hem = [[Rs_[-1][0] * (1 - u) + Ls_[-1][0] * u, ys1 + 3.0 * math.sin(math.pi * u)] for u in (0.25, 0.5, 0.75)]
        outline = top + Rs_ + hem + Ls_[::-1]
        backh = np.linalg.inv(Mh)
        ow = [(backh @ np.array([x, y, 1]))[:2] for x, y in outline]
        put('coxa ' + s, J['hip' + s], a_, [group('calcao', smooth_path(ow), fill=hexc('#161213'))] + parts['coxa ' + s], l_)
        a_, l_ = seg('knee' + s, 'ankle' + s)
        put('perna ' + s, J['knee' + s], a_, parts['perna ' + s], l_)
        # the arm cut at the elbow: left/right edges of Dinh's outline, a round cap at the cut on each half
        a_, l_ = seg('shoulder' + s, 'wrist' + s)
        r = a_ - 90.0
        M = mat(np.zeros(2), np.zeros(2), np.ones(2), -r) @ np.array([[1, 0, -J['shoulder' + s][0]], [0, 1, -J['shoulder' + s][1]], [0, 0, 1]])
        P = bez_points(parts['_arm ' + s], M, 40)
        el = float(np.linalg.norm(J['elbow' + s] - J['shoulder' + s]))
        y0, y1 = float(P[:, 1].min()) + 1.5, float(P[:, 1].max()) - 0.5

        def edges(ya, yb, n):
            L_, R_ = [], []
            for y in np.linspace(ya, yb, n):
                sc_ = scan(P, y)
                if sc_ is None:
                    continue
                L_.append([sc_[0], float(y)])
                R_.append([sc_[1], float(y)])
            return L_, R_

        def cap(cx, cy, rad, a0, a1, n=6):
            return [[cx + rad * math.cos(math.radians(t)), cy + rad * math.sin(math.radians(t))] for t in np.linspace(a0, a1, n)]
        Lu, Ru = edges(y0, el, 14)
        we = (Ru[-1][0] - Lu[-1][0]) / 2
        ce = (Ru[-1][0] + Lu[-1][0]) / 2
        J['elbowW' + s] = 2 * we
        upper = Ru + cap(ce, el, we, 0, 180)[1:-1] + Lu[::-1]
        Lf, Rf = edges(el, y1, 12)
        fore = cap(ce, el, we, 180, 360)[1:-1] + Rf + Lf[::-1]
        J['wristW' + s] = Rf[-1][0] - Lf[-1][0]
        skin = hexc('#E1BD9E')
        back = np.linalg.inv(M)
        up_w = [(back @ np.array([x, y, 1]))[:2] for x, y in upper]
        fo_w = [(back @ np.array([x, y, 1]))[:2] for x, y in fore]
        a_u, l_u = seg('shoulder' + s, 'elbow' + s)
        put('braco ' + s, J['shoulder' + s], a_u, [group('braco', smooth_path(up_w), fill=skin)], l_u)
        # the copy drawn over the torso ends in a round cap on the joint: Dinh's deltoid top would show on the chest
        L2, R2 = edges(0.0, el, 12)
        ws, cs = (R2[0][0] - L2[0][0]) / 2, (R2[0][0] + L2[0][0]) / 2
        up2 = cap(cs, 0.0, ws, 180, 360, 9)[1:-1] + R2 + cap(ce, el, we, 0, 180)[1:-1] + L2[::-1]
        up2_w = [(back @ np.array([x, y, 1]))[:2] for x, y in up2]
        put('braco ' + s + ' rc', J['shoulder' + s], a_u, [group('braco', smooth_path(up2_w), fill=skin)], l_u)
        a_f, l_f = seg('elbow' + s, 'wrist' + s)
        put('antebraco ' + s, J['elbow' + s], a_f, [group('antebraco', smooth_path(fo_w), fill=skin)], l_f)
        # relaxed hand, palm towards the thigh: seen from the front, its thumb edge. It starts on the forearm's
        # own edges a little above the wrist (so the wrist cannot gap), widens to the palm, rounds at the fingertips
        wy = el + (y1 - el) * 0.80
        row = [p_ for p_ in zip(Lf, Rf) if p_[0][1] <= wy]
        (xl, _), (xr, _) = row[-1]
        ww = xr - xl
        hl = 0.62 * l_f
        md = -1.0 if s == 'L' else 1.0                 # towards the body's midline (the thumb side seen from the front)
        loc = lambda u, v: (back @ np.array([(xl + xr) / 2 + md * u * ww / 2, wy + v * hl, 1]))[:2]
        hand = [loc(-1.0, -0.10), loc(-1.12, 0.28), loc(-1.08, 0.60), loc(-0.82, 0.88), loc(-0.30, 1.0), loc(0.25, 0.94),
                loc(0.60, 0.72), loc(0.84, 0.42), loc(1.04, 0.18), loc(1.0, -0.10), loc(0.0, -0.16)]
        thumb = [loc(0.55, 0.10), loc(0.98, 0.20), loc(0.88, 0.50), loc(0.62, 0.60), loc(0.50, 0.32)]
        crease = [loc(0.48, 0.22), loc(0.62, 0.30), loc(0.60, 0.56), loc(0.52, 0.40)]
        J['wristW' + s] = ww
        put('mao ' + s, J['wrist' + s], a_f, [group('vinco', smooth_path(crease), fill=hexc('#DDB28D')),
                                              group('polegar', smooth_path(thumb), fill=skin),
                                              group('mao', smooth_path(hand), fill=skin)], hl)
        # shoe, seen from the front: collar, toe box, the orange line and the sole (the side puppet's colours)
        an = J['ankle' + s]
        h = float(FLOOR_Y - an[1])
        w = J['ankleW' + s] * 1.85                 # full width of the toe box
        side = 1.0 if s == 'L' else -1.0           # toes turn slightly out
        q = lambda x, y: [x * w / 2 + side * 0.05 * w * max(0.0, y - 0.45), y * h]
        # low sneaker seen from the toes: a narrow collar round the ankle, the toe box widening to the floor,
        # the orange line and the dark sole as rounded bands (as on the side puppet's shoe)
        # (a low shoe like the side's: the ankle shows above the collar, drawn on the shoe layer so the shin cannot gap)
        aw = J['ankleW' + s] / w
        ankle_skin = [q(-aw * 0.96, -0.20), q(aw * 0.96, -0.20), q(aw * 0.92, 0.45), q(-aw * 0.92, 0.45)]
        upper_pts = [q(-0.72, 0.30), q(0.0, 0.24), q(0.72, 0.30), q(0.88, 0.50), q(0.98, 0.70), q(0.95, 0.86),
                     q(0.0, 0.90), q(-0.95, 0.86), q(-0.98, 0.70), q(-0.88, 0.50)]
        tongue = [q(-0.26, 0.28), q(0.26, 0.28), q(0.32, 0.52), q(0.0, 0.60), q(-0.32, 0.52)]
        line = [q(-1.0, 0.76), q(0.0, 0.80), q(1.0, 0.76), q(1.02, 0.87), q(0.0, 0.90), q(-1.02, 0.87)]
        solep = [q(-1.02, 0.85), q(0.0, 0.88), q(1.02, 0.85), q(0.98, 1.0), q(0.0, 1.0), q(-0.98, 1.0)]
        g_sole = group('sola', smooth_path(solep), fill=SHOE_SOLE)
        g_line = group('faixa', smooth_path(line), fill=SHOE_LINE)
        g_up = group('cabedal', smooth_path(upper_pts), fill=SHOE_UP)
        g_to = group('lingua', smooth_path(tongue), fill=SHOE_TONGUE)
        pieces['pe ' + s] = {'origin': [float(an[0]), float(an[1])], 'axis': 90.0, 'len': h,
                             'shapes': [g_to, g_line, g_sole, g_up,
                                        group('tornozelo', smooth_path(ankle_skin), fill=hexc('#E1BD9E'))]}
        # joint discs between pieces (the pieces scale along their length; the discs keep the joint round)
        pieces['joelho ' + s] = {'origin': [float(J['knee' + s][0]), float(J['knee' + s][1])], 'axis': 90.0, 'len': 0.0,
                                 'shapes': [group('disco', smooth_path(cap(0, 0, J['kneeW' + s] * 0.40, 0, 360, 13)[:-1]), fill=skin)]}
        pieces['cotovelo ' + s] = {'origin': [float(J['elbow' + s][0]), float(J['elbow' + s][1])], 'axis': 90.0, 'len': 0.0,
                                   'shapes': [group('disco', smooth_path(cap(0, 0, J['elbowW' + s] * 0.34, 0, 360, 13)[:-1]), fill=skin)]}
    recolor(pieces, RESTYLE)
    # z order, top first. The arms have a copy in front of the torso (switched on while the hand is in front of it)
    order = ['mao L', 'antebraco L', 'braco L', 'cotovelo L', 'mao R', 'antebraco R', 'braco R', 'cotovelo R']
    # the shorts' legs (on the thighs) over the seat: in a squat the seat's crotch would hang below them
    order = ['cabeca'] + [o + ' +' for o in order] + ['tronco', 'coxa L', 'coxa R', 'quadril'] + order + \
        ['pe L', 'perna L', 'joelho L', 'pe R', 'perna R', 'joelho R']
    floor_y = FLOOR_Y
    W_, H_ = 985, 885            # the side puppet's canvas
    layers = []
    for i, nm in enumerate(order):
        base = nm[:-2] if nm.endswith(' +') else nm
        pc = pieces[base]
        alt = pieces.get(base + ' rc') if nm.endswith(' +') else None
        l = shape_layer(i + 1, nm, copy.deepcopy((alt or pc)['shapes']))
        l['ks']['p']['k'] = [pc['origin'][0], pc['origin'][1], 0]
        l['ks']['r']['k'] = pc['axis'] - 90.0
        if nm.endswith(' +'):
            l['ks']['o']['k'] = 0
        layers.append(l)
    shadow = shape_layer(len(layers) + 1, 'shadow', [group('shadow', smooth_path(cap(0, 0, 1.0, 0, 360, 17)[:-1]), fill='#F1F2F2')])
    shadow['ks']['p']['k'] = [float(J['pelvis'][0]), floor_y + 6, 0]
    shadow['ks']['s']['k'] = [110, 16, 100]
    layers.append(shadow)
    allp = np.vstack([bez_points(pc['shapes'], mat(np.array(pc['origin']), np.zeros(2), np.ones(2), pc['axis'] - 90)) for pc in pieces.values()])
    cx = float((allp[:, 0].min() + allp[:, 0].max()) / 2)
    comp = {'id': 'comp_0', 'layers': layers}
    root = {'ddd': 0, 'ind': 1, 'ty': 0, 'nm': 'front', 'refId': 'comp_0', 'sr': 1,
            'ks': {'o': {'a': 0, 'k': 100}, 'r': {'a': 0, 'k': 0}, 'p': {'a': 0, 'k': [W_ / 2, H_ - 0.08 * H_, 0]},
                   'a': {'a': 0, 'k': [cx, floor_y, 0]}, 's': {'a': 0, 'k': [100, 100, 100]}},
            'ao': 0, 'w': int(2 * CX), 'h': int(FLOOR_Y + 300), 'ip': 0, 'op': 1, 'st': 0, 'bm': 0}
    rig = {'pieces': {k: {kk: vv for kk, vv in v.items() if kk != 'shapes'} for k, v in pieces.items() if not k.endswith(' rc')},
           'joints': {k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in J.items()},
           'floor_y': floor_y, 'order': order,
           'source': 'Dinh Bui Xuan, "Jumping Jack" (LottieFiles, Lottie Simple License), restyled'}
    solid = {'ddd': 0, 'ind': 2, 'ty': 1, 'nm': 'White Solid', 'sr': 1, 'sc': '#ffffff', 'sw': W_, 'sh': H_,
             'ks': {'o': {'a': 0, 'k': 100}, 'r': {'a': 0, 'k': 0}, 'p': {'a': 0, 'k': [W_ / 2, H_ / 2, 0]},
                    'a': {'a': 0, 'k': [W_ / 2, H_ / 2, 0]}, 's': {'a': 0, 'k': [100, 100, 100]}},
             'ao': 0, 'ip': 0, 'op': 1, 'st': 0, 'bm': 0}
    out_d = {'v': '5.7.4', 'fr': 30, 'ip': 0, 'op': 1, 'w': W_, 'h': H_, 'nm': 'kineti front puppet', 'ddd': 0,
             'assets': [comp], 'layers': [root, solid], 'kineti_rig': rig}
    json.dump(out_d, open(out, 'w'))
    print('WROTE', out, len(layers), 'layers; joints', {k: [round(x) for x in v] if isinstance(v, np.ndarray) else round(v, 1) for k, v in J.items()})


if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == '--build-puppet':
    h = float(next((a.split('=')[1] for a in sys.argv if a.startswith('--height=')), 711))
    build_puppet(sys.argv[2], sys.argv[3], h)
    sys.exit(0)

# ======================================================================================================
# driving
# ======================================================================================================
SRC, JOINTS, ACT, OUT = sys.argv[1:5]
KINETI = '--kineti' in sys.argv          # the front puppet is already in the Kineti colours; kept for the shared CLI
WALK = '--walk' in sys.argv
PROPS = set()
for _a in sys.argv:
    if _a.startswith('--props='):
        PROPS |= set(_a.split('=', 1)[1].replace('+', ',').split(','))
PROPS.discard('')
HANDS = next((a.split('=')[1] for a in sys.argv if a.startswith('--hands=')), 'auto')
# (as drive_puppet) running moves make fists, unless the palms are on a ball; held props close the hand that holds
RUN = ('jog', 'run', 'sprint', 'march', 'high-knee', 'butt-kick', 'skater', 'punch', 'box')
_open_props = any(p_ in ('heldball', 'waistball') or p_.startswith(('pball-v-h', 'wallpress-h', 'tableball', 'wallat-h'))
                  for p_ in PROPS)
if HANDS == 'auto' and any(w in ACT for w in RUN) and not _open_props:
    HANDS = 'fist'
HELD = {'dumbbell', 'bandhands', 'bandanchor', 'bandanchor1', 'bandfeet', 'stick', 'walker', 'walkergo', 'pulley'}


def grips(s_):
    """Hand s_ holds something (render_mannequin.grips): a handle prop, a cane on that side, a band/towel/stick end."""
    if PROPS & HELD or 'cane' + s_ in PROPS:
        return True
    return any(p_.startswith(('band-', 'towel-', 'stick-', 'stickend-', 'stickfloor-')) and 'h' + s_ in p_.split('-')[1:]
               for p_ in PROPS)


FIST = {s_: HANDS == 'fist' or (HANDS == 'auto' and grips(s_)) for s_ in 'LR'}
print('HANDS', HANDS, {s_: 'fist' if FIST[s_] else 'open' for s_ in 'LR'})

d = json.load(open(SRC))
comp = d['assets'][0]
RIG = d.pop('kineti_rig')
PC = RIG['pieces']
JR = {k: (np.array(v, float) if isinstance(v, list) else v) for k, v in RIG['joints'].items()}
FLOOR_PX = float(RIG['floor_y'])
LAY = {l['nm']: l for l in comp['layers']}


def base_of(nm):
    """Layer name -> the piece it draws ('mao L +' in front of the torso, 'mao L ^' over the head, 'coxa R ^' over
    the other leg are copies of 'mao L' / 'coxa R')."""
    return nm[:-2] if nm.endswith((' +', ' ^')) else nm


# ---------- extra copies for the layer order: a leg crossing in front of the other, a hand in front of the face
def add_copy(src_nm, new_nm, above):
    lay = copy.deepcopy(LAY[src_nm])
    lay['nm'] = new_nm
    lay['ks']['o'] = {'a': 0, 'k': 0}
    k = next(i for i, l in enumerate(comp['layers']) if l['nm'] == above)
    comp['layers'].insert(k, lay)
    LAY[new_nm] = lay


for _nm in ('coxa R',):                                  # the right thigh over the left one
    add_copy(_nm, _nm + ' ^', 'coxa L')
for _nm in ('pe R', 'perna R', 'joelho R'):              # the right shin and shoe over the left ones
    add_copy(_nm, _nm + ' ^', 'pe L')
for _s in 'LR':                                          # hand and forearm over the head
    add_copy('mao ' + _s, 'mao %s ^' % _s, 'cabeca')
    add_copy('antebraco ' + _s, 'antebraco %s ^' % _s, 'cabeca')
    add_copy('cotovelo ' + _s, 'cotovelo %s ^' % _s, 'cabeca')
for _i, _l in enumerate(comp['layers']):
    _l['ind'] = _i + 1


# ---------- hands: Dinh's relaxed open hand (built in the puppet), a fist, the palm flat on a support
def wrap_g(name, items):
    """A group whose transform (opacity, mirror) can be keyed; it pivots on the layer's origin (the wrist)."""
    return {'ty': 'gr', 'nm': name, 'it': items + [copy.deepcopy(IDENT_TR)]}


def line_g(name, pts, color, width, closed=False):
    it = [{'ty': 'sh', 'nm': 'path', 'ks': {'a': 0, 'k': smooth_path(pts, closed)}},
          {'ty': 'st', 'c': {'a': 0, 'k': hexc(color)}, 'o': {'a': 0, 'k': 100}, 'w': {'a': 0, 'k': width},
           'lc': 2, 'lj': 2, 'nm': 'stroke'}, copy.deepcopy(IDENT_TR)]
    return {'ty': 'gr', 'nm': name, 'it': it}


HG = {}
for _s in 'LR':
    # the wrist, from the drawn forearm (local: origin at the elbow, +y towards the wrist): its centre and half width
    _pf = bez_points(LAY['antebraco ' + _s]['shapes'])
    _fl = PC['antebraco ' + _s]['len']
    _row = _pf[np.abs(_pf[:, 1] - (_fl - 4.0)) < 5.0]
    _cx = float((_row[:, 0].min() + _row[:, 0].max()) / 2)
    _hw = float((_row[:, 0].max() - _row[:, 0].min()) / 2)
    _po = bez_points(LAY['mao ' + _s]['shapes'])
    HG[_s] = dict(cx=_cx, hw=_hw, hl=PC['mao ' + _s]['len'], md=-1.0 if _s == 'L' else 1.0,
                  y1=float(_po[:, 1].max()))


def hand_shapes(s):
    """The fist and the flat hand in the hand layer's frame (origin at the wrist, +y along the hand), the skin and
    shading of the open hand. Both start with a round wrist cap on the forearm's end, so the joint stays closed.
      fist:  seen from the thumb side (hanging arm, palm to the thigh): the curled fingers a little wider than the
             wrist, the thumb wrapped over the front, two finger-curl lines;
      flat:  the hand lying palm down on a support, fingers along +y, the palm on the local -x side (local +x is up
             when the fingers point to the right; the group is mirrored for fingers to the left)."""
    g = HG[s]
    hw, hl, md = g['hw'], g['hl'], g['md']
    cx = 0.0                                               # (every hand drawing is centred on the wrist: see below)
    Q = lambda u, v: (cx + md * u * hw, v * hl)            # u across (thumb side +), v along the hand
    capc = [(cx + hw * 0.97 * math.cos(a_), hw * 0.97 * math.sin(a_)) for a_ in np.linspace(0, 2 * math.pi, 12, endpoint=False)]
    cap = group('pulso', smooth_path(capc), fill=SKIN)
    fist = [Q(-1.0, -0.10), Q(-1.10, 0.10), Q(-1.16, 0.30), Q(-1.02, 0.47), Q(-0.55, 0.57), Q(0.10, 0.58), Q(0.70, 0.52),
            Q(1.10, 0.38), Q(1.22, 0.20), Q(1.08, 0.02), Q(1.0, -0.10), Q(0.0, -0.16)]
    thumb = [Q(0.30, 0.06), Q(0.95, 0.10), Q(1.20, 0.24), Q(1.02, 0.38), Q(0.55, 0.40), Q(0.22, 0.30), Q(0.16, 0.16)]
    curls = [line_g('dedo', [Q(-1.02, 0.30), Q(-0.40, 0.33), Q(0.15, 0.36)], SKIN_SH, 1.3),
             line_g('dedo', [Q(-0.98, 0.44), Q(-0.40, 0.48), Q(0.25, 0.50)], SKIN_SH, 1.3),
             line_g('polegar', [Q(0.22, 0.30), Q(0.55, 0.40), Q(1.02, 0.38)], SKIN_SH, 1.2)]
    fist_g = curls + [group('polegar', smooth_path(thumb), fill=SKIN), group('punho', smooth_path(fist), fill=SKIN), cap]
    # flat: in (along the hand, across: + up) units of the hand length Lh and the wrist half width, as drive_puppet's
    # flat hand; the heel of the hand reaches the support Dn below the wrist pivot
    Lh = 1.05 * hl
    Dn = 1.04 * hw
    wb = -Dn
    F = lambda sv, wv: (wv, sv)
    flat_pts = [(-0.55 * hw, wb + 0.25 * hw), (-hw, 0.0), (-0.7 * hw, 0.7 * hw), (0.0, hw),
                (0.2 * Lh, 0.96 * hw), (0.4 * Lh, 0.66 * hw), (0.55 * Lh, 0.56 * hw), (0.74 * Lh, 0.22 * hw),
                (0.92 * Lh, wb + 0.95 * hw), (1.03 * Lh, wb + 0.48 * hw), (1.0 * Lh, wb + 0.04 * hw),
                (0.62 * Lh, wb), (0.25 * Lh, wb), (0.05 * Lh, wb)]
    flat_l = [line_g('dedo', [F(0.6 * Lh, 0.3 * hw), F(0.78 * Lh, wb + 1.02 * hw), F(0.94 * Lh, wb + 0.62 * hw)], SKIN_SH, 1.4),
              line_g('dedo', [F(0.6 * Lh, wb + 0.55 * hw), F(0.8 * Lh, wb + 0.5 * hw), F(0.95 * Lh, wb + 0.36 * hw)], SKIN_SH, 1.3),
              line_g('polegar', [F(0.12 * Lh, 0.55 * hw), F(0.3 * Lh, 0.38 * hw), F(0.46 * Lh, 0.12 * hw)], SKIN_SH, 1.3)]
    flatc = [(hw * 0.97 * math.cos(a_), hw * 0.97 * math.sin(a_)) for a_ in np.linspace(0, 2 * math.pi, 12, endpoint=False)]
    flat_g = flat_l + [group('palma', smooth_path([F(*p_) for p_ in flat_pts]), fill=SKIN),
                       group('pulso', smooth_path(flatc), fill=SKIN)]
    g.update(Dn=Dn, Lh=Lh, grip=np.array([cx + md * 0.05 * hw, 0.27 * hl]), palm=np.array([cx, 0.42 * hl]))
    return fist_g, flat_g


for _s in 'LR':
    _fist, _flat = hand_shapes(_s)
    for _nm in ('mao ' + _s, 'mao %s +' % _s, 'mao %s ^' % _s):
        # the layer's origin moves to the centre of the forearm's end (chain()), so the hand turns about the wrist
        _sh = bake(LAY[_nm]['shapes'], np.array([[1, 0, -HG[_s]['cx']], [0, 1, 0], [0, 0, 1.0]]))
        LAY[_nm]['shapes'] = [wrap_g('mao aberta', _sh), wrap_g('punho', copy.deepcopy(_fist)),
                              wrap_g('mao apoiada', copy.deepcopy(_flat))]
SHAPES = {nm: l['shapes'] for nm, l in LAY.items()}
print('HAND GEOM', {s_: {k: round(float(v), 1) for k, v in HG[s_].items() if np.ndim(v) == 0} for s_ in 'LR'})


def rot2(deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return np.array([[c, -s], [s, c]])


def dirv(deg):
    return np.array([math.cos(math.radians(deg)), math.sin(math.radians(deg))])


def local_pt(piece, world_rest):
    """A rest-pose point of the drawing in a piece's local frame (origin at its joint, +y along it)."""
    pc = PC[piece]
    return rot2(-(pc['axis'] - 90.0)) @ (np.asarray(world_rest, float) - np.array(pc['origin']))


def place(pose, local):
    """Local point of a piece -> world px, for a pose (origin, angle, sx, sy)."""
    o, a, sx, sy = pose
    return np.array(o) + rot2(a - 90.0) @ (np.array([sx, sy]) * local)


def layer_matrix(pose):
    o, a, sx, sy = pose
    return mat(np.array(o, float), np.zeros(2), np.array([sx, sy]), a - 90.0)


# ---------- the 3D motion
J = json.load(open(JOINTS))
frames = J[ACT]
# a lying move rotated upright by top_view.py: drawn as seen from above, laid back down (head left) at the end
TOP = (J.get('_top') or {}).get(ACT)
if TOP:
    print('TOP VIEW', 'supine' if TOP['sky'] > 0 else 'prone')


def smooth_frames(frames, sigma=1.2):
    """As drive_puppet: light cyclic Gaussian smoothing of the joints (hides the builder's one-frame pops)."""
    names = [b for b in frames[0] if not b.startswith('_')]
    A_ = np.array([[frames[f][b] for b in names] for f in range(len(frames))], float)
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
N = len(frames)


def jp(fr, b, tail=False):
    return np.array(fr[b][1 if tail else 0], float)


def hipc(fr):
    return (jp(fr, 'legL') + jp(fr, 'legR')) / 2


def facing(fr):
    lat = (jp(fr, 'armL') - jp(fr, 'armR')) + 2 * (jp(fr, 'legL') - jp(fr, 'legR'))
    up = jp(fr, 'neck') - hipc(fr)
    f = np.cross(lat, up)
    return f / (np.linalg.norm(f) + 1e-9)


# the camera looks at the figure's front: the facing of the move, horizontal (a side-lying body faces the camera too)
_fs = np.array([facing(fr) for fr in frames])
CAM = _fs.sum(0)
CAM[2] = 0
if np.linalg.norm(CAM) < 0.3 * N:          # prone/supine: the chest faces the floor or the sky; use the shoulders' line
    _lat = sum(jp(fr, 'armL') - jp(fr, 'armR') for fr in frames)
    CAM = np.cross(_lat, [0, 0, 1])
CAM = CAM / np.linalg.norm(CAM)
XS = np.cross([0.0, 0.0, 1.0], CAM)          # the figure's left, seen on the right of the screen
XS /= np.linalg.norm(XS)
print('CAMERA', np.round(CAM, 2), 'screen x', np.round(XS, 2))


def P(v, xs=None):
    """Frontal projection, metres: x = towards the figure's left (screen right), y down."""
    return np.array([float(np.dot(v, XS if xs is None else xs)), -float(v[2])])


def depth(v):
    return float(np.dot(v, CAM))


R0 = J['rest']
XS_REST = np.array([1.0, 0.0, 0.0])          # the rig's rest pose faces -Y: its left is +X


def L3(a, b):
    return float(np.linalg.norm(jp(R0, b) - jp(R0, a)))


SEG3 = {'braco': ('arm', 'elbow'), 'antebraco': ('elbow', 'hand'), 'coxa': ('leg', 'knee'), 'perna': ('knee', 'foot')}
LEN3 = {k + ' ' + s: L3(a + s, b + s) for k, (a, b) in SEG3.items() for s in 'LR'}
LEN3['tronco'] = float(np.linalg.norm(jp(R0, 'neck') - hipc(R0)))
LEN3['quadril'] = L3('legR', 'legL')
LEN3['ombros'] = L3('armR', 'armL')

# floor and contacts (as drive_puppet: the lowest mesh point of each foot / hand). The supports the move was built on:
# the floor and the raised boxes of kineti_builder's "ground" (a step, a table under the hands, a pillow...)
GROUND = (J.get('_ground') or {}).get(ACT) or {}
LOWF = {e: min(fr['_low'][e][2] for fr in frames) for e in ('footL', 'footR', 'handL', 'handR')}
FLOOR_Z = float(GROUND['base']) if 'base' in GROUND else min(LOWF['footL'], LOWF['footR'], LOWF['handL'], LOWF['handR'])
# the lowest contact standing on a ground box (a balance board or disc under both feet) is not the floor: the floor is
# under the box, as in drive_puppet
if 'base' not in GROUND and any(b[4] > 0.05 and abs(b[4] - FLOOR_Z) < 0.04 for b in GROUND.get('boxes', [])):
    FLOOR_Z = 0.0
# a standing move whose sliding foot sinks through the floor in 3D (cross-leg-side-stretch: 3 cm) must not lower the
# floor to that dip: the standing foot would then never read as planted and the sliding one would anchor the body for
# single frames (a 7 px jerk). The floor is where the hands/feet rest most of the time.
_rest = float(np.median([min(fr['_low'][e][2] for e in LOWF) for fr in frames]))
if 'base' not in GROUND and FLOOR_Z < _rest - 0.015 and float(np.median([hipc(fr)[2] for fr in frames])) - _rest > 0.6:
    FLOOR_Z = _rest
BOXES = [b for b in GROUND.get('boxes', []) if b[4] > FLOOR_Z + 0.03]


def sup_h(p, margin=0.04):
    """Height (world z) of the support under the world point p: the floor, or the highest ground box there that is
    not above p (as drive_puppet)."""
    h = FLOOR_Z
    for x0, x1, y0, y1, hb in BOXES:
        if x0 - margin <= p[0] <= x1 + margin and y0 - margin <= p[1] <= y1 + margin and hb <= p[2] + 0.05:
            h = max(h, hb)
    return h


def low_z(fr, e):
    """Height of the lowest point of a foot / hand above the support under it."""
    lo = fr['_low'][e]
    return lo[2] - sup_h(lo)


def foot_sup(fr, s):
    """Height of the support under a foot above the floor, metres."""
    return sup_h(fr['_low']['foot' + s]) - FLOOR_Z


A0 = {s: min(fr['foot' + s][0][2] - FLOOR_Z - foot_sup(fr, s) for fr in frames) for s in 'LR'}   # flat ankle height
print('SUPPORTS floor', round(FLOOR_Z, 3), 'boxes', BOXES)


def contact(fr, s, near=0.01, far=0.035):
    w = float(np.clip((far - low_z(fr, 'foot' + s)) / (far - near), 0, 1))
    return w * w * (3 - 2 * w)


def smooth_cyclic(v, sigma=2.0):
    v = np.array(v, float)
    r = int(3 * sigma) + 1
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    return sum(w * np.roll(v, -j) for j, w in zip(range(-r, r + 1), k))


CW = {key: {s: smooth_cyclic([contact(fr_, s, a_, b_) for fr_ in frames]) for s in 'LR'}
      for key, (a_, b_) in {'leg': (0.02, 0.10), 'shoe': (0.015, 0.06), 'floor': (0.01, 0.06)}.items()}

# body scale: the drawn hip joints stand FLOOR_PX - hip_y above the floor when the rig's hip joints are at rest height
K = (FLOOR_PX - (JR['hipL'][1] + JR['hipR'][1]) / 2) / float(hipc(R0)[2])
SHOE_H = {s: FLOOR_PX - JR['ankle' + s][1] for s in 'LR'}
print(f'K {K:.1f} px/m, floor z {FLOOR_Z:.3f}, flat ankle {A0}')

# lying, kneeling, sitting: the legs are not stood on the floor line (as drive_puppet's FLOOR)
_up = [jp(fr_, 'neck') - hipc(fr_) for fr_ in frames]
_off = float(np.median([math.degrees(math.acos(np.clip(u[2] / np.linalg.norm(u), -1, 1))) for u in _up]))
_hip = float(np.median([hipc(fr_)[2] - FLOOR_Z for fr_ in frames]))
FLOOR = _off > 50 or _hip < 0.45
print('POSE', 'chao' if FLOOR else 'em pe', 'spine off vertical', round(_off, 1), 'hip', round(_hip, 2))


# ---------- angle tracks with foreshortening: projected angle, held while the projection is too short
def seg_track(b0, b1, l3, lo):
    th, rr = [], []
    prev = None
    for _pass in range(2):                       # a first pass through the cycle gives frame 0 its "previous" angle
        th, rr = [], []
        for fr in frames:
            v = P(jp(fr, b1)) - P(jp(fr, b0))
            r = float(np.linalg.norm(v)) / l3
            raw = ang(v)
            if prev is None:
                prev = raw
            w = float(np.clip((r - 0.12) / 0.25, 0, 1))
            a = prev + w * wdelta(raw - prev)
            prev = a
            th.append(a)
            rr.append(float(np.clip(r, lo, 1.08)))
    return settle_angles(np.rad2deg(np.unwrap(np.deg2rad(th))), np.array(rr_raw_of(b0, b1, l3))), np.array(rr)


def rr_raw_of(b0, b1, l3):
    return [float(np.linalg.norm(P(jp(fr, b1)) - P(jp(fr, b0)))) / l3 for fr in frames]


def settle_angles(th, r, sigma=4.0):
    """Where a segment points (nearly) at the camera its projected angle is unreliable and sweeps fast as the
    limb passes through that direction. Those frames take a confidence-weighted cyclic average of the track (weights
    from the projected length), so the sweep is spread over several frames instead of popping."""
    th = np.array(th, float)
    w = np.clip((np.array(r) - 0.10) / 0.40, 0.02, 1.0) ** 2
    k = int(3 * sigma) + 1
    ker = np.exp(-0.5 * (np.arange(-k, k + 1) / sigma) ** 2)
    n = len(th)
    num = np.zeros(n)
    den = np.zeros(n)
    # cyclic, but the unwrapped track may not close: carry the per-cycle drift
    drift = th[-1] - th[0] + (th[1] - th[0] if n > 1 else 0)
    drift = 360.0 * round(drift / 360.0)
    for j, kw in zip(range(-k, k + 1), ker):
        idx = np.arange(n) + j
        wrap = np.floor_divide(idx, n)
        vals = th[idx % n] + wrap * drift
        num += kw * w[idx % n] * vals
        den += kw * w[idx % n]
    sm = num / den
    b = np.clip((np.array(r) - 0.15) / 0.35, 0, 1)
    return th * b + sm * (1 - b)


TRK = {}
for s in 'LR':
    TRK['braco ' + s] = seg_track('arm' + s, 'elbow' + s, LEN3['braco ' + s], 0.22)
    TRK['antebraco ' + s] = seg_track('elbow' + s, 'hand' + s, LEN3['antebraco ' + s], 0.25)
    TRK['coxa ' + s] = seg_track('leg' + s, 'knee' + s, LEN3['coxa ' + s], 0.30)
    TRK['perna ' + s] = seg_track('knee' + s, 'foot' + s, LEN3['perna ' + s], 0.35)


def _torso_track():
    th, rr, prev = [], [], None
    for _pass in range(2):
        th, rr = [], []
        for fr in frames:
            v = P(jp(fr, 'neck')) - P(hipc(fr))
            r = float(np.linalg.norm(v)) / LEN3['tronco']
            raw = ang(v)
            prev = raw if prev is None else prev
            w = float(np.clip((r - 0.12) / 0.25, 0, 1))
            prev = prev + w * wdelta(raw - prev)
            th.append(prev)
            rr.append(float(np.clip(r, 0.40, 1.08)))
    raw_r = [float(np.linalg.norm(P(jp(fr, 'neck')) - P(hipc(fr)))) / LEN3['tronco'] for fr in frames]
    return settle_angles(np.rad2deg(np.unwrap(np.deg2rad(th))), np.array(raw_r)), np.array(rr)


TRK['tronco'] = _torso_track()
TRK['quadril'] = seg_track('legR', 'legL', LEN3['quadril'], 0.35)
TRK['ombros'] = seg_track('armR', 'armL', LEN3['ombros'], 0.45)


def rel_angle(fr, s, xs=None):
    """The hand against the forearm, in the frontal projection (the rig's hand bone points back up the arm)."""
    hv = P(jp(fr, 'hand' + s), xs) - P(jp(fr, 'hand' + s, True), xs)
    fv = P(jp(fr, 'hand' + s), xs) - P(jp(fr, 'elbow' + s), xs)
    return wdelta(ang(hv) - ang(fv)), float(np.linalg.norm(hv)) / 0.06


HAND0 = {s: rel_angle(R0, s, XS_REST)[0] for s in 'LR'}


def neck_angle(fr, xs=None):
    v = P(jp(fr, 'neck', True), xs) - P(jp(fr, 'neck'), xs)
    return ang(v), float(np.linalg.norm(v)) / 0.06


NECK0 = neck_angle(R0, XS_REST)[0]
print('REST hand', {k: round(v, 1) for k, v in HAND0.items()}, 'neck', round(NECK0, 1))

HANDX = {}
for s in 'LR':
    _x, _l = [], []
    for fr in frames:
        ra, rl = rel_angle(fr, s)
        wgt = float(np.clip((rl - 0.25) / 0.35, 0, 1))
        _x.append(float(np.clip(wdelta(ra - HAND0[s]), -45, 45)) * wgt)
        _l.append(float(np.clip(0.55 + 0.45 * rl, 0.6, 1.0)))
    HANDX[s] = (smooth_cyclic(_x, 2.0), smooth_cyclic(_l, 2.0))

# height of the shorts' waist above the pelvis centre (the seat squash keeps it in place)
_qp = bez_points(SHAPES['quadril'])
WAIST = float(-_qp[:, 0].min()) if len(_qp) else 30.0     # quadril local x points up (axis 0 deg, +y = figure's left)

# rest-pose points in their pieces' frames
LP = {'hipL': local_pt('quadril', JR['hipL']), 'hipR': local_pt('quadril', JR['hipR']),
      'shoulderL': local_pt('tronco', JR['shoulderL']), 'shoulderR': local_pt('tronco', JR['shoulderR']),
      'head': local_pt('tronco', JR['headpivot'])}


def shoe_pts(pose, s):
    return bez_points(SHAPES['pe ' + s], layer_matrix(pose))


HAND_GROUP = {'open': 'mao aberta', 'fist': 'punho', 'flat': 'mao apoiada'}


def hand_pts(pose, s, kind, mirror=False):
    """Outline points of one of the hand drawings (open / fist / flat; flat mirrored for fingers to the left)."""
    gr_ = next(g for g in SHAPES['mao ' + s] if g['nm'] == HAND_GROUP[kind])
    M = layer_matrix(pose)
    if mirror:
        M = M @ np.diag([-1.0, 1.0, 1.0])
    return bez_points(gr_['it'][:-1], M)


def piece_pts(nm, pose, f=None):
    """Outline points of a piece at a pose; a hand draws the drawing it shows at frame f (open before planting)."""
    b = base_of(nm)
    if b.startswith('mao '):
        s = b[-1]
        if f is None or 'FLAT' not in globals():
            return hand_pts(pose, s, 'fist' if FIST[s] else 'open')
        k_ = hand_kind(f, s)
        return hand_pts(pose, s, k_, k_ == 'flat' and PDIR[s][f] < 0)
    return bez_points(SHAPES[b], layer_matrix(pose))


# ---------- per-frame chain
def chain(f, hx_px, extra=None):
    """Poses of every piece for frame f with the pelvis at x = hx_px (y from the 3D hips).
    extra: per-leg (rotation deg, scale) applied to the hip->ankle chain (the floor fit)."""
    fr = frames[f]
    pose = {}
    hc = hipc(fr)
    Pc = np.array([hx_px, FLOOR_PX - K * (hc[2] - FLOOR_Z)])
    thp, rp = TRK['quadril'][0][f], TRK['quadril'][1][f]
    pose['quadril'] = (Pc, thp, 1.0, rp)
    tht, rt = TRK['tronco'][0][f], TRK['tronco'][1][f]
    sw = float(np.clip(TRK['ombros'][1][f], 0.55, 1.0))
    pose['tronco'] = (Pc, tht, sw, rt)
    na, nr = neck_angle(fr)
    head_a = tht + float(np.clip(wdelta(na - tht), -50, 50))      # the 3D neck, within 50 deg of the trunk
    pose['cabeca'] = (place(pose['tronco'], LP['head']), head_a, 1.0, float(np.clip(nr, 0.8, 1.0)))
    J2 = {'pelvis': Pc}
    for s in 'LR':
        H = place(pose['quadril'], LP['hip' + s])
        t1, r1 = TRK['coxa ' + s][0][f], TRK['coxa ' + s][1][f]
        t2, r2 = TRK['perna ' + s][0][f], TRK['perna ' + s][1][f]
        sc = 1.0
        if extra and s in extra:
            dr, sc = extra[s]
            t1, t2 = t1 + dr, t2 + dr
        l1, l2 = PC['coxa ' + s]['len'] * r1 * sc, PC['perna ' + s]['len'] * r2 * sc
        Kn = H + dirv(t1) * l1
        An = Kn + dirv(t2) * l2
        pose['coxa ' + s] = (H, t1, 1.0, r1 * sc)
        pose['perna ' + s] = (Kn, t2, 1.0, r2 * sc)
        pose['joelho ' + s] = (Kn, 90.0, 1.0, 1.0)
        w = float(CW['shoe'][s][f]) if not FLOOR else 0.0
        # on tiptoe (heel raise, the back foot of a curtsy) the toes stay on the floor: seen from the front the shoe
        # shows more of its instep, so it is drawn taller down to the floor instead of lifting off it
        wt = contact(fr, s, 0.006, 0.02) if not FLOOR else 0.0
        st = 1.0
        if wt > 0:
            st = 1.0 + wt * (float(np.clip((FLOOR_PX - K * foot_sup(fr, s) - An[1]) / PC['pe ' + s]['len'], 1.0, 1.7)) - 1.0)
        w = max(w, wt)
        pose['pe ' + s] = (An, t2 + w * wdelta(90.0 - t2), 1.0, st)
        J2['hip' + s], J2['knee' + s], J2['ankle' + s] = H, Kn, An
        S = place(pose['tronco'], LP['shoulder' + s])
        u1, q1 = TRK['braco ' + s][0][f], TRK['braco ' + s][1][f]
        # a raised arm overlaps the shoulder (the scapula turns up): the joint slides in and up with the elevation, so
        # the top of Dinh's arm (his deltoid) stays behind the torso instead of poking out under the armpit
        elev = abs(wdelta(u1 - (tht + 180.0)))
        e_ = float(np.clip((elev - 60.0) / 90.0, 0, 1))
        e_ = e_ * e_ * (3 - 2 * e_)
        across = dirv(tht + 90.0)
        inward = -math.copysign(1.0, float(np.dot(S - Pc, across))) * across
        S = S + (inward * 0.55 + dirv(tht) * 0.20) * JR['elbowW' + s] * e_
        u2, q2 = TRK['antebraco ' + s][0][f], TRK['antebraco ' + s][1][f]
        E = S + dirv(u1) * PC['braco ' + s]['len'] * q1
        W = E + dirv(u2) * PC['antebraco ' + s]['len'] * q2
        pose['braco ' + s] = (S, u1, 1.0, q1)
        pose['antebraco ' + s] = (E, u2, 1.0, q2)
        pose['cotovelo ' + s] = (E, 90.0, 1.0, 1.0)
        Wc = place(pose['antebraco ' + s], np.array([HG[s]['cx'], PC['antebraco ' + s]['len']]))   # centre of the wrist
        pose['mao ' + s] = (Wc, u2 + HANDX[s][0][f], 1.0, HANDX[s][1][f])
        J2['shoulder' + s], J2['elbow' + s], J2['wrist' + s] = S, E, W
    # thighs pointing at the camera (squats) shorten the shorts' legs; the shorts' seat would then hang below them as
    # a skirt. Squash the seat (below the waist) by the thighs' mean foreshortening, keeping the waist where it is.
    rq = float(np.clip(0.25 + 0.75 * (TRK['coxa L'][1][f] + TRK['coxa R'][1][f]) / 2, 0.5, 1.0))
    if rq < 0.999:
        o, a_, sx_, sy_ = pose['quadril']
        up = dirv(a_ - 90.0)
        pose['quadril'] = (np.array(o) + up * (1 - rq) * WAIST, a_, rq, sy_)
    return pose, J2


def planted_y(f, s):
    """Where the ankle of a foot resting on the floor goes: the drawn shoe on the floor line, lifted when the 3D
    ankle rises over its flat height (heel raise)."""
    hs = foot_sup(frames[f], s)
    z = frames[f]['foot' + s][0][2] - FLOOR_Z - hs
    return FLOOR_PX - SHOE_H[s] - K * hs - K * max(0.0, z - A0[s])


def still(f, s):
    if f == 0:
        return True
    a, b = frames[f], frames[f - 1]
    if abs(P(jp(a, 'foot' + s))[0] - P(jp(b, 'foot' + s))[0]) < 0.006:
        return True
    return abs(P(np.array(a['_low']['foot' + s]))[0] - P(np.array(b['_low']['foot' + s]))[0]) < 0.004


_pl = {s: [low_z(fr_, 'foot' + s) < 0.012 and (k_ == 0 or abs(P(jp(fr_, 'foot' + s))[0] - P(jp(frames[k_ - 1], 'foot' + s))[0]) < 0.006)
           for k_, fr_ in enumerate(frames)] for s in 'LR'}
STAY = {}
for s_ in 'LR':
    run, out_ = 0, [0] * N
    for k_ in range(N - 1, -1, -1):
        run = run + 1 if _pl[s_][k_] else 0
        out_[k_] = run
    STAY[s_] = out_

POSES, JOINT2, QA = [], [], []
anchor, hold, primary = {}, {}, None
x0 = None
for f, fr in enumerate(frames):
    hx = 0.0 if WALK else P(hipc(fr))[0] * K
    if x0 is None:
        x0 = float(JR['pelvis'][0]) - hx
    px = x0 + hx
    pose, j2 = chain(f, px)
    extra = {}
    if not FLOOR:
        planted = [s for s in 'LR' if low_z(fr, 'foot' + s) < 0.012 and still(f, s)]
        if primary not in planted:
            primary = max(planted, key=lambda s: STAY[s][f]) if planted else None
            if primary is not None:
                # it takes over from where it was drawn (held, or last frame), not from its raw FK spot
                anchor.clear()
                anchor[primary] = (hold[primary][0] if primary in hold else
                                   JOINT2[f - 1]['ankle' + primary][0] if f > 0 else j2['ankle' + primary][0])
        if primary is not None:
            px += anchor[primary] - j2['ankle' + primary][0]
            pose, j2 = chain(f, px)
        for s in 'LR':
            if _pl[s][f] and s != primary:
                if s not in hold:
                    hold[s] = [j2['ankle' + s][0], 1.0]
                hold[s][1] = 1.0
            elif s in hold:
                hold[s][1] -= 1 / 6
                if hold[s][1] <= 0:
                    hold.pop(s)
        # the floor fit: near the floor each hip->ankle chain is turned/scaled about the hip so the ankle lands on
        # its planted height (and a held foot on its spot). The knee keeps its 3D shape: no IK flip in front view.
        for s in 'LR':
            A = j2['ankle' + s]
            H = j2['hip' + s]
            w_ = float(CW['floor'][s][f])
            ty = planted_y(f, s)
            through = A[1] > ty + 0.5
            if w_ <= 0 and not through:
                continue
            T = A.copy()
            T[1] = A[1] + (ty - A[1]) * (1.0 if through and w_ < 1 and contact(fr, s, 0.01, 0.06) == 0 and A[1] > ty else w_)
            if through and contact(fr, s, 0.01, 0.06) == 0:
                T[1] = min(T[1], ty)                       # in the air: only out of the floor
            if s == primary:
                T[0] = anchor[s]
            elif s in hold:
                T[0] += (hold[s][0] - T[0]) * w_ * hold[s][1]
            sc = float(np.clip(np.linalg.norm(T - H) / max(np.linalg.norm(A - H), 1e-6), 0.80, 1.20))
            extra[s] = (wdelta(ang(T - H) - ang(A - H)), sc)
        if extra:
            pose, j2 = chain(f, px, extra)
    POSES.append(pose)
    JOINT2.append(j2)
    sh = {}
    for s in 'LR':
        pts = shoe_pts(pose['pe ' + s], s)
        sh[s] = (float(pts[:, 1].max()), float(j2['ankle' + s][0]))
    QA.append(dict(hip=j2['pelvis'].copy(), hz=hipc(fr)[2], sh=sh, fz={s: low_z(fr, 'foot' + s) for s in 'LR'},
                   fx={s: P(jp(fr, 'foot' + s))[0] for s in 'LR'}, pose=pose))

# lying / sitting: one vertical shift so what rests on the floor in 3D sits on the floor line. The feet decide when
# they rest (a hand that rests on the floor is then reached down to it by the arm IK below); hands only otherwise.
floor_dy = 0.0
if FLOOR:
    gaps, hgaps = [], []
    for f, fr in enumerate(frames):
        pose = POSES[f]
        for s in 'LR':
            if low_z(fr, 'foot' + s) < 0.03:
                gaps.append(FLOOR_PX - float(shoe_pts(pose['pe ' + s], s)[:, 1].max()))
            if low_z(fr, 'hand' + s) < 0.03:
                hgaps.append(FLOOR_PX - float(hand_pts(pose['mao ' + s], s, 'open')[:, 1].max()))
    if gaps or hgaps:
        floor_dy = float(np.median(gaps or hgaps))
        print('FLOOR SHIFT', round(floor_dy, 1), 'from', 'feet' if gaps else 'hands')


def shift_pose(pose, dx, dy):
    return {k: (np.array(o) + [dx, dy], a, sx, sy) for k, (o, a, sx, sy) in pose.items()}


# close the loop (x drift of the anchoring spread over the cycle), then centre the motion
drift = JOINT2[-1]['pelvis'][0] - JOINT2[0]['pelvis'][0] - (0.0 if WALK else (P(hipc(frames[-1]))[0] - P(hipc(frames[0]))[0]) * K)
POSES = [shift_pose(p, -drift * k / max(N - 1, 1), floor_dy) for k, p in enumerate(POSES)]
for k, q in enumerate(QA):
    q['hip'] = q['hip'] + [-drift * k / max(N - 1, 1), floor_dy]
    q['sh'] = {s: (v[0] + floor_dy, v[1] - drift * k / max(N - 1, 1)) for s, v in q['sh'].items()}


# ---------- planted hands (as drive_puppet): a hand that rests on a support in 3D (the floor, a ground box, a chair's
# backrest beside the body, a table) lies flat on it in the drawing - palm down, fingers along the support pointing
# away from the body, wrist bent - and the arm reaches for it by 2-bone IK; its wrist is pinned while it stays there.
def palm3(fr, s):
    return np.array(fr['_palm'][s] if '_palm' in fr else fr['_low']['hand' + s], float)


def tip3(fr, s):
    return np.array(fr['_tip'][s] if '_tip' in fr else fr['hand' + s][1], float)


def smoothstep(x):
    x = float(np.clip(x, 0.0, 1.0))
    return x * x * (3 - 2 * x)


def solve2(H, T, l1, l2, guide):
    """2-bone IK (drive_puppet): world angles of both pieces reaching T from H; of the two elbow solutions, the one
    nearer `guide`."""
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


PLANT = {s: np.zeros(N) for s in 'LR'}        # weight of the planted pose
PKIND = {s: [None] * N for s in 'LR'}         # ('h', height above the floor) of the support the hand is on
PDIR = {s: np.ones(N) for s in 'LR'}          # fingers towards screen right (+1) or left (-1)
VIRT = {}                                     # supports drawn under the hands only (no ground box): side -> height
_hx = lambda fr_, p_: float(np.dot(np.asarray(p_, float) - hipc(fr_), XS))
if PROPS & {'support', 'side'} or ('table' in PROPS and not BOXES):
    sides = list('LR')
    if 'side' in PROPS and 'support' not in PROPS:      # the hand furthest out to the side holds the backrest
        sides = [max('LR', key=lambda s_: np.mean([abs(_hx(fr, palm3(fr, s_))) for fr in frames]))]
    if 'table' in PROPS and not BOXES:                  # the hand(s) that stay put
        trav = {s_: max(np.linalg.norm(palm3(fr, s_) - palm3(frames[0], s_)) for fr in frames) for s_ in 'LR'}
        sides = [s_ for s_ in 'LR' if trav[s_] < 0.05] or [min(trav, key=trav.get)]
        sides = [s_ for s_ in 'LR' if 'table' + s_ in PROPS] or sides
    for s_ in sides:
        VIRT[s_] = min(palm3(fr, s_)[2] for fr in frames) - 0.035 - FLOOR_Z
for s in 'LR':
    if FIST[s] and grips(s):                            # a closed hand holds its prop; it is not laid flat
        continue
    w_raw, kind = [], []
    for f, fr in enumerate(frames):
        lo = np.array(fr['_low']['hand' + s], float)
        cand = []
        if s in VIRT:
            cand.append((0.0, ('h', round(float(VIRT[s]), 3))))
        hs = sup_h(lo)
        if fr['arm' + s][0][2] - lo[2] > 0.12:          # the hand well below the shoulder: it can lean on it
            cand.append((lo[2] - hs, ('h', round(float(hs - FLOOR_Z), 3))))
        gap, k_ = min(cand, key=lambda c: c[0]) if cand else (1.0, None)
        w_raw.append(smoothstep((0.06 - gap) / 0.04))
        kind.append(k_)
    w_s = np.clip(smooth_cyclic(w_raw, 1.5), 0, 1)
    w_s[w_s < 0.02] = 0.0
    PLANT[s] = w_s
    last = None
    for f in range(N):                                  # the support a hand is on holds while it eases off
        if kind[f] is not None and w_raw[f] > 0.3:
            last = kind[f]
        PKIND[s][f] = kind[f] if w_raw[f] > 0.3 or last is None else last

# where a support stands in the drawing: the floor line, or its 3D height; a raised support only the hands touch goes
# where the drawn arms put the flat palm (the puppet's arms are not the rig's length), as drive_puppet's SUPY
FOOT_HS = {round(foot_sup(fr, s_), 3) for fr in frames for s_ in 'LR' if low_z(fr, 'foot' + s_) < 0.012}
SUPY = {}
_sy = {}
for f in range(N):
    for s in 'LR':
        k_ = PKIND[s][f]
        if PLANT[s][f] < 0.5 or k_ is None or k_[1] < 0.03 or k_[1] in FOOT_HS:
            continue
        _sy.setdefault(k_[1], []).append(float(POSES[f]['mao ' + s][0][1]) + HG[s]['Dn'])
for h_, ys in _sy.items():
    SUPY[h_] = float(np.median(ys))
    print('HAND SUPPORT', h_, 'at', round(SUPY[h_], 1), 'px (3D height gives', round(FLOOR_PX - K * h_, 1), ')')


def sup_y(h):
    return SUPY.get(round(float(h), 3), FLOOR_PX - K * float(h))


# Lying on the floor with a hand planted (side plank): the drawing's arms are ~20% shorter than the rig's, so a straight
# arm would stop short of the floor. The whole figure is turned about its resting feet just enough for the drawn arm
# to reach (a few degrees: the body line slopes a little more), instead of stretching the arm out of shape.
SETTLE = 0.0
_fp = [f for f in range(N) for s in 'LR' if PLANT[s][f] > 0.5 and PKIND[s][f] and PKIND[s][f][1] < 0.03]
if FLOOR and _fp:
    _feet = [shoe_pts(POSES[f]['pe ' + s], s) for f in range(N) for s in 'LR' if low_z(frames[f], 'foot' + s) < 0.03]
    if _feet:
        _low = np.vstack([p_[p_[:, 1] > p_[:, 1].max() - 3] for p_ in _feet])
        pivot = np.array([float(np.median(_low[:, 0])), FLOOR_PX])

        def _reach(th, f, s):
            S_ = pivot + rot2(th) @ (np.array(POSES[f]['braco ' + s][0]) - pivot)
            W_ = pivot + rot2(th) @ (np.array(POSES[f]['mao ' + s][0]) - pivot)
            l_ = PC['braco ' + s]['len'] * POSES[f]['braco ' + s][3] + PC['antebraco ' + s]['len'] * POSES[f]['antebraco ' + s][3]
            return float(np.hypot(W_[0] - S_[0], FLOOR_PX - HG[s]['Dn'] - S_[1])) / (0.995 * l_)
        sides_ = [s for s in 'LR' if PLANT[s].max() > 0.5]
        sgn = 1.0 if np.median([POSES[f]['braco ' + s][0][0] for f in _fp for s in sides_]) > pivot[0] else -1.0
        for th in np.arange(0.0, 15.01, 0.25) * sgn:
            need = [_reach(th, f, s) for f in _fp for s in sides_ if PLANT[s][f] > 0.5]
            if np.percentile(need, 90) <= 1.06:
                break
        SETTLE = float(th)
        if SETTLE:
            Rm = rot2(SETTLE)
            POSES = [{k: (pivot + Rm @ (np.array(o) - pivot), a + SETTLE, sx, sy) for k, (o, a, sx, sy) in p.items()} for p in POSES]
            for q in QA:
                q['hip'] = pivot + Rm @ (np.array(q['hip']) - pivot)
            print('SETTLE the lying body turned', round(SETTLE, 2), 'deg about the feet so the planted arm reaches the floor')

PIN, LAST_UA, HAND_FLOAT = {}, {}, 0.0
FLAT = {s: [False] * N for s in 'LR'}
MAXST = 1.25 if FLOOR else 1.12
for f in range(N):
    pose = POSES[f]
    fr = frames[f]
    for s in 'LR':
        w_ = float(PLANT[s][f])
        if w_ <= 0 or PKIND[s][f] is None:
            PIN.pop(s, None)
            continue
        _, val = PKIND[s][f]
        S = np.array(pose['braco ' + s][0], float)
        E0 = np.array(pose['antebraco ' + s][0], float)
        Wn = np.array(pose['mao ' + s][0], float)
        q1, q2 = pose['braco ' + s][3], pose['antebraco ' + s][3]
        l1, l2 = PC['braco ' + s]['len'] * q1, PC['antebraco ' + s]['len'] * q2
        tv = P(tip3(fr, s)) - P(palm3(fr, s))
        dirn = float(np.sign(tv[0])) if abs(tv[0]) > 0.03 else (1.0 if Wn[0] >= pose['quadril'][0][0] else -1.0)
        if w_ > 0.5:
            if s not in PIN or PIN[s][1] != PKIND[s][f]:
                PIN[s] = (float(Wn[0]), PKIND[s][f], dirn)
            tx, dirn = PIN[s][0], PIN[s][2]
        else:
            PIN.pop(s, None)
            tx = float(Wn[0])
        T = np.array([tx, sup_y(val) - HG[s]['Dn']])
        R = 0.995 * (l1 + l2)
        dv = T - S
        stretch = 1.0
        if np.linalg.norm(dv) > R:
            stretch = float(min(MAXST, np.linalg.norm(dv) / R))
            if np.linalg.norm(dv) > R * stretch and abs(dv[1]) < R * stretch:     # slide along the support
                T[0] = S[0] + np.sign(dv[0]) * math.sqrt((R * stretch) ** 2 - dv[1] ** 2)
        guide = E0
        if s in LAST_UA and LAST_UA[s][0] == f - 1:     # continuous: the elbow stays on the side it was
            guide = S + l1 * stretch * dirv(LAST_UA[s][1])
        a1, a2 = solve2(S, T, l1 * stretch, l2 * stretch, guide)
        LAST_UA[s] = (f, a1)
        u1, u2 = pose['braco ' + s][1], pose['antebraco ' + s][1]
        n1, n2 = u1 + w_ * wdelta(a1 - u1), u2 + w_ * wdelta(a2 - u2)
        sc = 1.0 + w_ * (stretch - 1.0)
        pose['braco ' + s] = (S, n1, 1.0, q1 * sc)
        E = S + dirv(n1) * l1 * sc
        pose['antebraco ' + s] = (E, n2, 1.0, q2 * sc)
        pose['cotovelo ' + s] = (E, 90.0, 1.0, 1.0)
        Wc = place(pose['antebraco ' + s], np.array([HG[s]['cx'], PC['antebraco ' + s]['len']]))
        want = 0.0 if dirn > 0 else 180.0
        ha = pose['mao ' + s][1]
        on = w_ > 0.5
        pose['mao ' + s] = (Wc, ha + (w_ if not on else 1.0) * wdelta(want - ha), 1.0, 1.0 if on else pose['mao ' + s][3])
        PDIR[s][f] = dirn
        FLAT[s][f] = on
        if on:
            HAND_FLOAT = max(HAND_FLOAT, abs(float(Wc[1]) + HG[s]['Dn'] - sup_y(val)))
            if '--debughands' in sys.argv and f % 20 == 0:
                print('HANDDBG', f, s, 'S', np.round(S, 1), 'T', np.round(T, 1), 'Wc', np.round(Wc, 1), 'l', round(l1, 1), round(l2, 1),
                      'stretch', round(stretch, 3), 'q', round(q1, 2), round(q2, 2))
for s in 'LR':
    if PLANT[s].max() > 0:
        print('PLANT', s, 'frames', int(sum(FLAT[s])), 'kinds', sorted({str(k) for k in PKIND[s] if k}))


def hand_kind(f, s):
    return 'flat' if FLAT[s][f] else ('fist' if FIST[s] else 'open')


# ---------- layer order: arms in front of the torso while the elbow / hand is in front of the chest, a hand (and its
# forearm) over the head while it is in front of the face, the right leg over the left while it is nearer the camera
# (curtsy, crossover). Hysteresis on each, so a switch does not flicker.
FRONT = {}
OVER = {}
for s in 'LR':
    fu, ff, fo, fa = [], [], [], []
    su = sf = so = sa = False
    for _pass in range(2):
        fu, ff, fo, fa = [], [], [], []
        for f, fr in enumerate(frames):
            de = depth(jp(fr, 'elbow' + s) - jp(fr, 'arm' + s))
            dh = depth(jp(fr, 'hand' + s) - jp(fr, 'arm' + s))
            su = de > (0.04 if su else 0.08)
            sf = su or dh > (0.05 if sf else 0.10)
            dface = depth(jp(fr, 'hand' + s) - jp(fr, 'neck', True))
            hp = np.array(POSES[f]['mao ' + s][0])
            hc_ = np.array(POSES[f]['cabeca'][0]) + dirv(POSES[f]['cabeca'][1]) * PC['cabeca']['len'] * 0.5
            nearhead = np.linalg.norm(hp - hc_) < 1.6 * PC['cabeca']['len']
            so = sf and not FLAT[s][f] and nearhead and dface > (0.03 if so else 0.07)
            # the forearm too only while its middle is in front of the face as well (a hand reaching past the head
            # from behind it keeps its forearm behind)
            dmid = depth((jp(fr, 'hand' + s) + jp(fr, 'elbow' + s)) / 2 - jp(fr, 'neck', True))
            sa = so and dmid > (0.03 if sa else 0.07)
            fu.append(su)
            ff.append(sf)
            fo.append(so)
            fa.append(sa)
    FRONT['braco ' + s] = fu
    for nm in ('antebraco ', 'mao ', 'cotovelo '):
        FRONT[nm + s] = ff
    OVER['mao ' + s] = fo
    OVER['antebraco ' + s] = OVER['cotovelo ' + s] = fa
RTOP = []
_on = False
for _pass in range(2):
    RTOP = []
    for fr in frames:
        dd = 0.5 * (depth(jp(fr, 'kneeR') - jp(fr, 'kneeL')) + depth(jp(fr, 'footR') - jp(fr, 'footL')))
        _on = dd > (0.02 if _on else 0.05)
        RTOP.append(_on)
print('LAYERS arms in front', {s: int(sum(FRONT['antebraco ' + s])) for s in 'LR'}, 'hand over head',
      {s: int(sum(OVER['mao ' + s])) for s in 'LR'}, 'forearm over head', {s: int(sum(OVER['antebraco ' + s])) for s in 'LR'},
      'right leg on top', int(sum(RTOP)))


def visible(nm, f):
    """Is layer nm drawn at frame f (of a piece's normal / ' +' / ' ^' copies, exactly one is)."""
    b = base_of(nm)
    if b.endswith(' R') and b.split(' ')[0] in ('coxa', 'perna', 'joelho', 'pe'):
        return RTOP[f] == nm.endswith(' ^')
    if b in FRONT:
        fr_, ov = FRONT[b][f], OVER.get(b, [False] * N)[f]
        if nm.endswith(' ^'):
            return ov
        if nm.endswith(' +'):
            return fr_ and not ov
        return not fr_
    return True


# ---------- shadow: a flat ellipse spanning what touches the floor
SHADOW = []
for f, fr in enumerate(frames):
    pose = POSES[f]
    xs = []
    for nm in ('pe L', 'pe R', 'mao L', 'mao R', 'perna L', 'perna R', 'coxa L', 'coxa R', 'antebraco L', 'antebraco R'):
        pts = piece_pts(nm, pose[nm], f)
        on = pts[pts[:, 1] > FLOOR_PX - 40]
        if len(on):
            xs += [float(on[:, 0].min()), float(on[:, 0].max())]
    if xs:
        SHADOW.append(((min(xs) + max(xs)) / 2, FLOOR_PX + 4, (max(xs) - min(xs)) / 2 + 26, 13.0))
    else:
        SHADOW.append((float(pose['quadril'][0][0]), FLOOR_PX + 4, 30.0, 8.0))


# ---------- angle tracks: unwrapped (no blink), single-frame reversals removed (drive_puppet's despike: a key that
# jumps out and straight back, from a contact switching on for one frame, flashes in the rendered in-betweens)
ROT = {}
_despiked = 0
for b in POSES[0]:
    v = list(np.rad2deg(np.unwrap(np.deg2rad([POSES[f][b][1] - 90.0 for f in range(N)]))))
    for i_ in range(1, N - 1):
        a_, b_ = v[i_] - v[i_ - 1], v[i_ + 1] - v[i_]
        if a_ * b_ < 0 and min(abs(a_), abs(b_)) > 1.0:
            v[i_] = (v[i_ - 1] + v[i_ + 1]) / 2
            _despiked += 1
    ROT[b] = v
if _despiked:
    print('DESPIKE', _despiked, 'keys')
_flips = [(b, i_) for b in ROT for i_ in range(1, N) if abs(ROT[b][i_] - ROT[b][i_ - 1]) > 45]
print('FLIPS', len(_flips), _flips[:6])          # a piece turning > 45 deg in one frame: a visible snap


# ---------- QA
def qa():
    out = {}
    hip_h = np.array([FLOOR_PX - q['hip'][1] for q in QA])
    hz = np.array([q['hz'] for q in QA]) * K
    out['bob_px'] = round(float(np.ptp(hip_h - hz)), 1)
    fl, sk = 0.0, 0.0
    for s in 'LR':
        on = [i for i, q in enumerate(QA) if q['fz'][s] < 0.012]
        if not FLOOR:
            fl = max([fl] + [abs(QA[i]['sh'][s][0] - (FLOOR_PX - K * foot_sup(frames[i], s))) for i in on])
        for a_, b_ in zip(on, on[1:]):
            if b_ == a_ + 1 and abs(QA[b_]['fx'][s] - QA[a_]['fx'][s]) < 0.002:
                sk = max(sk, abs(QA[b_]['sh'][s][1] - QA[a_]['sh'][s][1]))
    out['float_px'], out['skate_px_per_frame'] = round(fl, 1), round(sk, 2)
    out['hand_float_px'] = round(HAND_FLOAT, 1)
    jump, who = 0.0, ''
    for b, v in ROT.items():
        for f_ in range(1, N):
            if abs(v[f_] - v[f_ - 1]) > jump:
                jump, who = abs(v[f_] - v[f_ - 1]), f'{b}@{f_}'
    out['max_turn_deg_per_frame'] = round(jump, 1)
    out['max_turn_at'] = who
    hy = np.array([q['hip'][1] for q in QA])
    out['max_body_step_px'] = round(float(np.abs(np.diff(hy) + np.diff(hz)).max()), 1) if N > 1 else 0
    out['min_foreshortening'] = {k: round(float(TRK[k][1].min()), 2) for k in ('braco L', 'braco R', 'antebraco L', 'antebraco R', 'coxa L', 'coxa R', 'tronco')}
    out['arms_in_front_frames'] = {s: int(sum(FRONT['antebraco ' + s])) for s in 'LR'}
    out['flips'] = len(_flips)
    return out


print('QA', json.dumps(qa()))

# ---------- keys: thinned (a key that linear interpolation between its neighbours reproduces within 0.3 px / 0.3 deg
# / 0.3 % is dropped; contacts within 0.1 px); a layer that is never drawn is left out
TOL = {'p': 0.3, 'r': 0.3, 's': 0.3}


def thin(vals, tol, care=None, keep=()):
    """Indices of the keys to keep: greedy, each segment as long as linear interpolation stays within tol[f] of
    every frame it spans (care[f] False: that frame is not drawn, any value will do)."""
    V = np.array(vals, float).reshape(len(vals), -1)
    n = len(V)
    if '--nothin' in sys.argv:                          # every key (to check the thinning against)
        return list(range(n))
    tol = np.broadcast_to(np.asarray(tol, float), (n,))
    care = np.ones(n, bool) if care is None else np.asarray(care, bool)
    keep = set(keep)
    out, i = [0], 0
    while i < n - 1:
        best = i + 1
        for j in range(i + 2, n):
            if (j - 1) in keep and j - 1 > i:
                break
            k = np.arange(i + 1, j)
            u = ((k - i) / (j - i))[:, None]
            err = np.abs(V[i] + (V[j] - V[i]) * u - V[k]).max(1)
            if np.any((err > tol[k]) & care[k]):
                break
            best = j
        out.append(best)
        i = best
    return out


def anim(vals, dims, hold=False, tol=None, care=None, keep=()):
    idx = range(len(vals))
    if hold:
        idx = [t for t in range(len(vals)) if t == 0 or vals[t] != vals[t - 1]]
        if len(idx) == 1:
            return {'a': 0, 'k': vals[0]}
    elif tol is not None:
        idx = thin(vals, tol, care, keep)
        if len(idx) == 2 and np.allclose(vals[0], vals[-1]) and np.allclose(vals[0], vals[len(vals) // 2]):
            if all(np.allclose(v, vals[0], atol=float(np.max(tol))) for v in vals):
                return {'a': 0, 'k': vals[0] if dims > 1 else vals[0]}
    ks = []
    for t in idx:
        v = vals[t]
        k = {'t': t, 's': (list(v) if dims > 1 else [v])}
        if hold:
            k['h'] = 1
        else:
            k['i'], k['o'] = {'x': 0.5, 'y': 0.5}, {'x': 0.5, 'y': 0.5}
            if dims > 1:
                k['ti'], k['to'] = [0] * dims, [0] * dims
        ks.append(k)
    return {'a': 1, 'k': ks}


def contact_frames(b):
    """Frames where piece b rests on something: its tolerance is tighter there (contacts stay exact)."""
    s = b.split(' ')[1] if ' ' in b else ''
    if b.startswith(('pe ', 'perna ')) and s in 'LR' and s:
        return [low_z(frames[f], 'foot' + s) < 0.012 for f in range(N)]
    if b.startswith(('mao ', 'antebraco ')) and s:
        return FLAT[s]
    return [False] * N


# ======================================================================================================
# equipment, in the same frontal pixels as the body (names and meaning as drive_puppet / render_mannequin)
# ======================================================================================================
# Every prop is placed from the DRAWN body (hands, feet, knees, pelvis of the final poses), so held things stay in the
# hand and supports stay under what rests on them; 3D positions only say where a fixed prop stands. Flat style, the
# side puppet's colours. Seen from the front: screen x grows towards the figure's left; a support's top shows as a
# lighter band (the drawing is seen from a little above).
PROP_PTS = []
CHAIR, CHAIR_DK, CHAIR_TOP = '#C5D0DC', '#8E9AAB', '#DCE3EB'
WALL_C, STEP_C, STEP_TOP = '#E7EDF4', '#9AA8BA', '#5E6B7D'
BALL_C, DB_C, DB_HI, BAND_C = '#F2A65A', '#3D4654', '#5A6577', '#F57C1F'
MAT_C, MAT_TOP, ROLL_C, BED_C = '#C9D5E2', '#DCE5EE', '#7FB7AE', '#F4F6F9'
BED_BASE, PILLOW_C, PILLOW_LN = '#C5D0DC', '#F4F1EC', '#DDD6CB'
SWISS_C, SWISS_HI, WOBBLE_C, BOSU_C = '#5B8DEF', '#7FA6F3', '#7C6FD6', '#2F80ED'
STICK_C, WALKER_C, GRIP_C, LADDER_C = '#3F6E8C', '#AEB8C6', '#3D4A5C', '#E2B43A'
TOWEL_C, TOWEL_LN, MARK_C, TAPE_C = '#E6DCC6', '#CFC6B3', '#F5593D', '#3D4A5C'
FL = FLOOR_PX
TOPF = 0.035 * K                  # depth of a support's top face as seen from a little above
THICK = max(8.0, 0.04 * K)


def drawn(f, nm):
    """Origin (joint) of a drawn piece at frame f."""
    return np.array(POSES[f][nm][0], float)


def hip_px(f):
    return drawn(f, 'quadril')


def to_px(f, world):
    """A 3D point in the puppet's pixels: one metre towards the figure's left is K pixels to the right."""
    return hip_px(f) + (P(np.array(world, float)) - P(hipc(frames[f]))) * K


def grip(f, s):
    """Where the drawn hand holds something: the fist's centre, the open palm's middle, or the flat palm's."""
    pose = POSES[f]['mao ' + s]
    k_ = hand_kind(f, s)
    if k_ == 'flat':
        return place(pose, np.array([0.0, 0.45 * HG[s]['Lh']]))
    return place(pose, HG[s]['grip'] if k_ == 'fist' else HG[s]['palm'])


def hand_dir(f, s):
    return dirv(POSES[f]['mao ' + s][1])


def foot_pt(f, s, where='ball'):
    """The drawn shoe: its ankle, or the sole's middle (seen from the front the ball of the foot is under the shoe)."""
    o, a, sx, sy = POSES[f]['pe ' + s]
    if where == 'ankle':
        return np.array(o, float)
    return place(POSES[f]['pe ' + s], np.array([0.0, 0.8 * PC['pe ' + s]['len']]))


def knee_pt(f, s):
    return drawn(f, 'joelho ' + s)


def shin_pt(f, s, up):
    a, k = drawn(f, 'pe ' + s), knee_pt(f, s)
    v = k - a
    return a + v / max(np.linalg.norm(v), 1e-6) * up * K


def thigh_pt(f, s, up):
    k, h = knee_pt(f, s), drawn(f, 'coxa ' + s)
    v = h - k
    return k + v / max(np.linalg.norm(v), 1e-6) * up * K


def end_pt(f, code):
    """band_end codes of render_mannequin: hL/hR grip, fL/fR the foot, aL/aR above the ankle, kL/kR knee, sL/sR the
    shoulder (the band runs behind it), eL/eR the elbow."""
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
        return drawn(f, 'braco ' + s)
    if k == 'e':
        return drawn(f, 'cotovelo ' + s)
    raise KeyError(code)


def end3(fr, code):
    k, s = code[0], code[1]
    return jp(fr, {'h': 'hand', 'f': 'foot', 'a': 'foot', 'k': 'knee', 's': 'arm', 'e': 'elbow'}[k] + s)


def path_of(pts, closed=True):
    return {'c': closed, 'v': [[round(float(x), 2), round(float(y), 2)] for x, y in pts],
            'i': [[0, 0]] * len(pts), 'o': [[0, 0]] * len(pts)}


def rect(x0, y0, x1, y1, fill, track=True, nm='box'):
    x0, x1 = sorted((x0, x1))
    y0, y1 = sorted((y0, y1))
    if track:
        PROP_PTS.extend([[x0, y0], [x1, y1]])
    return group(nm, path_of([(x0, y0), (x1, y0), (x1, y1), (x0, y1)]), fill=fill)


def rrect(x0, y0, x1, y1, r, fill, track=True, nm='box', stroke=None):
    x0, x1 = sorted((x0, x1))
    y0, y1 = sorted((y0, y1))
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


def prop_layer(nm, shapes, where='behind'):
    """A shape layer for a prop: 'behind' the whole body (in front of its floor shadow), 'front' of everything,
    ('above', layer) just above that layer, ('below', layer) just under it."""
    lay = shape_layer(0, nm, shapes, N)
    if where == 'behind':
        k = next(i for i, l in enumerate(comp['layers']) if l['nm'] == 'shadow')
    elif where == 'front':
        k = 0
    elif where[0] == 'above':
        k = next(i for i, l in enumerate(comp['layers']) if l['nm'] == where[1])
    else:
        k = next(i for i, l in enumerate(comp['layers']) if l['nm'] == where[1]) + 1
    comp['layers'].insert(k, lay)
    PROP_LAYERS.append(lay)
    return lay


PROP_LAYERS = []


def solid_layer(nm, shapes, where='behind'):
    if shapes:
        return prop_layer(nm, shapes, where)


def moving_layer(nm, shapes, ps, rs=None, where='front', r_track=0.0, ss=None):
    """A prop drawn around its own origin, carried every frame to ps[f] (turned rs[f] degrees, scaled ss[f])."""
    lay = prop_layer(nm, shapes, where)
    lay['ks']['p'] = anim([[round(float(p[0]), 1), round(float(p[1]), 1), 0] for p in ps], 3, tol=TOL['p'])
    if rs is not None:
        lay['ks']['r'] = anim([round(float(v), 2) for v in np.rad2deg(np.unwrap(np.deg2rad(np.array(rs, float))))], 1, tol=TOL['r'])
    if ss is not None:
        lay['ks']['s'] = anim([[round(float(a), 1), round(float(b), 1), 100] for a, b in ss], 3, tol=TOL['s'])
    for p in ps[::2]:
        PROP_PTS.extend([[p[0] - r_track, p[1] - r_track], [p[0] + r_track, p[1] + r_track]])
    return lay


def bar_between(pa, pb, nm, fill, thick, where='front', min_len=1.0, center_len=None):
    """A straight bar (band, rope, stick, towel) between two moving points: a unit rectangle stretched, turned and
    carried every frame."""
    ks_p, ks_r, ks_s = [], [], []
    for a, b in zip(pa, pb):
        dv = np.asarray(b, float) - np.asarray(a, float)
        dist = float(np.linalg.norm(dv))
        mid = (np.asarray(a, float) + np.asarray(b, float)) / 2
        an = math.degrees(math.atan2(dv[1], dv[0])) if dist > 8 else (ks_r[-1] if ks_r else 0.0)
        if center_len is not None:
            dist = center_len
        dist = max(dist, min_len)
        ks_p.append([round(float(mid[0]), 1), round(float(mid[1]), 1), 0])
        ks_r.append(an)
        ks_s.append([round(dist * 100, 1), 100, 100])
        u_ = dirv(an)
        PROP_PTS.extend([(mid + u_ * dist / 2).tolist(), (mid - u_ * dist / 2).tolist()])
    bar = {'ty': 'gr', 'nm': 'barra', 'it': [
        {'ty': 'rc', 'nm': 'rc', 'p': {'a': 0, 'k': [0, 0]}, 's': {'a': 0, 'k': [1, thick * 2]}, 'r': {'a': 0, 'k': 0}},
        {'ty': 'fl', 'c': {'a': 0, 'k': hexc(fill)}, 'o': {'a': 0, 'k': 100}, 'r': 1, 'nm': 'fill'},
        copy.deepcopy(IDENT_TR)]}
    lay = prop_layer(nm, [bar], where)
    lay['ks']['p'] = anim(ks_p, 3, tol=TOL['p'])
    lay['ks']['r'] = anim([round(float(v), 2) for v in np.rad2deg(np.unwrap(np.deg2rad(np.array(ks_r))))], 1, tol=TOL['r'])
    lay['ks']['s'] = anim(ks_s, 3, tol=TOL['s'])
    return lay


def in_piece(nms, shapes, top=True):
    """Shapes drawn inside a body piece's layer(s) (local frame of the piece): they follow it at no cost in keys
    and keep its place in the layer order (a cuff on the shin, a dumbbell in the fist)."""
    for nm in nms:
        if nm in LAY:
            LAY[nm]['shapes'] = (copy.deepcopy(shapes) + LAY[nm]['shapes']) if top else (LAY[nm]['shapes'] + copy.deepcopy(shapes))


def copies(b):
    return [nm for nm in (b, b + ' +', b + ' ^') if nm in LAY]


def top_of(*nms):
    """Of these layers, the one highest in the order (to put a prop just above all of them)."""
    idx = {l['nm']: i for i, l in enumerate(comp['layers'])}
    return min((n for n in nms if n in idx), key=lambda n: idx[n])


IN_FRONT = ('below', 'cabeca')                # over the arms and the torso, under the head (and a hand over it)
DONE = set()
seat_f = min(range(N), key=lambda i: frames[i]['hips'][0][2])
seated = (not TOP) and bool(PROPS & {'chair', 'stool'} or ('ball' in PROPS and not PROPS & {'wallball', 'wallback'} and 0.38 < hipc(frames[0])[2] - FLOOR_Z < 0.68))


def seat_bottom(f):
    """Lowest point of the drawn seat of the shorts at frame f."""
    return float(piece_pts('quadril', POSES[f]['quadril'], f)[:, 1].max())


def chair_front(cx, seat_y, back_h, half=0.24):
    """A chair seen from the front, behind the body: backrest (if any) and back legs, the seat's top face and front
    edge, the front legs."""
    hw_ = half * K
    out = []
    if back_h > 4:
        out.append(rrect(cx - hw_ * 0.86, seat_y - back_h, cx + hw_ * 0.86, seat_y - back_h + 0.2 * K, 4, CHAIR, nm='encosto'))
        for sx in (-1, 1):
            out.append(rect(cx + sx * hw_ * 0.80 - THICK * 0.35, seat_y - back_h + 0.05 * K, cx + sx * hw_ * 0.80 + THICK * 0.35,
                            FL - TOPF * 0.6, CHAIR_DK, nm='perna tras'))
    out.append(rect(cx - hw_, seat_y - TOPF, cx + hw_, seat_y, CHAIR_TOP, nm='assento'))
    out.append(rrect(cx - hw_, seat_y, cx + hw_, seat_y + THICK, 2, CHAIR, nm='assento frente'))
    for sx in (-1, 1):
        x = cx + sx * (hw_ - THICK * 0.35)
        out.append(rect(x - THICK * 0.35, seat_y + THICK * 0.3, x + THICK * 0.35, FL, CHAIR_DK, nm='perna'))
    return out[::-1]


def chair_profile(x_back, out, top_y, seat_y):
    """A chair beside the body seen from its side ("h"): the backrest post under the hand at x_back, the seat running
    away from the body (out = +-1), legs to the floor."""
    d_ = 0.42 * K
    bits = [rrect(x_back - 0.035 * K, top_y, x_back + 0.035 * K, top_y + THICK, 3, CHAIR, nm='encosto topo'),
            rect(x_back - THICK * 0.45, top_y, x_back + THICK * 0.45, FL, CHAIR, nm='encosto'),
            rrect(min(x_back, x_back + out * d_), seat_y, max(x_back, x_back + out * d_), seat_y + THICK, 2, CHAIR, nm='assento'),
            rect(x_back + out * d_ - THICK * 0.4, seat_y, x_back + out * d_ + THICK * 0.4, FL, CHAIR_DK, nm='perna')]
    return bits


# --- seats
if 'swissseat' in PROPS:
    hip = hip_px(seat_f)
    bottom = seat_bottom(seat_f)
    ry = (FL - bottom + 4) / 2
    rx = 0.29 * K
    solid_layer('bola suica', [ellipse(hip[0] - rx * 0.35, FL - ry * 1.4, rx * 0.2, ry * 0.12, SWISS_HI, nm='brilho'),
                               ellipse(hip[0], FL - ry, rx, ry, SWISS_C, n=16)])
    DONE.add('swissseat')
elif seated or PROPS & {'chairfit'}:
    f_ = seat_f if seated else 0
    hip = hip_px(f_)
    sy = min(seat_bottom(f_) - 0.02 * K, hip[1] + 0.06 * K)
    solid_layer('cadeira', chair_front(hip[0], sy, 0.0 if 'stool' in PROPS else 0.5 * K))
    DONE |= {'chair', 'stool', 'chairfit'}
if 'chairbehind' in PROPS:
    hip = hip_px(max(range(N), key=lambda i: float(hip_px(i)[1])))
    solid_layer('cadeira', chair_front(hip[0], FL - 0.45 * K, 0.5 * K))
if 'bedfit' in PROPS:
    hip = hip_px(0)
    top = hip[1] + 0.075 * K
    solid_layer('cama', [rect(hip[0] - 0.95 * K, top - TOPF, hip[0] + 0.95 * K, top, BED_C),
                         rect(hip[0] - 0.95 * K, top, hip[0] + 0.95 * K, top + 0.16 * K, BED_C),
                         rect(hip[0] - 0.97 * K, top + 0.16 * K, hip[0] + 0.97 * K, FL, BED_BASE)][::-1])


# --- the ground boxes the move was built on: what each one is depends on the props
def box_x(b, f=0):
    """Screen x range of a ground box. It is placed from the drawn part that rests on it (the head on a pillow, a
    hand on a table, a foot on a step: the drawing's proportions are not the rig's), else from the hips."""
    fr = frames[f]
    nk = jp(fr, 'neck', True) - jp(fr, 'neck')
    hc3 = jp(fr, 'neck', True) + nk / max(np.linalg.norm(nk), 1e-6) * 0.11          # the head's centre
    cands = {'head': (hc3, lambda: place(POSES[f]['cabeca'], np.array([0.0, 0.5 * PC['cabeca']['len']])))}
    for s_ in 'LR':
        cands['hand' + s_] = (palm3(fr, s_), lambda s_=s_: grip(f, s_))
        cands['foot' + s_] = (np.array(fr['_low']['foot' + s_], float), lambda s_=s_: foot_pt(f, s_))
        cands['knee' + s_] = (jp(fr, 'knee' + s_), lambda s_=s_: knee_pt(f, s_))
    cands['hips'] = (hipc(fr), lambda: hip_px(f))

    def dist(p):
        dx = max(b[0] - p[0], 0.0, p[0] - b[1])
        dy = max(b[2] - p[1], 0.0, p[1] - b[3])
        return math.hypot(dx, dy) + (0.0 if p[2] > b[4] - 0.05 else 9.0)
    nm = min(cands, key=lambda k_: dist(cands[k_][0]))
    p3, p2 = cands[nm][0], cands[nm][1]()
    xs = [float(p2[0] + (P(np.array([x, y, p3[2]])) - P(p3))[0] * K) for x in b[:2] for y in b[2:4]]
    return min(xs), max(xs)


if BOXES and not PROPS & {'walker', 'walkergo', 'swissseat'} and not any(p.startswith(('ballfeet', 'ballarms', 'ballhands', 'ballback')) for p in PROPS):
    for b in BOXES:
        h = b[4] - FLOOR_Z
        x0, x1 = box_x(b)
        yn = sup_y(h)
        if 'chairbox' in PROPS:
            solid_layer('cadeira', chair_front((x0 + x1) / 2, yn, 0.5 * K, half=(x1 - x0) / 2 / K))
        elif 'table' in PROPS or any(p.startswith('table') for p in PROPS):
            bits = [rect(x0, yn - TOPF, x1, yn, CHAIR_TOP), rrect(x0 - 4, yn, x1 + 4, yn + THICK, 2, CHAIR)]
            for x in (x0 + 0.05 * K, x1 - 0.05 * K - THICK * 0.7):
                bits.append(rect(x, yn + THICK, x + THICK * 0.7, FL, CHAIR_DK))
            solid_layer('mesa', bits[::-1])
        elif 'pillow' in PROPS:
            bits = []
            z = 0.0
            if h > 0.45:                                # a small table under one pillow
                yt = sup_y(h - 0.1)
                bits += [rect(x0 - 0.05 * K, yt, x1 + 0.05 * K, yt + THICK, CHAIR)]
                for x in (x0, x1 - THICK * 0.7):
                    bits.append(rect(x, yt + THICK, x + THICK * 0.7, FL, CHAIR_DK))
                z = h - 0.1
            n = max(1, round((h - z) / 0.12))
            tk = (h - z) / n
            for i_ in range(n):
                ya, yb = sup_y(z + tk * (i_ + 1)), sup_y(z + tk * i_)
                bits.insert(0, rrect(x0 + 0.01 * K * (i_ % 2), ya - (TOPF * 0.5 if i_ == n - 1 else 0), x1, yb, tk * K * 0.45,
                                     PILLOW_C, stroke=PILLOW_LN))
            solid_layer('travesseiro', bits)
        elif PROPS & {'wobble', 'board', 'bosu', 'bosuflat'}:
            c, r = (x0 + x1) / 2, (x1 - x0) / 2
            yf = yn - TOPF
            if 'wobble' in PROPS:
                bits = [rrect(c - r, yf, c + r, FL, (FL - yf) * 0.45, WOBBLE_C)]
            elif 'board' in PROPS:
                bits = [rrect(c - r, yf, c + r, yn + 0.025 * K, 3, STEP_TOP),
                        ellipse(c, FL, (h - 0.025) * K, (h - 0.025) * K, STEP_C, n=14)]
            elif 'bosuflat' in PROPS:
                bits = [rrect(c - r, yf, c + r, yn + 0.03 * K, 3, STEP_TOP),
                        group('cupula', path_of([(c - r, yn + 0.03 * K), (c + r, yn + 0.03 * K), (c + 0.1 * K, FL), (c - 0.1 * K, FL)]), fill=BOSU_C)]
            else:
                dome = [[c + r * math.cos(a), FL - (FL - yf + 4) * math.sin(a)] for a in np.linspace(0, math.pi, 9)]
                bits = [rect(c - r - 4, FL - 0.03 * K, c + r + 4, FL, STEP_TOP), group('cupula', smooth_path(dome), fill=BOSU_C)]
            PROP_PTS.extend([[c - r, yf], [c + r, FL]])
            solid_layer('disco', bits)
        elif 'bed' in PROPS:
            solid_layer('cama', [rect(x0, yn - TOPF, x1, yn, BED_C), rect(x0, yn, x1, yn + 0.12 * K, BED_C),
                                 rect(x0 - 3, yn + 0.12 * K, x1 + 3, FL, BED_BASE)][::-1])
        else:                                           # an aerobic step: grey block, dark rubber top
            solid_layer('degrau', [rect(x0, yn - TOPF, x1, yn + 0.02 * K, STEP_TOP), rect(x0, yn, x1, FL, STEP_C)])
    DONE |= {'chairbox', 'pillow', 'wobble', 'board', 'bosu', 'bosuflat', 'step'}
    if 'bed' in PROPS:
        DONE.add('bed')
elif PROPS & {'wobble', 'board', 'bosu', 'bosuflat'} and float(GROUND.get('base', 0.0)) > 0.03:
    # the move was built with the floor raised to the disc's top (ground "base", no box): the feet stand on FL, the
    # disc is drawn under them down to the real floor
    hb = float(GROUND['base']) * K
    xs = [foot_pt(f, s_)[0] for f in range(0, N, 4) for s_ in 'LR']
    c, r = (min(xs) + max(xs)) / 2, max(0.2 * K, (max(xs) - min(xs)) / 2 + 0.08 * K)
    yf, yb = FL - TOPF, FL + hb
    if 'wobble' in PROPS:
        bits = [rrect(c - r, yf, c + r, yb, (yb - yf) * 0.45, WOBBLE_C)]
    elif 'board' in PROPS:
        bits = [rrect(c - r, yf, c + r, FL + 0.025 * K, 3, STEP_TOP), ellipse(c, yb, hb - 0.025 * K, hb - 0.025 * K, STEP_C, n=14)]
    elif 'bosuflat' in PROPS:
        bits = [rrect(c - r, yf, c + r, FL + 0.03 * K, 3, STEP_TOP),
                group('cupula', path_of([(c - r, FL + 0.03 * K), (c + r, FL + 0.03 * K), (c + 0.1 * K, yb), (c - 0.1 * K, yb)]), fill=BOSU_C)]
    else:
        dome = [[c + r * math.cos(a), yb - (yb - yf + 4) * math.sin(a)] for a in np.linspace(0, math.pi, 9)]
        bits = [rect(c - r - 4, yb - 0.03 * K, c + r + 4, yb, STEP_TOP), group('cupula', smooth_path(dome), fill=BOSU_C)]
    PROP_PTS.extend([[c - r, yf], [c + r, yb]])
    solid_layer('disco', bits)
    DONE |= {'wobble', 'board', 'bosu', 'bosuflat'}

# --- supports under planted hands (no ground box): a chair beside the body, a chair in front, a table
if PROPS & {'support', 'side'}:
    hipx = float(np.median([hip_px(f)[0] for f in range(N)]))
    if 'support' in PROPS:                          # both hands on a backrest in front of the body (drawn behind it)
        fs = [f for f in range(N) if FLAT['L'][f] or FLAT['R'][f]] or list(range(N))
        xs = [grip(f, s)[0] for f in fs for s in VIRT]
        h = min(VIRT.values())
        yn = sup_y(h)
        x0, x1 = min(xs) - 0.06 * K, max(xs) + 0.06 * K
        # only the backrest: its top rail under the palms and its two posts (seen through the body, the seat would
        # cross the legs like a bar)
        bits = [rect(x0, yn - TOPF * 0.6, x1, yn, CHAIR_TOP), rrect(x0, yn, x1, yn + THICK, 3, CHAIR)]
        for x in (x0 + THICK * 0.4, x1 - THICK * 0.4):
            bits.append(rect(x - THICK * 0.4, yn, x + THICK * 0.4, FL, CHAIR_DK))
        solid_layer('cadeira', bits[::-1])
    else:
        for s, h in VIRT.items():
            fs = [f for f in range(N) if FLAT[s][f]] or list(range(N))
            hx = float(np.median([grip(f, s)[0] for f in fs]))
            out = 1.0 if hx > hipx else -1.0
            # the backrest's top under the heel of the hand: the post a little in from the fingers
            solid_layer('cadeira', chair_profile(hx - out * 0.01 * K, out, sup_y(h), FL - 0.45 * K)[::-1])
    DONE |= {'support', 'side'}
if 'table' in PROPS and not BOXES and VIRT:
    h = min(VIRT.values())
    hipx = float(np.median([hip_px(f)[0] for f in range(N)]))
    gx = [grip(f, s)[0] for s in VIRT for f in range(N)]
    if len(VIRT) == 1:                              # one hand on it: a small table extending away from the body
        hx = float(np.median(gx))
        out = 1.0 if hx > hipx else -1.0
        x0, x1 = hx - out * 0.15 * K, hx + out * 0.4 * K
    else:
        x0, x1 = min(gx) - 0.2 * K, max(gx) + 0.2 * K
    x0, x1 = sorted((x0, x1))
    yn = sup_y(h)
    bits = [rect(x0, yn - TOPF, x1, yn, CHAIR_TOP), rrect(x0, yn, x1, yn + THICK, 2, CHAIR)]
    for x in (x0 + 0.04 * K, x1 - 0.04 * K - THICK * 0.7):
        bits.append(rect(x, yn + THICK, x + THICK * 0.7, FL, CHAIR_DK))
    solid_layer('mesa', bits[::-1])
    DONE.add('table')

# --- walls: one behind the back is a panel behind the body; one beside it (wallat-*-L/R) a strip at that side.
# (A wall in front of the body, 'wall', stands between the camera and the figure: not drawn in the front view.)
xs_body = [float(x) for f in range(0, N, 3) for x in (hip_px(f)[0],)]
if PROPS & {'wallback', 'wallball'}:
    c = float(np.median(xs_body))
    solid_layer('parede', [rect(c - 0.75 * K, FL - 2.2 * K, c + 0.75 * K, FL, WALL_C, track=False)])
    PROP_PTS.extend([[c - 0.5 * K, FL - 2.0 * K], [c + 0.5 * K, FL]])
    DONE |= {'wallback', 'wallball'}
for wa in [p for p in PROPS if p.startswith('wallat-')]:
    _, end, dr = wa.split('-')
    if dr[0] not in 'LR':
        continue
    sgn = 1 if dr[0] == 'L' else -1                 # the figure's left is screen right
    pts_ = [end_pt(f, end) for f in range(N)]
    far_x = max(p[0] * sgn for p in pts_) * sgn + sgn * 0.03 * K
    if dr.endswith('p'):
        solid_layer('batente', [rect(far_x, FL - 2.2 * K, far_x + sgn * 0.12 * K, FL, CHAIR)])
    else:
        solid_layer('parede', [rect(far_x, FL - 2.4 * K, far_x + sgn * 0.1 * K, FL, WALL_C)])
for wp in [p for p in PROPS if p.startswith('wallpress-')]:
    _, end, dr = wp.split('-')
    sgn = {'L': 1, 'R': -1}.get(dr, 0)
    if not sgn:
        continue
    rb = 0.11 * K
    pts_ = [end_pt(f, end) for f in range(N)]
    far_x = max(p[0] * sgn for p in pts_) * sgn
    solid_layer('parede', [rect(far_x + sgn * 2 * rb, FL - 2.2 * K, far_x + sgn * (2 * rb + 0.1 * K), FL, WALL_C)])
    moving_layer('bola', [ellipse(0, 0, rb, rb, BALL_C, False)], [p + np.array([sgn * rb, 0.0]) for p in pts_],
                 where=IN_FRONT, r_track=rb)

# --- top view (top_view.py): the floor is the page; a mat (or the bed's top) under the whole body, a pillow under
# the head, all behind the figure
if TOP:
    xs, ys = [], []
    for f in range(0, N, 3):
        for nm in ('cabeca', 'pe L', 'pe R', 'quadril', 'mao L', 'mao R', 'joelho L', 'joelho R'):
            if nm in POSES[f]:
                p_ = piece_pts(nm, POSES[f][nm], f)
                xs += [float(p_[:, 0].min()), float(p_[:, 0].max())]
                ys += [float(p_[:, 1].min()), float(p_[:, 1].max())]
    cx = (min(xs) + max(xs)) / 2
    hw = max(0.36 * K, (max(xs) - min(xs)) / 2 + 0.08 * K)
    y0, y1 = min(ys) - 0.12 * K, max(ys) + 0.1 * K
    if 'bed' in PROPS:
        solid_layer('cama', [rrect(cx - hw - 0.1 * K, y0 - 0.05 * K, cx + hw + 0.1 * K, y1 + 0.05 * K, 0.03 * K, BED_C, stroke=BED_BASE)])
    else:
        solid_layer('colchonete', [rrect(cx - hw, y0, cx + hw, y1, 0.04 * K, MAT_TOP, stroke=MAT_C)])
    if 'pillow' in PROPS:
        hd = place(POSES[0]['cabeca'], np.array([0.0, 0.5 * PC['cabeca']['len']]))
        solid_layer('travesseiro', [rrect(hd[0] - 0.26 * K, hd[1] - 0.3 * K, hd[0] + 0.26 * K, hd[1] + 0.14 * K, 0.05 * K,
                                          PILLOW_C, stroke=PILLOW_LN)])
    DONE |= {'bed', 'mat', 'pillow'}
# --- floor things: bed / mat under a lying body, a pillow under the head, a step, marks, a ladder
if 'bed' in PROPS and 'bed' not in DONE:
    xs = [float(piece_pts(nm, POSES[f][nm], f)[:, 0].min()) for f in range(0, N, 3) for nm in ('cabeca', 'pe L', 'pe R', 'quadril')]
    xs += [float(piece_pts(nm, POSES[f][nm], f)[:, 0].max()) for f in range(0, N, 3) for nm in ('cabeca', 'pe L', 'pe R', 'quadril')]
    x0, x1 = min(xs) - 0.15 * K, max(xs) + 0.15 * K
    drop = 0.55 * K
    solid_layer('cama', [rect(x0, FL - TOPF, x1, FL, BED_C), rect(x0, FL, x1, FL + 0.14 * K, '#E9EEF4'),
                         rect(x0 - 3, FL + 0.14 * K, x1 + 3, FL + drop - 0.08 * K, BED_BASE),
                         rect(x0 + 0.04 * K, FL + drop - 0.08 * K, x0 + 0.08 * K, FL + drop, CHAIR_DK),
                         rect(x1 - 0.08 * K, FL + drop - 0.08 * K, x1 - 0.04 * K, FL + drop, CHAIR_DK)][::-1])
    DONE.add('bed')
elif not TOP and ('mat' in PROPS or (FLOOR and not PROPS & {'chair', 'chairfit', 'bed', 'swissseat'})):
    xs = []
    for f in range(0, N, 3):
        for nm in ('cabeca', 'pe L', 'pe R', 'quadril', 'mao L', 'mao R'):
            p_ = piece_pts(nm, POSES[f][nm], f)
            xs += [float(p_[:, 0].min()), float(p_[:, 0].max())]
    x0, x1 = min(xs) - 0.15 * K, max(xs) + 0.15 * K
    solid_layer('colchonete', [rect(x0, FL - TOPF * 0.8, x1, FL + 2, MAT_TOP), rect(x0, FL + 2, x1, FL + max(8, 0.02 * K), MAT_C)][::-1])
if 'pillow' in PROPS and 'pillow' not in DONE:
    if FLOOR:                                       # under the head of a lying body
        hd = place(POSES[0]['cabeca'], np.array([0.0, 0.5 * PC['cabeca']['len']]))
        solid_layer('travesseiro', [rrect(hd[0] - 0.2 * K, FL - 0.09 * K - TOPF * 0.5, hd[0] + 0.2 * K, FL, 0.04 * K, PILLOW_C, stroke=PILLOW_LN)])
    DONE.add('pillow')
if 'step' in PROPS and 'step' not in DONE:
    # no ground box: a 20 cm step under the soles that are highest in 3D
    hi_f = min(range(N), key=lambda f: min(QA[f]['sh'][s][0] for s in 'LR'))
    xs = [foot_pt(hi_f, s)[0] for s in 'LR']
    x0, x1 = min(xs) - 0.2 * K, max(xs) + 0.2 * K
    solid_layer('degrau', [rect(x0, FL - 0.2 * K - TOPF, x1, FL - 0.18 * K, STEP_TOP), rect(x0, FL - 0.2 * K, x1, FL, STEP_C)])
if 'marks' in PROPS:
    bits = []
    for s in 'LR':
        spots = []
        for f in range(N):
            if QA[f]['fz'][s] < 0.015:
                q = foot_pt(f, s)
                if spots and abs(spots[-1][-1] - q[0]) < 0.08 * K:
                    spots[-1].append(q[0])
                else:
                    spots.append([q[0]])
        for sp_ in spots:
            bits.append(ellipse(float(np.mean(sp_)), FL - 2, 0.075 * K, 0.018 * K, MARK_C))
    solid_layer('marcas', bits)
if 'line' in PROPS:
    xs = [hip_px(f)[0] for f in range(N)]
    c = (max(xs) + min(xs)) / 2
    solid_layer('fita', [rect(c - 0.02 * K, FL - TOPF, c + 0.02 * K, FL + 2, TAPE_C)])
ladders = [p for p in PROPS if p.startswith('ladder-')]
if ladders:                                         # an agility ladder on the floor, running across the screen
    step_m = int(ladders[0].split('-')[1]) / 100
    xs = [foot_pt(f, s)[0] for f in range(N) for s in 'LR']
    x0, x1 = min(xs) - 0.6 * K, max(xs) + 0.6 * K
    rail = max(4.0, 0.012 * K)
    bits = [rect(x0, FL - TOPF - rail * 0.5, x1, FL - TOPF + rail * 0.5, LADDER_C), rect(x0, FL - rail, x1, FL, LADDER_C)]
    x = x0
    while x < x1:
        bits.append(rect(x, FL - TOPF, x + rail, FL, LADDER_C, track=False, nm='degrau'))
        x += step_m * K
    solid_layer('escada', bits)
if 'roll' in PROPS:
    kn = knee_pt(0, 'R')
    r = 0.07 * K
    solid_layer('rolo', [ellipse(kn[0], FL - r, r * 1.6, r, ROLL_C, n=12)])

# --- worn and held things
if 'cuff' in PROPS:                                 # ankle weights: drawn in the shin's own layer, above the ankle
    for s in 'LR':
        Pp = bez_points(SHAPES['perna ' + s])
        L_ = PC['perna ' + s]['len']
        y_ = L_ - 0.07 * K
        row = Pp[np.abs(Pp[:, 1] - y_) < 6]
        x0, x1 = (float(row[:, 0].min()), float(row[:, 0].max())) if len(row) else (-12.0, 12.0)
        in_piece(copies('perna ' + s), [rrect(x0 - 4, y_ - 0.035 * K, x1 + 4, y_ + 0.035 * K, 6, '#334155', False, 'caneleira')])
if 'dumbbell' in PROPS:
    # in the fist (the hand's own layer, so it keeps the hand's place in the layer order): the bar across the fist,
    # a plate each side, as a dumbbell seen three-quarter (end-on from the front it would hide the hand)
    for s in 'LR':
        g = HG[s]
        hw = g['hw']
        cy = float(g['grip'][1])
        pr, pw, bt = 0.042 * K, 0.034 * K, 0.011 * K
        off = 1.25 * hw + pw * 0.5
        plates = [rrect(-off - pw / 2, cy - pr, -off + pw / 2, cy + pr, 4, DB_C, False, 'anilha'),
                  rrect(off - pw / 2, cy - pr, off + pw / 2, cy + pr, 4, DB_C, False, 'anilha')]
        bar = rect(-off, cy - bt, off, cy + bt, DB_HI, False, 'barra')
        for nm in copies('mao ' + s):
            for gr_ in LAY[nm]['shapes']:
                if gr_['nm'] == 'punho':
                    gr_['it'] = copy.deepcopy(plates) + gr_['it'][:-1] + [copy.deepcopy(bar), gr_['it'][-1]]
        for f in range(0, N, 3):
            c_ = grip(f, s)
            PROP_PTS.extend([[c_[0] - off - pw, c_[1] - off - pw], [c_[0] + off + pw, c_[1] + off + pw]])
if 'ball' in PROPS or 'kneepillow' in PROPS:
    # squeezed between the knees: between the legs (behind them), as wide as the gap
    r = 0.1 * K
    ps, ss = [], []
    for f in range(N):
        a_, b_ = knee_pt(f, 'R'), knee_pt(f, 'L')
        gap = abs(b_[0] - a_[0]) - 0.8 * JR['kneeWL']
        ps.append((a_ + b_) / 2 + np.array([0.0, 0.02 * K]))
        ss.append((float(np.clip(gap / (2 * r), 0.5, 1.0)) * 100, 100))
    if 'ball' in PROPS:
        moving_layer('bola', [ellipse(-r * 0.35, -r * 0.4, r * 0.22, r * 0.13, '#F6BC82', False, 'brilho'),
                              ellipse(0, 0, r, r, BALL_C, False)], ps, where='behind', r_track=r, ss=ss)
    else:
        moving_layer('travesseiro', [rrect(-0.1 * K, -0.07 * K, 0.1 * K, 0.07 * K, 0.04 * K, PILLOW_C, False, stroke=PILLOW_LN)],
                     ps, where='behind', r_track=0.1 * K, ss=ss)
for ap in [p for p in PROPS if p.startswith('armpillow')]:
    s = ap[-1]
    ps = [(drawn(f, 'antebraco ' + s) + drawn(f, 'mao ' + s)) / 2 for f in range(N)]
    moving_layer('travesseiro', [rrect(-0.12 * K, -0.05 * K, 0.12 * K, 0.05 * K, 0.04 * K, PILLOW_C, False, stroke=PILLOW_LN)],
                 ps, where=('below', 'antebraco ' + s), r_track=0.12 * K)
if 'heldball' in PROPS:
    # a ball between the palms (radius from the palms' 3D distance, render_mannequin), over the torso, under the arms
    pl3 = np.linalg.norm(palm3(frames[0], 'L') - palm3(frames[0], 'R'))
    rb = min(max(pl3 / 2 - 0.035, 0.08), 0.3) * K
    ps = [(grip(f, 'R') + grip(f, 'L')) / 2 for f in range(N)]
    moving_layer('bola', [ellipse(-rb * 0.35, -rb * 0.4, rb * 0.22, rb * 0.13, '#F6BC82', False, 'brilho'),
                          ellipse(0, 0, rb, rb, BALL_C, False, n=14)], ps, where=('above', 'tronco'), r_track=rb)
if 'waistball' in PROPS:
    rb = 0.1 * K
    ps = [grip(f, 'R' if f < N / 2 else 'L') for f in range(N)]
    moving_layer('bola', [ellipse(0, 0, rb, rb, BALL_C, False)], ps, where=IN_FRONT, r_track=rb)

# --- elastic bands, towels
BT = max(2.4, 0.008 * K)                       # band half thickness
if 'bandhands' in PROPS:
    bar_between([grip(f, 'L') for f in range(N)], [grip(f, 'R') for f in range(N)], 'faixa', BAND_C, BT, where=IN_FRONT)


def post_at(x, top_y, nm='batente', anchor_y=None):
    """A post (door frame) the band is tied to; only its lower part counts for the framing (a tall post would
    shrink the figure), the rest may run out of the frame."""
    solid_layer(nm, [rect(x - 0.025 * K, top_y, x + 0.025 * K, FL, CHAIR, track=False)])
    PROP_PTS.extend([[x - 0.03 * K, (anchor_y if anchor_y is not None else FL - 1.0 * K) - 0.15 * K], [x + 0.03 * K, FL]])


if PROPS & {'bandanchor', 'bandanchor1'}:
    sides = ['L', 'R']
    if 'bandanchor1' in PROPS:
        trav = {s: max(np.linalg.norm(palm3(fr, s) - palm3(frames[0], s)) for fr in frames) for s in 'LR'}
        sides = [max(trav, key=trav.get)]
    p0 = np.mean([palm3(frames[0], s) for s in sides], axis=0)
    sh0 = np.mean([jp(frames[0], 'arm' + s) for s in sides], axis=0)
    dv = p0 - sh0
    dv[2] = 0
    dv = dv / np.linalg.norm(dv) if np.linalg.norm(dv) > 0.05 else CAM
    anc = np.mean([grip(0, s) for s in sides], axis=0) + np.array([P(dv)[0], 0.0]) * 0.55 * K
    if abs(P(dv)[0]) > 0.3:                    # beside the body: its post shows
        post_at(anc[0], FL - 2.0 * K)
    for s in sides:
        bar_between([grip(f, s) for f in range(N)], [anc] * N, 'faixa ' + s, BAND_C, BT, where=IN_FRONT)
if 'bandfeet' in PROPS:
    for s in 'LR':
        bar_between([grip(f, s) for f in range(N)], [foot_pt(f, s) for f in range(N)], 'faixa ' + s, BAND_C, BT, where=IN_FRONT)
if PROPS & {'bandknees', 'bandankles'}:
    # a loop round both thighs above the knees (or both shins above the ankles): seen from the front, a strip across
    # both legs, over them, stretching as they part
    for kind in [k for k in ('bandknees', 'bandankles') if k in PROPS]:
        pa, pb = [], []
        for f in range(N):
            if kind == 'bandknees':
                a_, b_ = thigh_pt(f, 'R', 0.09), thigh_pt(f, 'L', 0.09)
                hw_ = 0.5 * JR['kneeWL'] * 1.05
            else:
                a_, b_ = shin_pt(f, 'R', 0.07), shin_pt(f, 'L', 0.07)
                hw_ = 0.5 * JR['ankleWL'] * 1.25
            u_ = (b_ - a_) / max(np.linalg.norm(b_ - a_), 1e-6)
            pa.append(a_ - u_ * hw_)
            pb.append(b_ + u_ * hw_)
        bar_between(pa, pb, 'faixa', BAND_C, BT * 1.5,
                    where=('above', top_of('coxa L', 'coxa R ^') if kind == 'bandknees' else top_of('pe L', 'perna L', 'pe R ^', 'perna R ^')))
# band-<end>-<end> and towel-<end>-<end> (render_mannequin): ends are body points or a post F/B/L/R 0.6 m from the
# other end's start at its height (lo/hi: 12 cm / 1.95 m). From the front the L/R posts stand beside the body (the
# side view cannot show them); F/B posts are in front of / behind the body, on its own line of sight.
for bp in sorted(p for p in PROPS if p.startswith(('band-', 'towel-'))):
    ends = bp.split('-')[1:]
    towel = bp.startswith('towel-')
    tracks = []
    for i_, e_ in enumerate(ends):
        if e_[0] in 'FBLR' and (len(e_) == 1 or e_[1:] in ('lo', 'hi')):
            other = ends[1 - i_]
            o2 = end_pt(0, other)
            dx = {'L': 0.6, 'R': -0.6}.get(e_[0], 0.0) * K
            zy = {'lo': FL - 0.12 * K, 'hi': FL - 1.95 * K}.get(e_[1:], o2[1])
            anc = np.array([o2[0] + dx, zy])
            if e_[0] in 'LRB':
                post_at(anc[0], min(FL - 2.0 * K, zy - 0.1 * K), anchor_y=zy)
            else:                                   # in front: the band runs at the camera; a short stub reads as one
                anc = anc + np.array([0.0, 0.03 * K])
            tracks.append([anc] * N)
        else:
            tracks.append([end_pt(f, e_) for f in range(N)])
    where = ('below', 'tronco') if any(e_[0] == 's' for e_ in ends) else IN_FRONT
    if towel:
        bar_between(tracks[0], tracks[1], 'toalha', TOWEL_C, max(6.0, 0.02 * K), where=where)
    else:
        bar_between(tracks[0], tracks[1], 'faixa', BAND_C, BT, where=where)

# --- sticks, canes, walkers
STICK_L = 1.05
for sp in sorted(p for p in PROPS if p == 'stick' or p.startswith(('stick-', 'stickend-', 'stickfloor-'))):
    kind, *ends = sp.split('-')
    ends = ends or ['hL', 'hR']
    A_ = [end_pt(f, ends[0]) for f in range(N)]
    B_ = [end_pt(f, ends[-1]) for f in range(N)]
    if kind == 'stickfloor':
        top0 = (A_[0] + B_[0]) / 2
        tip = np.array([top0[0], FL])
        L0 = float(np.linalg.norm(top0 - tip)) + 0.06 * K
        tops = []
        for f in range(N):
            top = (A_[f] + B_[f]) / 2
            dv = top - tip
            tops.append(tip + dv / np.linalg.norm(dv) * max(L0, np.linalg.norm(dv) + 0.04 * K))
        bar_between([tip] * N, tops, 'bastao', STICK_C, max(3.5, 0.013 * K), where=IN_FRONT)
        continue
    # the stick's own 3D length and direction, projected: pointing at the camera it is seen end-on, a short stub
    pa3 = [end3(fr, ends[0]) for fr in frames]
    pb3 = [end3(fr, ends[-1]) for fr in frames]
    E0, E1 = [], []
    for f in range(N):
        c3 = float(np.linalg.norm(pb3[f] - pa3[f]))
        full = max(STICK_L, c3 + 0.2)
        proj = float(np.linalg.norm(P(pb3[f]) - P(pa3[f])))
        ln = full * (proj / c3 if c3 > 1e-3 else 0.0) * K
        dv = B_[f] - A_[f]
        if ln < 0.2 * K or np.linalg.norm(dv) < 8:
            dv, ln = np.array([1.0, 0.0]), 0.2 * K
        dv = dv / np.linalg.norm(dv)
        if kind == 'stickend':
            E0.append(A_[f] - dv * 0.05 * K)
            E1.append(A_[f] + dv * (ln - 0.05 * K))
        else:
            c = (A_[f] + B_[f]) / 2
            E0.append(c - dv * ln / 2)
            E1.append(c + dv * ln / 2)
    bar_between(E0, E1, 'bastao', STICK_C, max(3.5, 0.013 * K), where=IN_FRONT)
for cp in [p for p in PROPS if p in ('caneL', 'caneR')]:
    s = cp[-1]
    tops = [grip(f, s) for f in range(N)]
    out = 1.0 if s == 'L' else -1.0
    bots = [np.array([t[0] + out * 0.03 * K, FL]) for t in tops]
    bar_between(bots, tops, 'bengala', STICK_C, max(3.5, 0.012 * K), where=('above', 'mao ' + s))
    bar_between([t + np.array([-0.05 * K, -0.02 * K]) for t in tops], [t + np.array([0.05 * K, -0.02 * K]) for t in tops],
                'bengala cabo', GRIP_C, max(4.0, 0.015 * K), where=('above', 'mao ' + s))
if PROPS & {'walker', 'walkergo'}:
    # a walker seen from the front, just in front of the body: a frame each side under the hands (handle, legs, a
    # front wheel), the cross bar low in front
    fs = list(range(N)) if 'walkergo' in PROPS else [min(range(N), key=lambda i: float(grip(i, 'L')[1] + grip(i, 'R')[1]))] * N
    tb = max(5.0, 0.014 * K)
    ps, shapes = [], None
    for f in fs:
        gl, gr = grip(f, 'L'), grip(f, 'R')
        ps.append(np.array([(gl[0] + gr[0]) / 2, (gl[1] + gr[1]) / 2]))
    hz_ = float(np.mean([p[1] for p in ps]))
    ps = [np.array([p[0], hz_]) for p in ps]
    half = abs(float(np.median([grip(f, 'L')[0] - grip(f, 'R')[0] for f in fs]))) / 2 + 0.03 * K
    hgt = FL - hz_
    shapes = []
    for sx in (-1, 1):
        x = sx * half
        shapes += [rrect(x - tb * 1.1, -tb * 0.8, x + tb * 1.1, 0.07 * K, tb, GRIP_C, False, 'pega'),
                   rect(x - tb * 0.5, 0, x + tb * 0.5, hgt - 0.04 * K, WALKER_C, False, 'perna'),
                   ellipse(x, hgt - 0.04 * K, 0.035 * K, 0.04 * K, GRIP_C, False, 'roda')]
    shapes.append(rect(-half, hgt * 0.55 - tb * 0.4, half, hgt * 0.55 + tb * 0.4, WALKER_C, False, 'travessa'))
    moving_layer('andador', shapes, ps, where=('above', 'tronco'))
    for p in ps[::3]:
        PROP_PTS.extend([[p[0] - half - tb, p[1] - tb], [p[0] + half + tb, FL]])
if 'pulley' in PROPS:
    nk = drawn(0, 'cabeca')
    c = nk + np.array([0.0, -PC['cabeca']['len'] - 0.45 * K])
    r = max(10.0, 0.05 * K)
    solid_layer('roldana', [rect(c[0] - 3, c[1] - 0.4 * K, c[0] + 3, c[1], CHAIR_DK), ellipse(c[0], c[1], r, r, GRIP_C)])
    for s in 'LR':
        bar_between([grip(f, s) for f in range(N)], [c] * N, 'corda ' + s, BAND_C, max(1.8, 0.006 * K), where=IN_FRONT)

# --- exercise balls under a part (render_mannequin.support_ball), small balls under a foot / hand
for kind in sorted(p for p in PROPS if p.startswith(('ballfeet', 'ballhands', 'ballarms', 'ballback'))):
    part, side = (kind[:-1], kind[-1]) if kind[-1] in 'LR' else (kind, None)
    ss_ = [side] if side else ['L', 'R']
    ps, rr = [], []
    for f in range(N):
        if part == 'ballfeet':
            pts_ = [foot_pt(f, s) for s in ss_]
            low = max(p[1] for p in pts_)
        elif part == 'ballarms':
            pts_ = [(drawn(f, 'antebraco ' + s) + drawn(f, 'mao ' + s)) / 2 for s in ss_]
            low = max(p[1] for p in pts_) + HG['R']['hw']
        elif part == 'ballhands':
            pts_ = [grip(f, s) for s in ss_]
            low = max(p[1] for p in pts_) + HG['R']['hw']
        else:
            pts_ = [hip_px(f)]
            low = pts_[0][1] + 0.12 * K
        r = float(np.clip((FL - low) / 2, 0.18 * K, 0.33 * K))
        ps.append([float(np.mean([p[0] for p in pts_])), FL - r])
        rr.append(r)
    r = float(np.median(rr))
    if part == 'ballhands':
        ps = [ps[0]] * N
    ps = [[p[0], FL - r] for p in ps]
    moving_layer('bola suica', [ellipse(-r * 0.35, -r * 0.42, r * 0.2, r * 0.12, SWISS_HI, False, 'brilho'),
                                ellipse(0, 0, r, r, SWISS_C, False, n=16)], ps, where='behind', r_track=r)
for pp in [p for p in PROPS if p.startswith('pball-')]:
    _, size, part = pp.split('-')
    static = part.endswith('0')
    part = part[:2]
    r = {'v': 0.11, 't': 0.034}[size] * K
    col = BALL_C if size == 'v' else '#C8E64A'
    s = part[1]
    pts_ = []
    for f in range(N):
        q = grip(f, s) if part[0] == 'h' else foot_pt(f, s) if part[0] == 'f' else knee_pt(f, s)
        pts_.append([q[0], FL - r])
    if static:
        pts_ = [pts_[0]] * N
    moving_layer('bola', [ellipse(0, 0, r, r, col, False)], pts_, where='behind', r_track=r)
_not = sorted(p for p in PROPS if p == 'wall' or p == 'throw' or p.startswith(('throw-', 'tableball')) or
              (p.startswith('wallat-') and p.split('-')[2][0] in 'FB') or (p.startswith('wallpress-') and p.split('-')[2] in 'FB'))
if PROPS:
    print('PROPS', sorted(PROPS), 'not drawn in the front view:', _not)

# ---------- keys of the body pieces. Every piece is parented to a null that carries the pelvis: the pieces' own
# position tracks are then relative to it and nearly still whenever a limb rests on the body (far fewer keys).
BODY_P = [[round(float(POSES[f]['tronco'][0][0]), 1), round(float(POSES[f]['tronco'][0][1]), 1)] for f in range(N)]
NULL = {'ddd': 0, 'ind': 0, 'ty': 3, 'nm': 'corpo', 'sr': 1,
        'ks': {'o': {'a': 0, 'k': 0}, 'r': {'a': 0, 'k': 0}, 'p': anim([v + [0] for v in BODY_P], 3, tol=0.1),
               'a': {'a': 0, 'k': [0, 0, 0]}, 's': {'a': 0, 'k': [100, 100, 100]}},
        'ao': 0, 'ip': 0, 'op': N, 'st': 0, 'bm': 0}
comp['layers'].append(NULL)
_drop = []
for nm, lay in list(LAY.items()):
    if nm == 'shadow':
        continue
    b = base_of(nm)
    vis = [visible(nm, f) for f in range(N)]
    if not any(vis):
        _drop.append(nm)
        continue
    con = contact_frames(b)
    tp = [0.1 if c else TOL['p'] for c in con]
    switch = [f for f in range(1, N) if vis[f] != vis[f - 1]] + [f - 1 for f in range(1, N) if vis[f] != vis[f - 1]]
    # relative to the pelvis null, or in the comp's own frame when that takes fewer keys (a planted foot stands still)
    p_rel = anim([[round(float(POSES[f][b][0][0]) - BODY_P[f][0], 1), round(float(POSES[f][b][0][1]) - BODY_P[f][1], 1), 0]
                  for f in range(N)], 3, tol=tp, care=vis, keep=switch)
    p_abs = anim([[round(float(POSES[f][b][0][0]), 1), round(float(POSES[f][b][0][1]), 1), 0] for f in range(N)], 3,
                 tol=tp, care=vis, keep=switch)
    nk = lambda t_: len(t_['k']) if t_.get('a') == 1 else 1
    if nk(p_rel) < nk(p_abs):
        lay['ks']['p'] = p_rel
        lay['parent'] = 'corpo'
    else:
        lay['ks']['p'] = p_abs
        lay.pop('parent', None)
    lay['ks']['r'] = anim([round(float(v), 2) for v in ROT[b]], 1, tol=TOL['r'], care=vis, keep=switch)
    sc = [(POSES[f][b][2], POSES[f][b][3]) for f in range(N)]
    if any(abs(a - 1) > 1e-3 or abs(c - 1) > 1e-3 for a, c in sc):
        lay['ks']['s'] = anim([[round(a * 100, 1), round(c * 100, 1), 100] for a, c in sc], 3, tol=TOL['s'], care=vis, keep=switch)
    else:
        lay['ks']['s'] = {'a': 0, 'k': [100, 100, 100]}
    lay['ks']['o'] = anim([100 if v else 0 for v in vis], 1, hold=True)
    if b.startswith('mao '):
        s = b[-1]
        kinds = [hand_kind(f, s) for f in range(N)]
        for gr_ in lay['shapes']:
            tr_ = gr_['it'][-1]
            want = {'mao aberta': 'open', 'punho': 'fist', 'mao apoiada': 'flat'}[gr_['nm']]
            tr_['o'] = anim([100 if k_ == want else 0 for k_ in kinds], 1, hold=True)
            if want == 'flat' and any(FLAT[s][f] and PDIR[s][f] < 0 for f in range(N)):
                tr_['s'] = anim([[-100, 100] if FLAT[s][f] and PDIR[s][f] < 0 else [100, 100] for f in range(N)], 2, hold=True)
        lay['shapes'] = [gr_ for gr_ in lay['shapes'] if any(
            hand_kind(f, s) == {'mao aberta': 'open', 'punho': 'fist', 'mao apoiada': 'flat'}[gr_['nm']] for f in range(N))]
comp['layers'] = [l for l in comp['layers'] if l['nm'] not in _drop]
print('LAYERS dropped (never drawn)', len(_drop))
sh_l = LAY['shadow']
sh_l['ks']['p'] = anim([[round(x, 1), round(y, 1), 0] for x, y, _, _ in SHADOW], 3, tol=TOL['p'])
sh_l['ks']['s'] = anim([[round(sx * 100, 1), round(sy * 100, 1), 100] for _, _, sx, sy in SHADOW], 3, tol=TOL['s'])

for i_, l in enumerate(comp['layers']):
    l['ip'], l['op'] = 0, N
    l['ind'] = i_ + 1
for l in comp['layers']:
    if l.get('parent') == 'corpo':
        l['parent'] = NULL['ind']
d['ip'], d['op'], d['fr'] = 0, N, 30
for l in d['layers']:
    l['ip'], l['op'] = 0, N

# ---------- framing (as drive_puppet): the whole motion fits with a margin, never enlarged past the drawing's size;
# the floor sits where the side puppet's floor sits when the motion fits at full size
pts = []
for f in range(0, N, 2):
    for nm in LAY:
        if nm == 'shadow' or nm in _drop or not visible(nm, f):
            continue
        pts.append(piece_pts(nm, POSES[f][base_of(nm)], f))
pts = np.vstack(pts + ([np.array(PROP_PTS)] if PROP_PTS else []))
x0_, y0_ = pts.min(0)
x1_, y1_ = pts.max(0)
y1_ = max(y1_, FLOOR_PX)
root = d['layers'][0]
W_, H_ = d['w'], d['h']
MT, MB, MS = 0.06 * H_, 0.05 * H_, 0.06 * W_
sc = min(1.0, (H_ - MT - MB) / (y1_ - y0_), (W_ - 2 * MS) / (x1_ - x0_))
py = min(832.36, H_ - MB) if sc >= 1.0 else H_ - MB
# --match=<side lottie of the same move>: same figure size and floor line as the side view (never larger than fits)
MATCH = next((a.split('=', 1)[1] for a in sys.argv if a.startswith('--match=')), None)
if MATCH:
    _md = json.load(open(MATCH))
    _sr = _md['layers'][0]['ks']
    _ss = float(_sr['s']['k'][0]) / 100
    if _ss < sc:
        sc = _ss
    # the side's floor on screen: its shadow sits 0.32 x 52 px below the floor line (drive_puppet), in comp pixels
    _sh = next((l for l in _md['assets'][0]['layers'] if l.get('nm') == 'shadow'), None)
    py = float(_sr['p']['k'][1])
    if _sh is not None and _sh['ks']['p'].get('a') == 1:
        _fy = float(_sh['ks']['p']['k'][0]['s'][1]) - 52.0 * 0.32
        py = float(_sr['p']['k'][1]) + _ss * (_fy - float(_sr['a']['k'][1]))
    y1_ = FLOOR_PX
    if (y1_ - y0_) * sc > py - MT * 0.5:          # keep the top inside the frame
        sc = (py - MT * 0.5) / (y1_ - y0_)
root['ks']['s'] = {'a': 0, 'k': [round(sc * 100, 3), round(sc * 100, 3), 100]}
root['ks']['a'] = {'a': 0, 'k': [round(float((x0_ + x1_) / 2), 2), round(float(y1_), 2), 0]}
root['ks']['p'] = {'a': 0, 'k': [W_ / 2, round(float(py), 2), 0]}
if TOP:
    # laid down: turned 90 deg counter-clockwise about the motion's centre (head to the left), fitted the same way;
    # no floor shadow; a prone body shows the back of the head (no brows / nose)
    y0_ = float(pts[:, 1].min())
    y1_ = float(pts[:, 1].max())
    sc = min(1.0, (W_ - 2 * MS) / (y1_ - y0_), (H_ - MT - MB) / (x1_ - x0_))
    root['ks']['s'] = {'a': 0, 'k': [round(sc * 100, 3), round(sc * 100, 3), 100]}
    root['ks']['a'] = {'a': 0, 'k': [round(float((x0_ + x1_) / 2), 2), round(float((y0_ + y1_) / 2), 2), 0]}
    root['ks']['p'] = {'a': 0, 'k': [W_ / 2, round(H_ * 0.52, 2), 0]}
    root['ks']['r'] = {'a': 0, 'k': -90}
    LAY['shadow']['ks']['o'] = {'a': 0, 'k': 0}
    if TOP['sky'] < 0:
        LAY['cabeca']['shapes'] = [g_ for g_ in LAY['cabeca']['shapes'] if g_.get('nm') not in ('sobrancelha', 'nariz')]
print('FRAME scale', round(sc, 3), 'bbox', [round(float(v)) for v in (x0_, y0_, x1_, y1_)])
json.dump(d, open(OUT, 'w'), separators=(',', ':'))
print('WROTE', OUT, N, 'frames')
