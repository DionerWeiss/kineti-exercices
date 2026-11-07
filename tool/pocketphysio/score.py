"""Effort scores (0-10) to animate each PocketPhysio exercise in Lottie and in
Blender, computed from the features Gemini extracted from the video
(analyze.py). The rubric is calibrated against what the rig already covers
(catalog.json, tool/README.md, tool/blender/README.md).

    python3 tool/pocketphysio/score.py <exercises.json> <analise.jsonl> <out_dir> \
        [--kineti match_kineti.jsonl] [--deskbreak match_deskbreak.jsonl]

The match files (match_library.py) mark exercises a library already has:
Kineti lowers the Lottie/Blender effort (identico x0.2, variacao x0.6),
desk-break lowers the mannequin effort (identico x0.2, variacao x0.5).

Writes <out_dir>/exercicios.json and <out_dir>/exercicios.csv.
"""
import argparse, csv, json, math, os

# ---------------------------------------------------------------- Lottie
# Posição de partida: quanto o rig já sabe montar.
POSICAO = {
    'em_pe': (0, None), 'sentado_cadeira': (0, None), 'supino': (0.5, None),
    'prono': (1, 'decúbito ventral'), 'decubito_lateral': (1, 'decúbito lateral'), 'quatro_apoios': (1, 'quatro apoios'),
    'sentado_chao_ou_cama': (2, 'sentado no chão/cama (pose nova)'),
    'ajoelhado': (2.5, 'ajoelhado (pose nova)'), 'semiajoelhado': (2.5, 'semiajoelhado (pose nova)'),
    'agachado': (2, 'agachado profundo'), 'close_up_mao': (1.5, 'close-up de mão'),
    'close_up_rosto': (5, 'rosto: rig sem face'), 'outra': (3, 'posição fora do rig'),
}
TIPO = {
    'articular_simples': 0, 'multiarticular': 1, 'rotacao_axial': 1.5, 'circular': 1, 'transicao_postural': 1,
    'locomocao': 1.5, 'equilibrio_estatico': 0.5, 'equilibrio_dinamico': 1.5, 'coordenacao_complexa': 2.5,
    'respiratorio': 1.5, 'motricidade_fina': 2, 'alongamento_sustentado': 0.5, 'isometrico_sem_movimento_visivel': 0.5,
}
INTERACAO = {
    'nenhuma': 0, 'apoio_estatico': 0.5, 'segura_objeto': 1, 'elastico': 1.5, 'superficie_instavel': 2,
    'objeto_dinamico': 2.5, 'objeto_deformavel': 2.5, 'segunda_pessoa': 4,
}
# Acessórios que o rig/builders já desenham (lotes base a 4).
PROPS_PRONTOS = {'nenhum', 'colchonete', 'cadeira', 'cama', 'mesa', 'parede', 'degrau', 'banqueta', 'halter',
                 'tornozeleira', 'faixa_elastica', 'bola_suica', 'bola_pequena', 'bola_media', 'toalha'}
# Acessórios que o render 3D já monta (cadeira, blocos, bola, halter, tornozeleira, faixa, rolo).
PROPS_3D = {'nenhum', 'colchonete', 'cadeira', 'cama', 'mesa', 'parede', 'degrau', 'banqueta', 'halter', 'tornozeleira',
            'faixa_elastica', 'bola_pequena', 'bola_media', 'bola_suica', 'toalha'}
REUSO = {'identico': 0.2, 'variacao': 0.6}
DEITADO = {'supino', 'prono', 'decubito_lateral', 'quatro_apoios', 'sentado_chao_ou_cama', 'ajoelhado', 'semiajoelhado'}


def lottie(a):
    pts, why = 0.0, []

    def add(v, motivo):
        nonlocal pts
        if v:
            pts += v
            why.append((v, motivo))

    pos = a['posicao_inicial']
    v, m = POSICAO.get(pos, (3, pos))
    add(v, m or '')
    fim = a.get('posicao_final', 'mesma')
    if fim not in ('mesma', pos):
        par = {pos, fim}
        if par <= {'em_pe', 'sentado_cadeira'}:
            add(0.5, 'transição em pé↔cadeira (5xSTS no rig)')
        elif par <= {'supino', 'decubito_lateral', 'sentado_cadeira', 'sentado_chao_ou_cama'}:
            add(1.5, f'transição {pos}→{fim} (base no rolar/sentar do rig)')
        else:
            add(2.5, f'transição {pos}→{fim} (nova)')
    add(min(3, max(0, a.get('fases', 1) - 1)) * 0.75, f"{a.get('fases')} fases")
    add(TIPO.get(a['tipo_movimento'], 1), a['tipo_movimento'].replace('_', ' '))
    seg = set(a.get('segmentos_em_movimento') or [])
    if seg & {'dedos', 'polegar'}:
        add(1 if pos == 'close_up_mao' else 2.5, 'dedos')
    if seg & {'face', 'olhos', 'mandibula'}:
        add(1 if pos == 'close_up_rosto' else 3, 'face/olhos/mandíbula')
    if 'escapula' in seg:
        add(1, 'escápula (sutil no 2D)')
    if 'antebraco_rotacao' in seg:
        add(1, 'pronossupinação')
    add(0.5 * len(seg & {'coluna_toracica', 'coluna_lombar'}), 'coluna segmentada')
    if len(seg - {'corpo_inteiro'}) > 3 or 'corpo_inteiro' in seg:
        add(1, 'muitos segmentos ao mesmo tempo')
    add({'alternado': 0.5, 'assimetrico': 1}.get(a.get('lateralidade'), 0), a.get('lateralidade', '').replace('_', ' '))
    if a.get('deslocamento_no_espaco'):
        add(1, 'desloca no espaço')
    if a.get('maos_apoiadas'):
        add(0.5, 'mãos fixas (IK)')
    if a.get('contato_proprio_corpo'):
        add(1, 'mão no próprio corpo')
    add(INTERACAO.get(a.get('interacao_objeto'), 1), f"objeto: {a.get('interacao_objeto', '').replace('_', ' ')}")
    novos = sorted(set(a.get('equipamentos') or []) - PROPS_PRONTOS)
    add(min(2, len(novos)), 'acessório novo: ' + ', '.join(novos))
    if a.get('amplitude') == 'sutil':
        add(1, 'amplitude sutil')
    add(0.25 * a.get('entendimento', 0), 'entendimento do exercício')
    return pts, why, novos


def blender(a, base, novos):
    """Blender reaproveita a cinemática do builder Lottie; soma o custo do 3D."""
    pts, why = base + 1, [(1, 'cena 3D: conferir volume e câmera')]

    def add(v, motivo):
        nonlocal pts
        if v:
            pts += v
            why.append((v, motivo))

    pos, seg = a['posicao_inicial'], set(a.get('segmentos_em_movimento') or [])
    if a.get('contato_proprio_corpo'):
        add(1.5, '3D: membro atravessa o corpo')
    if pos in DEITADO or a.get('posicao_final') in DEITADO:
        add(1, '3D: contato do corpo com o apoio')
    if seg & {'dedos', 'polegar'} or pos == 'close_up_mao':
        add(2.5, '3D: dedos do personagem (não coberto)')
    if seg & {'face', 'olhos', 'mandibula'} or pos == 'close_up_rosto':
        add(3, '3D: rig facial')
    if a.get('tipo_movimento') == 'respiratorio':
        add(1, '3D: shape keys de tórax/abdômen')
    novos3d = sorted(set(a.get('equipamentos') or []) - PROPS_3D)
    add(0.5 * min(3, len(novos3d)), 'modelar: ' + ', '.join(novos3d))
    add({'objeto_deformavel': 1.5, 'objeto_dinamico': 1, 'segunda_pessoa': 2, 'superficie_instavel': 0.5}
        .get(a.get('interacao_objeto'), 0), f"3D: {a.get('interacao_objeto', '').replace('_', ' ')}")
    fim = a.get('posicao_final', 'mesma')
    if fim not in ('mesma', pos):
        add(1, '3D: colisões na transição')
    return pts, why


# ------------------------------------------------------------- manequim
# desk-break (github.com/shlomorsh/desk-break, MIT) + build/kineti_mannequin/render_v2.py:
# 14 ossos em FK (hips, spine inteiro, neck, arm/elbow/hand, leg/knee/foot), poses em JSON,
# chão e contatos com o chão automáticos (IK de dois ossos). Sem dedos, sem rosto, sem
# clavícula (só arm.pos), coluna num osso só, contatos só com o chão (mão no encosto/parede
# não fica presa). Acessórios do render_v2: chair, support, wall, roll, ball, cuff, dumbbell.
PROPS_MANEQUIM = {'nenhum', 'colchonete', 'cadeira', 'parede', 'banqueta', 'toalha', 'bola_pequena', 'bola_media',
                  'tornozeleira', 'halter', 'cama'}
MAOS_NO_CHAO = {'prono', 'quatro_apoios', 'sentado_chao_ou_cama'}


def manequim(a):
    pts, why = 0.5, [(0.5, 'poses em JSON')]

    def add(v, motivo):
        nonlocal pts
        if v:
            pts += v
            why.append((v, motivo))

    pos, fim = a['posicao_inicial'], a.get('posicao_final', 'mesma')
    seg = set(a.get('segmentos_em_movimento') or [])
    add({'close_up_mao': 8, 'close_up_rosto': 10, 'outra': 2}.get(pos, 0), 'manequim sem dedos/rosto' if pos.startswith('close') else pos)
    if fim not in ('mesma', pos):
        add(1.5 if 'em_pe' in (pos, fim) and fim != 'sentado_cadeira' and pos != 'sentado_cadeira' else 1, 'transição por keys')
    add(min(3, max(0, a.get('fases', 1) - 1)) * 0.3, f"{a.get('fases')} fases")
    add({'coordenacao_complexa': 1, 'rotacao_axial': 0.5, 'respiratorio': 3, 'isometrico_sem_movimento_visivel': 2,
         'motricidade_fina': 3}.get(a['tipo_movimento'], 0), a['tipo_movimento'].replace('_', ' '))
    if seg & {'dedos', 'polegar'} and pos != 'close_up_mao':
        add(6, 'dedos: manequim tem mão em luva')
    if seg & {'face', 'olhos', 'mandibula'} and pos != 'close_up_rosto':
        add(8, 'rosto: manequim sem face')
    if 'escapula' in seg:
        add(1.5, 'escápula: sem clavícula (só arm.pos)')
    if {'coluna_toracica', 'coluna_lombar'} <= seg or 'pelve' in seg and 'coluna_lombar' in seg:
        add(1.5, 'coluna num osso só')
    if 'pe_dedos' in seg:
        add(1, 'dedos do pé')
    if a.get('maos_apoiadas') and pos not in MAOS_NO_CHAO:
        add(2, 'mão presa em apoio fora do chão (IK novo)')
    if a.get('contato_proprio_corpo'):
        add(1.5, 'mão no próprio corpo (sem colisão)')
    add({'apoio_estatico': 0.5, 'segura_objeto': 1, 'elastico': 2.5, 'objeto_dinamico': 3, 'superficie_instavel': 2,
         'objeto_deformavel': 3, 'segunda_pessoa': 5}.get(a.get('interacao_objeto'), 0),
        f"objeto: {a.get('interacao_objeto', '').replace('_', ' ')}")
    novos = sorted(set(a.get('equipamentos') or []) - PROPS_MANEQUIM)
    add(min(2, len(novos)), 'acessório novo: ' + ', '.join(novos))
    if a.get('deslocamento_no_espaco'):
        add(0.5, 'desloca (pos)')
    if a.get('amplitude') == 'sutil':
        add(1, 'amplitude sutil')
    add(0.25 * a.get('entendimento', 0), 'entendimento do exercício')
    return pts, why


def clamp(v, k=8.0):
    """Pontos somados -> 0-10 com saturação: o rig atual (tier 1-2 do catálogo)
    cai em 1-4; tier 3 em 5-7; só o que exige rig novo chega a 9-10."""
    return int(round(10 * (1 - math.exp(-max(0.0, v) / k))))


def top(why, n=4):
    return '; '.join(m for v, m in sorted(why, key=lambda x: -x[0])[:n] if m)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src'); ap.add_argument('analysis'); ap.add_argument('out')
    ap.add_argument('--kineti'); ap.add_argument('--deskbreak')
    args = ap.parse_args()
    src, analysis, out = args.src, args.analysis, args.out
    load = lambda p: {m['id']: m for m in map(json.loads, open(p))} if p and os.path.exists(p) else {}
    match, desk = load(args.kineti), load(args.deskbreak)
    items = {x['_id']: x for x in json.load(open(src))['data']}
    rows, latest = [], {}
    for line in open(analysis):
        r = json.loads(line)
        if 'erro' not in r['analise'] or r['id'] not in latest:
            latest[r['id']] = r
    for ex_id, ex in items.items():
        r = latest.get(ex_id)
        base = {
            'id': ex_id, 'publicado': bool(ex.get('isLive')), 'titulo_original': (ex.get('title') or '').strip(),
            'regioes': [b.get('title') for b in ex.get('body_part_id') or [] if isinstance(b, dict)],
            'equipamento_original': ex.get('equipment') or [], 'movimento_original': ex.get('movementType'),
            'video': ex.get('videoUrl'), 'imagem': ex.get('exerciseImage') or ex.get('imageUrl'),
        }
        if not r or 'erro' in r['analise']:
            rows.append({**base, 'fonte': None, 'erro': (r or {}).get('analise', {}).get('erro', 'não analisado')})
            continue
        a = r['analise']
        lp, lw, novos = lottie(a)
        bp, bw = blender(a, lp, novos)
        mp, mw = manequim(a)
        d = desk.get(ex_id, {})
        fd = {'identico': 0.2, 'variacao': 0.5}.get(d.get('relacao'), 1)
        if fd < 1:
            mp, mw = mp * fd, [(99, f"{d['relacao']} de desk-break/{d['kineti_slug']} (x{fd})")] + mw
        m = match.get(ex_id, {})
        fator = REUSO.get(m.get('relacao'), 1)
        if fator < 1:
            motivo = f"{m['relacao']} de {m['kineti_slug']} (x{fator})"
            lp, bp = lp * fator, bp * fator
            lw, bw = [(99, motivo)] + lw, [(99, motivo)] + bw
        rows.append({**base, 'fonte': r.get('fonte', 'video'),
                     'nome_pt': a['nome_pt'], 'descricao_pt': a['descricao_pt'], 'objetivo_pt': a['objetivo_pt'],
                     'entendimento': a['entendimento'], 'comunicabilidade': a['comunicabilidade'],
                     'kineti_slug': m.get('kineti_slug') or None, 'relacao_kineti': m.get('relacao'),
                     'deskbreak_id': d.get('kineti_slug') or None, 'relacao_deskbreak': d.get('relacao'),
                     'esforco_lottie': clamp(lp), 'esforco_blender': clamp(bp), 'esforco_manequim': clamp(mp),
                     'motivos_lottie': top(lw), 'motivos_blender': top([w for w in bw if w[1].startswith(('3D', 'modelar', 'identico', 'variacao'))] or bw),
                     'motivos_manequim': top(mw),
                     'observacoes': a['observacoes'], 'caracteristicas': {k: v for k, v in a.items() if k not in (
                         'nome_pt', 'descricao_pt', 'objetivo_pt', 'entendimento', 'comunicabilidade', 'observacoes')}})
    rows.sort(key=lambda x: (x.get('esforco_lottie', 99), x.get('esforco_blender', 99), x['titulo_original']))
    os.makedirs(out, exist_ok=True)
    json.dump(rows, open(os.path.join(out, 'exercicios.json'), 'w'), ensure_ascii=False, indent=1)
    cols = ['id', 'publicado', 'nome_pt', 'titulo_original', 'regioes', 'esforco_lottie', 'esforco_blender', 'esforco_manequim', 'entendimento',
            'comunicabilidade', 'relacao_kineti', 'kineti_slug', 'relacao_deskbreak', 'deskbreak_id', 'descricao_pt', 'objetivo_pt', 'motivos_lottie', 'motivos_blender', 'motivos_manequim', 'observacoes',
            'posicao_inicial', 'tipo_movimento', 'equipamentos', 'fonte', 'video', 'erro']
    with open(os.path.join(out, 'exercicios.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, cols, extrasaction='ignore')
        w.writeheader()
        for x in rows:
            c = x.get('caracteristicas', {})
            w.writerow({**x, 'regioes': ', '.join(x['regioes']), 'posicao_inicial': c.get('posicao_inicial'),
                        'tipo_movimento': c.get('tipo_movimento'), 'equipamentos': ', '.join(c.get('equipamentos', []))})
    ok = [x for x in rows if 'esforco_lottie' in x]
    print(f'{len(rows)} exercícios, {len(ok)} analisados, {len(rows) - len(ok)} com erro')


if __name__ == '__main__':
    main()
