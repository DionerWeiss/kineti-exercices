You are validating animated exercise videos (a low-poly avatar, blue Kineti shirt) against the PocketPhysio
reference videos (real people), the way the client did for a pilot. Only look and write JSON: do not edit any other
file, do not render or run Blender.

The client's pilot feedback shows the standard (this is exactly the kind of note expected):
- "mini-squat: precisa se abaixar um pouco mais, precisa ficar igual do video" (depth)
- "single-leg-bridge: a perna de trás já começa levantada, quando deveria começar esticada no chão. A perna da frente
  também precisa ficar com o pé no chão, não apenas o calcanhar" (start pose, foot contact)
- "knee-push-up: os joelhos devem permanecer fixos no lugar" (a contact that should not move)
- "forward-lunge: chegando com o joelho até o chão e levantando os braços" (depth + arms as in the video)
- "backward-lunge: posição das mãos errada, movimento errado"
- "jumping-jacks: movimento errado e devagar. Juntar os braços no corpo ao fechar as pernas; ao abrir, levantar as
  mãos e juntá-las" (arm path, speed)
- "incline-push-up: está dobrando os joelhos e deslizando um pouco os braços"
- "side-plank: pé encostado no chão, corpo em linha diagonal, igual ao PocketPhysio"
- "seated-band-row: ok 100%"

Batch: job ids in /mnt/e/mannequin/avatar_man/final/lotes/lote_NN.txt (space-separated). Skip jobs whose
pocketphysio list is empty (jobs.json: /home/dioner/projects/kineti/animated_exercices/tool/mannequin/jobs.json)
and jobs listed in SKIP below.
Per job J:
- compare image /mnt/e/mannequin/avatar_man/out/compare/J.png: one row per PocketPhysio id (start / peak / return)
  and a last row "Kineti J" with our frames. Read it.
- our video /mnt/e/mannequin/avatar_man/out/videos_final/J.mp4: make an 8-frame tile and look at it too
  (ffmpeg -v error -y -i VIDEO -vf "select='not(mod(n\,STEP))',scale=480:-2,tile=4x2" -frames:v 1 OUT.png with
  STEP = frame_count // 8; frame_count via ffprobe -v error -select_streams v:0 -count_packets -show_entries
  stream=nb_read_packets -of csv=p=0 VIDEO). Tiles go in /mnt/e/mannequin/avatar_man/ops/val/.
- PocketPhysio texts: /home/dioner/projects/kineti/animated_exercices/research/pocketphysio/exercicios.json (list;
  "id", "nome_pt", "descricao_pt"); load once with python3 and print only what you need.
- If needed, look at more frames of a PocketPhysio video: /mnt/e/mannequin/pocketphysio_ref/<pp id>.mp4.
Pick the PocketPhysio id that best represents the job (usually the closest "igual"), and compare against it:
  1. posição inicial (lying/seated/standing; legs straight or bent; which limb starts where; feet flat),
  2. amplitude / profundidade (how far it goes: knee to floor, squat depth, arm height...),
  3. braços e mãos (where they are and how they move),
  4. contatos (feet flat vs heel only; knees/hands/feet that should stay fixed but slide; a foot that floats),
  5. ritmo (much too slow or too fast for the exercise; very long pauses that the video does not have),
  6. movimento errado (a different movement or a different pattern than the video).
Be concrete and short, in Portuguese, like the client. Only report differences a client would notice; small style
differences (hair, clothes, chair style, bare feet) do not matter.
Output /mnt/e/mannequin/avatar_man/final/validation/lote_NN.json (UTF-8, ensure_ascii=False, indent=1):
{"<job>": {"ref": "<full pp id used>", "verdict": "ok" | "ajustar" | "refazer",
           "issues": [{"tipo": "posição inicial"|"amplitude"|"braços"|"contato"|"ritmo"|"movimento", "nota": "..."}],
           "resumo": "<one line in the client's style>"}, ...}
"ok" = matches the video; "ajustar" = same exercise, specific fixes; "refazer" = the movement is wrong.
Write incrementally every ~10 jobs. Reply with counts ok/ajustar/refazer and the list of "refazer" (job: resumo),
under 300 words.
SKIP: mini-squat kineti-single-leg-bridge kineti-seated-band-row kineti-indoor-walking kineti-knee-push-up
kineti-forward-lunge kineti-backward-lunge kineti-jumping-jacks kineti-incline-push-up kineti-side-plank
