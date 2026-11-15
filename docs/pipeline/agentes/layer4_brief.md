You are doing "layer 4" (visual review) of a QA pass over animated exercise videos: a low-poly avatar (blue Kineti
shirt, black shorts) performing physiotherapy exercises, rendered in Blender. Only look and write JSON; do not
edit any other file and do not render.

Batch: the job ids are in /mnt/e/mannequin/avatar_man/final/lotes/lote_NN.txt (space-separated).
Per job J:
- video: /mnt/e/mannequin/avatar_man/out/videos_final/J.mp4 (1920x1080, 30 fps; starts with ~0.5 s still).
- automatic findings: /mnt/e/mannequin/avatar_man/final/review_lote_NN.csv (utf-8-sig CSV, one row per job; columns
  tecnico / problemas_tecnicos (layer 1: pose, contacts, clothes, props, camera), motion_status /
  problemas_movimento (layer 2: pops, jerk, ROM, balance, legibility, rhythm), video_status / problemas_video).
- notes from the engineer who fixed the moves: /mnt/e/mannequin/avatar_man/ops/notes_plan.json
  {J: {"tipo": "corrigido"|"falso positivo"|"verificar"|"pendente", "correcao"|"nota"|"motivo": "..."}} (not every job has one).
Make a contact tile of 8 frames and look at it (Read the PNG):
  ffmpeg -v error -y -i VIDEO -vf "select='not(mod(n\,STEP))',scale=480:-2,tile=4x2" -frames:v 1 OUT.png
  with STEP = max(1, frame_count // 8) (frame_count: ffprobe -v error -select_streams v:0 -count_packets -show_entries stream=nb_read_packets -of csv=p=0 VIDEO).
  Write tiles under /mnt/e/mannequin/avatar_man/ops/l4/.
  When a finding names a frame (e.g. "quadro 135"), also grab that frame (video frame = 15 + action frame - 1) at
  full size and crop around the body part named, to judge it properly.

Which jobs: every job whose row has tecnico, motion_status or video_status different from "ok", plus every 10th job
of the batch file (positions 1, 11, 21, ...) even if all ok. For the others just record visual "ok" with nota "amostra não sorteada; automático ok".

Judging (be concrete, do not nitpick; the low-poly look and plain shading are intended):
- Visible defects that matter: a limb through the body or through a prop/the floor, a hand or foot clearly
  floating above what it should rest on, a foot visibly sliding/skating on the floor, a snap/pop between frames,
  the body cut off by the frame (close-ups framing only the upper body or only the feet are deliberate), the camera
  showing the back when the exercise needs the front, a held prop not in the hand, a pose that is anatomically wrong.
- Many automatic findings are small (skin 1-2 cm through clothes, 2-4 cm self-contact) and invisible at normal size:
  if you cannot see a problem, the visual verdict is "ok".
Verdict per job (JSON):
  {"visual": "ok"|"corrigido"|"pendente", "nota": "<short Portuguese>", "correcao": "...", "motivo": "..."}
  - "ok": nothing visibly wrong (nota: what you checked, e.g. "pele 1,5 cm na coxa não aparece").
  - "corrigido": the engineer's note says tipo corrigido AND the video looks right -> copy its "correcao" text.
  - "pendente": a visible defect remains -> "motivo" says what and where (frame), in Portuguese. If the engineer's note
    says pendente and you can see that defect, keep pendente with that motivo; if you cannot see it, use "ok" and say so.
  - "falso positivo" notes: if the video agrees, visual "ok" with the note's text in "nota".
Output: /mnt/e/mannequin/avatar_man/final/visual_review/lote_NN.json (UTF-8, ensure_ascii=False, indent=1):
  {"<job id>": {...verdict...}, ...} with every job of the batch. Write incrementally every ~10 jobs.
Reply when done with: counts ok / corrigido / pendente, and the list of pendente (job: motivo), under 300 words.
