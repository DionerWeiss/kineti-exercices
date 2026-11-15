"""Layer 2, the encoded video: tool/mannequin/video_qa.py <mp4> <motion.npz> <lead frames> <loops> [<reference mp4>]

The video is <lead> copies of the first frame (the still start), then the action's frames 1..F-1 <loops> times and
frame F (mannequin.py render). Checks, with ffprobe and frame differences (grey, 240 px wide):
- frame count = duration x fps = lead + loops x (F - 1) + 1; 1920x1080 at 30 fps;
- frozen / duplicated frames: two equal frames where the rig moves (motion.npz);
- flicker / z-fighting: the image changing where the rig and camera stand still;
- the still start lasts >= 0.5 s; a video shorter than the reference (videos_v9 or the old video) is only noted,
  since the therapeutic rhythm (motion_review) takes priority.
Prints one JSON line.
"""
import json
import subprocess
import sys

import numpy as np

FPS, W, H = 30, 1920, 1080


def probe(p):
    r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-count_packets', '-show_entries',
                        'stream=width,height,r_frame_rate,nb_read_packets:format=duration', '-of', 'json', str(p)],
                       capture_output=True, text=True, check=True)
    j = json.loads(r.stdout)
    s = j['streams'][0]
    a, b = s['r_frame_rate'].split('/')
    return dict(w=s['width'], h=s['height'], fps=float(a) / float(b), frames=int(s['nb_read_packets']),
                duration=float(j['format']['duration']))


def grey(p, w=240):
    h = int(round(w * 9 / 16 / 2)) * 2
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(p), '-vf', f'scale={w}:{h},format=gray', '-f', 'rawvideo', '-'],
                       capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.uint8).reshape(-1, h, w).astype(np.float32)


def rig_motion(npz):
    D = np.load(npz)
    q = D['q']
    dots = np.abs((q[1:] * q[:-1]).sum(-1)).clip(0, 1)
    ang = np.degrees(2 * np.arccos(dots)).max(1)
    dp = np.linalg.norm(np.diff(D['heads'][:, 0], axis=0), axis=1)
    dc = np.linalg.norm(np.diff(D['cam'], axis=0), axis=1)
    return ang, dp, dc, len(q)


def check(mp4, npz, lead, loops, ref=None):
    pr = probe(mp4)
    ang, dp, dc, F = rig_motion(npz)
    expected = lead + loops * (F - 1) + 1 if loops > 1 else lead + F
    out = dict(video=str(mp4), **pr, expected=expected, issues=[])

    def issue(sev, msg):
        out['issues'].append(dict(layer=2, code='video', sev=sev, msg=msg))
    if (pr['w'], pr['h']) != (W, H) or abs(pr['fps'] - FPS) > 0.01:
        issue(2, f"resolução/fps {pr['w']}x{pr['h']} @ {pr['fps']:.2f} (esperado {W}x{H} @ {FPS})")
    if pr['frames'] != expected:
        issue(2, f"{pr['frames']} quadros; esperado {expected} (faltando ou sobrando)")
    if abs(pr['frames'] - round(pr['duration'] * pr['fps'])) > 1:
        issue(1, f"contagem de quadros {pr['frames']} não bate com a duração {pr['duration']:.2f} s")
    G = grey(mp4)
    d = np.abs(np.diff(G, axis=0)).mean((1, 2))      # transition v -> v+1

    def rig(v):  # video frame -> action frame index (0-based)
        if v < lead:
            return 0
        k = v - lead
        if loops > 1:
            return k % (F - 1) if k < loops * (F - 1) else F - 1
        return min(k, F - 1)
    moving, still = np.zeros(len(d), bool), np.zeros(len(d), bool)
    for v in range(len(d)):
        a, b = rig(v), rig(v + 1)
        if b == a + 1:
            m_ang, m_p, m_c = ang[a], dp[a], dc[a]
        elif b == 0 and a == F - 2:   # the loop seam: frame F-1 is frame 0 again
            m_ang, m_p, m_c = ang[a], dp[a], dc[a]
        else:
            m_ang = m_p = m_c = 0.0
        moving[v] = m_ang > 2.5 or m_p > 0.003 or m_c > 0.003  # (a head turning 1-2 deg/frame barely changes a full-body frame)
        still[v] = m_ang < 0.05 and m_p < 0.0003 and m_c < 0.0003
    frozen = np.flatnonzero(moving & (d < 0.02))
    out['frozen'] = int(len(frozen))
    if len(frozen):
        issue(2 if len(frozen) >= 3 else 1, f'{len(frozen)} quadro(s) congelado(s)/duplicado(s) com o boneco em movimento (quadro {int(frozen[0]) + 1})')
    base = np.median(d[moving]) if moving.any() else 1.0
    fl = np.flatnonzero(still & (d > max(0.25, 0.15 * base)))
    out['flicker'] = int(len(fl))
    if len(fl):
        issue(1, f'imagem muda com o boneco parado em {len(fl)} quadro(s) (flicker? quadro {int(fl[0]) + 1}, dif {d[fl].max():.2f})')
    k = 0
    while k < len(d) and d[k] < 0.05:  # (x264 noise on the cloned frames reaches ~0.03)
        k += 1
    out['still_start_s'] = round((k + 1) / FPS, 2)
    if (k + 1) / FPS < 0.5:
        issue(1, f'começa parado só {(k + 1) / FPS:.2f} s (mínimo 0,5 s)')
    if ref:
        rd = probe(ref)['duration']
        out['ref_duration'] = rd
        if pr['duration'] + 0.05 < rd:  # the therapeutic rhythm wins over the old length (approved 13/11): a note
            out['note'] = f"vídeo {pr['duration']:.1f} s, mais curto que o de referência ({rd:.1f} s); ritmo terapêutico prevalece"
    out['video_status'] = 'quebrado' if any(i['sev'] >= 2 for i in out['issues']) else 'suspeito' if out['issues'] else 'ok'
    return out


if __name__ == '__main__':
    a = sys.argv[1:]
    print(json.dumps(check(a[0], a[1], int(a[2]), int(a[3]), a[4] if len(a) > 4 else None), ensure_ascii=False))
