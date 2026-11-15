"""Review tables of the avatar re-render: tool/mannequin/review.py <out> [<videos dir> [<ids file> [<csv name>]]]

Joins jobs.json, the automatic checks of <out>/qa (layer 1 <id>.json from qa_pose.py, layer 2 <id>.motion.json
from motion_review.py and <id>.video.json from video_qa.py) and two hand-written files:
- <out>/review_notes.json: the visual review per job (layer 4)
    {"<id>": {"visual": "ok" | "corrigido" | "pendente", "nota": "...", "correcao": "...", "motivo": "..."}}
- <out>/review_pp.json: the PocketPhysio comparison per job and id (layer 3)
    {"<job>": {"<pp id>": {"pp_match": "igual" | "próximo" | "diferente", "ref": "video" | "texto",
                            "divergencias": "...", "corrigido": "sim" | "não" | "-", "acao": "mantido" | "removido"}}}
Writes <out>/<csv name> (default review.csv, one row per job) and review_pp.csv (one row per job and id).
"final" is the visual verdict when there is one; otherwise "ok" when every automatic layer is ok, and "pendente"
(motivo: "aguarda revisão visual") for anything flagged. Prints the totals.
"""
import csv
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def load(p):
    return json.load(open(p, encoding='utf-8')) if p.exists() else None


def main(out, vids=None, only=None, name='review.csv'):
    jobs = json.load(open(HERE / 'jobs.json'))
    cat = {e['id']: e for e in json.load(open(REPO / 'research/pocketphysio/exercicios.json', encoding='utf-8'))}
    notes = load(out / 'review_notes.json') or {}
    pp = load(out / 'review_pp.json') or {}
    rows, pprows = [], []
    for jid, j in jobs.items():
        if only and jid not in only:
            continue
        qa, mo, vi = (load(out / 'qa' / f'{jid}{s}.json') for s in ('', '.motion', '.video'))
        n = notes.get(jid, {})
        tec = qa['status'] if qa else ('—' if j['lib'] == 'hand' else 'não checado')
        mov = mo['motion_status'] if mo else ('—' if j['lib'] == 'hand' else 'não checado')
        vid = vi['video_status'] if vi else 'não checado'
        jp = pp.get(jid, {})
        cnt = Counter(v.get('pp_match', '') for v in jp.values())
        autos = [x for x in (tec, mov, vid) if x not in ('—',)]
        final = n.get('visual') or ('ok' if autos and all(x == 'ok' for x in autos) else '')
        motivo = n.get('motivo', '')
        if not final:
            final, motivo = 'pendente', motivo or 'aguarda revisão visual'
        rows.append(dict(
            id=jid, lib=j['lib'], view=j['view'], props='+'.join(j.get('props', [])),
            tecnico=tec, problemas_tecnicos='; '.join(i['msg'] for i in qa['issues']) if qa else '',
            pops=mo.get('pops', '') if mo else '', max_jerk=mo.get('max_jerk', '') if mo else '',
            loop_gap=' / '.join(f'{v}' for v in mo['loop_gap']) if mo else '',
            rom_violations='; '.join(mo.get('rom_violations', [])) if mo else '',
            balance=(mo.get('balance') if mo and mo.get('balance') is not None else ''),
            legivel=mo.get('legivel', '') if mo else '', motion_status=mov,
            problemas_movimento='; '.join(i['msg'] for i in mo['motion_issues']) if mo else '',
            video_status=vid, problemas_video='; '.join(i['msg'] for i in vi['issues']) if vi else '',
            repeticoes=f"{mo['reps_cycle']}x{mo['loops']}" if mo else '', seg_por_rep=mo.get('sec_per_rep', '') if mo else '',
            pp_ids=len(j.get('pocketphysio', [])),
            pp_resumo=', '.join(f'{k} {v}' for k, v in cnt.items() if k) or 'não comparado',
            revisado='sim' if n.get('visual') else 'não', final=final, correcao=n.get('correcao', ''), motivo=motivo,
            nota=n.get('nota', ''),
            video=(str(vids / f'{jid}.mp4') if vids and (vids / f'{jid}.mp4').exists() else '')))
        for pid in j.get('pocketphysio', []) + [k for k in jp if k not in j.get('pocketphysio', [])]:
            v = jp.get(pid, {})
            pprows.append(dict(job=jid, pp_id=pid, nome_pt=cat.get(pid, {}).get('nome_pt', ''),
                               relacao=cat.get(pid, {}).get('relacao_deskbreak', ''), ref=v.get('ref', ''),
                               pp_match=v.get('pp_match', 'não comparado'), divergencias=v.get('divergencias', ''),
                               corrigido=v.get('corrigido', ''), acao=v.get('acao', '')))
    for fname, rr in ((name, rows), ('review_pp.csv' if name == 'review.csv' else name.replace('.csv', '_pp.csv'), pprows)):
        if not rr:
            continue
        with open(out / fname, 'w', newline='', encoding='utf-8-sig') as fh:
            w = csv.DictWriter(fh, fieldnames=list(rr[0]))
            w.writeheader()
            w.writerows(rr)
        print(out / fname)
    print('técnico:', dict(Counter(r['tecnico'] for r in rows)))
    print('movimento:', dict(Counter(r['motion_status'] for r in rows)))
    print('vídeo:', dict(Counter(r['video_status'] for r in rows)))
    print('final:', dict(Counter(r['final'] for r in rows)))
    print('pp:', dict(Counter(r['pp_match'] for r in pprows)))


if __name__ == '__main__':
    a = sys.argv[1:]
    main(Path(a[0]), Path(a[1]) if len(a) > 1 else None, open(a[2]).read().split() if len(a) > 2 else None,
         a[3] if len(a) > 3 else 'review.csv')
