"""Builds every animation listed in catalog.json into its folder.

    python3 tool/build_catalog.py              # build all
    python3 tool/build_catalog.py bridge ...   # build some slugs
    python3 tool/build_catalog.py --check      # rebuild in memory and compare

Exercises go to exercises/<area>/<slug>.json, clinical tests to
clinical_tests/<slug>.json. Each slug is produced by the first module in
SOURCES whose SCENES has it; slugs in EXTERNAL come from app builders that
have no SCENES registry and are kept as committed.

--check also validates the catalogue: every entry has a source and a file,
no JSON is orphaned, every loop is 5 to 8 s (exercises), every scene
passes its geometric checks and every styled slug exists.

Exercises are drawn with the library figure (figure_style.py); the clinical
test references keep the rig's own figure, to match the app.
"""

import importlib
import json
import sys
from pathlib import Path

import _rig  # noqa: F401  (rig on sys.path)
import figure_style

REPO = _rig.REPO
SOURCES = [
    # this repository
    'build_library_pilot_animations',
    'build_library_seated_animations',
    'build_library_standing_animations',
    'build_library_supine_animations',
    'build_library_props_animations',
    'build_library_floor_animations',
    'build_library_hand_animations',
    'build_library_bed_animations',
    # app repository (tool/lottie)
    'build_home_exercise_animations',
    'build_hip_exercise_animations',
    'build_clinical_test_animations',
]
EXTERNAL = set()  # slugs kept as committed files, with no builder here


def targets():
    cat = json.loads((REPO / 'catalog.json').read_text(encoding='utf-8'))
    out = {e['slug']: REPO / 'exercises' / e['area'] / f"{e['slug']}.json" for e in cat['exercises']}
    for r in cat['references']:
        out[Path(r['file']).stem] = REPO / r['file']
    return cat, out


def scenes():
    found = {}
    for name in SOURCES:
        try:
            mod = importlib.import_module(name)
        except ModuleNotFoundError as e:
            if e.name == name:
                continue  # builder not written yet
            raise
        for slug, fn in getattr(mod, 'SCENES', {}).items():
            found.setdefault(slug, (name, fn))
    return found


def build(fn):
    from figure3d import IK_ERRORS
    from kineti_lottie import GEOMETRY_WARNINGS
    GEOMETRY_WARNINGS.clear()
    IK_ERRORS.clear()
    scene = fn()
    return scene.to_json() if hasattr(scene, 'to_json') else scene


def canonical(data):
    return json.dumps(json.loads(json.dumps(data)), sort_keys=True)


def main(args):
    check = '--check' in args
    slugs = [a for a in args if not a.startswith('--')]
    cat, paths = targets()
    found = scenes()
    problems = []
    wanted = slugs or list(paths)
    for slug in wanted:
        if slug not in paths:
            problems.append(f'{slug}: not in catalog.json')
            continue
        path = paths[slug]
        if slug in EXTERNAL:
            if not path.exists():
                problems.append(f'{slug}: external file missing at {path.relative_to(REPO)}')
            continue
        if slug not in found:
            problems.append(f'{slug}: no builder has this scene')
            continue
        module, fn = found[slug]
        is_exercise = path.parts[-3] == 'exercises'
        try:
            with figure_style.style(slug if is_exercise else None):  # references keep the app's figure
                data = build(fn)
        except AssertionError as e:
            problems.append(f'{slug}: geometric check failed: {e}')
            continue
        seconds = data['op'] / data['fr']
        if is_exercise and not 5.0 <= seconds <= 8.05:
            problems.append(f'{slug}: loop {seconds:.1f}s outside 5-8 s')
        if check:
            if not path.exists():
                problems.append(f'{slug}: file missing')
            elif canonical(data) != canonical(json.loads(path.read_text(encoding='utf-8'))):
                problems.append(f'{slug}: committed JSON differs from {module}')
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as fh:
                json.dump(data, fh, separators=(',', ':'), ensure_ascii=False)
            print(f'{str(path.relative_to(REPO)):58s} {seconds:4.1f}s {path.stat().st_size / 1024:6.1f} KB')
    if check and not slugs:
        problems += [f'{s}: in figure_style.STYLE but not in catalog.json' for s in figure_style.STYLE if s not in paths]
        known = set(paths.values())
        for f in sorted(list(REPO.glob('exercises/*/*.json')) + list(REPO.glob('clinical_tests/*.json'))):
            if f not in known:
                problems.append(f'orphan file: {f.relative_to(REPO)}')
        areas = {a['id'] for a in cat['areas']}
        problems += [f"{e['slug']}: unknown area {e['area']}" for e in cat['exercises'] if e['area'] not in areas]
        dupes = {e['slug'] for e in cat['exercises'] if [x['slug'] for x in cat['exercises']].count(e['slug']) > 1}
        problems += [f'{s}: duplicated in catalog' for s in sorted(dupes)]
    for p in problems:
        print('FAIL', p)
    if check and not problems:
        print(f'OK: {len(wanted)} entries match their builders')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
