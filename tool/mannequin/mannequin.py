"""Kineti mannequin videos: the desk-break rig (github.com/shlomorsh/desk-break, MIT)
repainted with the Kineti palette and mark (render_mannequin.py).

    python3 tool/mannequin/mannequin.py setup                      # clone desk-break at the pinned commit
    python3 tool/mannequin/mannequin.py build                      # kineti_moves.json -> build/mannequin/kineti_lib
    python3 tool/mannequin/mannequin.py sheet [ids...]             # stills + contact sheet build/mannequin/sheet_*.png
    python3 tool/mannequin/mannequin.py render [ids...]            # MP4 in build/mannequin/videos/<id>.mp4

Without ids, every job in jobs.json. Each job: {"lib": "deskbreak"|"kineti"|"hand" (with "scene": a hand scene of export_hand.py), "view": ..., "props": [...],
"frame": "full"|"upper"|"lower", "pocketphysio": [ids]}. Views and props: see render_mannequin.py (DIRS, props).
Env: KINETI_BLENDER (default: the Windows install), MANNEQUIN_PALETTE (default areia).
"""
import json, os, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
DESK = REPO / 'build' / 'desk-break'
DESK_COMMIT = '8d475aa476b2c0e9ec6d09d8558faf17161e19ef'  # 0.2.2, 2026-10-07
OUT = REPO / 'build' / 'mannequin'
BLENDER = os.environ.get('KINETI_BLENDER', '/mnt/e/tools/blender-5.3.0/blender.exe')
PALETTE = os.environ.get('MANNEQUIN_PALETTE', 'areia')
LIBS = {'deskbreak': DESK / 'library' / 'exercises.blend', 'kineti': OUT / 'kineti_lib' / 'exercises.blend'}


def win(p):
    if not BLENDER.endswith('.exe'):
        return str(p)
    return subprocess.run(['wslpath', '-w', str(p)], capture_output=True, text=True, check=True).stdout.strip()


def blender(*args, env=None):
    e = dict(os.environ, **(env or {}))
    if env and BLENDER.endswith('.exe'):
        e['WSLENV'] = ':'.join(list(env) + ([e['WSLENV']] if e.get('WSLENV') else []))
    r = subprocess.run([BLENDER, '-b', *args], capture_output=True, text=True, env=e)
    for line in r.stdout.splitlines():
        if line.startswith(('JOB', 'DONE', 'OK', 'Traceback', 'Error', 'KeyError')) or 'Error' in line:
            print(' ', line)
    if r.returncode:
        print(r.stdout[-2000:], r.stderr[-2000:])
        raise SystemExit(f'blender failed ({r.returncode})')


def setup():
    if not DESK.exists():
        subprocess.run(['git', 'clone', '-q', 'https://github.com/shlomorsh/desk-break.git', str(DESK)], check=True)
    subprocess.run(['git', '-C', str(DESK), 'checkout', '-q', DESK_COMMIT], check=True)
    print('desk-break at', DESK_COMMIT[:7])


def build():
    out = OUT / 'kineti_lib'
    out.mkdir(parents=True, exist_ok=True)
    blender('-P', win(HERE / 'build_lib.py'), '--', win(DESK / 'library' / 'build_library.py'), win(HERE / 'kineti_moves.json'),
            win(out))


def jobs(ids):
    allj = json.load(open(HERE / 'jobs.json'))
    sel = {i: allj[i] for i in (ids or allj)}
    missing = [i for i in ids if i not in allj]
    if missing:
        raise SystemExit(f'not in jobs.json: {missing}')
    return sel


def run(sel, outdir, still=None):
    by_lib = {}
    for i, j in sel.items():
        by_lib.setdefault(j['lib'], []).append(f"{i}:{j['view']}:{'+'.join(j.get('props', []))}:{j.get('frame', 'full')}")
    for lib, js in by_lib.items():
        for k in range(0, len(js), 20):  # several jobs per Blender launch
            blender(win(LIBS[lib]), '--python', win(HERE / 'render_mannequin.py'), '--', win(outdir), PALETTE,
                    win(HERE / 'kineti_mark.png'), *js[k:k + 20], env={'STILL': still} if still else None)


def sheet(ids):
    sel = jobs(ids)
    st = OUT / 'stills'
    hands({i: j for i, j in sel.items() if j['lib'] == 'hand'}, st, still='0,0.25,0.5')
    run({i: j for i, j in sel.items() if j['lib'] != 'hand'}, st, still='0,0.25,0.5')
    names = list(sel)
    for n in range(0, len(names), 12):  # 12 exercises x 3 frames per sheet
        chunk = names[n:n + 12]
        inputs, filt, rows = [], [], []
        for r, name in enumerate(chunk):
            fs = sorted((st / name).glob('f_*.png'))[:3]
            for c, f in enumerate(fs):
                inputs += ['-i', str(f)]
                idx = len(inputs) // 2 - 1
                filt.append(f"[{idx}]scale=400:-1,drawtext=text='{name}':x=6:y=6:fontsize=16:fontcolor=0x334155[v{idx}]")
            rows.append([len(inputs) // 2 - len(fs) + c for c in range(len(fs))])
        layout = '|'.join(f'{c * 400}_{r * 225}' for r, row in enumerate(rows) for c in range(len(row)))
        total = sum(len(r) for r in rows)
        out = OUT / f'sheet_{n // 12 + 1:02d}.png'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', *inputs, '-filter_complex',
                        ';'.join(filt) + ';' + ''.join(f'[v{i}]' for i in range(total)) +
                        f'xstack=inputs={total}:layout={layout}:fill=white', str(out)], check=True)
        print(out)


def hands(sel, outdir, still=None):
    """Hand close-ups (lib "hand"): Lottie hand kinematics exported by export_hand.py, rendered by render_hand.py."""
    if not sel:
        return
    src = OUT / 'hand'
    subprocess.run([sys.executable, str(HERE / 'export_hand.py'), str(src), *{j['scene'] for j in sel.values()}], check=True)
    for name, j in sel.items():
        (outdir / name).mkdir(parents=True, exist_ok=True)
        blender('--factory-startup', '--python', win(HERE / 'render_hand.py'), '--', win(src / f"{j['scene']}.json"),
                win(outdir / name), PALETTE, *([still] if still else []))


def render(ids):
    sel = jobs(ids)
    frames = OUT / 'frames'
    hands({i: j for i, j in sel.items() if j['lib'] == 'hand'}, frames)
    run({i: j for i, j in sel.items() if j['lib'] != 'hand'}, frames)
    vids = OUT / 'videos'
    vids.mkdir(parents=True, exist_ok=True)
    for name in sel:
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-framerate', '30', '-i', str(frames / name / 'f_%04d.png'),
                        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '22', '-tune', 'animation',
                        '-movflags', '+faststart', str(vids / f'{name}.mp4')], check=True)
        print(vids / f'{name}.mp4')


if __name__ == '__main__':
    cmd, ids = (sys.argv[1:] + [''])[0], sys.argv[2:]
    {'setup': lambda: setup(), 'build': lambda: build(), 'sheet': lambda: sheet(ids),
     'render': lambda: render(ids)}.get(cmd, lambda: print(__doc__))()
