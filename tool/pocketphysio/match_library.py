"""Second pass (text only): for each analysed PocketPhysio exercise, find the
closest exercise in a reference library and classify it as identico / variacao /
novo. Batches of 25 per Gemini call.

    bash -ic "python3 -I tool/pocketphysio/match_library.py <analise.jsonl> kineti catalog.json <out.jsonl>"
    bash -ic "python3 -I tool/pocketphysio/match_library.py <analise.jsonl> deskbreak <desk-break library/exercises.json> <out.jsonl>"

Resumable: ids already in out.jsonl are skipped.
"""
import json, os, sys, time, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor

MODEL = 'gemini-3-flash-preview'
BASE = 'https://aiplatform.googleapis.com/v1/projects/143173535779/locations/global/publishers/google'
SCHEMA = {'type': 'ARRAY', 'items': {'type': 'OBJECT', 'properties': {
    'id': {'type': 'STRING'},
    'kineti_slug': {'type': 'STRING', 'description': 'identificador do exercício da biblioteca mais próximo, ou vazio'},
    'relacao': {'type': 'STRING', 'enum': ['identico', 'variacao', 'novo']},
}, 'required': ['id', 'kineti_slug', 'relacao']}}

PROMPT = """Biblioteca de referência (exercícios que já têm animação pronta):
{kineti}

Para cada exercício abaixo, diga qual exercício da biblioteca é o mais próximo (pelo identificador antes dos dois-pontos) e a relação:
- identico: mesmo movimento, mesma posição e mesmo acessório (pequenas diferenças de repetição/ritmo não importam)
- variacao: mesmo movimento-base com uma mudança que reaproveita a cena (outro acessório, braços em outra posição, unilateral, outra altura, apoio diferente)
- novo: exige outra posição, outro movimento ou outra cena
Seja rigoroso: na dúvida entre variacao e novo, escolha novo.

Exercícios:
{batch}"""


def main():
    analysis, kind, library, out = sys.argv[1:5]
    key = os.environ['GEMINI_API_KEY']
    cat = json.load(open(library))['exercises']
    if kind == 'kineti':
        lines = [(e['slug'], f"{e['name']} — {e['desc']} (acessórios: {e['props']})") for e in cat]
    else:  # desk-break: mannequin, no props besides an optional chair
        lines = [(e['id'], f"{e['en']} — {' '.join(x.lstrip('!') for x in e.get('steps_en', []))}"
                           f"{' (sentado na cadeira)' if e.get('seated') else ''}") for e in cat]
    kineti = '\n'.join(f'- {i}: {t}' for i, t in lines)
    slugs = {i for i, _ in lines}
    done = set()
    if os.path.exists(out):
        done = {json.loads(l)['id'] for l in open(out)}
    rows = {}
    for line in open(analysis):
        r = json.loads(line)
        if 'erro' not in r['analise']:
            rows[r['id']] = r['analise']
    todo = [(i, a) for i, a in rows.items() if i not in done]
    batches = [todo[i:i + 25] for i in range(0, len(todo), 25)]
    print(len(todo), 'to match in', len(batches), 'batches', flush=True)

    def work(batch):
        text = '\n'.join(f"[{i}] {a['nome_pt']} — {a['descricao_pt']} (posição: {a['posicao_inicial']}; acessórios: "
                         f"{', '.join(a.get('equipamentos') or [])})" for i, a in batch)
        body = {'contents': [{'role': 'user', 'parts': [{'text': PROMPT.format(kineti=kineti, batch=text)}]}],
                'generationConfig': {'responseMimeType': 'application/json', 'responseSchema': SCHEMA, 'temperature': 0, 'maxOutputTokens': 32768}}
        for k in range(5):
            try:
                req = urllib.request.Request(f'{BASE}/models/{MODEL}:generateContent', data=json.dumps(body).encode(),
                                             headers={'x-goog-api-key': key, 'Content-Type': 'application/json'})
                d = json.loads(urllib.request.urlopen(req, timeout=300).read())
                parts = d['candidates'][0]['content']['parts']
                res = json.loads(''.join(p.get('text', '') for p in parts if not p.get('thought')))
                ids = {i for i, _ in batch}
                return [r for r in res if r['id'] in ids]
            except Exception as e:  # noqa: BLE001
                print('retry', k, repr(e)[:150], flush=True)
                time.sleep(5 * 2 ** k)
        return []

    with ThreadPoolExecutor(8) as pool:
        for res in pool.map(work, batches):
            with open(out, 'a') as f:
                for r in res:
                    if r['kineti_slug'] not in slugs:
                        r['kineti_slug'], r['relacao'] = '', 'novo'
                    f.write(json.dumps(r, ensure_ascii=False) + '\n')
    print('done', flush=True)


if __name__ == '__main__':
    main()
