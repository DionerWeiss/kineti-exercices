"""Video -> body landmarks with MediaPipe Pose (heavy model), every frame.

    build/mocap-venv/bin/python tool/mocap/extract_pose.py <video> <out.json>

Writes, per frame, the 33 world landmarks (metres, origin between the hips; MediaPipe axes: x to the
image right, y down, z grows away from the camera; to_scene.py converts them), the image landmarks (normalised x, y) and
each landmark's visibility.
"""

import json
import sys
from pathlib import Path

import cv2
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions, vision

MODEL = Path(__file__).resolve().parents[2] / 'build' / 'mocap-models' / 'pose_landmarker_heavy.task'


def main(video, out):
    cap = cv2.VideoCapture(video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    size = [int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))]
    opts = vision.PoseLandmarkerOptions(base_options=BaseOptions(model_asset_path=str(MODEL)),
                                        running_mode=vision.RunningMode.VIDEO, num_poses=1,
                                        min_pose_detection_confidence=0.5, min_tracking_confidence=0.5)
    frames = []
    with vision.PoseLandmarker.create_from_options(opts) as lm:
        i = 0
        while True:
            ok, img = cap.read()
            if not ok:
                break
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            res = lm.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), int(i * 1000 / fps))
            if res.pose_world_landmarks:
                w = res.pose_world_landmarks[0]
                n = res.pose_landmarks[0]
                frames.append({'i': i, 'world': [[p.x, p.y, p.z] for p in w],
                               'image': [[p.x, p.y] for p in n], 'vis': [p.visibility for p in n]})
            else:
                frames.append({'i': i, 'world': None})
            i += 1
    Path(out).write_text(json.dumps({'video': video, 'fps': fps, 'size': size, 'frames': frames}))
    found = sum(1 for f in frames if f['world'])
    print(f'{found}/{len(frames)} frames with a pose, {fps:.0f} fps')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
