"""Removes one-frame twitches from a generated Lottie, in place (both drivers' output).

    python3 lottie_despike.py <anim.json>

A twitch is a key that steps out and straight back while the pose around it is still: on a transform track (position,
rotation, scale of a layer) the key at t differs from the keys at t-1 and t+1 in opposite directions by more than a
small tolerance, those two neighbours agree (within a quarter of the step) and the steps just outside (t-2 -> t-1,
t+1 -> t+2) are under half of it. Rendered at 60 fps such a key flashes for one frame (a hand or a whole arm jumping
3-10 px and back while the figure holds a pose). It is replaced by its neighbours' mean. A real turning point (the
bottom of a squat, a jump's landing) has motion on both sides and is kept, so are hold keys and opacity switches.
"""
import json
import sys

TOL = {'p': 0.5, 'r': 0.3, 's': 0.3}


def fix_track(prop, tol):
    ks = prop.get('k')
    if prop.get('a') != 1 or not isinstance(ks, list) or len(ks) < 5:
        return 0
    if any(not isinstance(k, dict) or 's' not in k or k.get('h') == 1 for k in ks):
        return 0
    by_t = {int(round(k['t'])): k for k in ks}
    n = 0
    for t, k in by_t.items():
        if not all(t + d in by_t for d in (-2, -1, 1, 2)):
            continue
        v = [by_t[t + d]['s'] for d in (-2, -1, 0, 1, 2)]
        changed = False
        for i in range(len(v[2])):
            if not all(isinstance(x[i], (int, float)) for x in v):
                continue
            a, b = v[2][i] - v[1][i], v[3][i] - v[2][i]
            m = min(abs(a), abs(b))
            if a * b < 0 and m > tol and abs(v[3][i] - v[1][i]) < 0.25 * m \
                    and max(abs(v[1][i] - v[0][i]), abs(v[4][i] - v[3][i])) < 0.5 * m:
                k['s'][i] = round((v[1][i] + v[3][i]) / 2, 3)
                changed = True
        n += changed
    return n


def walk_layers(layers):
    n = 0
    for l in layers:
        for key, tol in TOL.items():
            if key in l.get('ks', {}):
                n += fix_track(l['ks'][key], tol)
    return n


def main():
    path = sys.argv[1]
    d = json.load(open(path))
    n = walk_layers(d.get('layers', []))
    for a in d.get('assets', []):
        n += walk_layers(a.get('layers', []))
    if n:
        json.dump(d, open(path, 'w'), separators=(',', ':'))
    print('TWITCH keys fixed', n)


if __name__ == '__main__':
    main()
