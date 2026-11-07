"""Video of a person doing an exercise -> the Kineti character doing it.

    python3 tool/mocap/render_mocap.py <video> <name> [--ball] [--camera 22,14] [--seconds 6] [--still]

1. MediaPipe Pose (build/mocap-venv) extracts the body landmarks, once per video.
2. to_scene.py scales, smooths, loops and grounds them into a render scene.
3. tool/blender/render_scene.py poses the character and renders; ffmpeg encodes
   build/mocap/<name>.mp4 with the same colour treatment as the library videos.
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'tool'))
from render_3d import BLENDER, CHARACTER, SATURATION, WIDTH, saturation_matrix, win  # noqa: E402

PY = REPO / 'build' / 'mocap-venv' / 'bin' / 'python'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('video')
    ap.add_argument('name')
    ap.add_argument('--ball', action='store_true')
    ap.add_argument('--camera', default='22,14')
    ap.add_argument('--seconds', type=float, default=6.0)
    ap.add_argument('--still', action='store_true')
    a = ap.parse_args()
    work = REPO / 'build' / 'mocap' / a.name
    work.mkdir(parents=True, exist_ok=True)
    marks = work / 'landmarks.json'
    if not marks.exists():
        subprocess.run([str(PY), str(REPO / 'tool' / 'mocap' / 'extract_pose.py'), a.video, str(marks)], check=True)
    scene = work / 'scene.json'
    cmd = [str(PY), str(REPO / 'tool' / 'mocap' / 'to_scene.py'), str(marks), str(scene),
           '--seconds', str(a.seconds), '--camera', a.camera] + (['--ball'] if a.ball else [])
    subprocess.run(cmd, check=True)
    for f in work.glob('f_*.png'):
        f.unlink()
    t0 = time.time()
    run = subprocess.run([BLENDER, '-b', win(CHARACTER), '--python', win(REPO / 'tool' / 'blender' / 'render_scene.py'),
                          '--', win(scene), win(work / 'f'), str(WIDTH), 'still' if a.still else 'anim'],
                         capture_output=True, text=True)
    if 'DONE' not in run.stdout:
        sys.stdout.write(run.stdout[-3000:] + run.stderr[-2000:])
        raise SystemExit('Blender failed')
    if a.still:
        print(f'{len(list(work.glob("f_*.png")))} stills in {work.relative_to(REPO)} ({time.time() - t0:.0f} s)')
        return
    out = REPO / 'build' / 'mocap' / f'{a.name}.mp4'
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-framerate', '30', '-i', str(work / 'f_%04d.png'),
                    '-vf', f'format=rgb24,colorchannelmixer={saturation_matrix(SATURATION)},format=yuv420p',
                    '-c:v', 'libx264', '-crf', '22', '-movflags', '+faststart', str(out)], check=True)
    print(f'{out.relative_to(REPO)}: {out.stat().st_size / 1024:.0f} KB ({time.time() - t0:.0f} s)')


if __name__ == '__main__':
    main()
