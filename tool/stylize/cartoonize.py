"""Video -> flat illustration (internal look test).

    build/mocap-venv/bin/python tool/stylize/cartoonize.py <video> <out.mp4> [--start 4 --seconds 6 --colors 9]

Edge-preserving smoothing, a fixed palette (k-means on frames spread over the
clip, so colours do not flicker), and dark outlines from the smoothed image.
"""
import argparse

import cv2
import numpy as np


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('video')
    ap.add_argument('out')
    ap.add_argument('--start', type=float, default=0.0)
    ap.add_argument('--seconds', type=float, default=6.0)
    ap.add_argument('--colors', type=int, default=9)
    a = ap.parse_args()
    cap = cv2.VideoCapture(a.video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    cap.set(cv2.CAP_PROP_POS_MSEC, a.start * 1000)
    frames = []
    while len(frames) < int(a.seconds * fps):
        ok, f = cap.read()
        if not ok:
            break
        frames.append(f)

    def smooth(f):
        s = f
        for _ in range(4):
            s = cv2.bilateralFilter(s, 9, 40, 9)
        return s

    sm = [smooth(f) for f in frames]
    # one palette for the whole clip (Lab space, k-means on a sample of pixels)
    lab = np.concatenate([cv2.cvtColor(s, cv2.COLOR_BGR2LAB)[::6, ::6].reshape(-1, 3) for s in sm[::max(1, len(sm) // 8)]])
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.5)
    _, _, centres = cv2.kmeans(lab.astype(np.float32), a.colors, None, crit, 4, cv2.KMEANS_PP_CENTERS)
    h, w = frames[0].shape[:2]
    out = cv2.VideoWriter(a.out, cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))
    prev_edges = None
    for s in sm:
        L = cv2.cvtColor(s, cv2.COLOR_BGR2LAB).reshape(-1, 3).astype(np.float32)
        idx = np.argmin(((L[:, None, :] - centres[None]) ** 2).sum(-1), axis=1)
        flat = cv2.cvtColor(centres[idx].reshape(h, w, 3).astype(np.uint8), cv2.COLOR_LAB2BGR)
        flat = cv2.medianBlur(flat, 5)
        gray = cv2.cvtColor(s, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 30, 80).astype(np.float32) / 255
        edges = cv2.GaussianBlur(cv2.dilate(edges, np.ones((2, 2), np.uint8)), (3, 3), 0)
        if prev_edges is not None:  # light temporal smoothing of the outline
            edges = 0.6 * edges + 0.4 * prev_edges
        prev_edges = edges
        line = np.array([40, 30, 25], np.float32)
        img = flat.astype(np.float32) * (1 - edges[..., None] * 0.85) + line * edges[..., None] * 0.85
        out.write(np.clip(img, 0, 255).astype(np.uint8))
    out.release()
    print(f'{len(sm)} frames -> {a.out}')


if __name__ == '__main__':
    main()
