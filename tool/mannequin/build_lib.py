"""Run kineti_builder.py (our fork of desk-break's build_library.py, with "ground" height fields) on one moves
file and also save the .blend (upstream saves it only for the full library).

    blender -b -P tool/mannequin/build_lib.py -- <desk-break library dir> <moves.json> <out_dir>
"""
import os, runpy, sys

import bpy

lib, moves, out = sys.argv[sys.argv.index('--') + 1:][:3]
os.environ['DESK_LIB'] = lib                     # mannequin.blend lives there
sys.argv = [sys.argv[0], '--', moves, out]
runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kineti_builder.py'), run_name='__main__')
bpy.context.scene.frame_set(1)
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, 'exercises.blend'), compress=True, copy=True)
print('OK saved', os.path.join(out, 'exercises.blend'))
