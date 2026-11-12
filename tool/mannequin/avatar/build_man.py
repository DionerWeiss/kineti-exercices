"""Builds the base of the Kineti low-poly man with MPFB and its Mixamo skeleton: a fit man of about 30 with
blue trainers and nothing else. fit_avatar.py (style "lowpoly") facets the body and makes the shirt, the
shorts and the hair from the body itself. Run inside Blender with the MPFB extension and the MakeHuman CC0
asset pack installed:

    blender -b --python build_man.py -- <out.blend>
"""

import sys

import addon_utils
import bpy

addon_utils.enable('bl_ext.user_default.mpfb', default_set=True)
from bl_ext.user_default.mpfb.services.humanservice import HumanService  # noqa: E402

OUT = sys.argv[sys.argv.index('--') + 1:][0]

for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)

# MakeHuman age: 0.5 is 25 years, 1.0 is 90.
human_info = {
    'name': 'KinetiMan',
    'phenotype': {
        'gender': 1.0, 'age': 0.55, 'muscle': 0.78, 'weight': 0.52, 'proportions': 0.6,
        'height': 0.55, 'cupsize': 0.5, 'firmness': 0.5,
        'race': {'caucasian': 0.8, 'african': 0.1, 'asian': 0.1},
    },
    'rig': 'mixamo',
    'eyes': '', 'eyebrows': '', 'eyelashes': '', 'tongue': '', 'teeth': '', 'hair': '', 'proxy': '',
    'targets': [], 'expressions': [],
    'clothes': ['shoes06.mhclo'],
    'skin_mhmat': 'young_caucasian_male.mhmat', 'skin_material_type': 'MAKESKIN',
    'eyes_material_type': 'MAKESKIN', 'skin_material_settings': {}, 'eyes_material_settings': {},
}
settings = HumanService.get_default_deserialization_settings()
HumanService.deserialize_from_dict(human_info, settings)

rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
print('RIG', rig.name, len(rig.data.bones))
print('OBJECTS', [(o.name, o.type, len(o.data.vertices) if o.type == 'MESH' else 0) for o in bpy.data.objects])
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print('DONE', OUT)
