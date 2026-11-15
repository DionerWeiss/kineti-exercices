You are doing the visual review of a RE-RENDERED batch of animated exercise videos: a low-poly avatar (blue Kineti
shirt, black shorts) performing physiotherapy exercises, rendered in Blender. Earlier review rounds found defects,
an engineer fixed the moves at the source, and these videos are the re-render. Your job: confirm each fix is visible
in the new video and that nothing new broke. Only look and write JSON; do not edit any other file and do not render.

Batch NN (e.g. R01): job ids in /mnt/e/mannequin/avatar_man/final/lotes/lote_NN.txt (whitespace-separated).
Per job J:
- new video: /mnt/e/mannequin/avatar_man/out/videos_final/J.mp4 (1920x1080, 30 fps; starts with ~0.5 s still).
- automatic findings for the new render: /mnt/e/mannequin/avatar_man/final/review_lote_NN.csv (utf-8-sig, one row
  per job; columns tecnico / problemas_tecnicos (pose, contacts, clothes, props, camera), motion_status /
  problemas_movimento (pops, jerk, ROM, balance, rhythm), video_status / problemas_video; the columns final /
  correcao / motivo / nota carry the PREVIOUS round's verdict).
- what the engineer changed: /mnt/e/mannequin/avatar_man/fix/lote_*/report.json, {J: {"status": "corrigido"|"não
  corrigido", "correcao": "...", "motivo": "..."}} — search all lote folders; a job may appear in several (the
  highest-numbered lote is the latest).
- PocketPhysio reference (what the exercise should look like): /mnt/e/mannequin/pocketphysio_ref/<id>.mp4, ids in
  /home/dioner/projects/kineti/animated_exercices/tool/mannequin/jobs.json [J]["pocketphysio"]. Use one when the fix
  is about the movement itself (wrong exercise, wrong ROM, wrong side) to judge it.
- known open issues: /mnt/e/mannequin/avatar_man/ops/pendentes_final.txt (`job: motivo` lines).

Look at EVERY job of the batch (they were all changed). Make a contact tile of 8 frames and Read the PNG:
  ffmpeg -v error -y -i VIDEO -vf "select='not(mod(n\,STEP))',scale=480:-2,tile=4x2" -frames:v 1 OUT.png
  with STEP = max(1, frame_count // 8) (frame_count: ffprobe -v error -select_streams v:0 -count_packets -show_entries stream=nb_read_packets -of csv=p=0 VIDEO).
  Write tiles under /mnt/e/mannequin/avatar_man/ops/l4R/NN/.
  When the fix or a finding is about a contact (hand/forearm/knee/foot on floor, wall, chair, step) or a frame number,
  also grab that frame at full size (video frame = 15 + action frame - 1) and crop around the body part: the
  automatic QA does not catch floating hands/forearms/knees, so judge contact against the shadow and the surface.

Judging (be concrete, do not nitpick; the low-poly look and plain shading are intended):
- Visible defects that matter: a limb through the body, a prop, a wall or the floor; a hand, forearm, knee or foot
  clearly floating above what it should rest on; a foot visibly skating; a snap/pop between frames; the body cut off
  by the frame (close-ups of only the upper body or only the feet are deliberate); the camera showing the back when
  the exercise needs the front; a held prop not in the hand; an anatomically wrong pose; a movement that is not the
  exercise named.
- Small automatic findings (skin 1-2 cm through clothes, 2-4 cm self-contact) are usually invisible: if you cannot
  see it, it is "ok".
Verdict per job:
  {"visual": "ok"|"corrigido"|"pendente", "nota": "<short Portuguese>", "correcao": "...", "motivo": "..."}
  - "corrigido": the report says corrigido AND the new video shows it -> copy its "correcao" text, nota says what you saw.
  - "ok": nothing was asked of this job beyond a re-render, or the fix is cosmetic, and nothing looks wrong.
  - "pendente": the fix is not visible or a visible defect remains/appeared -> "motivo" says what and where (frame),
    in Portuguese. Known open issues from pendentes_final.txt that you can still see stay "pendente" with that motivo.
Output: /mnt/e/mannequin/avatar_man/final/visual_review/lote_NN.json (UTF-8, ensure_ascii=False, indent=1):
  {"<job id>": {...verdict...}, ...} with every job of the batch. Write incrementally every ~10 jobs.
Reply when done with: counts ok / corrigido / pendente, and the list of pendente (job: motivo), under 300 words.
