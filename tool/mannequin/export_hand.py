"""Exports the hand close-up scenes (tool/build_library_hand_animations.py) frame by frame, for the
mannequin-style hand render (render_hand.py). Same kinematics and checks as the Lottie version.

    python3 tool/mannequin/export_hand.py <out_dir> [slugs...]     # <out_dir>/<slug>.json

World axes of the builder: x along the forearm (hand at +x), y up (table top at y = 0), z towards the camera
side. Each frame stores the forearm, palm outline, the four fingers and the thumb (joint points, metres).
"""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_library_hand_animations as H  # noqa: E402
from kineti_lottie import FPS  # noqa: E402

SLUGS = ['wrist_flexion_extension', 'forearm_pronation_supination', 'open_close_hand', 'thumb_opposition']
EDGES = {'wrist_flexion_extension': H.EDGE, 'forearm_pronation_supination': H.EDGE,
         'open_close_hand': H.ON_TABLE, 'thumb_opposition': H.ON_TABLE}


def main():
    out, slugs = Path(sys.argv[1]), sys.argv[2:] or SLUGS
    out.mkdir(parents=True, exist_ok=True)
    seen = {}
    orig = H.fit_scene

    def spy(title, cam, track, *a, **kw):
        seen.update(cam=cam, track=track)
        return orig(title, cam, track, *a, **kw)

    H.fit_scene = spy
    for slug in slugs:
        H.SCENES[slug]()  # builds and checks the Lottie scene, and records its camera and track
        cam, tr = seen['cam'], seen['track']
        n = int(round(tr.duration * FPS))
        frames = []
        for f in range(n):
            g = H.geometry(tr.at(f / FPS))
            frames.append({k: g[k] for k in ('forearm', 'palm', 'thumb', *H.ORDER)})
        data = {'slug': slug, 'fps': FPS, 'edge': EDGES[slug], 'cam_right': list(cam.right), 'cam_up': list(cam.up),
                'widths': {'forearm': H.FORE_W, 'palm': H.PALM_W, 'thumb': H.THUMB_W,
                           **{k: H.FINGERS[k][2] for k in H.ORDER}}, 'frames': frames}
        json.dump(data, open(out / f'{slug}.json', 'w'))
        print(slug, n, 'frames')


if __name__ == '__main__':
    main()
