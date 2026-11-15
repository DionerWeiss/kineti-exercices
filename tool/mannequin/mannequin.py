"""Kineti mannequin videos: the desk-break rig (github.com/shlomorsh/desk-break, MIT)
repainted with the Kineti palette and mark (render_mannequin.py).

    python3 tool/mannequin/mannequin.py setup                      # clone desk-break at the pinned commit
    python3 tool/mannequin/mannequin.py build [ids...]             # kineti_moves.json -> <out>/kineti_lib (with ids: <out>/kineti_sub,
                                                                   # also desk-break's moves forked in deskbreak_moves.json)
    python3 tool/mannequin/mannequin.py sync ids...                # the moves of kineti_sub -> the avatar lib (MANNEQUIN_AVATAR)
    python3 tool/mannequin/mannequin.py sheet [ids...]             # stills + contact sheet build/mannequin/sheet_*.png
    python3 tool/mannequin/mannequin.py render [ids...]            # MP4 in build/mannequin/videos/<id>.mp4
    python3 tool/mannequin/mannequin.py qa [ids...]                # avatar only: pose + motion checks -> <out>/qa (qa_pose.py, motion_review.py)

Without ids, every job in jobs.json. Each job: {"lib": "deskbreak"|"kineti"|"hand" (with "scene": a hand scene of export_hand.py), "view": ..., "props": [...],
"frame": "full"|"upper"|"lower", "pocketphysio": [ids], "move": optional action to reuse (default the id)}. Views and props: see render_mannequin.py (DIRS, props).
Env: KINETI_BLENDER (default: the Windows install), MANNEQUIN_PALETTE (default areia), MANNEQUIN_OUT (default build/mannequin),
MANNEQUIN_AVATAR (a lib .blend from avatar/fit_avatar.py: kineti jobs use the humanoid avatar instead of the mannequin),
MANNEQUIN_RES (WxH, default 960x540), MANNEQUIN_VIDEOS (the MP4 folder, default <out>/videos),
QA=1 with render: also write the pose checks to <out>/qa, review the motion (loops the action to 2 repetitions) and check
the encoded video. Every video starts with 0.5 s still on the first pose. MANNEQUIN_DROP_FRAMES=1: delete the PNG frames
once encoded. MANNEQUIN_MOVES_DIR: where `build` reads kineti_moves.json / deskbreak_moves.json (default here). MANNEQUIN_PY: the Python with numpy for the review scripts (default: uv run --with numpy).
"""
import json, os, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
DESK = REPO / 'build' / 'desk-break'
DESK_COMMIT = '8d475aa476b2c0e9ec6d09d8558faf17161e19ef'  # 0.2.2, 2026-10-07
OUT = Path(os.environ.get('MANNEQUIN_OUT', REPO / 'build' / 'mannequin'))
BLENDER = os.environ.get('KINETI_BLENDER', '/mnt/e/tools/blender-5.3.0/blender.exe')
PALETTE = os.environ.get('MANNEQUIN_PALETTE', 'areia')
LIBS = {'deskbreak': DESK / 'library' / 'exercises.blend', 'kineti': OUT / 'kineti_lib' / 'exercises.blend'}
AVATAR = os.environ.get('MANNEQUIN_AVATAR')  # a lib .blend whose body is the humanoid avatar (avatar/fit_avatar.py)
if AVATAR:  # the avatar lib also carries desk-break's actions (same rig), so every job uses the avatar
    LIBS['kineti'] = LIBS['deskbreak'] = Path(AVATAR)


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
        if line.startswith(('JOB', 'PLANT', 'PLANTDBG', 'BALL', 'BALLF', 'HELDBALL', 'DONE', 'OK', 'KEY', 'TOUCH', 'AVATAR', 'QA', 'GROUND', 'CLEAR', 'UNCLIP', 'KBDBG', 'KBTRACE', 'built', 'DBG', 'QADBG', 'WARNING', 'ERROR', 'Traceback', 'Error', 'KeyError')) or 'Error' in line:
            print(' ', line)
    if r.returncode:
        print(r.stdout[-2000:], r.stderr[-2000:])
        raise SystemExit(f'blender failed ({r.returncode})')


def setup():
    if not DESK.exists():
        subprocess.run(['git', 'clone', '-q', 'https://github.com/shlomorsh/desk-break.git', str(DESK)], check=True)
    subprocess.run(['git', '-C', str(DESK), 'checkout', '-q', DESK_COMMIT], check=True)
    print('desk-break at', DESK_COMMIT[:7])


def build(ids=()):
    """kineti_moves.json -> <out>/kineti_lib; with ids, only those moves -> <out>/kineti_sub (then `sync`)."""
    src = Path(os.environ.get('MANNEQUIN_MOVES_DIR', HERE))  # (a copy of both moves files, to work on them apart)
    moves = src / 'kineti_moves.json'
    out = OUT / ('kineti_sub' if ids else 'kineti_lib')
    out.mkdir(parents=True, exist_ok=True)
    if ids:  # (desk-break's own moves that the jobs use are forked in deskbreak_moves.json, built the same way)
        allm = json.load(open(moves, encoding='utf-8'))
        desk = json.load(open(src / 'deskbreak_moves.json', encoding='utf-8'))['exercises']
        sub = [e for e in allm['exercises'] + desk if e['id'] in ids]
        missing = set(ids) - {e['id'] for e in sub}
        if missing:
            raise SystemExit(f'not in kineti_moves.json / deskbreak_moves.json: {sorted(missing)}')
        moves = out / 'moves.json'
        json.dump(allm | {'exercises': sub}, open(moves, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    blender('-P', win(HERE / 'build_lib.py'), '--', win(DESK / 'library'), win(moves), win(out),
            env={k: os.environ[k] for k in ('KB_DEBUG', 'KB_KEYS', 'KB_TRACE') if os.environ.get(k)} or None)


def sync(ids):
    """Copies the moves just built (`build ids`) into the avatar lib (MANNEQUIN_AVATAR), replacing the old ones."""
    if not AVATAR or not ids:
        raise SystemExit('sync needs MANNEQUIN_AVATAR and ids')
    blender(win(AVATAR), '--python', win(HERE / 'sync_actions.py'), '--', win(OUT / 'kineti_sub' / 'exercises.blend'), *ids)


def jobs(ids):
    allj = json.load(open(HERE / 'jobs.json'))
    sel = {i: allj[i] for i in (ids or allj)}
    missing = [i for i in ids if i not in allj]
    if missing:
        raise SystemExit(f'not in jobs.json: {missing}')
    return sel


def run(sel, outdir, still=None, qa=False):
    by_lib = {}
    for i, j in sel.items():
        by_lib.setdefault(j['lib'], []).append(
            f"{i}:{j['view']}:{'+'.join(j.get('props', []))}:{j.get('frame', 'full')}:{j.get('move', '')}")
    for lib, js in by_lib.items():
        for k in range(0, len(js), 20):  # several jobs per Blender launch
            blender(win(LIBS[lib]), '--python', win(HERE / 'render_mannequin.py'), '--', win(outdir), PALETTE,
                    win(HERE / 'kineti_mark.png'), *js[k:k + 20],
                    env=({'STILL': still} if still else {})
                    | ({'QA': win(OUT / 'qa')} if qa else {}) | ({'NORENDER': '1'} if qa == 'only' else {}) | ({k: os.environ[k] for k in ('BALL_DEBUG', 'PLANT_DEBUG', 'QA_DEBUG', 'QA_PEN', 'NOPLANT', 'NOUNCLIP', 'EEVEE_SAMPLES') if os.environ.get(k)})
                    | ({'AVATAR': '1'} if AVATAR else {})
                    | ({'MANNEQUIN_RES': os.environ['MANNEQUIN_RES']} if os.environ.get('MANNEQUIN_RES') else {}) or None)


def sheet(ids):
    sel = jobs(ids)
    st = OUT / 'stills'
    fr = os.environ.get('SHEET_FRACS', '0,0.25,0.5')  # the points of the motion shown, one column each
    ncol = len(fr.split(','))
    hands({i: j for i, j in sel.items() if j['lib'] == 'hand'}, st, still=fr)
    run({i: j for i, j in sel.items() if j['lib'] != 'hand'}, st, still=fr, qa=bool(os.environ.get('QA')))
    names = list(sel)
    for n in range(0, len(names), 12):  # 12 exercises x ncol frames per sheet
        chunk = names[n:n + 12]
        inputs, filt, rows = [], [], []
        for r, name in enumerate(chunk):
            fs = sorted((st / name).glob('f_*.png'))[:ncol]
            for c, f in enumerate(fs):
                inputs += ['-i', str(f)]
                idx = len(inputs) // 2 - 1
                filt.append(f"[{idx}]scale=400:-1,drawtext=text='{name}':x=6:y=6:fontsize=16:fontcolor=0x334155[v{idx}]")
            rows.append([len(inputs) // 2 - len(fs) + c for c in range(len(fs))])
        layout = '|'.join(f'{c * 400}_{r * 225}' for r, row in enumerate(rows) for c in range(len(row)))
        total = sum(len(r) for r in rows)
        out = OUT / f"{os.environ.get('SHEET_NAME', 'sheet')}_{n // 12 + 1:02d}.png"
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


LEAD = 15  # the video starts still on the first pose for 0.5 s


def pyrun(script, *args):
    """Runs a review script that needs numpy (motion_review.py, video_qa.py) with MANNEQUIN_PY (default: uv)."""
    py = os.environ.get('MANNEQUIN_PY', 'uv run -q --no-project --with numpy python3').split()
    r = subprocess.run([*py, str(HERE / script), *map(str, args)], capture_output=True, text=True)
    if r.returncode:
        print(r.stdout[-1500:], r.stderr[-1500:])
        raise SystemExit(f'{script} failed')
    return r.stdout


def motion(name):
    """Layer-2 motion review of one job (<out>/qa/<name>.motion.json); None without motion data."""
    if not (OUT / 'qa' / f'{name}.motion.npz').exists():
        return None
    pyrun('motion_review.py', OUT / 'qa', name)
    return json.load(open(OUT / 'qa' / f'{name}.motion.json', encoding='utf-8'))


def encode(name, vids):
    """frames/<name>/f_*.png -> <vids>/<name>.mp4: 0.5 s still on the first pose, then the action repeated until it
    shows 2 repetitions (motion.json "loops"; the last frame of a loop is the first again, so it is played once at
    the very end). Then the video checks (video_qa.py -> <out>/qa/<name>.video.json)."""
    frames = sorted((OUT / 'frames' / name).glob('f_*.png'))
    m = motion(name) if os.environ.get('QA') else None
    loops = m['loops'] if m else 1
    vf = 'format=yuv420p'
    if loops > 1:
        vf += f',loop=loop={loops - 1}:size={len(frames) - 1}:start=0'
    vf += f',setpts=N/30/TB,tpad=start_duration={LEAD / 30}:start_mode=clone'
    out = vids / f'{name}.mp4'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-framerate', '30', '-start_number', frames[0].stem[2:], '-i',
                    str(OUT / 'frames' / name / 'f_%04d.png'), '-vf', vf, '-r', '30', '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                    '-crf', '22', '-tune', 'animation', '-movflags', '+faststart', str(out)], check=True)
    print(out, f'loops {loops}')
    if m:
        ref = next((p for p in (Path(os.environ.get('MANNEQUIN_REF_VIDEOS', '/mnt/e/mannequin/avatar_man/out/videos_v9')) / f'{name}.mp4',
                                Path('/mnt/e/mannequin/videos') / f'{name}.mp4') if p.exists()), None)
        v = json.loads(pyrun('video_qa.py', out, OUT / 'qa' / f'{name}.motion.npz', LEAD, loops, *([ref] if ref else [])))
        json.dump(v, open(OUT / 'qa' / f'{name}.video.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(' ', 'video', v['video_status'], '; '.join(i['msg'] for i in v['issues']))


def render(ids):
    sel = jobs(ids)
    frames = OUT / 'frames'
    hands({i: j for i, j in sel.items() if j['lib'] == 'hand'}, frames)
    run({i: j for i, j in sel.items() if j['lib'] != 'hand'}, frames, qa=bool(os.environ.get('QA')))
    vids = Path(os.environ.get('MANNEQUIN_VIDEOS', OUT / 'videos'))
    vids.mkdir(parents=True, exist_ok=True)
    for name in sel:
        encode(name, vids)
        if os.environ.get('MANNEQUIN_DROP_FRAMES'):  # 1080p PNGs: ~400 MB per video
            for f in (frames / name).glob('f_*.png'):
                f.unlink()


def qa(ids):
    """Pose and motion checks only (avatar): <out>/qa/<id>.json (layer 1) and <id>.motion.json (layer 2), nothing rendered."""
    sel = jobs(ids)
    (OUT / 'qa').mkdir(parents=True, exist_ok=True)
    run({i: j for i, j in sel.items() if j['lib'] != 'hand'}, OUT / 'frames', qa='only')
    for name in sel:
        m = motion(name)
        q = OUT / 'qa' / f'{name}.json'
        if m and q.exists():
            st = json.load(open(q, encoding='utf-8'))['status']
            print(f"  {name}: técnico {st}, movimento {m['motion_status']}")


if __name__ == '__main__':
    cmd, ids = (sys.argv[1:] + [''])[0], sys.argv[2:]
    {'setup': lambda: setup(), 'build': lambda: build(ids), 'sync': lambda: sync(ids), 'sheet': lambda: sheet(ids),
     'render': lambda: render(ids), 'qa': lambda: qa(ids)}.get(cmd, lambda: print(__doc__))()
