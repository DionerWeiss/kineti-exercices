# Brief: front-view 2D Lottie puppet driven by the mannequin rig

## Context
Kineti (physiotherapy app) animates ~688 exercises. The client approved a 2D Lottie cut-out puppet seen from
the SIDE: the LottieFiles "Split Jump" man by Dinh Bui Xuan (Lottie Simple License), recoloured to Kineti blue
and driven per frame by our 3D mannequin joints projected on the sagittal plane. Side view cannot show
frontal-plane exercises (shoulder/hip abduction, jumping jacks, side bends, lateral raises, side steps). The
client asked for a FRONT-view animation too.

Read first:
- `tool/puppet2d/drive_puppet.py` (side puppet generator; read the whole file: FK/IK legs and arms, contact
  anchoring, shoe/floor handling, smoothing, auto-framing, QA output, angle unwrap). Another agent is editing it
  right now (hands + props): do NOT edit it. Copy what you need into your own file.
- `tool/puppet2d/gen.sh`, `tool/puppet2d/render.mjs`, `tool/puppet2d/export_joints.py`.
- Memory notes on past client feedback for the side puppet (apply the same care):
  `/home/dioner/.claude/projects/-home-dioner-projects-kineti-animated-exercices/memory/lottie-puppet-2d.md`.
- Front-facing Dinh men exist: `examples/dinh/src/jumping_jack.json` (precomp with torso, upper arms
  "Pre-comp 16", forearms, hands; legs comp with thigh "Đùi", shoe "Giầy", shin "Chân") and
  `examples/dinh/src/shoulder_stretch.json` (arms split into shoulder cap, upper arm, forearm, hand, fingers,
  thumb). They are a different-looking character (brown hair, orange top, lighter skin) from the side puppet
  (`/mnt/e/mannequin/puppet2d/scripts/split-jump-dinh.json`: grey hair, Kineti-blue tank, black shorts, dark
  shoes with orange sole line).

## Goal
`tool/puppet2d/drive_front.py`: same CLI as drive_puppet.py (`<puppet.json> <joints.json> <action> <out.json>
--kineti [--hands=...] [--walk]`), producing a front-view Lottie of the same exercise.
1. **Puppet.** Pick the best front Dinh rig (jumping_jack or shoulder_stretch, or combine) and restyle it so it
   reads as the SAME man as the side puppet: Kineti blue tank top (same blues as drive_puppet --kineti), grey
   hair matching the side puppet, the side puppet's skin tones, black shorts, dark shoes with the orange sole
   line, similar proportions/height. Compare stills of both puppets next to each other and iterate until they
   match. Hands must look like part of the arm.
2. **Driving.** Project the 3D joints on the frontal plane (screen x = figure's left/right, y = height), set
   each piece's rotation from its 3D segment, legs FK in the air blended to IK near the floor, planted feet
   anchored (no skating), body height following the 3D hips, ground from shoes (and hands when planted),
   unwrap all angle tracks (no blink), auto-framing, QA json like drive_puppet.
   Foreshortening: a segment pointing at the camera (e.g. arm raised forward) gets shorter in projection;
   handle it (scale the piece along its length, or clamp) so it doesn't look broken.
3. **Choosing the view.** Write `tool/puppet2d/pick_view.py <joints.json> <action...>`: for each action, measure
   how much the moving limbs travel in the frontal plane vs the sagittal plane (relative to the pelvis) and
   print `front` or `side`. Check it on: kineti-jumping-jacks, kineti-side-plank (lying on the side: front view
   of the body = side-lying seen from the front), standing hip abduction, shoulder abduction, lateral raise,
   side step, side bend → front; squat, lunge, bridge, push-up, march → side.
4. **Test set** in `/mnt/e/mannequin/puppet2d/front/`: build joints for ~15 frontal-plane exercises (pick from
   tool/mannequin/jobs.json; jobs with view front/front3q are candidates), generate them, look at every one
   (extract frames with ffmpeg, Read the PNGs at full size), compare each with its PocketPhysio reference video
   (`/mnt/e/mannequin/pocketphysio_ref/<pocketphysio id>.mp4`, ids in jobs.json `pocketphysio`), fix, and make
   `front/sheet.png` (one strip per exercise with id) plus `front/side_by_side.png` showing one still of the
   side puppet and the front puppet together.

How to get joints: `MANNEQUIN_OUT=<work dir> python3 tool/mannequin/mannequin.py build <move ids>` then run
`export_joints.py` in the Windows Blender (`/mnt/e/tools/blender-5.3.0/blender.exe -b '<E:\...\exercises.blend>'
--python '<E:\...\export_joints.py>' -- '<E:\...\joints.json>' <ids>`; give Blender Windows paths, copy the
script to E: if needed). Kineti moves build into `<work dir>/kineti_sub/exercises.blend`, desk-break moves into
`desk_sub`. The 10-exercise joints at `/mnt/e/mannequin/puppet2d/compare10/joints.json` include jumping jacks
and side plank. Python: `uv run -q --no-project --with numpy python3 -I ...`. Blink check:
`uv run -q --no-project --with numpy python3 tool/mannequin/ops/blink.py <mp4s>` → 0.

## Rules
- Create only new files in `tool/puppet2d/` (drive_front.py, pick_view.py, assets you derive); outputs only under
  `/mnt/e/mannequin/puppet2d/front/`. Don't edit drive_puppet.py, tool/mannequin/, jobs.json, moves files, or
  anything in E:\mannequin\avatar_man (a 3D render is running).
- No Gemini/Vertex. No global smoothing that loosens contacts. Props are out of scope for now (another agent
  is adding them to the side puppet; keep the prop hook structure similar so they can be ported).

## Report back
Which rig you used and how you restyled it, how foreshortening is handled, pick_view rules and its results,
the ~15 ids with a one-line verdict each vs PocketPhysio, blink results, paths to sheets/videos, and limitations.
