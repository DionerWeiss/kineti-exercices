# Client notes round (lote 01 review by the client)

Follow docs/pipeline/agentes/fix_brief.md
(setup, environment, move format, sign conventions, QA, stills, report.json format) with your NN and these changes.

INPUT (replaces the brief's "Input" section): the CLIENT's own notes, in Portuguese, file
/mnt/e/mannequin/avatar_man/ops/user_notes_l01.csv
(`id;nota`). Fix only the jobs of YOUR group (listed in your prompt). The client asked: "avalie e aplique a todos os
exercícios que fizerem sentido" — so for each note, also find the sibling jobs in tool/mannequin/jobs.json /
catalog.json with the same issue (same move family, same props, same kind of movement) and apply the same change
where it makes sense; list every sibling you changed or deliberately left alone (and why) in report.json under the
key "_siblings" ({job: "what/why"}). Only touch siblings within your group's theme; if a sibling belongs to another
theme, name it in your reply instead.

These are the client's words: they win over earlier reviewers' notes. When the note says "igual ao pocketphysio" /
"não está igual", the PocketPhysio VIDEO is the truth (/mnt/e/mannequin/pocketphysio_ref/<id>.mp4, ids in
jobs.json[job]["pocketphysio"]): watch it (ffmpeg frames, Read the PNGs) and match pose, ROM, side, rhythm.
Current videos: /mnt/e/mannequin/avatar_man/out/videos_final/<job>.mp4. Earlier fix notes:
/mnt/e/mannequin/avatar_man/fix/lote_*/report.json (search all; lote_R2a/R2b/R2c are the newest; don't repeat a
failed approach; lift-off keys need the foot flexed up — leg -18, knee 38, foot -20).

Common requests and how to do them:
- "mais devagar" (slower): raise the move's "beat" (s per key transition) and/or "hold"s, ~1.4-1.6x, keeping
  contacts; check the video still loops cleanly.
- "de frente" (front view): jobs_change {"view": "front"} (or "front3q" if the movement reads better). Check a still.
- view / props / move changes go in report.json as a FLAT "jobs_change": {key: value} (null deletes a key).
- Contacts: after sync, measure the hand/foot/knee `_low` against the surface (≤3 cm gap while resting, no
  penetration > 1 cm, slide ≤ 2 cm while planted). Hands near the ground are re-posed at render by plant_hands —
  measure after it like fix/lote_R2c/postplant.py does. Put the numbers in correcao.

Rules: work only in your W dir; never edit the repo or /mnt/e/mannequin/avatar_man/exercises_final.blend (renders
read it); stills only (other renders share the GPU). No global smoothing that loosens contacts. Do not change the
avatar's look (body/mesh/clothes) — if a note seems to ask for that, fix it via the pose if possible, otherwise
explain in motivo. Do not use Gemini or Vertex. Another fix agent (fix/lote_R3a) owns these jobs — don't edit their
moves: kineti-bed-walker-sit-to-stand, kineti-pillow-inclined-knee-fall-out, kineti-chair-plantar-ball-roll,
kineti-prone-scapular-retraction, kineti-band-pnf-d2-extension, kineti-band-supine-leg-press,
kineti-wall-ball-squat-adductor-ball, kineti-bridge-ball-squeeze, kineti-supine-ball-squeeze,
kineti-pillow-legs-ankle-pumps, kineti-pillow-one-leg-relax, kineti-knee-pillow-squeeze, kineti-prone-relaxed.
Time box ~90 min. Reply (under 300 words): fixed / not fixed per client note, siblings changed, changed move ids,
jobs_change, and anything that needs a change outside the moves (renderer/props) with the exact proposal.
