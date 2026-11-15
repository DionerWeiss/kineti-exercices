"""merge_visual.py NN: final/visual_review/lote_NN.json -> final/review_notes.json, then review_lote_NN.csv + review.csv."""
import json, sys, subprocess
N = sys.argv[1]
F = '/mnt/e/mannequin/avatar_man/final'
src = json.load(open(f'{F}/visual_review/lote_{N}.json', encoding='utf-8'))
notes = json.load(open(f'{F}/review_notes.json', encoding='utf-8'))
for j, v in src.items():
    notes.setdefault(j, {}).update({k: x for k, x in v.items() if x not in (None,)})
json.dump(notes, open(f'{F}/review_notes.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
M = '/home/dioner/projects/kineti/animated_exercices/tool/mannequin'
O = '/mnt/e/mannequin/avatar_man/out'
r = subprocess.run(['python3', 'review.py', F, f'{O}/videos_final', f'{F}/lotes/lote_{N}.txt', f'review_lote_{N}.csv'], cwd=M, capture_output=True, text=True)
print(r.stdout[-600:], r.stderr[-300:])
subprocess.run(['python3', 'review.py', F, f'{O}/videos_final'], cwd=M, capture_output=True)
