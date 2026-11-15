# Brief: 2D Lottie puppet, hands + planted hands + assistive props

## Context
The client (a physiotherapy app, Kineti) reviewed 10 exercises rendered as a 2D Lottie cut-out puppet and liked
them. They asked for three things: (1) better hands, (2) no blinking (fixed already, see below), (3) the assistive
devices / props (chair, band, ball, dumbbell, stick, step, walker...) drawn in.

The puppet is the LottieFiles "Split Jump" man by Dinh Bui Xuan (Lottie Simple License), recoloured to Kineti blue,
driven per frame by the 3D joints of our mannequin rig (side view, sagittal projection).

- Generator: `tool/puppet2d/drive_puppet.py` (in the repo, cwd /home/dioner/projects/kineti/animated_exercices).
  Read its docstring and the whole file before editing. Puppet source: `/mnt/e/mannequin/puppet2d/scripts/split-jump-dinh.json`.
- Batch: `tool/puppet2d/gen.sh <joints.json> <out dir> <list file>` (each list line: `<action> [flags]`, e.g.
  `kineti-seated-band-row --props=chair`). Renders `<out>/<action>.json` + `.mp4` + `strips/<action>.png` + `qa/`.
- Joints: `tool/puppet2d/export_joints.py`, run in Blender on a built move library:
  ```
  cd /home/dioner/projects/kineti/animated_exercices
  MANNEQUIN_OUT=<work dir> python3 tool/mannequin/mannequin.py build <move ids>     # -> <work dir>/kineti_sub/exercises.blend (kineti moves) / desk_sub (desk-break moves)
  /mnt/e/tools/blender-5.3.0/blender.exe -b '<win path to exercises.blend>' --python 'E:\...\tool path\export_joints.py' -- '<win path out joints.json>' <action ids...>
  ```
  Blender is the Windows build: give it Windows paths (`/mnt/e/x` = `E:\x`; for repo files use
  `\\wsl.localhost\Ubuntu-24.04\home\dioner\projects\kineti\animated_exercices\...` or copy the script to E: first).
  Job → move id: `tool/mannequin/jobs.json` (`move` field, default the job id; `lib` kineti or deskbreak; `props`;
  `view`). Moves live in `tool/mannequin/kineti_moves.json` and `deskbreak_moves.json` — READ ONLY for you.
- Current 10-exercise set: `/mnt/e/mannequin/puppet2d/compare10/` (joints.json, list.txt, mp4/json, strips/).
- Blink check: `uv run -q --no-project --with numpy python3 tool/mannequin/ops/blink.py <mp4s>` must report 0 blinks.
  (Angle tracks are now unwrapped before keying; keep it that way.)
- Python: `uv run -q --no-project --with numpy python3 -I ...`. Node deps are installed in tool/puppet2d/node_modules.
- To see results, extract frames with ffmpeg and Read the PNGs. Look closely at full-resolution crops of hands
  and props; do not judge from tiny strips only.

## What to do
1. **Hands.** The current open hand is a thin tapered paddle continuing the forearm (see compare10 mini-squat,
   seated-band-row). Redraw it as a readable hand in the same flat Dinh style: rounded palm a bit wider than the
   wrist, fingers as one rounded block with subtle finger separation lines, a visible thumb, joined seamlessly
   to the forearm outline, near/far arm shading kept. Keep the fist variant (`--hands=auto|open|fist`) and
   improve it if it looks off. Hands must look like part of the arm (the client complained about that before).
2. **Planted hands.** When the 3D hand is on a support (floor, box/bench, chair seat, wall, ball, table), the 2D
   hand must lie flat on that support, palm down, fingers forward, wrist bent, with no floating. Today
   kineti-knee-push-up floats ~28 px with the hands in the air and kineti-incline-push-up floats 61 px with the
   bench drawn under the FEET instead of under the hands. Fix both (arm IK to the support line, like the legs).
3. **Props.** Draw the props named in jobs.json `props` (124 distinct names; mirror their meaning and placement
   from `tool/mannequin/render_mannequin.py`, which builds them in 3D). Some already exist in drive_puppet
   (chair, chairfit, stool, chairbehind, support, side, wall, wallback, wallball, step, roll, bed, mat, chairbox,
   pillow, ball) — check they sit right. Priority by frequency: chair 95, band 58 (elastic line between hand(s)/
   foot/ankles and an anchor or the other hand, stretching with the motion), swissseat 26, dumbbell 24, pillow 23,
   side 19, stick 19, step 18, bed 16, table 14, support 13, wall 10, heldball 10, wobble/board/bosu, ball, towel,
   walker, cane, ladder/marks. Flat style, muted greys/blues like the existing chair, no outlines heavier than the
   puppet's. Held objects follow the hand(s) every frame and never pass through the body.
   `walk` and `throw` are not props for you (walk = `--walk`; throw = skip unless trivial).
4. **Validation set.** Build a set of ~30 exercises covering the props above plus the 10 in compare10, generate
   them into `/mnt/e/mannequin/puppet2d/props30/`, check every one visually (hands, props, contacts, blinks), fix,
   and make a contact sheet `props30/sheet.png` (one strip per exercise with its id).

## Rules
- Edit only `tool/puppet2d/` and write outputs only under `/mnt/e/mannequin/puppet2d/`. Do not touch
  tool/mannequin/, jobs.json, the moves files, exercises_final.blend, or E:\mannequin\avatar_man (a 3D render
  batch is running there).
- Do not use Gemini or Vertex. Do not change the avatar's look (face, hair, Kineti blue shirt, shorts, shoes).
- No global smoothing that hides problems by loosening contacts.
- The puppet is side-view only: exercises in the frontal plane (abduction, jumping jacks, side plank) will not
  read; list them as limitations, do not hack them.

## Report back
What changed in drive_puppet.py (hands, planted hands, each prop), the list of props supported vs not, the 30
ids with a one-line verdict each, blink results, and paths to the sheet and videos.
