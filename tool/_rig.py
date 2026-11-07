"""Puts the Kineti Lottie rig on sys.path.

The rig (kineti_lottie, figure3d and the base builders) lives in the app
repository under tool/lottie. By default it is looked up next to this
repository (../kineti_app/tool/lottie); set KINETI_LOTTIE_DIR to override.
"""

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RIG = Path(os.environ.get('KINETI_LOTTIE_DIR', REPO.parent / 'kineti_app' / 'tool' / 'lottie')).resolve()

if not (RIG / 'figure3d.py').exists():
    raise SystemExit(f'Kineti rig not found at {RIG}; set KINETI_LOTTIE_DIR to the app\'s tool/lottie folder.')
for p in (str(Path(__file__).resolve().parent), str(RIG)):
    if p not in sys.path:
        sys.path.insert(0, p)

import figure_style  # noqa: E402,F401  (library figure; inactive until figure_style.use(slug))
