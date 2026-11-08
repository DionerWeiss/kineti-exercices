"""Catálogo dos vídeos do manequim, em português, no formato do catalog.json da biblioteca Kineti.

    python3 tool/mannequin/catalog.py      # -> tool/mannequin/catalog.json

Os movimentos Kineti que já existem na biblioteca copiam nome, descrição, foco e área do catalog.json. Os demais vêm
de texts_pt.json ({slug: [nome, descrição, foco, área]}), escrito à mão a partir dos passos do desk-break e dos
nomes dos exercícios do PocketPhysio que o vídeo atende. A descrição segue o que o vídeo mostra.
"""
import collections, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
DESK = REPO / 'build' / 'desk-break' / 'library' / 'exercises.json'
POCKET = REPO / 'research' / 'pocketphysio' / 'exercicios.json'
OUT = HERE / 'catalog.json'

VIEWS = {'side': 'Lateral', 'front': 'Frontal', 'side3q': 'Lateral 3/4', 'front3q': 'Frontal 3/4', 'rside3q': 'Lateral 3/4',
         'back3q': 'Posterior 3/4', 'top3q': 'Elevada', 'floor': 'Lateral elevada',
         'close': 'Detalhe da mão'}
FRAMES = {'upper': ', do peito para cima', 'lower': ', pés em destaque', 'full': ''}
PROPS = {'chair': 'Cadeira', 'support': 'Cadeira (apoio)', 'side': 'Cadeira (apoio lateral)', 'wall': 'Parede', 'roll': 'Rolo', 'ball': 'Bola pequena',
         'cuff': 'Tornozeleira', 'dumbbell': 'Halteres', 'mat': 'Colchonete', 'table': 'Mesa', 'bed': 'Cama',
         'bandhands': 'Faixa elástica', 'bandanchor': 'Faixa elástica presa no batente',
         'bandanchor1': 'Faixa elástica presa no batente', 'bandfeet': 'Faixa elástica sob os pés',
         'bandknees': 'Faixa elástica nas coxas', 'chairfit': 'Cadeira', 'walk': '—', 'wallball': 'Parede, bola suíça',
         'wallback': 'Parede', 'swissseat': 'Bola suíça', 'step': 'Degrau', 'heldball': 'Bola',
         'bandankles': 'Faixa elástica nos tornozelos'}


def prop_label(p):
    if p.startswith(('ballfeet', 'ballarms', 'ballhands', 'ballback')):
        return 'Bola suíça'
    if p.startswith('band-'):  # band-<end>-<end> (render_mannequin.py)
        ends = p.split('-')[1:]
        if any(e[0] in 'FBLR' for e in ends):
            return 'Faixa elástica presa'
        return 'Faixa elástica no pé' if any(e[0] == 'f' for e in ends) else 'Faixa elástica'
    return PROPS[p]

KSLUG = {'kineti-standing-hip-abduction-supported': 'standing_hip_abduction',
         'kineti-standing-knee-flexion-supported': 'standing_knee_flexion',
         'kineti-seated-elbow-curl-dumbbell': 'elbow_flexion_dumbbell'}


def kineti_slug(slug):
    return KSLUG.get(slug, slug.removeprefix('kineti-').replace('-', '_'))


def main():
    jobs = json.load(open(HERE / 'jobs.json'))
    kcat = json.load(open(REPO / 'catalog.json'))
    kin = {e['slug']: e for e in kcat['exercises']}
    areas = {a['id'] for a in kcat['areas']}
    desk = {e['id']: e for e in json.load(open(DESK))['exercises']}
    pocket = {e['id']: e for e in json.load(open(POCKET))}

    texts = {}
    for slug, j in jobs.items():
        if j['lib'] in ('kineti', 'hand') and kineti_slug(slug) in kin:
            e = kin[kineti_slug(slug)]
            texts[slug] = {k: e[k] for k in ('name', 'desc', 'focus', 'area')}
    for slug, (name, desc, focus, area) in json.load(open(HERE / 'texts_pt.json')).items():
        texts[slug] = {'name': name, 'desc': desc, 'focus': focus, 'area': area}
    missing = [s for s in jobs if s not in texts]
    bad = [s for s, t in texts.items() if t['area'] not in areas]
    dup = [n for n, c in collections.Counter(t['name'] for t in texts.values()).items() if c > 1]
    if missing or bad or dup:
        raise SystemExit(f'sem texto: {missing}; área inválida: {bad}; nome repetido: {dup}')

    libmap = {v['video']: k for k, v in json.load(open(HERE / 'library_map.json')).items() if v['video']}
    out = []
    for slug, j in jobs.items():
        props = list(j.get('props', []))
        rel = collections.Counter(pocket[i]['kineti_slug'] for i in j['pocketphysio']
                                  if pocket[i].get('relacao_kineti') == 'identico' and pocket[i].get('kineti_slug'))
        # the library exercise this video replaces (library_map.json); otherwise only an indicative match
        kslug = libmap.get(slug) or (rel.most_common(1)[0][0] if rel else '')
        cat = desk.get(slug, {}).get('category', '')
        # no chão o render põe o colchonete (só a deusa, do grupo yoga, é em pé)
        lying = 'bed' not in props and j['view'] == 'floor' or cat.startswith('floor') or (cat == 'yoga' and slug != 'goddess-pose-gentle')
        out.append({
            'slug': slug, 'lib': j['lib'], **texts[slug],
            'view': VIEWS[j['view']] + FRAMES[j.get('frame', 'full')],
            'props': ', '.join(dict.fromkeys([prop_label(p) for p in props if prop_label(p) != '—'] + (['Colchonete'] if lying else []))) or '—',
            'video': f'build/mannequin/videos/{slug}.mp4',
            'kineti_slug': kslug,
            'substitui': libmap.get(slug, ''),
            'pocketphysio': j['pocketphysio'],
        })
    order = [a['id'] for a in kcat['areas']]
    out.sort(key=lambda e: (order.index(e['area']), e['name']))
    json.dump({'areas': kcat['areas'], 'license': 'Manequim e movimentos do desk-break: MIT, Copyright (c) 2026 Shlomy Reshef (parametric.co.il), '
               'github.com/shlomorsh/desk-break', 'exercises': out}, open(OUT, 'w'), ensure_ascii=False, indent=1)
    print(OUT, len(out), collections.Counter(e['area'] for e in out))


if __name__ == '__main__':
    main()
