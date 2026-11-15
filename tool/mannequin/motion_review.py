"""Layer 2 of the avatar review: motion quality from <qa>/<id>.motion.npz (motion_qa.py, written by the QA run).

    python3 tool/mannequin/motion_review.py <qa dir> [ids...]      # -> <qa>/<id>.motion.json, prints a line per job

Measures (thresholds at 30 fps in TH, scaled for other rates):
- fluidez: pops (a joint turning more than 8 deg in one frame, 12 in walks and lunges), jerk (a joint's angular acceleration against the
  median of that joint while it moves), teleport (the pelvis moving more than 3 cm in a frame with both feet down),
  easing (each stroke of the main joint slows down to ~0 over several frames before it turns), loop (last frame
  against the first);
- biomecânica: anatomical angles per joint against the limits of LIMITS, balance (the centre of mass over the
  feet when standing on them), compensations (contralateral arm swing and heel strike when walking, knees that
  absorb the landing of a jump), parts at rest (stiff T arm, tremor, slow drift), left/right symmetry, rhythm
  (seconds per repetition) and the length of the holds;
- legibilidade: the moving part visible, its plane facing the camera, its amplitude on screen, repetitions.
Ballistic moves (jumps, runs) skip the pop/teleport limits; stepping moves (walks, lunges, steps) skip the balance
check while a foot is in the air.
Every verdict carries a severity (1 = suspeito, 2 = quebrado); motion_status is the worst one.
"""
import json
import re
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
FPS = 30
TH = dict(
    pop=8.0,              # deg/frame
    pop_step=12.0,        # deg/frame for walks and lunges (approved 13/11)
    wrist_ext_load=90.0,  # deg of wrist extension allowed while the palm bears weight (approved 13/11)
    hold_cap=5.0,         # s: a long hold in the text (e.g. 30 s) is shown capped at this (approved 13/11)
    jerk=3.0,             # x the joint's median angular acceleration while it moves
    jerk_floor=1.0,       # deg/frame^2: smaller peaks are not visible (good moves peak under 0.6)
    jerk_bad=6.0,         # deg/frame^2: a peak this big is a visible kick (quebrado); keyed curves have a tiny median
                          # acceleration, so the ratio alone flags most moves
    teleport=0.03,        # m/frame
    ease_end=0.4,         # last moving frame of a stroke: speed below this share of the stroke's peak
    ease_frames=3,        # frames from 80 % to 20 % of the peak speed at the end of a stroke
    loop_rot=2.0, loop_pos=0.01,
    rom_tol=5.0,          # deg over a limit before it counts (mesh / rig measurement noise)
    balance=0.03, balance_bad=0.08,
    part=15.0,            # deg: a channel with this range takes part in the exercise
    sym=0.10,             # left/right range and timing
    rep_lo=2.0, rep_hi=5.0,
    hold_default=2.0,
    vis=0.15, vis_frames=0.8,
    plane=0.6, amp=0.10,
    cam_low=14.0,         # deg: camera elevation over a body on the floor
)
LIMITS = {  # channel: (min, max) in degrees
    'joelho flexão': (-5, 160),  # (sitting back on the heels takes 155-160) 'joelho lateral': (-10, 10),
    'cotovelo flexão': (-5, 150), 'cotovelo lateral': (-25, 25),
    'quadril flexão': (-20, 125), 'quadril abdução': (-30, 45), 'quadril rotação': (-60, 60),  # (external rotation reaches ~60 with the hip flexed)
    'ombro extensão': (-180, 60),
    'coluna flexão': (-30, 80), 'coluna inclinação': (-35, 35), 'coluna rotação': (-45, 45),
    'pescoço flexão': (-60, 50), 'pescoço rotação': (-70, 70), 'pescoço inclinação': (-45, 45),
    'tornozelo dorsiflexão': (-50, 20),
    'punho flexão': (-90, 85),  # (total bend, >= 0)
}
BALLISTIC = ('jump', 'hop', 'skip', 'jack', 'burpee', 'bound', 'tuck', 'jog', 'run', 'sprint', 'high-knee',
             'butt-kick', 'skater', 'pop-squat', 'star', 'lunge-switch', 'scissor', 'throw', 'kick', 'punch')
STEPPING = ('walk', 'march', 'step', 'lunge', 'gait', 'stair', 'tandem', 'heel-to-toe', 'grapevine', 'carioca',
            'shuffle', 'turn', 'tug', 'cross')
POINTS = {  # channel joint -> the tracked points around it (proximal joint, the joint, distal end)
    'quadril': ('hips', 'knee', 'foot'), 'joelho': ('knee', 'foot', 'hips'), 'tornozelo': ('foot', 'toe', 'knee'),
    'ombro': ('arm', 'elbow', 'hand'), 'cotovelo': ('elbow', 'hand', 'arm'), 'punho': ('hand', 'fing', 'elbow'),
    'coluna': ('spine', 'neck', 'headtop'), 'pescoço': ('neck', 'headtop'),
}
SEGMENT = {  # channel joint -> (visible parts, the point whose path shows the motion)
    'quadril': (['leg', 'knee'], 'foot'), 'joelho': (['knee'], 'foot'), 'tornozelo': (['foot'], 'toe'),
    'ombro': (['arm', 'elbow'], 'hand'), 'cotovelo': (['elbow'], 'hand'), 'punho': (['hand'], 'fing'),
    'coluna': (['spine'], 'neck'), 'pescoço': (['neck'], 'headtop'),
}


def qmat(q):
    w, x, y, z = q[..., 0], q[..., 1], q[..., 2], q[..., 3]
    return np.stack([np.stack([1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)], -1),
                     np.stack([2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)], -1),
                     np.stack([2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)], -1)], -2)


def qmul(a, b):
    w1, x1, y1, z1 = np.moveaxis(a, -1, 0)
    w2, x2, y2, z2 = np.moveaxis(b, -1, 0)
    return np.stack([w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2, w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
                     w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2, w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2], -1)


def qconj(q):
    return q * np.array([1, -1, -1, -1])


def qlog(q):
    """Rotation vector (degrees) of unit quaternions, shortest way."""
    q = np.where(q[..., :1] < 0, -q, q)
    s = np.linalg.norm(q[..., 1:], axis=-1, keepdims=True)
    ang = 2 * np.arctan2(s, q[..., :1])
    return np.degrees(np.where(s > 1e-9, q[..., 1:] / np.maximum(s, 1e-12) * ang, 2 * q[..., 1:]))


def twist_z(q):
    a = np.degrees(2 * np.arctan2(q[..., 3], q[..., 0]))
    return (a + 180) % 360 - 180


def deg_atan2(y, x):
    return np.degrees(np.unwrap(np.arctan2(y, x)))


def channels(q, bones):
    """Anatomical angles (deg) per frame. Sides: E = left (+x), D = right."""
    B = {b: i for i, b in enumerate(bones)}
    R = qmat(q)
    ch = {}

    def ap(b, v):
        return R[:, B[b]] @ np.array(v, float)
    for s, sg, pt in (('L', 1, 'E'), ('R', -1, 'D')):
        t = ap('leg' + s, (0, 0, -1))
        ch[f'quadril flexão {pt}'] = deg_atan2(-t[:, 1], -t[:, 2])
        ch[f'quadril abdução {pt}'] = np.degrees(np.arcsin(np.clip(t[:, 0] * sg, -1, 1)))
        # rotation about the thigh's own axis after flexion and abduction (intrinsic X, Y, Z: what the keys' y
        # says); the swing-twist split added Codman's twist on a flexed, abducted hip (butterfly keyed 78 read 127)
        Rl = R[:, B['leg' + s]]
        ch[f'quadril rotação {pt}'] = np.degrees(np.arctan2(-Rl[:, 0, 1], Rl[:, 0, 0])) * sg
        k = ap('knee' + s, (0, 0, -1))
        ch[f'joelho flexão {pt}'] = deg_atan2(k[:, 1], -k[:, 2])
        ch[f'joelho lateral {pt}'] = np.degrees(np.arcsin(np.clip(k[:, 0] * sg, -1, 1)))
        f = ap('foot' + s, (0, -1, 0))
        ch[f'tornozelo dorsiflexão {pt}'] = deg_atan2(f[:, 2], np.hypot(f[:, 0], f[:, 1]))
        a = ap('arm' + s, (0, 0, -1))  # elevation from hanging, and its forward / behind / sideways shares
        ch[f'ombro elevação {pt}'] = np.degrees(np.arccos(np.clip(-a[:, 2], -1, 1)))
        ch[f'ombro flexão {pt}'] = np.degrees(np.arcsin(np.clip(-a[:, 1], -1, 1)))
        ch[f'ombro extensão {pt}'] = -ch[f'ombro flexão {pt}']
        ch[f'ombro abdução {pt}'] = np.degrees(np.arcsin(np.clip(a[:, 0] * sg, -1, 1)))
        e = ap('elbow' + s, (0, 0, -1))
        ch[f'cotovelo flexão {pt}'] = deg_atan2(-e[:, 1], -e[:, 2])
        ch[f'cotovelo lateral {pt}'] = np.degrees(np.arcsin(np.clip(e[:, 0] * sg, -1, 1)))
        h = ap('hand' + s, (0, 0, -1))  # the wrist's total bend off the forearm axis, whatever its direction (the
        # flexion / deviation split depends on the rig's hand axes and wrapped to +-180 deg for a hand bent over 90)
        ch[f'punho flexão {pt}'] = np.degrees(np.arccos(np.clip(-h[:, 2], -1, 1)))
    for b, nm in (('spine', 'coluna'), ('neck', 'pescoço')):
        u = ap(b, (0, 0, 1))
        ch[f'{nm} flexão'] = deg_atan2(-u[:, 1], u[:, 2])
        ch[f'{nm} inclinação'] = deg_atan2(u[:, 0], u[:, 2])
        ch[f'{nm} rotação'] = twist_z(q[:, B[b]])
    return ch


def runs(mask):
    out, s = [], None
    for i, m in enumerate(list(mask) + [False]):
        if m and s is None:
            s = i
        elif not m and s is not None:
            out.append((s, i))
            s = None
    return out


def base(chname):
    """'joelho flexão E' -> ('joelho flexão', 'E'); 'coluna flexão' -> ('coluna flexão', '')."""
    p = chname.rsplit(' ', 1)
    return (p[0], p[1]) if p[-1] in ('E', 'D') else (chname, '')


def required_hold(job):
    """Seconds a hold should last, from the PocketPhysio texts of the job (default 2 s), and whether the job is
    a hold / stretch at all."""
    cat = {e['id']: e for e in json.load(open(REPO / 'research/pocketphysio/exercicios.json', encoding='utf-8'))}
    secs, holdy, who = [], False, []
    for pid in job.get('pocketphysio', []):
        e = cat.get(pid, {})
        txt = ' '.join(str(e.get(k, '')) for k in ('descricao_pt', 'observacoes', 'nome_pt')).lower()
        title = str(e.get('nome_pt', '')).lower()
        if re.search(r'isom[eé]tric|alongament|prancha|sustenta', title) or re.search(
                r'isom[eé]tric|(?:mantenha|segure|sustente|permaneça)(?:-a|-o)?\s+(?:\w+\s+){0,2}(?:posição|contração|alongamento)'
                r'\s+(?:por|durante|estátic|pelo|alguns)|(?:mantenha|segure|sustente|permaneça)(?:-a|-o)?\s+(?:por|durante)', txt):
            holdy = True
            who.append(pid)
        for m in re.finditer(r'(\d+)\s*(?:a\s*\d+\s*)?(?:segundos|seg\b)', txt):
            secs.append(int(m.group(1)))
            holdy = True
            who.append(pid)
    return min(min(secs) if secs else TH['hold_default'], TH['hold_cap']), holdy, sorted(set(who))


def analyze(npz_path, job, name, ref_secs=None):
    D = np.load(npz_path, allow_pickle=False)
    bones = list(D['bones'])
    B = {b: i for i, b in enumerate(bones)}
    q = D['q'].copy()
    for i in range(1, len(q)):  # same hemisphere frame to frame
        flip = (q[i] * q[i - 1]).sum(-1) < 0
        q[i, flip] *= -1
    nF = len(q)
    fps = FPS
    sc = FPS / fps
    lname = name.lower()
    props = str(D['props'])
    ballistic = any(w in lname for w in BALLISTIC) or job.get('balistico', False)
    stepping = any(w in lname for w in STEPPING) or 'walk' in props.split('+') or 'walkergo' in props
    walking = any(w in lname for w in ('walk', 'march', 'gait')) or 'walk' in props.split('+')
    seated = bool(D['seated'])
    issues = []

    def issue(layer, code, sev, msg, **kw):
        issues.append(dict(layer=layer, code=code, sev=sev, msg=msg, **kw))
    m = {}
    ch = channels(q, bones)
    rom = {k: float(np.percentile(v, 99) - np.percentile(v, 1)) for k, v in ch.items()}
    pelvis = D['heads'][:, B['hips']]
    gap = D['gap']  # pé E, pé D, mão E, mão D
    foot_air = (gap[:, :2] > 0.01)
    # --- fluidez
    rel = qmul(qconj(q[:-1]), q[1:])
    w = qlog(rel)                                   # [nF-1, bones, 3] deg/frame
    spd = np.linalg.norm(w, axis=-1)
    pop_th = TH['pop_step'] if stepping else TH['pop']
    pops = np.argwhere(spd > pop_th * sc)
    m['pops'] = int(len({int(f) for f, _ in pops}))
    if len(pops):
        worst = max(((float(spd[f, b]), int(f), bones[b]) for f, b in pops))
        m['pop_max'] = [round(worst[0], 1), worst[2], int(D['frames'][worst[1]])]
        if not ballistic:
            issue(2, 'pop', 2 if worst[0] > 2 * pop_th else 1,
                  f"pop: {worst[2]} gira {worst[0]:.0f}° em 1 quadro (quadro {int(D['frames'][worst[1]])}, {m['pops']} quadros > {pop_th:.0f}°)")
    acc = np.linalg.norm(np.diff(w, axis=0), axis=-1)  # [nF-2, bones]
    jr, jworst = 0.0, None
    for b in range(len(bones)):
        mv = spd[:-1, b] > 0.2
        if mv.sum() < 10:
            continue
        med = float(np.median(acc[mv, b]))
        if med <= 0:
            continue
        j = int(np.argmax(acc[:, b]))
        r = float(acc[j, b] / med)
        if acc[j, b] > TH['jerk_floor'] * sc * sc and r > jr:
            jr, jworst = r, (bones[b], int(D['frames'][j + 1]), float(acc[j, b]))
    m['max_jerk'] = round(jr, 1)
    if jworst:
        m['jerk_at'] = [jworst[0], jworst[1], round(jworst[2], 2)]
    if jr > TH['jerk'] and not ballistic:
        issue(2, 'tranco', 2 if jworst[2] >= TH['jerk_bad'] * sc * sc else 1,
              f'tranco: {jworst[0]} acelera {jr:.1f}x a mediana (quadro {jworst[1]}, {jworst[2]:.1f}°/quadro²)')
    dp = np.linalg.norm(np.diff(pelvis, axis=0), axis=1)
    tel = [i for i in np.flatnonzero(dp > TH['teleport'] / sc)
           if not (foot_air[max(i - 2, 0):i + 3].any() or ballistic)]
    m['pelvis_max_cm'] = round(float(dp.max()) * 100, 1)
    if tel:
        issue(2, 'teleporte', 2, f'pelve desloca {dp[tel].max() * 100:.1f} cm em 1 quadro com os pés no chão (quadro {int(D["frames"][tel[0]])})')
    # main channel: the widest range (sided channels only once per joint)
    cand = {k: v for k, v in rom.items() if not k.startswith(('ombro extensão', 'ombro flexão', 'ombro abdução'))}
    main = max(cand, key=cand.get)
    m['main'] = main
    m['main_rom'] = round(rom[main], 1)
    th = ch[main]
    v = np.diff(th)
    peak_all = np.abs(v).max() if len(v) else 0
    bad_ease = []
    for a, b in runs(np.abs(v) > max(0.03 * peak_all, 0.05)):
        seg = v[a:b]
        for a2, b2 in runs(seg > 0) + runs(seg < 0):  # one direction at a time
            s2 = np.abs(seg[a2:b2])
            if abs(th[a + b2] - th[a + a2]) < 0.25 * rom[main] or len(s2) < 3:
                continue
            pk = s2.max()
            end_r, start_r = s2[-1] / pk, s2[0] / pk
            k80 = np.flatnonzero(s2 >= 0.8 * pk)[-1]
            dec = len(s2) - 1 - k80
            if end_r > TH['ease_end'] or start_r > TH['ease_end'] or dec < TH['ease_frames'] / sc:
                bad_ease.append((int(D['frames'][a + a2]), round(float(start_r), 2), round(float(end_r), 2), int(dec)))
    m['ease_bad'] = bad_ease[:4]
    if bad_ease:
        issue(2, 'easing', 1, f'{main}: {len(bad_ease)} trecho(s) sem desaceleração nas pontas (quadro {bad_ease[0][0]})')
    # loop
    ang_gap = np.degrees(2 * np.arccos(np.clip(np.abs((q[0] * q[-1]).sum(-1)), 0, 1)))
    pgap = pelvis[-1] - pelvis[0]
    travel = 'walk' in props.split('+') or 'walkergo' in props
    pg = abs(pgap[2]) if travel else np.linalg.norm(pgap)
    m['loop_gap'] = [round(float(ang_gap.max()), 1), round(float(pg) * 100, 1)]
    closes = ang_gap.max() < TH['loop_rot'] and pg < TH['loop_pos']
    m['loop_closes'] = bool(closes)
    if not closes:
        b = bones[int(np.argmax(ang_gap))]
        issue(2, 'loop', 2 if ang_gap.max() > 10 or pg > 0.05 else 1,
              f'emenda do loop: {b} {ang_gap.max():.1f}°, pelve {pg * 100:.1f} cm')
    # --- biomecânica: limits
    viol = []
    for k, vals in ch.items():
        bk, side = base(k)
        if bk not in LIMITS:
            continue
        lo, hi = LIMITS[bk]
        if bk == 'punho flexão':  # a palm bearing weight may extend to wrist_ext_load
            load = gap[:, 2 if side == 'E' else 3] < 0.01
            if load.any() and vals[load].max() <= TH['wrist_ext_load'] + TH['rom_tol']:
                if (~load).sum() < 10:
                    continue
                vals = vals[~load]
        mx, mn = float(np.percentile(vals, 99.5)), float(np.percentile(vals, 0.5))
        if mx > hi + TH['rom_tol']:
            viol.append((k, round(mx), hi, round(mx - hi)))
        if mn < lo - TH['rom_tol']:
            viol.append((k, round(mn), lo, round(lo - mn)))
    m['rom_violations'] = [f'{k} {v_}° (limite {lim}°)' for k, v_, lim, _ in viol]
    for k, v_, lim, ex in viol:  # (the rig has no toe joint: standing on the toes reads as ankle dorsiflexion)
        issue(2, 'amplitude', 2 if ex > 10 and not k.startswith('tornozelo') else 1, f'{k} {v_}° (limite {lim}°)')
    # balance: centre of mass over the feet when standing on them
    R0 = qmat(q[:, B['hips']])
    Rsp = R0 @ qmat(q[:, B['spine']])
    upright = Rsp[:, 2, 2] > 0.7
    standing = upright & ((pelvis[:, 2] - float(D['floor_z'])) > 0.75) & (not seated)  # (tall kneeling: pelvis ~0.6)
    hands_free = (gap[:, 2] > 0.02) & (gap[:, 3] > 0.02)
    if set(str(D['props']).split('+')) & {'support', 'side', 'wall', 'walker', 'walkergo', 'caneL', 'caneR', 'bar'}:
        hands_free[:] = False  # holding a chair back / wall / walker: the hands may ride a few cm above it (no contact
        # solver for the chair back) but the body is supported
    ev = standing & hands_free & np.isfinite(D['bos'])
    if stepping or ballistic:
        ev &= ~foot_air.any(1)
    if ballistic:  # take-off and landing: on the toes for a moment around every flight
        air_all = foot_air.all(1)
        near = np.convolve(air_all.astype(float), np.ones(9), 'same') > 0
        ev &= ~near
    bos = np.where(ev, D['bos'], np.nan)
    if np.isfinite(bos).any():
        bmax = float(np.nanmax(bos))
        m['balance'] = round(bmax * 100, 1)
        if bmax > TH['balance']:
            f = int(D['frames'][int(np.nanargmax(bos))])
            issue(2, 'equilibrio', 2 if bmax > TH['balance_bad'] else 1,
                  f'centro de massa {bmax * 100:.0f} cm fora da base de apoio (quadro {f})')
    else:
        m['balance'] = None
    # compensations
    if walking:
        c = []
        for s, o in (('E', 'D'), ('D', 'E')):
            a_, l_ = ch[f'ombro flexão {s}'], ch[f'quadril flexão {o}']
            if a_.std() > 1 and l_.std() > 1:
                c.append(float(np.corrcoef(a_, l_)[0, 1]))
        m['arm_swing_corr'] = round(min(c), 2) if c else None
        if not c or min(c) < 0.3:
            issue(2, 'compensacao', 1, f'braços não balançam ao contrário das pernas (corr {min(c) if c else 0:.2f})')
        heel = D['heel']
        hs, n_on = 0, 0
        for j in range(2):
            on = np.isfinite(heel[:, j])
            for a, b in runs(on):
                if a == 0:
                    continue
                n_on += 1
                hs += heel[a, j] < 0
        m['heel_strike'] = f'{hs}/{n_on}'
        if n_on and hs / n_on < 0.5:
            issue(2, 'compensacao', 1, f'o calcanhar toca o chão primeiro em só {hs} de {n_on} passos')
    if ballistic:
        air = foot_air.all(1) & (gap[:, 2] > 0.02) & (gap[:, 3] > 0.02)
        bad = 0
        lands = 0
        for a, b in runs(air):
            if b - a < 2 or b >= nF - 1:
                continue
            lands += 1
            kf = np.maximum(ch['joelho flexão E'], ch['joelho flexão D'])
            if kf[b:b + 9].max() - kf[b] < 8:
                bad += 1
        m['landings'] = f'{lands - bad}/{lands}'
        if lands and bad:
            issue(2, 'compensacao', 1, f'{bad} de {lands} aterrissagens sem o joelho absorver o impacto')
    # parts at rest
    part = {k for k, r in rom.items() if r >= TH['part']}
    for s in ('E', 'D'):
        arm_moves = any(k.endswith(' ' + s) and k.startswith(('ombro', 'cotovelo')) for k in part)
        if not arm_moves:
            tpose = (ch[f'ombro abdução {s}'] > 65) & (ch[f'cotovelo flexão {s}'] < 20)
            if tpose.mean() > 0.5:
                issue(2, 'repouso', 1, f'braço {s} duro em T sem participar do exercício')
    mainv = ch[main]
    for k, vals in ch.items():
        if k in part or base(k)[0] in ('ombro extensão', 'ombro flexão', 'ombro abdução'):
            continue
        r = rom[k]
        dv = np.diff(vals)
        flips = np.sum((dv[:-1] * dv[1:] < 0) & (np.abs(dv[:-1]) > 0.1))
        if r < 5 and flips / (nF / fps) > 2:
            issue(2, 'repouso', 1, f'{k}: tremor ({flips} inversões, {r:.1f}°)')
        elif 6 <= r < TH['part'] and mainv.std() > 0 and vals.std() > 0 and abs(np.corrcoef(vals, mainv)[0, 1]) < 0.4:
            issue(2, 'repouso', 1, f'{k}: deriva lenta de {r:.0f}° sem relação com o movimento')
    # symmetry
    sym = []
    for k in part:
        bk, s = base(k)
        if s != 'E' or f'{bk} D' not in rom:
            continue
        rl, rr = rom[k], rom[f'{bk} D']
        hi_, lo_ = max(rl, rr), min(rl, rr)
        if lo_ < TH['part'] or lo_ / hi_ < 0.5:
            continue  # one side only, or two different roles
        d = 1 - lo_ / hi_
        tl = np.mean(np.abs(ch[k] - np.median(ch[k])) > 0.5 * rl)
        tr = np.mean(np.abs(ch[f'{bk} D'] - np.median(ch[f'{bk} D'])) > 0.5 * rr)
        dt = abs(tl - tr) / max(tl, tr, 1e-6)
        sym.append((bk, round(d, 2), round(dt, 2)))
        if d > TH['sym'] or dt > TH['sym'] * 2.5:
            issue(2, 'simetria', 1, f'{bk}: lados diferentes (amplitude {d * 100:.0f}%, tempo {dt * 100:.0f}%)')
    m['symmetry'] = sym
    # repetitions: excursions away from the start pose and back
    dist = np.degrees(2 * np.arccos(np.clip(np.abs((q * q[:1]).sum(-1)), 0, 1))).mean(1)
    if not travel:
        dist = dist + 100 * np.linalg.norm(pelvis - pelvis[:1], axis=1)
    else:
        dist = dist + 100 * np.abs(pelvis[:, 2] - pelvis[0, 2])
    dmax = dist.max()
    reps, out_ = 0, False
    for x in dist:
        if not out_ and x > 0.5 * dmax:
            out_ = True
        elif out_ and x < 0.2 * dmax:
            out_, reps = False, reps + 1
    if travel:  # a walk: one repetition per step (the main hip peaks)
        reps = max(reps, int(np.sum((th[1:-1] > th[:-2]) & (th[1:-1] >= th[2:]) & (th[1:-1] > np.median(th) + 0.3 * rom[main]))))
    reps = max(reps, 1)
    m['reps_cycle'] = reps
    secs = nF / fps
    m['seconds'] = round(secs, 2)
    m['sec_per_rep'] = round(secs / reps, 2)
    m['loops'] = 1 if not closes else int(np.ceil(2 / reps))
    # holds: the pose still for >= 0.3 s away from the start
    still = (spd.max(1) < 0.25 * sc) & (dp < 0.002 / sc)
    holds = [(b - a) / fps for a, b in runs(still) if b - a >= 0.3 * fps and dist[(a + b) // 2] > 0.3 * dmax]
    need, holdy, who = required_hold(job)
    m['hold_s'] = round(max(holds), 2) if holds else 0.0
    m['hold_needed'] = need if holdy else None
    m['hold_ids'] = who
    if holdy and m['hold_s'] + 0.1 < need:
        issue(2, 'ritmo', 1, f'sustenta {m["hold_s"]:.1f} s; {len(who)} id(s) pedem {need} s ({", ".join(w[-6:] for w in who)})')
    if not ballistic and not walking:
        allow = TH['rep_hi'] + (m['hold_s'] if holdy else 0)
        if m['sec_per_rep'] < TH['rep_lo']:
            issue(2, 'ritmo', 1, f'{m["sec_per_rep"]:.1f} s por repetição (rápido; terapêutico 2-5 s)')
        elif m['sec_per_rep'] > allow:
            issue(2, 'ritmo', 1, f'{m["sec_per_rep"]:.1f} s por repetição (lento; terapêutico 2-5 s)')
    # --- legibilidade
    jnt = main.split(' ')[0]
    side = base(main)[1]
    sfx = {'E': 'L', 'D': 'R', '': ''}[side]
    groups = list(D['groups'])
    leg = []
    vis = D['vis']
    if len(vis):
        vf = D['vis_frames']
        moving_parts = []
        for k in part:
            j_, s_ = k.split(' ')[0], {'E': 'L', 'D': 'R', '': ''}[base(k)[1]]
            if j_ in SEGMENT:
                moving_parts.append((k, [groups.index(g + s_) for g in SEGMENT[j_][0] if g + s_ in groups]))
        seen, n = 0, 0
        for r_, f in enumerate(vf):
            best = None
            for k, gi in moving_parts:
                if f < nF - 1 and abs(np.diff(ch[k])[min(f, nF - 2)]) > 0.5 * sc and gi:
                    best = max(best or 0, max(vis[r_, gi]))
            if best is not None:
                n += 1
                seen += best >= TH['vis']
        m['visible'] = round(seen / n, 2) if n else None
        if n and seen / n < TH['vis_frames']:
            leg.append(f'segmento que se move visível em {seen / n * 100:.0f}% dos quadros')
        # the limb that bears the body (a hand or forearm on the floor or a prop) must be seen too
        sup_vis = []
        for j, (eff, gs) in enumerate((('mão E', ['handL', 'elbowL']), ('mão D', ['handR', 'elbowR']))):
            on = gap[vf, 2 + j] < 0.02
            if on.mean() > 0.3 and not seated:  # (seated, a hand on the chair only rests there or grips its edge)
                gi = [groups.index(g) for g in gs]
                sv = float(np.mean(vis[on][:, gi].max(1) >= TH['vis']))
                sup_vis.append((eff, round(sv, 2)))
                if sv < TH['vis_frames']:
                    leg.append(f'{eff} de apoio visível em {sv * 100:.0f}% dos quadros')
        m['support_visible'] = sup_vis
    track = list(D['track'])
    W, H = (int(x) for x in D['res'])
    best = None  # the point that moves most on screen among the joints that take part (a planted hand does not)
    for k in sorted(part | {main}):
        j_ = k.split(' ')[0]
        s_ = {'E': 'L', 'D': 'R', '': ''}[base(k)[1]]
        for pn in POINTS.get(j_, ()):
            key = pn + s_ if pn + s_ in track else pn
            if key not in track:
                continue
            pj = D['proj'][:, track.index(key)]
            sub = np.column_stack([pj[:, 0] * W / H, pj[:, 1]])[::2]
            amp = float(np.max(np.linalg.norm(sub[:, None] - sub[None], axis=-1)))
            if best is None or amp > best[0]:
                best = (amp, key)
    if best:
        amp, key = best
        P = D['pts'][:, track.index(key)]
        m['amp_frame'], m['amp_point'] = round(amp, 3), key
        cam = D['cam'].mean(0)
        vdir = P.mean(0) - cam
        vdir /= np.linalg.norm(vdir)
        P0 = P - P.mean(0)
        e3 = np.linalg.svd(P0, compute_uv=False)[0]
        P2 = P0 - np.outer(P0 @ vdir, vdir)
        e2 = np.linalg.svd(P2, compute_uv=False)[0]
        ratio = float(e2 / e3) if e3 > 1e-6 else 1.0
        m['plane'] = round(ratio, 2)
        if e3 > 0.03 and ratio < TH['plane']:
            leg.append(f'plano do movimento de lado para a câmera ({ratio:.2f})')
        if amp < TH['amp']:
            leg.append(f'amplitude ocupa {amp * 100:.0f}% da altura do quadro')
    # a low body (lying, plank, quadruped) seen from a grazing camera: the floor disappears and the body floats
    low = float(np.median(pelvis[:, 2]) - float(D['floor_z'])) < 0.6
    ctr = D['pts'].mean(1)
    rel = D['cam'] - ctr
    elev = float(np.degrees(np.median(np.arcsin(rel[:, 2] / np.linalg.norm(rel, axis=1)))))
    m['cam_elev'] = round(elev, 1)
    if low and elev < TH['cam_low']:
        leg.append(f'câmera rasante ({elev:.0f}°) com o corpo no chão: o chão some e o corpo parece flutuar')
    if m['reps_cycle'] * m['loops'] < 2:
        leg.append('menos de 2 repetições')
    m['legivel'] = 'sim' if not leg else 'não: ' + '; '.join(leg)
    for x in leg:
        issue(2, 'legibilidade', 1, x)
    m['ballistic'], m['stepping'] = bool(ballistic), bool(stepping)
    m['rom'] = {k: round(r, 1) for k, r in sorted(rom.items(), key=lambda kv: -kv[1]) if r >= 5}
    m['motion_issues'] = issues
    m['motion_status'] = 'quebrado' if any(i['sev'] >= 2 for i in issues) else 'suspeito' if issues else 'ok'
    return m


def main(qa, ids):
    jobs = json.load(open(HERE / 'jobs.json'))
    qa = Path(qa)
    ids = ids or sorted(p.name[:-len('.motion.npz')] for p in qa.glob('*.motion.npz'))
    for i in ids:
        p = qa / f'{i}.motion.npz'
        if not p.exists():
            print(i, 'sem motion.npz')
            continue
        jid = i.split('@')[0]
        m = analyze(p, jobs.get(jid, {}), jid)
        json.dump(m, open(qa / f'{i}.motion.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f"{i:40s} {m['motion_status']:9s} pops={m['pops']} jerk={m['max_jerk']} loop={m['loop_gap']} "
              f"bal={m['balance']} main={m['main']}({m['main_rom']}) reps={m['reps_cycle']}x{m['loops']} "
              f"{m['sec_per_rep']}s/rep vis={m.get('visible')} plane={m.get('plane')} amp={m.get('amp_frame')}")
        for x in m['motion_issues']:
            print('    ', 'Q' if x['sev'] >= 2 else 'S', x['msg'])


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2:])
