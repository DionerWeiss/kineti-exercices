#!/usr/bin/env python3
"""Recolour Dinh tank tops to Kineti blue. Motion, layers and timing stay as-is.

Each source file uses its own tank hexes. Only those clothing fills are remapped.
Skin, shorts, shoes and props are left alone. If a listed source hex is missing,
or remains after the pass, the file is refused.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"

PRIMARY = "#2563EB"
SHADOW = "#1E40AF"

# Clothing fills only (ao / than / bra / yem nguc). Discovered per file.
MAPS: dict[str, dict[str, str]] = {
    # lote 1
    "cobra": {
        "#DB0000": PRIMARY,
    },
    "forearm_stretch": {
        "#44885F": PRIMARY,
        "#53A270": SHADOW,
    },
    "reverse_crunches": {
        "#D66228": PRIMARY,
        "#B43C26": SHADOW,
    },
    "shoulder_stretch": {
        "#D66228": PRIMARY,
        "#C95728": PRIMARY,
        "#B43C26": SHADOW,
    },
    "squat_reach": {
        "#D66228": PRIMARY,
    },
    "step_up_on_chair": {
        "#EB5750": PRIMARY,
        "#F81A48": PRIMARY,
        "#F73260": SHADOW,
        "#E80000": SHADOW,
    },
    # lote 2
    "walking_hip_opener": {
        "#F07561": PRIMARY,
        "#D95E52": SHADOW,
    },
    "split_jump": {
        "#E96A2A": PRIMARY,
        "#CC5E28": SHADOW,
    },
    "t_plank": {
        "#E96A2A": PRIMARY,
        "#CC5E28": SHADOW,
    },
    "burpee_and_jump": {
        "#E96A2A": PRIMARY,
        "#CC5E28": SHADOW,
    },
    "press_up_toe_tap": {
        "#EE7561": PRIMARY,
        "#F07561": PRIMARY,
    },
    "box_jump": {
        "#F07561": PRIMARY,
    },
    "clean_and_press": {
        "#F07561": PRIMARY,
        "#D95E52": SHADOW,
    },
    "military_push_ups": {
        "#D66228": PRIMARY,
    },
    "squat_kicks": {
        "#D66428": PRIMARY,
        "#B43C26": SHADOW,
    },
    "staggered_push_ups": {
        "#D66228": PRIMARY,
    },
    "punches": {
        "#D66228": PRIMARY,
    },
    "wide_arm_push_up": {
        "#D66228": PRIMARY,
    },
    "jumping_squats": {
        "#D66228": PRIMARY,
    },
    "frog_press": {
        "#DB0000": PRIMARY,
        "#AF0000": SHADOW,
    },
    "seated_abs_circles": {
        "#D66228": PRIMARY,
    },
    "inchworm": {
        "#D66428": PRIMARY,
    },
    "jumping_jack": {
        "#D66227": PRIMARY,
        "#C95728": PRIMARY,
        "#B43D26": SHADOW,
    },
    "lunge": {
        "#E80000": PRIMARY,
    },
}


def hex_of(rgb: list[float]) -> str:
    return "#%02X%02X%02X" % tuple(round(float(v) * 255) for v in rgb[:3])


def from_hex(h: str) -> list[float]:
    h = h.lstrip("#")
    return [int(h[i : i + 2], 16) / 255 for i in (0, 2, 4)]


def collect_solid_hexes(o, out: set[str]) -> None:
    if isinstance(o, dict):
        if o.get("ty") in ("fl", "st"):
            k = o.get("c", {}).get("k")
            if isinstance(k, list) and k and isinstance(k[0], (int, float)):
                out.add(hex_of(k))
            elif isinstance(k, list) and k and isinstance(k[0], dict):
                for kf in k:
                    for key in ("s", "e"):
                        v = kf.get(key)
                        if isinstance(v, list) and v and isinstance(v[0], (int, float)):
                            out.add(hex_of(v))
        for v in o.values():
            collect_solid_hexes(v, out)
    elif isinstance(o, list):
        for v in o:
            collect_solid_hexes(v, out)


def recolor_node(o, mapping: dict[str, str], hits: dict[str, int]) -> None:
    if isinstance(o, dict):
        if o.get("ty") in ("fl", "st"):
            c = o.get("c")
            if isinstance(c, dict) and "k" in c:
                k = c["k"]
                if isinstance(k, list) and k and isinstance(k[0], (int, float)):
                    hx = hex_of(k)
                    if hx in mapping:
                        alpha = k[3:] if len(k) > 3 else [1]
                        c["k"] = from_hex(mapping[hx]) + alpha
                        hits[hx] = hits.get(hx, 0) + 1
                elif isinstance(k, list) and k and isinstance(k[0], dict):
                    for kf in k:
                        for key in ("s", "e"):
                            v = kf.get(key)
                            if isinstance(v, list) and v and isinstance(v[0], (int, float)):
                                hx = hex_of(v)
                                if hx in mapping:
                                    alpha = v[3:] if len(v) > 3 else [1]
                                    kf[key] = from_hex(mapping[hx]) + alpha
                                    hits[hx] = hits.get(hx, 0) + 1
        for v in o.values():
            recolor_node(v, mapping, hits)
    elif isinstance(o, list):
        for v in o:
            recolor_node(v, mapping, hits)


def main() -> int:
    errors = 0
    for slug, mapping in MAPS.items():
        src = SRC / f"{slug}.json"
        if not src.exists():
            print(f"MISSING {src}", file=sys.stderr)
            errors += 1
            continue
        data = json.loads(src.read_text())
        present: set[str] = set()
        collect_solid_hexes(data, present)
        missing = sorted(h for h in mapping if h not in present)
        if missing:
            print(f"REFUSE {slug}: mapped hexes not in file: {missing}", file=sys.stderr)
            print(f"  present sample: {sorted(present)[:30]}", file=sys.stderr)
            errors += 1
            continue
        hits: dict[str, int] = {}
        recolor_node(data, mapping, hits)
        after: set[str] = set()
        collect_solid_hexes(data, after)
        leftover = sorted(h for h in mapping if h in after)
        if leftover:
            print(f"REFUSE {slug}: source hexes still present after recolour: {leftover}", file=sys.stderr)
            errors += 1
            continue
        out = ROOT / f"{slug}.json"
        out.write_text(json.dumps(data, separators=(",", ":")))
        print(f"OK {slug} -> {out.name} hits={hits}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
