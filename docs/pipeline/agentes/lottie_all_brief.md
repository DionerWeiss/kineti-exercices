# Brief: generate the 2D Lottie for every exercise job (lotes 01–13)

## Context
Kineti (physiotherapy app) animates ~688 exercise jobs (`tool/mannequin/jobs.json`). The client approved a 2D
Lottie cut-out puppet (the LottieFiles Dinh man, recoloured to Kineti blue) driven per frame by the 3D joints of
our mannequin rig. Two puppets exist, both in the repo (cwd /home/dioner/projects/kineti/animated_exercices):
- side: `tool/puppet2d/drive_puppet.py` (hands open/fist/flat-planted, planted-hand IK, ~100 props, unwrap, despike)
- front: `tool/puppet2d/drive_front.py` + `front_puppet.json` (same CLI, props ported)
- `tool/puppet2d/pick_view.py <joints.json> <action...> [--json]` prints front/side per action
- `tool/puppet2d/gen.sh`, `render.mjs` (lottie-web in headless chromium → mp4), `export_joints.py` (Blender)
- tests already validated: `/mnt/e/mannequin/puppet2d/props30/` (side) and `/mnt/e/mannequin/puppet2d/front/`
Read the docstrings of these files, and the memory note with the client's past feedback (apply the same care:
hands look part of the arm, no blinking, no floating, no skating, shoes flat, props drawn, videos ≥ 10 s):
`/home/dioner/.claude/projects/-home-dioner-projects-kineti-animated-exercices/memory/lottie-puppet-2d.md`.

The 3D move fixes of lotes 01–13 are merged; every move lives as an action in
`E:\mannequin\avatar_man\exercises_final.blend` (action name = the job's move id: jobs.json `move`, default the
job id). A 3D re-render reads that file and lote 14 fixes will be synced into it later, so FIRST copy it to
`E:\mannequin\puppet2d\final\lib_snapshot.blend` and export joints only from the snapshot.

## Goal
One Lottie per job (not per move: jobs sharing a move can differ in props/view) for the jobs of lotes 01–13:
`/mnt/e/mannequin/avatar_man/final/lotes/lote_01.txt` … `lote_13.txt` (50 job ids each). Skip lote_14.txt (its
fixes are pending — a later pass) and jobs with `lib: "hand"` (hand close-ups: list them as not applicable).

1. **Joints.** Export all needed actions from the snapshot with export_joints.py (Windows Blender
   `/mnt/e/tools/blender-5.3.0/blender.exe -b '<win path>' --python '<win path to a copy of export_joints.py on E:>'
   -- '<win path out.json>' <actions...>`; `/mnt/e/x` = `E:\x`). Split into a few json files if huge.
2. **View.** Run pick_view.py; use its answer unless it is clearly wrong for the exercise (e.g. a lateral raise
   seen from the side, a squat from the front) — then override and note it. jobs.json `view` is the 3D camera
   and only a hint.
3. **Flags.** Map jobs.json `props` to `--props=` (check the names each driver supports; `walk` → `--walk`;
   `throw` → skip the prop). Pick `--hands=` as the drivers' auto unless the exercise needs a fist/open hand.
4. **Generate** into `/mnt/e/mannequin/puppet2d/final/` named by JOB id: `<job>.json` (Lottie), `<job>.mp4`,
   `strips/<job>.png`, `qa/<job>.json|log`. Write a small `gen_jobs.sh` (in tool/puppet2d, list lines
   `<job> <action> <view> [flags]`) based on gen.sh. Run up to 3 jobs in parallel (a 3D render shares the CPU);
   measure the time per job first and tell me the ETA in the report.
5. **Automatic QA per job:** blink check
   `uv run -q --no-project --with numpy python3 tool/mannequin/ops/blink.py <mp4s>` → 0;
   the drivers' QA numbers (float, skate, step, turn, FLIPS); flag any job over float 5 px, skate 1.5 px/frame,
   any blink, a render failure, an empty/cropped frame (auto-framing), props missing that jobs.json asks for.
6. **Look** at every flagged job and at 1 in 10 of the rest (ffmpeg frames, Read the PNGs at full size — hands,
   props, contacts) and compare with its PocketPhysio video (`/mnt/e/mannequin/pocketphysio_ref/<id>.mp4`, ids in
   jobs.json `pocketphysio`). Fix driver bugs in tool/puppet2d (keep the approved look) and regenerate.
7. **Deliver** `final/manifest.json` (per job: move, view (+ "override" reason), flags, qa numbers, status ok /
   limitação with reason), a contact sheet per lote `final/sheet_lote_NN.png` (one strip per job with its id), and
   `final/move_bugs.txt` for 3D move bugs you notice (the same joints drive the 3D render; I forward them).

## Rules
- Edit only `tool/puppet2d/`; write outputs only under `/mnt/e/mannequin/puppet2d/`. Do not touch tool/mannequin/,
  jobs.json, the moves files, or anything in E:\mannequin\avatar_man (a 3D render is running there).
- Do not use Gemini or Vertex. Do not change the avatar's look. No global smoothing that loosens contacts.
- Known limits you can list rather than hack: foreshortening when a limb points at the camera, band posts at
  left/right foreshortened, throw-* not drawn.

## Report back
ETA/time per job, counts (ok / limitação / not applicable), front vs side counts and overrides, the flagged jobs
with what you fixed, blink results, driver changes, paths to manifest and sheets, and move_bugs.txt contents.
