"""Mixamo pilot: renders a few exercises with the Kineti woman driven by Mixamo motion.

    python3 tool/mixamo/pilot.py                  # every clip, mp4 in build/mixamo/
    python3 tool/mixamo/pilot.py --still mini_squat

Settings:
    KINETI_BLENDER     Blender executable (default: the Windows install, run from WSL)
    KINETI_DOCS        folder with kineti_woman_mixamo.blend and downloads/mixamo/
"""

import argparse
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BLENDER = os.environ.get('KINETI_BLENDER', '/mnt/e/tools/blender-5.3.0/blender.exe')
DOCS = Path(os.environ.get('KINETI_DOCS', '/mnt/c/Users/Dioner/Documents/kineti_exercises'))
CHARACTER = DOCS / 'kineti_woman_mixamo.blend'
MIXAMO = DOCS / 'downloads' / 'mixamo'

# Each clip: Mixamo source, timeline [[from, to, frames]] in source frames, camera.
CLIPS = {
    # Air Squat goes to 131 degrees of knee flexion; a mini squat stops near 60 (source frame 11.5).
    'mini_squat': {'fbx': 'Air_Squat.fbx', 'yaw': 70,
                   'timeline': [[1, 1, 10], [1, 11.5, 45], [11.5, 11.5, 12], [11.5, 1, 45], [1, 1, 8]],
                   'still': [1, 55, 100]},
    # Stand To Sit forward, then backwards: sit down, pause, stand up.
    'sit_to_stand_exercise': {'fbx': 'Stand_To_Sit.fbx', 'yaw': 60, 'chair': True, 'chair_frame': 75,
                              'shift_y': 0.2,
                              'timeline': [[1, 1, 10], [1, 50, 60], [50, 50, 20], [50, 1, 60], [1, 1, 10]],
                              'still': [1, 40, 75, 120]},
}
# Mixamo's own realistic characters ("With Skin" FBX): no retarget, rendered in Cycles.
STS = CLIPS['sit_to_stand_exercise']
for who in ('Megan', 'Jody'):
    CLIPS[f'{who.lower()}_sit_to_stand'] = {**STS, 'fbx': f'{who}_Stand_To_Sit.fbx', 'skinned': True, 'engine': 'CYCLES'}


# Motion from the desk-break library (MIT, github.com/shlomorsh/desk-break) on Jody.
DESK_BREAK = Path(os.environ.get('KINETI_DESK_BREAK', '/tmp/claude-1000/-home-dioner-projects-kineti-animated-exercices/'
                                 '3fb48f76-c878-448c-b5f8-a25f2cc93391/scratchpad/deskbreak/repo/library/exercises.glb'))
LYING = {'ground': 'mat', 'yaw': 90, 'look_z': 0.3, 'cam_height': 1.1, 'distance': 8.0}
for slug, motion, extra in (
        ('heel_slides', 'heel-slides', LYING),
        ('bridge', 'glute-bridge', LYING),
        ('side_lying_clamshell', 'clam-shell', {**LYING, 'yaw': 0}),
        ('seated_knee_extension', 'chair-knee-extension', {'chair': True, 'chair_frame': 1, 'yaw': 70})):
    CLIPS[f'jody_{slug}'] = {'fbx': 'Jody_Stand_To_Sit.fbx', 'skinned': True, 'engine': 'CYCLES', 'motion': motion,
                             'motion_glb': 'DESK_BREAK', 'timeline': 'auto', 'still': [1, 30, 60], **extra}


def win(path):
    return subprocess.run(['wslpath', '-w', str(path)], capture_output=True, text=True, check=True).stdout.strip()


def render(slug, still, width):
    clip = dict(CLIPS[slug])
    work = REPO / 'build' / 'mixamo' / slug
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    spec = {**clip, 'fbx': win(MIXAMO / clip['fbx']), 'out': win(work / 'f'), 'width': width}
    if clip.get('motion_glb'):
        spec['motion_glb'] = win(DESK_BREAK)
    if not still:
        spec.pop('still', None)
    (work / 'spec.json').write_text(json.dumps(spec))
    t0 = time.time()
    scene = ['--factory-startup'] if clip.get('skinned') else [win(CHARACTER)]
    run = subprocess.run([BLENDER, '-b', *scene, '--python', win(Path(__file__).with_name('render_mixamo.py')),
                          '--', win(work / 'spec.json')], capture_output=True, text=True)
    (work / 'blender.log').write_text(run.stdout + run.stderr)
    if 'DONE' not in run.stdout:
        print(run.stdout[-3000:] + run.stderr[-2000:])
        raise SystemExit(f'{slug}: Blender failed')
    frames = sorted(work.glob('f_*.png'))
    if still:
        print(f'{slug}: {len(frames)} stills in {work} ({time.time() - t0:.0f} s)')
        return
    out = REPO / 'build' / 'mixamo' / f'{slug}.mp4'
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-framerate', '30', '-i', str(work / 'f_%04d.png'),
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '20', '-tune', 'animation',
                    '-movflags', '+faststart', str(out)], check=True)
    print(f'{out}: {len(frames)} frames ({time.time() - t0:.0f} s)')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('slugs', nargs='*')
    ap.add_argument('--still', action='store_true')
    ap.add_argument('--width', type=int, default=1280)
    a = ap.parse_args()
    for slug in a.slugs or CLIPS:
        render(slug, a.still, a.width)


if __name__ == '__main__':
    main()
