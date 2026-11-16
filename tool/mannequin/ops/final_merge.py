"""final_merge.py: fold every visual review (lotes 01-14, then R01-R14 in order, later wins) into final/review_notes.json
(replacing the verdict fields, keeping other keys like nota_pp), then the full review.csv over all jobs.
Prints totals and writes final/pendentes_final.json (job: motivo) for the summary."""
import glob, json, os, subprocess
from kpaths import F, M, O, VID
notes = json.load(open(f'{F}/review_notes.json', encoding='utf-8'))
json.dump(notes, open(f'{F}/review_notes_before_final.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
order = sorted(glob.glob(f'{F}/visual_review/lote_[0-9]*.json')) + \
        sorted(glob.glob(f'{F}/visual_review/lote_R*.json'), key=lambda p: int(os.path.basename(p)[6:-5]))
src = {}
for p in order:
    for j, v in json.load(open(p, encoding='utf-8')).items():
        src[j] = (os.path.basename(p)[5:-5], v)
for j, (lote, v) in src.items():
    e = notes.setdefault(j, {})
    for k in ('visual', 'nota', 'correcao', 'motivo'):
        e[k] = v.get(k, '') or ''
    e['lote_revisao'] = lote
json.dump(notes, open(f'{F}/review_notes.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
jobs = json.load(open(f'{M}/jobs.json'))
open(f'{F}/all_ids.txt', 'w').write(' '.join(jobs))
r = subprocess.run(['python3', 'review.py', F, VID, f'{F}/all_ids.txt', 'review.csv'], cwd=M,
                   capture_output=True, text=True)
print(r.stdout[-1500:], r.stderr[-800:])
pend = {j: notes[j].get('motivo', '') for j in jobs if notes.get(j, {}).get('visual') == 'pendente'}
json.dump(pend, open(f'{F}/pendentes_final.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('visual verdicts', len(src), 'pendentes', len(pend))
