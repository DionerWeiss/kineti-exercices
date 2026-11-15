"""Layer 3 of the avatar review: our render next to the PocketPhysio original.

    python3 tool/mannequin/pp_compare.py fetch <job ids...>       # originals -> E:/mannequin/pocketphysio_ref/<id>.mp4 (cached)
    python3 tool/mannequin/pp_compare.py compare <job ids...>     # -> <compare>/<job>.mp4 and <job>.png (+ _2.png ...)

fetch keeps <ref>/status.json: {id: "ok" | "403" | "erro" | "placeholder"}; a placeholder is a file shared by
several different exercises (the "Demo Video" clip). Those ids are compared with the text only (ref=texto).
compare finds the movement cycle of each side (the PocketPhysio clip: autocorrelation of its frames; ours: the
excursions of the rig away from the start pose, from <qa>/<job>.motion.npz), plays the original at the speed that
matches its cycle to ours, starting on its start pose when our still start ends, and writes:
- <job>.mp4: original (the first id with a video) on the left, ours on the right, 960x540 each;
- <job>.png: per id a row with its start, peak and return frames, and our row at the bottom (8 rows per sheet).
Env: MANNEQUIN_OUT (the work dir with qa/), PP_REF, PP_COMPARE, MANNEQUIN_VIDEOS (our mp4s), LEAD (still start frames, 15).
"""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
REF = Path(os.environ.get('PP_REF', '/mnt/e/mannequin/pocketphysio_ref'))
OUT = Path(os.environ.get('MANNEQUIN_OUT', '/mnt/e/mannequin/avatar_man/final'))
CMP = Path(os.environ.get('PP_COMPARE', '/mnt/e/mannequin/avatar_man/out/compare'))
VIDS = Path(os.environ.get('MANNEQUIN_VIDEOS', '/mnt/e/mannequin/avatar_man/out/videos_final'))
LEAD = int(os.environ.get('LEAD', 15))
FPS = 30
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'


def catalog():
    return {e['id']: e for e in json.load(open(REPO / 'research/pocketphysio/exercicios.json', encoding='utf-8'))}


def jobs():
    return json.load(open(HERE / 'jobs.json'))


def status():
    p = REF / 'status.json'
    return json.load(open(p)) if p.exists() else {}


def fetch(job_ids):
    REF.mkdir(parents=True, exist_ok=True)
    cat, js, st = catalog(), jobs(), status()
    for jid in job_ids:
        for pid in js[jid].get('pocketphysio', []):
            dst = REF / f'{pid}.mp4'
            if dst.exists() and st.get(pid) in ('ok', 'placeholder'):
                continue
            if st.get(pid) == '403':
                continue
            url = cat[pid].get('video')
            if not url:
                st[pid] = 'erro'
                continue
            r = subprocess.run(['curl', '-sS', '-L', '-o', str(dst), '-w', '%{http_code}', url], capture_output=True, text=True)
            code = r.stdout.strip()
            if code == '200' and dst.exists() and dst.stat().st_size > 10_000:
                st[pid] = 'ok'
            else:
                st[pid] = '403' if code in ('403', '401') else 'erro'
                dst.unlink(missing_ok=True)
            print(pid, st[pid], cat[pid]['nome_pt'])
    # placeholders: the same file for different exercises
    by_hash = {}
    for pid, s in st.items():
        if s in ('ok', 'placeholder') and (REF / f'{pid}.mp4').exists():
            h = hashlib.md5((REF / f'{pid}.mp4').read_bytes()).hexdigest()
            by_hash.setdefault(h, []).append(pid)
    for h, ids in by_hash.items():
        names = {cat[i]['titulo_original'].strip().lower() for i in ids}
        for i in ids:
            st[i] = 'placeholder' if len(names) > 1 else 'ok'
    json.dump(st, open(REF / 'status.json', 'w'), indent=1)


def frames(p, w=96, h=54):
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(p), '-vf', f'fps={FPS},scale={w}:{h},format=gray', '-f', 'rawvideo', '-'],
                       capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.uint8).reshape(-1, h * w).astype(np.float32)


def pp_cycle(p):
    """(start, peak, return, period) in frames at 30 fps of the PocketPhysio clip."""
    X = frames(p)
    n = len(X)
    mot = np.r_[0, np.abs(np.diff(X, axis=0)).mean(1)]
    act = mot > 0.25 * np.percentile(mot, 90)
    t0 = int(np.argmax(act)) if act.any() else 0
    t0 = max(t0 - 3, 0)
    Y = X[t0:] - X[t0:].mean(0)
    U, S, Vt = np.linalg.svd(Y[::2], full_matrices=False)
    s = Y @ Vt[0]
    s = s - s.mean()
    ac = np.correlate(s, s, 'full')[len(s) - 1:]
    ac /= ac[0] if ac[0] else 1
    lo, hi = int(0.8 * FPS), min(int(14 * FPS), len(s) - 1)
    period = None
    # first: the time back to the start pose after the first excursion (out past half the largest distance from the
    # start frame, back under a quarter) - clips with one or two repetitions or a hold have no autocorrelation peak
    d0 = np.linalg.norm(X[t0:] - X[t0], axis=1)
    if len(d0) and d0.max() > 0:
        out_ = np.flatnonzero(d0 > 0.5 * d0.max())
        if len(out_):
            back_ = np.flatnonzero(d0[out_[0]:] < 0.25 * d0.max())
            if len(back_) and lo <= out_[0] + back_[0] <= hi:
                period = int(out_[0] + back_[0])
    for L in range(lo + 1, hi - 1):
        if period is not None:
            break
        if ac[L] > 0.3 and ac[L] >= ac[L - 1] and ac[L] >= ac[L + 1]:
            period = L
            break
    span = period or min(n - t0, 6 * FPS)
    dist = np.linalg.norm(X[t0:t0 + span] - X[t0], axis=1)
    peak = t0 + int(np.argmax(dist))
    end = min(t0 + int(1.3 * span), n)
    back = np.linalg.norm(X[peak:end] - X[t0], axis=1)
    ret = peak + int(np.argmin(back)) if len(back) else n - 1
    return t0, peak, ret, period


def our_cycle(jid):
    """(start, peak, return, rep frames, cycle frames) in action frames, from motion.npz (a hand close-up has none:
    thirds of its video)."""
    npz = OUT / 'qa' / f'{jid}.motion.npz'
    if not npz.exists():
        v = Path(os.environ.get('MANNEQUIN_VIDEOS', OUT / 'videos')) / f'{jid}.mp4'
        r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-count_packets', '-show_entries',
                            'stream=nb_read_packets', '-of', 'csv=p=0', str(v)], capture_output=True, text=True)
        F = max(int(r.stdout.strip() or 31) - 15, 4)
        return 0, F // 3, 2 * F // 3, F - 1, F - 1
    D = np.load(npz)
    q = D['q']
    dist = np.degrees(2 * np.arccos(np.clip(np.abs((q * q[:1]).sum(-1)), 0, 1))).mean(1)
    pel = D['heads'][:, 0]
    travel = 'walk' in str(D['props']).split('+')
    dist = dist + 100 * (np.abs(pel[:, 2] - pel[0, 2]) if travel else np.linalg.norm(pel - pel[0], axis=1))
    F = len(q)
    mx = dist.max()
    # first excursion: out past half the max, back under a fifth
    i = 0
    while i < F and dist[i] < 0.5 * mx:
        i += 1
    j = i
    while j < F and dist[j] >= 0.2 * mx:
        j += 1
    peak = int(np.argmax(dist[:j])) if j > 0 else 0
    ret = min(j, F - 1)
    mj = OUT / 'qa' / f'{jid}.motion.json'
    reps = json.load(open(mj))['reps_cycle'] if mj.exists() else 1
    return 0, peak, ret, (F - 1) / max(reps, 1), F - 1


def grab(p, t, w=640, h=360):
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(p), '-vf', f"fps={FPS},select='eq(n\\,{t})',scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:white",
                        '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True, check=True)
    a = np.frombuffer(r.stdout, np.uint8)
    return a.reshape(h, w, 3) if a.size == w * h * 3 else np.full((h, w, 3), 255, np.uint8)


def label_png(rows, labels, out):
    """rows: list of [img, img, img]; labels: text per row. Writes a PNG via ffmpeg (drawtext)."""
    h, w = rows[0][0].shape[:2]
    lab = 34
    canvas = np.full((len(rows) * (h + lab), 3 * w + 20, 3), 255, np.uint8)
    for r, imgs in enumerate(rows):
        y = r * (h + lab) + lab
        for c, im in enumerate(imgs):
            canvas[y:y + h, 10 + c * w:10 + (c + 1) * w] = im
    raw = out.with_suffix('.rgb')
    raw.write_bytes(canvas.tobytes())
    txt = ','.join(f"drawtext=fontfile={FONT}:text='{t}':x=12:y={r * (h + lab) + 8}:fontsize=20:fontcolor=0x1F2937"
                   for r, t in enumerate(labels))
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{canvas.shape[1]}x{canvas.shape[0]}',
                    '-i', str(raw), '-vf', txt, '-frames:v', '1', str(out)], check=True)
    raw.unlink()


def esc(s):
    return s.replace("'", '’').replace(':', ' -').replace(',', ' ').replace('%', ' pct')


def compare(job_ids):
    CMP.mkdir(parents=True, exist_ok=True)
    cat, js, st = catalog(), jobs(), status()
    for jid in job_ids:
        ours = VIDS / f'{jid}.mp4'
        if not ours.exists():
            print(jid, 'sem vídeo nosso')
            continue
        s0, pk, rt, rep, cyc = our_cycle(jid)
        rows, labels, first = [], [], None
        for pid in js[jid].get('pocketphysio', []):
            e = cat[pid]
            src = REF / f'{pid}.mp4'
            if st.get(pid) != 'ok' or not src.exists():
                labels.append(esc(f"{pid[-6:]} {e['nome_pt']} - ref=texto ({st.get(pid, 'sem vídeo')})"))
                rows.append([np.full((360, 640, 3), 245, np.uint8)] * 3)
                continue
            t0, p1, r1, per = pp_cycle(src)
            rows.append([grab(src, t) for t in (t0, p1, r1)])
            labels.append(esc(f"PocketPhysio {pid[-6:]} {e['nome_pt']} [{e.get('caracteristicas', {}).get('posicao_inicial', '?')}] "
                              f"início / pico / retorno"))
            if first is None:
                first = (pid, src, t0, per)
        ours_row = [grab(ours, LEAD + t) for t in (s0, pk, rt)]
        sheets = [rows[k:k + 8] for k in range(0, max(len(rows), 1), 8)] or [[]]
        labs = [labels[k:k + 8] for k in range(0, max(len(labels), 1), 8)] or [[]]
        for n, (rr, ll) in enumerate(zip(sheets, labs)):
            out = CMP / (f'{jid}.png' if n == 0 else f'{jid}_{n + 1}.png')
            label_png(rr + [ours_row], ll + [esc(f'Kineti {jid} início / pico / retorno')], out)
            print(out)
        if first is None:
            print(jid, 'sem vídeo de referência: só o PNG')
            continue
        pid, src, t0, per = first
        # our cycle to match: one repetition, or the whole cycle when the original's period is closer to it
        target = rep
        if per and abs(np.log(cyc / per)) < abs(np.log(rep / per)):
            target = cyc
        fac = float(np.clip(target / per, 0.25, 4)) if per else 1.0
        dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(ours)],
                                   capture_output=True, text=True).stdout)
        lt = esc(f"PocketPhysio {cat[pid]['nome_pt']} (x{1 / fac:.2f})")
        fc = (f"[0:v]fps={FPS},trim=start_frame={t0},setpts=(PTS-STARTPTS)*{fac:.4f},fps={FPS},"
              f"tpad=start_duration={LEAD / FPS}:start_mode=clone,scale=960:540:force_original_aspect_ratio=decrease,"
              f"pad=960:540:(ow-iw)/2:(oh-ih)/2:white,drawtext=fontfile={FONT}:text='{lt}':x=10:y=10:fontsize=22:fontcolor=0x1F2937[a];"
              f"[1:v]scale=960:540,drawtext=fontfile={FONT}:text='Kineti':x=10:y=10:fontsize=22:fontcolor=0x1F2937[b];"
              f"[a][b]hstack=inputs=2,trim=duration={dur:.3f}[v]")
        out = CMP / f'{jid}.mp4'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-stream_loop', '-1', '-i', str(src), '-i', str(ours), '-filter_complex', fc,
                        '-map', '[v]', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '24', '-r', str(FPS), str(out)], check=True)
        print(out, f'speed x{1 / fac:.2f} (PP period {per} f, ours {target:.0f} f)')


if __name__ == '__main__':
    cmd, ids = sys.argv[1], sys.argv[2:]
    {'fetch': fetch, 'compare': compare}[cmd](ids)
