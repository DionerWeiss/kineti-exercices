"""Puts the Kineti Lottie rig on sys.path.

The rig (kineti_lottie, figure3d and the base builders) lives in the app
repository under tool/lottie. By default it is looked up next to this
repository (../kineti_app/tool/lottie); set KINETI_LOTTIE_DIR to override.
"""

import importlib.abc
import importlib.machinery
import importlib.util
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RIG = Path(os.environ.get('KINETI_LOTTIE_DIR', REPO.parent / 'kineti_app' / 'tool' / 'lottie')).resolve()


class _RigPycFinder(importlib.abc.MetaPathFinder):
    """Loads a rig module from its cached bytecode when the .py is gone."""

    def find_spec(self, fullname, path, target=None):
        if path is not None or '.' in fullname:
            return None
        source = RIG / f'{fullname}.py'
        cached = Path(importlib.util.cache_from_source(str(source)))
        if source.exists() or not cached.exists():
            return None
        loader = importlib.machinery.SourcelessFileLoader(fullname, str(cached))
        return importlib.util.spec_from_loader(fullname, loader)


if not (RIG / 'figure3d.py').exists() and not Path(importlib.util.cache_from_source(str(RIG / 'figure3d.py'))).exists():
    raise SystemExit(f'Kineti rig not found at {RIG}; set KINETI_LOTTIE_DIR to the app\'s tool/lottie folder.')
sys.meta_path.insert(0, _RigPycFinder())
for p in (str(Path(__file__).resolve().parent), str(RIG)):
    if p not in sys.path:
        sys.path.insert(0, p)

import figure_style  # noqa: E402,F401  (library figure; inactive until figure_style.use(slug))
