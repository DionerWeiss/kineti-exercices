"""Run desk-break's build_library.py on one moves file and also save the .blend
(upstream saves it only for the full library).

    blender -b -P tool/mannequin/build_lib.py -- <desk-break build_library.py> <moves.json> <out_dir>
"""
import os, runpy, sys

import bpy

builder, moves, out = sys.argv[sys.argv.index('--') + 1:][:3]
sys.argv = [sys.argv[0], '--', moves, out]
runpy.run_path(builder, run_name='__main__')
bpy.context.scene.frame_set(1)
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, 'exercises.blend'), compress=True, copy=True)
print('OK saved', os.path.join(out, 'exercises.blend'))
