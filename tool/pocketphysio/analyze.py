"""Watch each PocketPhysio exercise video with Gemini (Vertex) and extract
structured features + an original Portuguese description.

    bash -ic "python3 -I tool/pocketphysio/analyze.py <exercises.json> <out.jsonl> [--limit N] [--ids a,b] [--workers 8]"

Resumable: ids already in out.jsonl are skipped.
"""
import argparse, base64, json, os, subprocess, sys, tempfile, threading, time, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor

MODEL = 'gemini-3-flash-preview'
BASE = 'https://aiplatform.googleapis.com/v1/projects/143173535779/locations/global/publishers/google'

E = lambda *v: {'type': 'STRING', 'enum': list(v)}
SCHEMA = {
  'type': 'OBJECT',
  'properties': {
    'nome_pt': {'type': 'STRING', 'description': 'Nome curto em português do Brasil, termo clínico usual de fisioterapia'},
    'descricao_pt': {'type': 'STRING', 'description': 'Descrição ORIGINAL (não tradução literal) em PT-BR, 2 a 3 frases: posição inicial, execução, retorno. Baseada no que o vídeo mostra.'},
    'objetivo_pt': {'type': 'STRING', 'description': 'Objetivo clínico em poucas palavras (ex.: fortalecer glúteo médio)'},
    'posicao_inicial': E('em_pe', 'sentado_cadeira', 'sentado_chao_ou_cama', 'supino', 'prono', 'decubito_lateral',
                         'quatro_apoios', 'ajoelhado', 'semiajoelhado', 'agachado', 'close_up_mao', 'close_up_rosto', 'outra'),
    'posicao_final': E('mesma', 'em_pe', 'sentado_cadeira', 'sentado_chao_ou_cama', 'supino', 'prono', 'decubito_lateral',
                       'quatro_apoios', 'ajoelhado', 'semiajoelhado', 'agachado', 'outra'),
    'vista_ideal': E('perfil', 'frontal', 'diagonal', 'posterior', 'superior', 'close_up'),
    'fases': {'type': 'INTEGER', 'description': 'Número de etapas distintas do movimento num ciclo (1 = ida e volta simples)'},
    'segmentos_em_movimento': {'type': 'ARRAY', 'items': E(
        'cabeca_pescoco', 'olhos', 'face', 'mandibula', 'escapula', 'ombro', 'cotovelo', 'antebraco_rotacao', 'punho', 'dedos', 'polegar',
        'coluna_toracica', 'coluna_lombar', 'pelve', 'quadril', 'joelho', 'tornozelo', 'pe_dedos', 'corpo_inteiro')},
    'lateralidade': E('unilateral', 'bilateral_simetrico', 'alternado', 'assimetrico'),
    'tipo_movimento': E('isometrico_sem_movimento_visivel', 'articular_simples', 'multiarticular', 'rotacao_axial',
                        'circular', 'transicao_postural', 'locomocao', 'equilibrio_estatico', 'equilibrio_dinamico',
                        'coordenacao_complexa', 'respiratorio', 'motricidade_fina', 'alongamento_sustentado'),
    'deslocamento_no_espaco': {'type': 'BOOLEAN', 'description': 'A pessoa sai do lugar (anda, dá passos, desloca o corpo)'},
    'maos_apoiadas': {'type': 'BOOLEAN', 'description': 'Mãos fixas num apoio (encosto, parede, chão, mesa) durante o movimento'},
    'contato_proprio_corpo': {'type': 'BOOLEAN', 'description': 'Mão segura/toca o próprio corpo (joelho, nuca, braços cruzados...)'},
    'equipamentos': {'type': 'ARRAY', 'items': E(
        'nenhum', 'colchonete', 'cadeira', 'cama', 'mesa', 'parede', 'degrau', 'banqueta', 'travesseiro', 'toalha', 'bastao',
        'halter', 'tornozeleira', 'faixa_elastica', 'bola_suica', 'bola_pequena', 'bola_media', 'theraputty', 'rolo_espuma',
        'bosu', 'prancha_equilibrio', 'cones_marcadores', 'andador', 'bengala', 'cadeira_rodas', 'assistente', 'objeto_cotidiano', 'outro')},
    'interacao_objeto': E('nenhuma', 'apoio_estatico', 'segura_objeto', 'objeto_dinamico', 'elastico', 'superficie_instavel',
                          'objeto_deformavel', 'segunda_pessoa'),
    'amplitude': E('sutil', 'moderada', 'grande'),
    'ritmo': E('lento_controlado', 'moderado', 'rapido', 'sustentado'),
    'texto_coerente_com_video': {'type': 'BOOLEAN'},
    'entendimento': {'type': 'INTEGER', 'description': '0 a 10: dificuldade de ENTENDER e especificar o movimento exato a partir do vídeo+texto (0 = óbvio; 10 = ambíguo, sutil, muitos detalhes ou texto contradiz o vídeo)'},
    'comunicabilidade': {'type': 'INTEGER', 'description': '0 a 10: dificuldade de um paciente entender o exercício só vendo uma animação muda de bonequinho, sem texto (0 = óbvio; 10 = quase invisível, ex. isometria, respiração, ativação interna)'},
    'observacoes': {'type': 'STRING', 'description': 'Detalhes que um animador precisa saber: pegada, ângulos, o que fica parado, armadilhas. Curto, PT-BR.'},
  },
  'required': ['nome_pt', 'descricao_pt', 'objetivo_pt', 'posicao_inicial', 'posicao_final', 'vista_ideal', 'fases',
               'segmentos_em_movimento', 'lateralidade', 'tipo_movimento', 'deslocamento_no_espaco', 'maos_apoiadas',
               'contato_proprio_corpo', 'equipamentos', 'interacao_objeto', 'amplitude', 'ritmo',
               'texto_coerente_com_video', 'entendimento', 'comunicabilidade', 'observacoes'],
}

PROMPT = """Você é um fisioterapeuta e diretor de animação analisando um vídeo de exercício para recriá-lo como animação de um boneco (Lottie 2D e personagem 3D no Blender).
Assista ao vídeo inteiro. Use o texto abaixo só como apoio; quando divergir, vale o vídeo.

Título original: {title}
Texto original: {description}
Equipamento informado: {equipment}
Tipo de movimento informado: {movement}
Regiões: {regions}

Responda no esquema JSON. Escreva a descrição com suas próprias palavras, em português do Brasil, linguagem clara para paciente idoso."""

lock = threading.Lock()


TMP = os.environ.get('POCKETPHYSIO_TMP', '/tmp/pocketphysio_vid')


def shrink(url):
    """Download a large video and re-encode to 360p (keeps narration) for inline upload."""
    os.makedirs(TMP, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=TMP) as d:
        src, dst = os.path.join(d, 'in.mp4'), os.path.join(d, 'out.mp4')
        urllib.request.urlretrieve(url, src)
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-vf', 'scale=-2:360,fps=12', '-c:v', 'libx264',
                        '-crf', '32', '-preset', 'veryfast', '-c:a', 'aac', '-ac', '1', '-b:a', '32k', dst], check=True)
        return base64.b64encode(open(dst, 'rb').read()).decode()


def has_video(ex):
    u = ex.get('videoUrl') or ''
    return u.lower().endswith(('.mp4', '.mov', '.webm')) and 'Demo+Video' not in u


def has_image(ex):
    img = ex.get('exerciseImage') or ex.get('imageUrl') or ''
    return bool(img) and 'Demo+Thumbnail' not in img


def fonte(ex):
    return 'video' if has_video(ex) else 'imagem+texto' if has_image(ex) else 'texto'


def call(ex, key, retries=5):
    regions = ', '.join(b.get('title', '') for b in ex.get('body_part_id') or [] if isinstance(b, dict))
    text = PROMPT.format(title=(ex.get('title') or '').strip(), description=(ex.get('description') or '').strip(),
                         equipment=', '.join(ex.get('equipment') or []), movement=ex.get('movementType'), regions=regions)
    media = {'fileData': {'mimeType': 'video/mp4', 'fileUri': ex['videoUrl']}}
    if not has_video(ex):
        img = ex.get('exerciseImage') or ex.get('imageUrl') or ''
        if has_image(ex):
            mt = 'image/jpeg' if img.lower().endswith(('.jpg', '.jpeg')) else 'image/png'
            media = {'fileData': {'mimeType': mt, 'fileUri': img}}
            text += '\n\nATENÇÃO: não há vídeo, só a imagem do exercício. Baseie-se na imagem e no texto, e aumente a nota de entendimento se faltar informação.'
        else:
            media = None
            text += '\n\nATENÇÃO: não há vídeo nem imagem, só o texto. Deduza o movimento pelo texto e some pelo menos 3 à nota de entendimento.'
    body = {'contents': [{'role': 'user', 'parts': [m for m in (media, {'text': text}) if m]}],
        'generationConfig': {'responseMimeType': 'application/json', 'responseSchema': SCHEMA, 'temperature': 0.2}}
    inline, used = False, fonte(ex)
    for i in range(retries):
        try:
            if inline and used == 'video' and 'fileData' in body['contents'][0]['parts'][0]:
                body['contents'][0]['parts'][0] = {'inlineData': {'mimeType': 'video/mp4', 'data': shrink(ex['videoUrl'])}}
            req = urllib.request.Request(f'{BASE}/models/{MODEL}:generateContent', data=json.dumps(body).encode(),
                                         headers={'x-goog-api-key': key, 'Content-Type': 'application/json'})
            d = json.loads(urllib.request.urlopen(req, timeout=300).read())
            parts = d['candidates'][0]['content']['parts']
            out = json.loads(''.join(p.get('text', '') for p in parts if not p.get('thought')))
            return out, d.get('usageMetadata', {}), used
        except urllib.error.HTTPError as e:
            msg = f'HTTP {e.code}: {e.read().decode()[:200]}'
            if e.code == 403 and used == 'video' and not has_image(ex):
                used = 'imagem+texto'  # nothing to show: fall through to text only below
            if e.code == 403 and used == 'video':
                img = ex.get('exerciseImage') or ex.get('imageUrl')
                body['contents'][0]['parts'][0] = {'fileData': {'mimeType': 'image/png', 'fileUri': img}}
                body['contents'][0]['parts'][1]['text'] += ('\n\nATENÇÃO: o vídeo está indisponível, só há a imagem. '
                                                            'Baseie-se na imagem e no texto, e aumente a nota de entendimento.')
                used = 'imagem+texto'
                continue
            if e.code in (400, 403) and used == 'imagem+texto' and 'fileData' in body['contents'][0]['parts'][0]:
                parts = body['contents'][0]['parts']
                parts.pop(0)
                parts[0]['text'] += '\n\nATENÇÃO: a imagem também está indisponível. Use só o texto e some pelo menos 3 à nota de entendimento.'
                used = 'texto'
                continue
            if e.code == 400 and not inline:
                inline = True
                continue
            if e.code in (400, 403, 404) and i >= 1:
                return {'erro': msg}, {}, used
        except Exception as e:  # noqa: BLE001
            msg = repr(e)[:200]
        time.sleep(4 * 2 ** i)
    return {'erro': msg}, {}, used


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src'); ap.add_argument('out')
    ap.add_argument('--limit', type=int); ap.add_argument('--ids'); ap.add_argument('--workers', type=int, default=8)
    a = ap.parse_args()
    key = os.environ['GEMINI_API_KEY']
    items = json.load(open(a.src))['data']
    done = set()
    if os.path.exists(a.out):
        for line in open(a.out):
            r = json.loads(line)
            if 'erro' not in r['analise']:
                done.add(r['id'])
    if a.ids:
        want = set(a.ids.split(',')); items = [x for x in items if x['_id'] in want]
    items = [x for x in items if x['_id'] not in done]
    if a.limit:
        items = items[:a.limit]
    print(f'{len(items)} to analyze ({len(done)} done)', flush=True)
    tok = [0]; n = [0]

    def work(ex):
        res, usage, used = call(ex, key)
        with lock:
            with open(a.out, 'a') as f:
                f.write(json.dumps({'id': ex['_id'], 'fonte': used, 'analise': res}, ensure_ascii=False) + '\n')
            tok[0] += usage.get('totalTokenCount', 0); n[0] += 1
            if n[0] % 25 == 0 or 'erro' in res:
                print(f'{n[0]}/{len(items)} tokens={tok[0]} {"ERRO " + res["erro"] if "erro" in res else ""}', flush=True)

    with ThreadPoolExecutor(a.workers) as pool:
        list(pool.map(work, items))
    print('done', n[0], 'tokens', tok[0], flush=True)


if __name__ == '__main__':
    main()
