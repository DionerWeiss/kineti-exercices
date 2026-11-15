You are doing "layer 3" of a QA review: comparing our animated exercise videos (a low-poly avatar, Kineti) against
the reference videos of PocketPhysio (real people), id by id. Write the result as JSON. Do not edit any other file
and do not run Blender or renders.

Inputs
- Job ids of this batch: /mnt/e/mannequin/avatar_man/final/lotes/lote_NN.txt (space-separated).
- For each job id J: PocketPhysio ids in /home/dioner/projects/kineti/animated_exercices/tool/mannequin/jobs.json under
  J -> "pocketphysio" (may be empty: skip the job). Skip "lib": "hand" jobs.
- Compare image: /mnt/e/mannequin/avatar_man/out/compare/J.png: one row per PocketPhysio id (title "PocketPhysio
  <last 6 chars> <name> [position] início / pico / retorno", start / peak / return frames) and a last row "Kineti J"
  with our 3 frames. Read it (image). A row may be a placeholder (reference missing): judge that id from text only.
- Catalog: /home/dioner/projects/kineti/animated_exercices/research/pocketphysio/exercicios.json (list; "id",
  "nome_pt", "descricao_pt", "observacoes", "posicao"); load once with python3, print only the entries you need.
- Already judged ids (keep consistency; do not redo them): /mnt/e/mannequin/avatar_man/final/review_pp.json
  ({job: {pp id: {...}}}). Judge only ids missing there, but still list every id of the batch in your output,
  copying the existing judgement for those already present.

Rubric for "pp_match" (per PP id, PP exercise vs OUR movement):
- "igual": same exercise: same body position (standing / chair / floor or bed seated / supine / prone / side /
  kneeling / all fours), same joint(s) moving the same way, similar range. Small differences are fine (hand
  placement, chair style, speed, one side vs alternating, bare feet).
- "próximo": same pattern with a clear variant difference: support or position (bed edge vs chair, feet on floor vs
  leg extended), noticeably different range, arms doing something that matters, a support or prop missing.
- "diferente": a different movement (different joint, plane or exercise): a patient following our video would do a
  different exercise. Use sparingly.
"divergencias": short Portuguese (max ~15 words), "" when igual with nothing notable. "ref": "video" or "texto".
Output: /mnt/e/mannequin/avatar_man/final/pp_review/lote_NN.json (UTF-8, ensure_ascii=False, indent=1):
{"<job id>": {"<full pp id>": {"pp_match": ..., "ref": ..., "divergencias": "...", "corrigido": "-", "acao": "mantido"}, ..., "_visual": ""}, ...}
Every non-hand job of the batch with PP ids, every PP id of each (full 24-char ids). Write incrementally.
Reply: counts igual / próximo / diferente, the "diferente" list (job, pp id, reason), under 250 words.
