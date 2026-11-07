"""Renders library exercises with the 3D Kineti character.

    python3 tool/render_3d.py bridge mini_squat ...   # videos/<area>/<slug>.mp4
    python3 tool/render_3d.py --still bridge          # 4 PNG frames in build/3d/<slug>/
    python3 tool/render_3d.py --all                   # every exercise with a 3D-capable scene

Each slug is exported from its Lottie builder (tool/blender/export_scene.py),
posed and rendered in Blender (tool/blender/render_scene.py) and encoded
with ffmpeg. Settings:

    KINETI_BLENDER     Blender executable (default: the Windows install, run from WSL)
    KINETI_CHARACTER   character .blend (default: Documents/kineti_exercises/kineti_character.blend)
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BLENDER = os.environ.get('KINETI_BLENDER', '/mnt/e/tools/blender-5.3.0/blender.exe')
CHARACTER = os.environ.get('KINETI_CHARACTER',
                           '/mnt/c/Users/Dioner/Documents/kineti_exercises/kineti_character.blend')
SATURATION = 1.18   # luma-preserving, in RGB: neutrals (the background) keep their tone
ARM = 0.88          # upper arm and forearm length factor for the character
WIDTH = 1440
HAND_CLOSEUPS = {'wrist_flexion_extension', 'forearm_pronation_supination', 'open_close_hand', 'thumb_opposition'}


def win(path):
    """Windows path for Blender (a Windows program) to reach WSL or /mnt files."""
    return subprocess.run(['wslpath', '-w', str(path)], capture_output=True, text=True, check=True).stdout.strip()


def saturation_matrix(s):
    r, g, b = 0.2126, 0.7152, 0.0722
    rows = [[r * (1 - s) + s, g * (1 - s), b * (1 - s)],
            [r * (1 - s), g * (1 - s) + s, b * (1 - s)],
            [r * (1 - s), g * (1 - s), b * (1 - s) + s]]
    return ':'.join(f'{c1}{c2}={rows[i][j]:.4f}' for i, c1 in enumerate('rgb') for j, c2 in enumerate('rgb'))


def render(slug, area, still, width, arm):
    work = REPO / 'build' / '3d' / slug
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    scene_json = work / 'scene.json'
    subprocess.run([sys.executable, str(REPO / 'tool' / 'blender' / 'export_scene.py'), slug, str(scene_json)], check=True)
    t0 = time.time()
    cmd = [BLENDER, '-b', win(CHARACTER), '--python', win(REPO / 'tool' / 'blender' / 'render_scene.py'), '--',
           win(scene_json), win(work / 'f'), str(width), 'still' if still else 'anim', str(arm)]
    run = subprocess.run(cmd, capture_output=True, text=True)
    if 'DONE' not in run.stdout:
        sys.stdout.write(run.stdout[-3000:] + run.stderr[-2000:])
        raise SystemExit(f'{slug}: Blender failed')
    frames = sorted(work.glob('f_*.png'))
    if still:
        print(f'{slug}: {len(frames)} stills in {work.relative_to(REPO)} ({time.time() - t0:.0f} s)')
        return
    out = REPO / 'videos' / area / f'{slug}.mp4'
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-framerate', '30', '-i', str(work / 'f_%04d.png'),
                    '-vf', f'format=rgb24,colorchannelmixer={saturation_matrix(SATURATION)},format=yuv420p',
                    '-c:v', 'libx264', '-crf', '22', '-movflags', '+faststart',
                    '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', str(out)], check=True)
    print(f'{str(out.relative_to(REPO)):60s} {len(frames)} frames, {out.stat().st_size / 1024:.0f} KB, '
          f'{time.time() - t0:.0f} s')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('slugs', nargs='*')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--still', action='store_true')
    ap.add_argument('--width', type=int, default=WIDTH)
    ap.add_argument('--arm', type=float, default=ARM)
    a = ap.parse_args()
    cat = json.loads((REPO / 'catalog.json').read_text(encoding='utf-8'))
    areas = {e['slug']: e['area'] for e in cat['exercises']}
    slugs = [s for s in areas if s not in HAND_CLOSEUPS] if a.all else a.slugs
    for slug in slugs:
        if slug not in areas:
            raise SystemExit(f'{slug}: not in catalog.json')
        render(slug, areas[slug], a.still, a.width, a.arm)


if __name__ == '__main__':
    main()
