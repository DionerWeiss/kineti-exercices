"""merge_pp.py NN: final/pp_review/lote_NN.json -> final/review_pp.json; "diferente" ids leave jobs.json and go to
tool/mannequin/pp_removed.json ("precisa de vídeo próprio"); "_visual" notes go to review_notes.json (nota_pp)."""
import json, sys, datetime
from kpaths import F, R
N = sys.argv[1]
src = json.load(open(f'{F}/pp_review/lote_{N}.json', encoding='utf-8'))
pp = json.load(open(f'{F}/review_pp.json', encoding='utf-8'))
notes = json.load(open(f'{F}/review_notes.json', encoding='utf-8'))
jobs = json.load(open(f'{R}/tool/mannequin/jobs.json'))
rem = json.load(open(f'{R}/tool/mannequin/pp_removed.json', encoding='utf-8'))
cat = {e['id']: e for e in json.load(open(f'{R}/research/pocketphysio/exercicios.json', encoding='utf-8'))}
done = {(r['job'], r['pp_id']) for r in rem}
nrem = 0
for job, d in src.items():
    vis = d.pop('_visual', '')
    if vis:
        notes.setdefault(job, {})['nota_pp'] = vis
    for pid, v in d.items():
        if v['pp_match'] == 'diferente':
            v['acao'] = 'removido'
            if job in jobs and pid in jobs[job].get('pocketphysio', []):
                jobs[job]['pocketphysio'].remove(pid)
            if (job, pid) not in done:
                rem.append(dict(pp_id=pid, job=job, nome_pt=cat.get(pid, {}).get('nome_pt', ''), motivo=v['divergencias'],
                                status='precisa de vídeo próprio', removido_em=str(datetime.date.today())))
                nrem += 1
        pp.setdefault(job, {})[pid] = v
json.dump(pp, open(f'{F}/review_pp.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
json.dump(notes, open(f'{F}/review_notes.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
open(f'{R}/tool/mannequin/jobs.json', 'w').write(json.dumps(jobs, indent=1))
open(f'{R}/tool/mannequin/pp_removed.json', 'w', encoding='utf-8').write(json.dumps(rem, ensure_ascii=False, indent=1))
print('merged', len(src), 'jobs;', nrem, 'ids removed; total removed', len(rem))
