"""Runs fit_avatar.py with style "vector" (vector.py) in place of lowpoly.py, without touching fit_avatar.py:

    blender -b <lib exercises.blend> --python vector_fit.py -- kineti_man_mixamo.blend <out.blend>
"""
import os
import runpy
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lowpoly  # noqa: E402,F401  (vector.py imports it by name)
import vector  # noqa: E402

sys.modules['lowpoly'] = vector  # fit_avatar.py's "import lowpoly" now gets the vector style
i = sys.argv.index('--')
sys.argv = sys.argv[:i + 1] + sys.argv[i + 1:i + 3] + ['lowpoly']
runpy.run_path(os.path.join(HERE, 'fit_avatar.py'), run_name='__main__')
