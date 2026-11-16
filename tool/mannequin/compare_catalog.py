"""Catálogo de comparação PocketPhysio x manequim x Lottie x render 3D, uma página HTML local.

    python3 tool/mannequin/compare_catalog.py            # -> E:\\mannequin\\catalogo\\index.html + data.js

Rodar de novo atualiza os dados (vídeos novos do re-render, Lotties, revisões). Os vídeos não são copiados: a página
usa caminhos relativos a partir de E:\\mannequin\\catalogo:
  PocketPhysio  ../pocketphysio_ref/<pp id>.mp4
  Manequim      ../videos/<job>.mp4                      (vídeos antigos do manequim, intocados)
  Lottie        ../puppet2d/final/<job>.mp4               (o .json do Lottie fica ao lado)
  Render 3D     ../avatar_man/out/videos_final/<job>.mp4
Nome, descrição, foco e área: tool/mannequin/catalog.json. Nomes do PocketPhysio: research/pocketphysio/exercicios.json.
Situação: final/validation, final/pp_review, final/visual_review, fix/lote_NN/report.json, pp_removed.json,
puppet2d/final/manifest.json e a lista de pendências (PENDENTES).
"""
import datetime
import glob
import json
import os
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
E = Path('/mnt/e/mannequin')
FINAL = E / 'avatar_man' / 'final'
FIX = E / 'avatar_man' / 'fix'
OUT = E / 'catalogo'
LOTTIE = E / 'puppet2d' / 'final'
V3D = E / 'avatar_man' / 'out' / 'videos_final'
PENDENTES = Path(os.environ.get('PENDENTES', str(E / 'avatar_man' / 'ops' / 'pendentes_final.txt')))
RERENDER_START = datetime.datetime(2026, 11, 14, 11, 20).timestamp()


def load(p, default=None):
    try:
        return json.load(open(p, encoding='utf-8-sig'))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def main():
    cat = load(HERE / 'catalog.json')
    jobs = load(HERE / 'jobs.json')
    areas = {a['id']: a['name'] for a in cat['areas']}
    pp_names = {e['id']: e.get('nome_pt') or e.get('titulo_original', '') for e in load(REPO / 'research' / 'pocketphysio' / 'exercicios.json', [])}
    removed = {}
    for r in load(HERE / 'pp_removed.json', []):
        removed.setdefault(r['job'], []).append(r)

    lote_of, rerender = {}, set()
    for f in sorted(glob.glob(str(FINAL / 'lotes' / 'lote_*.txt'))):
        n = Path(f).stem[5:]
        for j in open(f).read().split():
            if n.startswith('R'):
                rerender.add(j)
            else:
                lote_of[j] = n

    def per_lote(sub):
        d = {}
        for f in sorted(glob.glob(str(FINAL / sub / 'lote_*.json'))):
            for k, v in (load(f, {}) or {}).items():
                d[k] = v
        return d
    val, ppr, vis = per_lote('validation'), per_lote('pp_review'), per_lote('visual_review')
    fixes = {}
    for f in sorted(glob.glob(str(FIX / 'lote_*' / 'report.json'))):
        for k, v in (load(f, {}) or {}).items():
            if isinstance(v, dict):
                fixes[k] = {'lote': Path(f).parent.name[5:], 'status': v.get('status', ''),
                            'correcao': v.get('correcao', ''), 'motivo': v.get('motivo', '')}
    pend = {}
    if PENDENTES.exists():
        for line in PENDENTES.read_text(encoding='utf-8').splitlines():
            m = re.match(r'\s*([\w-]+)(?:\s*/\s*([\w-]+))?\s*:\s*(.+)', line)
            if m:
                for j in filter(None, m.group(1, 2)):
                    pend.setdefault(j, []).append(m.group(3).strip())
    man = load(LOTTIE / 'manifest.json', {}) or {}
    if isinstance(man, list):
        man = {m.get('job'): m for m in man}
    elif 'jobs' in man:
        man = man['jobs'] if isinstance(man['jobs'], dict) else {m.get('job'): m for m in man['jobs']}

    data = []
    for c in cat['exercises']:
        j = c['slug']
        jb = jobs.get(j, {})
        pps = []
        for pid in jb.get('pocketphysio', []):
            r = (ppr.get(j) or {}).get(pid) or {}
            pps.append({'id': pid, 'nome': pp_names.get(pid, ''), 'match': r.get('pp_match', ''),
                        'div': r.get('divergencias', ''), 'video': (E / 'pocketphysio_ref' / f'{pid}.mp4').exists()})
        for r in removed.get(j, []):
            pps.append({'id': r['pp_id'], 'nome': pp_names.get(r['pp_id'], r.get('nome_pt', '')), 'match': 'removido',
                        'div': r.get('motivo', ''), 'video': (E / 'pocketphysio_ref' / f"{r['pp_id']}.mp4").exists()})
        v3 = V3D / f'{j}.mp4'
        st3 = 'sem vídeo'
        if v3.exists():
            new = v3.stat().st_mtime >= RERENDER_START
            st3 = 'novo' if new else ('aguardando re-render' if j in rerender else 'final')
        lm = man.get(j) or {}
        lot = {'video': (LOTTIE / f'{j}.mp4').exists(), 'view': lm.get('view', ''), 'status': lm.get('status', ''),
               'motivo': lm.get('motivo') or lm.get('reason') or lm.get('limitacao') or ''}
        if jb.get('lib') == 'hand':
            lot['status'], lot['motivo'] = lot['status'] or 'não se aplica', lot['motivo'] or 'close da mão (sem corpo)'
        vv, vs = val.get(j) or {}, vis.get(j) or {}
        data.append({
            'id': j, 'nome': c.get('name', j), 'desc': c.get('desc', ''), 'foco': c.get('focus', ''),
            'area': areas.get(c.get('area'), c.get('area', '')), 'props': c.get('props', ''), 'lib': jb.get('lib', ''),
            'lote': lote_of.get(j, ''), 'pp': pps,
            'val': vv.get('verdict', ''), 'val_txt': vv.get('resumo', ''),
            'vis': vs.get('visual', ''), 'vis_txt': vs.get('nota', ''),
            'fix': fixes.get(j), 'pend': pend.get(j, []),
            'man': (E / 'videos' / f'{j}.mp4').exists(), 'lottie': lot, 'r3d': st3,
        })
    OUT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime('%d/%m %H:%M')
    (OUT / 'data.js').write_text('window.CATALOG=' + json.dumps({'stamp': stamp, 'items': data}, ensure_ascii=False) + ';\n',
                                 encoding='utf-8')
    (OUT / 'index.html').write_text((HERE / 'compare_catalog.html').read_text(encoding='utf-8'), encoding='utf-8')
    n = len(data)
    print(f'{n} exercícios -> {OUT}/index.html ({stamp}); lottie {sum(d["lottie"]["video"] for d in data)}, '
          f'3D novos {sum(d["r3d"] == "novo" for d in data)}, aguardando {sum(d["r3d"] == "aguardando re-render" for d in data)}')


if __name__ == '__main__':
    main()
