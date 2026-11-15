You fix animated exercise moves so they match the PocketPhysio reference videos, following a validation report.
Work ONLY inside your work dir W=/mnt/e/mannequin/avatar_man/fix/lote_NN (create it). Never edit files in the repo
(/home/dioner/projects/kineti/animated_exercices) and never touch /mnt/e/mannequin/avatar_man/exercises_final.blend.

Setup (once):
  mkdir -p $W/out $W/moves && cp /home/dioner/projects/kineti/animated_exercices/tool/mannequin/{kineti_moves,deskbreak_moves}.json $W/moves/
  cp /mnt/e/mannequin/avatar_man/exercises_final.blend $W/lib.blend
Environment for every command (from /home/dioner/projects/kineti/animated_exercices):
  export MANNEQUIN_MOVES_DIR=$W/moves MANNEQUIN_OUT=$W/out MANNEQUIN_AVATAR=$W/lib.blend MANNEQUIN_RES=1920x1080
  build+sync a move:  python3 tool/mannequin/mannequin.py build <move ids> && python3 tool/mannequin/mannequin.py sync <move ids>
  QA a job:           python3 tool/mannequin/mannequin.py qa <job ids> 2>&1 | grep "^  QA "   (layer 1, pose)
                      (cd tool/mannequin && uv run -q --no-project --with numpy python3 motion_review.py $W/out/qa <job ids>)   (layer 2)
  stills:             SHEET_FRACS=0,0.25,0.5 SHEET_NAME=fix python3 tool/mannequin/mannequin.py sheet <job ids>  -> $W/out/fix_01.png
                      (delete $W/out/stills/<job> first, or old frames stay)
  joint positions:    uv run -q --no-project --with numpy python3 - (load $W/out/qa/<job>.motion.npz: arrays 'track' (names:
                      hips spine neck armL elbowL handL armR elbowR handR legL kneeL footL legR kneeR footR toeL toeR fingL fingR
                      headtop) and 'pts' [frame, point, xyz] in metres; z up, the figure faces -y, +x is its left).
A job's move: jobs.json[job]["move"] if present, else the job id. Moves live in $W/moves/kineti_moves.json (ids
"kineti-...") or deskbreak_moves.json (desk-break ids). Keep each file's format: json.dumps(doc, ensure_ascii=False,
indent=1), no trailing newline.

Move format: {"id", "beat" (s per key transition), "keys": [{bone: [x, y, z] degrees, ...}, ...]}; a key may have
"hold" (s held at it), "pos" [x, y, z] pelvis offset (x = figure's left, z > 0 forward, z < 0 backward), "touch"
(contacts to solve, e.g. "foot", "footL:leg", "hand:arm"), "lift" (m above the floor, jumps). Bones: hips spine neck
arm/armL/armR elbow hand leg/legL/legR knee foot (no suffix = both sides). Keys loop (last -> first) unless "once".
Sign conventions: leg x < 0 hip flexion, x > 0 extension, z > 0 abduction, y = rotation about the thigh (45 = feet
turned out); knee x > 0 bends; foot x < 0 toes up, x > 0 toes down (tiptoe ~35-50); arm x < 0 raises the arm forward
(-90 horizontal in front when upright; the arm is relative to the trunk, so a forward lean changes it), arm z > 0
raises it sideways (90 = T, 180 overhead, ~200 hands together overhead); elbow x < 0 bends; hand x > 0 flexes;
spine x > 0 bends forward, z = side bend, y = twist; hips [-90,0,0] lying on the back, hips [0,-70,0] = turned, hips
[-59,90,0] = side plank on the left side (less negative x raises the head).
The builder grounds every key (the lowest point touches the floor) and keeps planted feet/hands where they landed
(IK), so a key that moves a planted contact makes it slide or the knee bend.
Tricks that worked on the pilot:
- a foot that must leave the floor without scraping: add a key with hip flexion p and knee ~2p (e.g. leg -25,
  knee 55) before moving it, and the same key on the way back.
- a contact that must stay fixed while the body rotates (knees in a knee push-up, toes in an incline push-up): add
  "pos" to the key so the pelvis moves along the arc around that contact (e.g. +0.06 to +0.08 forward), and set the
  pelvis pitch so straight legs point at the planted foot.
- deep lunge (knee to the floor): front leg [-92,0,0] knee 106 foot -8; back leg [10,0,0] knee 98 foot 50.
- arms raised in front with elbows bent: arm [-95,0,10], elbow [-95,0,0]; arms forward horizontal in a squat with
  the trunk leaning ~30: arm [-118,0,6].
- feet flat on the floor in a supine bent knee: foot ~ [25,0,0] with leg -45 knee 95 (check toe z ~ ankle z).
Validate each fix with numbers (joint positions) and QA, then look at stills. A fix is done when it matches the
validation note and QA layer 1 has no "quebrado" it did not have before (compare against $W/out/qa before you edit:
run QA once on all the batch's jobs first and keep a copy). Max ~4 tries per job; if it does not work, revert that
move and report why.

Input: the validation report /mnt/e/mannequin/avatar_man/final/validation/lote_NN.json ({job: {ref, verdict, issues,
resumo}}); fix the jobs with verdict "ajustar" or "refazer". PocketPhysio frames: compare images
/mnt/e/mannequin/avatar_man/out/compare/<job>.png and videos /mnt/e/mannequin/pocketphysio_ref/<pp id>.mp4.
Output: $W/report.json {job: {"move": id, "status": "corrigido" | "não corrigido", "correcao": "<Portuguese, short,
what changed>", "motivo": "<if not fixed>", "qa_before": "...", "qa_after": "...", "still": "<png path>"}} and the
edited $W/moves/*.json. Reply with the count fixed / not fixed and the list of changed move ids, under 250 words.
