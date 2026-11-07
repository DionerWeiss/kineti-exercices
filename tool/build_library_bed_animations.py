"""Bed mobility on the 3D rig: rolling and lying-to-sitting.

These replace the app's bed-mobility animations, which have their own 2D
figure, so the two transfers use the same figure as the rest of the library.

Built by tool/build_catalog.py (see its docstring).

The rig turns the body with pitch, roll and yaw; getting up from side-lying
to sitting on the edge of the bed is a turn about the chest axis that those
cannot express, so this module adds `lean`: a rotation of the whole body
about world Z (the chest axis when lying on the near side), applied after the
rig's own frames. Poses without `lean` are untouched.
"""

import _rig  # noqa: F401  (puts the Kineti rig on sys.path)

import figure3d
from build_home_exercise_animations import BED_TOP, bed3d, chain, markers, scene3d, supine_in_bed
from figure3d import (IK_ERRORS, Camera, add_figure, arm_fk, check as check3d, floor_patch, geometry, leg_fk,
                      rotate, with_body)
from kineti_lottie import HIP_Z, W_ARM, W_LEG, Track

# ------------------------------------------------------------------ lean
_rig_frames = figure3d.frames


def _frames(p):
    pelvis, thorax = _rig_frames(p)
    lean = p.get('lean', 0.0)
    if not lean:
        return pelvis, thorax
    z = (0.0, 0.0, 1.0)
    return tuple(tuple(rotate(v, z, lean) for v in basis) for basis in (pelvis, thorax))


figure3d.frames = _frames

# ------------------------------------------------------------------ bed and poses
EDGE_Z = 0.42                     # near edge of the mattress (bed3d)
BED_X = (-0.96, 1.18)             # mattress length, head towards -X
SIDE_Y = BED_TOP + W_LEG / 2 + HIP_Z  # pelvis lying on the near side: lower thigh on the mattress
SIT_Y = BED_TOP + 0.095           # pelvis sitting on the edge (same height over the seat as the chair poses)
# Above and to the side of the foot end: the turns towards the viewer (top knee
# forward, legs over the edge) read as depth instead of vanishing.
CAM = Camera(yaw=35, pitch=38)


def supine(**changes):
    """Lying on the back, head on the pillow, arms along the body."""
    p = with_body(supine_in_bed(plantar=8), lean=0.0,
                  arms={'near': arm_fk(-4, 0, abd=12), 'far': arm_fk(-4, 0, abd=12)})
    return with_body(p, **changes)


def side(**changes):
    """Lying on the near side, facing the near edge of the bed (+Z)."""
    p = with_body(supine(), pelvis=(0.0, SIDE_Y, -0.02), roll=-90, twist=-22, nod=0)
    return with_body(p, **changes)


def bed_scene(title, cam, tr):
    extra = [(x, y, z) for x in BED_X for y in (0.0, BED_TOP) for z in (-EDGE_Z, EDGE_Z)]
    s = scene3d(title, cam, tr, extra)
    floor_patch(s, cam, -1.15, 1.4, -0.75, 0.95)
    bed3d(s, cam)
    return s


def on_the_bed(samples, slack=0.02):
    """Nothing sinks into the mattress: limb and torso centrelines over the
    bed stay at least their half-width above its top (less a couple of
    centimetres of give). Lying on the side, the lower shoulder presses into
    the mattress, so arms are checked from a third of the upper arm on, and
    an arm lying under the head may press 1.5 cm deeper than the legs."""
    for fr, g in samples:
        parts = [(g['torso'], 0.09, 0)]
        for sd in ('near', 'far'):
            parts += [(g[f'{sd} leg'], W_LEG / 2, 0), (g[f'{sd} arm'], W_ARM / 2 - 0.015, 3), (g[f'{sd} foot'], 0.03, 0)]
        for pts, half, skip in parts:
            for n, (a, b) in enumerate(zip(pts, pts[1:])):
                for i in range(skip if n == 0 else 0, 9):
                    x, y, z = (a[k] + (b[k] - a[k]) * i / 8 for k in range(3))
                    if BED_X[0] < x < BED_X[1] and abs(z) < EDGE_Z:
                        assert y - half > BED_TOP - slack, ('into the mattress', fr, round(y - half, 3))


# ------------------------------------------------------------------ rolling
# The lower arm slides up beside the head along the bed (abduction), so it ends
# under the head once on the side.
OVERHEAD = arm_fk(0, 0, abd=174)


def bed_rolling():
    """Lying on the back. The far knee bends, the near arm goes up beside the
    head and the far arm reaches across; head and chest lead the roll onto the
    near side, the pelvis follows. Slowly back to the start."""
    rest = supine()
    ready = with_body(rest, legs={'far': leg_fk(hip=48, knee=92, plantar=12)},
                      arms={'near': OVERHEAD, 'far': arm_fk(82, 30, abd=-24)})  # reaching across, elbow nearly straight
    mid = with_body(ready, pelvis=(0.0, 0.58, 0.02), roll=-42, twist=-26, nod=6,
                    legs={'near': leg_fk(hip=6, knee=10, plantar=10), 'far': leg_fk(hip=50, knee=88, plantar=12, abd=-6)},
                    arms={'near': arm_fk(0, 0, abd=184), 'far': arm_fk(88, 40, abd=-26)})
    lying = with_body(side(pelvis=(0.0, SIDE_Y, 0.06), twist=-34),
                      legs={'near': leg_fk(hip=18, knee=28, plantar=10), 'far': leg_fk(hip=46, knee=70, plantar=10, abd=-12)},
                      arms={'near': arm_fk(0, 0, abd=186), 'far': arm_fk(15, 130, abd=-8)})  # top hand on the bed
    tr = Track()
    t = chain(tr, [(rest, 0.5), (ready, 0.8), (mid, 0.6), (lying, 0.8), (lying, 0.9), (mid, 0.8), (ready, 0.7),
                   (rest, 0.9), (rest, 0.6)])
    t = [t[0], t[1], t[2], t[4], t[5], t[7], t[8], t[9]]  # mid is part of the roll, both ways
    cam = CAM
    s = bed_scene('Rolar na cama', cam, tr)
    samples = add_figure(s, cam, tr, front=('near', 'far'), shadow=False)
    markers(s, ['start', 'bend_knee', 'roll_to_side', 'side_lying', 'return_to_back', 'extend_knee', 'rest'], t)
    check3d(s, cam, tr, samples, floor=False)
    on_the_bed(samples)
    return s


# ------------------------------------------------------------------ lying to sitting
def lying_to_sitting():
    """Rolls onto the near side with the knees bent, brings the knees to the
    edge, pushes up on the elbow and the far hand while the legs come down
    off the bed, and sits on the edge with the feet on the floor. Lies back
    down the same way."""
    rest = supine()
    knees = leg_fk(hip=48, knee=92, plantar=12)
    hook = with_body(rest, legs={'near': knees, 'far': knees})
    # On the side, curled, the forearm of the lower arm and the upper hand on the bed in front.
    curl = leg_fk(hip=72, knee=95, plantar=8)
    curled = side(pelvis=(0.0, SIDE_Y, -0.1), twist=-34, legs={'near': curl, 'far': curl},
                  arms={'near': arm_fk(45, 135, abd=-28), 'far': arm_fk(15, 110, abd=-4)})
    # Knees slide past the edge, shins still level: nothing dips into the mattress before the trunk turns up.
    # Hip and knee bent alike keep the shins parallel to the edge, so they swing down outside it.
    level = leg_fk(hip=80, knee=80, plantar=6)
    slide = with_body(curled, pelvis=(0.0, SIDE_Y, 0.06), legs={'near': level, 'far': level},
                      arms={'near': arm_fk(40, 140, abd=-24), 'far': arm_fk(5, 100, abd=-8)})
    # Halfway up: pushing on both hands while the lower legs swing down.
    rising = with_body(curled, pelvis=(0.0, (SIDE_Y + SIT_Y) / 2 + 0.015, 0.06), lean=-45, twist=-17,
                       legs={'near': leg_fk(hip=86, knee=86, plantar=3), 'far': leg_fk(hip=86, knee=86, plantar=3)},
                       arms={'near': arm_fk(-15, 100, abd=12), 'far': arm_fk(30, 20, abd=-12)})
    seated = with_body(curled, pelvis=(0.0, SIT_Y, 0.06), lean=-90, twist=0,
                       legs={'near': leg_fk(hip=90, knee=90, plantar=0, abd=3), 'far': leg_fk(hip=90, knee=90, plantar=0, abd=3)},
                       arms={'near': arm_fk(-30, 30, abd=20), 'far': arm_fk(-30, 30, abd=20)})  # hands beside the hips
    tr = Track()
    t = chain(tr, [(rest, 0.5), (hook, 0.6), (curled, 1.0), (slide, 0.5), (rising, 0.5), (seated, 0.6),
                   (seated, 0.8), (rising, 0.6), (slide, 0.5), (curled, 0.5), (hook, 0.9), (rest, 0.6), (rest, 0.4)])
    t = t[:5] + t[6:8] + t[9:]  # rising is the middle of sit_up and of lower_trunk
    cam = CAM
    s = bed_scene('Passar de deitado para sentado', cam, tr)
    samples = add_figure(s, cam, tr, front=('near', 'far'), shadow=False)
    markers(s, ['start', 'bend_knee', 'roll_to_side', 'legs_off_edge', 'sit_up', 'seated_feet_supported',
                'lower_trunk', 'legs_on_bed', 'roll_to_back', 'extend_knee', 'rest'], t)
    check3d(s, cam, tr, samples, floor=True)
    on_the_bed(samples)
    g = geometry(seated)
    for sd in ('near', 'far'):  # sitting: feet on the floor, past the edge
        heel, toe = g[f'{sd} foot']
        assert min(heel[1], toe[1]) < 0.05, ('foot not on the floor', sd)
        assert g[f'{sd} leg'][2][2] > EDGE_Z + W_LEG / 2, ('shin against the mattress', sd)
    assert not IK_ERRORS
    return s


SCENES = {
    'bed_rolling': bed_rolling,
    'lying_to_sitting': lying_to_sitting,
}
