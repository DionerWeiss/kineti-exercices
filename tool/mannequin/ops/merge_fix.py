"""merge_fix.py NN: moves the fix agent changed (fix/lote_NN/moves vs its starting copy) -> the repo moves files;
jobs_change from report.json -> jobs.json; jobs using changed moves -> rerender_ids.txt. Prints the changed move ids."""
import json, sys, os
import kpaths
N = sys.argv[1]
W = f'{kpaths.FIX}/lote_{N}'
M = kpaths.M + '/'
S = kpaths.S + '/'
rep = json.load(open(f'{W}/report.json', encoding='utf-8'))
fixed_moves = {v.get('move', j) for j, v in rep.items() if v.get('status') == 'corrigido'}
changed = []
for fn in ('kineti_moves.json', 'deskbreak_moves.json'):
    main = json.load(open(M + fn, encoding='utf-8'))
    fix = {e['id']: e for e in json.load(open(f'{W}/moves/{fn}', encoding='utf-8'))['exercises']}
    for i, e in enumerate(main['exercises']):
        f = fix.get(e['id'])
        if f is not None and f != e and e['id'] in fixed_moves:
            main['exercises'][i] = f
            changed.append(e['id'])
    have = {e['id'] for e in main['exercises']}
    for k, f in fix.items():
        if k not in have and (k in fixed_moves or k in rep):
            main['exercises'].append(f); changed.append(k)
    open(M + fn, 'w', encoding='utf-8').write(json.dumps(main, ensure_ascii=False, indent=1))
J = json.load(open(M + 'jobs.json'))
jc = []
for j, v in rep.items():
    if v.get('jobs_change') and j in J:
        J[j].update(v['jobs_change']); jc.append(j)
        for k in [k for k, x in J[j].items() if x is None]: del J[j][k]
open(M + 'jobs.json', 'w').write(json.dumps(J, indent=1))
ids = [j for j, v in J.items() if v.get('move', j) in changed] + jc
old = open(S + 'rerender_ids.txt').read().split()
allr = sorted(set(old + ids))
open(S + 'rerender_ids.txt', 'w').write(' '.join(allr))
print('changed', len(changed), 'jobs_change', jc, 'rerender total', len(allr))
open(f'{W}/merged_moves.txt', 'w').write(' '.join(changed))
print(' '.join(changed))
