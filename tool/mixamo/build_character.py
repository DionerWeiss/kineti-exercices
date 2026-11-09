"""Builds the Kineti woman (about 50, Kineti t-shirt, navy trousers, white
trainers) with MPFB and its Mixamo skeleton, so Mixamo animations drive it
directly. Run inside Blender with the MPFB extension and the MakeHuman CC0
asset pack installed:

    blender -b --python build_character.py -- <suit_diffuse.png> <out.blend>
"""

import sys

import addon_utils
import bpy

addon_utils.enable('bl_ext.user_default.mpfb', default_set=True)  # MPFB reads its own preferences while registering
from bl_ext.user_default.mpfb.services.humanservice import HumanService  # noqa: E402

argv = sys.argv[sys.argv.index('--') + 1:]
SUIT, OUT = argv[0], argv[1]

for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)

# MakeHuman age: 0.5 is 25 years, 1.0 is 90; 0.69 is about 50.
human_info = {
    'name': 'Kineti',
    'phenotype': {
        'gender': 0.0, 'age': 0.69, 'muscle': 0.45, 'weight': 0.58, 'proportions': 0.55,
        'height': 0.42, 'cupsize': 0.5, 'firmness': 0.4,
        'race': {'caucasian': 0.55, 'african': 0.25, 'asian': 0.2},
    },
    'rig': 'mixamo',
    'eyes': 'high-poly.mhclo', 'eyebrows': 'eyebrow001.mhclo', 'eyelashes': 'eyelashes01.mhclo',
    'tongue': '', 'teeth': '', 'hair': 'ponytail01.mhclo', 'proxy': '',
    'targets': [], 'expressions': [],
    'clothes': ['female_casualsuit01.mhclo', 'shoes05.mhclo'],
    'skin_mhmat': 'middleage_caucasian_female.mhmat', 'skin_material_type': 'ENHANCED_SSS',
    'eyes_material_type': 'MAKESKIN', 'skin_material_settings': {}, 'eyes_material_settings': {},
}
settings = HumanService.get_default_deserialization_settings()
basemesh = HumanService.deserialize_from_dict(human_info, settings)

# Kineti print on the t-shirt
suit = next(o for o in bpy.data.objects if o.name.endswith('female_casualsuit01'))
img = bpy.data.images.load(SUIT)
for slot in suit.material_slots:
    for node in slot.material.node_tree.nodes:
        if node.type == 'TEX_IMAGE' and node.image and 'diffuse' in node.image.name.lower():
            node.image = img

rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
print('RIG', rig.name, len(rig.data.bones), [b.name for b in rig.data.bones][:12])
print('OBJECTS', [o.name for o in bpy.data.objects])
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print('DONE', OUT)
